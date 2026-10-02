# GRAPH-002-CAL benchmark comparison

Gold set: 143 labeled pairs; SHA-256 `dfa05987a13f20e1fb6a1eafed9c645e1c43e234a48a7dde70112887b4dc8dba`.

| Metric | Strict 3-class | 5-class |
|---|---:|---:|
| Accuracy | 0.6923076923076923 | 0.4755244755244755 |
| Macro F1 | 0.42722794446932383 | 0.3798425011199396 |
| SAME precision | 0.3392857142857143 | 0.32653061224489793 |
| SAME recall | 0.9047619047619048 | 0.7619047619047619 |
| SAME F1 | 0.49350649350649356 | 0.45714285714285713 |
| False merges | 37 | 33 |

Selected: **3-class**. Acceptance gate: **failed**.
Reason: Neither contract meets SAME precision >= 0.95 with zero safety-critical false merges; selected the higher-scoring benchmark by SAME precision, false merges, recall, then macro F1.

The threshold applies only to `P(SAME)` after the predicted label is SAME. Model confidence is recorded for diagnostics and is not a second threshold.

## Threshold sweeps

### 3-class

| P(SAME) threshold | Precision | Recall | Accepted SAME | False merges | Safety-critical false SAME |
|---:|---:|---:|---:|---:|---:|
| 0.70 | 0.421 | 0.762 | 38 | 22 | 0 |
| 0.75 | 0.379 | 0.524 | 29 | 18 | 0 |
| 0.80 | 0.346 | 0.429 | 26 | 17 | 0 |
| 0.85 | 0.214 | 0.143 | 14 | 11 | 0 |
| 0.90 | 0.000 | 0.000 | 9 | 9 | 0 |
| 0.95 | 0.000 | 0.000 | 3 | 3 | 0 |

### 5-class

| P(SAME) threshold | Precision | Recall | Accepted SAME | False merges | Safety-critical false SAME |
|---:|---:|---:|---:|---:|---:|
| 0.70 | 0.444 | 0.381 | 18 | 10 | 0 |
| 0.75 | 0.429 | 0.286 | 14 | 8 | 0 |
| 0.80 | 0.286 | 0.095 | 7 | 5 | 0 |
| 0.85 | 0.000 | 0.000 | 4 | 4 | 0 |
| 0.90 | 0.000 | 0.000 | 3 | 3 | 0 |
| 0.95 | 0.000 | 0.000 | 0 | 0 | 0 |
