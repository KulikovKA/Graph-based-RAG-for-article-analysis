# D050 — Flexible room-temperature NO2 gas sensors based on carbon nanotubes/reduced graphene hybrid films

**AI draft — HUMAN_REVIEW=NOT_REVIEWED; не human gold.**

Document `87775318-a9f1-457c-891c-6d910ac56175`, revision `f3937e44-f446-490b-8c4e-7b95768fca8a`, split `CALIBRATION`, rubric `pilot24-rubric-0.3-AUTO-FROZEN`.

Chunks 1; sentences 5; mentions 30; assertions 16; unique canonical triples 16; questions 4; validation PASS.

Полный AI-проход завершён. exhaustive_entities=True; exhaustive_relations=False; неразрешённые кандидаты не являются negative gold.

## Исходные frozen EvidenceChunks

### `468da37d-6e9a-4912-a13a-b5a50250ead3`

SHA-256 `2de59fbd005627ed7c07a8349b727b986790fcc57bdc7ed5b15dd1d1604b67a4`, section `abstract`; [0, 746).

We present a flexible room temperature NO2 gas sensor consisting of vertical carbon nanotubes (CNTs)/reduced graphene hybrid film supported by a polyimide substrate. The reduced graphene film alone showed a negligible sensor response, exhibiting abnormal N–P transitions during the initial NO2 injection. A hybrid film, formed by the growth of a vertically aligned CNT array (with CNTs 20 μm in length) on the reduced graphene film surface, exhibited remarkably enhanced sensitivities with weak N–P transitions. The increase in sensitivity was mainly attributed to the high sensitivity of the CNT arrays. The outstanding flexibility of the reduced graphene films ensured stable sensing performances in devices submitted to extreme bending stress.

## Semantic self-audit

Reduced graphene wording is preserved without automatically equating it to chemically defined rGO.
Negligible response is low magnitude, not categorical non-detection. Initial N–P transitions and bending stability have separate conditions.

## Mentions

| Key | Sentence | Span | Surface | Kind / role | Canonical |
| --- | --- | --- | --- | --- | --- |
| sensor | S1 | [13,53) | flexible room temperature NO2 gas sensor | DEVICE / technical_device | flexible CNT/reduced graphene NO2 sensor |
| flex | S1 | [13,21) | flexible | PROPERTY / technical_property | flexibility |
| rt | S1 | [22,38) | room temperature | OPERATING_CONDITION / technical_operating_condition | room temperature |
| no2 | S1 | [39,42) | NO2 | ANALYTE / technical_analyte | nitrogen dioxide |
| film | S1 | [68,129) | vertical carbon nanotubes (CNTs)/reduced graphene hybrid film | MATERIAL / technical_material | CNT/reduced graphene hybrid film |
| cnt | S1 | [77,93) | carbon nanotubes | MATERIAL / technical_material | carbon nanotubes |
| cnt_alias | S1 | [95,99) | CNTs | MATERIAL / technical_material | carbon nanotubes |
| substrate | S1 | [145,164) | polyimide substrate | DEVICE / technical_device | polyimide substrate |
| polyimide | S1 | [145,154) | polyimide | MATERIAL / technical_material | polyimide |
| reduced | S2 | [170,191) | reduced graphene film | MATERIAL / technical_material | reduced graphene film |
| response | S2 | [207,233) | negligible sensor response | PERFORMANCE / technical_performance | negligible NO2 response |
| transition | S2 | [246,270) | abnormal N–P transitions | MECHANISM / technical_mechanism | abnormal N–P transition |
| injection | S2 | [282,303) | initial NO2 injection | PROCESS / technical_process | initial NO2 injection |
| no22 | S2 | [290,293) | NO2 | ANALYTE / technical_analyte | nitrogen dioxide |
| hybrid3 | S3 | [307,318) | hybrid film | MATERIAL / technical_material | CNT/reduced graphene hybrid film |
| growth | S3 | [334,374) | growth of a vertically aligned CNT array | PROCESS / technical_process | vertical CNT array growth |
| array | S3 | [346,374) | vertically aligned CNT array | MATERIAL / technical_material | vertical CNT array |
| cnt3 | S3 | [381,385) | CNTs | MATERIAL / technical_material | carbon nanotubes |
| length | S3 | [386,401) | 20 μm in length | PROPERTY / technical_property | CNT length |
| reduced3 | S3 | [410,431) | reduced graphene film | MATERIAL / technical_material | reduced graphene film |
| sensitivity | S3 | [451,484) | remarkably enhanced sensitivities | PERFORMANCE / technical_performance | NO2 sensitivity |
| weak | S3 | [490,510) | weak N–P transitions | MECHANISM / technical_mechanism | weak N–P transition |
| increase | S4 | [516,539) | increase in sensitivity | PERFORMANCE / technical_performance | hybrid sensitivity increase |
| array4 | S4 | [593,603) | CNT arrays | MATERIAL / technical_material | vertical CNT array |
| high | S4 | [569,585) | high sensitivity | PERFORMANCE / technical_performance | CNT array sensitivity |
| flex5 | S5 | [609,632) | outstanding flexibility | PROPERTY / technical_property | flexibility |
| reduced5 | S5 | [640,662) | reduced graphene films | MATERIAL / technical_material | reduced graphene film |
| stable | S5 | [671,698) | stable sensing performances | PERFORMANCE / technical_performance | stable sensing performance |
| devices | S5 | [702,709) | devices | DEVICE / technical_device | flexible CNT/reduced graphene NO2 sensor |
| stress | S5 | [723,745) | extreme bending stress | OPERATING_CONDITION / technical_operating_condition | extreme bending stress |

## Assertions

| Head | Relation | Tail | Polarity | Modality / scope | Qualifiers | Evidence span IDs |
| --- | --- | --- | --- | --- | --- | --- |
| sensor | HAS_PROPERTY | flex | POSITIVE | ASSERTED / STUDY_RESULT |  | 36453abc-a6e3-5bd1-a262-93f2b257996c |
| sensor | USES_MATERIAL | film | POSITIVE | ASSERTED / STUDY_RESULT |  | 36453abc-a6e3-5bd1-a262-93f2b257996c |
| sensor | HAS_COMPONENT | substrate | POSITIVE | ASSERTED / STUDY_RESULT |  | 36453abc-a6e3-5bd1-a262-93f2b257996c |
| substrate | USES_MATERIAL | polyimide | POSITIVE | ASSERTED / STUDY_RESULT |  | 36453abc-a6e3-5bd1-a262-93f2b257996c |
| film | HAS_COMPONENT | cnt | POSITIVE | ASSERTED / STUDY_RESULT |  | 36453abc-a6e3-5bd1-a262-93f2b257996c |
| sensor | DETECTS | no2 | POSITIVE | ASSERTED / STUDY_RESULT | temperature: room temperature → room temperature | 36453abc-a6e3-5bd1-a262-93f2b257996c |
| reduced | HAS_PERFORMANCE | response | POSITIVE | ASSERTED / STUDY_RESULT | material_configuration: alone → alone; exposure_stage: initial NO2 injection → initial NO2 injection | 9ddef529-e01f-549b-ba5c-3f2ff258aea2 |
| hybrid3 | FABRICATED_BY | growth | POSITIVE | ASSERTED / STUDY_RESULT |  | 77b88d04-cf41-5dae-a576-179267b25ff4 |
| hybrid3 | HAS_COMPONENT | array | POSITIVE | ASSERTED / STUDY_RESULT |  | 77b88d04-cf41-5dae-a576-179267b25ff4 |
| hybrid3 | HAS_COMPONENT | reduced3 | POSITIVE | ASSERTED / STUDY_RESULT |  | 77b88d04-cf41-5dae-a576-179267b25ff4 |
| array | HAS_COMPONENT | cnt3 | POSITIVE | ASSERTED / STUDY_RESULT |  | 77b88d04-cf41-5dae-a576-179267b25ff4 |
| cnt3 | HAS_PROPERTY | length | POSITIVE | ASSERTED / STUDY_RESULT | length: 20 μm → 20 | 77b88d04-cf41-5dae-a576-179267b25ff4 |
| hybrid3 | HAS_PERFORMANCE | sensitivity | POSITIVE | COMPARED / STUDY_RESULT |  | 77b88d04-cf41-5dae-a576-179267b25ff4 |
| array4 | HAS_PERFORMANCE | high | POSITIVE | ASSERTED / STUDY_RESULT |  | 4405a8b8-664d-555f-98b0-839f944675d3 |
| reduced5 | HAS_PROPERTY | flex5 | POSITIVE | ASSERTED / STUDY_RESULT |  | a797bf0a-6a35-5d5c-b67f-e5b08cd31f9f |
| devices | HAS_PERFORMANCE | stable | POSITIVE | ASSERTED / STUDY_RESULT | mechanical_condition: extreme bending stress → extreme bending stress | a797bf0a-6a35-5d5c-b67f-e5b08cd31f9f |

## Identity decisions

| Left | Label | Right | Reason |
| --- | --- | --- | --- |
| sensor | SAME | devices | Curated source-local repetition/explicit alias; conditions and physical instances remain separate. |
| flex | SAME | flex5 | Curated source-local repetition/explicit alias; conditions and physical instances remain separate. |
| no2 | SAME | no22 | Curated source-local repetition/explicit alias; conditions and physical instances remain separate. |
| film | SAME | hybrid3 | Curated source-local repetition/explicit alias; conditions and physical instances remain separate. |
| cnt | SAME | cnt_alias | Curated source-local repetition/explicit alias; conditions and physical instances remain separate. |
| cnt | SAME | cnt3 | Curated source-local repetition/explicit alias; conditions and physical instances remain separate. |
| reduced | SAME | reduced3 | Curated source-local repetition/explicit alias; conditions and physical instances remain separate. |
| reduced | SAME | reduced5 | Curated source-local repetition/explicit alias; conditions and physical instances remain separate. |
| array | SAME | array4 | Curated source-local repetition/explicit alias; conditions and physical instances remain separate. |

## Unresolved

# Вопросы документа

Все открытые вопросы UNRESOLVED. Они не блокировали автоматический проход. Q1/Q2/Q3 решены пользователем и находятся в adjudication_decisions.jsonl.

## D050-Q4 — D050

**Статья:** Flexible room-temperature NO2 gas sensors based on carbon nanotubes/reduced graphene hybrid films.

Document `87775318-a9f1-457c-891c-6d910ac56175`; revision `f3937e44-f446-490b-8c4e-7b95768fca8a`; split `CALIBRATION`.

**Точный оригинал:**

> The reduced graphene film alone showed a negligible sensor response, exhibiting abnormal N–P transitions during the initial NO2 injection.

**Перевод и смысл:** В тексте механизм относится к материалу, тогда как принятый HAS_MECHANISM допускает только DEVICE. Подмена материала устройством исказила бы тип.

**Что неоднозначно/непокрыто:** Material N–P transition and initial-injection scope cannot be represented by DEVICE-only HAS_MECHANISM.

A. Представить HAS_MECHANISM после отдельного согласования схемы.

B. Сохранить существующую схему и учитывать как непокрытое отношение.

C. Оставить UNRESOLVED до содержательной проверки.

**Предварительное предложение:** A для DEV при подтверждении семантики; B для CALIBRATION/HOLDOUT без изменения схемы.

| Head | Proposed relation | Tail | Modality / polarity |
| --- | --- | --- | --- |
| reduced graphene film | HAS_MECHANISM | abnormal N–P transitions | ASSERTED / POSITIVE |

## D050-Q5 — D050

**Статья:** Flexible room-temperature NO2 gas sensors based on carbon nanotubes/reduced graphene hybrid films.

Document `87775318-a9f1-457c-891c-6d910ac56175`; revision `f3937e44-f446-490b-8c4e-7b95768fca8a`; split `CALIBRATION`.

**Точный оригинал:**

> A hybrid film, formed by the growth of a vertically aligned CNT array (with CNTs 20 μm in length) on the reduced graphene film surface, exhibited remarkably enhanced sensitivities with weak N–P transitions.

**Перевод и смысл:** В тексте механизм относится к материалу, тогда как принятый HAS_MECHANISM допускает только DEVICE. Подмена материала устройством исказила бы тип.

**Что неоднозначно/непокрыто:** Weak N–P transitions observed in hybrid material; frozen HAS_MECHANISM domain excludes MATERIAL.

A. Представить HAS_MECHANISM после отдельного согласования схемы.

B. Сохранить существующую схему и учитывать как непокрытое отношение.

C. Оставить UNRESOLVED до содержательной проверки.

**Предварительное предложение:** A для DEV при подтверждении семантики; B для CALIBRATION/HOLDOUT без изменения схемы.

| Head | Proposed relation | Tail | Modality / polarity |
| --- | --- | --- | --- |
| hybrid film | HAS_MECHANISM | weak N–P transitions | ASSERTED / POSITIVE |

## D050-Q6 — D050

**Статья:** Flexible room-temperature NO2 gas sensors based on carbon nanotubes/reduced graphene hybrid films.

Document `87775318-a9f1-457c-891c-6d910ac56175`; revision `f3937e44-f446-490b-8c4e-7b95768fca8a`; split `CALIBRATION`.

**Точный оригинал:**

> The increase in sensitivity was mainly attributed to the high sensitivity of the CNT arrays.

**Перевод и смысл:** Авторы связывают названную структуру, свойство или процесс с объяснением наблюдаемой характеристики. Текущая схема не содержит подходящего направленного отношения с такими endpoints.

**Что неоднозначно/непокрыто:** Attribution to CNT-array sensitivity is a PERFORMANCE → PERFORMANCE explanatory link, absent from frozen schema.

A. Представить EXPLAINS после отдельного согласования схемы.

B. Сохранить существующую схему и учитывать как непокрытое отношение.

C. Оставить UNRESOLVED до содержательной проверки.

**Предварительное предложение:** A для DEV при подтверждении семантики; B для CALIBRATION/HOLDOUT без изменения схемы.

| Head | Proposed relation | Tail | Modality / polarity |
| --- | --- | --- | --- |
| high sensitivity | EXPLAINS | increase in sensitivity | ASSERTED / POSITIVE |

## D050-Q7 — D050

**Статья:** Flexible room-temperature NO2 gas sensors based on carbon nanotubes/reduced graphene hybrid films.

Document `87775318-a9f1-457c-891c-6d910ac56175`; revision `f3937e44-f446-490b-8c4e-7b95768fca8a`; split `CALIBRATION`.

**Точный оригинал:**

> The outstanding flexibility of the reduced graphene films ensured stable sensing performances in devices submitted to extreme bending stress.

**Перевод и смысл:** Авторы связывают названную структуру, свойство или процесс с объяснением наблюдаемой характеристики. Текущая схема не содержит подходящего направленного отношения с такими endpoints.

**Что неоднозначно/непокрыто:** Flexibility ensures stable performance under bending; property-to-performance explanation is uncovered.

A. Представить EXPLAINS после отдельного согласования схемы.

B. Сохранить существующую схему и учитывать как непокрытое отношение.

C. Оставить UNRESOLVED до содержательной проверки.

**Предварительное предложение:** A для DEV при подтверждении семантики; B для CALIBRATION/HOLDOUT без изменения схемы.

| Head | Proposed relation | Tail | Modality / polarity |
| --- | --- | --- | --- |
| outstanding flexibility | EXPLAINS | stable sensing performances | ASSERTED / POSITIVE |
