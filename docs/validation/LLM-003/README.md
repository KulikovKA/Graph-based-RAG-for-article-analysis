# LLM-003 — comparative local model evaluation

Status: **benchmark runs complete; production selection remains open for the
Analyst role**. Planner and Graph candidates pass structural hard gates and are
selected below. `CORPUS-001` remains blocked until a defensible Analyst winner is
available. No model weights or user/corpus data are included.

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
| Analyst final | `lfm2.5:8b-a1b-q4_K_M` | `9cf756159fc2f3b9128c6a3f544ec90c5e9b8afdbb4179a57b8aea9de589cfb2` | `analyst_v4`, `low` |

Other candidates inspected with `ollama list` and `/api/tags`:

| Exact tag | Digest | Size |
|---|---|---:|
| `granite4.2:3b` | `40577dc168a3a9ad34e9a1234e0c2570be86097fa75a236d4574ae985705d3c4` | 2,244,023,965 B |
| `lfm2:24b-a2b` | `d6c816d74887ed480a3afd5baa2dd2a5987ef6b359b8661e80e1e9fb3501650c` | 14,415,742,358 B |
| `gemma4:26b-a4b-it-mtp-q4_K_M` | `001e5dafc3c77684c2307ebc6ab8e336e10c9b18eca52acf547d72fc83c3ca8c` | 18,731,025,629 B |

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
- **Analyst:** final LFM2.5 v4 scored 5/18 exact; 17/18 outputs were
  schema- and citation-valid, and one case used safe fallback. It predicted
  `full` 11 times and `none` 7 times, never correctly distinguishing any of
  the partial, conflicting, or uncertain labels. LFM2-24B v3 scored 5/18 but
  had 5 fallbacks and only 13/18 schema/citation-valid outputs. LFM2.5 v3
  scored 4/18 with 2 fallbacks. The earlier LFM2.5 v2 run had 18/18
  schema/citation validity and no fallback but only 2/18 exact; the historical
  LFM2.5 baseline reached 5/18 with 18/18 schema/citation validity. Historical
  Gemma 4 scored 3/18 with 15 fallbacks; it was not selected. On a later
  semantic-DTO run, Gemma was user-stopped after six cases and that partial run
  was excluded from results and selection. No Analyst candidate is selected:
  relation taxonomy quality and, for the latest runs, hard gates remain
  insufficient for production.

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

There is no Analyst winner. Analyst production configuration remains unchanged
pending a quality-valid candidate. The latest tested prompt is `analyst_v4`;
the next iteration should focus on discriminating partial/conflicting/uncertain
cases, which remain missed, and preserve the frozen labels. LLM-003 therefore
remains open, and
`mass_backfill_allowed` remains false. Do not start `CORPUS-001` until that
selection is resolved. The active unresolved issue is semantic quality, not
RAM, swap, or a runtime blocker.
