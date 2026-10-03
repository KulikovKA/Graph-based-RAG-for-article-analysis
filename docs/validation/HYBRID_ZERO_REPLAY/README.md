# HYBRID_ZERO_REPLAY

Controlled diagnostic replay of the 27 historical Hybrid zero-concept documents. The replay used the frozen source export and the current v1.4 extraction/validation code, with no persistence to production stores.

> **CURRENT REPLAY RESULTS DO NOT RECOVER HISTORICAL CAUSALITY. HISTORICAL 27 REMAIN UNKNOWN.**

## Identity and setup

- Code commit before this work: `8fb0326d575b33d17a0c63413311ec839fff392f`; the harness and report are included in the local follow-up commit.
- SHA-256 identities for the extractor observer, isolated harness, validator and inference adapter are recorded in `replay_metrics.json`.
- Extractor: `hybrid-technical-concepts-v1.4`; schema: `technical-concept-mention-v1` (`32de2363d1540d3b9ce5b9870a578f188a5a51a78544c2b4e044b9800cc9a36c`).
- Model: `qwen3.5:4b-q4_K_M`; digest: `2a654d98e6fba55d452b7043684e9b57a947e393bbffa62485a7aac05ee4eefd`.
- Runtime: Ollama `0.35.0`; observed effective context: `4096` tokens.
- The repository's container-oriented inference address was unreachable from the host runner; replay used loopback to the same installed Ollama runtime after verifying its version and exact model digest. Prompt/model/request parameters were unchanged.
- Temperature 0; thinking disabled; 300-second request timeout; output budget 2048, retry once at 3072 only after output-limit.
- Frozen read-only export: `docs/analysis/HYBRID_ZERO_AUDIT/live_read.json`; every source chunk SHA-256 was checked before inference and again at report finalization.
- Replayed all 27 IDs, 36 chunks, in two phases: smoke `D010, D020, D039, D048, D092`, then remaining 22 with the same code and configuration.
- The isolated runner connected only to the inference API and wrote artifacts under this directory. It made no PostgreSQL/Neo4j/checkpoint writes; `production_stores_touched=false`. The pre/post checkpoint, frozen snapshot and source-export hashes match the audit manifest in `replay_metrics.json`.

## Results

- Model calls: 36; diagnostics include inference status, finish metadata where provided, timings, retries, counts and stable validator reasons.
- Current document classifications: `{"ACCEPTED": 3, "ALL_REJECTED": 6, "PARTIAL_ACCEPTED": 18}`.
- Raw candidates 362; accepted before dedup 198; rejected 164; deduplicated 21.
- Rejection histogram: `{"AMBIGUOUS_SOURCE_OCCURRENCE": 15, "NO_EXACT_SOURCE_OCCURRENCE": 111, "QUOTE_SURFACE_REQUIRED": 1, "UNSUPPORTED_CANONICAL_NAME": 37}`.
- Synthetic observer tests and all repository unit tests passed; see session verification and `zero_replay_findings.md` for interpretation limits.

## Interpretation limits

Current behavior can be observed; the historical run cannot be reconstructed because its provider outputs and rejected candidates were not retained. The source annotations are assistant analytical reading, not human gold or exhaustive recall labels. Rejected model values, prompts, reasoning, credentials and provider response bodies are not stored. Token counts appear only when the provider reports them reliably. Context size is the runtime observation for this session, not the model's advertised maximum.

## Artifacts

- `document_summary.csv`: one row per historical zero document, with historical cause fixed to UNKNOWN.
- `chunk_attempts.csv`: attempt-level allowlisted diagnostics and source hashes; no raw outputs.
- `rejection_reasons.csv`: global and per-document stable reason counts.
- `replay_metrics.json`: aggregate metrics, configuration and immutability statement.
- `zero_replay_findings.md`: observed facts, cautious inferences, unknowns, and per-document outcomes.
