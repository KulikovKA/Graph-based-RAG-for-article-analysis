# HYBRID-001 semantic concept graph experiment

## Execution

The additive migration is applied through `0007_hybrid_semantic_concepts`; the existing database advanced from `0005_graph002_shadow`. Historical migration `0003` was not changed or rerun. The run used the frozen GRAPH-002 snapshot `5b80378fa2d8312951446fcbb3ada7994d775f13d452ff08fd415377a5fcade0` and local Ollama model `qwen3.5:4b-q4_K_M` with digest `2a654d98e6fba55d452b7043684e9b57a947e393bbffa62485a7aac05ee4eefd`.

The 10-document smoke passed with 10/10 successful documents, including audited zero-fact documents D007 and D064. It stored 96 unique mentions and 80 concepts. The full resumable pass then completed 100/100 documents with 747 unique mentions, 532 concepts, and 747 projected `MENTIONS_CONCEPT` edges. One article initially exceeded the 2,048-token response limit; the checkpointed run retried that article at 3,072 tokens and completed without restarting the other 99 documents. The measured run took 3.608 hours, with median extraction latency 102.8 seconds/document and p95 238.9 seconds/document.

Raw graph and GRAPH-002 structures retained their pre-run counts: 100 source documents, 417 raw facts, 409 raw/canonical features, and 417 raw/canonical edges. Hybrid data is stored in additive PostgreSQL tables and the `TechnicalConcept` / `MENTIONS_CONCEPT` Neo4j shadow structures.

## Measured quality summary

- 60 of 532 concepts occur in more than one document; 472 are singletons.
- Hybrid concepts appear in 6 of the audited 30 nearest-neighbor pairs; the raw shared-feature baseline is 0 of those pairs.
- 7 of the 11 raw zero-fact documents received at least one concept.
- The largest hybrid document component has 65 documents. The most frequent concepts are NO2 (19 documents) and NH3 (14); generic process concepts such as sensing, fabrication, response, adsorption, detection, selectivity, and sensitivity also recur. No single concept spans 20% of the corpus, so the configured semantic-collapse flag is false.
- Literal exact recall against the manual shared-concept labels is 1/124 (0.8%). This strict match understates qualified or synonymous wording, but indicates that extraction quality needs review. The run rejected 686 candidate mentions through validation.

The measured decision is **B - Hybrid promising but needs refinement**: pair coverage and zero-fact recovery improved, while literal audit recall is weak and the large connected component needs human review. This experiment does not establish a retrieval-quality gain.

## Artifacts

`hybrid_metrics.json`, `performance.json`, and `comparison.md` contain the summary. CSV files include zero-fact recovery, nearest-pair comparisons, concept types, top/shared/singleton concepts, high-degree review, a source-quote sample, and extraction failures. `baseline_after_smoke.json` and `baseline_after_full.json` record raw and GRAPH-002 immutability checks. The full run checkpoint is `data/checkpoints/hybrid-001-full-v1.3.json`.

Generate the reports from the completed checkpoint with:

```powershell
docker compose --profile tools run --rm --no-deps `
  -v "${PWD}/docs/validation/HYBRID-001:/opt/app/docs/validation/HYBRID-001" `
  -v "${PWD}/docs/analysis/GRAPH_CORPUS_AUDIT:/opt/app/docs/analysis/GRAPH_CORPUS_AUDIT:ro" `
  --entrypoint python corpus-runner /opt/app/scripts/hybrid_concept_report.py `
  --checkpoint data/checkpoints/hybrid-001-full-v1.3.json
```

The extractor never fetches OpenAlex/EPO data, creates revisions, or indexes Qdrant articles. Production retrieval and the raw graph are unchanged.
