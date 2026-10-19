"""Метрики и escaped HTML/Markdown отчёт; несовместимые baseline отвергаются."""

from __future__ import annotations

import html
import json
import math
import statistics
from pathlib import Path
from typing import Any

KNOWN_ERRORS = frozenset(
    """
ANSWER_ANALYSIS_MISMATCH COVERAGE_MISMATCH DUPLICATE_CANDIDATE DUPLICATE_EVIDENCE
EVIDENCE_SPAN_MISMATCH EXPECTED_NO_EVIDENCE FABRICATED_QUOTE INVALID_ANALYSIS_GROUNDING
INVALID_CITATION INVALID_CLARIFICATION INVALID_COMPLETED_OUTCOME INVALID_FALLBACK
INVALID_FALLBACK_PROJECTION INVALID_NO_EVIDENCE INVALID_TERMINAL_OUTCOME MISSING_ANALYSIS
MISSING_CONCLUSION_CONSTRAINT MISSING_PARTIAL_NOTICE MISSING_RESULT NONTERMINAL_RESULT_LEAK
PHANTOM_CITATION PUBLIC_PROJECTION_MISMATCH REPLAY_MISMATCH SOURCE_METADATA_MISMATCH
SOURCE_REVISION_MISMATCH UNAVAILABLE_SOURCE_USED UNKNOWN_CANDIDATE UNKNOWN_SOURCE
UNSUPPORTED_FALLBACK_CLAIM JUDGE_FAILED SEMANTIC_FAITHFULNESS UNEXPECTED_TERMINAL_STATUS
""".split()
)


def mean(rows: list[dict[str, Any]], key: str) -> float | None:
    values = [row[key] for row in rows if row[key] is not None]
    return statistics.mean(values) if values else None


def summarize(rows: list[dict[str, Any]]) -> dict[str, Any]:
    times = sorted(r["elapsed_ms"] for r in rows if r["elapsed_ms"] is not None)
    judged = [r["judge"]["scores"]["faithfulness"] for r in rows if r["judge"] is not None]
    citation_total = sum(r["citation_denominator"] for r in rows)
    citation_valid = sum(
        r["citation_validity"] * r["citation_denominator"]
        for r in rows
        if r["citation_validity"] is not None
    )
    return {
        "cases": len(rows),
        "passed": sum(r["passed"] for r in rows),
        "recall_at_10": mean(rows, "recall_at_10"),
        "mrr": mean(rows, "reciprocal_rank"),
        "citation_validity": citation_valid / citation_total if citation_total else None,
        "citation_denominator": citation_total,
        "citation_na_cases": sum(r["citation_validity"] is None for r in rows),
        "faithfulness": statistics.mean(judged) if judged else None,
        "judge_evaluated_cases": len(judged),
        "latency_p50_ms": statistics.median(times) if times else None,
        "latency_p95_ms": times[max(0, math.ceil(len(times) * 0.95) - 1)] if times else None,
        "latency_gate": "UNSET",
        "planner_accuracy": None,
        "planner_reason": "EVAL000_HAS_NO_PLANNER_GOLD",
        "failure_rate": sum(r["status"] == "failed" for r in rows) / len(rows),
    }


def compare(current: dict[str, Any], baseline: dict[str, Any]) -> dict[str, Any]:
    for key in (
        "schema_version",
        "snapshot",
        "index_snapshot",
        "case_ids",
        "profile",
        "judge_identity",
    ):
        if current[key] != baseline[key]:
            raise ValueError("INCOMPATIBLE_BASELINE")
    old_rows = {r["case_id"]: r for r in baseline["results"]}
    if any(not set(row["errors"]) <= KNOWN_ERRORS for row in old_rows.values()):
        raise ValueError("INVALID_BASELINE_DIAGNOSTICS")
    if len(old_rows) != len(baseline["case_ids"]) or set(old_rows) != set(current["case_ids"]):
        raise ValueError("INCOMPATIBLE_BASELINE_CASES")
    regressions = []
    for row in current["results"]:
        previous = old_rows[row["case_id"]]
        if previous["passed"] and not row["passed"]:
            regressions.append(row["case_id"])
    metric_changes = {}
    for metric, threshold in (("recall_at_10", 0.05), ("faithfulness", 0.25)):
        new, old = current["summary"][metric], baseline["summary"][metric]
        if new is None and old is not None:
            regressions.append(metric + ":MISSING")
        delta = new - old if new is not None and old is not None else None
        metric_changes[metric] = delta
        if (
            delta is not None
            and delta < -threshold
            and not math.isclose(delta, -threshold, abs_tol=1e-12)
        ):
            regressions.append(metric)
    return {
        "regressions": regressions,
        "metric_deltas": metric_changes,
        "per_case": [
            {
                "case_id": r["case_id"],
                "previous_errors": old_rows[r["case_id"]]["errors"],
                "current_errors": r["errors"],
                "previous_outcome": old_rows[r["case_id"]]["outcome"],
                "current_outcome": r["outcome"],
                "recall_delta": r["recall_at_10"] - old_rows[r["case_id"]]["recall_at_10"]
                if r["recall_at_10"] is not None
                and old_rows[r["case_id"]]["recall_at_10"] is not None
                else None,
            }
            for r in current["results"]
        ],
    }


def write_reports(destination: Path, run: dict[str, Any]) -> None:
    lines = [
        "# EVAL-001 — offline regression report",
        "",
        f"Profile: `{run['profile']}`. Run: `{run['run_id']}`.",
        "",
        "Fixture profile проверяет lexical fallback и deterministic Analyst fallback. "
        "Это не baseline качества production-моделей и не EVAL-002.",
        "",
        "Judge: " + run["judge_identity"] + ". Без judge semantic faithfulness = N/A.",
        "Latency gate: UNSET. Модель, RAM, TTFT, tokens и browser timings в fixture не измеряются.",
        "",
        "| Case | Outcome | Recall@10 | Citations | Errors |",
        "|---|---|---|---|---|",
    ]
    for row in run["results"]:
        citation = row["citation_validity"]
        lines.append(
            f"| {row['case_id']} | {row['outcome'] or row['status']} | "
            f"{row['recall_at_10'] if row['recall_at_10'] is not None else 'N/A'} | "
            f"{citation if citation is not None else 'N/A'} | {', '.join(row['errors']) or '—'} |"
        )
    lines.extend(
        [
            "",
            "## Summary",
            "",
            "```json",
            json.dumps(run["summary"], ensure_ascii=False, indent=2),
            "```",
        ]
    )
    if run.get("baseline_diff") is not None:
        lines.extend(
            [
                "",
                "## Baseline diff",
                "",
                "```json",
                json.dumps(run["baseline_diff"], ensure_ascii=False, indent=2),
                "```",
            ]
        )
    text = "\n".join(lines) + "\n"
    (destination / "report.md").write_text(text, encoding="utf-8")
    (destination / "report.html").write_text(
        '<!doctype html><html lang="ru"><meta charset="utf-8">'
        "<title>EVAL-001</title><style>body{max-width:1100px;margin:2rem auto;"
        "font:16px system-ui}pre{white-space:pre-wrap;overflow-wrap:anywhere}</style>"
        "<body><pre>" + html.escape(text) + "</pre></body></html>",
        encoding="utf-8",
    )
