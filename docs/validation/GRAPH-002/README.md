# GRAPH-002 — TechnicalFeature Canonicalization

Run: `95f0e6c8-83b8-4788-9641-4c08b249e717`<br>
Resolver: `graph002-technical-feature-v1`<br>
Snapshot: `5b80378fa2d8312951446fcbb3ada7994d775f13d452ff08fd415377a5fcade0`<br>
Documents: 100 active revisions with completed graph extraction<br>
GraphFacts: 417 `DISCLOSES_FEATURE` facts<br>
Qdrant shadow collection: `graph_feature_mentions_graph002_technical_featu_3dcc0a1ee166b09a5b67`

The report compares the production baseline and canonical shadow graph on this exact snapshot.
The baseline `GraphFact`, `TechnicalFeature`, `DISCLOSES_FEATURE`, article-chunk collection,
extractor, and retrieval path were not changed. Canonicalization decisions and `GraphFact`
resolutions are in the four `canonicalization_runs`, `canonical_features`,
`feature_pair_decisions`, and `feature_resolutions` PostgreSQL tables.

Artifacts:

- `before.json` — baseline graph metrics
- `after.json` — 0.95 materialization, decision counts,
  quality samples, and timing
- `comparison.json` / `comparison.md` — same-snapshot comparison and 0.90/0.95 sensitivity
- `same_pairs.csv`, `uncertain_pairs.csv`, `conflicts.csv`, `clusters.csv` — review data

If this run stopped before completion, resume it with:

```powershell
python scripts/graph002_canonicalize.py `
  --run-id 95f0e6c8-83b8-4788-9641-4c08b249e717 `
  --checkpoint data/checkpoints/graph002/95f0e6c8-83b8-4788-9641-4c08b249e717.json `
  --resume
```

For another run, apply the additive PostgreSQL migration first with `alembic upgrade head`.
The configured Qwen3 Embedding 0.6B and Tev1:4b digests are checked against the installed
inference runtime; the runner does not pull models.

## Neo4j queries for the morning review

Baseline graph:

```cypher
MATCH p=(d)-[:DISCLOSES_FEATURE]->(f:TechnicalFeature)
RETURN p
LIMIT 300;
```

Canonical shadow graph:

```cypher
MATCH p=(d)-[:DISCLOSES_CANONICAL_FEATURE]->(f:CanonicalTechnicalFeature)
RETURN p
LIMIT 300;
```

Only shared canonical features:

```cypher
MATCH (d)-[:DISCLOSES_CANONICAL_FEATURE]->(f:CanonicalTechnicalFeature)
WITH f, collect(DISTINCT d) AS docs
WHERE size(docs) > 1
UNWIND docs AS d
MATCH p=(d)-[:DISCLOSES_CANONICAL_FEATURE]->(f)
RETURN p
LIMIT 300;
```

Top shared canonical features:

```cypher
MATCH (d)-[:DISCLOSES_CANONICAL_FEATURE]->(f:CanonicalTechnicalFeature)
WITH f, count(DISTINCT d) AS documents
RETURN
  f.canonical_text AS feature,
  documents
ORDER BY documents DESC
LIMIT 50;
```
