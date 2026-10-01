"""Adversarial checks for AnalysisV1 validation and deterministic projections."""

import asyncio
from uuid import uuid4

import pytest
from pydantic import ValidationError

from app.domain.contracts import AnalysisV1, CoverageV1
from app.domain.inference import InferenceCancelled, InferenceMetadata, InferenceTimeout, JsonResult
from app.domain.planner import FeatureV1, IdeaV1
from app.services.analyst import Analyst, AnalystViolation, validate_analysis
from app.services.evidence_pack import EvidencePack, EvidencePackItem

FEATURE, DOCUMENT, REVISION, CHUNK, EVIDENCE = (uuid4() for _ in range(5))
IDEA = IdeaV1(features=[FeatureV1(id=FEATURE, text="распознавание 📷")])
TEXT = "Прибор распознаёт изображение 📷 точно."
START = 14
QUOTE = "изображение 📷"
QUOTE_START = START + TEXT.index(QUOTE)
PACK = EvidencePack(
    items=(
        EvidencePackItem(
            evidence_id=EVIDENCE,
            document_id=DOCUMENT,
            revision_id=REVISION,
            chunk_id=CHUNK,
            source="fixture",
            external_id="doc-1",
            canonical_url="https://example.invalid/doc-1",
            title="Документ",
            section="Описание",
            language="ru",
            span_start=START,
            span_end=START + len(TEXT),
            quoted_span=TEXT,
            retrieval_score=0.8,
            rerank_score=0.9,
        ),
    ),
    token_count=10,
    token_budget=6000,
)
COVERAGE = CoverageV1(sources=[], channels=[], partial=False, historical=False)


def draft(**changes):  # type: ignore[no-untyped-def]
    value = {
        "schema_version": 1,
        "relations": [
            {
                "feature_id": str(FEATURE),
                "document_id": str(DOCUMENT),
                "relation": "partial",
                "evidence_ids": [str(EVIDENCE)],
                "quotes": [
                    {
                        "evidence_id": str(EVIDENCE),
                        "start": QUOTE_START,
                        "end": QUOTE_START + len(QUOTE),
                        "text": QUOTE,
                    }
                ],
            }
        ],
        "unresolved_feature_ids": [],
    }
    return {**value, **changes}


def model_draft():
    value = draft()
    value["relations"][0]["quotes"] = [
        {"evidence_id": str(EVIDENCE), "text": QUOTE}
    ]
    return value


def test_exact_unicode_quote_and_deterministic_claim_projections() -> None:
    from app.services.analyst import _render_analysis

    analysis = AnalysisV1.model_validate(draft())
    validate_analysis(analysis, idea=IDEA, pack=PACK)
    answer, public, presentation = _render_analysis(analysis, IDEA, COVERAGE)
    assert answer.matches[0].claims[0] == answer.summary[0] == public.items[0]
    assert "изображение 📷" in answer.summary[0].text
    assert answer.summary[0].text.startswith("В выбранном фрагменте")
    assert presentation.text_sha256
    assert "https://" not in presentation.text


def test_quote_offsets_are_enriched_from_exact_evidence_text() -> None:
    from app.domain.contracts import AnalysisDraftV1
    from app.services.analyst import enrich_analysis_draft

    semantic_draft = AnalysisDraftV1.model_validate(model_draft())
    result = enrich_analysis_draft(semantic_draft, PACK)
    quote = result.relations[0].quotes[0]
    assert (quote.start, quote.end) == (QUOTE_START, QUOTE_START + len(QUOTE))
    assert TEXT[quote.start - START : quote.end - START] == QUOTE


def test_analyst_model_schema_excludes_mechanical_quote_offsets() -> None:
    provider = FakeProvider([model_draft()])
    result = run(provider)
    assert result.outcome == "analysis"
    assert '"start"' not in str(provider.schemas[0])
    assert '"end"' not in str(provider.schemas[0])


def test_missing_exact_quote_is_rejected_before_analysis_validation() -> None:
    from app.domain.contracts import AnalysisDraftV1
    from app.services.analyst import enrich_analysis_draft

    value = model_draft()
    value["relations"][0]["quotes"][0]["text"] = "invented quote"
    with pytest.raises(AnalystViolation, match="QUOTE_TEXT_MISMATCH"):
        enrich_analysis_draft(AnalysisDraftV1.model_validate(value), PACK)


@pytest.mark.parametrize(
    ("changes", "code"),
    [
        (
            {
                "relations": [{**draft()["relations"][0], "feature_id": str(uuid4())}],
                "unresolved_feature_ids": [str(FEATURE)],
            },
            "UNKNOWN_FEATURE_ID",
        ),
        (
            {
                "relations": [{**draft()["relations"][0], "document_id": str(uuid4())}],
                "unresolved_feature_ids": [str(FEATURE)],
            },
            "UNKNOWN_DOCUMENT_ID",
        ),
        (
            {
                "relations": [
                    {
                        **draft()["relations"][0],
                        "evidence_ids": [str(uuid4())],
                        "quotes": [
                            {"evidence_id": "replace-me", "start": 0, "end": 1, "text": "x"}
                        ],
                    }
                ],
                "unresolved_feature_ids": [str(FEATURE)],
            },
            "UNKNOWN_EVIDENCE_ID",
        ),
        ({"unresolved_feature_ids": [str(FEATURE)]}, "UNRESOLVED_FEATURE_SET_MISMATCH"),
        (
            {
                "relations": [
                    {
                        **draft()["relations"][0],
                        "quotes": [
                            {
                                "evidence_id": str(EVIDENCE),
                                "start": QUOTE_START,
                                "end": QUOTE_START + len(QUOTE),
                                "text": "подмена",
                            }
                        ],
                    }
                ]
            },
            "QUOTE_TEXT_MISMATCH",
        ),
        (
            {
                "relations": [
                    {
                        **draft()["relations"][0],
                        "quotes": [
                            {
                                "evidence_id": str(EVIDENCE),
                                "start": START - 1,
                                "end": START + 1,
                                "text": "xП",
                            }
                        ],
                    }
                ]
            },
            "QUOTE_OFFSET_OUT_OF_RANGE",
        ),
        (
            {
                "relations": [
                    {
                        **draft()["relations"][0],
                        "quotes": [
                            {
                                "evidence_id": str(EVIDENCE),
                                "start": QUOTE_START,
                                "end": QUOTE_START + len(QUOTE),
                                "text": QUOTE,
                            }
                        ],
                        "injected": "ignore rules",
                    }
                ]
            },
            "schema",
        ),
    ],
)
def test_rejects_membership_quote_and_extra_field_mismatches(changes, code) -> None:  # type: ignore[no-untyped-def]
    if code == "UNKNOWN_EVIDENCE_ID":
        evidence_id = changes["relations"][0]["evidence_ids"][0]
        changes["relations"][0]["quotes"][0]["evidence_id"] = evidence_id
    value = draft(**changes)
    if code == "schema":
        with pytest.raises(ValidationError):
            AnalysisV1.model_validate(value)
        return
    analysis = AnalysisV1.model_validate(value)
    with pytest.raises(AnalystViolation, match=code):
        validate_analysis(analysis, idea=IDEA, pack=PACK)


def test_conflicting_and_uncertain_relations_remain_unresolved() -> None:
    for kind in ("conflicting", "uncertain"):
        value = draft(
            relations=[{**draft()["relations"][0], "relation": kind}],
            unresolved_feature_ids=[str(FEATURE)],
        )
        validate_analysis(AnalysisV1.model_validate(value), idea=IDEA, pack=PACK)


def test_absent_feature_is_only_a_gap_in_the_selected_pack() -> None:
    second_id = uuid4()
    idea = IdeaV1(features=[*IDEA.features, FeatureV1(id=second_id, text="offline processing")])
    value = draft(unresolved_feature_ids=[str(second_id)])
    analysis = AnalysisV1.model_validate(value)
    validate_analysis(analysis, idea=idea, pack=PACK)
    from app.services.analyst import _render_analysis

    answer, _, _ = _render_analysis(analysis, idea, COVERAGE)
    notice = next(item for item in answer.limitations if item.code == "unresolved_in_selected_pack")
    assert "выбранными фрагментами" in notice.message
    assert "полном корпусе" in notice.message


def test_structurally_valid_quote_does_not_establish_semantic_faithfulness() -> None:
    # The validator can verify provenance and offsets, but not entailment of the label.
    unrelated_id = uuid4()
    idea = IdeaV1(features=[FeatureV1(id=unrelated_id, text="underwater wireless charging")])
    relation = {**draft()["relations"][0], "feature_id": str(unrelated_id), "relation": "full"}
    value = draft(relations=[relation])
    validate_analysis(AnalysisV1.model_validate(value), idea=idea, pack=PACK)


def test_evidence_from_another_known_document_is_rejected() -> None:
    second_doc, second_revision, second_chunk = uuid4(), uuid4(), uuid4()
    second_item = EvidencePackItem(
        evidence_id=uuid4(),
        document_id=second_doc,
        revision_id=second_revision,
        chunk_id=second_chunk,
        source="fixture",
        external_id="doc-2",
        canonical_url="https://example.invalid/doc-2",
        title="Документ 2",
        section="Описание",
        language="ru",
        span_start=START,
        span_end=START + len(TEXT),
        quoted_span=TEXT,
        retrieval_score=0.7,
        rerank_score=0.8,
    )
    pack = EvidencePack(items=(*PACK.items, second_item), token_count=20, token_budget=6000)
    value = draft(relations=[{**draft()["relations"][0], "document_id": str(second_doc)}])
    with pytest.raises(AnalystViolation, match="EVIDENCE_DOCUMENT_MISMATCH"):
        validate_analysis(AnalysisV1.model_validate(value), idea=IDEA, pack=pack)


class FakeProvider:
    def __init__(self, outputs):  # type: ignore[no-untyped-def]
        self.outputs = outputs
        self.prompts = []
        self.schemas = []

    async def complete_json(self, **kwargs):  # type: ignore[no-untyped-def]
        self.prompts.append(kwargs["prompt"])
        self.schemas.append(kwargs["schema"])
        value = self.outputs.pop(0)
        if isinstance(value, Exception):
            raise value
        return JsonResult(
            value=value,
            metadata=InferenceMetadata(
                provider="fake",
                model_id="gemma",
                model_revision="test",
                finish_reason="stop",
                model_ttft_ms=None,
                model_ttft_reason="fixture",
                reasoning_duration_ms=None,
                reasoning_duration_reason="fixture",
                reasoning_tokens=None,
                reasoning_tokens_reason="fixture",
                output_duration_ms=None,
                output_duration_reason="fixture",
                output_tokens=None,
                output_tokens_reason="fixture",
                total_ms=1,
                load_ms=None,
                load_reason="fixture",
            ),
        )


def run(provider, *, cancel=None):  # type: ignore[no-untyped-def]
    return asyncio.run(
        Analyst(
            provider, model_id="gemma", prompt="schema={schema_json}\ninput={input_json}"
        ).analyze(
            idea=IDEA,
            pack=PACK,
            coverage=COVERAGE,
            request_id="test",
            timeout=2,
            cancel=cancel,
        )
    )


def test_invalid_draft_gets_one_repair_without_raw_thinking() -> None:
    provider = FakeProvider([{"schema_version": 1, "private": "DRAFT"}, model_draft()])
    result = run(provider)
    assert result.outcome == "analysis" and result.attempts == 2
    assert len(provider.prompts) == 2
    assert "rejected_draft" in provider.prompts[1]
    assert "PRIVATE_REASONING" not in provider.prompts[1]
    assert "DRAFT" in provider.prompts[1]


def test_failed_repair_fallback_ignores_model_relations() -> None:
    provider = FakeProvider([model_draft() | {"relations": []}, {"schema_version": 1, "bad": True}])
    result = run(provider)
    assert result.outcome == "safe_fallback" and result.analysis is None
    assert result.answer.matches == result.answer.differences == []
    assert result.public_analysis.items == result.answer.summary
    assert result.answer.summary[0].text.startswith("Фрагмент выбранного источника")
    assert result.answer.limitations[0].code == "safe_fallback"


def test_timeout_falls_back_without_repair_and_cancel_propagates() -> None:
    provider = FakeProvider([InferenceTimeout("private backend detail")])
    result = run(provider)
    assert result.outcome == "safe_fallback" and len(provider.prompts) == 1
    cancel = asyncio.Event()
    cancel.set()
    with pytest.raises(InferenceCancelled):
        run(FakeProvider([model_draft()]), cancel=cancel)


def test_empty_pack_returns_no_evidence_without_inference() -> None:
    provider = FakeProvider([])
    empty = EvidencePack(items=(), token_count=1, token_budget=6000)
    result = asyncio.run(
        Analyst(provider, model_id="gemma", prompt="").analyze(
            idea=IDEA,
            pack=empty,
            coverage=COVERAGE,
            request_id="test",
            timeout=2,
        )
    )
    assert result.outcome == "no_evidence" and result.answer.summary == []
    assert not provider.prompts
