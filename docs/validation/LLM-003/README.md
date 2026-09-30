# LLM-003 — production model selection

Status: **blocked before comparative benchmark; no production model changes made**.
Recorded 2026-09-30 on the configured Windows 11 host. This report is a gate
assessment, not a model-quality result. Mass corpus backfill must remain blocked.

## Contracts reviewed

The benchmark targets the existing `PlannerV1` and `IntentPlanner` in
`src/app/domain/planner.py`, `AnalysisV1` and `Analyst` in
`src/app/services/analyst.py`, and the `InferenceGraphExtractor` plus
`GraphIndexingService` contract in `src/app/services/graph_index.py`. Prompts,
schemas, repair/fallback behavior and citation provenance must remain identical
for all candidates. Planner measures intent/patch validity and ID discipline;
Analyst measures schema, feature matching, relations, citation membership and
Unicode spans; graph extraction measures allowlisted facts, exact quotes and
Unicode offsets. Structural validation alone does not establish semantic
faithfulness.

## Host and runtime gate

- Windows 11 Pro, AMD64 Family 25 Model 117, about 3.8 GHz; 32,061 MB physical
  memory. GPU acceleration was not established by this inspection.
- Ollama 0.34.4; active project Compose services are healthy.
- At inspection: 13,634 MB available physical memory; virtual memory committed
  37,516 MB of 40,588 MB, with 3,072 MB available.
- LLM-002 measured Gemma 4 26B Analyst peak RSS at 20.6 GB and host swap at
  5.32 GB warm. This host currently has less available memory than that RSS
  alone. The 24B candidate is a 14.4 GB Q4_K_M artifact. Sequential candidate
  comparisons with cold/warm and role switching cannot be treated as safe or
  representative until the host is drained/restarted and enough memory headroom
  is demonstrated.

## Candidate inventory observed locally

Digests are local Ollama registry digests at inspection. Disk size is not RAM
usage. Exact tags and digests are recorded in `results.json`.

| Role | Candidate | Local observation |
|---|---|---|
| Planner | `granite4.2:3b` | available, 3.7B, Q4_K_M |
| Planner | `qwen3.5:4b-q4_K_M` | available, 4.7B, Q4_K_M |
| Planner/reference | `lfm2.5:8b-a1b-q4_K_M` | available, 8.5B, Q4_K_M; prior LLM-002 schema smoke only |
| Analyst | `lfm2.5:8b-a1b-q4_K_M` | available; prior smoke does not compare AnalysisV1 quality |
| Analyst | `lfm2:24b-a2b` | available, 23.8B, Q4_K_M; local tag used for the requested LFM2-24B-A2B candidate |
| Analyst/reference | `gemma4:26b-a4b-it-mtp-q4_K_M` | available; prior LLM-002 CPU smoke, not comparative quality evidence |
| Graph extractor | `granite4.2:3b` | available |
| Graph extractor | `qwen3.5:4b-q4_K_M` | available |
| Graph extractor | `lfm2.5:8b-a1b-q4_K_M` | available |

## Why no candidate is selected

The repository has only `eval/cases/dev_smoke.jsonl`; it is not the required
versioned three-role gold dataset with RU/EN/mixed splits, per-case labels,
provenance, dev/holdout separation and deterministic scoring. A benchmark on
that smoke fixture would not support the hard gates in TASKS.md. No comparative
case runs were executed, so all quality and latency scores are null in
`results.json`. Existing LLM-002 measurements remain untouched and are not
relabelled as LLM-003.

The acceptance threshold is not to nominate the fastest model. First prepare
and review the gold dataset, freeze the identical prompts/schemas/inputs and
protocol, define per-case gates and error/timeout limits, and measure RSS plus
host/container memory and swap across cold/warm runs and Planner↔Analyst
switches. Select each role independently only from candidates that pass every
hard gate. If the available RAM headroom cannot safely support those runs,
perform them on a suitably provisioned target host. Until then retain the
existing `config/models.yaml` identities and do not start CORPUS-001.

## Acceptance checklist

- [ ] Versioned, provenance-backed gold cases for all three roles, with RU/EN/mixed coverage and held-out cases.
- [ ] Frozen prompts, schemas, case IDs, runtime, hardware, timeouts/output budgets and warm/cold protocol.
- [ ] Deterministic per-case scoring and thresholds fixed before model runs.
- [ ] All required candidates run through the real role implementations and graph fact validation.
- [ ] Hard schema/citation/graph-fact/privacy/error gates pass; latency and resource figures are measured.
- [ ] Independent production choices and exact versions recorded; inventory/config updated only after evidence.
- [x] Existing LLM-002 artifacts preserved.
