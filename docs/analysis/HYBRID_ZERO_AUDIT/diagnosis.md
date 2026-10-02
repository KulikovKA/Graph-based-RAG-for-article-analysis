# HYBRID-002: forensic diagnosis

**Historical classification: E — insufficient retained artifacts. All 27 zero-concept documents are `UNKNOWN` between model-empty and all-rejected. This is an established information-loss finding, not an estimate of which mechanism is more likely. PostgreSQL→Neo4j loss is excluded for the final persisted result.**

Audit date: 2026-10-02, Europe/Moscow. Audited repository HEAD: `14470be839a6aaddca2328c36cab2e4d6fe0a0fb`; initial working tree clean. Read-only PostgreSQL collection at 22:24:18 Moscow time, repeatable-read transaction with `transaction_read_only=on`. Neo4j used read transactions. No model generation, downloads, corpus ingestion, projection writes, production changes or diagnostic rerun occurred.

## Exact historical run

Run `d895217d-ebbe-4117-9066-8ae0ebcd0bdc`, extractor `hybrid-technical-concepts-v1.3`, snapshot `5b80378fa2d8312951446fcbb3ada7994d775f13d452ff08fd415377a5fcade0`. PostgreSQL start/end: 18:25:10–22:01:39 Moscow time. Six semantic runs exist: three failed v1/v1.1 runs, one unfinished v1.2 run, the completed ten-document v1.3 smoke `321713c9-6238-49f5-b1e9-b1de6ba223b5`, and this completed 100-document run. Only the exact final run is used for mention/coverage calculations.

The checked-in HYBRID-001 `config.json` is an earlier smoke-blocked artifact with extractor `v1`, not an authoritative final runtime configuration. Final DB rows and checkpoint identify v1.3. No earlier smoke mentions are included in this audit's mention counts; shared `technical_concepts` metadata is joined only through final-run mentions.

| Final-run measurement | Result |
|---|---:|
| Run documents / completed / failed | 100 / 100 / 0 |
| Documents with / without persisted mentions | 73 / 27 |
| Unique concepts / singleton / shared | 532 / 472 / 60 |
| Unique document–concept incidences | 692 |
| PostgreSQL / checkpoint / Neo4j mention edges | 747 / 747 / 747 |
| Missing / extra projected mention IDs | 0 / 0 |
| Projected provenance property mismatches | 0 |
| Exact accepted grounding checks passed | 747 / 747 |
| Immutable EvidenceChunk hashes/spans checked | 136 / 136 |
| Frozen GraphFact IDs still present | 417 / 417 |
| Recorded cumulative validation rejects | 686 |

747 counts source **mentions**, including several distinct occurrences of the same concept within a document; 692 counts distinct document–concept edges. These counts are compatible. All 100 Neo4j source-document keys were present in the live read; all 27 zeros have zero accepted mentions in both stores. `postgres_neo4j_diff.csv` contains all 100 document rows, exact ID comparisons and property checks. Concept display names may have different equivalent canonical spellings between checkpoint drafts and first-created shared concept records; identity and mention provenance are the comparison criteria.

This excludes an observed projection defect. It also excludes loss of checkpoint-retained mentions during PostgreSQL persistence. It does **not** claim a historical count of every candidate that ever passed validation: pre-dedup candidates and valid mentions from failed attempts were never retained.

## Source and baseline coverage

All **36 EvidenceChunks** of the 27 zero documents were read in full. Hashes and text matched the earlier corpus export. Each chunk equals its immutable normalized section slice, and all nonwhitespace source characters are covered. No missing chunks or malformed stored-source spans were found. This checks stored abstracts, not full article text or upstream OpenAlex completeness.

`source_concept_spans.csv` contains **80 exact source anchors**, with chunk IDs and Python codepoint offsets. They are assistant analytical annotations, not raw model output, an exhaustive recall gold set, or changes to the extractor. All 27 have at least broad material/domain concepts. 26 have obvious technical concepts under the actual semantic prompt; D048 is a low-specificity roadmap with policy-dependent usefulness. Source-quality label E for the 26 means that the cause of omission is unknown despite visible concepts; it does **not** assert that the model emitted an empty answer or that validation rejected them. D048's source assessment A is not a proven causal classification.

Representative source evidence:

- D010: hydrothermal synthesis of Ti3C2Tx/MXene/GO/CuO/ZnO, NH3 response 96% at 200 ppm; ten raw facts, two chunks, zero concepts.
- D020: even a 270-character abstract explicitly names CVD graphene, ZnO and ALD; one raw fact, zero concepts. Long input cannot explain every zero.
- D039: explicit `MoS₂`, `WS₂` and sensor modalities in two intact chunks; three raw facts, zero concepts.
- D088: nanomesh lithography/RIE and NO(2)/NH(3) sensitivity in two chunks; sixteen raw facts, zero concepts.
- D092: doped/defective graphene, DFT and four gas molecules; zero raw facts and zero concepts despite explicit source vocabulary.
- D048: roadmap overview supplies graphene/related-material concepts but few concrete devices/processes. Do not treat this like a high-specificity measured sensor abstract.

The exact zero list is D010, D011, D012, D017, D018, D020, D023, D025, D028, D029, D035, D039, D040, D045, D048, D058, D063, D065, D068, D069, D080, D084, D086, D088, D091, D092, D097. `zero_documents.csv` supplies UUIDs, revisions, OpenAlex IDs, titles, lengths, chunks, raw facts, final status and DB attempt counts.

| Raw GraphFacts | Hybrid YES | Hybrid NO | Total |
|---|---:|---:|---:|
| YES | 66 | 23 | 89 |
| NO | 7 | 4 | 11 |
| Total | 73 | 27 | 100 |

Thus 23 documents with raw facts lost semantic-layer coverage, seven baseline zeros were recovered, and four remained zero (D023, D048, D084, D092). Recovery IDs: D007, D013, D015, D019, D041, D059, D064. Net coverage reduction is 23−7=16 documents, explaining 89%→73% **arithmetically**, without assigning an extraction cause. The raw and semantic contracts select different representations; a raw fact is diagnostic evidence of available content, not proof that the model proposed a corresponding semantic candidate.

The seven recoveries are **stored-count coverage**, not seven certified semantic recoveries. In particular D013's three concepts are NO2, NH3 and selectivity, all anchored on generic gas/property wording; its entire 147-character source does not explicitly establish those specific analytes or selectivity. The two analyte counterexamples are included in the eight findings below; the selectivity issue is also noted in the top-30 review.

| Per-document median | 73 concept docs | 27 zero docs |
|---|---:|---:|
| Raw candidates before validation | unavailable | unavailable |
| Rejects | unavailable | unavailable |
| Accepted candidates before dedup | unavailable | unavailable |
| Unique persisted accepted mentions | 11 | 0 |
| Unique concepts | 9 | 0 |
| Chunks | 1 | 1 |
| Sum of chunk text characters | 1020 | 1053 |

These descriptive lengths do not establish a length-related cause. Empty numeric CSV fields and JSON nulls mean unavailable, not zero. Acceptance rates cannot be reconstructed.

## Actual pipeline and retained diagnostics

Implementation: `scripts/hybrid_concept_backfill.py`, `src/app/services/technical_concepts.py`, `src/app/integrations/inference_http.py`, `migrations/versions/0007_hybrid_semantic_concepts.py` at the audited HEAD. Runner serialization is document-by-document, **one inference request per chunk**, with no cross-document model batch. Projection later batches up to 200 already-validated mention rows; it is not extraction batching.

1. Read frozen active document/revision pairs and every chunk, ordered by revision/ordinal. The prompt receives the chunk text encoded as a JSON string; it does not receive title, other chunks or baseline GraphFacts.
2. Request up to 12 distinct high-value explicit concepts, exact short source quote and surface, with Unicode codepoint offsets. Empty `mentions` is expressly valid.
3. Ollama streams `/api/chat`; adapter separates content and thinking, discards thinking, requires a terminal frame with `done_reason=stop`, joins final content and parses a JSON **object**. `length` raises `InferenceOutputLimit`; other protocol/transport/JSON errors raise outside candidate validation. Backend gets the schema, but the Python adapter does not independently validate the complete response against JSON Schema. Individual candidates undergo Pydantic validation later.
4. `validate_or_reanchor_draft` copies each draft, trims textual fields, searches **exact** quote/surface occurrences, preserves a valid preferred start or reanchors a uniquely recoverable occurrence, and **recomputes end_offset**. Then Pydantic checks fields/types/limits and `validate_grounding` checks exact codepoint slices and quoted occurrence membership.
5. `_extract` catches `ValidationError`, `ValueError` and `TypeError` for individual drafts, increments an integer, and discards the draft and exception. It returns accepted objects, elapsed seconds, reject total and request-attempt count. It does not return candidate/reject reasons or `result.metadata`.
6. Runner adds chunk rejects to a **run-wide cumulative counter**, forms concept IDs from type+normalized canonical name, and silently deduplicates mentions by run/document/chunk/span/concept ID. Duplicate accepted drafts are **not** counted as validator rejects.
7. Per-document transaction inserts concepts/mentions and marks the document completed atomically, even for an empty retained list. DB `attempts` counts outer document attempts, not per-chunk HTTP attempts. Failure changes document status; successful retry clears its error. Checkpoint saves accepted deduplicated mentions, completed IDs, latencies and aggregate counters; successful retry removes the failure entry.
8. Neo4j projects the checkpoint's accepted mentions with exact mention IDs, quote, surface, offsets, chunk/revision and qualifiers. No source re-extraction occurs here.

| Diagnostic | Historical retention |
|---|---|
| Frozen source text/revision/hash | yes |
| Accepted deduplicated mentions and provenance | yes, checkpoint + PG + Neo4j |
| Raw final provider content / parsed rejected drafts | no |
| Raw candidate count / pre-dedup accepted count | no |
| Per-chunk / per-document rejects | no |
| Reject reason / validator exception / draft offsets | no |
| Dedup count / valid mentions in failed attempts | no |
| Empty model array vs nonempty all-rejected array | no |
| Final success/failure, outer attempts | yes, DB |
| Historical error after successful retry | cleared in DB and checkpoint |
| Finish reason, token count, TTFT, load time | adapter produces metadata on success, runner discards it |
| HTTP status/duration | host Ollama log; no document/run identity |

`semantic_concept_run_documents` has status, attempts, error and updated_at, **no counts or inference diagnostics**. The live information_schema inventory inspected all 35 public tables and the 39 semantic/diagnostic columns. No table supplies the discarded semantic drafts. Checkpoints, HYBRID validation CSVs, runner state and repository/cache trace/log filenames were inspected; no per-candidate semantic trace was located. The removed corpus-runner container is absent from `docker ps -a`, so its stdout is unavailable from Docker. This is a bounded audit of available project/host artifacts, not a claim about hypothetical external backups.

Host Ollama `server.log` covers the final time interval; rotated earlier logs were also inventoried. `inference_http_window.csv` contains 139 HTTP chat completions, all HTTP 200, during that interval; it is **time-window evidence only**, not an exact run-labelled trace. `_extract` passes `request_id` to the adapter but the adapter does not send it to Ollama. HTTP 200 does not imply valid JSON, `done_reason=stop`, nonempty candidates or accepted mentions. No `done_reason` traces/candidate bodies survive in these logs. No input-truncation warning was found in the active log; absence of that warning does not prove absence of output truncation.

This establishes a many-to-one information loss: `{"mentions":[]}` and `{"mentions":[candidate rejected by validation]}` both become the same completed zero-mention document, with no per-document diagnostic discriminator. The aggregate 686 cannot restore the missing mapping. Neither scenario is ruled out for any of the 27 documents.

## What the 686 counter actually means

686 is the final checkpoint's **cumulative number of caught candidate validation exceptions from chunks whose `_extract` completed**. Rejected candidates are never inserted into PostgreSQL/Neo4j; their fields and reason codes are discarded. It is not a JSON parse failure count, timeout count, dedup count, number of distinct concepts, or count attributable to zero documents.

The counter is updated after each successful chunk, before the document transaction. If a later chunk fails and the document is retried, rejects from the already-processed prefix may remain in the counter and be counted again on retry. D010 has two DB document attempts, two chunks, final zero mentions, and is last in checkpoint completion order. Therefore retry-prefix contamination is possible; how many, if any, of the 686 came from its failed prefix is not recoverable. Do not call 686 a deduplicated final-pass reject population, compute 747/(747+686) as an acceptance rate, or assert exactly 1433 model candidates. Accepted duplicates and failed prefixes make that denominator unidentifiable.

`rejection_reasons.csv` assigns 686 to **UNRECORDED_AGGREGATE**, 100% of the *recorded counter*. This is an availability bucket, not a validator cause. No percentages of actual schema/grounding/type reasons or good/bad rejects can be calculated. Header-only `rejection_examples.csv` and `unicode_offset_failures.csv` mean **samples unavailable**, not zero failures.

Real reachable rejection conditions, grouped without fabricated historical frequencies:

- Draft-shape type/value errors during dictionary conversion, membership checks or offset handling.
- `quote and surface_text are required`.
- `no exact source occurrence for surface within quote` (merges missing quote and missing surface into one early rejection).
- `surface occurrence is ambiguous` when preferred offset is not an exact occurrence and multiple recoverable occurrences remain.
- Pydantic literal/type/length/extra-field/confidence/qualifier-dictionary errors, plus text trimming and span validators. `qualifiers` has unconstrained dictionary values; there is no semantic qualifier validator.
- Defensive grounding messages: outside chunk, slice mismatch, quote absent, surface outside quoted occurrence. Most malformed reported offsets are corrected before these checks in the actual v1.3 path.

There is no dedicated canonical-name semantic entailment check, ontology role check, conflict detector or rejection reason `DUPLICATE`. Canonical names only have structural text constraints; concept-type validation checks enum membership, not whether the type suits the source concept.

## Unicode and quote strategy

Evidence source is preserved literally. Identity normalization (`NFKC`, casefold, punctuation/space normalization) is applied **only to canonical_name for concept identity after validation**; it does not rewrite chunk text, quote or surface before grounding. Python indexes Unicode codepoints, not UTF-8 bytes or JavaScript UTF-16 units.

A model rewriting source `NO 2` into surface/quote `NO2`, or replacing a subscript/dash/special space, can be rejected by exact occurrence checking. A wrong reported offset with otherwise unique exact quote/surface is reanchored, so an assertion that incorrect LLM numeric offsets alone cause all 686 rejects is inconsistent with this code path. Reported end offsets are always recomputed.

Actual **accepted** chemistry examples refute a universal formula-normalization failure: D001's canonical NO2 is grounded on surface `NO 2` at `[755,759)`, D095 uses literal `NO(2)`, and accepted quotes include NH 3/H 2 S and Greek/scientific notation. Every persisted accepted slice passes current exact validation. D039's Unicode source is intact but has no retained model candidates. Neither a systematic Unicode rejection rate nor any real rejected quote/paraphrase example can be recovered. The requested split `SEMANTICALLY_CORRECT_BUT_GROUNDING_INVALID` vs `ACTUALLY_BAD_CANDIDATE` is **unknown**, not zero in either class.

Existing contract tests were run offline: **11 passed**. They exercise Unicode slices, type/schema checks, exact quote failures, NFKC identity behavior and unique/ambiguous reanchoring. They establish code behavior, not the causes of historical rejects.

## Inference budget and retries

Actual semantic runner/provider path, not the similarly named production graph extractor:

| Parameter | Evidence |
|---|---|
| Model / digest | qwen3.5:4b-q4_K_M / 2a654d98e6fba55d452b7043684e9b57a947e393bbffa62485a7aac05ee4eefd; DB/checkpoint, currently installed digest matches |
| Extractor / schema | hybrid-technical-concepts-v1.3 / technical-concept-mention-v1 |
| Temperature / thinking | schema request temperature 0 / explicit thinking=false |
| Output budget | current HEAD tries 2048, retries once at 3072 on InferenceOutputLimit |
| Context request | **omitted**: `_extract` never passes context_window; config/models.yaml graph_extractor.context_window=16384 is not read by this runner |
| Observed runtime context | active host log shows n_ctx/ctx-size=4096, OLLAMA_CONTEXT_LENGTH=0 and OLLAMA_NUM_PARALLEL=1; log-wide observation, not per-request response metadata |
| Model context capacity | current `/api/show` metadata says 262144; capacity is not effective request context |
| Timeout | request/generation deadline 300 s; HTTP transport 300 s, connect 10 s |
| Concurrency / batching | serial chunk calls; GenerationGate waiting_capacity=0; no cross-document inference batch |
| General retry policy | only one internal length retry in current HEAD; other failures require explicit checkpoint resume/outer document retry |
| Calls / latency | checkpoint counted 138 returned chunk request attempts; total run 3.608 h, document median 102.8 s, p95 238.9 s |

HYBRID-001 README explicitly reports an output-limit incident followed by a 3072-token retry. D010 is the **only** DB row with attempts=2, so associating that documented incident with D010 is strongly supported but still an **inference from report+attempt count**, not a retained run/document-labelled `done_reason` trace. D010's final zero result is confirmed; neither its final candidate array nor rejection reasons were preserved. Checkpoint call counters advance only after `_extract` returns, so an aborted call need not be counted; 139 time-window HTTP calls vs 138 checkpoint calls are consistent with this, not independent proof of the exact failed-call identity.

No terminal JSON/timeout failures remain in the final DB/checkpoint: 100 completed, 0 failed. This does not prove there were no transient protocol errors. The cleared D010 error and discarded provider metadata prevent a precise reconstruction. No cross-document batching exists, so an output's last document/batch-position explanation is inapplicable. We cannot estimate whether output budgets indirectly reduced concept selection.

## Top-30 semantic and connectivity audit

All mentions/quotes for the ranked top 30 concepts were reviewed, with stable ranking by degree/type/name/id. `high_degree_concepts.csv` classifies each node. Degree 19 NO2 is a useful analyte concept **with contaminated document membership**: four documents D005/D013/D034/D094 anchor only generic `gas`, `gases` or even `liquids`, and their entire stored text contains no NO2 or ammonia. NH3 has the same four unsupported document links. Source-grounded string validation passes all eight mentions, but specific canonical identity is not semantically entailed.

`accepted_semantic_findings.csv` lists these **eight accepted** counterexamples, not rejected examples. Verified supported NO2 document presence is 15/19 and NH3 10/14 for these particular nodes. Negative-response/interferent mentions (for example D061 NO2 and D057 N2) are legitimate analyte occurrences, not proof of successful target sensing.

Additional top-30 errors: graphene and graphene oxide are typed ANALYTE although reviewed contexts use them as materials; graphene sensors is typed MATERIAL although it names devices. Generic process nodes such as sensing, fabrication, detection, response and sensitivity link dissimilar devices; PROPERTY selectivity/sensitivity can be valid comparison dimensions but their unqualified existence is weak evidence for similarity. These are measured source/canonical/type interface defects, not evidence of why rejected candidates were lost.

Offline pair sensitivity calculations, with **no graph mutations**:

| Counterfactual on the same retained graph | Connected document pairs |
|---|---:|
| All final concepts | 476 |
| Remove all 12 top-30 nodes marked TOO_GENERIC | 327 |
| Remove only the eight unsupported NO2/NH3 mentions | 397 |

The 12 generic nodes participate in 184 distinct pairs (38.66% of 476); only 149 pairs disappear when those nodes are excluded because other concepts support overlapping pairs. Under this explicit top-30 review, the 476 pairs are **not mostly generic-only**, although generic connectivity is substantial. Removing the eight unsupported analyte mentions alone removes 79 pairs (16.60%); this is a sensitivity calculation, not a measured false-positive relevance rate. Effects overlap and must not be added. Shared analytes/materials/mechanisms do not by themselves establish retrieval quality or claim equivalence. The old threshold-based semantic-collapse flag being false cannot certify semantic provenance.

## Answers to the ten requested questions

1. **Why 27/100 zeros?** All have no retained mentions before projection. Exact model-empty vs all-rejected cause remains UNKNOWN for each; 26 sources contain clear concepts, one is low-specificity. Available artifacts prove the missing discriminator.
2. **What happened to 686 rejects?** They were counted in successful `_extract` returns and discarded before persistence, without candidate fields/reasons/document assignment. Retry prefixes may be included.
3. **How many bad vs useful-but-grounding-invalid?** Unavailable. No defensible percentages or real historical rejected examples exist in inspected artifacts.
4. **Systematic Unicode/chemical-formula problem?** Possible exact quote/surface mismatch mechanism, no measured historical frequency. Identity normalization does not alter source grounding; incorrect offsets are recoverable when exact occurrence is unique.
5. **Truncation/runtime problem?** One output-budget incident is documented; D010 is the only retried document and remained zero. Causal contribution to the 27 is unknown. No extraction batch-position problem exists.
6. **PostgreSQL→Neo4j loss?** No for the exact final persisted run: 747 identical mention IDs/provenance records, all 100 document counts match.
7. **Why 89 raw vs 73 Hybrid?** 23 raw-positive documents became semantic-zero and seven baseline zeros gained concepts: net −16. Pipeline evidence cannot assign model/validator causes to those 23.
8. **Change Hybrid architecture?** No architectural replacement is supported by these data. The additive stores/projection work and typed concepts expose more shared structure.
9. **Is extractor/validator interface refinement sufficient?** It is the justified next scope: retain diagnostics and enforce/review canonical-to-source and type semantics. Sufficiency for recovery remains unmeasured; do not promise coverage gains.
10. **Accept Hybrid as target architecture now?** **ACCEPT_WITH_REFINEMENT** as an additive target, with source-entailment and extraction-quality gates pending; not an acceptance of current quality or a demonstrated retrieval gain.

No principal bottleneck A–G can honestly be selected for the **historical zero-document cause**. The correct user-permitted outcome is **E/UNKNOWN: insufficient artifacts**. Independently observed quality problems concern extractor/validator semantic contract and generic connectivity; those do not establish a mixed historical zero-cause diagnosis.

Final verdicts: **HYBRID_ARCHITECTURE=ACCEPT_WITH_REFINEMENT; CURRENT_EXTRACTOR=REFINE; CURRENT_VALIDATOR=REFINE.** Architecture: exact additive persistence/projection, 60 shared concepts vs six raw features, with uncertain retrieval gain. Extractor: 27 zero documents including 23 raw-positive and 26 with visible concepts, plus eight unsupported accepted analyte identities. Validator: 747 exact string-grounded mentions and no projection loss justify retaining strict provenance; enum/string validation does not establish semantic identity/type entailment, and reject observability is missing. No evidence supports replacing either component or relaxing grounding.

Controlled rerun was **not performed**. It is unnecessary to establish this historical evidence-insufficiency result, and cannot reconstruct the discarded original 686 candidates. An instrumented isolated 5-document replay would be needed to diagnose *reproducible current behavior*; recommendations specify the gates and preserve UNKNOWN for the historical run.
