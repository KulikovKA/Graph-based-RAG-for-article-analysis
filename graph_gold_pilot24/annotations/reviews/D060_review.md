# D060 — Enhanced sensitivity of graphene ammonia gas sensors using molecular doping

**AI draft — HUMAN_REVIEW=NOT_REVIEWED; не human gold.**

Document `96575fc6-1212-4cb1-889f-179dd9515854`, revision `61ce4e43-1d79-4cee-af6c-43026828532a`, split `DEV`, rubric `pilot24-rubric-0.3-AUTO-FROZEN`.

Chunks 1; sentences 4; mentions 23; assertions 10; unique canonical triples 10; questions 2; validation PASS.

Полный AI-проход завершён. exhaustive_entities=True; exhaustive_relations=False; неразрешённые кандидаты не являются negative gold.

## Исходные frozen EvidenceChunks

### `006deffa-1906-4677-942b-2a29bd47046b`

SHA-256 `7e3054e2cb1e788c55f6c5f17b4855b0993823ba82f68f8cf3c012bac4ed1393`, section `abstract`; [0, 745).

We report on employing molecular doping to enhance the sensitivity of graphene sensors synthesized via chemical vapor deposition to NH3 molecules at room temperature. We experimentally show that doping an as-fabricated graphene sensor with NO2 gas improves sensitivity of its electrical resistance to adsorption of NH3 molecules by about an order of magnitude. The detection limit of our NO2-doped graphene sensor is found to be ∼200 parts per billion (ppb), compared to ∼1400 ppb before doping. Electrical characterization and Raman spectroscopy measurements on graphene field-effect transistors show that adsorption of NO2 molecules significantly increases hole concentration in graphene, which results in the observed sensitivity enhancement.

## Semantic self-audit

NO2 dopant and NH3 analyte roles preserved; no NO2 DETECTS inferred.
LOD before/after and approximate factor preserved; experiment is asserted, not hypothetical.

## Mentions

| Key | Sentence | Span | Surface | Kind / role | Canonical |
| --- | --- | --- | --- | --- | --- |
| doping | S1 | [23,39) | molecular doping | PROCESS / technical_process | molecular doping |
| sensitivity | S1 | [55,66) | sensitivity | PERFORMANCE / technical_performance | NH3 sensitivity |
| sensor | S1 | [70,86) | graphene sensors | DEVICE / technical_device | graphene sensor |
| cvd | S1 | [103,128) | chemical vapor deposition | PROCESS / technical_process | chemical vapor deposition |
| nh3 | S1 | [132,135) | NH3 | ANALYTE / technical_analyte | ammonia |
| rt | S1 | [149,165) | room temperature | OPERATING_CONDITION / technical_operating_condition | room temperature |
| doping2 | S2 | [195,247) | doping an as-fabricated graphene sensor with NO2 gas | PROCESS / technical_process | NO2 molecular doping |
| sensor2 | S2 | [205,234) | as-fabricated graphene sensor | DEVICE / technical_device | graphene sensor |
| no2 | S2 | [240,243) | NO2 | MATERIAL / dopant | nitrogen dioxide dopant |
| sensitivity2 | S2 | [257,297) | sensitivity of its electrical resistance | PERFORMANCE / technical_performance | NH3 resistance sensitivity |
| adsorb | S2 | [301,328) | adsorption of NH3 molecules | PROCESS / technical_process | NH3 adsorption |
| nh32 | S2 | [315,318) | NH3 | ANALYTE / technical_analyte | ammonia |
| doped | S3 | [388,413) | NO2-doped graphene sensor | DEVICE / technical_device | NO2-doped graphene sensor |
| lod | S3 | [365,380) | detection limit | PERFORMANCE / technical_performance | detection limit |
| before | S3 | [481,494) | before doping | OPERATING_CONDITION / technical_operating_condition | before NO2 doping |
| electrical | S4 | [496,523) | Electrical characterization | PROCESS / technical_process | electrical characterization |
| raman | S4 | [528,559) | Raman spectroscopy measurements | PROCESS / technical_process | Raman spectroscopy |
| fet | S4 | [563,596) | graphene field-effect transistors | DEVICE / technical_device | graphene field-effect transistor |
| adsorb4 | S4 | [607,634) | adsorption of NO2 molecules | PROCESS / technical_process | NO2 adsorption |
| no24 | S4 | [621,624) | NO2 | MATERIAL / dopant | nitrogen dioxide dopant |
| holes | S4 | [659,677) | hole concentration | PROPERTY / technical_property | hole concentration |
| graphene | S4 | [681,689) | graphene | MATERIAL / charge_carrier_host | graphene |
| enhance | S4 | [721,744) | sensitivity enhancement | PERFORMANCE / technical_performance | NH3 sensitivity enhancement |

## Assertions

| Head | Relation | Tail | Polarity | Modality / scope | Qualifiers | Evidence span IDs |
| --- | --- | --- | --- | --- | --- | --- |
| sensor | FABRICATED_BY | cvd | POSITIVE | ASSERTED / STUDY_RESULT |  | a9b4419b-913a-5f56-9bc5-a029722e0af5 |
| doping | IMPROVES | sensitivity | POSITIVE | ASSERTED / STUDY_RESULT |  | a9b4419b-913a-5f56-9bc5-a029722e0af5 |
| sensor | DETECTS | nh3 | POSITIVE | ASSERTED / STUDY_RESULT | temperature: room temperature → room temperature | a9b4419b-913a-5f56-9bc5-a029722e0af5 |
| doping2 | ACTS_ON | sensor2 | POSITIVE | ASSERTED / STUDY_RESULT | dopant: NO2 gas → NO2 gas | 4f6df152-def2-5cf6-93b9-b1b8410f79da |
| doping2 | IMPROVES | sensitivity2 | POSITIVE | ASSERTED / STUDY_RESULT | improvement_factor: about an order of magnitude → about an order of magnitude | 4f6df152-def2-5cf6-93b9-b1b8410f79da |
| doped | HAS_PERFORMANCE | lod | POSITIVE | COMPARED / STUDY_RESULT | doped_detection_limit: ∼200 parts per billion (ppb) → 200; undoped_detection_limit: ∼1400 ppb before doping → 1400 | 9bb648f3-2e41-52e0-afd1-9bc58857d960 |
| electrical | ACTS_ON | fet | POSITIVE | ASSERTED / STUDY_RESULT |  | b7acc52e-a60e-526c-9bcf-4965b07fb208 |
| raman | ACTS_ON | fet | POSITIVE | ASSERTED / STUDY_RESULT |  | b7acc52e-a60e-526c-9bcf-4965b07fb208 |
| fet | USES_MATERIAL | graphene | POSITIVE | ASSERTED / STUDY_RESULT |  | b7acc52e-a60e-526c-9bcf-4965b07fb208 |
| graphene | HAS_PROPERTY | holes | POSITIVE | ASSERTED / STUDY_RESULT |  | b7acc52e-a60e-526c-9bcf-4965b07fb208 |

## Identity decisions

| Left | Label | Right | Reason |
| --- | --- | --- | --- |
| sensor | BROADER | doped | Doped configuration is narrower than generic graphene sensor; do not merge before/after instances. |
| sensor | SAME | sensor2 | Curated source-local repetition/explicit alias; conditions and physical instances remain separate. |
| nh3 | SAME | nh32 | Curated source-local repetition/explicit alias; conditions and physical instances remain separate. |
| no2 | SAME | no24 | Curated source-local repetition/explicit alias; conditions and physical instances remain separate. |

## Unresolved

# Вопросы документа

Все открытые вопросы UNRESOLVED. Они не блокировали автоматический проход. Q1/Q2/Q3 решены пользователем и находятся в adjudication_decisions.jsonl.

## D060-Q4 — D060

**Статья:** Enhanced sensitivity of graphene ammonia gas sensors using molecular doping.

Document `96575fc6-1212-4cb1-889f-179dd9515854`; revision `61ce4e43-1d79-4cee-af6c-43026828532a`; split `DEV`.

**Точный оригинал:**

> Electrical characterization and Raman spectroscopy measurements on graphene field-effect transistors show that adsorption of NO2 molecules significantly increases hole concentration in graphene, which results in the observed sensitivity enhancement.

**Перевод и смысл:** Величина явно увеличивается под действием указанного фактора. Это направление изменения; оно не всегда равнозначно улучшению качества.

**Что неоднозначно/непокрыто:** Увеличение концентрации носителей — направление изменения; не тождественно улучшению качества.

A. Представить INCREASES после отдельного согласования схемы.

B. Сохранить существующую схему и учитывать как непокрытое отношение.

C. Оставить UNRESOLVED до содержательной проверки.

**Предварительное предложение:** A для DEV при подтверждении семантики; B для CALIBRATION/HOLDOUT без изменения схемы.

| Head | Proposed relation | Tail | Modality / polarity |
| --- | --- | --- | --- |
| adsorption of NO2 molecules | INCREASES | hole concentration | ASSERTED / POSITIVE |

## D060-Q5 — D060

**Статья:** Enhanced sensitivity of graphene ammonia gas sensors using molecular doping.

Document `96575fc6-1212-4cb1-889f-179dd9515854`; revision `61ce4e43-1d79-4cee-af6c-43026828532a`; split `DEV`.

**Точный оригинал:**

> Electrical characterization and Raman spectroscopy measurements on graphene field-effect transistors show that adsorption of NO2 molecules significantly increases hole concentration in graphene, which results in the observed sensitivity enhancement.

**Перевод и смысл:** Авторы связывают названную структуру, свойство или процесс с объяснением наблюдаемой характеристики. Текущая схема не содержит подходящего направленного отношения с такими endpoints.

**Что неоднозначно/непокрыто:** Адсорбция NO2 через повышение hole concentration объясняет усиление чувствительности; причинный effect не выражается ACTS_ON.

A. Представить EXPLAINS после отдельного согласования схемы.

B. Сохранить существующую схему и учитывать как непокрытое отношение.

C. Оставить UNRESOLVED до содержательной проверки.

**Предварительное предложение:** A для DEV при подтверждении семантики; B для CALIBRATION/HOLDOUT без изменения схемы.

| Head | Proposed relation | Tail | Modality / polarity |
| --- | --- | --- | --- |
| adsorption of NO2 molecules | EXPLAINS | sensitivity enhancement | ASSERTED / POSITIVE |
