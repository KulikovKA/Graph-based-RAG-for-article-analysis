# GRAPH-002-CAL — Feature Equivalence Calibration

This calibration uses only the existing GRAPH-002 v1 candidate-pair set for the frozen 100-document snapshot. It does not create a corpus, re-extract graph facts, regenerate embeddings, alter v1, or update the production graph/retrieval path.

## Source and sampling

- Source run: `95f0e6c8-83b8-4788-9641-4c08b249e717`, resolver `graph002-technical-feature-v1`.
- Frozen snapshot: `5b80378fa2d8312951446fcbb3ada7994d775f13d452ff08fd415377a5fcade0`.
- Source frame: 2,255 persisted `feature_pair_decisions` rows (656 SAME, 1,559 DIFFERENT, 40 UNCERTAIN); candidate similarity, v1 label, same probability, and confidence are retained in the gold CSV.
- Gold sample: 147 distinct existing candidate pairs; 143 manually annotated and 4 retained for manual review. A row with a blank `gold_label` is excluded from the acceptance benchmark.
- Labeled class distribution: SAME 21, RELATED 62, BROADER_NARROWER 19, DIFFERENT 38, UNCERTAIN 3.
- Strata: top 35 v1 SAME by confidence; top 35 by SAME probability; 25 medium-confidence SAME (0.70–0.90); 25 low-confidence SAME (<0.70); 40 high-similarity v1 DIFFERENT; and 40 v1 UNCERTAIN, plus explicit alias and safety contrast cases where present.
- Representative source context is a short exact GraphFact quote when available, capped at 800 characters per side. Documents are never sent.

Gold labels were assigned from the strict definitions in the task, with an explanatory note per row. Tev1 output is included only as a sampling stratum and comparison field, never as gold truth. Explicit examples include graphene versus its structural description (RELATED), gas sensor subtype pairs (BROADER_NARROWER), `transparency`/`transparent` and other alias pairs (SAME), and analyte/polarity/property contrasts (DIFFERENT). Four ambiguous sample rows remain unlabeled for review.

The existing frame contains explicit n-type/p-type, NO2/NH3, and high/low selectivity pairs, which are included. It has no exact room-temperature operation versus room-temperature synthesis pair, nor an exact `gas sensing` versus `NO2 sensing` phrase pair; the closest available broader/narrower sensor examples are included instead.

## Contracts and execution

`feature-equivalence-v2` is independent of `feature-equivalence-v1`. The 3-class contract collapses RELATED and BROADER_NARROWER into DIFFERENT for merge purposes; the 5-class contract preserves them. Both use the same strict SAME definition and short symmetric source contexts. Only SAME can be a merge candidate.

The benchmark runner uses the already-installed `tev1:4b` and configured digest through `/v1/systemone`. It records every contract/pair result in a versioned JSONL cache, so an interrupted run can resume without repeating completed calls. The threshold policy is `decision == SAME AND P(SAME) >= threshold`; confidence is diagnostic only, avoiding a second-threshold ambiguity. Both contracts are swept at 0.70, 0.75, 0.80, 0.85, 0.90, and 0.95.

## GRAPH-002 v1 implementation inspection

- Current contract, labels, prompt criteria, and probability validation: `src/app/services/feature_equivalence.py` (`feature-equivalence-v1`; SAME/DIFFERENT/UNCERTAIN).
- Relation-classifier labels are separate in `src/app/services/relation_classifier.py`; they are not canonical-equivalence labels.
- v1 persists pair labels, `probabilities_json`, confidence, similarity, and latency in PostgreSQL `feature_pair_decisions`; the additive schema is `migrations/versions/0005_graph002_shadow.py`.
- The merge threshold is applied in `src/app/services/graph002.py::constrained_clusters`: v1 requires decision SAME and both SAME probability and confidence >= threshold. This is the double-threshold policy v2 calibration explicitly replaces with one documented SAME-probability threshold.
- Candidate pairs are generated from feature embeddings in `scripts/graph002_canonicalize.py`; the Qdrant shadow collection is versioned by its `FeatureEmbeddingSpec`. Classification decisions are also cached in `feature_pair_decisions` and the checkpoint.
- v1 materialization is in `scripts/graph002_canonicalize.py::_persist_materialization`; projection uses `src/app/integrations/neo4j.py`. Its labels and relationship stay isolated from baseline `TechnicalFeature`/`DISCLOSES_FEATURE`.
- A retry of the same v1 run reuses persisted classifier decisions and only classifies missing pairs. The current runner still rebuilds candidate hits from its feature vector collection; it embeds only features missing from that collection. Reusing v1's candidate list in a distinct v2 run would need an explicit candidate-pair input or reuse path, which is only relevant if the calibration gate passes.

Run from the repository root:

```powershell
$env:PYTHONPATH = "src"
.\.venv\Scripts\python.exe scripts/graph002_calibration.py
```

The report, per-contract benchmark JSON, mismatch CSVs, safety audit, selected contract, and raw decisions are stored here. Full resolver v2 is allowed only if a contract reaches SAME precision >= 0.95 and has zero safety-critical false SAME at the selected threshold.
