"""Summarize deterministic LLM-003 candidate results without model judging."""
from __future__ import annotations

import json
import statistics
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
RAW = ROOT / "docs/validation/LLM-003/raw"


def read(path: Path) -> list[dict]:
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]


def percentile(values: list[float], p: float) -> float | None:
    if not values:
        return None
    ordered = sorted(values)
    return ordered[min(len(ordered) - 1, int((len(ordered) - 1) * p))]


def summarize(rows: list[dict], role: str) -> dict:
    by_case = {row["case_id"]: row for row in rows}
    latencies = [float(r[k]) for r in rows for k in ("latency_ms", "group_latency_ms") if r.get(k) is not None]
    base = {"tag": rows[0]["model"], "digest": rows[0]["digest"], "cases": len(by_case),
            "latency_ms": {"median": statistics.median(latencies) if latencies else None,
                           "p95": percentile(latencies, .95)}}
    if role == "planner":
        base.update({"passed": sum(bool(r["pass"]) for r in by_case.values()),
                     "schema_passed": sum(bool(r.get("schema_valid")) for r in by_case.values()),
                     "hard_gates_pass": all(r.get("schema_valid") and r.get("citation_ids_valid") for r in by_case.values())})
    elif role == "analyst":
        base.update({"passed": sum(bool(r["pass"]) for r in by_case.values()),
                     "schema_passed": sum(bool(r.get("schema_valid")) for r in by_case.values()),
                     "citation_passed": sum(bool(r.get("citation_valid")) for r in by_case.values()),
                     "safe_fallbacks": sum(r.get("outcome") == "safe_fallback" for r in by_case.values()),
                     "hard_gates_pass": all(r.get("schema_valid") and r.get("citation_valid") and r.get("outcome") != "safe_fallback" for r in by_case.values())})
    else:
        positives = [r for r in by_case.values() if not r.get("gold_negative")]
        negatives = [r for r in by_case.values() if r.get("gold_negative")]
        tp = sum(int(r.get("validated_fact_count", 0)) for r in positives)
        predicted = sum(int(r.get("validated_fact_count", 0)) for r in by_case.values())
        protocol_failures = sum(r.get("status") == "protocol_or_runtime_failure" for r in by_case.values())
        base.update({"positive_cases": len(positives), "negative_cases": len(negatives),
                     "valid_gold_facts": tp, "gold_facts": sum(int(r.get("gold_fact_count", 0)) for r in positives),
                     "precision": tp / predicted if predicted else 1.0,
                     "recall": tp / sum(int(r.get("gold_fact_count", 0)) for r in positives) if positives else 0.0,
                     "negative_cases_passed": sum(bool(r.get("pass")) for r in negatives),
                     "protocol_failures": protocol_failures,
                     "hard_gates_pass": protocol_failures == 0 and all(r.get("schema_and_provenance_valid") and not r.get("extra_facts") for r in by_case.values())})
    return base


def main() -> None:
    candidates = {"planner": RAW / "planner_candidate_warm.jsonl",
                  "graph_extractor": RAW / "graph_candidate_warm.jsonl"}
    results = {"schema_version": 1, "task": "LLM-003", "status": "comparison_complete_no_safe_production_decision",
               "protocol": {"profile": "candidate_warm", "sequential": True, "gold_labels_model_generated": False,
                            "latency_note": "runner call timings; RSS/swap and reliable output token counts unavailable"},
               "roles": {}, "failures": []}
    for role, path in candidates.items():
        rows = read(path)
        groups: dict[str, list[dict]] = {}
        for row in rows:
            groups.setdefault(row["model"], []).append(row)
        actual_role = "graph" if role == "graph_extractor" else role
        results["roles"][role] = [summarize(group, actual_role) for group in groups.values()]
    graph_fixtures = read(ROOT / "eval/llm003/graph.jsonl")
    expected_graph_facts = sum(len(case["expected"]) for case in graph_fixtures)
    expected_positive = sum(bool(case["expected"]) for case in graph_fixtures)
    expected_negative = len(graph_fixtures) - expected_positive
    for item in results["roles"]["graph_extractor"]:
        item["positive_cases"] = expected_positive
        item["negative_cases"] = expected_negative
        item["gold_facts"] = expected_graph_facts
        item["recall"] = item["valid_gold_facts"] / expected_graph_facts if expected_graph_facts else 0.0
    results["failures"] = [{"role": "graph_extractor", "tag": row["model"], "case_id": row["case_id"],
                            "error_type": row["error_type"], "status": row["status"]}
                           for row in read(candidates["graph_extractor"])
                           if row.get("status") == "protocol_or_runtime_failure"]
    analyst_paths = [RAW / "analyst_candidate_warm_low.jsonl", RAW / "analyst_candidate_warm_default.jsonl"]
    analyst_groups: dict[str, list[dict]] = {}
    for path in analyst_paths:
        for row in read(path):
            analyst_groups.setdefault(row["model"], []).append(row)
    results["roles"]["analyst"] = [summarize(group, "analyst") for group in analyst_groups.values()]
    results["production_decision"] = {"planner": None, "analyst": None, "graph_extractor": None,
                                       "reason": "Observed semantic accuracy is too low for a safe model pin; Graph extractor candidates yielded 0/25, 1/25 and 0/25 validated facts.",
                                       "config_changed": False, "mass_backfill_allowed": False}
    (ROOT / "docs/validation/LLM-003/results.json").write_text(json.dumps(results, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(results, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
