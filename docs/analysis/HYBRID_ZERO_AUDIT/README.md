# HYBRID-002 — zero-concept / rejection forensic audit

**Result: historical cause is UNKNOWN for all 27 zero-concept documents. The available pipeline discards the fields needed to distinguish MODEL_EMPTY from ALL_REJECTED. Final PostgreSQL, checkpoint and Neo4j agree on all 747 accepted mentions; no projection loss was found.**

Audited HEAD `14470be839a6aaddca2328c36cab2e4d6fe0a0fb`, final run `d895217d-ebbe-4117-9066-8ae0ebcd0bdc`, frozen snapshot `5b80378fa2d8312951446fcbb3ada7994d775f13d452ff08fd415377a5fcade0`. Audit 2026-10-02, Europe/Moscow. Initial git status clean. DB read transaction explicitly read-only/repeatable-read; Neo4j read transactions. No extraction calls, model downloads, production/source/config changes, corpus rerun or push.

Findings:

- 100 completed, zero failed; 73 concept docs, 27 zeros; 532 concepts and 692 distinct document–concept incidences.
- Confusion table: raw-positive/Hybrid-positive 66; raw-positive/Hybrid-zero 23; raw-zero/Hybrid-positive seven; raw-zero/Hybrid-zero four.
- Read all 36 chunks of the 27 zeros; checked 136 corpus chunk hashes/spans and 417 frozen raw fact IDs. 26 zeros have obvious source concepts; D048 has low specificity. 80 analytical exact anchors are recorded.
- 686 is a cumulative rejected-candidate **counter**, not a retained population with reasons. No per-document counts or rejected drafts survive; retry-prefix contributions cannot be excluded.
- One documented output-limit retry, sole retried DB document D010, which remained zero. Individual finish reasons/arrays are unavailable. Runtime logs expose 139 time-window chat calls without run/document IDs; effective context observation is 4096, not production graph_extractor's 16384.
- Top-30 review finds generic/type issues and eight accepted NO2/NH3 identities unsupported by their source. Removing those eight links in an offline calculation changes connected pairs 476→397; removing reviewed generic top-30 nodes changes 476→327. Neither operation modified the graph.

Verdicts: `HYBRID_ARCHITECTURE=ACCEPT_WITH_REFINEMENT`, `CURRENT_EXTRACTOR=REFINE`, `CURRENT_VALIDATOR=REFINE`. These do not certify retrieval quality or identify the historical zero cause. Strict provenance must remain; exact string anchoring must be distinguished from semantic identity entailment.

## Artifacts and availability

| File | Meaning |
|---|---|
| [diagnosis.md](diagnosis.md) | Pipeline, retention proof, sources, runtime, connectivity audit and all ten requested answers |
| [recommendations.md](recommendations.md) | Three proposed follow-ups; minimal observer specification and five-document replay design; no fixes implemented |
| [zero_documents.csv](zero_documents.csv) | Exact 27 document/revision IDs, OpenAlex IDs, titles, lengths, chunks, raw facts, status, attempts and source assessment |
| [raw_vs_hybrid_confusion.csv](raw_vs_hybrid_confusion.csv) | All four coverage cells, total 100 |
| [document_diagnostics.csv](document_diagnostics.csv) | All 100 docs; persisted counts and UNKNOWN/unavailable candidate diagnostics |
| [rejection_reasons.csv](rejection_reasons.csv) | 686 in UNRECORDED_AGGREGATE; an availability bucket, not a validator reason |
| [rejection_examples.csv](rejection_examples.csv) | Header only: no historical rejected examples retained; does not mean zero rejected examples |
| [unicode_offset_failures.csv](unicode_offset_failures.csv) | Header only: rejected offsets unavailable; does not mean no Unicode failures |
| [postgres_neo4j_diff.csv](postgres_neo4j_diff.csv) | All 100 per-document counts; mention IDs and projected provenance compared exactly |
| [high_degree_concepts.csv](high_degree_concepts.csv) | Ranked top 30, degree/type/name, source-informed classification and rationale |
| [source_concept_spans.csv](source_concept_spans.csv) | 80 exact codepoint anchors from assistant source reading, not model outputs |
| [accepted_semantic_findings.csv](accepted_semantic_findings.csv) | Eight **accepted** generic-surface→specific-analyte counterexamples |
| [audit_metrics.json](audit_metrics.json) | Reproducible counts, group medians, sensitivity calculations and verdicts |
| [evidence_hashes.json](evidence_hashes.json) | SHA-256 of audited source/code/checkpoint and local read evidence |
| [log_inventory.json](log_inventory.json), [runtime_log_metadata.json](runtime_log_metadata.json), [inference_http_window.csv](inference_http_window.csv) | Sanitized log timestamp/range/config/HTTP metadata; no response bodies |
| [source_annotations.json](source_annotations.json), [high_degree_review.json](high_degree_review.json) | Analytical annotations from full source/quote reading; not independent human gold |

Blank raw/accepted-before-dedup/rejected/acceptance-rate CSV cells and JSON nulls mean **not recorded**, never zero. `accepted_count` is explicitly the number of unique persisted mentions; the number of accepted candidates before dedup cannot be reconstructed. Cause UNKNOWN applies to each historical zero doc.

Full source/database reads (`live_read.json`, `source_reading.txt`) and current model metadata (`runtime_read.json`) remain local and git-ignored, matching GRAPH_CORPUS_AUDIT's corpus-publication policy. Only source excerpts, annotations and diagnostics are committed; no credentials or provider reasoning are retained.

## Reproduction and verification

`collect_live.py` is a standalone read-only audit collector, not inference instrumentation. It can run through stdin inside the existing API container, using its credentials without printing them:

```powershell
Get-Content docs/analysis/HYBRID_ZERO_AUDIT/collect_live.py -Raw -Encoding UTF8 |
  docker exec -i article-analysis-api-1 python - |
  Out-File docs/analysis/HYBRID_ZERO_AUDIT/live_read.json -Encoding utf8
.venv/Scripts/python.exe -X utf8 docs/analysis/HYBRID_ZERO_AUDIT/build_artifacts.py
.venv/Scripts/python.exe -X utf8 docs/analysis/HYBRID_ZERO_AUDIT/inspect_logs.py
.venv/Scripts/python.exe -X utf8 -m pytest tests/unit/test_technical_concepts.py
```

`build_artifacts.py` is offline and requires the original ignored corpus export/checkpoint and local read exports. It asserts frozen identities/hashes/full nonwhitespace source coverage, all 747 exact accepted spans, equality of checkpoint/PG/Neo4j mention IDs and provenance, all 27 annotation identities and all 80 source spans. It only writes files in this audit directory. Historical measurements are captured in the committed CSV/JSON files for environments without the private exports. Existing contract tests: **11 passed**; no production code or tests were changed.

Controlled rerun: **not performed**. Historical evidence insufficiency is established without generation; a future isolated instrumented replay can diagnose reproducible current behavior, but cannot recover the original rejected candidates. Git: analysis-only local commit requested; no push authorized.
