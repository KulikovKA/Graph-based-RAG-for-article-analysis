# HYBRID-001 measured comparison

Frozen snapshot `5b80378fa2d8312951446fcbb3ada7994d775f13d452ff08fd415377a5fcade0`; run `d895217d-ebbe-4117-9066-8ae0ebcd0bdc`.

| Metric | Raw GRAPH-001 | GRAPH-002 | Hybrid |
|---|---:|---:|---:|
| Nodes | 409 | 409 | 532 |
| Edges / mentions | 417 | 417 | 747 |
| Shared nodes/concepts | 6 | 6 | 60 |
| Singleton concepts | 403 | 403 | 472 |
| Zero-fact / zero-concept documents | 11 | 11 | 27 |
| Connected document pairs | 11 | 11 | 476 |
| Largest component | 4 | 4 | 65 |

Of 30 audited nearest pairs, raw shared features occur in 0.
Hybrid shared concepts occur in 6.
Exact manual concept recall is 0.008064516129032258
(1/124);
this literal string match undercounts semantically equivalent qualified wording.
Hybrid recovers 7 of 11 raw zero-fact documents.
686 model candidates failed strict validation.
High-degree generic concepts: 8.
Flagged high-degree names: sensing, fabrication, response, adsorption, detection, selectivity, selectivity, sensitivity.
Semantic collapse flag: False.

## Decision

**B - Hybrid promising but needs refinement**

Use pair-level evidence and source quotes to assess semantic quality.
