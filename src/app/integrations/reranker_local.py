"""Изолированный CPU-процесс Qwen reranker с остановкой при отмене."""

import asyncio
import multiprocessing as mp
import os
import time
from multiprocessing.connection import Connection
from multiprocessing.process import BaseProcess
from pathlib import Path
from typing import cast

from app.domain.inference import (
    InferenceCancelled,
    InferenceConfigurationError,
    InferenceTimeout,
    InferenceUnavailable,
)


def _worker(connection: Connection, model_path: str, max_length: int) -> None:
    os.environ["HF_HUB_OFFLINE"] = "1"
    os.environ["TRANSFORMERS_OFFLINE"] = "1"
    os.environ["HF_HUB_DISABLE_PROGRESS_BARS"] = "1"
    os.environ["TQDM_DISABLE"] = "1"
    try:
        import torch
        from transformers import AutoModelForCausalLM, AutoTokenizer
        from transformers.utils import logging as transformers_logging

        transformers_logging.disable_progress_bar()  # type: ignore[no-untyped-call]

        tokenizer = AutoTokenizer.from_pretrained(model_path, local_files_only=True,
                                                   padding_side="left")
        tokenizer.pad_token = tokenizer.eos_token
        model = AutoModelForCausalLM.from_pretrained(model_path, local_files_only=True)
        model.eval()  # type: ignore[no-untyped-call]
        no_id = tokenizer.convert_tokens_to_ids("no")
        yes_id = tokenizer.convert_tokens_to_ids("yes")
        prefix = ("<|im_start|>system\nJudge whether the Document meets the requirements "
                  "based on the Query and the Instruct provided. Note that the answer "
                  "can only be \"yes\" or \"no\".<|im_end|>\n<|im_start|>user\n")
        suffix = "<|im_end|>\n<|im_start|>assistant\n<think>\n\n</think>\n\n"
        prefix_ids = tokenizer.encode(prefix, add_special_tokens=False)
        suffix_ids = tokenizer.encode(suffix, add_special_tokens=False)
        budget = max_length - len(prefix_ids) - len(suffix_ids)
        if budget < 1:
            raise ValueError("reranker max_length is too small")
        connection.send(("ready", None))
        while True:
            message = connection.recv()
            if message is None:
                return
            query, documents = message
            scores: list[float] = []
            for start in range(0, len(documents), 4):
                batch = documents[start:start + 4]
                ids = [
                    prefix_ids + tokenizer.encode(
                        "<Instruct>: Given a web search query, retrieve relevant passages "
                        "that answer the query\n<Query>: " + query + "\n<Document>: " + document,
                        add_special_tokens=False,
                    )[:budget] + suffix_ids
                    for document in batch
                ]
                inputs = tokenizer.pad({"input_ids": ids}, padding=True,
                                       return_tensors="pt")
                with torch.no_grad():
                    logits = model(**inputs).logits[:, -1, [no_id, yes_id]]
                    scores.extend(torch.softmax(logits.float(), dim=1)[:, 1].tolist())
            connection.send(("scores", [float(value) for value in scores]))
    except (EOFError, KeyboardInterrupt):
        return
    except Exception:
        try:
            connection.send(("error", None))
        except (BrokenPipeError, OSError):
            pass
    finally:
        connection.close()


class LocalQwenReranker:
    def __init__(self, *, model_id: str, model_path: Path, max_length: int = 1024) -> None:
        if not model_id or not model_path.is_dir() or max_length < 1:
            raise InferenceConfigurationError("invalid local reranker configuration")
        self.model_id = model_id
        self.model_path = model_path
        self.max_length = max_length
        self._process: BaseProcess | None = None
        self._connection: Connection | None = None
        self._lock = asyncio.Lock()

    @property
    def pid(self) -> int | None:
        return self._process.pid if self._process is not None else None

    async def _stop(self) -> None:
        connection, process = self._connection, self._process
        self._connection = None
        self._process = None
        if connection is not None:
            connection.close()
        if process is not None:
            if process.is_alive():
                process.terminate()
            await asyncio.to_thread(process.join, 5)
            if process.is_alive():
                process.kill()
                await asyncio.to_thread(process.join, 5)

    async def close(self) -> None:
        async with self._lock:
            await self._stop()

    async def _receive(self, deadline: float, cancel: asyncio.Event | None) -> tuple[str, object]:
        assert self._connection is not None
        while True:
            if cancel is not None and cancel.is_set():
                raise InferenceCancelled("reranking cancelled")
            if time.monotonic() >= deadline:
                raise InferenceTimeout("reranking deadline exceeded")
            if await asyncio.to_thread(self._connection.poll, 0.05):
                try:
                    kind, payload = self._connection.recv()
                except EOFError:
                    raise InferenceUnavailable("reranker process stopped") from None
                return str(kind), payload
            if self._process is None or not self._process.is_alive():
                raise InferenceUnavailable("reranker process stopped")

    async def _start(self, deadline: float, cancel: asyncio.Event | None) -> None:
        if self._process is not None and self._process.is_alive():
            return
        await self._stop()
        parent, child = mp.get_context("spawn").Pipe()
        process = mp.get_context("spawn").Process(
            target=_worker, args=(child, str(self.model_path), self.max_length), daemon=True
        )
        process.start()
        child.close()
        self._process = process
        self._connection = cast(Connection, parent)
        kind, _ = await self._receive(deadline, cancel)
        if kind != "ready":
            raise InferenceUnavailable("reranker startup failed")

    async def score(
        self, *, model_id: str, query: str, documents: list[str],
        timeout: float, cancel: asyncio.Event | None,
    ) -> list[float]:
        if model_id != self.model_id:
            raise InferenceConfigurationError("unknown reranker model")
        if timeout <= 0 or not query.strip() or not documents or any(
            not item.strip() for item in documents
        ):
            raise InferenceConfigurationError("invalid reranking request")
        deadline = time.monotonic() + timeout
        async with self._lock:
            try:
                await self._start(deadline, cancel)
                assert self._connection is not None
                self._connection.send((query, documents))
                kind, payload = await self._receive(deadline, cancel)
                if kind != "scores" or not isinstance(payload, list) or len(payload) != len(
                    documents
                ):
                    raise InferenceUnavailable("reranker returned invalid scores")
                return [float(value) for value in payload]
            except BaseException:
                await self._stop()
                raise
