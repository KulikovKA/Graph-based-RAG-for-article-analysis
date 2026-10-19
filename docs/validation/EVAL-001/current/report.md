# EVAL-001 — offline regression report

Profile: `fixture-contract-replay`. Run: `3e7cf5f0-fecf-42d1-9a5a-8872d6b9cb99`.

Fixture profile проверяет lexical fallback и deterministic Analyst fallback. Это не baseline качества production-моделей и не EVAL-002.

Judge: disabled. Без judge semantic faithfulness = N/A.
Latency gate: UNSET. Модель, RAM, TTFT, tokens и browser timings в fixture не измеряются.

| Case | Outcome | Recall@10 | Citations | Errors |
|---|---|---|---|---|
| EVAL000-DEV-001 | safe_fallback | 1.0 | 1.0 | — |
| EVAL000-DEV-002 | safe_fallback | 1.0 | 1.0 | — |
| EVAL000-DEV-003 | safe_fallback | 1.0 | 1.0 | — |
| EVAL000-DEV-004 | safe_fallback | 1.0 | 1.0 | — |
| EVAL000-DEV-005 | safe_fallback | 1.0 | 1.0 | — |
| EVAL000-DEV-006 | safe_fallback | 1.0 | 1.0 | — |
| EVAL000-DEV-007 | safe_fallback | 0.5 | 1.0 | — |
| EVAL000-DEV-008 | safe_fallback | 0.5 | 1.0 | — |
| EVAL000-DEV-009 | no_evidence | N/A | N/A | — |
| EVAL000-DEV-010 | safe_fallback | 1.0 | 1.0 | — |

## Summary

```json
{
  "cases": 10,
  "passed": 10,
  "recall_at_10": 0.8888888888888888,
  "mrr": 1.0,
  "citation_validity": 1.0,
  "citation_denominator": 19,
  "citation_na_cases": 1,
  "faithfulness": null,
  "judge_evaluated_cases": 0,
  "latency_p50_ms": null,
  "latency_p95_ms": null,
  "latency_gate": "UNSET",
  "planner_accuracy": null,
  "planner_reason": "EVAL000_HAS_NO_PLANNER_GOLD",
  "failure_rate": 0.0
}
```

## Baseline diff

```json
{
  "regressions": [],
  "metric_deltas": {
    "recall_at_10": 0.0,
    "faithfulness": null
  },
  "per_case": [
    {
      "case_id": "EVAL000-DEV-001",
      "previous_errors": [],
      "current_errors": [],
      "previous_outcome": "safe_fallback",
      "current_outcome": "safe_fallback",
      "recall_delta": 0.0
    },
    {
      "case_id": "EVAL000-DEV-002",
      "previous_errors": [],
      "current_errors": [],
      "previous_outcome": "safe_fallback",
      "current_outcome": "safe_fallback",
      "recall_delta": 0.0
    },
    {
      "case_id": "EVAL000-DEV-003",
      "previous_errors": [],
      "current_errors": [],
      "previous_outcome": "safe_fallback",
      "current_outcome": "safe_fallback",
      "recall_delta": 0.0
    },
    {
      "case_id": "EVAL000-DEV-004",
      "previous_errors": [],
      "current_errors": [],
      "previous_outcome": "safe_fallback",
      "current_outcome": "safe_fallback",
      "recall_delta": 0.0
    },
    {
      "case_id": "EVAL000-DEV-005",
      "previous_errors": [],
      "current_errors": [],
      "previous_outcome": "safe_fallback",
      "current_outcome": "safe_fallback",
      "recall_delta": 0.0
    },
    {
      "case_id": "EVAL000-DEV-006",
      "previous_errors": [],
      "current_errors": [],
      "previous_outcome": "safe_fallback",
      "current_outcome": "safe_fallback",
      "recall_delta": 0.0
    },
    {
      "case_id": "EVAL000-DEV-007",
      "previous_errors": [],
      "current_errors": [],
      "previous_outcome": "safe_fallback",
      "current_outcome": "safe_fallback",
      "recall_delta": 0.0
    },
    {
      "case_id": "EVAL000-DEV-008",
      "previous_errors": [],
      "current_errors": [],
      "previous_outcome": "safe_fallback",
      "current_outcome": "safe_fallback",
      "recall_delta": 0.0
    },
    {
      "case_id": "EVAL000-DEV-009",
      "previous_errors": [],
      "current_errors": [],
      "previous_outcome": "no_evidence",
      "current_outcome": "no_evidence",
      "recall_delta": null
    },
    {
      "case_id": "EVAL000-DEV-010",
      "previous_errors": [],
      "current_errors": [],
      "previous_outcome": "safe_fallback",
      "current_outcome": "safe_fallback",
      "recall_delta": 0.0
    }
  ]
}
```
