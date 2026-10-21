# D029 — NO2 and NH3 Sensing Characteristics of Inkjet Printing Graphene Gas Sensors

**AI draft — HUMAN_REVIEW=NOT_REVIEWED; не human gold.**

Document `4a17444d-09e0-4cad-becb-0ad9e9a95b73`, revision `94abe07d-65fd-4ac6-96c3-0c65e777ed09`, split `CALIBRATION`, rubric `pilot24-rubric-0.3-AUTO-FROZEN`.

Chunks 1; sentences 5; mentions 32; assertions 16; unique canonical triples 16; questions 1; validation PASS.

Полный AI-проход завершён. exhaustive_entities=True; exhaustive_relations=False; неразрешённые кандидаты не являются negative gold.

## Исходные frozen EvidenceChunks

### `28d1c15e-e2d5-41b9-96f3-dfb222eb27f1`

SHA-256 `1b03dbb818cbfa9687373be6d034d98968ed06e5e12d54386847f91cb999477b`, section `abstract`; [0, 988).

Graphene is a good candidate for filling the market requirements for cheap, high sensitivity, robust towards contamination, low noise, and low power consumption gas sensors, thanks to its unique properties, i.e., large surface, high mobility, and long-term stability. Inkjet printing is a cheap additive manufacturing method allowing fast, relatively precise and contactless deposition of a wide range of materials; it can be considered therefore the ideal technique for fast deposition of graphene films on thin substrates. In this paper, the sensitivity of graphene-based chemiresistor gas sensors, fabricated through inkjet printing, is investigated using different concentrations of graphene in the inks. Samples have been produced and characterized in terms of response towards humidity, nitrogen dioxide, and ammonia. The presented results highlight the importance of tuning the layer thickness and achieving good film homogeneity in order to maximize the sensitivity of the sensor.

## Semantic self-audit

Background market requirements are hypothetical targets, not measured properties of the study sensors.
Only response characterization is stated, so no invented successful DETECTS threshold for each stimulus.
Humidity is a tested stimulus, not device material; ink concentration and thickness values remain unspecified.

## Mentions

| Key | Sentence | Span | Surface | Kind / role | Canonical |
| --- | --- | --- | --- | --- | --- |
| graphene | S1 | [0,8) | Graphene | MATERIAL / technical_material | graphene |
| cheap | S1 | [69,74) | cheap | PROPERTY / technical_property | low cost |
| sensitivity | S1 | [76,92) | high sensitivity | PERFORMANCE / technical_performance | high sensitivity |
| robust | S1 | [94,122) | robust towards contamination | PERFORMANCE / technical_performance | contamination robustness |
| noise | S1 | [124,133) | low noise | PROPERTY / technical_property | low noise |
| power | S1 | [139,160) | low power consumption | PROPERTY / technical_property | low power consumption |
| sensor | S1 | [161,172) | gas sensors | DEVICE / technical_device | prospective graphene gas sensor |
| surface | S1 | [213,226) | large surface | PROPERTY / technical_property | large surface area |
| mobility | S1 | [228,241) | high mobility | PROPERTY / technical_property | high mobility |
| stability | S1 | [247,266) | long-term stability | PERFORMANCE / technical_performance | long-term stability |
| printing | S2 | [268,283) | Inkjet printing | PROCESS / technical_process | inkjet printing |
| cheap2 | S2 | [289,294) | cheap | PROPERTY / technical_property | low cost |
| manufacture | S2 | [295,324) | additive manufacturing method | TECHNOLOGY / technical_technology | additive manufacturing |
| deposit | S2 | [334,385) | fast, relatively precise and contactless deposition | PROCESS / technical_process | fast precise contactless deposition |
| film | S2 | [490,504) | graphene films | MATERIAL / technical_material | graphene film |
| substrate | S2 | [508,523) | thin substrates | DEVICE / technical_device | thin substrate |
| sensitivity3 | S3 | [544,555) | sensitivity | PERFORMANCE / technical_performance | gas sensitivity |
| sensor3 | S3 | [559,599) | graphene-based chemiresistor gas sensors | DEVICE / technical_device | inkjet-printed graphene chemiresistor |
| printing3 | S3 | [620,635) | inkjet printing | PROCESS / technical_process | inkjet printing |
| graphene3 | S3 | [687,695) | graphene | MATERIAL / material | graphene |
| concentrations | S3 | [659,707) | different concentrations of graphene in the inks | OPERATING_CONDITION / technical_operating_condition | graphene ink concentration variation |
| inks | S3 | [703,707) | inks | MATERIAL / technical_material | graphene ink |
| samples | S4 | [709,716) | Samples | DEVICE / technical_device | inkjet-printed graphene chemiresistor |
| response | S4 | [766,774) | response | PERFORMANCE / technical_performance | gas sensor response |
| humidity | S4 | [783,791) | humidity | ANALYTE / environmental_stimulus | humidity stimulus |
| no2 | S4 | [793,809) | nitrogen dioxide | ANALYTE / technical_analyte | nitrogen dioxide |
| nh3 | S4 | [815,822) | ammonia | ANALYTE / technical_analyte | ammonia |
| tuning | S5 | [874,900) | tuning the layer thickness | PROCESS / technical_process | layer thickness tuning |
| thickness | S5 | [885,900) | layer thickness | PROPERTY / technical_property | sensing layer thickness |
| homogeneity | S5 | [915,936) | good film homogeneity | PROPERTY / technical_property | film homogeneity |
| sensitivity5 | S5 | [962,973) | sensitivity | PERFORMANCE / technical_performance | gas sensitivity |
| sensor5 | S5 | [981,987) | sensor | DEVICE / technical_device | inkjet-printed graphene chemiresistor |

## Assertions

| Head | Relation | Tail | Polarity | Modality / scope | Qualifiers | Evidence span IDs |
| --- | --- | --- | --- | --- | --- | --- |
| graphene | HAS_PROPERTY | surface | POSITIVE | ASSERTED / BACKGROUND |  | 544fe366-4fe9-5794-a71d-30663437c92f |
| graphene | HAS_PROPERTY | mobility | POSITIVE | ASSERTED / BACKGROUND |  | 544fe366-4fe9-5794-a71d-30663437c92f |
| graphene | HAS_PERFORMANCE | stability | POSITIVE | ASSERTED / BACKGROUND |  | 544fe366-4fe9-5794-a71d-30663437c92f |
| sensor | HAS_PERFORMANCE | sensitivity | POSITIVE | HYPOTHETICAL / BACKGROUND_REQUIREMENT |  | 544fe366-4fe9-5794-a71d-30663437c92f |
| sensor | HAS_PERFORMANCE | robust | POSITIVE | HYPOTHETICAL / BACKGROUND_REQUIREMENT |  | 544fe366-4fe9-5794-a71d-30663437c92f |
| sensor | HAS_PROPERTY | cheap | POSITIVE | HYPOTHETICAL / BACKGROUND_REQUIREMENT |  | 544fe366-4fe9-5794-a71d-30663437c92f |
| sensor | HAS_PROPERTY | noise | POSITIVE | HYPOTHETICAL / BACKGROUND_REQUIREMENT |  | 544fe366-4fe9-5794-a71d-30663437c92f |
| sensor | HAS_PROPERTY | power | POSITIVE | HYPOTHETICAL / BACKGROUND_REQUIREMENT |  | 544fe366-4fe9-5794-a71d-30663437c92f |
| printing | HAS_PROPERTY | cheap2 | POSITIVE | ASSERTED / BACKGROUND |  | 6860e2dd-809a-57ec-aada-34d1ef80934c |
| film | FABRICATED_BY | printing | POSITIVE | PROPOSED / BACKGROUND | deposition_substrate: thin substrates → thin substrates | 6860e2dd-809a-57ec-aada-34d1ef80934c |
| sensor3 | FABRICATED_BY | printing3 | POSITIVE | ASSERTED / STUDY_RESULT |  | f496ccb1-48e2-58cd-97d5-aa1c765ed915 |
| sensor3 | USES_MATERIAL | graphene3 | POSITIVE | ASSERTED / STUDY_RESULT |  | f496ccb1-48e2-58cd-97d5-aa1c765ed915 |
| sensor3 | HAS_PERFORMANCE | sensitivity3 | POSITIVE | ASSERTED / STUDY_RESULT |  | f496ccb1-48e2-58cd-97d5-aa1c765ed915 |
| inks | HAS_COMPONENT | graphene3 | POSITIVE | ASSERTED / STUDY_RESULT |  | f496ccb1-48e2-58cd-97d5-aa1c765ed915 |
| samples | HAS_PERFORMANCE | response | POSITIVE | ASSERTED / STUDY_RESULT | tested_stimuli: humidity, nitrogen dioxide, and ammonia → humidity, nitrogen dioxide, and ammonia | 7dea8cf2-2de1-5d09-9097-89c3376a349a |
| tuning | IMPROVES | sensitivity5 | POSITIVE | PROPOSED / STUDY_RESULT |  | 0ebe590a-3dfb-5199-8429-092a5685ef08 |

## Identity decisions

| Left | Label | Right | Reason |
| --- | --- | --- | --- |
| no2 | DIFFERENT | nh3 | Two named measured gas stimuli; no selectivity ordering supplied. |
| graphene | SAME | graphene3 | Curated source-local repetition/explicit alias; conditions and physical instances remain separate. |
| cheap | SAME | cheap2 | Curated source-local repetition/explicit alias; conditions and physical instances remain separate. |
| printing | SAME | printing3 | Curated source-local repetition/explicit alias; conditions and physical instances remain separate. |
| sensitivity3 | SAME | sensitivity5 | Curated source-local repetition/explicit alias; conditions and physical instances remain separate. |
| sensor3 | SAME | samples | Curated source-local repetition/explicit alias; conditions and physical instances remain separate. |
| sensor3 | SAME | sensor5 | Curated source-local repetition/explicit alias; conditions and physical instances remain separate. |

## Unresolved

# Вопросы документа

Все открытые вопросы UNRESOLVED. Они не блокировали автоматический проход. Q1/Q2/Q3 решены пользователем и находятся в adjudication_decisions.jsonl.

## D029-Q4 — D029

**Статья:** NO2 and NH3 Sensing Characteristics of Inkjet Printing Graphene Gas Sensors.

Document `4a17444d-09e0-4cad-becb-0ad9e9a95b73`; revision `94abe07d-65fd-4ac6-96c3-0c65e777ed09`; split `CALIBRATION`.

**Точный оригинал:**

> The presented results highlight the importance of tuning the layer thickness and achieving good film homogeneity in order to maximize the sensitivity of the sensor.

**Перевод и смысл:** Авторы связывают названную структуру, свойство или процесс с объяснением наблюдаемой характеристики. Текущая схема не содержит подходящего направленного отношения с такими endpoints.

**Что неоднозначно/непокрыто:** Importance of film homogeneity for sensitivity is a PROPERTY → PERFORMANCE effect, not a measured numeric relation.

A. Представить EXPLAINS после отдельного согласования схемы.

B. Сохранить существующую схему и учитывать как непокрытое отношение.

C. Оставить UNRESOLVED до содержательной проверки.

**Предварительное предложение:** A для DEV при подтверждении семантики; B для CALIBRATION/HOLDOUT без изменения схемы.

| Head | Proposed relation | Tail | Modality / polarity |
| --- | --- | --- | --- |
| good film homogeneity | EXPLAINS | sensitivity | ASSERTED / POSITIVE |
