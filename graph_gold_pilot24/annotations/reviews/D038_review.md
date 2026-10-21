# D038 — 3D Architectured Graphene/Metal Oxide Hybrids for Gas Sensors: A Review

**AI draft — HUMAN_REVIEW=NOT_REVIEWED; не human gold.**

Document `6a675d0d-8256-4c8f-b2ae-7c95c1bcabf8`, revision `b6535766-c337-4abd-9925-8381f0acc7fa`, split `DEV`, rubric `pilot24-rubric-0.3-AUTO-FROZEN`.

Chunks 1; sentences 5; mentions 27; assertions 16; unique canonical triples 16; questions 1; validation PASS.

Полный AI-проход завершён. exhaustive_entities=True; exhaustive_relations=False; неразрешённые кандидаты не являются negative gold.

## Исходные frozen EvidenceChunks

### `fb767df1-8f61-4334-89e7-29c1cdcf5364`

SHA-256 `6d06ae3b6c61d47994638233f63c8c06319dd0eb8a5ec0b5203b72e47f6e2da4`, section `abstract`; [0, 997).

Graphene/metal oxide-based materials have been demonstrated as promising candidates for gas sensing applications due to the enhanced sensing performance and synergetic effects of the two components. Plenty of metal oxides such as SnO₂, ZnO, WO₃, etc. have been hybridized with graphene to improve the gas sensing properties. However, graphene/metal oxide nanohybrid- based gas sensors still have several limitations in practical application such as the insufficient sensitivity and response rate, and long recovery time in some cases. To achieve higher sensing performances of graphene/metal oxides nanocomposites, many recent efforts have been devoted to the controllable synthesis of 3D graphene/metal oxides architectures owing to their large surface area and well-organized structure for the enhanced gas adsorption/diffusion on sensing films. This review summarizes recent advances in the synthesis, assembly, and applications of 3D architectured graphene/metal oxide hybrids for gas sensing.

## Semantic self-audit

Limitations have in some cases scope; no universal failure claim or invented numeric recovery time.
Review-level application and synthesis claims kept separate from experimental results.

## Mentions

| Key | Sentence | Span | Surface | Kind / role | Canonical |
| --- | --- | --- | --- | --- | --- |
| hybrid | S1 | [0,36) | Graphene/metal oxide-based materials | MATERIAL / technical_material | graphene/metal oxide hybrid |
| application | S1 | [88,112) | gas sensing applications | APPLICATION / technical_application | gas sensing |
| performance | S1 | [124,152) | enhanced sensing performance | PERFORMANCE / technical_performance | sensing performance |
| synergy | S1 | [157,175) | synergetic effects | MECHANISM / technical_mechanism | graphene–oxide synergy |
| oxides | S2 | [209,221) | metal oxides | MATERIAL / technical_material | metal oxide class |
| sno2 | S2 | [230,234) | SnO₂ | MATERIAL / technical_material | tin dioxide |
| zno | S2 | [236,239) | ZnO | MATERIAL / technical_material | zinc oxide |
| wo3 | S2 | [241,244) | WO₃ | MATERIAL / technical_material | tungsten trioxide |
| graphene | S2 | [277,285) | graphene | MATERIAL / technical_material | graphene |
| hybridize | S2 | [261,285) | hybridized with graphene | PROCESS / technical_process | graphene–oxide hybridization |
| properties | S2 | [301,323) | gas sensing properties | PERFORMANCE / technical_performance | sensing performance |
| sensors | S3 | [334,384) | graphene/metal oxide nanohybrid- based gas sensors | DEVICE / technical_device | graphene/oxide nanohybrid gas sensor |
| sensitivity | S3 | [453,477) | insufficient sensitivity | PERFORMANCE / technical_performance | insufficient sensitivity |
| response | S3 | [482,495) | response rate | PERFORMANCE / technical_performance | insufficient response rate |
| recovery | S3 | [501,519) | long recovery time | PERFORMANCE / technical_performance | long recovery time |
| application3 | S3 | [419,440) | practical application | APPLICATION / technical_application | practical gas sensing |
| synthesis | S4 | [660,682) | controllable synthesis | PROCESS / technical_process | controllable 3D hybrid synthesis |
| architecture | S4 | [686,724) | 3D graphene/metal oxides architectures | MATERIAL / technical_material | 3D graphene/metal oxide hybrid |
| three | S4 | [686,688) | 3D | MORPHOLOGY / technical_morphology | three-dimensional morphology |
| area | S4 | [740,758) | large surface area | PROPERTY / technical_property | surface area |
| structure | S4 | [763,787) | well-organized structure | MORPHOLOGY / technical_morphology | well-organized structure |
| adsorb | S4 | [805,829) | gas adsorption/diffusion | PROCESS / technical_process | gas adsorption/diffusion |
| films | S4 | [833,846) | sensing films | DEVICE / technical_device | sensing film |
| synth5 | S5 | [894,903) | synthesis | PROCESS / technical_process | 3D hybrid synthesis |
| assembly | S5 | [905,913) | assembly | PROCESS / technical_process | 3D hybrid assembly |
| hybrid5 | S5 | [935,980) | 3D architectured graphene/metal oxide hybrids | MATERIAL / technical_material | 3D graphene/metal oxide hybrid |
| application5 | S5 | [985,996) | gas sensing | APPLICATION / technical_application | gas sensing |

## Assertions

| Head | Relation | Tail | Polarity | Modality / scope | Qualifiers | Evidence span IDs |
| --- | --- | --- | --- | --- | --- | --- |
| hybrid | USED_FOR | application | POSITIVE | ASSERTED / REVIEW_BACKGROUND |  | 0b22767d-2d0c-5e45-8362-bff0eea5475e |
| hybrid | HAS_PERFORMANCE | performance | POSITIVE | ASSERTED / REVIEW_BACKGROUND |  | 0b22767d-2d0c-5e45-8362-bff0eea5475e |
| hybrid | HAS_COMPONENT | oxides | POSITIVE | ASSERTED / REVIEW_BACKGROUND |  | 0b22767d-2d0c-5e45-8362-bff0eea5475e; 2fd3e9b1-1bf7-5fcc-a2fb-d5d540a4d91b |
| hybrid | HAS_COMPONENT | graphene | POSITIVE | ASSERTED / REVIEW_BACKGROUND |  | 0b22767d-2d0c-5e45-8362-bff0eea5475e; 2fd3e9b1-1bf7-5fcc-a2fb-d5d540a4d91b |
| hybridize | IMPROVES | properties | POSITIVE | PROPOSED / REVIEW_BACKGROUND |  | 2fd3e9b1-1bf7-5fcc-a2fb-d5d540a4d91b |
| sensors | HAS_PERFORMANCE | sensitivity | POSITIVE | ASSERTED / REVIEW_LIMITATION | scope_limit: in some cases → in some cases | 978860a4-3524-5fff-94d6-3c78cc1e9bfe |
| sensors | HAS_PERFORMANCE | response | POSITIVE | ASSERTED / REVIEW_LIMITATION | scope_limit: in some cases → in some cases | 978860a4-3524-5fff-94d6-3c78cc1e9bfe |
| sensors | HAS_PERFORMANCE | recovery | POSITIVE | ASSERTED / REVIEW_LIMITATION | scope_limit: in some cases → in some cases | 978860a4-3524-5fff-94d6-3c78cc1e9bfe |
| architecture | FABRICATED_BY | synthesis | POSITIVE | ASSERTED / REVIEW_BACKGROUND |  | f173c223-c90e-52f4-a2cd-693d9a092a12 |
| architecture | HAS_MORPHOLOGY | three | POSITIVE | ASSERTED / REVIEW_BACKGROUND |  | f173c223-c90e-52f4-a2cd-693d9a092a12 |
| architecture | HAS_MORPHOLOGY | structure | POSITIVE | ASSERTED / REVIEW_BACKGROUND |  | f173c223-c90e-52f4-a2cd-693d9a092a12 |
| architecture | HAS_PROPERTY | area | POSITIVE | ASSERTED / REVIEW_BACKGROUND |  | f173c223-c90e-52f4-a2cd-693d9a092a12 |
| architecture | FACILITATES | adsorb | POSITIVE | ASSERTED / REVIEW_BACKGROUND | process_location: on sensing films → on sensing films | f173c223-c90e-52f4-a2cd-693d9a092a12 |
| hybrid5 | FABRICATED_BY | synth5 | POSITIVE | ASSERTED / REVIEW_SCOPE |  | c9a4ff24-bb76-5dc0-a7d6-d7c343109e51 |
| hybrid5 | FABRICATED_BY | assembly | POSITIVE | ASSERTED / REVIEW_SCOPE |  | c9a4ff24-bb76-5dc0-a7d6-d7c343109e51 |
| hybrid5 | USED_FOR | application5 | POSITIVE | ASSERTED / REVIEW_SCOPE |  | c9a4ff24-bb76-5dc0-a7d6-d7c343109e51 |

## Identity decisions

| Left | Label | Right | Reason |
| --- | --- | --- | --- |
| sno2 | NARROWER | oxides | Named metal oxide within an explicit class, not equivalent to the entire class. |
| zno | NARROWER | oxides | Named metal oxide within an explicit class, not equivalent to the entire class. |
| wo3 | NARROWER | oxides | Named metal oxide within an explicit class, not equivalent to the entire class. |
| application | SAME | application5 | Curated source-local repetition/explicit alias; conditions and physical instances remain separate. |
| performance | SAME | properties | Curated source-local repetition/explicit alias; conditions and physical instances remain separate. |
| architecture | SAME | hybrid5 | Curated source-local repetition/explicit alias; conditions and physical instances remain separate. |

## Unresolved

# Вопросы документа

Все открытые вопросы UNRESOLVED. Они не блокировали автоматический проход. Q1/Q2/Q3 решены пользователем и находятся в adjudication_decisions.jsonl.

## D038-Q4 — D038

**Статья:** 3D Architectured Graphene/Metal Oxide Hybrids for Gas Sensors: A Review.

Document `6a675d0d-8256-4c8f-b2ae-7c95c1bcabf8`; revision `b6535766-c337-4abd-9925-8381f0acc7fa`; split `DEV`.

**Точный оригинал:**

> Graphene/metal oxide-based materials have been demonstrated as promising candidates for gas sensing applications due to the enhanced sensing performance and synergetic effects of the two components.

**Перевод и смысл:** В тексте механизм относится к материалу, тогда как принятый HAS_MECHANISM допускает только DEVICE. Подмена материала устройством исказила бы тип.

**Что неоднозначно/непокрыто:** Материал является носителем заявленной synergy; HAS_MECHANISM domain сейчас DEVICE.

A. Представить HAS_MECHANISM после отдельного согласования схемы.

B. Сохранить существующую схему и учитывать как непокрытое отношение.

C. Оставить UNRESOLVED до содержательной проверки.

**Предварительное предложение:** A для DEV при подтверждении семантики; B для CALIBRATION/HOLDOUT без изменения схемы.

| Head | Proposed relation | Tail | Modality / polarity |
| --- | --- | --- | --- |
| Graphene/metal oxide-based materials | HAS_MECHANISM | synergetic effects | ASSERTED / POSITIVE |
