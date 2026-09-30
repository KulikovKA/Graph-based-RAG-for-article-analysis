"""Compact deterministic baseline and typed reranking result records."""

from __future__ import annotations

import math
import re
import unicodedata
from collections import Counter
from collections.abc import Awaitable, Callable, Sequence
from dataclasses import dataclass

from app.domain.evidence import CandidateEvidence

TOKEN_RE = re.compile(r"[^\W_]+", re.UNICODE)


def _terms(text: str) -> list[str]:
    normalized = unicodedata.normalize("NFKC", text).casefold()
    return [item for item in TOKEN_RE.findall(normalized) if len(item) > 1]


@dataclass(frozen=True)
class RankedCandidate:
    candidate: CandidateEvidence
    score: float


def lexical_scores(query: str, documents: Sequence[str]) -> list[float]:
    """Small BM25 implementation used as the compact CPU baseline/fallback."""
    query_terms = _terms(query)
    tokenized = [_terms(document) for document in documents]
    if not tokenized:
        return []
    average_length = sum(map(len, tokenized)) / len(tokenized) or 1.0
    document_frequency = Counter(term for doc in tokenized for term in set(doc))
    scores: list[float] = []
    for tokens in tokenized:
        frequencies = Counter(tokens)
        length = len(tokens)
        score = 0.0
        for term in query_terms:
            frequency = frequencies[term]
            if not frequency:
                continue
            inverse = math.log(1 + (len(tokenized) - document_frequency[term] + 0.5)
                               / (document_frequency[term] + 0.5))
            score += inverse * frequency * 2.2 / (
                frequency + 1.2 * (0.25 + 0.75 * length / average_length)
            )
        scores.append(score)
    return scores


def _ordered(
    candidates: Sequence[CandidateEvidence], scores: Sequence[float], limit: int
) -> tuple[RankedCandidate, ...]:
    if len(scores) != len(candidates) or any(not math.isfinite(float(value)) for value in scores):
        raise ValueError("reranker returned invalid scores")
    ranked = [RankedCandidate(item, float(score))
              for item, score in zip(candidates, scores, strict=True)]
    ranked.sort(key=lambda item: (
        -item.score, item.candidate.source, item.candidate.external_id,
        str(item.candidate.document_id), str(item.candidate.chunk_id),
    ))
    return tuple(ranked[:limit])


def _validate_request(query: str, limit: int) -> None:
    if not query.strip() or not 1 <= limit <= 15:
        raise ValueError("query and a limit from 1 to 15 are required")


def rank_candidates_bm25(
    query: str, candidates: Sequence[CandidateEvidence], *, limit: int = 12
) -> tuple[RankedCandidate, ...]:
    """Explicit no-model baseline/fallback; the selected production scorer is Qwen."""
    _validate_request(query, limit)
    if not candidates:
        return ()
    texts = [f"{item.title}\n{item.section}\n{item.text}" for item in candidates]
    return _ordered(candidates, lexical_scores(query, texts), limit)


async def rerank_candidates(
    query: str,
    candidates: Sequence[CandidateEvidence],
    *,
    score_documents: Callable[[str, list[str]], Awaitable[Sequence[float]]],
    limit: int = 12,
) -> tuple[RankedCandidate, ...]:
    """Apply the configured Qwen cross-encoder and deterministic tie-breaks."""
    _validate_request(query, limit)
    if not candidates:
        return ()
    texts = [f"{item.title}\n{item.section}\n{item.text}" for item in candidates]
    scores = list(await score_documents(query, texts))
    return _ordered(candidates, scores, limit)
