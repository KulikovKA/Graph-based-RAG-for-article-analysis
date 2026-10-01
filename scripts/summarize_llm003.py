"""Summarize deterministic LLM-003 runs from immutable per-case JSONL."""

from __future__ import annotations

import json
import statistics
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
RAW = ROOT / "docs/validation/LLM-003/raw"


def read(path: Path) -> list[dict]:
    return [
        json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()
    ]


def percentile(values: list[float], p: float) -> float | None:
    if not values:
        return None
    ordered = sorted(values)
    return ordered[min(len(ordered) - 1, int((len(ordered) - 1) * p))]


def summarize(rows: list[dict], role: str, run: str) -> dict:
    by_case = {row["case_id"]: row for row in rows}
    latencies = [
        float(row[key])
        for row in by_case.values()
        for key in ("latency_ms", "group_latency_ms")
        if row.get(key) is not None
    ]
    base = {
        "run": run,
        "tag": rows[0]["model"],
        "digest": rows[0]["digest"],
        "cases": len(by_case),
        "latency_ms": {
            "median": statistics.median(latencies) if latencies else None,
            "p95": percentile(latencies, 0.95),
        },
    }
    if role == "planner":
        keys = (
            "intent_correct",
            "add_correct",
            "remove_correct",
            "replace_correct",
            "feature_ids_valid",
        )
        base.update(
            {
                "passed": sum(bool(row.get("pass")) for row in by_case.values()),
                "schema_passed": sum(bool(row.get("schema_valid")) for row in by_case.values()),
                "exact_components": {
                    key: sum(bool(row.get(key)) for row in by_case.values())
                    for key in keys
                    if any(key in row for row in by_case.values())
                },
                "fallback_or_repair": sum(
                    bool(row.get("fallback_or_repair")) for row in by_case.values()
                ),
                "hard_gates_pass": all(
                    row.get("schema_valid")
                    and row.get("citation_ids_valid", True)
                    and row.get("feature_ids_valid", True)
                    for row in by_case.values()
                ),
            }
        )
    elif role == "analyst":
        labels = ("full", "partial", "conflicting", "uncertain", "none")
        base.update(
            {
                "passed": sum(bool(row.get("pass")) for row in by_case.values()),
                "schema_passed": sum(bool(row.get("schema_valid")) for row in by_case.values()),
                "citation_passed": sum(bool(row.get("citation_valid")) for row in by_case.values()),
                "safe_fallbacks": sum(
                    row.get("outcome") == "safe_fallback" for row in by_case.values()
                ),
                "unsupported_claims": sum(
                    bool(row.get("unsupported_claim")) for row in by_case.values()
                ),
                "relation_confusion": {
                    label: {
                        "expected": sum(
                            row.get("expected_relation") == label for row in by_case.values()
                        ),
                        "exact": sum(
                            row.get("expected_relation") == label
                            and row.get("actual_relation") == label
                            and row.get("expected_unresolved") == row.get("actual_unresolved")
                            for row in by_case.values()
                        ),
                        "predicted": sum(
                            row.get("actual_relation") == label for row in by_case.values()
                        ),
                    }
                    for label in labels
                },
                "hard_gates_pass": all(
                    row.get("schema_valid")
                    and row.get("citation_valid")
                    and row.get("outcome") != "safe_fallback"
                    and not row.get("unsupported_claim")
                    for row in by_case.values()
                ),
            }
        )
    else:
        invented = sum(int(row.get("extra_facts", 0)) for row in by_case.values())
        predicted = sum(int(row.get("validated_fact_count", 0)) for row in by_case.values())
        matched = max(0, predicted - invented)
        protocol_failures = sum(
            row.get("status") == "protocol_or_runtime_failure" for row in by_case.values()
        )
        fixture_cases = read(ROOT / "eval/llm003/graph.jsonl")
        gold = (
            sum(len(case["expected"]) for case in fixture_cases)
            if run == "qwen_semantic_dto_v2_final_gold"
            else 25
        )
        positives = [case for case in fixture_cases if not case["negative"]]
        negatives = [case for case in fixture_cases if case["negative"]]
        negative_rows = [row for row in by_case.values() if row.get("gold_negative")]
        base.update(
            {
                "positive_cases": len(positives),
                "negative_cases": len(negatives),
                "matched_gold_facts": matched,
                "gold_facts": gold,
                "validated_facts": predicted,
                "invented_facts": invented,
                "precision": matched / predicted if predicted else 1.0,
                "recall": matched / gold if gold else 0.0,
                "negative_cases_passed": sum(bool(row.get("pass")) for row in negative_rows),
                "schema_and_provenance_passed": sum(
                    bool(row.get("schema_and_provenance_valid")) for row in by_case.values()
                ),
                "protocol_failures": protocol_failures,
                "hard_gates_pass": protocol_failures == 0
                and invented == 0
                and all(row.get("schema_and_provenance_valid") for row in by_case.values()),
            }
        )
    return base


def group_file(path: Path, role: str, run: str) -> list[dict]:
    if not path.exists():
        return []
    groups: dict[str, list[dict]] = {}
    for row in read(path):
        groups.setdefault(row["model"], []).append(row)
    return [summarize(group, role, run) for group in groups.values()]


def main() -> None:
    definitions = {
        "planner": [
            ("planner_candidate_warm.jsonl", "planner", "candidate_warm_historical"),
            ("planner_qwen_v2.jsonl", "planner", "qwen_prompt_v2"),
            ("planner_qwen_v3.jsonl", "planner", "qwen_semantic_dto_v3"),
        ],
        "analyst": [
            ("analyst_candidate_warm_low.jsonl", "analyst", "candidate_warm_historical"),
            ("analyst_lfm25_v2_low.jsonl", "analyst", "lfm25_prompt_v2"),
            ("analyst_lfm25_v3_low.jsonl", "analyst", "lfm25_semantic_dto_v3"),
            ("analyst_lfm25_v4_low.jsonl", "analyst", "lfm25_decision_order_v4"),
            ("analyst_lfm2_24b-a2b_v3_default.jsonl", "analyst", "lfm24_semantic_dto_v3"),
        ],
        "graph_extractor": [
            ("graph_candidate_warm.jsonl", "graph", "candidate_warm_historical"),
            ("graph_qwen_v2.jsonl", "graph", "qwen_semantic_dto_v2_pre_adjudication"),
            ("graph_qwen_v3.jsonl", "graph", "qwen_semantic_dto_v2_final_gold"),
        ],
    }
    results = {
        "schema_version": 2,
        "task": "LLM-003",
        "status": "open_no_safe_production_selection",
        "protocol": {
            "sequential": True,
            "gold_labels_model_generated": False,
            "latency_note": (
                "per-call/group wall latency; reliable tokens/sec, RSS, and swap attribution "
                "were not captured"
            ),
            "ollama_version": "0.34.4",
            "run_order": ["graph_extractor", "planner", "analyst"],
        },
        "gold": {
            "planner_cases": 30,
            "analyst_cases": 18,
            "graph_cases": 48,
            "graph_facts": 26,
            "provenance": "synthetic-CC0",
            "fixtures": "eval/llm003/",
        },
        "roles": {},
        "production_decision": {
            "planner": None,
            "analyst": None,
            "graph_extractor": None,
            "config_changed": False,
            "mass_backfill_allowed": False,
        },
    }
    for role, runs in definitions.items():
        results["roles"][role] = [
            item
            for filename, metric_role, run in runs
            for item in group_file(RAW / filename, metric_role, run)
        ]
    graph = next(
        item
        for item in results["roles"]["graph_extractor"]
        if item["run"] == "qwen_semantic_dto_v2_final_gold"
    )
    planner = next(
        item for item in results["roles"]["planner"] if item["run"] == "qwen_semantic_dto_v3"
    )
    analyst = next(
        item for item in results["roles"]["analyst"] if item["run"] == "lfm25_decision_order_v4"
    )
    results["status"] = "open_analyst_selection_pending"
    results["production_decision"].update(
        {
            "planner": {
                "tag": planner["tag"],
                "digest": planner["digest"],
                "prompt_version": "planner_v3",
                "profile": "non-thinking",
                "max_output_tokens": 384,
                "exact_cases": planner["passed"],
                "case_count": planner["cases"],
                "hard_gates_pass": planner["hard_gates_pass"],
            },
            "graph_extractor": {
                "tag": graph["tag"],
                "digest": graph["digest"],
                "extractor_version": "graph-extraction-v2",
                "profile": "non-thinking",
                "max_output_tokens": 384,
                "matched_gold_facts": graph["matched_gold_facts"],
                "gold_facts": graph["gold_facts"],
                "invented_facts": graph["invented_facts"],
                "hard_gates_pass": graph["hard_gates_pass"],
            },
            "analyst": None,
            "config_changed": True,
            "mass_backfill_allowed": False,
        }
    )
    results["production_decision"]["reason"] = (
        f"Planner Qwen v3 scored {planner['passed']}/30 exact and passes structural gates; "
        f"Analyst LFM2.5 v4 scored {analyst['passed']}/18 exact with "
        f"{analyst['safe_fallbacks']} safe fallbacks, so no Analyst is selected; "
        f"Graph Qwen on adjudicated gold matched "
        f"{graph['matched_gold_facts']}/{graph['gold_facts']} facts, "
        f"with {graph['invented_facts']} extra facts and "
        f"{graph['negative_cases_passed']}/{graph['negative_cases']} negative cases correct."
    )
    out = ROOT / "docs/validation/LLM-003/results.json"
    out.write_text(json.dumps(results, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(results, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
