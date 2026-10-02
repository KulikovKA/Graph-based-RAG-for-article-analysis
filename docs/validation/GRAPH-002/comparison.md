# GRAPH-002 before/after comparison

Run: `95f0e6c8-83b8-4788-9641-4c08b249e717`<br>
Resolver: `graph002-technical-feature-v1`<br>
Snapshot: `5b80378fa2d8312951446fcbb3ada7994d775f13d452ff08fd415377a5fcade0` (100 completed active revisions)

All values below use the exact same immutable snapshot. Baseline tables, article chunks, TechnicalFeature nodes, and DISCLOSES_FEATURE relationships remain the production view.

| METRIC | BASELINE | CANONICAL (0.95) | DELTA |
|---|---:|---:|---:|
| documents | 100.00 | 100.00 | +0.00 |
| feature nodes | 409.00 | 409.00 | +0.00 |
| edges | 417.00 | 417.00 | +0.00 |
| shared features | 6.00 | 6.00 | +0.00 |
| shared feature % | 1.47 | 1.47 | +0.00 |
| singleton % | 98.53 | 98.53 | +0.00 |
| connected components | 92.00 | 92.00 | +0.00 |
| largest component docs | 4.00 | 4.00 | +0.00 |
| connected doc pairs | 11.00 | 11.00 | +0.00 |

## Threshold sensitivity

| SAME probability and confidence threshold | Canonical features | Shared feature % | Components | Largest component documents | Connected document pairs |
|---:|---:|---:|---:|---:|---:|
| 0.90 | 406 | 1.72 | 89 | 8 | 17 |
| 0.95 | 409 | 1.47 | 92 | 4 | 11 |

Tev1 candidate pairs: 2255; SAME: 656; DIFFERENT: 1559; UNCERTAIN: 40; cannot-link merges prevented: 0.

Quality examples and the requested manual cases are in `after.json`. The report keeps UNCERTAIN decisions and conflicts visible; it does not mark model-labeled merges as human-verified.
