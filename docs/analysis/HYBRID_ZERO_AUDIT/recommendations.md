# Recommendations after HYBRID-002

Historical zero-document cause is UNKNOWN; no quality fixes were implemented. Preserve exact source provenance and the existing production results. Maximum three follow-ups:

| Follow-up | Expected benefit | Provenance risk | Complexity | CPU impact | 100-doc rerun needed? |
|---|---|---|---|---|---|
| 1. Structured attempt/chunk diagnostics and isolated replay | Distinguish empty output, all-rejected, runtime failure, dedup and persisted/projection loss for **new** diagnostic observations. Does not recover historical drafts. | Low if only allowlisted codes/counts/timings and IDs are retained; no reasoning, provider bodies, prompts or rejected JSON. | Low–medium: observer sidecar, typed reason mapping, attempt-scoped counters and metadata forwarding. | Negligible diagnostic overhead; replay itself incurs existing model cost. | No: validate observer, then five representative zero docs, optionally remaining 22. |
| 2. Canonical identity/type entailment gate at extractor–validator interface | Prevent generic gas/liquids from claiming NO2/NH3 and materials from being typed as analytes; address eight measured accepted canonical counterexamples and top-30 type errors. Coverage benefit is unknown and may initially decrease. | Low if exact quotes/spans stay mandatory and semantic decisions are evidence-backed; poorly designed semantic gate could overreject valid synonyms. | Medium; define evidence-backed rules/review cases before choosing deterministic or semantic checking. Do not hardcode corpus-specific concepts. | Low for deterministic checks; potentially substantial if a second model call is chosen, so measure before adopting. | No for a pilot/interface validation; a later separate 100-doc frozen evaluation is required before claiming corpus-wide improvement. |
| 3. Scoped connectivity evaluation using concept kind, qualifiers and relevance labels | Stop treating generic node degree or analyte occurrence as equal technical claims; measure usefulness of shared specific concepts and negative/interferent contexts. Preserve raw-fact evidence layer. | Low for evaluation-only changes; downstream filtering must preserve source access and qualifiers. | Medium, mostly annotation/evaluation; ontology redesign is not justified. | Small for offline graph filtering; no new model work required for the current 476-pair sensitivity analysis. | No for current graph analysis; later evaluation depends on any chosen quality change. |

## Minimal proposed instrumentation (specification only)

Do not change the extraction prompt, model/digest, schema, grounding behavior, output budget, sampling, dedup identity or database production result. Keep a standalone observer/sidecar isolated from `HYBRID-001` rather than backfilling invented diagnostics into old rows. Persist each completed or failed chunk **attempt**, keyed by diagnostic_run_id, historical_reference_run_id, document_id, revision_id, chunk_id, outer_attempt and inference_attempt; do not overwrite previous attempts on success.

Allowlisted fields:

- source SHA-256; prompt/schema/code SHA-256; extractor version; model/digest; provider version and effective runtime context; config values including temperature, thinking, output budget, timeout and retry.
- `raw_candidate_count`, `accepted_candidate_count`, `rejected_candidate_count` for the returned candidate array; separate `deduplicated_mention_count`, `duplicate_count`, persistence/projection counts if those stages are exercised in isolated storage. Counts are null when no complete parseable candidate array exists. Check `raw=accepted+rejected` per parsed attempt, then separately account for dedup.
- inference status `success`, `empty`, `invalid_json`, `truncated`, `timeout`, plus `protocol_error`, `unavailable`, `cancelled`, `invalid_envelope` as actual provider contracts require. **Nonempty all-rejected inference is success plus validation counts, not model-empty.**
- terminal `finish_reason`, available token counts and their reliability/reason fields, elapsed/TTFT/load timings, provider exception class as allowlisted code, retry trigger and retry outcome. Do not serialize exception bodies.
- rejection counts by deterministic stage/code; Pydantic `.errors()` may supply allowlisted error `type` and known field location only, excluding `input`, arbitrary `ctx`, model values and exception messages containing input. Distinguish draft-shape failure, required quote/surface, no exact occurrence, ambiguous occurrence and schema/type/length/extra-field errors. Grounding defensive codes map to the actual validator messages; do not invent counts for unreachable paths.
- aggregate final per-document counts from the **designated final attempts**, with failed/retried attempts reported separately. Record reanchor-applied and reported-offset-valid booleans/counts; never conflate repaired offsets with rejected candidates.

Structured diagnostics obey `docs/SECURITY.md`: no raw provider bodies, parsed rejected JSON, chain-of-thought/hidden reasoning, full prompts, secrets or response-body exception capture. Do not add a debug opt-in for reasoning. Current security contract does not authorize retaining raw responses. Real rejected semantic examples would require a separately approved project policy for narrowly scoped non-reasoning fields; this audit does not introduce that policy or fabricate examples.

Observer verification should include synthetic empty/all-rejected/partial cases, ambiguity, malformed JSON, length retry, timeout and dedup; verify count conservation and that reasoning/rejected-value sentinels never reach diagnostics. Then compare accepted mention IDs with the unmodified extractor on fixed test fixtures to prove observation did not change acceptance behavior. These are follow-up acceptance checks, not implemented production tests in this audit.

## Controlled replay design

Historical 686 drafts are irrecoverable from currently retained artifacts. A future rerun answers whether a failure mechanism **reproduces**, not exactly which original candidates were lost. Keep original 27 cause labels UNKNOWN unless new independently recoverable historical evidence appears.

After the observer is verified, choose five with source/contract variation:

| Document | Reason |
|---|---|
| D010 | Two chunks, spaced chemistry, sole outer retry, ten raw facts, zero concepts |
| D020 | 270-character but specific CVD/ALD/ZnO source; short-source control |
| D039 | Two-chunk review with true Unicode subscripts MoS₂/WS₂ |
| D048 | Low-specificity roadmap control |
| D092 | Explicit DFT/chemistry source, originally raw-zero and still Hybrid-zero |

Verify frozen 100-document snapshot identity and all selected revision/chunk SHA-256 values; installed model tag and exact digest; audited prompt/schema/code; historic effective context and sampling/runtime defaults as far as recoverable. Current HEAD omits context_window and host log observes 4096; **do not substitute production graph_extractor's 16384**. Pin/check effective historical defaults in the diagnostic harness only if their identity is established; if exact historical runtime cannot be established, label the replay comparable rather than identical and do not infer historical causality.

Use the same 2048→3072 length-only retry and 300-second deadline from the audited path; do not optimize parameters. Note that historical v1.3 identifiers do not by themselves hash every intermediate runtime code revision. Store observer output in a distinct diagnostic namespace/run; do not call the production backfill runner's `main_async` because it writes PostgreSQL, Neo4j and checkpoints. A read-only source/validation observer need not persist concept graph results at all. Preserve original checkpoint/production data.

Only after the first five demonstrate useful counts, actual status/reason attribution and no leakage should the remaining 22 be considered. Never rerun the entire 100-document corpus in this forensic task. No replay occurred here.
