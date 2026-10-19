import argparse
import asyncio
import copy
import json

import pytest
from pydantic import ValidationError

from app.domain.contracts import AnalysisRelationV1, AnalysisV1, QuoteV1
from app.services.analyst import _presentation, _render_analysis
from eval.harness import (
    Observation,
    ReplayFrame,
    evaluate,
    fixture_observation,
    frozen_inputs,
    replay_matches,
    uid,
)
from eval.judge import judge_case
from eval.report import compare
from eval.run import execute


@pytest.fixture
def sample():
    manifest, cases, _ = frozen_inputs()
    observation = asyncio.run(fixture_observation(cases[0], manifest))
    return manifest, cases[0], observation


def args(path, **changes):
    return argparse.Namespace(
        output=path,
        baseline=changes.get("baseline"),
        observations=changes.get("observations"),
        judge_results=changes.get("judge_results"),
        judge_id="offline-review-rubric-v1",
        database_env=None,
    )


def sync_projection(observation):
    observation.public_analysis.items = observation.answer.summary
    observation.public_analysis.limitations = observation.answer.limitations
    observation.presentation = _presentation(observation.answer)
    observation.replay = [
        ReplayFrame(kind="reset", sequence=1, text=observation.presentation.text, chunk_index=1),
        ReplayFrame(kind="terminal", sequence=2),
    ]


def test_ten_case_run_and_compatible_baseline(tmp_path):
    baseline, current = tmp_path / "baseline", tmp_path / "current"
    assert asyncio.run(execute(args(baseline))) == 0
    assert asyncio.run(execute(args(current, baseline=baseline / "run.json"))) == 0
    run = json.loads((current / "run.json").read_text(encoding="utf-8"))
    assert run["summary"]["cases"] == run["summary"]["passed"] == 10
    assert run["summary"]["citation_na_cases"] == 1
    assert run["summary"]["faithfulness"] is None
    assert run["summary"]["latency_p95_ms"] is None
    assert run["baseline_diff"]["regressions"] == []
    assert len((current / "validated.jsonl").read_text(encoding="utf-8").splitlines()) == 10
    assert (current / "report.md").exists() and (current / "report.html").exists()


@pytest.mark.parametrize(
    "defect,code",
    [
        ("phantom", "PHANTOM_CITATION"),
        ("quote", "FABRICATED_QUOTE"),
        ("offset", "FABRICATED_QUOTE"),
        ("revision", "SOURCE_REVISION_MISMATCH"),
        ("public", "PUBLIC_PROJECTION_MISMATCH"),
        ("fallback", "INVALID_FALLBACK"),
        ("unsupported", "INVALID_FALLBACK_PROJECTION"),
        ("replay", "REPLAY_MISMATCH"),
    ],
)
def test_adversarial_outputs_fail(sample, defect, code):
    manifest, case, observation = sample
    claim = observation.answer.summary[0]
    if defect == "phantom":
        claim.quotes[0].evidence_id = uid("foreign")
        claim.evidence_ids = [uid("foreign")]
    elif defect == "quote":
        claim.quotes[0].text = "invented quotation"
    elif defect == "offset":
        claim.quotes[0].start += 1
    elif defect == "revision":
        observation.evidence[0].revision_id = uid("different-revision")
    elif defect == "public":
        observation.public_analysis.items = []
        observation.public_analysis.limitations[0].message = "unscoped global conclusion"
        # Списки могли разделяться renderer-ом; создаём независимый public notice.
        observation.public_analysis = observation.public_analysis.model_copy(deep=True)
        observation.public_analysis.limitations[0].message = "extra public claim"
    elif defect == "fallback":
        observation.answer.matches = [
            {
                "feature_id": observation.idea.features[0].id,
                "document_id": uid("fake"),
                "claims": [],
            }
        ]
        # Используем валидный DTO, а не обход schema через присваивание dict.
        from app.domain.contracts import MatchV1

        observation.answer.matches = [
            MatchV1(feature_id=observation.idea.features[0].id, document_id=uid("fake"), claims=[])
        ]
    elif defect == "unsupported":
        claim.text += " Это доказывает юридическую новизну."
    elif defect == "replay":
        observation.replay = observation.replay[:-1]
    assert code in evaluate(observation, case, manifest)["errors"]


@pytest.mark.parametrize("relation", ["full", "partial", "conflicting", "uncertain"])
def test_analysis_projection_and_semantics_are_separate(sample, relation):
    manifest, case, observation = sample
    item = observation.evidence[0]
    feature_id = observation.idea.features[0].id
    observation.analysis = AnalysisV1(
        schema_version=1,
        relations=[
            AnalysisRelationV1(
                feature_id=feature_id,
                document_id=item.document_id,
                relation=relation,
                evidence_ids=[item.evidence_id],
                quotes=[
                    QuoteV1(
                        evidence_id=item.evidence_id,
                        start=item.span_start,
                        end=item.span_end,
                        text=item.quoted_span,
                    )
                ],
            )
        ],
        unresolved_feature_ids=[] if relation in ("full", "partial") else [feature_id],
    )
    observation.answer, observation.public_analysis, observation.presentation = _render_analysis(
        observation.analysis, observation.idea, observation.coverage
    )
    observation.outcome = "analysis"
    sync_projection(observation)
    row = evaluate(observation, case, manifest)
    assert row["passed"]
    assert row["judge"] is None  # Структура не доказывает смысловую поддержку relation.
    observation.public_analysis = observation.public_analysis.model_copy(deep=True)
    observation.public_analysis.items[0].text += "unsupported"
    assert "PUBLIC_PROJECTION_MISMATCH" in evaluate(observation, case, manifest)["errors"]


@pytest.mark.parametrize("status", ["failed", "cancelled"])
def test_terminal_outcomes_do_not_publish_result(sample, status):
    manifest, case, observation = sample
    observation.status, observation.outcome = status, None
    assert "NONTERMINAL_RESULT_LEAK" in evaluate(observation, case, manifest)["errors"]
    observation.answer = observation.analysis = observation.public_analysis = None
    observation.presentation = None
    assert evaluate(observation, case, manifest)["errors"] == ["UNEXPECTED_TERMINAL_STATUS"]


def test_no_gold_used_for_retrieval(sample):
    manifest, case, observation = sample
    altered = copy.deepcopy(case)
    altered["expected"]["expected_source_ids"] = ["not-a-real-source"]
    altered["expected"]["spans"] = []
    assert (
        asyncio.run(fixture_observation(altered, manifest)).candidate_ids
        == observation.candidate_ids
    )


def test_frozen_input_drift_is_rejected(monkeypatch, tmp_path):
    import eval.harness as harness

    (tmp_path / "eval").mkdir()
    lock = {"bad.txt": "0" * 64}
    (tmp_path / "eval/fixture.lock.json").write_text(json.dumps(lock))
    (tmp_path / "bad.txt").write_text("changed")
    monkeypatch.setattr(harness, "ROOT", tmp_path)
    with pytest.raises(ValueError, match="FROZEN_INPUT_DRIFT"):
        frozen_inputs()


def test_capture_rejects_reasoning_without_artifact_or_error_echo(tmp_path, capsys):
    manifest, cases, lock = frozen_inputs()
    values = [
        asyncio.run(fixture_observation(case, manifest)).model_dump(mode="json") for case in cases
    ]
    values[0]["thinking"] = "PRIVATE_REASONING_SENTINEL"
    capture = tmp_path / "capture.json"
    capture.write_text(json.dumps(capture_value(lock, values)), encoding="utf-8")
    with pytest.raises(ValueError, match="INVALID_OBSERVATION_SCHEMA") as caught:
        asyncio.run(execute(args(tmp_path / "out", observations=capture)))
    assert "PRIVATE_REASONING_SENTINEL" not in str(caught.value)
    assert "PRIVATE_REASONING_SENTINEL" not in capsys.readouterr().out
    assert not (tmp_path / "out").exists()


def test_invalid_capture_grounding_not_saved(tmp_path):
    manifest, cases, lock = frozen_inputs()
    values = [
        asyncio.run(fixture_observation(case, manifest)).model_dump(mode="json") for case in cases
    ]
    values[0]["answer"]["summary"][0]["quotes"][0]["text"] = "REJECTED_VALUE_SENTINEL"
    capture = tmp_path / "capture.json"
    capture.write_text(json.dumps(capture_value(lock, values)), encoding="utf-8")
    output = tmp_path / "out"
    assert asyncio.run(execute(args(output, observations=capture))) == 1
    assert all(
        "REJECTED_VALUE_SENTINEL" not in p.read_text(encoding="utf-8") for p in output.iterdir()
    )


def judge_value(case_id):
    return {
        "case_id": case_id,
        "scores": dict.fromkeys(
            [
                "faithfulness",
                "relevance",
                "completeness",
                "feature_matching",
                "conclusion_validity",
            ],
            4,
        ),
        "cited_problem_spans": [],
        "rationale": "SUPPORTED",
        "confidence": 0.8,
    }


def capture_value(lock, values):
    return {
        "snapshot": lock,
        "observations": values,
        "versions": {
            "pipeline_version": "synthetic-test-v1",
            "model_config_sha256": "0" * 64,
            "prompt_schema_sha256": "1" * 64,
            "retrieval_config_sha256": "2" * 64,
        },
    }


def test_semantic_judge_blocks_unsupported_relation(tmp_path):
    _, cases, _ = frozen_inputs()
    results = {c["case_id"]: judge_value(c["case_id"]) for c in cases}
    results[cases[0]["case_id"]]["rationale"] = "UNSUPPORTED_RELATION"
    path = tmp_path / "judgments.json"
    path.write_text(json.dumps(results), encoding="utf-8")
    assert asyncio.run(execute(args(tmp_path / "out", judge_results=path))) == 1
    run = json.loads((tmp_path / "out/run.json").read_text(encoding="utf-8"))
    assert run["results"][0]["errors"] == ["SEMANTIC_FAITHFULNESS"]


def test_judge_disabled_retry_and_span_membership(sample):
    _, case, observation = sample
    payload = observation.model_dump(mode="json")
    assert judge_case(case["case_id"], payload) == (None, "DISABLED")
    calls = []

    def invoke(value, retry):
        calls.append(retry)
        return judge_value(case["case_id"]) if retry else {"thinking": "SECRET"}

    result, status = judge_case(case["case_id"], payload, invoke)
    assert result and status == "OK" and calls == [False, True]
    bad = judge_value(case["case_id"])
    bad["cited_problem_spans"] = [{"evidence_id": "foreign", "start": 0, "end": 2}]
    assert judge_case(case["case_id"], payload, lambda *_: bad) == (None, "INVALID_RESULT")


def test_baseline_identity_drop_and_per_case_defect(tmp_path):
    output = tmp_path / "run"
    asyncio.run(execute(args(output)))
    baseline = json.loads((output / "run.json").read_text(encoding="utf-8"))
    current = copy.deepcopy(baseline)
    current["snapshot"] = {}
    with pytest.raises(ValueError, match="INCOMPATIBLE_BASELINE"):
        compare(current, baseline)
    current = copy.deepcopy(baseline)
    current["summary"]["recall_at_10"] -= 0.05
    assert compare(current, baseline)["regressions"] == []
    current = copy.deepcopy(baseline)
    current["summary"]["recall_at_10"] -= 0.06
    current["results"][0]["passed"] = False
    current["results"][0]["errors"] = ["FABRICATED_QUOTE"]
    assert set(compare(current, baseline)["regressions"]) == {
        "recall_at_10",
        current["case_ids"][0],
    }


def test_duplicate_delivery_reset_and_truncated_terminal(sample):
    _, _, observation = sample
    p = observation.presentation
    first = ReplayFrame(kind="delta", sequence=1, chunk_index=0, text=p.text[:20])
    frames = [
        first,
        first,
        ReplayFrame(kind="reset", sequence=4, text=p.text, chunk_index=1),
        ReplayFrame(kind="terminal", sequence=5),
    ]
    assert replay_matches(frames, p)
    assert not replay_matches(frames[:-1], p)
    assert not replay_matches([first, first.model_copy(update={"text": "changed"})], p)


def test_observation_strict_nested_schema_and_empty_citations(sample):
    _, _, observation = sample
    value = observation.model_dump(mode="json")
    value["answer"]["summary"][0]["evidence_ids"] = []
    with pytest.raises(ValidationError):
        Observation.model_validate_json(json.dumps(value))


def test_html_escapes_model_text(tmp_path):
    from eval.report import write_reports

    run = {
        "profile": "<script>bad()</script>",
        "run_id": "x",
        "judge_identity": "disabled",
        "results": [],
        "summary": {},
        "baseline_diff": None,
    }
    write_reports(tmp_path, run)
    assert "<script>" not in (tmp_path / "report.html").read_text(encoding="utf-8")
