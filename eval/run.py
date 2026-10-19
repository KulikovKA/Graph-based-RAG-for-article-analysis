"""Запуск: python -m eval.run --output data/eval/run-001 [--baseline .../run.json]."""

from __future__ import annotations

import argparse
import asyncio
import json
import os
import re
import subprocess
from datetime import UTC, datetime
from pathlib import Path
from typing import Any
from uuid import UUID, uuid4

import yaml
from pydantic import ValidationError

from eval.harness import (
    ROOT,
    CaptureVersions,
    Observation,
    evaluate,
    fixture_observation,
    frozen_inputs,
    index_identity,
    sha,
)
from eval.judge import file_judge, judge_case
from eval.report import compare, summarize, write_reports


def persist(database_url: str, run: dict[str, Any], cases: list[dict[str, Any]]) -> None:
    """Необязательная атомарная запись в существующие eval_* таблицы."""
    from sqlalchemy import select
    from sqlalchemy.orm import Session

    from app.storage.models import EvalCase, EvalResult, EvalRun
    from app.storage.repositories import make_engine

    engine = make_engine(database_url)
    try:
        with Session(engine) as session, session.begin():
            record = EvalRun(
                id=UUID(run["run_id"]),
                config_versions_json=run["versions"],
                snapshot_ref=run["snapshot_id"],
                completed_at=datetime.now(UTC),
            )
            session.add(record)
            session.flush()
            for case, result in zip(cases, run["results"], strict=True):
                stored = session.scalar(
                    select(EvalCase).where(EvalCase.case_key == case["case_id"])
                )
                if stored is None:
                    stored = EvalCase(
                        case_key=case["case_id"],
                        split="dev",
                        input_json={"query": case["query"]},
                        expected_json=case["expected"],
                        provenance_json=case["provenance"],
                    )
                    session.add(stored)
                    session.flush()
                elif stored.expected_json != case["expected"]:
                    raise ValueError("DATABASE_CASE_DRIFT")
                session.add(
                    EvalResult(
                        eval_run_id=record.id,
                        eval_case_id=stored.id,
                        result_json=result,
                    )
                )
    finally:
        engine.dispose()


async def execute(args: argparse.Namespace) -> int:
    manifest, cases, lock = frozen_inputs()
    versions: dict[str, Any] = {
        name: sha(ROOT / name)
        for name in (
            "config/models.yaml",
            "prompts/planner_v1.txt",
            "prompts/analyst_v1.txt",
            "prompts/analyst_narrative_v1.txt",
            "eval/harness.py",
            "eval/judge.py",
            "eval/report.py",
            "eval/run.py",
            "src/app/services/analyst.py",
            "src/app/services/rerank.py",
            "src/app/domain/contracts.py",
            "src/app/services/ingestion.py",
        )
    }
    observations = {}
    capture = None
    if args.observations:
        capture = json.loads(args.observations.read_text(encoding="utf-8"))
        if capture["snapshot"] != lock or set(capture) != {"snapshot", "observations", "versions"}:
            raise ValueError("CAPTURE_SNAPSHOT_MISMATCH")
        try:
            versions["observed_pipeline"] = CaptureVersions.model_validate(
                capture["versions"]
            ).model_dump()
        except ValidationError:
            raise ValueError("INVALID_CAPTURE_VERSIONS") from None
        for value in capture["observations"]:
            if not isinstance(value, dict):
                raise ValueError("INVALID_OBSERVATION_SCHEMA")
            key = value.get("case_id")
            if key in observations:
                raise ValueError("DUPLICATE_CASE")
            observations[key] = value
        if set(observations) != {c["case_id"] for c in cases}:
            raise ValueError("CAPTURE_CASE_MISMATCH")
        versions["capture_sha256"] = sha(args.observations)
    judge_rows = None
    if args.judge_results:
        if not re.fullmatch(r"[a-zA-Z0-9_.:-]{1,100}", args.judge_id):
            raise ValueError("INVALID_JUDGE_ID")
        versions["judge_results_sha256"] = sha(args.judge_results)
        judge_rows = json.loads(args.judge_results.read_text(encoding="utf-8"))
        if set(judge_rows) != {c["case_id"] for c in cases}:
            raise ValueError("JUDGE_CASE_MISMATCH")
    run: dict[str, Any] = {
        "schema_version": "eval.run.v1",
        "run_id": str(uuid4()),
        "started_at": datetime.now(UTC).isoformat(),
        "git_commit": subprocess.check_output(
            ["git", "rev-parse", "HEAD"], cwd=ROOT, text=True
        ).strip(),
        "git_dirty": bool(
            subprocess.check_output(["git", "status", "--porcelain"], cwd=ROOT, text=True).strip()
        ),
        "profile": "captured-observations" if capture else "fixture-contract-replay",
        "snapshot": lock,
        "snapshot_id": sha(ROOT / "eval/fixture.lock.json"),
        "index_snapshot": index_identity(manifest),
        "case_ids": [c["case_id"] for c in cases],
        "versions": versions,
        "judge_identity": args.judge_id if args.judge_results else "disabled",
        "results": [],
        "baseline_diff": None,
        "pipeline_version": "eval001-contract-replay-v1",
        "configured_models": yaml.safe_load(
            (ROOT / "config/models.yaml").read_text(encoding="utf-8")
        ),
        "execution": {
            "models_called_by_harness": [],
            "retrieval": "imported" if capture else "lexical_scores; top10; stopword overlap gate",
            "analyst": "imported"
            if capture
            else "production Analyst; unavailable fixture provider",
            "production_model_quality_measured": False,
            "ttft_ms": None,
            "reasoning_tokens": None,
            "output_tokens": None,
            "peak_ram_bytes": None,
            "model_switch_ms": None,
            "timing_reason": "NOT_MEASURED",
        },
    }
    artifacts = []
    for case in cases:
        try:
            observation = (
                Observation.model_validate_json(json.dumps(observations[case["case_id"]]))
                if capture
                else await fixture_observation(case, manifest)
            )
        except ValidationError:
            # Не сериализуем ValidationError: он может содержать rejected input.
            raise ValueError("INVALID_OBSERVATION_SCHEMA") from None
        row = evaluate(observation, case, manifest)
        if row["passed"]:
            payload = observation.model_dump(mode="json")
            judge, status = judge_case(
                case["case_id"],
                payload,
                file_judge(judge_rows[case["case_id"]]) if judge_rows is not None else None,
            )
            row["judge_status"] = status
            row["judge"] = judge.model_dump(mode="json") if judge else None
            if status not in ("DISABLED", "OK"):
                row["errors"].append("JUDGE_FAILED")
            if judge and (
                judge.rationale == "UNSUPPORTED_RELATION" or judge.scores.faithfulness < 2
            ):
                row["errors"].append("SEMANTIC_FAITHFULNESS")
            row["passed"] = not row["errors"]
            artifacts.append(
                {
                    "input": {"case_id": case["case_id"], "query": case["query"]},
                    "validated_observation": payload,
                }
            )
        run["results"].append(row)
    run["summary"] = summarize(run["results"])
    if args.baseline:
        run["baseline_diff"] = compare(run, json.loads(args.baseline.read_text(encoding="utf-8")))
    # Каталог создаётся лишь после проверки всех inputs и совместимости baseline.
    args.output.mkdir(parents=True, exist_ok=False)
    (args.output / "run.json").write_text(
        json.dumps(run, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    (args.output / "results.jsonl").write_text(
        "".join(json.dumps(row, ensure_ascii=False) + "\n" for row in run["results"]),
        encoding="utf-8",
    )
    (args.output / "validated.jsonl").write_text(
        "".join(json.dumps(row, ensure_ascii=False) + "\n" for row in artifacts), encoding="utf-8"
    )
    write_reports(args.output, run)
    if args.database_env:
        try:
            persist(os.environ[args.database_env], run, cases)
        except Exception:
            raise ValueError("EVAL_DATABASE_WRITE_FAILED") from None
    print(json.dumps(run["summary"], ensure_ascii=False))
    return int(
        any(not r["passed"] for r in run["results"])
        or bool(run["baseline_diff"] and run["baseline_diff"]["regressions"])
    )


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--baseline", type=Path)
    parser.add_argument("--observations", type=Path)
    parser.add_argument("--judge-results", type=Path)
    parser.add_argument("--judge-id", default="offline-review-rubric-v1")
    parser.add_argument("--database-env", help="Имя переменной с URL отдельной eval БД")
    args = parser.parse_args()
    try:
        return asyncio.run(execute(args))
    except (ValueError, KeyError, TypeError, OSError):
        print("EVAL_INPUT_OR_STORAGE_ERROR")
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
