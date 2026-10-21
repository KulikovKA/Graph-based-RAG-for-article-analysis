# D024 — Porous Graphene as the Ultimate Membrane for Gas Separation

**AI draft — HUMAN_REVIEW=NOT_REVIEWED; не human gold.**

Document `3a5a587d-5ddf-49b9-aa34-bd081fb0d04b`, revision `95f3f5a0-077c-4f5d-859f-37fc344f12f0`, split `DEV`, rubric `pilot24-rubric-0.3-AUTO-FROZEN`.

Chunks 2; sentences 7; mentions 39; assertions 15; unique canonical triples 14; questions 4; validation PASS.

Полный AI-проход завершён. exhaustive_entities=True; exhaustive_relations=False; неразрешённые кандидаты не являются negative gold.

## Исходные frozen EvidenceChunks

### `8c66a2f4-bc1a-4135-b4ed-059f62c24390`

SHA-256 `c8eb765f52f0ff76bff16cd80f39ce601f551a617e79388c49bedca77cac4058`, section `abstract`; [0, 1121).

We investigate the permeability and selectivity of graphene sheets with designed subnanometer pores using first principles density functional theory calculations. We find high selectivity on the order of 10(8) for H(2)/CH(4) with a high H(2) permeance for a nitrogen-functionalized pore. We find extremely high selectivity on the order of 10(23) for H(2)/CH(4) for an all-hydrogen passivated pore whose small width (at 2.5 A) presents a formidable barrier (1.6 eV) for CH(4) but easily surmountable for H(2) (0.22 eV). These results suggest that these pores are far superior to traditional polymer and silica membranes, where bulk solubility and diffusivity dominate the transport of gas molecules through the material. Recent experimental investigations, using either electron beams or bottom-up synthesis to create pores in graphene, suggest that it may be possible to employ such techniques to engineer variable-sized, graphene nanopores to tune selectivity and molecular diffusivity. Hence, we propose using porous graphene sheets as one-atom-thin, highly efficient, and highly selective membranes for gas separation.

### `6a14ebc5-5021-4e98-9eda-0b99d7267b5c`

SHA-256 `fe0a7132f2db425be78db46f877f70719cc94fd42d2865431beaf449cb9580e9`, section `abstract`; [1122, 1274).

Such a pore could have widespread impact on numerous energy and technological applications; including carbon sequestration, fuel cells, and gas sensors.

## Semantic self-audit

Theoretical 10(8)/10(23) selectivity values remain literal; no invented experimental separation.
Barrier values preserve H2/CH4 attachment. A remains source unit; nitrogen and H passivation distinct.
Gas sensor/fuel-cell use is hypothetical outlook, not measured device performance.

## Mentions

| Key | Sentence | Span | Surface | Kind / role | Canonical |
| --- | --- | --- | --- | --- | --- |
| permeability | S1 | [19,31) | permeability | PROPERTY / technical_property | permeability |
| selectivity | S1 | [36,47) | selectivity | PERFORMANCE / technical_performance | gas separation selectivity |
| sheets | S1 | [51,66) | graphene sheets | MATERIAL / technical_material | porous graphene sheet |
| pores | S1 | [72,99) | designed subnanometer pores | MORPHOLOGY / technical_morphology | subnanometer pore |
| dft | S1 | [106,161) | first principles density functional theory calculations | TECHNOLOGY / technical_technology | first-principles DFT |
| selectivity2 | S2 | [171,187) | high selectivity | PERFORMANCE / technical_performance | H2/CH4 selectivity |
| h2 | S2 | [214,218) | H(2) | ANALYTE / permeating_gas | hydrogen |
| ch4 | S2 | [219,224) | CH(4) | ANALYTE / technical_analyte | methane |
| permeance | S2 | [232,251) | high H(2) permeance | PERFORMANCE / technical_performance | H2 permeance |
| nitrogen | S2 | [258,286) | nitrogen-functionalized pore | MORPHOLOGY / technical_morphology | nitrogen-functionalized pore |
| selectivity3 | S3 | [296,322) | extremely high selectivity | PERFORMANCE / technical_performance | H2/CH4 selectivity |
| h2_3 | S3 | [350,354) | H(2) | ANALYTE / permeating_gas | hydrogen |
| ch4_3 | S3 | [355,360) | CH(4) | ANALYTE / restricted_gas | methane |
| hydrogenpore | S3 | [368,396) | all-hydrogen passivated pore | MORPHOLOGY / technical_morphology | all-hydrogen-passivated pore |
| width | S3 | [403,414) | small width | PROPERTY / technical_property | pore width |
| barrier | S3 | [437,455) | formidable barrier | PROPERTY / technical_property | CH4 permeation barrier |
| pores4 | S4 | [552,557) | pores | MORPHOLOGY / technical_morphology | graphene pore class |
| polymer | S4 | [590,597) | polymer | MATERIAL / technical_material | polymer membrane material |
| silica | S4 | [602,618) | silica membranes | DEVICE / technical_device | silica membrane |
| solubility | S4 | [626,641) | bulk solubility | PROPERTY / technical_property | bulk solubility |
| diffusivity | S4 | [646,657) | diffusivity | PROPERTY / technical_property | diffusivity |
| transport | S4 | [671,697) | transport of gas molecules | PROCESS / technical_process | gas transport |
| beams | S5 | [769,783) | electron beams | TECHNOLOGY / technical_technology | electron-beam pore fabrication |
| bottomup | S5 | [787,806) | bottom-up synthesis | PROCESS / technical_process | bottom-up synthesis |
| create | S5 | [810,834) | create pores in graphene | PROCESS / technical_process | graphene pore creation |
| graphene5 | S5 | [826,834) | graphene | MATERIAL / material | graphene |
| nanopores | S5 | [906,940) | variable-sized, graphene nanopores | MORPHOLOGY / technical_morphology | variable-size graphene nanopores |
| selectivity5 | S5 | [949,960) | selectivity | PERFORMANCE / technical_performance | gas separation selectivity |
| diffusivity5 | S5 | [965,986) | molecular diffusivity | PROPERTY / technical_property | molecular diffusivity |
| sheets6 | S6 | [1012,1034) | porous graphene sheets | MATERIAL / technical_material | porous graphene sheet |
| membrane | S6 | [1038,1101) | one-atom-thin, highly efficient, and highly selective membranes | DEVICE / technical_device | porous graphene gas separation membrane |
| thin | S6 | [1038,1051) | one-atom-thin | MORPHOLOGY / technical_morphology | one-atom-thin morphology |
| efficient | S6 | [1053,1069) | highly efficient | PERFORMANCE / technical_performance | high efficiency |
| selective | S6 | [1075,1091) | highly selective | PERFORMANCE / technical_performance | high selectivity |
| separation | S6 | [1106,1120) | gas separation | APPLICATION / technical_application | gas separation |
| pore7 | S7 | [7,11) | pore | MORPHOLOGY / technical_morphology | graphene pore class |
| sequestration | S7 | [102,122) | carbon sequestration | APPLICATION / technical_application | carbon sequestration |
| fuel | S7 | [124,134) | fuel cells | DEVICE / technical_device | fuel cell |
| sensors7 | S7 | [140,151) | gas sensors | DEVICE / technical_device | gas sensor |

## Assertions

| Head | Relation | Tail | Polarity | Modality / scope | Qualifiers | Evidence span IDs |
| --- | --- | --- | --- | --- | --- | --- |
| sheets | HAS_PROPERTY | permeability | POSITIVE | ASSERTED / COMPUTATIONAL_RESULT |  | 6f3ac072-9708-55b6-bc14-11f19dcb600d |
| sheets | HAS_PERFORMANCE | selectivity | POSITIVE | ASSERTED / COMPUTATIONAL_RESULT |  | 6f3ac072-9708-55b6-bc14-11f19dcb600d |
| sheets | HAS_MORPHOLOGY | pores | POSITIVE | ASSERTED / COMPUTATIONAL_RESULT |  | 6f3ac072-9708-55b6-bc14-11f19dcb600d |
| sheets | HAS_PERFORMANCE | selectivity2 | POSITIVE | ASSERTED / COMPUTATIONAL_RESULT | selectivity_order: 10(8) → 10(8); gas_pair: H(2)/CH(4) → H(2)/CH(4); pore_configuration: nitrogen-functionalized pore → nitrogen-functionalized pore | 6f3ac072-9708-55b6-bc14-11f19dcb600d; e60d2ab5-b94a-50c6-bae1-ee10d012f145 |
| sheets | HAS_PERFORMANCE | permeance | POSITIVE | ASSERTED / COMPUTATIONAL_RESULT | pore_configuration: nitrogen-functionalized pore → nitrogen-functionalized pore | 6f3ac072-9708-55b6-bc14-11f19dcb600d; e60d2ab5-b94a-50c6-bae1-ee10d012f145 |
| sheets | HAS_PERFORMANCE | selectivity3 | POSITIVE | ASSERTED / COMPUTATIONAL_RESULT | selectivity_order: 10(23) → 10(23); gas_pair: H(2)/CH(4) → H(2)/CH(4); pore_configuration: all-hydrogen passivated pore → all-hydrogen passivated pore | 6f3ac072-9708-55b6-bc14-11f19dcb600d; 63b5b21a-0358-52b7-b055-aa4a3100a2f4 |
| sheets | HAS_PROPERTY | barrier | POSITIVE | ASSERTED / COMPUTATIONAL_RESULT | CH4_barrier: 1.6 eV → 1.6; H2_barrier: 0.22 eV → 0.22; pore_configuration: all-hydrogen passivated pore → all-hydrogen passivated pore | 6f3ac072-9708-55b6-bc14-11f19dcb600d; 63b5b21a-0358-52b7-b055-aa4a3100a2f4 |
| create | ACTS_ON | graphene5 | POSITIVE | PROPOSED / COMPUTATIONAL_RESULT | fabrication_techniques: electron beams or bottom-up synthesis → electron beams or bottom-up synthesis | 19d206b2-4084-58af-8674-9ef55193395b |
| create | OPTIMIZES | graphene5 | POSITIVE | HYPOTHETICAL / COMPUTATIONAL_RESULT |  | 19d206b2-4084-58af-8674-9ef55193395b |
| sheets6 | FUNCTIONS_AS | membrane | POSITIVE | PROPOSED / COMPUTATIONAL_RESULT |  | 540929a9-d14a-5016-9e32-3f45ce56b68d |
| membrane | HAS_MORPHOLOGY | thin | POSITIVE | PROPOSED / COMPUTATIONAL_RESULT |  | 540929a9-d14a-5016-9e32-3f45ce56b68d |
| membrane | HAS_PERFORMANCE | efficient | POSITIVE | PROPOSED / COMPUTATIONAL_RESULT |  | 540929a9-d14a-5016-9e32-3f45ce56b68d |
| membrane | HAS_PERFORMANCE | selective | POSITIVE | PROPOSED / COMPUTATIONAL_RESULT |  | 540929a9-d14a-5016-9e32-3f45ce56b68d |
| membrane | USED_FOR | separation | POSITIVE | PROPOSED / COMPUTATIONAL_RESULT |  | 540929a9-d14a-5016-9e32-3f45ce56b68d |
| membrane | USED_FOR | sequestration | POSITIVE | HYPOTHETICAL / OUTLOOK |  | 540929a9-d14a-5016-9e32-3f45ce56b68d; 25d69469-bb2a-5909-916c-f1d3421accf3 |

## Identity decisions

| Left | Label | Right | Reason |
| --- | --- | --- | --- |
| nitrogen | DIFFERENT | hydrogenpore | Two pore functionalization configurations; selectivity orders and barriers cannot be merged. |
| selectivity | SAME | selectivity5 | Curated source-local repetition/explicit alias; conditions and physical instances remain separate. |
| sheets | SAME | sheets6 | Curated source-local repetition/explicit alias; conditions and physical instances remain separate. |
| selectivity2 | SAME | selectivity3 | Curated source-local repetition/explicit alias; conditions and physical instances remain separate. |
| h2 | SAME | h2_3 | Curated source-local repetition/explicit alias; conditions and physical instances remain separate. |
| ch4 | SAME | ch4_3 | Curated source-local repetition/explicit alias; conditions and physical instances remain separate. |
| pores4 | SAME | pore7 | Curated source-local repetition/explicit alias; conditions and physical instances remain separate. |

## Unresolved

# Вопросы документа

Все открытые вопросы UNRESOLVED. Они не блокировали автоматический проход. Q1/Q2/Q3 решены пользователем и находятся в adjudication_decisions.jsonl.

## D024-Q4 — D024

**Статья:** Porous Graphene as the Ultimate Membrane for Gas Separation.

Document `3a5a587d-5ddf-49b9-aa34-bd081fb0d04b`; revision `95f3f5a0-077c-4f5d-859f-37fc344f12f0`; split `DEV`.

**Точный оригинал:**

> We find extremely high selectivity on the order of 10(23) for H(2)/CH(4) for an all-hydrogen passivated pore whose small width (at 2.5 A) presents a formidable barrier (1.6 eV) for CH(4) but easily surmountable for H(2) (0.22 eV).

**Перевод и смысл:** Свойство явно относится к структуре MORPHOLOGY, но у HAS_PROPERTY такой тип носителя не разрешён.

**Что неоднозначно/непокрыто:** MORPHOLOGY → PROPERTY endpoint gap; keep source unit A without silent Angstrom normalization.

A. Представить HAS_PROPERTY после отдельного согласования схемы.

B. Сохранить существующую схему и учитывать как непокрытое отношение.

C. Оставить UNRESOLVED до содержательной проверки.

**Предварительное предложение:** A для DEV при подтверждении семантики; B для CALIBRATION/HOLDOUT без изменения схемы.

| Head | Proposed relation | Tail | Modality / polarity |
| --- | --- | --- | --- |
| all-hydrogen passivated pore | HAS_PROPERTY | small width | ASSERTED / POSITIVE |

## D024-Q5 — D024

**Статья:** Porous Graphene as the Ultimate Membrane for Gas Separation.

Document `3a5a587d-5ddf-49b9-aa34-bd081fb0d04b`; revision `95f3f5a0-077c-4f5d-859f-37fc344f12f0`; split `DEV`.

**Точный оригинал:**

> These results suggest that these pores are far superior to traditional polymer and silica membranes, where bulk solubility and diffusivity dominate the transport of gas molecules through the material.

**Перевод и смысл:** Названное свойство определяет преобладающий вклад в перенос молекул. Это иной смысл, чем принадлежность свойства или действие на материал.

**Что неоднозначно/непокрыто:** Transport dominated by bulk solubility/diffusivity; PROPERTY → PROCESS dominance is not FACILITATES.

A. Представить DOMINATES после отдельного согласования схемы.

B. Сохранить существующую схему и учитывать как непокрытое отношение.

C. Оставить UNRESOLVED до содержательной проверки.

**Предварительное предложение:** A для DEV при подтверждении семантики; B для CALIBRATION/HOLDOUT без изменения схемы.

| Head | Proposed relation | Tail | Modality / polarity |
| --- | --- | --- | --- |
| bulk solubility | DOMINATES | transport of gas molecules | ASSERTED / POSITIVE |
| diffusivity | DOMINATES | transport of gas molecules | ASSERTED / POSITIVE |

## D024-Q6 — D024

**Статья:** Porous Graphene as the Ultimate Membrane for Gas Separation.

Document `3a5a587d-5ddf-49b9-aa34-bd081fb0d04b`; revision `95f3f5a0-077c-4f5d-859f-37fc344f12f0`; split `DEV`.

**Точный оригинал:**

> Hence, we propose using porous graphene sheets as one-atom-thin, highly efficient, and highly selective membranes for gas separation.
> Such a pore could have widespread impact on numerous energy and technological applications; including carbon sequestration, fuel cells, and gas sensors.

**Перевод и смысл:** Указано перспективное применение материала в названном устройстве. Текущие tail kinds USED_FOR не включают DEVICE; физический состав устройства не утверждён.

**Что неоднозначно/непокрыто:** Prospective application to fuel cells; material-to-device use is outside allowed USED_FOR tails, and a physical component relation is not explicitly asserted.

A. Представить USED_FOR после отдельного согласования схемы.

B. Сохранить существующую схему и учитывать как непокрытое отношение.

C. Оставить UNRESOLVED до содержательной проверки.

**Предварительное предложение:** A для DEV при подтверждении семантики; B для CALIBRATION/HOLDOUT без изменения схемы.

| Head | Proposed relation | Tail | Modality / polarity |
| --- | --- | --- | --- |
| porous graphene sheets | USED_FOR | fuel cells | HYPOTHETICAL / POSITIVE |

## D024-Q7 — D024

**Статья:** Porous Graphene as the Ultimate Membrane for Gas Separation.

Document `3a5a587d-5ddf-49b9-aa34-bd081fb0d04b`; revision `95f3f5a0-077c-4f5d-859f-37fc344f12f0`; split `DEV`.

**Точный оригинал:**

> Hence, we propose using porous graphene sheets as one-atom-thin, highly efficient, and highly selective membranes for gas separation.
> Such a pore could have widespread impact on numerous energy and technological applications; including carbon sequestration, fuel cells, and gas sensors.

**Перевод и смысл:** Указано перспективное применение материала в названном устройстве. Текущие tail kinds USED_FOR не включают DEVICE; физический состав устройства не утверждён.

**Что неоднозначно/непокрыто:** Prospective application to gas sensors; no separately fabricated component is asserted.

A. Представить USED_FOR после отдельного согласования схемы.

B. Сохранить существующую схему и учитывать как непокрытое отношение.

C. Оставить UNRESOLVED до содержательной проверки.

**Предварительное предложение:** A для DEV при подтверждении семантики; B для CALIBRATION/HOLDOUT без изменения схемы.

| Head | Proposed relation | Tail | Modality / polarity |
| --- | --- | --- | --- |
| porous graphene sheets | USED_FOR | gas sensors | HYPOTHETICAL / POSITIVE |
