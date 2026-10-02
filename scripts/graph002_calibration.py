"""Run the local GRAPH-002-CAL benchmark against the pinned Tev1 runtime."""

from __future__ import annotations

import argparse
import asyncio
import csv
import hashlib
import json
import os
from collections import Counter
from pathlib import Path
from typing import Any

import httpx
import yaml

from app.services.feature_equivalence_v2 import (
    CONTRACT_3_LABELS,
    CONTRACT_5_LABELS,
    CONTRACT_VERSION,
    FeatureEquivalenceClassifierV2,
    load_decision_cache,
    merge_eligible,
    safety_veto,
)

THRESHOLDS = (0.70, 0.75, 0.80, 0.85, 0.90, 0.95)
GOLD_LABELS = set(CONTRACT_5_LABELS)


def _prf(gold: list[str], predicted: list[str], label: str) -> dict[str, float | int]:
    tp = sum(g == label and p == label for g, p in zip(gold, predicted, strict=True))
    fp = sum(g != label and p == label for g, p in zip(gold, predicted, strict=True))
    fn = sum(g == label and p != label for g, p in zip(gold, predicted, strict=True))
    precision = tp / (tp + fp) if tp + fp else 0.0
    recall = tp / (tp + fn) if tp + fn else 0.0
    f1 = 2 * precision * recall / (precision + recall) if precision + recall else 0.0
    return {"precision": precision, "recall": recall, "f1": f1, "support": tp + fn}


def evaluate(gold: list[str], predicted: list[str], labels: tuple[str, ...]) -> dict[str, Any]:
    if not gold or len(gold) != len(predicted):
        raise ValueError("benchmark requires equally sized non-empty gold and predictions")
    matrix = {g: {p: 0 for p in labels} for g in labels}
    for g, p in zip(gold, predicted, strict=True):
        matrix[g][p] += 1
    per_class = {label: _prf(gold, predicted, label) for label in labels}
    accuracy = sum(g == p for g, p in zip(gold, predicted, strict=True)) / len(gold)
    macro_f1 = sum(float(metric["f1"]) for metric in per_class.values()) / len(labels)
    false_merge_count = sum(
        p == "SAME" and g != "SAME" for g, p in zip(gold, predicted, strict=True)
    )
    return {
        "count": len(gold),
        "class_distribution": dict(Counter(gold)),
        "accuracy": accuracy,
        "macro_f1": macro_f1,
        "per_class": per_class,
        "same_precision": per_class["SAME"]["precision"],
        "same_recall": per_class["SAME"]["recall"],
        "same_f1": per_class["SAME"]["f1"],
        "false_merge_count": false_merge_count,
        "false_merge_rate": false_merge_count / len(gold),
        "confusion_matrix": matrix,
    }


def threshold_sweep(rows: list[dict[str, Any]], contract: str) -> list[dict[str, Any]]:
    if contract == "3-class":
        gold = [
            "DIFFERENT"
            if row["gold_label"] in {"RELATED", "BROADER_NARROWER"}
            else row["gold_label"]
            for row in rows
        ]
    else:
        gold = [row["gold_label"] for row in rows]
    sweep = []
    for threshold in THRESHOLDS:
        accepted = [
            (row, gold_label)
            for row, gold_label in zip(rows, gold, strict=True)
            if row[f"{contract}_decision"] == "SAME"
            and float(row[f"{contract}_probabilities"]["SAME"]) >= threshold
        ]
        false_merges = sum(gold_label != "SAME" for _, gold_label in accepted)
        true_merges = len(accepted) - false_merges
        vetoes = sum(
            merge_eligible(
                decision="SAME",
                same_probability=float(row[f"{contract}_probabilities"]["SAME"]),
                threshold=threshold,
                feature_a=row["feature_a"],
                feature_b=row["feature_b"],
            )[1]
            is not None
            for row, _ in accepted
        )
        safety_false_merges = sum(
            label != "SAME"
            and (
                row.get("safety_critical", "false").casefold() == "true"
                or safety_veto(row["feature_a"], row["feature_b"]) is not None
            )
            for row, label in accepted
        )
        sweep.append(
            {
                "threshold": threshold,
                "same_precision": true_merges / len(accepted) if accepted else 0.0,
                "same_recall": true_merges / sum(label == "SAME" for label in gold)
                if any(label == "SAME" for label in gold)
                else 0.0,
                "accepted_same_count": len(accepted),
                "false_merge_count": false_merges,
                "safety_veto_count": vetoes,
                "safety_critical_false_same_count": safety_false_merges,
            }
        )
    return sweep


def _load_gold(path: Path) -> tuple[list[dict[str, Any]], str]:
    raw = path.read_bytes()
    with path.open(encoding="utf-8-sig", newline="") as handle:
        source = list(csv.DictReader(handle))
    rows = [row for row in source if row.get("gold_label", "").strip()]
    for row in rows:
        if row["gold_label"] not in GOLD_LABELS:
            raise ValueError(f"invalid gold label: {row['gold_label']}")
    if len(rows) < 120:
        raise ValueError(f"gold benchmark has only {len(rows)} labeled pairs; minimum is 120")
    return rows, hashlib.sha256(raw).hexdigest()


async def _run(args: argparse.Namespace) -> int:
    rows, gold_hash = _load_gold(Path(args.gold))
    config = yaml.safe_load(Path(args.model_config).read_text(encoding="utf-8"))
    model = config["generation"]["relation_classifier"]
    if model["model_id"] != "tev1:4b":
        raise ValueError("calibration is pinned to the existing tev1:4b model")
    base_url = os.getenv("INFERENCE_BASE_URL", "http://127.0.0.1:11434").rstrip("/")
    output_path = Path(args.decisions)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    prior = load_decision_cache(output_path)
    async with httpx.AsyncClient(base_url=base_url) as client:
        tags = await client.get("/api/tags", timeout=10)
        tags.raise_for_status()
        installed = next(
            (
                item
                for item in tags.json().get("models", [])
                if item.get("name") == model["model_id"]
            ),
            None,
        )
        if installed is None or installed.get("digest") != model["digest"]:
            raise ValueError("installed Tev1 model digest does not match config/models.yaml")
        classifier = FeatureEquivalenceClassifierV2(
            client, model_id=model["model_id"], digest=model["digest"]
        )
        with output_path.open("a", encoding="utf-8", newline="") as sink:
            for contract in ("3-class", "5-class"):
                for index, row in enumerate(rows, 1):
                    key = (contract, row["feature_a"], row["feature_b"])
                    if key in prior:
                        continue
                    result = await classifier.classify(
                        feature_a=row["feature_a"],
                        feature_b=row["feature_b"],
                        context_a=row.get("context_a", ""),
                        context_b=row.get("context_b", ""),
                        contract=contract,  # type: ignore[arg-type]
                        request_id=f"graph002-cal-{contract}-{index}",
                        timeout=args.timeout,
                    )
                    item = {
                        "contract": contract,
                        "contract_version": CONTRACT_VERSION,
                        "feature_a": row["feature_a"],
                        "feature_b": row["feature_b"],
                        "decision": result.decision,
                        "probabilities": result.probabilities,
                        "confidence": result.confidence,
                        "latency_ms": result.latency_ms,
                    }
                    sink.write(json.dumps(item, ensure_ascii=False) + "\n")
                    sink.flush()
                    prior[key] = item
                    if index % 10 == 0:
                        print(f"{contract}: {index}/{len(rows)} pairs classified", flush=True)

    by_pair = {(r["feature_a"], r["feature_b"]): r for r in rows}
    merged_rows: list[dict[str, Any]] = []
    for key, row in by_pair.items():
        entry = dict(row)
        for contract in ("3-class", "5-class"):
            item = prior[(contract, *key)]
            entry[f"{contract}_decision"] = item["decision"]
            entry[f"{contract}_probabilities"] = item["probabilities"]
            entry[f"{contract}_confidence"] = item["confidence"]
        merged_rows.append(entry)

    gold_3 = [
        "DIFFERENT" if row["gold_label"] in {"RELATED", "BROADER_NARROWER"} else row["gold_label"]
        for row in merged_rows
    ]
    pred_3 = [row["3-class_decision"] for row in merged_rows]
    gold_5 = [row["gold_label"] for row in merged_rows]
    pred_5 = [row["5-class_decision"] for row in merged_rows]
    result = {
        "contract_version": CONTRACT_VERSION,
        "model_id": model["model_id"],
        "model_digest": model["digest"],
        "gold_set_sha256": gold_hash,
        "labeled_pairs": len(merged_rows),
        "benchmark_3class": evaluate(gold_3, pred_3, CONTRACT_3_LABELS),
        "benchmark_5class": evaluate(gold_5, pred_5, CONTRACT_5_LABELS),
        "threshold_sweep_3class": threshold_sweep(merged_rows, "3-class"),
        "threshold_sweep_5class": threshold_sweep(merged_rows, "5-class"),
    }
    eligible_contracts = []
    for contract, metric_key, sweep_key in (
        ("3-class", "benchmark_3class", "threshold_sweep_3class"),
        ("5-class", "benchmark_5class", "threshold_sweep_5class"),
    ):
        eligible = [
            row
            for row in result[sweep_key]
            if row["same_precision"] >= 0.95 and row["safety_critical_false_same_count"] == 0
        ]
        if eligible:
            eligible_contracts.append((contract, result[metric_key], eligible[0]))
    if eligible_contracts:
        eligible_contracts.sort(
            key=lambda item: (
                float(item[1]["same_precision"]),
                -int(item[1]["false_merge_count"]),
                float(item[1]["same_recall"]),
                float(item[1]["macro_f1"]),
            ),
            reverse=True,
        )
        selected_contract, selected_metrics, selected_threshold = eligible_contracts[0]
        gate_passed = True
        selection_reason = (
            "Passed threshold gate; selected by SAME precision, false merges, recall, "
            "then macro F1."
        )
    else:
        fallback = [
            ("3-class", result["benchmark_3class"]),
            ("5-class", result["benchmark_5class"]),
        ]
        fallback.sort(
            key=lambda item: (
                float(item[1]["same_precision"]),
                -int(item[1]["false_merge_count"]),
                float(item[1]["same_recall"]),
                float(item[1]["macro_f1"]),
            ),
            reverse=True,
        )
        selected_contract, selected_metrics = fallback[0]
        selected_threshold = None
        gate_passed = False
        selection_reason = (
            "Neither contract meets SAME precision >= 0.95 with zero safety-critical false merges; "
            "selected the higher-scoring benchmark by SAME precision, false merges, "
            "recall, then macro F1."
        )
    labels = CONTRACT_3_LABELS if selected_contract == "3-class" else CONTRACT_5_LABELS
    selected_json = {
        "contract_version": CONTRACT_VERSION,
        "selected_contract": selected_contract,
        "labels": list(labels),
        "prompt_criteria_version": "feature-equivalence-v2-strict-2026-10-02",
        "gold_set_sha256": gold_hash,
        "metrics": selected_metrics,
        "threshold_policy": (
            "model decision == SAME AND P(SAME) >= threshold; confidence is recorded "
            "but not thresholded"
        ),
        "selected_threshold": selected_threshold["threshold"] if selected_threshold else None,
        "threshold_metrics": selected_threshold,
        "acceptance_gate_passed": gate_passed,
        "selection_reason": selection_reason,
    }
    result["selected_contract"] = selected_json
    Path(args.report_3).write_text(
        json.dumps(
            {
                "metrics": result["benchmark_3class"],
                "threshold_sweep": result["threshold_sweep_3class"],
            },
            indent=2,
        ),
        encoding="utf-8",
    )
    Path(args.report_5).write_text(
        json.dumps(
            {
                "metrics": result["benchmark_5class"],
                "threshold_sweep": result["threshold_sweep_5class"],
            },
            indent=2,
        ),
        encoding="utf-8",
    )
    Path(args.summary).write_text(json.dumps(result, indent=2), encoding="utf-8")
    Path(args.selected_contract).write_text(json.dumps(selected_json, indent=2), encoding="utf-8")
    comparison = [
        "# GRAPH-002-CAL benchmark comparison",
        "",
        f"Gold set: {len(merged_rows)} labeled pairs; SHA-256 `{gold_hash}`.",
        "",
        "| Metric | Strict 3-class | 5-class |",
        "|---|---:|---:|",
    ]
    for key, title in (
        ("accuracy", "Accuracy"),
        ("macro_f1", "Macro F1"),
        ("same_precision", "SAME precision"),
        ("same_recall", "SAME recall"),
        ("same_f1", "SAME F1"),
        ("false_merge_count", "False merges"),
    ):
        comparison.append(
            f"| {title} | {result['benchmark_3class'][key]} | {result['benchmark_5class'][key]} |"
        )
    comparison.extend(
        [
            "",
            f"Selected: **{selected_contract}**. Acceptance gate: "
            f"**{'passed' if gate_passed else 'failed'}**.",
            f"Reason: {selection_reason}",
            "",
            "The threshold applies only to `P(SAME)` after the predicted label is SAME. "
            "Model confidence is recorded for diagnostics and is not a second threshold.",
            "",
            "## Threshold sweeps",
            "",
        ]
    )
    for contract, sweep_key in (
        ("3-class", "threshold_sweep_3class"),
        ("5-class", "threshold_sweep_5class"),
    ):
        comparison.extend(
            [
                f"### {contract}",
                "",
                "| P(SAME) threshold | Precision | Recall | Accepted SAME | False merges | "
                "Safety-critical false SAME |",
                "|---:|---:|---:|---:|---:|---:|",
            ]
        )
        for item in result[sweep_key]:
            comparison.append(
                f"| {item['threshold']:.2f} | {item['same_precision']:.3f} | "
                f"{item['same_recall']:.3f} | {item['accepted_same_count']} | "
                f"{item['false_merge_count']} | {item['safety_critical_false_same_count']} |"
            )
        comparison.append("")
    Path(args.comparison).write_text("\n".join(comparison), encoding="utf-8")
    for contract in ("3-class", "5-class"):
        gold = gold_3 if contract == "3-class" else gold_5
        pred = pred_3 if contract == "3-class" else pred_5
        with Path(args.errors_3 if contract == "3-class" else args.errors_5).open(
            "w", encoding="utf-8-sig", newline=""
        ) as handle:
            writer = csv.DictWriter(
                handle,
                fieldnames=[
                    "feature_a",
                    "feature_b",
                    "gold_label",
                    "prediction",
                    "same_probability",
                    "confidence",
                    "notes",
                ],
            )
            writer.writeheader()
            for row, g, p in zip(merged_rows, gold, pred, strict=True):
                if g != p:
                    writer.writerow(
                        {
                            "feature_a": row["feature_a"],
                            "feature_b": row["feature_b"],
                            "gold_label": g,
                            "prediction": p,
                            "same_probability": row[f"{contract}_probabilities"]["SAME"],
                            "confidence": row[f"{contract}_confidence"],
                            "notes": row.get("notes", ""),
                        }
                    )
    with Path(args.safety_audit).open("w", encoding="utf-8-sig", newline="") as handle:
        writer = csv.DictWriter(
            handle,
            fieldnames=[
                "feature_a",
                "feature_b",
                "safety_reason",
                "gold_label",
                "3-class_decision",
                "3-class_same_probability",
                "5-class_decision",
                "5-class_same_probability",
            ],
        )
        writer.writeheader()
        for row in merged_rows:
            reason = safety_veto(row["feature_a"], row["feature_b"])
            if reason is None:
                continue
            writer.writerow(
                {
                    "feature_a": row["feature_a"],
                    "feature_b": row["feature_b"],
                    "safety_reason": reason,
                    "gold_label": row["gold_label"],
                    "3-class_decision": row["3-class_decision"],
                    "3-class_same_probability": row["3-class_probabilities"]["SAME"],
                    "5-class_decision": row["5-class_decision"],
                    "5-class_same_probability": row["5-class_probabilities"]["SAME"],
                }
            )
    print(json.dumps(result, indent=2), flush=True)
    return 0


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--gold", default="docs/validation/GRAPH-002-CAL/gold_pairs.csv")
    parser.add_argument(
        "--decisions", default="docs/validation/GRAPH-002-CAL/model_decisions.jsonl"
    )
    parser.add_argument("--summary", default="docs/validation/GRAPH-002-CAL/benchmark_summary.json")
    parser.add_argument("--report-3", default="docs/validation/GRAPH-002-CAL/benchmark_3class.json")
    parser.add_argument("--report-5", default="docs/validation/GRAPH-002-CAL/benchmark_5class.json")
    parser.add_argument("--errors-3", default="docs/validation/GRAPH-002-CAL/errors_3class.csv")
    parser.add_argument("--errors-5", default="docs/validation/GRAPH-002-CAL/errors_5class.csv")
    parser.add_argument("--safety-audit", default="docs/validation/GRAPH-002-CAL/safety_audit.csv")
    parser.add_argument(
        "--selected-contract", default="docs/validation/GRAPH-002-CAL/selected_contract.json"
    )
    parser.add_argument("--comparison", default="docs/validation/GRAPH-002-CAL/comparison.md")
    parser.add_argument("--model-config", default="config/models.yaml")
    parser.add_argument("--timeout", type=float, default=120)
    args = parser.parse_args()
    raise SystemExit(asyncio.run(_run(args)))


if __name__ == "__main__":
    main()
