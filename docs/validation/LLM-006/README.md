# LLM-006 — decomposed classification and Analyst integration

## Decision

The one-request four-question decomposed experiment returned **6/18** with four
logically inconsistent response sets. The agreed selection rule therefore
keeps the simpler five-label single-stage Tev1 classifier at its frozen **15/18**
baseline. The per-question assembly algorithm rejects contradictory support
decisions and otherwise uses `conflicting > full > partial > uncertain > none`.
No inconsistent combination is silently repaired.

The frozen source is `eval/llm003/analyst.jsonl` (18 cases). Labels, evidence,
and historical LLM-004/005 measurements were not changed. The baseline raw
records remain in LLM-005; this task's experiment and integration runs are in
[`raw/`](raw/).

## Classifier experiment

| Gold | Correct / cases | Accuracy |
|---|---:|---:|
| full | 0 / 5 | 0% |
| partial | 3 / 4 | 75% |
| conflicting | 1 / 4 | 25% |
| uncertain | 1 / 4 | 25% |
| none | 1 / 1 | 100% |
| **Total** | **6 / 18** | **33.3%** |

Decomposed confusion matrix (gold rows, predicted columns):

| Gold \ Predicted | full | partial | conflicting | uncertain | none |
|---|---:|---:|---:|---:|---:|
| full | 0 | 5 | 0 | 0 | 0 |
| partial | 0 | 3 | 0 | 0 | 0 |
| conflicting | 0 | 0 | 1 | 0 | 0 |
| uncertain | 0 | 1 | 1 | 1 | 1 |
| none | 0 | 0 | 0 | 0 | 1 |

The classifier made one request per case, 18 calls total. Median latency was
6,479 ms and p95 was 7,378 ms. Four responses violated deterministic
consistency (`contradiction=yes` together with a support decision) and were
counted as incorrect. Full per-question probabilities, confidence values,
decisions, and errors are recorded in
[`raw/decomposed_classifier.jsonl`](raw/decomposed_classifier.jsonl).

## Selected single-stage classifier

The unchanged LLM-005 single-stage Tev1 benchmark scored 15/18: full 5/5,
partial 2/4, conflicting 4/4, uncertain 3/4, none 1/1. Its median/p95
classifier latency was 5,127/7,854 ms with one request per case. The model is
`tev1:4b`, digest
`cef45ef93cf6df8bf32bdd689b0a8fd01f88ae9034d33ce890c54f77e4cd981e`.

| Case | Gold | Selected classifier |
|---|---|---|
| AN-02 | partial | uncertain |
| AN-08 | uncertain | conflicting |
| AN-10 | partial | conflicting |

The selected output probabilities and full confusion matrix are preserved in
[`LLM-005 results`](../LLM-005/results.json).

## Production Analyst path

`generation.relation_classifier` is now a separate pinned config role using
Ollama `/v1/systemone`, `tev1:4b`, no thinking, and contract
`relation-classifier-v1`. It owns each feature/document relation. GPT-OSS 20B
at low effort returns `AnalystNarrativeDraft`, whose schema contains no
relation field. Deterministic assembly joins its exact quote selections to the
classifier decisions, computes unresolved IDs, adds offsets, and validates
`AnalysisV1`. Classifier timeout, unavailable service, or malformed output
causes whole-pipeline safe fallback; there is no GPT relation fallback.

Production config and pinned metadata are in `config/models.yaml` and
`docs/model_inventory.json`; architecture details are in
[`docs/ARCHITECTURE.md`](../../ARCHITECTURE.md).

## E2E results

The frozen 18-case full-pipeline run is in [`results.json`](results.json), with
per-case aggregate records in [`raw/e2e.jsonl`](raw/e2e.jsonl). It reports
semantic score, schema/citation/fallback/unsupported/privacy gates, confusion
matrix, and measured combined latency of **33,324 ms median / 38,832 ms p95**.
The E2E score is **15/18**, matching the selected classifier. The E2E per-class
accuracy is full 5/5, partial 2/4, conflicting 4/4, uncertain 3/4, none 1/1.
All hard gates pass: schema 18/18, citations 18/18, fallback 0, unsupported 0,
reasoning leak 0. Both cases classified as `partial` by the selected classifier
(AN-06 and AN-14) remain `partial` in the assembled AnalysisV1.

Historical GPT-OSS low standalone
timing from LLM-004 is 26,999 ms median / 88,412 ms p95; GPT-OSS medium is
approximately 62.7 s / 176.7 s. LLM-004 records are historical and were not
rewritten.

The initial E2E attempt with a different classifier state shape is retained as
`raw/e2e_initial.jsonl` and marked as superseded in machine results. The final
benchmark result is the one in `raw/e2e.jsonl`.

The protocol's opaque state IDs are retained from the evidence source, as in
the frozen LLM-005 request contract. A generic placeholder-ID control scored
13/18 and is recorded in `single_stage_text_results.json`; the classifier and
E2E run use stable source IDs. `raw/e2e_uuid_state.jsonl` and
`raw/e2e_external_id_prior_rubric.jsonl` are diagnostic runs superseded by the
selected run. The latter is partial and stops after six cases.
