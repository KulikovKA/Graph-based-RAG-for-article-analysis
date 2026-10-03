from __future__ import annotations

import asyncio
import json
from argparse import Namespace
from contextlib import nullcontext
from pathlib import Path
from typing import Any, cast
from uuid import uuid4

import httpx
import pytest
import scripts.hybrid_concept_backfill as backfill

from app.domain.inference import (
    InferenceMetadata,
    InferenceOutputLimit,
    InferenceProtocolError,
    InferenceProvider,
    InferenceTimeout,
    JsonResult,
)
from app.storage.models import EvidenceChunk


def result(value: dict[str, Any]) -> JsonResult:
    return JsonResult(
        value=value,
        metadata=InferenceMetadata(
            provider="fake",
            model_id=backfill.MODEL_ID,
            model_revision=None,
            finish_reason="stop",
            model_ttft_ms=None,
            model_ttft_reason=None,
            reasoning_duration_ms=None,
            reasoning_duration_reason=None,
            reasoning_tokens=None,
            reasoning_tokens_reason=None,
            output_duration_ms=None,
            output_duration_reason=None,
            output_tokens=None,
            output_tokens_reason=None,
            total_ms=1,
            load_ms=None,
            load_reason=None,
        ),
    )


class FakeProvider:
    def __init__(self, responses: list[JsonResult | Exception]) -> None:
        self.responses = iter(responses)
        self.requests: list[dict[str, Any]] = []

    async def complete_json(self, **kwargs: Any) -> JsonResult:
        self.requests.append(kwargs)
        response = next(self.responses)
        if isinstance(response, Exception):
            raise response
        return response


def draft(**changes: Any) -> dict[str, Any]:
    return {
        "concept_type": "MATERIAL",
        "canonical_name": "graphene",
        "surface_text": "graphene",
        "quote": "graphene sensor",
        "start_offset": 0,
        "end_offset": 8,
        "qualifiers": {},
        **changes,
    }


def chunk(text: str = "graphene sensor") -> EvidenceChunk:
    return EvidenceChunk(id=uuid4(), revision_id=uuid4(), text=text)


def extract(
    provider: FakeProvider, diagnostic: dict[str, Any], source: EvidenceChunk | None = None
) -> tuple[Any, float, int, int]:
    return asyncio.run(
        backfill._extract(cast(InferenceProvider, provider), source or chunk(), diagnostic)
    )


@pytest.mark.parametrize(
    "drafts,outcome,accepted,rejected,reasons",
    [
        ([], "MODEL_EMPTY", 0, 0, {}),
        ([draft(canonical_name="NO2")], "ALL_REJECTED", 0, 1, {"UNSUPPORTED_CANONICAL_NAME": 1}),
        (
            [draft(), draft(canonical_name="NH3")],
            "PARTIALLY_ACCEPTED",
            1,
            1,
            {"UNSUPPORTED_CANONICAL_NAME": 1},
        ),
        ([draft(), draft()], "ACCEPTED", 2, 0, {}),
    ],
)
def test_document_counts_distinguish_empty_rejection_partial_and_dedup(
    drafts: list[dict[str, Any]],
    outcome: str,
    accepted: int,
    rejected: int,
    reasons: dict[str, int],
) -> None:
    diagnostic: dict[str, Any] = {}
    mentions, _, rejects, attempts = extract(
        FakeProvider([result({"mentions": drafts})]), diagnostic
    )
    assert (len(mentions), rejects, attempts) == (accepted, rejected, 1)
    document = {"document_attempt": 1, "chunks": [diagnostic]}
    backfill._summarize_document(document, status="completed", accepted_mentions=min(accepted, 1))
    assert document["status"] == "completed"
    assert document["outcome"] == outcome
    assert document["candidate_count"] == accepted + rejected
    assert document["accepted_candidate_count"] == accepted
    assert document["accepted_mentions"] == min(accepted, 1)
    assert document["duplicate_count"] == max(accepted - 1, 0)
    assert document["rejected_candidate_count"] == rejected
    assert document["rejection_reasons"] == reasons


def test_length_retry_is_retained_separately_from_final_candidate_counts() -> None:
    provider = FakeProvider(
        [
            InferenceOutputLimit(max_output_tokens=2048),
            result({"mentions": [draft()]}),
        ]
    )
    diagnostic: dict[str, Any] = {}
    mentions, _, _, attempts = extract(provider, diagnostic)
    assert attempts == 2 and len(mentions) == 1
    assert [r["max_output_tokens"] for r in provider.requests] == [2048, 3072]
    assert [r["status"] for r in diagnostic["inference_attempts"]] == ["OUTPUT_LIMIT", "success"]
    document = {"document_attempt": 2, "chunks": [diagnostic]}
    backfill._summarize_document(document, status="completed", accepted_mentions=1)
    assert document["candidate_count"] == 1
    assert document["inference_attempts"] == 2
    assert document["inference_retries"] == 1
    assert document["document_retries"] == 1


def test_document_failure_keeps_known_counts_but_not_unprocessed_chunk_totals() -> None:
    diagnostic: dict[str, Any] = {}
    extract(FakeProvider([result({"mentions": [draft()]})]), diagnostic)
    document = {"document_attempt": 1, "expected_chunk_count": 2, "chunks": [diagnostic]}
    backfill._summarize_document(document, status="failed", error_code="PROCESSING_ERROR")
    assert document["candidate_count"] is None
    assert document["accepted_candidate_count"] == 1
    document["expected_chunk_count"] = 1
    backfill._summarize_document(document, status="failed", error_code="PROCESSING_ERROR")
    assert document["candidate_count"] == 1
    assert document["rejected_candidate_count"] == 0
    assert document["accepted_mentions"] == 0


@pytest.mark.parametrize(
    "response,code",
    [
        (InferenceTimeout("SECRET_CHUNK_REASONING"), "TIMEOUT"),
        (InferenceProtocolError("final output is not JSON"), "UNPARSEABLE_RESULT"),
        (InferenceProtocolError("SECRET_CHUNK_REASONING"), "PROTOCOL_ERROR"),
        (result({}), "INVALID_ENVELOPE"),
        (result({"mentions": "SECRET_CHUNK_REASONING"}), "INVALID_ENVELOPE"),
        (result({"mentions": [], "thinking": "SECRET_CHUNK_REASONING"}), "INVALID_ENVELOPE"),
    ],
)
def test_failed_results_keep_unknown_counts_and_safe_codes(
    response: JsonResult | Exception,
    code: str,
) -> None:
    diagnostic: dict[str, Any] = {}
    with pytest.raises((InferenceTimeout, InferenceProtocolError)):
        extract(FakeProvider([response]), diagnostic)
    document = {"document_attempt": 1, "chunks": [diagnostic]}
    backfill._summarize_document(document, status="failed", error_code=code)
    assert document["outcome"] == code
    assert document["candidate_count"] is None
    assert document["rejected_candidate_count"] is None
    assert document["accepted_mentions"] == 0
    assert diagnostic["status"] == code
    assert "SECRET_CHUNK_REASONING" not in json.dumps(document)


def test_rejection_codes_do_not_retain_candidate_values() -> None:
    diagnostic: dict[str, Any] = {}
    responses = [
        "SECRET_CHUNK_REASONING",
        draft(quote="SECRET_CHUNK_REASONING"),
        draft(concept_type="SECRET_CHUNK_REASONING"),
        draft(surface_text=""),
        draft(extra="SECRET_CHUNK_REASONING"),
    ]
    _, _, rejected, _ = extract(FakeProvider([result({"mentions": responses})]), diagnostic)
    assert rejected == 5
    assert diagnostic["rejection_reasons"] == {
        "DRAFT_NOT_OBJECT": 1,
        "NO_EXACT_SOURCE_OCCURRENCE": 1,
        "DRAFT_SCHEMA_INVALID": 2,
        "QUOTE_SURFACE_REQUIRED": 1,
    }
    assert "SECRET_CHUNK_REASONING" not in json.dumps(diagnostic)


def test_ambiguous_reanchor_is_counted_but_unicode_repair_is_accepted() -> None:
    diagnostic: dict[str, Any] = {}
    _, _, rejects, _ = extract(
        FakeProvider([result({"mentions": [draft(start_offset=99)]})]),
        diagnostic,
        chunk("graphene sensor; graphene sensor"),
    )
    assert rejects == 1
    assert diagnostic["rejection_reasons"] == {"AMBIGUOUS_SOURCE_OCCURRENCE": 1}
    mentions, _, rejects, _ = extract(
        FakeProvider([result({"mentions": [draft(start_offset=99)]})]),
        diagnostic,
        chunk("🧪 е\u0301 graphene sensor"),
    )
    assert rejects == 0
    assert mentions[0].start_offset == 5


def test_failed_retry_keeps_both_attempts_and_no_invented_counts() -> None:
    diagnostic: dict[str, Any] = {}
    with pytest.raises(InferenceTimeout):
        extract(
            FakeProvider(
                [
                    InferenceOutputLimit(max_output_tokens=2048),
                    InferenceTimeout("SECRET"),
                ]
            ),
            diagnostic,
        )
    assert [a["status"] for a in diagnostic["inference_attempts"]] == ["OUTPUT_LIMIT", "TIMEOUT"]
    assert diagnostic["candidate_count"] is None


def test_sidecar_retains_failed_document_attempt_on_resume(tmp_path: Path) -> None:
    path = tmp_path / "checkpoint.diagnostics.json"
    run_id = uuid4()
    data = backfill._read_diagnostics(path, run_id)
    data["documents"]["synthetic-document"] = [{"status": "failed", "outcome": "TIMEOUT"}]
    backfill._save_diagnostics(path, data)
    resumed = backfill._read_diagnostics(path, run_id)
    resumed["documents"]["synthetic-document"].append({"status": "completed"})
    backfill._save_diagnostics(path, resumed)
    assert len(backfill._read_diagnostics(path, run_id)["documents"]["synthetic-document"]) == 2
    assert backfill._read_diagnostics(path, uuid4())["documents"] == {}


def test_malformed_sidecar_cannot_interrupt_authoritative_processing(tmp_path: Path) -> None:
    path = tmp_path / "checkpoint.diagnostics.json"
    run_id = uuid4()
    path.write_text(
        json.dumps(
            {
                "version": "hybrid-document-diagnostics-v1",
                "run_id": str(run_id),
                "documents": {"synthetic-document": 99},
            }
        ),
        encoding="utf-8",
    )
    assert backfill._read_diagnostics(path, run_id)["documents"] == {}
    path.write_text("not json", encoding="utf-8")
    assert backfill._read_diagnostics(path, run_id)["documents"] == {}


def test_diagnostics_write_failure_does_not_interrupt_caller(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    def fail_write(*args: Any) -> None:
        raise OSError("SECRET_CHUNK_REASONING")

    monkeypatch.setattr(backfill, "_write", fail_write)
    backfill._save_diagnostics(tmp_path / "diagnostics.json", {"documents": {}})
    assert capsys.readouterr().out == "DIAGNOSTICS_WRITE_FAILED\n"


def runner(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
    provider: FakeProvider,
    source: EvidenceChunk,
) -> tuple[Namespace, list[tuple[str, dict[str, Any]]]]:
    statements: list[tuple[str, dict[str, Any]]] = []
    document_id = str(uuid4())

    class Session:
        def execute(self, statement: Any, params: dict[str, Any]) -> None:
            statements.append((str(statement), params))

    class Sessions:
        def begin(self) -> Any:
            return nullcontext(Session())

    class Engine:
        def dispose(self) -> None:
            pass

    class Client:
        async def get(self, *args: Any, **kwargs: Any) -> httpx.Response:
            return httpx.Response(
                200,
                request=httpx.Request("GET", "https://synthetic.test"),
                json={"models": [{"name": backfill.MODEL_ID, "digest": backfill.MODEL_DIGEST}]},
            )

        async def aclose(self) -> None:
            pass

    async def project(rows: list[dict[str, Any]], run_id: Any) -> int:
        assert all(row["chunk_id"] == str(source.id) for row in rows)
        assert any("INSERT INTO concept_mentions" in sql for sql, _ in statements) or not rows
        return len(rows)

    monkeypatch.setenv("DATABASE_URL", "synthetic")
    monkeypatch.setenv("NEO4J_PASSWORD", "synthetic")
    monkeypatch.setattr(backfill, "_snapshot", lambda: {"snapshot_hash": "synthetic", "facts": []})
    monkeypatch.setattr(backfill, "make_engine", lambda _: Engine())
    monkeypatch.setattr(backfill, "sessionmaker", lambda *a, **kw: Sessions())
    monkeypatch.setattr(
        backfill,
        "_read_docs",
        lambda *a: [
            {
                "document_id": document_id,
                "revision_id": str(source.revision_id),
                "title": "Synthetic",
                "chunks": [source],
                "raw_feature_count": 0,
            }
        ],
    )
    monkeypatch.setattr(backfill, "_make_provider", lambda: (provider, Client()))
    monkeypatch.setattr(backfill, "_neo4j_project", project)
    return Namespace(
        report_dir=str(tmp_path / "reports"),
        checkpoint=str(tmp_path / "checkpoint.json"),
        report_only=False,
        dry_run=False,
        max_documents=None,
        resume=False,
    ), statements


def test_runner_diagnostics_failure_preserves_authoritative_mentions_and_chunk_ids(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    source = chunk()
    args, statements = runner(
        monkeypatch,
        tmp_path,
        FakeProvider([result({"mentions": [draft(), draft(), draft(canonical_name="NO2")]})]),
        source,
    )
    original_write = backfill._write

    def fail_sidecar(path: Path, value: Any) -> None:
        if path.name.endswith(".diagnostics.json"):
            raise OSError("SECRET_REASONING")
        original_write(path, value)

    monkeypatch.setattr(backfill, "_write", fail_sidecar)
    assert asyncio.run(backfill.main_async(args)) == 0
    inserted = [params for sql, params in statements if "INSERT INTO concept_mentions" in sql]
    assert len(inserted) == 1
    assert inserted[0]["ch"] == source.id
    assert inserted[0]["v"] == source.revision_id
    checkpoint = json.loads(Path(args.checkpoint).read_text(encoding="utf-8"))
    assert len(checkpoint["completed"]) == 1
    assert len(checkpoint["mentions"]) == 1
    assert checkpoint["validation_rejects"] == 1
    assert "DIAGNOSTICS_WRITE_FAILED" in capsys.readouterr().out


def test_runner_failed_outer_attempt_is_retained_after_resume_and_safe_success(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    provider = FakeProvider(
        [
            InferenceTimeout("SECRET_REASONING"),
            result({"mentions": [draft()]}),
        ]
    )
    args, statements = runner(monkeypatch, tmp_path, provider, chunk())
    assert asyncio.run(backfill.main_async(args)) == 2
    args.resume = True
    assert asyncio.run(backfill.main_async(args)) == 0
    sidecar = Path(args.checkpoint).with_suffix(".diagnostics.json").read_text(encoding="utf-8")
    records = next(iter(json.loads(sidecar)["documents"].values()))
    assert [r["status"] for r in records] == ["failed", "completed"]
    assert records[0]["outcome"] == "TIMEOUT"
    assert records[0]["candidate_count"] is None
    assert records[1]["document_attempt"] == 2
    assert records[1]["candidate_count"] == records[1]["accepted_mentions"] == 1
    assert "SECRET_REASONING" not in sidecar
    assert "SECRET_REASONING" not in Path(args.checkpoint).read_text(encoding="utf-8")
    assert "SECRET_REASONING" not in str(statements)
    assert "SECRET_REASONING" not in capsys.readouterr().out
