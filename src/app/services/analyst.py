"""Validated AnalysisV1 inference and deterministic answer projections."""

from __future__ import annotations

import asyncio
import hashlib
import json
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Any
from uuid import UUID

from pydantic import ValidationError

from app.domain.contracts import (
    AnalysisV1,
    AnswerPresentationV1,
    AnswerV1,
    ClaimV1,
    CoverageV1,
    DifferenceV1,
    LimitationV1,
    MatchV1,
    PublicAnalysisV1,
    QuoteV1,
)
from app.domain.inference import (
    InferenceCancelled,
    InferenceConfigurationError,
    InferenceError,
    InferenceMetadata,
    InferenceProtocolError,
    InferenceProvider,
    ReasoningEffort,
)
from app.domain.planner import IdeaV1
from app.services.evidence_pack import EvidencePack, EvidencePackItem, render_evidence_items

PROMPT_VERSION = "analyst_v1"
RENDERER_VERSION = "answer_v1.1"
MAX_JSON_BYTES = 256 * 1024
MAX_PRESENTATION_CHUNK = 1024


class AnalystViolation(ValueError):
    """Safe diagnostic code for a draft that failed contextual validation."""


@dataclass(frozen=True)
class AnalystResult:
    outcome: str
    analysis: AnalysisV1 | None
    answer: AnswerV1
    public_analysis: PublicAnalysisV1
    presentation: AnswerPresentationV1
    attempts: int
    diagnostic_codes: tuple[str, ...] = ()
    metadata: InferenceMetadata | None = None


def _schema_error_codes(exc: ValidationError) -> tuple[str, ...]:
    codes = []
    for error in exc.errors(include_input=False, include_context=False, include_url=False)[:8]:
        parts = [str(part) if isinstance(part, int) else "field" for part in error["loc"]]
        codes.append(f"INVALID_SCHEMA:{error['type']}:{'.'.join(parts)}")
    return tuple(codes or ("INVALID_SCHEMA",))


def validate_analysis(analysis: AnalysisV1, *, idea: IdeaV1, pack: EvidencePack) -> None:
    features = {feature.id for feature in idea.features}
    items = {item.evidence_id: item for item in pack.items}
    documents = {item.document_id for item in pack.items}
    if len(items) != len(pack.items):
        raise AnalystViolation("DUPLICATE_PACK_EVIDENCE_ID")
    if not {relation.feature_id for relation in analysis.relations} <= features:
        raise AnalystViolation("UNKNOWN_FEATURE_ID")
    if not {relation.document_id for relation in analysis.relations} <= documents:
        raise AnalystViolation("UNKNOWN_DOCUMENT_ID")
    supported: set[UUID] = set()
    for relation in analysis.relations:
        relation_items = [items.get(evidence_id) for evidence_id in relation.evidence_ids]
        if any(item is None for item in relation_items):
            raise AnalystViolation("UNKNOWN_EVIDENCE_ID")
        if any(item.document_id != relation.document_id for item in relation_items if item):
            raise AnalystViolation("EVIDENCE_DOCUMENT_MISMATCH")
        quotes_by_evidence: dict[UUID, list[QuoteV1]] = {}
        for quote in relation.quotes:
            quotes_by_evidence.setdefault(quote.evidence_id, []).append(quote)
        if set(relation.evidence_ids) != set(quotes_by_evidence):
            raise AnalystViolation("EVIDENCE_QUOTE_COVERAGE_MISMATCH")
        for evidence_id, quotes in quotes_by_evidence.items():
            item = items[evidence_id]
            if item.document_id != relation.document_id:
                raise AnalystViolation("QUOTE_DOCUMENT_MISMATCH")
            for quote in quotes:
                start = quote.start - item.span_start
                end = quote.end - item.span_start
                if start < 0 or end > len(item.quoted_span) or end <= start:
                    raise AnalystViolation("QUOTE_OFFSET_OUT_OF_RANGE")
                if item.quoted_span[start:end] != quote.text:
                    raise AnalystViolation("QUOTE_TEXT_MISMATCH")
        if relation.relation in ("full", "partial"):
            supported.add(relation.feature_id)
    expected_unresolved = features - supported
    if set(analysis.unresolved_feature_ids) != expected_unresolved:
        raise AnalystViolation("UNRESOLVED_FEATURE_SET_MISMATCH")


def _notice(code: str, message: str) -> LimitationV1:
    return LimitationV1(code=code, message=message)


def _coverage_limitations(coverage: CoverageV1) -> list[LimitationV1]:
    notices = [
        _notice(
            "selected_evidence_only",
            "Сопоставление ограничено выбранными фрагментами; отсутствие совпадения не доказывает "
            "отсутствие признака в документе.",
        ),
        _notice(
            "no_legal_novelty",
            "Сопоставление не является оценкой юридической новизны или патентоспособности.",
        ),
    ]
    if coverage.partial:
        notices.append(
            _notice(
                "partial_coverage",
                "Часть источников или каналов поиска была недоступна; результаты охватывают "
                "неполную выдачу.",
            )
        )
    if coverage.historical:
        notices.append(
            _notice(
                "historical_snapshot", "Использован сохранённый исторический снимок источников."
            )
        )
    return notices


def _make_claim(feature_text: str, relation: str, quotes: list[QuoteV1]) -> ClaimV1:
    wording = {
        "full": "В выбранном фрагменте найдено полное сопоставление признака",
        "partial": "В выбранном фрагменте найдено частичное сопоставление признака",
        "conflicting": "В выбранном фрагменте отмечено противоречие по признаку",
        "uncertain": "Сопоставление признака в выбранном фрагменте остаётся неопределённым",
        "fallback": "Фрагмент выбранного источника для проверки признака",
    }[relation]
    text = f"{wording} «{feature_text}». Цитата: «{quotes[0].text}»"
    ids = list(dict.fromkeys(quote.evidence_id for quote in quotes))
    return ClaimV1(text=text, evidence_ids=ids, quotes=quotes)


def _render_analysis(
    analysis: AnalysisV1, idea: IdeaV1, coverage: CoverageV1
) -> tuple[AnswerV1, PublicAnalysisV1, AnswerPresentationV1]:
    labels = {feature.id: feature.text for feature in idea.features}
    items_by_id: dict[UUID, EvidencePackItem] = {}
    # Evidence metadata is only used to group verified relation outputs.
    del items_by_id
    matches: list[MatchV1] = []
    differences: list[DifferenceV1] = []
    rendered_claims: list[ClaimV1] = []
    for relation in analysis.relations:
        claim = _make_claim(labels[relation.feature_id], relation.relation, relation.quotes)
        rendered_claims.append(claim)
        if relation.relation in ("full", "partial"):
            matches.append(
                MatchV1(
                    feature_id=relation.feature_id, document_id=relation.document_id, claims=[claim]
                )
            )
        else:
            differences.append(DifferenceV1(feature_id=relation.feature_id, claims=[claim]))
    limitations = _coverage_limitations(coverage)
    if analysis.unresolved_feature_ids:
        limitations.append(
            _notice(
                "unresolved_in_selected_pack",
                f"Для {len(analysis.unresolved_feature_ids)} признаков сопоставление не "
                "подтверждено выбранными фрагментами; это не означает отсутствия признаков "
                "в полном корпусе.",
            )
        )
    if any(
        relation.relation in ("partial", "conflicting", "uncertain")
        for relation in analysis.relations
    ):
        limitations.append(
            _notice(
                "uncertain_relations",
                "Часть сопоставлений является частичной, противоречивой или неопределённой.",
            )
        )
    answer = AnswerV1(
        summary=rendered_claims[:12],
        matches=matches,
        differences=differences,
        limitations=limitations,
        followup_suggestions=["Проверить полные разделы документов по отмеченным признакам."]
        if analysis.unresolved_feature_ids
        else [],
    )
    public = PublicAnalysisV1(items=rendered_claims[:12], limitations=limitations)
    presentation = _presentation(answer)
    validate_projections(answer, public, presentation)
    return answer, public, presentation


def _render_fallback(
    idea: IdeaV1, pack: EvidencePack, coverage: CoverageV1
) -> tuple[AnswerV1, PublicAnalysisV1, AnswerPresentationV1]:
    claims: list[ClaimV1] = []
    for item in pack.items[:12]:
        quote = QuoteV1(
            evidence_id=item.evidence_id,
            start=item.span_start,
            end=item.span_end,
            text=item.quoted_span,
        )
        label = (
            idea.features[min(len(claims), len(idea.features) - 1)].text
            if idea.features
            else item.title
        )
        claims.append(_make_claim(label, "fallback", [quote]))
    limitations = [
        _notice(
            "safe_fallback",
            "Автоматическое сопоставление не прошло проверку; ниже приведены только точные "
            "выдержки без выводов модели.",
        ),
        *_coverage_limitations(coverage),
    ]
    answer = AnswerV1(
        summary=claims[:3],
        matches=[],
        differences=[],
        limitations=limitations,
        followup_suggestions=[],
    )
    public = PublicAnalysisV1(items=claims[:3], limitations=limitations)
    presentation = _presentation(answer)
    validate_projections(answer, public, presentation)
    return answer, public, presentation


def _presentation(answer: AnswerV1) -> AnswerPresentationV1:
    lines = ["Результат сопоставления"]
    lines.extend(claim.text for claim in answer.summary)
    lines.extend(f"Ограничение: {item.message}" for item in answer.limitations)
    lines.extend(f"Дальше: {suggestion}" for suggestion in answer.followup_suggestions)
    text = "\n".join(lines)
    if not text:
        text = "Нет результатов для отображения."
    chunks = [
        text[i : i + MAX_PRESENTATION_CHUNK] for i in range(0, len(text), MAX_PRESENTATION_CHUNK)
    ]
    if len(chunks) > 128 or len(text.encode("utf-8")) > 65536:
        raise ValueError("PRESENTATION_LIMIT_EXCEEDED")
    digest = hashlib.sha256(text.encode("utf-8")).hexdigest()
    presentation_id = hashlib.sha256((RENDERER_VERSION + text).encode("utf-8")).hexdigest()
    return AnswerPresentationV1(
        presentation_id=presentation_id,
        renderer_version=RENDERER_VERSION,
        text=text,
        text_sha256=digest,
        chunk_count=len(chunks),
    )


def validate_projections(
    answer: AnswerV1, public: PublicAnalysisV1, presentation: AnswerPresentationV1
) -> None:
    all_claims = [claim for match in answer.matches for claim in match.claims] + [
        claim for diff in answer.differences for claim in diff.claims
    ]
    is_fallback = any(item.code == "safe_fallback" for item in answer.limitations)
    if any(claim not in all_claims for claim in answer.summary) and not is_fallback:
        raise AnalystViolation("SUMMARY_NOT_SUBSET_OF_CLAIMS")
    if any(claim not in answer.summary for claim in public.items):
        raise AnalystViolation("PUBLIC_ITEMS_NOT_SUBSET_OF_SUMMARY")
    if any(item not in answer.limitations for item in public.limitations):
        raise AnalystViolation("PUBLIC_LIMITATIONS_NOT_SUBSET_OF_ANSWER")
    expected = _presentation(answer)
    if presentation != expected:
        raise AnalystViolation("PRESENTATION_PROJECTION_MISMATCH")


def _jsonable(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False, separators=(",", ":"), default=str)


class Analyst:
    def __init__(
        self, provider: InferenceProvider, *, model_id: str, prompt: str | None = None
    ) -> None:
        self.provider = provider
        self.model_id = model_id
        self.prompt = (
            prompt
            if prompt is not None
            else Path("prompts/analyst_v1.txt").read_text(encoding="utf-8")
        )

    async def analyze(
        self,
        *,
        idea: IdeaV1,
        pack: EvidencePack,
        coverage: CoverageV1,
        request_id: str,
        timeout: float,
        max_output_tokens: int = 2048,
        reasoning_effort: ReasoningEffort = "low",
        cancel: asyncio.Event | None = None,
    ) -> AnalystResult:
        if timeout <= 0 or not 1 <= max_output_tokens <= 2048:
            raise ValueError("INVALID_ANALYST_LIMIT")
        if not idea.features:
            return self._empty("clarification", 0, coverage)
        if not pack.items:
            return self._empty("no_evidence", 0, coverage)
        input_value = {
            "idea": idea.model_dump(mode="json"),
            "coverage": coverage.model_dump(mode="json"),
            "evidence_pack": json.loads(render_evidence_items(pack.items)),
        }
        original = self.prompt.replace(
            "{schema_json}", _jsonable(AnalysisV1.model_json_schema())
        ).replace("{input_json}", _jsonable(input_value))
        prompt = original
        deadline = time.monotonic() + timeout
        codes: list[str] = []
        metadata = None
        rejected: Any = None
        for attempt in (1, 2):
            if cancel is not None and cancel.is_set():
                raise InferenceCancelled("analyst cancelled")
            remaining = deadline - time.monotonic()
            if remaining <= 0:
                return self._fallback(idea, pack, coverage, attempt - 1, (*codes, "DEADLINE"))
            try:
                result = await self.provider.complete_json(
                    model_id=self.model_id,
                    prompt_version=PROMPT_VERSION,
                    request_id=request_id,
                    prompt=prompt,
                    timeout=remaining,
                    schema=AnalysisV1.model_json_schema(),
                    max_output_tokens=max_output_tokens,
                    reasoning_effort=reasoning_effort,
                    cancel=cancel,
                )
                metadata = result.metadata
                rejected = result.value
                encoded = _jsonable(rejected).encode("utf-8")
                if len(encoded) > MAX_JSON_BYTES:
                    rejected = {"omitted": "DRAFT_TOO_LARGE"}
                    raise AnalystViolation("DRAFT_TOO_LARGE")
                analysis = AnalysisV1.model_validate_json(encoded)
                validate_analysis(analysis, idea=idea, pack=pack)
                answer, public, presentation = _render_analysis(analysis, idea, coverage)
                return AnalystResult(
                    "analysis",
                    analysis,
                    answer,
                    public,
                    presentation,
                    attempt,
                    tuple(codes),
                    metadata,
                )
            except InferenceCancelled:
                raise
            except InferenceConfigurationError:
                raise
            except InferenceProtocolError:
                codes.append("INVALID_PROVIDER_JSON")
            except InferenceError:
                return self._fallback(
                    idea, pack, coverage, attempt - 1, (*codes, "INFERENCE_ERROR")
                )
            except ValidationError as exc:
                codes.extend(_schema_error_codes(exc))
            except AnalystViolation as exc:
                codes.append(str(exc))
            if attempt == 1:
                prompt = (
                    original
                    + "\n\nREPAIR_JSON:\n"
                    + _jsonable({"rejected_draft": rejected, "violation_codes": codes})
                )
        return self._fallback(idea, pack, coverage, 2, tuple(codes), metadata)

    def _fallback(
        self,
        idea: IdeaV1,
        pack: EvidencePack,
        coverage: CoverageV1,
        attempts: int,
        codes: tuple[str, ...],
        metadata: InferenceMetadata | None = None,
    ) -> AnalystResult:
        answer, public, presentation = _render_fallback(idea, pack, coverage)
        return AnalystResult(
            "safe_fallback", None, answer, public, presentation, attempts, codes, metadata
        )

    def _empty(self, outcome: str, attempts: int, coverage: CoverageV1) -> AnalystResult:
        answer = AnswerV1(
            summary=[],
            matches=[],
            differences=[],
            limitations=_coverage_limitations(coverage),
            followup_suggestions=[],
        )
        public = PublicAnalysisV1(items=[], limitations=answer.limitations)
        presentation = _presentation(answer)
        validate_projections(answer, public, presentation)
        return AnalystResult(outcome, None, answer, public, presentation, attempts)
