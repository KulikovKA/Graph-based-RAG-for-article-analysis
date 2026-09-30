# LLM-003 — comparative local model evaluation

Status: **comparative runs recorded; production selection remains open**. No model
configuration was changed and `CORPUS-001` must not start.

## Gold fixtures and scoring

Fixtures are deterministic JSONL with stable case IDs, explicit labels, and
`synthetic-CC0` provenance. The Planner set has 30 cases, Analyst 18, and Graph
extractor 48. They cover English, Russian, and mixed language, plus planner
intent/patch/UUID/follow-up behavior, AnalysisV1 relation and citation cases,
and positive, negative, adversarial, and Unicode-offset graph cases. Labels are
fixture-authored and never produced by the evaluated model. `EVAL-000/dev_smoke`
informed applicable patterns; it is not scored as gold.

The runner exercises the repository's real Planner, Analyst, graph extractor,
and graph validator. Scores are deterministic exact-label/contract checks, not
LLM-as-judge. See [fixtures](../../../eval/llm003/) and the per-case
[raw results](raw/).

## Protocol

All model runs were sequential against local Ollama 0.34.4 on the Windows host.
Planner and Graph use the same non-thinking profile; Analyst uses `low` when
the installed model advertises thinking and `default` otherwise. A candidate is
kept warm for its role run and explicitly unloaded before the next candidate.
The mixed-language Graph positive was added to the fixture before finalizing
this report; all three Graph candidates were rerun on the affected six-case
batch. Granite completed the batch; Qwen and LFM2.5 returned
`InferenceProtocolError` for that batch. Their failures remain in the raw log.

Exact local Ollama identities at `ollama list`/`/api/tags` inspection:

| Tag | Digest | Size | Quantization |
|---|---|---:|---|
| `granite4.2:3b` | `40577dc168a3a9ad34e9a1234e0c2570be86097fa75a236d4574ae985705d3c4` | 2,244,023,965 B | Q4_K_M |
| `qwen3.5:4b-q4_K_M` | `2a654d98e6fba55d452b7043684e9b57a947e393bbffa62485a7aac05ee4eefd` | 3,389,983,735 B | Q4_K_M |
| `lfm2.5:8b-a1b-q4_K_M` | `9cf756159fc2f3b9128c6a3f544ec90c5e9b8afdbb4179a57b8aea9de589cfb2` | 5,156,075,525 B | Q4_K_M |
| `lfm2:24b-a2b` | `d6c816d74887ed480a3afd5baa2dd2a5987ef6b359b8661e80e1e9fb3501650c` | 14,415,742,358 B | Q4_K_M |
| `gemma4:26b-a4b-it-mtp-q4_K_M` | `001e5dafc3c77684c2307ebc6ab8e336e10c9b18eca52acf547d72fc83c3ca8c` | 18,731,025,629 B | Q4_K_M |

## Results and gates

The machine-readable per-candidate results, case counts, hard-gate outcomes,
and latency summaries are in [results.json](results.json). Highlights:

- **Planner:** Qwen led with 14/30 exact gold cases; Granite scored 11/30 and
  LFM2.5 5/30. All three produced schema-valid results, but exact intent/patch
  accuracy is too low to justify pinning a production Planner.
- **Analyst:** LFM2.5 had 18/18 schema- and citation-valid outputs with 5/18
  exact gold matches and no safe fallbacks. Gemma 4 matched 3/18 and fell back
  on 15/18; LFM2-24B matched 0/18 and fell back on 16/18. The best candidate's
  semantic match rate is insufficient for a production decision.
- **Graph extractor:** Granite and LFM2.5 validated 0/25 gold facts; Qwen
  validated 1/25 (4% recall). Qwen had zero invented validated facts in the
  complete cases, but its mixed-language six-case batch had a protocol failure.
  Precision alone does not make a near-empty extractor safe or useful for
  corpus backfill.

Latency is recorded by the runner and summarized in `results.json`. Reliable
tokens/sec, RSS, peak host/container memory, and swap attribution were not
collected by this harness, so those figures are `null`/unavailable rather than
inferred. The benchmark did not stop for predicted memory pressure; no model
candidate was excluded as a resource failure. Runtime/protocol failures are
reported per case/batch in raw results.

## Decision

No production winners are selected. The configured production identities remain
unchanged because the observed semantic accuracy—especially Graph recall—does
not support a safe pin. `mass_backfill_allowed` remains false. The next useful
step is to improve the role prompts/fixture alignment or add candidates, then
repeat this same frozen evaluation. This is an evaluation outcome, not a RAM
blocker. LLM-003 remains open until production choices can be supported by the
quality gates; do not start `CORPUS-001` before that decision.
