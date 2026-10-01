"""Проверки planner на подменах ID, повреждённых ответах и изменениях контекста."""

import asyncio
import json
from pathlib import Path
from uuid import uuid4

import httpx
import pytest
from pydantic import ValidationError

from app.domain.inference import InferenceCancelled
from app.domain.planner import (
    EvidenceSource,
    FeatureV1,
    IdeaV1,
    IntentPlanner,
    PlannerContext,
    PlannerV1,
    PlannerViolation,
    RetrievalKey,
    apply_patch,
    normalize_plan,
    requires_retrieval,
    state_hash,
    validate_plan,
)
from app.integrations.inference_http import OllamaProvider
from app.workers.inference import GenerationGate

OCR, CAMERA, EVIDENCE = uuid4(), uuid4(), uuid4()
IDEA = IdeaV1(
    features=[
        FeatureV1(id=OCR, text="OCR", normalized_term="ocr"),
        FeatureV1(id=CAMERA, text="Камера 📷"),
    ]
)
CONTEXT = PlannerContext(IDEA, 2, uuid4(), (EVIDENCE,))
PROMPT = Path("prompts/planner_v1.txt").read_text(encoding="utf-8")


def payload(**changes):  # type: ignore[no-untyped-def]
    return {
        "schema_version": 1,
        "intent": "modify_idea",
        "base_idea_version": 2,
        "add_features": [],
        "remove_feature_ids": [],
        "replace_features": [{"feature_id": str(OCR), "text": "barcode", "rationale": "запрос"}],
        "focus_evidence_ids": [],
        "suggested_retrieval": False,
        "confidence": 0.9,
        **changes,
    }


def model_payload(**changes):  # type: ignore[no-untyped-def]
    return {
        "intent": "modify_idea",
        "add_features": [],
        "remove_features": [],
        "replace_features": [
            {"feature_text": "OCR", "text": "barcode", "rationale": "explicit replacement"}
        ],
        "focus_source_ordinals": [],
        "suggested_retrieval": False,
        "confidence": 0.9,
        **changes,
    }


def parsed(**changes):  # type: ignore[no-untyped-def]
    return PlannerV1.model_validate_json(json.dumps(payload(**changes)))


def test_ocr_to_barcode_keeps_id_and_untouched_feature() -> None:
    changed = apply_patch(parsed(), CONTEXT)
    assert changed is not None
    assert changed.features[0].id == OCR and changed.features[0].text == "barcode"
    assert changed.features[0].normalized_term is None
    assert changed.features[1] == IDEA.features[1]
    assert IDEA.features[0].text == "OCR"
    assert state_hash(changed) != state_hash(IDEA)


def test_add_remove_and_fresh_ids() -> None:
    plan = parsed(
        remove_feature_ids=[str(OCR)],
        replace_features=[],
        add_features=[{"text": "barcode", "rationale": "запрос"}],
    )
    changed = apply_patch(plan, CONTEXT)
    repeated = apply_patch(plan, CONTEXT)
    assert changed is not None and repeated is not None
    assert changed.features[0].id == CAMERA
    assert changed.features[1].id not in (OCR, CAMERA, repeated.features[1].id)


def test_state_hash_ignores_ids_and_order_but_tracks_semantics() -> None:
    same = IdeaV1(
        features=[
            FeatureV1(id=uuid4(), text="Камера 📷"),
            FeatureV1(id=uuid4(), text="OCR", normalized_term="ocr"),
        ]
    )
    assert state_hash(same) == state_hash(IDEA)
    assert state_hash(IdeaV1(features=same.features, constraints=["Offline"])) != state_hash(IDEA)
    unicode_a = IdeaV1(features=[FeatureV1(id=uuid4(), text="café  OCR")])
    unicode_b = IdeaV1(features=[FeatureV1(id=uuid4(), text="cafe\u0301 OCR")])
    assert state_hash(unicode_a) == state_hash(unicode_b)


@pytest.mark.parametrize(
    "changes",
    [
        {"extra": "ignored?"},
        {"schema_version": True},
        {"schema_version": 1.0},
        {"base_idea_version": "2"},
        {"base_idea_version": True},
        {"suggested_retrieval": "false"},
        {"confidence": 1.1},
        {"confidence": float("nan")},
        {"replace_features": [{"feature_id": str(OCR), "text": "  ", "rationale": "x"}]},
        {"remove_feature_ids": [str(OCR)]},
        {"remove_feature_ids": [str(CAMERA), str(CAMERA)]},
        {"intent": "explain_evidence"},
        {"intent": "clarify"},
        {"replace_features": [], "add_features": []},
        {"replace_features": [{"feature_id": "fake", "text": "x", "rationale": "x"}]},
    ],
)
def test_strict_schema_rejects_invalid_payload(changes) -> None:  # type: ignore[no-untyped-def]
    with pytest.raises(ValidationError):
        parsed(**changes)


@pytest.mark.parametrize(
    ("changes", "code"),
    [
        ({"base_idea_version": 1}, "IDEA_VERSION_CONFLICT"),
        ({"remove_feature_ids": [str(uuid4())]}, "UNKNOWN_FEATURE_ID"),
        (
            {
                "intent": "new_idea",
                "replace_features": [],
                "add_features": [{"text": "new", "rationale": "x"}],
            },
            "NEW_CONVERSATION_REQUIRED",
        ),
        (
            {
                "intent": "explain_evidence",
                "replace_features": [],
                "focus_evidence_ids": [str(uuid4())],
            },
            "UNKNOWN_EVIDENCE_ID",
        ),
    ],
)
def test_context_rejects_unknown_ids_and_version(changes, code) -> None:  # type: ignore[no-untyped-def]
    with pytest.raises(PlannerViolation, match=code):
        validate_plan(parsed(**changes), CONTEXT)


def test_missing_source_or_focus_requires_clarification() -> None:
    plan = parsed(intent="explain_evidence", replace_features=[])
    assert normalize_plan(plan, PlannerContext(IDEA, 2)).intent == "clarify"
    assert normalize_plan(plan, CONTEXT).intent == "clarify"


@pytest.mark.parametrize("changed", ["state_hash", "generation_id", "config_hash", "query_hash"])
def test_retrieval_invalidated_independently(changed: str) -> None:
    key = RetrievalKey(
        state_hash=state_hash(IDEA),
        generation_id=uuid4(),
        config_hash="a" * 64,
        query_hash="b" * 64,
    )
    plan = parsed(intent="general_followup", replace_features=[])
    assert not requires_retrieval(plan, current=key, previous=key, has_evidence=True)
    value = uuid4() if changed == "generation_id" else "f" * 64
    assert requires_retrieval(
        plan, current=key.model_copy(update={changed: value}), previous=key, has_evidence=True
    )
    assert requires_retrieval(plan, current=key, previous=key, has_evidence=False)
    assert requires_retrieval(plan, current=key, previous=None, has_evidence=True)
    historical = normalize_plan(
        parsed(intent="explain_evidence", replace_features=[], focus_evidence_ids=[str(EVIDENCE)]),
        CONTEXT,
    )
    assert not requires_retrieval(historical, current=key, previous=None, has_evidence=True)


def run_planner(outputs, *, context=CONTEXT, cancel=None, status=200):  # type: ignore[no-untyped-def]
    calls = []

    async def exercise():  # type: ignore[no-untyped-def]
        def handler(request):  # type: ignore[no-untyped-def]
            calls.append(json.loads(request.content))
            content = outputs[min(len(calls) - 1, len(outputs) - 1)]
            if cancel is not None:
                cancel.set()
            frames = [
                {"message": {"role": "assistant", "thinking": "PRIVATE_REASONING"}},
                {"message": {"role": "assistant", "content": content}},
                {"done": True, "done_reason": "stop"},
            ]
            return httpx.Response(status, text="\n".join(json.dumps(f) for f in frames) + "\n")

        async with httpx.AsyncClient(
            base_url="http://fake", transport=httpx.MockTransport(handler)
        ) as client:
            provider = OllamaProvider(
                client,
                gate=GenerationGate(),
                model_revisions={"m": "fixture"},
                supported_efforts={},
            )
            planner = IntentPlanner(provider, model_id="m", prompt=PROMPT)
            return await planner.plan(
                message="Замени OCR на barcode",
                context=context,
                request_id="r",
                timeout=3,
                cancel=cancel,
            )

    return asyncio.run(exercise()), calls


@pytest.mark.parametrize(
    "invalid", ["{bad JSON PRIVATE_DRAFT", json.dumps({"secret": "PRIVATE_DRAFT"})]
)
def test_one_repair_from_malformed_json_or_schema(invalid: str) -> None:
    result, calls = run_planner([invalid, json.dumps(model_payload())])
    assert result.plan.intent == "modify_idea" and result.attempts == 2
    assert len(calls) == 2
    assert "PRIVATE_DRAFT" not in json.dumps(calls[1])
    assert "PRIVATE_REASONING" not in repr(result)
    assert calls[1]["options"]["num_predict"] == 4096


def test_two_invalid_responses_fall_back_without_patch() -> None:
    result, calls = run_planner(["broken"])
    assert result.attempts == len(calls) == 2
    assert result.plan.intent == "clarify" and not result.plan.has_patch
    assert apply_patch(result.plan, CONTEXT) == IDEA


def test_planner_does_not_receive_graph_context_window() -> None:
    _result, calls = run_planner([json.dumps(model_payload())])
    assert len(calls) == 1
    assert "num_ctx" not in calls[0]["options"]


def test_provider_unavailable_no_repair() -> None:
    result, calls = run_planner(["private provider error"], status=503)
    assert result.plan.intent == "clarify" and len(calls) == 1
    assert result.diagnostic_codes == ("INFERENCE_UNAVAILABLE",)


def test_cancel_propagates_without_fallback() -> None:
    with pytest.raises(InferenceCancelled):
        run_planner([json.dumps(model_payload())], cancel=asyncio.Event())


def test_second_patent_mapping_is_in_prompt_and_focus_is_preserved() -> None:
    first = uuid4()
    context = PlannerContext(
        IDEA,
        2,
        uuid4(),
        (first, EVIDENCE),
        (
            EvidenceSource(ordinal=1, document_id=uuid4(), title="Первый", evidence_ids=[first]),
            EvidenceSource(ordinal=2, document_id=uuid4(), title="Второй", evidence_ids=[EVIDENCE]),
        ),
    )
    result, calls = run_planner(
        [
            json.dumps(
                model_payload(
                    intent="explain_evidence",
                    replace_features=[],
                    focus_source_ordinals=[2],
                )
            )
        ],
        context=context,
    )
    assert result.plan.focus_evidence_ids == [EVIDENCE]
    prompt = calls[0]["messages"][-1]["content"]
    assert '"ordinal": 2' in prompt and '"Второй"' in prompt
