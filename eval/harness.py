"""Замороженные inputs и проверка validated артефактов, без сырых drafts."""

from __future__ import annotations

import hashlib
import json
from dataclasses import asdict
from pathlib import Path
from typing import Any, Literal, cast
from uuid import NAMESPACE_URL, UUID, uuid5

from pydantic import BaseModel, ConfigDict, Field, ValidationError

from app.domain.contracts import (
    AnalysisV1,
    AnswerPresentationV1,
    AnswerV1,
    CoverageV1,
    PublicAnalysisV1,
)
from app.domain.inference import InferenceProvider, InferenceUnavailable
from app.domain.planner import FeatureV1, IdeaV1
from app.services.analyst import (
    Analyst,
    AnalystViolation,
    validate_analysis,
    validate_projections,
)
from app.services.evidence_pack import EvidencePack, EvidencePackItem
from app.services.rerank import _terms, lexical_scores

ROOT = Path(__file__).resolve().parents[1]


def sha(path: Path) -> str:
    # Text-only inputs: одинаковая identity при Git checkout с CRLF и LF.
    return hashlib.sha256(path.read_bytes().replace(b"\r\n", b"\n")).hexdigest()


def uid(value: str) -> UUID:
    return uuid5(NAMESPACE_URL, "eval001/" + value)


def index_identity(manifest: dict[str, Any]) -> str:
    entries = [
        (doc["external_id"], _terms(doc["title"] + " " + doc["sections"][0]["text"]))
        for doc in sorted(manifest["documents"], key=lambda item: item["external_id"])
    ]
    return hashlib.sha256(json.dumps(entries, ensure_ascii=False).encode("utf-8")).hexdigest()


class Evidence(BaseModel):
    model_config = ConfigDict(extra="forbid")
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
    span_start: int = Field(strict=True, ge=0)
    span_end: int = Field(strict=True, gt=0)
    quoted_span: str
    retrieval_score: float = Field(allow_inf_nan=False)
    rerank_score: float = Field(allow_inf_nan=False)


class Observation(BaseModel):
    model_config = ConfigDict(extra="forbid")
    case_id: str
    status: Literal["completed", "failed", "cancelled"]
    outcome: Literal["analysis", "safe_fallback", "no_evidence", "clarification"] | None
    idea: IdeaV1
    coverage: CoverageV1
    candidate_ids: list[str]
    evidence: list[Evidence]
    analysis: AnalysisV1 | None
    answer: AnswerV1 | None
    public_analysis: PublicAnalysisV1 | None
    presentation: AnswerPresentationV1 | None
    elapsed_ms: float | None = Field(default=None, ge=0, allow_inf_nan=False)
    timing_reason: Literal["NOT_MEASURED", "OFFLINE_REPLAY", "MEASURED"] = "NOT_MEASURED"
    replay: list[ReplayFrame] = Field(default_factory=list)


class ReplayFrame(BaseModel):
    model_config = ConfigDict(extra="forbid")
    kind: Literal["delta", "reset", "terminal"]
    sequence: int = Field(strict=True, ge=0)
    chunk_index: int | None = Field(default=None, strict=True, ge=0)
    text: str = ""


Observation.model_rebuild()


class CaptureVersions(BaseModel):
    model_config = ConfigDict(extra="forbid")
    pipeline_version: str = Field(pattern=r"^[a-zA-Z0-9_.:-]{1,100}$")
    model_config_sha256: str = Field(pattern=r"^[0-9a-f]{64}$")
    prompt_schema_sha256: str = Field(pattern=r"^[0-9a-f]{64}$")
    retrieval_config_sha256: str = Field(pattern=r"^[0-9a-f]{64}$")


def replay_matches(frames: list[ReplayFrame], presentation: AnswerPresentationV1) -> bool:
    """Повторный seq допустим только с тем же payload; reset заменяет весь текст."""
    seen: dict[int, ReplayFrame] = {}
    text, next_chunk, last_seq, terminal = "", 0, -1, False
    for frame in frames:
        if frame.sequence in seen:
            if seen[frame.sequence] != frame:
                return False
            continue
        if frame.sequence <= last_seq or terminal:
            return False
        seen[frame.sequence] = frame
        last_seq = frame.sequence
        if frame.kind == "reset":
            if frame.chunk_index is None:
                return False
            text, next_chunk = frame.text, frame.chunk_index
        elif frame.kind == "delta":
            if frame.chunk_index != next_chunk:
                return False
            text += frame.text
            next_chunk += 1
        else:
            terminal = True
    return (
        terminal
        and text == presentation.text
        and hashlib.sha256(text.encode("utf-8")).hexdigest() == presentation.text_sha256
    )


class DisabledProvider:
    async def complete_json(self, **_kwargs: Any) -> Any:
        raise InferenceUnavailable("FIXTURE_MODEL_DISABLED")


def frozen_inputs() -> tuple[dict[str, Any], list[dict[str, Any]], dict[str, str]]:
    lock = json.loads((ROOT / "eval/fixture.lock.json").read_text(encoding="utf-8"))
    for name, digest in lock.items():
        if sha(ROOT / name) != digest:
            raise ValueError("FROZEN_INPUT_DRIFT")
    manifest = json.loads((ROOT / "eval/fixtures/manifest.json").read_text(encoding="utf-8"))
    cases = [
        json.loads(line)
        for line in (ROOT / "eval/cases/dev_smoke.jsonl").read_text(encoding="utf-8").splitlines()
    ]
    if len(cases) != 10 or {c["case_id"] for c in cases} != set(
        manifest["reserved_dev_ids"]["case_ids"]
    ):
        raise ValueError("INVALID_DEV_CASE_SET")
    documents = {d["external_id"]: d for d in manifest["documents"]}
    for case in cases:
        if case["split"] != "dev":
            raise ValueError("INVALID_SPLIT")
        for span in case["expected"]["spans"]:
            doc = documents[span["source_id"]]
            section = next(s for s in doc["sections"] if s["name"] == span["section"])
            if section["text"][span["start"] : span["end"]] != span["quote"]:
                raise ValueError("INVALID_GOLD_SPAN")
    return manifest, cases, lock


async def fixture_observation(case: dict[str, Any], manifest: dict[str, Any]) -> Observation:
    """Реальный lexical fallback и Analyst fallback; gold spans не выбирают выдачу."""
    documents = [
        d for d in manifest["documents"] if case["expected"]["source_status"][d["source"]] == "ok"
    ]
    scores = lexical_scores(
        case["query"], [d["title"] + " " + d["sections"][0]["text"] for d in documents]
    )
    stopwords = set(
        "a an the of in on at and or to for from by with how what which does during "
        "synthetic fixture measures compare study is are can it".split()
    )
    terms = set(_terms(case["query"])) - stopwords
    ranked = sorted(
        (
            (d, s)
            for d, s in zip(documents, scores, strict=True)
            if terms.intersection(_terms(d["title"] + " " + d["sections"][0]["text"]))
        ),
        key=lambda p: (-p[1], p[0]["external_id"]),
    )
    items = []
    for doc, score in ranked[:10]:
        section = doc["sections"][0]
        identity = doc["external_id"]
        text = section["text"]
        items.append(
            EvidencePackItem(
                evidence_id=uid(identity + "/evidence"),
                document_id=uid(identity),
                revision_id=uid(identity + hashlib.sha256(text.encode()).hexdigest()),
                chunk_id=uid(identity + "/chunk/0"),
                source=doc["source"],
                external_id=identity,
                canonical_url=doc["canonical_url"],
                title=doc["title"],
                section=section["name"],
                language=section.get("language") or "en",
                span_start=0,
                span_end=len(text),
                quoted_span=text,
                retrieval_score=score,
                rerank_score=score,
            )
        )
    idea = IdeaV1(features=[FeatureV1(id=uid(case["case_id"]), text=case["query"])])
    coverage = CoverageV1(
        sources=[{"source": k, "status": v} for k, v in case["expected"]["source_status"].items()],
        channels=[{"channel": "lexical_fixture", "status": "ok" if items else "empty"}],
        partial=case["expected"]["coverage"] == "partial",
        historical=False,
    )
    pack = EvidencePack(items=tuple(items), token_count=0, token_budget=6000)
    # Модель намеренно отключена: fixture проверяет production fallback/renderer.
    analyst = Analyst(cast(InferenceProvider, DisabledProvider()), model_id="disabled-fixture")
    result = await analyst.analyze(
        idea=idea,
        pack=pack,
        coverage=coverage,
        request_id=case["case_id"],
        timeout=10,
    )
    return Observation(
        case_id=case["case_id"],
        status="completed",
        outcome=result.outcome,
        idea=idea,
        coverage=coverage,
        candidate_ids=[d["external_id"] for d, _ in ranked],
        evidence=[Evidence.model_validate(asdict(item)) for item in items],
        analysis=result.analysis,
        answer=result.answer,
        public_analysis=result.public_analysis,
        presentation=result.presentation,
        elapsed_ms=None,
        timing_reason="OFFLINE_REPLAY",
        replay=[
            ReplayFrame(
                kind="reset",
                sequence=0,
                text=result.presentation.text,
                chunk_index=result.presentation.chunk_count,
            ),
            ReplayFrame(kind="terminal", sequence=1),
        ],
    )


def evaluate(
    observation: Observation, case: dict[str, Any], manifest: dict[str, Any]
) -> dict[str, Any]:
    errors: set[str] = set()
    docs = {d["external_id"]: d for d in manifest["documents"]}
    items = {e.evidence_id: e for e in observation.evidence}
    if len(items) != len(observation.evidence):
        errors.add("DUPLICATE_EVIDENCE")
    if len(set(observation.candidate_ids)) != len(observation.candidate_ids):
        errors.add("DUPLICATE_CANDIDATE")
    if not set(observation.candidate_ids) <= docs.keys():
        errors.add("UNKNOWN_CANDIDATE")
    if any(
        case["expected"]["source_status"][docs[source]["source"]] != "ok"
        for source in observation.candidate_ids
        if source in docs
    ):
        errors.add("UNAVAILABLE_SOURCE_USED")
    for item in observation.evidence:
        doc = docs.get(item.external_id)
        if doc is None:
            errors.add("UNKNOWN_SOURCE")
            continue
        if (
            item.source != doc["source"]
            or item.title != doc["title"]
            or item.canonical_url != doc["canonical_url"]
        ):
            errors.add("SOURCE_METADATA_MISMATCH")
        text = next((s["text"] for s in doc["sections"] if s["name"] == item.section), "")
        revision = uid(item.external_id + hashlib.sha256(text.encode()).hexdigest())
        if (
            item.document_id != uid(item.external_id)
            or item.revision_id != revision
            or item.chunk_id != uid(item.external_id + "/chunk/0")
        ):
            errors.add("SOURCE_REVISION_MISMATCH")
        if (
            item.span_end <= item.span_start
            or item.span_end > len(text)
            or text[item.span_start : item.span_end] != item.quoted_span
        ):
            errors.add("EVIDENCE_SPAN_MISMATCH")
        if case["expected"]["source_status"][doc["source"]] != "ok":
            errors.add("UNAVAILABLE_SOURCE_USED")
    pack = EvidencePack(
        tuple(EvidencePackItem(**e.model_dump()) for e in observation.evidence), 0, 6000
    )
    if observation.analysis is not None:
        try:
            validate_analysis(observation.analysis, idea=observation.idea, pack=pack)
        except AnalystViolation:
            errors.add("INVALID_ANALYSIS_GROUNDING")
    answer = observation.answer
    claim_count = valid_count = 0
    if observation.status != "completed":
        errors.add("UNEXPECTED_TERMINAL_STATUS")
        if any(
            (answer, observation.analysis, observation.public_analysis, observation.presentation)
        ):
            errors.add("NONTERMINAL_RESULT_LEAK")
        if observation.outcome is not None:
            errors.add("INVALID_TERMINAL_OUTCOME")
    elif not all((answer, observation.public_analysis, observation.presentation)):
        errors.add("MISSING_RESULT")
    elif answer is not None:
        assert observation.public_analysis is not None and observation.presentation is not None
        if not replay_matches(observation.replay, observation.presentation):
            errors.add("REPLAY_MISMATCH")
        try:
            validate_projections(answer, observation.public_analysis, observation.presentation)
        except (ValueError, ValidationError):
            errors.add("PUBLIC_PROJECTION_MISMATCH")
        claims = (
            answer.summary
            + [c for m in answer.matches for c in m.claims]
            + [c for d in answer.differences for c in d.claims]
        )
        for claim in claims:
            claim_count += len(claim.quotes)
            valid = set(claim.evidence_ids) == {q.evidence_id for q in claim.quotes}
            for quote in claim.quotes:
                cited_item = items.get(quote.evidence_id)
                if cited_item is None:
                    errors.add("PHANTOM_CITATION")
                    valid = False
                elif (
                    quote.start < cited_item.span_start
                    or quote.end > cited_item.span_end
                    or cited_item.quoted_span[
                        quote.start - cited_item.span_start : quote.end - cited_item.span_start
                    ]
                    != quote.text
                ):
                    errors.add("FABRICATED_QUOTE")
                    valid = False
                else:
                    valid_count += 1
            if not valid:
                errors.add("INVALID_CITATION")
        codes = {notice.code for notice in answer.limitations}
        if not {"selected_evidence_only", "no_legal_novelty"} <= codes:
            errors.add("MISSING_CONCLUSION_CONSTRAINT")
        if observation.coverage.partial != (case["expected"]["coverage"] == "partial"):
            errors.add("COVERAGE_MISMATCH")
        if observation.coverage.partial and "partial_coverage" not in codes:
            errors.add("MISSING_PARTIAL_NOTICE")
        if observation.outcome == "safe_fallback":
            if (
                observation.analysis is not None
                or answer.matches
                or answer.differences
                or "safe_fallback" not in codes
            ):
                errors.add("INVALID_FALLBACK")
            if any(not c.text.startswith("Фрагмент выбранного источника") for c in claims):
                errors.add("UNSUPPORTED_FALLBACK_CLAIM")
            from app.services.analyst import _render_fallback

            if (answer, observation.public_analysis, observation.presentation) != _render_fallback(
                observation.idea, pack, observation.coverage
            ):
                errors.add("INVALID_FALLBACK_PROJECTION")
        elif observation.outcome == "no_evidence":
            if claims or observation.evidence or observation.analysis is not None:
                errors.add("INVALID_NO_EVIDENCE")
        elif observation.outcome == "analysis":
            if observation.analysis is None:
                errors.add("MISSING_ANALYSIS")
            else:
                from app.services.analyst import _render_analysis

                try:
                    expected = _render_analysis(
                        observation.analysis, observation.idea, observation.coverage
                    )
                    if (answer, observation.public_analysis, observation.presentation) != expected:
                        errors.add("ANSWER_ANALYSIS_MISMATCH")
                except (ValueError, KeyError):
                    errors.add("ANSWER_ANALYSIS_MISMATCH")
        elif observation.outcome != "clarification":
            errors.add("INVALID_COMPLETED_OUTCOME")
        elif claims or observation.analysis is not None:
            errors.add("INVALID_CLARIFICATION")
    if case["expected"]["coverage"] == "no_evidence" and observation.outcome != "no_evidence":
        errors.add("EXPECTED_NO_EVIDENCE")
    expected_ids = set(case["expected"]["expected_source_ids"])
    retrieved = observation.candidate_ids[:10]
    recall = len(expected_ids.intersection(retrieved)) / len(expected_ids) if expected_ids else None
    rank = next((i for i, source in enumerate(retrieved, 1) if source in expected_ids), None)
    return {
        "case_id": case["case_id"],
        "status": observation.status,
        "outcome": observation.outcome,
        "errors": sorted(errors),
        "passed": not errors,
        "recall_at_10": recall,
        "reciprocal_rank": (1 / rank if rank else 0.0) if expected_ids else None,
        "citation_validity": valid_count / claim_count if claim_count else None,
        "citation_denominator": claim_count,
        "elapsed_ms": observation.elapsed_ms,
        "timing_reason": observation.timing_reason,
        "judge": None,
        "judge_status": "DISABLED",
    }
