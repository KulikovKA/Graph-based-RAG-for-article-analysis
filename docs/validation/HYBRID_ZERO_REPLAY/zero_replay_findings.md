# Zero replay findings

## Observed

- Replayed 27 documents / 36 frozen chunks with 36 model calls.
- Document outcomes: `{"ACCEPTED": 3, "ALL_REJECTED": 6, "PARTIAL_ACCEPTED": 18}`.
- Parsed candidate counts: 362 raw = 198 accepted before dedup + 164 rejected; 21 accepted candidates deduplicated.
- Rejection codes: `{"AMBIGUOUS_SOURCE_OCCURRENCE": 15, "NO_EXACT_SOURCE_OCCURRENCE": 111, "QUOTE_SURFACE_REQUIRED": 1, "UNSUPPORTED_CANONICAL_NAME": 37}`.
- Of 26 source-annotated obvious-concept documents, 0 were `MODEL_EMPTY` and 6 were `ALL_REJECTED` on replay.
- `UNSUPPORTED_CANONICAL_NAME` occurred 37 times across 11 documents.
- Retry count: 0; output-limit retry policy was 2048 -> 3072 only on `OUTPUT_LIMIT`.
- All 36 calls reported reliable output-token metadata.
- Document-length summaries by current outcome (descriptive only): ACCEPTED: n=3, median=859, range=646-1053 chars; ALL_REJECTED: n=6, median=1060, range=270-1490 chars; PARTIAL_ACCEPTED: n=18, median=1084, range=550-1945 chars.
- Unicode-focused cases: D010: ALL_REJECTED, {'NO_EXACT_SOURCE_OCCURRENCE': 21}; D035: ACCEPTED, {}; D039: PARTIAL_ACCEPTED, {'NO_EXACT_SOURCE_OCCURRENCE': 1}; D058: PARTIAL_ACCEPTED, {'NO_EXACT_SOURCE_OCCURRENCE': 15}; D068: PARTIAL_ACCEPTED, {'NO_EXACT_SOURCE_OCCURRENCE': 3}; D088: PARTIAL_ACCEPTED, {'NO_EXACT_SOURCE_OCCURRENCE': 1}; D092: PARTIAL_ACCEPTED, {'AMBIGUOUS_SOURCE_OCCURRENCE': 1}.
- D048 control: `ACCEPTED` with 6 final concepts, source annotation `LOW_SPECIFICITY_SOURCE`.
- Replay results describe current behavior only; source annotations are analytical notes, not gold truth.

## Inferred cautiously

- Exact source-occurrence rejections show that some current candidates failed the quote/surface anchoring stage. They do not identify which annotated source concepts the model attempted to represent because rejected candidate values were intentionally not retained.
- Unicode-focused documents (D010, D035, D039, D058, D068, D088, D092) have small purposive coverage; no systematic Unicode/offset effect can be established from this sample. See chunk-level statuses and rejection codes in `chunk_attempts.csv`.
- The sample includes one short explicit source (D020), multi-chunk sources, and a low-specificity control (D048); this is insufficient for a length or source-specificity causal claim.

## Unknown

- Historical causes for all 27 original zero outputs remain `UNKNOWN`: original model candidates, finish reasons and rejected drafts were not retained.
- Whether any rejected candidate semantically matched an annotated source anchor cannot be recovered without retaining candidate content; the privacy contract forbids that content here.
- This replay does not establish why historical runs behaved as they did, corpus-wide extractor quality, or retrieval impact.
- The host could not reach the repository's container-oriented `host.docker.internal:11434` address. The isolated runner used loopback to the same installed Ollama service after verifying its runtime version and exact model digest; request parameters remained unchanged. Endpoint-route equivalence is not a historical causality claim.

## Per-document current replay

| Document | Chunks | Current classification | Raw | Accepted | Rejected | Final | Main rejection code | Historical cause |
|---|---:|---|---:|---:|---:|---:|---|---|
| D010 | 2 | ALL_REJECTED | 21 | 0 | 21 | 0 | NO_EXACT_SOURCE_OCCURRENCE | UNKNOWN |
| D011 | 1 | PARTIAL_ACCEPTED | 12 | 5 | 7 | 5 | UNSUPPORTED_CANONICAL_NAME | UNKNOWN |
| D012 | 1 | PARTIAL_ACCEPTED | 12 | 2 | 10 | 2 | UNSUPPORTED_CANONICAL_NAME | UNKNOWN |
| D017 | 2 | ALL_REJECTED | 6 | 0 | 6 | 0 | NO_EXACT_SOURCE_OCCURRENCE | UNKNOWN |
| D018 | 2 | PARTIAL_ACCEPTED | 24 | 20 | 4 | 18 | UNSUPPORTED_CANONICAL_NAME | UNKNOWN |
| D020 | 1 | ALL_REJECTED | 7 | 0 | 7 | 0 | NO_EXACT_SOURCE_OCCURRENCE | UNKNOWN |
| D023 | 1 | PARTIAL_ACCEPTED | 12 | 9 | 3 | 9 | AMBIGUOUS_SOURCE_OCCURRENCE | UNKNOWN |
| D025 | 1 | PARTIAL_ACCEPTED | 12 | 8 | 4 | 8 | UNSUPPORTED_CANONICAL_NAME | UNKNOWN |
| D028 | 2 | PARTIAL_ACCEPTED | 13 | 4 | 9 | 4 | AMBIGUOUS_SOURCE_OCCURRENCE | UNKNOWN |
| D029 | 1 | ALL_REJECTED | 12 | 0 | 12 | 0 | NO_EXACT_SOURCE_OCCURRENCE | UNKNOWN |
| D035 | 1 | ACCEPTED | 2 | 2 | 0 | 2 | none | UNKNOWN |
| D039 | 2 | PARTIAL_ACCEPTED | 24 | 23 | 1 | 23 | NO_EXACT_SOURCE_OCCURRENCE | UNKNOWN |
| D040 | 2 | PARTIAL_ACCEPTED | 24 | 12 | 12 | 12 | NO_EXACT_SOURCE_OCCURRENCE | UNKNOWN |
| D045 | 1 | PARTIAL_ACCEPTED | 12 | 7 | 5 | 7 | UNSUPPORTED_CANONICAL_NAME | UNKNOWN |
| D048 | 1 | ACCEPTED | 6 | 6 | 0 | 6 | none | UNKNOWN |
| D058 | 2 | PARTIAL_ACCEPTED | 24 | 9 | 15 | 6 | NO_EXACT_SOURCE_OCCURRENCE | UNKNOWN |
| D063 | 1 | ACCEPTED | 12 | 12 | 0 | 6 | none | UNKNOWN |
| D065 | 1 | PARTIAL_ACCEPTED | 12 | 6 | 6 | 6 | AMBIGUOUS_SOURCE_OCCURRENCE | UNKNOWN |
| D068 | 2 | PARTIAL_ACCEPTED | 14 | 11 | 3 | 11 | NO_EXACT_SOURCE_OCCURRENCE | UNKNOWN |
| D069 | 1 | PARTIAL_ACCEPTED | 12 | 3 | 9 | 3 | UNSUPPORTED_CANONICAL_NAME | UNKNOWN |
| D080 | 1 | PARTIAL_ACCEPTED | 12 | 7 | 5 | 7 | NO_EXACT_SOURCE_OCCURRENCE | UNKNOWN |
| D084 | 1 | PARTIAL_ACCEPTED | 12 | 11 | 1 | 11 | NO_EXACT_SOURCE_OCCURRENCE | UNKNOWN |
| D086 | 1 | ALL_REJECTED | 5 | 0 | 5 | 0 | NO_EXACT_SOURCE_OCCURRENCE | UNKNOWN |
| D088 | 2 | PARTIAL_ACCEPTED | 24 | 23 | 1 | 13 | NO_EXACT_SOURCE_OCCURRENCE | UNKNOWN |
| D091 | 1 | ALL_REJECTED | 12 | 0 | 12 | 0 | NO_EXACT_SOURCE_OCCURRENCE | UNKNOWN |
| D092 | 1 | PARTIAL_ACCEPTED | 12 | 11 | 1 | 11 | AMBIGUOUS_SOURCE_OCCURRENCE | UNKNOWN |
| D097 | 1 | PARTIAL_ACCEPTED | 12 | 7 | 5 | 7 | UNSUPPORTED_CANONICAL_NAME | UNKNOWN |

## Classification rules

- `MODEL_EMPTY`: every chunk completed with a valid empty mentions array.
- `ALL_REJECTED`: non-empty parseable output, no accepted candidates, and at least one rejection.
- `PARTIAL_ACCEPTED`: at least one accepted and one rejected candidate.
- `ACCEPTED`: accepted candidates and no validation rejections.
- `MIXED_CHUNKS`: chunks differ between empty and non-empty successful outcomes.
- `INFERENCE_FAILURE`: at least one chunk did not complete inference/protocol parsing.
- `RETRY_RECOVERED`: the configured output-limit retry was used and the final attempt completed; counts and chunk statuses remain separate.
- Deduplication is reported separately and never counted as validation rejection.
