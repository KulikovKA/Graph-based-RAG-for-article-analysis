# LLM-005 — Tev1 Analyst relation benchmark

Status: **complete, Phase A only**. Tev1 scored 15/18 (83.3%), below the
17/18 integration gate. The benchmark is complete and documented; production
Analyst architecture, model configuration, and model inventory were not changed.

## Runtime and model

Ollama was already at 0.35.0 before the task and remained at 0.35.0; no runtime
upgrade was needed. The active application topology uses host Ollama at
`http://host.docker.internal:11434`. No Ollama container was active in the
Compose stack, and its `ollama/ollama:0.34.1` image was left unchanged.

The requested `ollama pull tev1:4b` completed successfully after one retry for
an `unexpected EOF`; the retry resumed the partial layer and Ollama verified
the digest. The exact installed model is:

| Field | Value |
|---|---|
| Tag | `tev1:4b` |
| Digest | `cef45ef93cf6df8bf32bdd689b0a8fd01f88ae9034d33ce890c54f77e4cd981e` |
| Size | 4,482,415,847 bytes (listed as 4.5 GB) |
| Architecture / family | `qwen35` |
| Parameters | 4.2B |
| Quantization | `Q8_0` |
| Model context length | 262,144 |
| Ollama `num_ctx` default / observed runner context | 2,050 |

Weights remain in the Ollama cache and are not in Git.

## Method

The frozen 18-case fixture is `eval/llm003/analyst.jsonl`; its SHA-256 and the
cross-checked Analyst prompt hash are recorded in `results.json`. Gold labels
and existing fixture meanings were not changed. Each case made one sequential
`POST /v1/systemone` request. The ordinary chat endpoint was not used.

The state contains only the feature ID/text/language and the evidence ID/exact
quote. State size was 188–325 UTF-8 bytes; SystemOne reported 276–295 input
tokens (median 280.5), including the decision question and options. No case was
truncated. Every frozen case has one feature and one evidence quote, so no
multi-evidence aggregation was needed. The request carries no sampling or
thinking option; SystemOne returns a direct choice and score distribution.

The rubric is versioned `relation-rubric-v1` and preserves the frozen Analyst
distinction: relevant evidence with an unreported/ambiguous result is
`uncertain`; `none` is unrelated evidence. Confidence is distribution
concentration, not calibrated correctness probability. No confidence threshold
was applied.

Per-case labels, all five probabilities, confidence, response token count,
latency, state size, model digest, errors, and truncation status are in
[`raw/tev1_classifier.jsonl`](raw/tev1_classifier.jsonl). Machine-readable
metrics and the full rubric are in [`results.json`](results.json). No prompts,
raw responses, or hidden reasoning are stored.

## Results

| Gold label | Correct / cases | Accuracy |
|---|---:|---:|
| `full` | 5 / 5 | 100% |
| `partial` | 2 / 4 | 50% |
| `conflicting` | 4 / 4 | 100% |
| `uncertain` | 3 / 4 | 75% |
| `none` | 1 / 1 | 100% |
| **Total** | **15 / 18** | **83.3%** |

Confusion matrix (rows are gold, columns predicted):

| Gold \ Predicted | full | partial | conflicting | uncertain | none |
|---|---:|---:|---:|---:|---:|
| full | 5 | 0 | 0 | 0 | 0 |
| partial | 0 | 2 | 1 | 1 | 0 |
| conflicting | 0 | 0 | 4 | 0 | 0 |
| uncertain | 0 | 0 | 1 | 3 | 0 |
| none | 0 | 0 | 0 | 0 | 1 |

There were zero protocol errors. Median classification latency was 5,127 ms;
p95 was 7,854 ms (nearest-rank sample percentile). Median input was 280.5
tokens. The first measured request took 7,854 ms; there was no separate warmup.
These classifier-only timings are well below the historical GPT-OSS medium
baseline (about 62.7 s median / 176.7 s p95), but are not combined Analyst
latency and are not an E2E comparison.

The classifier-only relation score is 15/18 versus 13/18 for the LLM-004
GPT-OSS medium Analyst run and 11/18 for GPT-OSS low. This is useful context,
not a like-for-like architecture comparison: Tev1 produced only a relation
label, while GPT-OSS produced the full validated Analyst result. In either
case, Tev1 remains below its required 17/18 gate.

### Requested hard cases

| Case | Gold | Tev1 | Result |
|---|---|---|---|
| AN-04 | uncertain | uncertain | correct |
| AN-06 | partial | partial | correct |
| AN-08 | uncertain | conflicting | incorrect |
| AN-10 | partial | conflicting | incorrect |
| AN-16 | uncertain | uncertain | correct |

The LLM-004 `gpt-oss:20b / low` run failed seven cases: AN-01, AN-04, AN-06,
AN-08, AN-10, AN-12, and AN-16. Tev1 fixed five of those seven; it still
misclassified AN-08 and AN-10, and introduced a miss on AN-02. Complete
per-case comparisons are in `results.json`.

Confidence did not separate correct and incorrect predictions usefully: the
correct cases had median 0.753 (range 0.239–0.967); the three incorrect cases
had median 0.705 (range 0.487–0.939). In particular, an incorrect answer had
0.939 confidence. No threshold is justified by this sample.

## Gate decision

The required minimum is 17/18. Tev1 reached 15/18, so Phase B was not run.
There is no Tev1 + GPT-OSS E2E score or combined latency measurement. E2E
schema, citation, fallback, unsupported-claim, and privacy gates are therefore
not newly measured here; LLM-004's historical hard-gate results remain
unchanged.

Production config and architecture stay on the existing Analyst path. Do not
promote this Tev1 candidate. Future classifier work should focus on the
partial/uncertain boundary and mixed-language cases, then rerun a frozen
benchmark before considering integration.

## Checks

- `python -m pytest -q` — passed; environment-gated integrations skipped where
  dedicated test services were not configured.
- `python -m ruff check scripts/tev1_relation_benchmark.py tests/unit/test_tev1_relation_benchmark.py` — passed.
- `python -m mypy scripts/tev1_relation_benchmark.py tests/unit/test_tev1_relation_benchmark.py` — passed.
- `python -m pytest tests/integration -ra` — 25 passed, 36 skipped because
  `TEST_DATABASE_URL`, `TEST_QDRANT_URL`, `TEST_NEO4J_*`, and `TEST_OLLAMA_URL`
  are not configured.
- `git diff --check` — passed (Git reported the repository's normal LF/CRLF
  working-copy warning for `TASKS.md`).
