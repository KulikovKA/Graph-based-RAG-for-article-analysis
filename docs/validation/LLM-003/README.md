# LLM-003 — comparative local model evaluation

Status: **all three production roles selected and pinned**. `CORPUS-001` was
not run; model selection is complete and its separate task may proceed. No model
weights or user/corpus data are included.

## Gold data and scoring

Fixtures are deterministic JSONL with stable IDs and explicit human-authored
labels. Planner has 30 cases, Analyst 18, and Graph extractor 48 (25 positive
cases, 23 negative). Cases cover RU, EN, mixed-language text, patch operations,
relation taxonomy, exact citations, adversarial inputs, Unicode offsets, and
empty Graph output. All labels are fixture-authored; evaluated models never
generate gold. `EVAL-000/dev_smoke` informed applicable patterns but is not
scored as gold. Results use exact contracts and labels, not an LLM judge.

One proven label omission was corrected before the final Graph run: GR-03 says
“The sodium-ion cell uses a hard-carbon anode; устройство includes thermal
management.” The second clause explicitly discloses thermal management as a
technical feature, but the previous expected list contained only the anode.
The deterministic gold now includes both features. No other labels changed.

## Runtime and exact identities

Runs used Ollama 0.34.4 and were sequential, with each model unloaded before a
different candidate. Planner used non-thinking; Analyst used `low` on the
thinking-capable candidate; Graph used the non-thinking profile. Gold artifacts
and fixture hashes are in `eval/llm003/`; immutable per-case raw results are in
[`raw/`](raw/).

| Role/run | Exact tag | Ollama digest | Prompt / profile |
|---|---|---|---|
| Planner final | `qwen3.5:4b-q4_K_M` | `2a654d98e6fba55d452b7043684e9b57a947e393bbffa62485a7aac05ee4eefd` | `planner_v3`, non-thinking |
| Graph final | `qwen3.5:4b-q4_K_M` | `2a654d98e6fba55d452b7043684e9b57a947e393bbffa62485a7aac05ee4eefd` | `graph-extraction-v2`, non-thinking |
| Analyst selected | `gpt-oss:20b` | `17052f91a42e97930aa6e28a6c6c06a983e6a58dbb00434885a0cf5313e376f7` | `analyst_v4`, `low` |

Other candidates inspected with `ollama list` and `/api/tags`:

| Exact tag | Digest | Size |
|---|---|---:|
| `granite4.2:3b` | `40577dc168a3a9ad34e9a1234e0c2570be86097fa75a236d4574ae985705d3c4` | 2,244,023,965 B |
| `lfm2:24b-a2b` | `d6c816d74887ed480a3afd5baa2dd2a5987ef6b359b8661e80e1e9fb3501650c` | 14,415,742,358 B |
| `gemma4:26b-a4b-it-mtp-q4_K_M` | `001e5dafc3c77684c2307ebc6ab8e336e10c9b18eca52acf547d72fc83c3ca8c` | 18,731,025,629 B |
| `gpt-oss:20b` | `17052f91a42e97930aa6e28a6c6c06a983e6a58dbb00434885a0cf5313e376f7` | 13,793,441,244 B |

## Results and hard gates

[`results.json`](results.json) contains historical and final per-candidate
counts, latency summaries, exact component/relation breakdowns, and gate
outcomes. Raw files with `_v2`/`_v3` suffixes preserve each rerun separately;
the original baseline files were not rewritten.

- **Planner:** final Qwen v3 scored 26/30 exact (86.7%), with 30/30 schema,
  feature-ID and citation-ID validity; intent 29/30, add 27/30, remove 30/30,
  replace 29/30; zero fallback/repair. It improved from 20/30 on the prompt-only
  v2 run and 14/30 in the historical warm baseline. Qwen is selected for
  Planner; it has the best quality among the compared candidates and passes
  structural gates.
- **Graph extractor:** final Qwen run on adjudicated gold matched 18/26 facts
  (69.2% recall), with 19 validated facts, 100% precision, zero invented
  facts, 48/48 schema/provenance-valid cases, 0 protocol failures, and 23/23
  negative cases correct. The Graph v2 semantic DTO no longer asks the model
  for offsets or IDs: Python deterministically resolves exact quote spans and
  known chunk IDs; strict fact validation is unchanged. This is materially
  stronger than historical candidates (0/25 Granite, 1/25 Qwen, 0/25 LFM2.5).
  Qwen is selected as the Graph candidate under the measured no-invented-fact
  gate; the 8 missed gold facts remain a documented recall limitation.
- **Analyst:** GPT-OSS 20B v4 scored 13/18 exact (72.2%), with 18/18
  schema-valid and citation-valid results, zero fallbacks, zero unsupported
  claims on the gold `none` case, and no raw reasoning in output artifacts. It
  matched all full (5/5), conflicting (4/4), and none (1/1) labels, plus 2/4
  partial and 1/4 uncertain. It is selected as the strongest candidate that
  passed structural and citation gates. The remaining partial/uncertain misses
  are documented for follow-up evaluation. LFM2.5 v4 scored 5/18, 17/18
  schema/citation-valid and one fallback; LFM2-24B v3 scored 5/18 with 5
  fallbacks and 13/18 valid. Historical Gemma 4 scored 3/18 with 15 fallbacks;
  it was not selected. A later Gemma semantic-DTO run was stopped at the user's
  direction after six cases and excluded from comparison and selection.

Historical Graph Qwen/LFM2.5 protocol failures were recorded only by exception
class (`InferenceProtocolError`), so the old artifacts do not preserve enough
information to identify their precise internal cause. The semantic DTO rerun
completed all 48 cases with no protocol/runtime failures, so those historical
failures did not recur. No evidence linked them to model-authored offsets.

Latency medians and p95 values are in `results.json`. The harness did not
collect reliable tokens/sec, host RSS/peak memory, or swap attribution; these
remain unavailable rather than inferred. No candidate stopped for predicted
memory pressure, and no candidate was excluded as a resource failure.

## Production decision

Planner winner: `qwen3.5:4b-q4_K_M` at digest
`2a654d98e6fba55d452b7043684e9b57a947e393bbffa62485a7aac05ee4eefd`,
non-thinking, 384 output tokens. Graph winner: the same exact tag/digest,
`graph-extraction-v2`, non-thinking, 384 output tokens. The worker pipeline does
not currently instantiate `GraphIndexingService`, but the selected Graph model
identity/version is pinned in `config/models.yaml` and registered with the
inference provider for the injected extractor. Planner config and inventory are
also updated to the selected identity.

Analyst winner: `gpt-oss:20b` at digest
`17052f91a42e97930aa6e28a6c6c06a983e6a58dbb00434885a0cf5313e376f7`,
`analyst_v4`, reasoning `low`, 2,048 output tokens. Its exact upstream
tokenizer is `openai/gpt-oss-20b` revision
`6cee5e81ee83917806bbde320786a8fb61efebee`, SHA-256
`0614fe83cadab421296e664e1f48f4261fa8fef6e03e63bb75c20f38e37d07d3`.
The shared JSON tokenizer loader was generalized and verifies that checksum at
startup. All three selected identities and profiles are recorded in
`config/models.yaml`, `docs/model_inventory.json`, and `results.json`.
For local deployment, place the tokenizer from the pinned revision at
`data/models/gpt-oss-tokenizer.json`; tokenizer assets stay outside Git.

`mass_backfill_allowed` remains false; this benchmark did not run or authorize
`CORPUS-001`. The corpus task remains separately gated and must follow its own
dry-run/small-run checks. The benchmark itself is complete; semantic misses are
reported as model limitations, not runtime blockers.
