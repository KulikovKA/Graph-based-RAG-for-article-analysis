# D026 — Metallic Ti3C2T x MXene Gas Sensors with Ultrahigh Signal-to-Noise Ratio

**AI draft — HUMAN_REVIEW=NOT_REVIEWED; не human gold.**

Document `3df9cd7a-940f-400e-b03a-a72459a5558f`, revision `3ed28d1a-4b30-4ea4-bf03-3a69308fb8ba`, split `DEV`, rubric `pilot24-rubric-0.3-AUTO-FROZEN`.

Chunks 1; sentences 7; mentions 30; assertions 12; unique canonical triples 12; questions 2; validation PASS.

Полный AI-проход завершён. exhaustive_entities=True; exhaustive_relations=False; неразрешённые кандидаты не являются negative gold.

## Исходные frozen EvidenceChunks

### `5a1139f9-9bf1-4665-96e1-c15a6477ded6`

SHA-256 `bedd2a7ed1ad17c747634824457042b37b609d742e51ee38b9ffc4f8c0f23907`, section `abstract`; [0, 1087).

Abstract Achieving high sensitivity in solid-state gas sensors can allow the precise detection of chemical agents. In particular, detection of volatile organic compounds (VOCs) at the parts per billion (ppb) level is critical for the early diagnosis of diseases. To obtain high sensitivity, two requirements need to be simultaneously satisfied: (i) low electrical noise and (ii) strong signal, which existing sensor materials cannot meet. Here, we demonstrate that 2D metal carbide MXenes, which possess high metallic conductivity for low noise and a fully functionalized surface for a strong signal, greatly outperform the sensitivity of conventional semiconductor channel materials. Ti3C2Tx MXene gas sensors exhibited a very low limit of detection of 50–100 ppb for VOC gases at room temperature. Also, the extremely low noise led to a signal-to-noise ratio 2 orders of magnitude higher than that of other 2D materials, surpassing the best sensors known. Our results provide insight in utilizing highly functionalized metallic sensing channels for developing highly sensitive sensors.

## Semantic self-audit

Joint cannot-meet statement preserved as a single unresolved joint constraint; no false two-way negation.
VOC class not narrowed to a named organic molecule; 50–100 ppb and room temperature attached to LOD only.
SNR 2 orders comparison is to other 2D materials, not a numeric absolute SNR.

## Mentions

| Key | Sentence | Span | Surface | Kind / role | Canonical |
| --- | --- | --- | --- | --- | --- |
| sensitivity | S1 | [19,35) | high sensitivity | PERFORMANCE / technical_performance | high sensitivity |
| sensor | S1 | [39,62) | solid-state gas sensors | DEVICE / technical_device | solid-state gas sensor |
| agents | S1 | [98,113) | chemical agents | ANALYTE / technical_analyte | chemical agents unspecified |
| detection | S1 | [77,94) | precise detection | APPLICATION / technical_application | precise chemical-agent detection |
| vocs | S2 | [143,169) | volatile organic compounds | ANALYTE / technical_analyte | volatile organic compounds |
| vocs_alias | S2 | [171,175) | VOCs | ANALYTE / technical_analyte | volatile organic compounds |
| ppb | S2 | [184,213) | parts per billion (ppb) level | OPERATING_CONDITION / technical_operating_condition | ppb concentration regime |
| diagnosis | S2 | [234,261) | early diagnosis of diseases | APPLICATION / technical_application | early disease diagnosis |
| noise | S3 | [349,369) | low electrical noise | PROPERTY / technical_property | low electrical noise |
| signal | S3 | [379,392) | strong signal | PERFORMANCE / technical_performance | strong signal |
| materials | S3 | [400,425) | existing sensor materials | MATERIAL / technical_material | existing sensor materials unspecified |
| mxene | S4 | [465,488) | 2D metal carbide MXenes | MATERIAL / technical_material | 2D metal carbide MXene |
| two | S4 | [465,467) | 2D | MORPHOLOGY / technical_morphology | two-dimensional morphology |
| conductivity | S4 | [504,530) | high metallic conductivity | PROPERTY / technical_property | metallic conductivity |
| noise4 | S4 | [535,544) | low noise | PROPERTY / technical_property | low electrical noise |
| surface | S4 | [551,579) | fully functionalized surface | MORPHOLOGY / technical_morphology | fully functionalized surface |
| signal4 | S4 | [586,599) | strong signal | PERFORMANCE / technical_performance | strong signal |
| sensitivity4 | S4 | [624,635) | sensitivity | PERFORMANCE / technical_performance | sensitivity |
| semiconductor | S4 | [639,683) | conventional semiconductor channel materials | MATERIAL / technical_material | conventional semiconductor channel material |
| sensor5 | S5 | [685,710) | Ti3C2Tx MXene gas sensors | DEVICE / technical_device | Ti3C2Tx MXene gas sensor |
| ti | S5 | [685,698) | Ti3C2Tx MXene | MATERIAL / technical_material | Ti3C2Tx MXene |
| lod | S5 | [723,750) | very low limit of detection | PERFORMANCE / technical_performance | detection limit |
| vocs5 | S5 | [769,778) | VOC gases | ANALYTE / technical_analyte | volatile organic compounds |
| rt | S5 | [782,798) | room temperature | OPERATING_CONDITION / technical_operating_condition | room temperature |
| noise6 | S6 | [810,829) | extremely low noise | PROPERTY / technical_property | low electrical noise |
| snr | S6 | [839,860) | signal-to-noise ratio | PERFORMANCE / technical_performance | signal-to-noise ratio |
| other | S6 | [903,921) | other 2D materials | MATERIAL / technical_material | other 2D materials |
| best | S6 | [938,956) | best sensors known | DEVICE / technical_device | comparison best sensors unspecified |
| channel | S7 | [999,1046) | highly functionalized metallic sensing channels | DEVICE / technical_device | functionalized metallic sensing channel |
| sensor7 | S7 | [1062,1086) | highly sensitive sensors | DEVICE / technical_device | prospective highly sensitive sensor |

## Assertions

| Head | Relation | Tail | Polarity | Modality / scope | Qualifiers | Evidence span IDs |
| --- | --- | --- | --- | --- | --- | --- |
| sensor | USED_FOR | detection | POSITIVE | HYPOTHETICAL / BACKGROUND |  | 37b1b2d9-e3ce-5c9c-9b52-f373de5d0533 |
| mxene | HAS_MORPHOLOGY | two | POSITIVE | ASSERTED / STUDY_RESULT |  | 988f6a46-2fbc-5f67-ba3a-054d01d8088a |
| mxene | HAS_MORPHOLOGY | surface | POSITIVE | ASSERTED / STUDY_RESULT |  | 988f6a46-2fbc-5f67-ba3a-054d01d8088a |
| mxene | HAS_PROPERTY | conductivity | POSITIVE | ASSERTED / STUDY_RESULT |  | 988f6a46-2fbc-5f67-ba3a-054d01d8088a |
| mxene | HAS_PROPERTY | noise4 | POSITIVE | ASSERTED / STUDY_RESULT |  | 988f6a46-2fbc-5f67-ba3a-054d01d8088a |
| mxene | HAS_PERFORMANCE | signal4 | POSITIVE | ASSERTED / STUDY_RESULT |  | 988f6a46-2fbc-5f67-ba3a-054d01d8088a |
| mxene | HAS_PERFORMANCE | sensitivity4 | POSITIVE | COMPARED / STUDY_RESULT | comparison_direction: greatly outperform → greatly outperform; comparison_material: conventional semiconductor channel materials → conventional semiconductor channel materials | 988f6a46-2fbc-5f67-ba3a-054d01d8088a |
| sensor5 | USES_MATERIAL | ti | POSITIVE | ASSERTED / STUDY_RESULT |  | b206d1d0-2b3a-5fab-886e-e0599a5bd94e |
| sensor5 | DETECTS | vocs5 | POSITIVE | ASSERTED / STUDY_RESULT |  | b206d1d0-2b3a-5fab-886e-e0599a5bd94e |
| sensor5 | HAS_PERFORMANCE | lod | POSITIVE | ASSERTED / STUDY_RESULT | detection_limit_range: 50–100 ppb → [50, 100]; temperature: room temperature → room temperature | b206d1d0-2b3a-5fab-886e-e0599a5bd94e |
| sensor5 | HAS_PERFORMANCE | snr | POSITIVE | COMPARED / STUDY_RESULT | SNR_ratio: 2 orders of magnitude higher → 2 orders of magnitude higher; comparison_material: other 2D materials → other 2D materials | b206d1d0-2b3a-5fab-886e-e0599a5bd94e; 1e963b81-9c81-52fa-b2f5-e8b4976942b1 |
| sensor7 | HAS_COMPONENT | channel | POSITIVE | HYPOTHETICAL / OUTLOOK |  | eeaf3c91-756e-5d10-a84e-783af329d7cc |

## Identity decisions

| Left | Label | Right | Reason |
| --- | --- | --- | --- |
| vocs | SAME | vocs_alias | Curated source-local repetition/explicit alias; conditions and physical instances remain separate. |
| vocs | SAME | vocs5 | Curated source-local repetition/explicit alias; conditions and physical instances remain separate. |
| noise | SAME | noise4 | Curated source-local repetition/explicit alias; conditions and physical instances remain separate. |
| noise | SAME | noise6 | Curated source-local repetition/explicit alias; conditions and physical instances remain separate. |
| signal | SAME | signal4 | Curated source-local repetition/explicit alias; conditions and physical instances remain separate. |

## Unresolved

# Вопросы документа

Все открытые вопросы UNRESOLVED. Они не блокировали автоматический проход. Q1/Q2/Q3 решены пользователем и находятся в adjudication_decisions.jsonl.

## D026-Q4 — D026

**Статья:** Metallic Ti3C2T x MXene Gas Sensors with Ultrahigh Signal-to-Noise Ratio.

Document `3df9cd7a-940f-400e-b03a-a72459a5558f`; revision `3ed28d1a-4b30-4ea4-bf03-3a69308fb8ba`; split `DEV`.

**Точный оригинал:**

> To obtain high sensitivity, two requirements need to be simultaneously satisfied: (i) low electrical noise and (ii) strong signal, which existing sensor materials cannot meet.

**Перевод и смысл:** Отрицание относится к совместному выполнению двух требований: низкий шум И сильный сигнал. Нельзя превращать его в два независимых отрицания.

**Что неоднозначно/непокрыто:** Cannot simultaneously meet low noise and strong signal: group negation must not become two independent failures.

A. Представить MEETS_REQUIREMENT после отдельного согласования схемы.

B. Сохранить существующую схему и учитывать как непокрытое отношение.

C. Оставить UNRESOLVED до содержательной проверки.

**Предварительное предложение:** A для DEV при подтверждении семантики; B для CALIBRATION/HOLDOUT без изменения схемы.

| Head | Proposed relation | Tail | Modality / polarity |
| --- | --- | --- | --- |
| existing sensor materials | MEETS_REQUIREMENT | low electrical noise | ASSERTED / NEGATIVE |

## D026-Q5 — D026

**Статья:** Metallic Ti3C2T x MXene Gas Sensors with Ultrahigh Signal-to-Noise Ratio.

Document `3df9cd7a-940f-400e-b03a-a72459a5558f`; revision `3ed28d1a-4b30-4ea4-bf03-3a69308fb8ba`; split `DEV`.

**Точный оригинал:**

> Also, the extremely low noise led to a signal-to-noise ratio 2 orders of magnitude higher than that of other 2D materials, surpassing the best sensors known.

**Перевод и смысл:** Авторы связывают названную структуру, свойство или процесс с объяснением наблюдаемой характеристики. Текущая схема не содержит подходящего направленного отношения с такими endpoints.

**Что неоднозначно/непокрыто:** Low noise led to SNR advantage; PROPERTY → PERFORMANCE causal effect cannot be replaced by HAS_PROPERTY.

A. Представить EXPLAINS после отдельного согласования схемы.

B. Сохранить существующую схему и учитывать как непокрытое отношение.

C. Оставить UNRESOLVED до содержательной проверки.

**Предварительное предложение:** A для DEV при подтверждении семантики; B для CALIBRATION/HOLDOUT без изменения схемы.

| Head | Proposed relation | Tail | Modality / polarity |
| --- | --- | --- | --- |
| extremely low noise | EXPLAINS | signal-to-noise ratio | ASSERTED / POSITIVE |
