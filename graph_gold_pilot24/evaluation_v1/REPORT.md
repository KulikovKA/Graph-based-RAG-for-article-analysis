# Annotation migration to the approved pilot v1.0

Ontology status: **HUMAN_APPROVED_FOR_PILOT_V1** (user decision 2026-10-21). Annotation status: **AI_DRAFT / NOT_REVIEWED**. Human gold: **0/24**. No A/B/F/C/D experiments were started.

CALIBRATION was reannotated and validated first; HOLDOUT followed separately. Definitions, domain/range and qualifier schema retain the original byte hashes. The 0.3 baseline and all old evaluation drafts are preserved. Technical freeze history remains immutable; approval is a sidecar.

| Document | Split | Mentions | Assertions | Unique canonical triples | Abstention cases | Check |
|---|---|---:|---:|---:|---:|---|
| D001 | DEV | 61 | 51 | 50 | 0 | PASS |
| D003 | DEV | 69 | 47 | 44 | 0 | PASS |
| D004 | DEV | 47 | 24 | 22 | 0 | PASS |
| D010 | DEV | 105 | 99 | 77 | 0 | PASS |
| D060 | DEV | 23 | 12 | 12 | 0 | PASS |
| D078 | DEV | 72 | 39 | 38 | 0 | PASS |
| D035 | DEV | 34 | 15 | 15 | 0 | PASS |
| D092 | DEV | 43 | 19 | 19 | 0 | PASS |
| D017 | DEV | 37 | 28 | 27 | 0 | PASS |
| D038 | DEV | 27 | 17 | 17 | 0 | PASS |
| D026 | DEV | 31 | 19 | 19 | 0 | PASS |
| D024 | DEV | 40 | 20 | 19 | 3 | PASS |
| D018 | CALIBRATION | 46 | 32 | 32 | 2 | PASS |
| D050 | CALIBRATION | 30 | 19 | 19 | 2 | PASS |
| D029 | CALIBRATION | 32 | 18 | 18 | 0 | PASS |
| D042 | CALIBRATION | 51 | 24 | 20 | 5 | PASS |
| D021 | CALIBRATION | 24 | 16 | 16 | 0 | PASS |
| D093 | CALIBRATION | 24 | 12 | 12 | 1 | PASS |
| D068 | HOLDOUT | 42 | 24 | 24 | 1 | PASS |
| D070 | HOLDOUT | 40 | 27 | 27 | 2 | PASS |
| D098 | HOLDOUT | 30 | 21 | 21 | 1 | PASS |
| D088 | HOLDOUT | 51 | 32 | 27 | 3 | PASS |
| D061 | HOLDOUT | 48 | 25 | 23 | 2 | PASS |
| D090 | HOLDOUT | 24 | 17 | 17 | 1 | PASS |

| Split | Documents | Mentions | Assertions | Unique triples | Abstentions | PASS |
|---|---:|---:|---:|---:|---:|---:|
| DEV | 12 | 589 | 390 | 359 | 3 | 12 |
| CALIBRATION | 6 | 207 | 121 | 117 | 10 | 6 |
| HOLDOUT | 6 | 235 | 146 | 139 | 10 | 6 |

Unique triples ignore repeated source mentions and qualifier/modality/polarity distinctions; full qualified source assertions are preserved. Abstentions count cases rather than candidate edges. Some concern an unsupported numeric qualifier on an otherwise supported base relation. They are never negative gold labels.

Checks cover exact Unicode spans, source/chunk hashes, registered evidence and endpoint coverage, allowed predicates, directed endpoints, group pairs, qualifier types/values/attachment, modality/polarity regressions, canonical identity, ontology/envelope versions, technical freeze hashes, approval identity and lossless diff replay. Structural PASS is not human semantic validation.

The only implementation adaptation is the explicit evaluation provenance envelope described in TECHNICAL_ISSUES.md. No new relation, endpoint or qualifier is introduced. The old frozen DEV validator and its reports remain unchanged.

Calibration snapshots, sources, decisions, patches and per-document audits are under calibration/. HOLDOUT equivalents and the label-level validation report are under the existing closed local storage, outside this repository. This report publishes only document counts/status for HOLDOUT.

The three accepted DEV abstentions are preserved. Evaluation gaps remain abstentions under the fixed schema; they may inform a future version only after this benchmark, without revising pilot-v1 labels or ontology silently. For independent content review and creation of Gold Dataset, follow HUMAN_REVIEW_PROTOCOL.md.
