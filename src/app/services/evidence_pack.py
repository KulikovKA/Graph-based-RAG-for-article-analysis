"""Exact, section-aware Analyst evidence selection under its prompt budget."""

from __future__ import annotations

import hashlib
import json
import math
import re
from collections.abc import Callable, Sequence
from dataclasses import asdict, dataclass
from pathlib import Path
from uuid import UUID, uuid4

from app.services.rerank import RankedCandidate, _terms

SENTENCE_RE = re.compile(r"[^.!?。！？\n]+(?:[.!?。！？]+|\n+|$)")


@dataclass(frozen=True)
class EvidencePackItem:
    evidence_id: UUID
    document_id: UUID
    revision_id: UUID
    chunk_id: UUID
    source: str
    external_id: str
    canonical_url: str
    title: str
    section: str
    language: str
    span_start: int
    span_end: int
    quoted_span: str
    retrieval_score: float
    rerank_score: float


@dataclass(frozen=True)
class EvidencePack:
    items: tuple[EvidencePackItem, ...]
    token_count: int
    token_budget: int


class TokenizerJsonCounter:
    """Count prompt tokens with the pinned model tokenizer JSON."""

    def __init__(self, tokenizer: object) -> None:
        self._tokenizer = tokenizer

    @classmethod
    def from_file(cls, path: Path, *, expected_sha256: str) -> TokenizerJsonCounter:
        actual_sha256 = hashlib.sha256(path.read_bytes()).hexdigest()
        if actual_sha256 != expected_sha256:
            raise ValueError("Analyst tokenizer SHA-256 does not match model inventory")
        try:
            from tokenizers import Tokenizer  # type: ignore[import-untyped]
        except ImportError as exc:
            raise RuntimeError("tokenizers is required for evidence budgeting") from exc
        return cls(Tokenizer.from_file(str(path)))

    def __call__(self, text: str) -> int:
        encode = getattr(self._tokenizer, "encode", None)
        if not callable(encode):
            raise TypeError("tokenizer must provide encode(text)")
        encoded = encode(text, add_special_tokens=True)
        ids = getattr(encoded, "ids", None)
        if not isinstance(ids, list):
            raise TypeError("tokenizer encode() did not return token IDs")
        return len(ids)


def render_evidence_items(items: Sequence[EvidencePackItem]) -> str:
    """Canonical prompt representation counted by the pack budget."""
    return json.dumps([asdict(item) for item in items], ensure_ascii=False,
                      separators=(",", ":"), default=str)


def _snippets(text: str, query: str) -> list[tuple[int, int, str, float]]:
    query_terms = set(_terms(query))
    snippets: list[tuple[int, int, str, float]] = []
    for match in SENTENCE_RE.finditer(text):
        start, end = match.span()
        while start < end and text[start].isspace():
            start += 1
        while end > start and text[end - 1].isspace():
            end -= 1
        quote = text[start:end]
        if not quote:
            continue
        tokens = _terms(quote)
        overlap = len(query_terms.intersection(tokens))
        score = overlap / math.sqrt(max(1, len(tokens)))
        if score > 0:
            snippets.append((start, end, quote, score))
    snippets.sort(key=lambda item: (-item[3], item[0]))
    return snippets[:3]


def _rendered_prompt(prefix: str, body: str, suffix: str) -> str:
    return prefix + body + suffix


def build_evidence_pack(
    ranked: Sequence[RankedCandidate],
    *,
    query: str,
    token_counter: Callable[[str], int],
    prompt_prefix: str = "",
    prompt_suffix: str = "",
    token_budget: int = 6000,
    max_documents: int = 12,
) -> EvidencePack:
    """Select 1–3 matching sentence spans per document, counting the whole prompt.

    Offsets are Unicode code-point half-open spans inside the immutable chunk text,
    matching EVAL-000's declared offset unit. The quote is always an exact slice.
    """
    if token_budget < 1 or not 1 <= max_documents <= 15:
        raise ValueError("invalid evidence pack budget or document limit")
    if token_counter(_rendered_prompt(prompt_prefix, "", prompt_suffix)) > token_budget:
        raise ValueError("Analyst prompt framing exceeds token budget")
    selected: list[EvidencePackItem] = []
    seen_docs: set[UUID] = set()
    body_items: list[EvidencePackItem] = []
    for entry in ranked:
        candidate = entry.candidate
        if candidate.document_id in seen_docs:
            continue
        additions: list[EvidencePackItem] = []
        for start, end, quote, _ in _snippets(candidate.text, query):
            item = EvidencePackItem(
                evidence_id=uuid4(), document_id=candidate.document_id,
                revision_id=candidate.revision_id, chunk_id=candidate.chunk_id,
                source=candidate.source, external_id=candidate.external_id,
                canonical_url=candidate.canonical_url, title=candidate.title,
                section=candidate.section, language=candidate.language,
                span_start=start, span_end=end, quoted_span=quote,
                retrieval_score=candidate.score, rerank_score=entry.score,
            )
            trial_items = [*body_items, *additions, item]
            trial = render_evidence_items(trial_items)
            if token_counter(_rendered_prompt(prompt_prefix, trial, prompt_suffix)) > token_budget:
                continue
            additions.append(item)
        if additions:
            selected.extend(additions)
            body_items.extend(additions)
            seen_docs.add(candidate.document_id)
        if len(seen_docs) >= max_documents:
            break
    rendered = render_evidence_items(body_items)
    count = token_counter(_rendered_prompt(prompt_prefix, rendered, prompt_suffix))
    if count > token_budget:
        raise AssertionError("evidence pack exceeded token budget")
    return EvidencePack(tuple(selected), count, token_budget)
