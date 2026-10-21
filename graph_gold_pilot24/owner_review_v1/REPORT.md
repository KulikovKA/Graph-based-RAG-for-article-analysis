# Owner-reviewed Gold Dataset — pilot24

All 24 documents are **HUMAN_REVIEWED**, with **human_review_status=APPROVED**, on the project owner's explicit confirmation of personal manual review in chat. Review date: **2026-10-21**. Primary annotator: **project_owner**; secondary annotator: **null**; method: **manual_owner_review**.

Standard: **HUMAN_REVIEWED_GOLD_STANDARD**; origin: **AI_GENERATED**; evaluation status: **OWNER_APPROVED_FOR_EVALUATION**. This is a single-owner review, not independent double annotation. Inter-annotator agreement is not measured.

| Document | Split | Mentions | Assertions | Unique triples | Abstentions | Annotation status | Check |
|---|---|---:|---:|---:|---:|---|---|
| D001 | DEV | 61 | 51 | 50 | 0 | HUMAN_REVIEWED | PASS |
| D003 | DEV | 69 | 47 | 44 | 0 | HUMAN_REVIEWED | PASS |
| D004 | DEV | 47 | 24 | 22 | 0 | HUMAN_REVIEWED | PASS |
| D010 | DEV | 105 | 99 | 77 | 0 | HUMAN_REVIEWED | PASS |
| D060 | DEV | 23 | 12 | 12 | 0 | HUMAN_REVIEWED | PASS |
| D078 | DEV | 72 | 39 | 38 | 0 | HUMAN_REVIEWED | PASS |
| D035 | DEV | 34 | 15 | 15 | 0 | HUMAN_REVIEWED | PASS |
| D092 | DEV | 43 | 19 | 19 | 0 | HUMAN_REVIEWED | PASS |
| D017 | DEV | 37 | 28 | 27 | 0 | HUMAN_REVIEWED | PASS |
| D038 | DEV | 27 | 17 | 17 | 0 | HUMAN_REVIEWED | PASS |
| D026 | DEV | 31 | 19 | 19 | 0 | HUMAN_REVIEWED | PASS |
| D024 | DEV | 40 | 20 | 19 | 3 | HUMAN_REVIEWED | PASS |
| D018 | CALIBRATION | 46 | 32 | 32 | 2 | HUMAN_REVIEWED | PASS |
| D050 | CALIBRATION | 30 | 19 | 19 | 2 | HUMAN_REVIEWED | PASS |
| D029 | CALIBRATION | 32 | 18 | 18 | 0 | HUMAN_REVIEWED | PASS |
| D042 | CALIBRATION | 51 | 24 | 20 | 5 | HUMAN_REVIEWED | PASS |
| D021 | CALIBRATION | 24 | 16 | 16 | 0 | HUMAN_REVIEWED | PASS |
| D093 | CALIBRATION | 24 | 12 | 12 | 1 | HUMAN_REVIEWED | PASS |
| D068 | HOLDOUT | 42 | 24 | 24 | 1 | HUMAN_REVIEWED | PASS |
| D070 | HOLDOUT | 40 | 27 | 27 | 2 | HUMAN_REVIEWED | PASS |
| D098 | HOLDOUT | 30 | 21 | 21 | 1 | HUMAN_REVIEWED | PASS |
| D088 | HOLDOUT | 51 | 32 | 27 | 3 | HUMAN_REVIEWED | PASS |
| D061 | HOLDOUT | 48 | 25 | 23 | 2 | HUMAN_REVIEWED | PASS |
| D090 | HOLDOUT | 24 | 17 | 17 | 1 | HUMAN_REVIEWED | PASS |

Totals: **1031 mentions, 657 assertions, 615 unique canonical triples, 23 abstentions**. Structural result: **24/24 PASS**.

Every source span, evidence item, relation, qualifier, modality, polarity, canonical identity and all 23 abstention objects are identical to the approved AI baseline after projecting only explicit review metadata. Original AI drafts and prior release manifests remain historical. Nested annotations are marked HUMAN_REVIEWED; historical abstention decision records are preserved exactly.

The immutable Ontology v1.0 and its technical-freeze hashes are unchanged. Separate owner-review metadata schemas permit human approval without modifying semantic ontology constraints. No A/B/F/C/D experiments were started.

Eighteen DEV/CALIBRATION Gold files are in annotations/gold/. The six HOLDOUT Gold files, snapshots, review patches, individual hashes and validation details remain in closed local storage outside Git. Public HOLDOUT rows contain review metadata and counts only.
