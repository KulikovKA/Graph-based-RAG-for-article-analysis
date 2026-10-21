# D001 — Reduced Graphene Oxide/Mesoporous ZnO NSs Hybrid Fibers for Flexible, Stretchable, Twisted, and Wearable NO2 E-Textile Gas Sensor

**AI draft; human review NOT_REVIEWED. Не gold.**

Document `00f9cfc7-459f-4c4d-8131-b425d01527dc`; revision `7664effe-8f20-46e8-b694-224b75bea829`; split `DEV`.

Область: все доступные frozen abstract chunks. Полный текст статьи не заявляется доступным.

Chunks: 2; sentences: 6; mentions: 61; assertions: 51; concepts: 54; identity decisions: 9.

Структурная проверка: PASS. Семантическая проверка выполнена AI; независимой человеческой проверки не было.

Рубрика `pilot24-dev-rubric-0.2-WORKING`. Q1 решён для рабочей схемы DEV; human review не предоставлен. Открытые вопросы: нет.

Полнота AI-прохода: entities=True, relations=True. UNRESOLVED candidates: 0; UNRESOLVED accepted assertions: 0.

Unique canonical triples: 50; qualified groups: 51. Source mentions/assertions не удалялись.

## Полный доступный исходный текст

### Chunk 0: `6319af2d-0fe1-4daa-87c6-131c379a75c9`

Section `abstract`, section offsets [0, 928); SHA-256 `51d6b3595cc1b465fba348487a2c2784ee54f3ce01e850c9bea6eb5d424b0831`.

E-textiles are gaining growing popularity recently due to low cost, light weight, and conformable compatibility with clothes in wearable and portable smart electronics. Here, an easy-handing, low cost, and scalable fabricating strategy is reported to fabricate conductive, highly flexible, and mechanically stretchable/twisted fiber gas sensor with great wearability and knittability. The proposed gas sensor is built using commercially available cotton/elastic threads as flexible/stretchable templates and reduced graphene oxide/mesoporous zinc oxide nanosheets as sensing layers to form conducting fibers. The as-prepared fiber demonstrates sensitive sensing response, excellent long-term stability (84 days), low theoretical detection limit (43.5 ppb NO 2 ), great mechanical deformation tolerance (3000 bending cycles, 1000 twisting cycles and 65% strain strength), and washing durability in room-temperature gas detection.

### Chunk 1: `e9796bf6-68c8-440f-a814-ca185157cce3`

Section `abstract`, section offsets [929, 1490); SHA-256 `272bcd1547345d4fa14705d9e0af1c56a2d5692244e2bb2b8f3b8b04b12da3a3`.

More significantly, scalable wearable characteristics including repairability, reliability, stability, and practicability have been efficiently improved, which are achieved by knotting the fractured fibers, incorporating multiple sensors in series/parallel and weaving multisensor array networks integrated into clothes. The good sensing properties, superior flexibility, and scalable applications of wearable fibers may provide a broad window for widespread monitoring of numerous human activities in personal mobile electronics and human–machine interactions.

## Проверка предложений

### S1: [0, 168)

E-textiles are gaining growing popularity recently due to low cost, light weight, and conformable compatibility with clothes in wearable and portable smart electronics.

### S2: [169, 384)

Here, an easy-handing, low cost, and scalable fabricating strategy is reported to fabricate conductive, highly flexible, and mechanically stretchable/twisted fiber gas sensor with great wearability and knittability.

### S3: [385, 608)

The proposed gas sensor is built using commercially available cotton/elastic threads as flexible/stretchable templates and reduced graphene oxide/mesoporous zinc oxide nanosheets as sensing layers to form conducting fibers.

### S4: [609, 928)

The as-prepared fiber demonstrates sensitive sensing response, excellent long-term stability (84 days), low theoretical detection limit (43.5 ppb NO 2 ), great mechanical deformation tolerance (3000 bending cycles, 1000 twisting cycles and 65% strain strength), and washing durability in room-temperature gas detection.

84 days attaches to stability, 43.5 ppb to theoretical NO2 LOD, bending/twisting/strain values to mechanical tolerance. No numerical room-temperature value is inferred.

Q1 follow-up audit: removed room-temperature from individual performance assertions (response, stability, LOD, washing durability). It remains on gas detection only; the trailing modifier does not explicitly specify separate test conditions.

### S5: [0, 320)

More significantly, scalable wearable characteristics including repairability, reliability, stability, and practicability have been efficiently improved, which are achieved by knotting the fractured fibers, incorporating multiple sensors in series/parallel and weaving multisensor array networks integrated into clothes.

No invented respectively mapping: collective improvement preserved as two explicit coordinated bundles.

### S6: [321, 561)

The good sensing properties, superior flexibility, and scalable applications of wearable fibers may provide a broad window for widespread monitoring of numerous human activities in personal mobile electronics and human–machine interactions.

## Все упоминания

| Key | Sentence | Span | Exact surface | Kind / role | Canonical concept |
| --- | --- | --- | --- | --- | --- |
| textiles | S1 | [0, 10) | E-textiles | DEVICE / background_device_class | e-textile |
| cost | S1 | [58, 66) | low cost | PROPERTY / technical_property | low cost |
| weight | S1 | [68, 80) | light weight | PROPERTY / technical_property | light weight |
| compat | S1 | [86, 124) | conformable compatibility with clothes | PROPERTY / technical_property | conformable compatibility with clothes |
| clothes | S1 | [117, 124) | clothes | OTHER / integration_host | clothes |
| wearable | S1 | [128, 167) | wearable and portable smart electronics | APPLICATION / technical_application | wearable and portable smart electronics |
| strategy | S2 | [215, 235) | fabricating strategy | PROCESS / technical_process | fabricating strategy |
| easy | S2 | [178, 190) | easy-handing | PROPERTY / technical_property | easy-handing |
| cost2 | S2 | [192, 200) | low cost | PROPERTY / technical_property | low cost |
| scalable | S2 | [206, 214) | scalable | PROPERTY / technical_property | scalability |
| sensor | S2 | [327, 343) | fiber gas sensor | DEVICE / technical_device | study fiber gas sensor |
| conductive | S2 | [261, 271) | conductive | PROPERTY / technical_property | electrical conductivity |
| flex | S2 | [273, 288) | highly flexible | PROPERTY / technical_property | flexibility |
| stretch | S2 | [294, 326) | mechanically stretchable/twisted | PROPERTY / technical_property | mechanical stretchability and twistability |
| wearability | S2 | [349, 366) | great wearability | PROPERTY / technical_property | wearability |
| knit | S2 | [371, 383) | knittability | PROPERTY / technical_property | knittability |
| sensor3 | S3 | [398, 408) | gas sensor | DEVICE / technical_device | study fiber gas sensor |
| threads | S3 | [447, 469) | cotton/elastic threads | MATERIAL / fabrication_template | cotton/elastic threads |
| available | S3 | [424, 446) | commercially available | PROPERTY / technical_property | commercial availability |
| templates | S3 | [473, 503) | flexible/stretchable templates | OTHER / template_function | flexible/stretchable templates |
| template_flex | S3 | [473, 493) | flexible/stretchable | PROPERTY / technical_property | template flexibility/stretchability |
| layer_material | S3 | [508, 563) | reduced graphene oxide/mesoporous zinc oxide nanosheets | MATERIAL / sensing_material | reduced graphene oxide/mesoporous zinc oxide nanosheets |
| rgo | S3 | [508, 530) | reduced graphene oxide | MATERIAL / sensing_component | reduced graphene oxide |
| zno | S3 | [531, 563) | mesoporous zinc oxide nanosheets | MATERIAL / sensing_component | mesoporous zinc oxide nanosheets |
| mesoporous | S3 | [531, 541) | mesoporous | MORPHOLOGY / technical_morphology | mesoporosity |
| sheets | S3 | [553, 563) | nanosheets | MORPHOLOGY / technical_morphology | nanosheet morphology |
| layers | S3 | [567, 581) | sensing layers | DEVICE / functional_layer | sensing layer |
| fibers | S3 | [590, 607) | conducting fibers | DEVICE / technical_device | study fiber gas sensor |
| fiber4 | S4 | [613, 630) | as-prepared fiber | DEVICE / technical_device | study fiber gas sensor |
| response | S4 | [644, 670) | sensitive sensing response | PERFORMANCE / technical_performance | sensing response |
| stability | S4 | [672, 701) | excellent long-term stability | PERFORMANCE / technical_performance | long-term stability |
| lod | S4 | [713, 744) | low theoretical detection limit | PERFORMANCE / technical_performance | theoretical detection limit |
| no2 | S4 | [755, 759) | NO 2 | ANALYTE / target_analyte | nitrogen dioxide |
| tolerance | S4 | [763, 801) | great mechanical deformation tolerance | PERFORMANCE / technical_performance | mechanical deformation tolerance |
| bend | S4 | [808, 822) | bending cycles | PROCESS / technical_process | bending test |
| twist | S4 | [829, 844) | twisting cycles | PROCESS / technical_process | twisting test |
| strain | S4 | [853, 868) | strain strength | PERFORMANCE / technical_performance | strain strength (source wording) |
| wash | S4 | [875, 893) | washing durability | PERFORMANCE / technical_performance | washing durability |
| temp | S4 | [897, 913) | room-temperature | OPERATING_CONDITION / technical_operating_condition | room temperature |
| detection | S4 | [914, 927) | gas detection | PROCESS / technical_process | gas detection |
| wearable_characteristics | S5 | [64, 121) | repairability, reliability, stability, and practicability | PROPERTY / technical_property | wearable characteristic bundle |
| repair | S5 | [64, 77) | repairability | PROPERTY / technical_property | repairability |
| reliability | S5 | [79, 90) | reliability | PROPERTY / technical_property | reliability |
| stability5 | S5 | [92, 101) | stability | PROPERTY / technical_property | wearable stability |
| practicability | S5 | [107, 121) | practicability | PROPERTY / technical_property | practicability |
| methods | S5 | [176, 319) | knotting the fractured fibers, incorporating multiple sensors in series/parallel and weaving multisensor array networks integrated into clothes | PROCESS / technical_process | wearable improvement procedure bundle |
| knot | S5 | [176, 205) | knotting the fractured fibers | PROCESS / technical_process | knotting fractured fibers |
| fractured | S5 | [189, 205) | fractured fibers | DEVICE / technical_device | fractured sensing fibers |
| incorporate | S5 | [207, 256) | incorporating multiple sensors in series/parallel | PROCESS / technical_process | series/parallel sensor incorporation |
| sensors5 | S5 | [221, 237) | multiple sensors | DEVICE / technical_device | multiple sensing devices |
| wiring | S5 | [241, 256) | series/parallel | MORPHOLOGY / technical_morphology | series/parallel sensor arrangement |
| weave | S5 | [261, 319) | weaving multisensor array networks integrated into clothes | PROCESS / technical_process | weaving sensor networks into clothes |
| network | S5 | [269, 295) | multisensor array networks | DEVICE / technical_device | multisensor array network |
| clothes5 | S5 | [312, 319) | clothes | OTHER / integration_host | clothes |
| props | S6 | [325, 348) | good sensing properties | PERFORMANCE / technical_performance | sensing performance |
| flex6 | S6 | [350, 370) | superior flexibility | PROPERTY / technical_property | flexibility |
| applications | S6 | [376, 397) | scalable applications | APPLICATION / technical_application | scalable wearable fiber applications |
| fibers6 | S6 | [401, 416) | wearable fibers | DEVICE / technical_device | study fiber gas sensor |
| monitor | S6 | [459, 498) | monitoring of numerous human activities | APPLICATION / technical_application | human activity monitoring |
| mobile | S6 | [502, 529) | personal mobile electronics | APPLICATION / technical_application | personal mobile electronics |
| hmi | S6 | [534, 560) | human–machine interactions | APPLICATION / technical_application | human–machine interactions |

## Все утверждения

Направление каждой строки: head → tail. Полные UUID и evidence находятся в JSONL.

| # | Head | Relation | Tail | Modality / scope | Qualifiers | Evidence sentences | Semantic note |
| --- | --- | --- | --- | --- | --- | --- | --- |
| 1 | textiles | HAS_PROPERTY | cost | ASSERTED / BACKGROUND |  | S1 |  |
| 2 | textiles | HAS_PROPERTY | weight | ASSERTED / BACKGROUND |  | S1 |  |
| 3 | textiles | HAS_PROPERTY | compat | ASSERTED / BACKGROUND |  | S1 |  |
| 4 | textiles | USED_FOR | wearable | ASSERTED / BACKGROUND |  | S1 |  |
| 5 | sensor | FABRICATED_BY | strategy | ASSERTED / STUDY_RESULT |  | S2 |  |
| 6 | strategy | HAS_PROPERTY | easy | ASSERTED / STUDY_RESULT |  | S2 |  |
| 7 | strategy | HAS_PROPERTY | cost2 | ASSERTED / STUDY_RESULT |  | S2 |  |
| 8 | strategy | HAS_PROPERTY | scalable | ASSERTED / STUDY_RESULT |  | S2 |  |
| 9 | sensor | HAS_PROPERTY | conductive | ASSERTED / STUDY_RESULT |  | S2 |  |
| 10 | sensor | HAS_PROPERTY | flex | ASSERTED / STUDY_RESULT |  | S2 |  |
| 11 | sensor | HAS_PROPERTY | stretch | ASSERTED / STUDY_RESULT |  | S2 |  |
| 12 | sensor | HAS_PROPERTY | wearability | ASSERTED / STUDY_RESULT |  | S2 |  |
| 13 | sensor | HAS_PROPERTY | knit | ASSERTED / STUDY_RESULT |  | S2 |  |
| 14 | sensor3 | USES_MATERIAL | threads | ASSERTED / STUDY_RESULT |  | S3 | Template role, not analyte; slash retained without assuming a blend or two separate device instances. |
| 15 | threads | FUNCTIONS_AS | templates | ASSERTED / STUDY_RESULT |  | S3 |  |
| 16 | threads | HAS_PROPERTY | available | ASSERTED / STUDY_RESULT |  | S3 |  |
| 17 | templates | HAS_PROPERTY | template_flex | ASSERTED / STUDY_RESULT |  | S3 |  |
| 18 | sensor3 | USES_MATERIAL | layer_material | ASSERTED / STUDY_RESULT |  | S3 |  |
| 19 | layer_material | HAS_COMPONENT | rgo | ASSERTED / STUDY_RESULT |  | S3 |  |
| 20 | layer_material | HAS_COMPONENT | zno | ASSERTED / STUDY_RESULT |  | S3 |  |
| 21 | zno | HAS_MORPHOLOGY | mesoporous | ASSERTED / STUDY_RESULT |  | S3 |  |
| 22 | zno | HAS_MORPHOLOGY | sheets | ASSERTED / STUDY_RESULT |  | S3 |  |
| 23 | layer_material | FUNCTIONS_AS | layers | ASSERTED / STUDY_RESULT |  | S3 |  |
| 24 | sensor3 | HAS_COMPONENT | layers | ASSERTED / STUDY_RESULT |  | S3 |  |
| 25 | fiber4 | HAS_PERFORMANCE | response | ASSERTED / STUDY_RESULT |  | S4 |  |
| 26 | fiber4 | HAS_PERFORMANCE | stability | ASSERTED / STUDY_RESULT | duration: 84 days | S4 |  |
| 27 | fiber4 | HAS_PERFORMANCE | lod | ASSERTED / STUDY_RESULT | detection_limit: 43.5 ppb NO 2; estimation_status: theoretical | S4 |  |
| 28 | fiber4 | DETECTS | no2 | ASSERTED / STUDY_RESULT | temperature: room-temperature | S4 | NO2 is explicitly attached to the theoretical detection limit; do not substitute an unspecified gas. |
| 29 | fiber4 | HAS_PERFORMANCE | tolerance | ASSERTED / STUDY_RESULT | bending_cycles: 3000 bending cycles; twisting_cycles: 1000 twisting cycles; strain: 65% strain strength | S4 |  |
| 30 | fiber4 | HAS_PERFORMANCE | strain | ASSERTED / STUDY_RESULT | strain: 65% strain strength | S4 | Retain unusual source wording strain strength; no conversion to tensile stress or failure strain. |
| 31 | fiber4 | HAS_PERFORMANCE | wash | ASSERTED / STUDY_RESULT |  | S4 | Room-temperature modifies gas detection; no washing-test temperature is specified. Do not attach it to washing durability. |
| 32 | fiber4 | USED_FOR | detection | ASSERTED / STUDY_RESULT | temperature: room-temperature | S4 |  |
| 33 | methods | IMPROVES | wearable_characteristics | ASSERTED / STUDY_RESULT |  | S5 | Collective claim only. The text does not give a one-to-one mapping of three methods to four characteristics. |
| 34 | wearable_characteristics | HAS_MEMBER | repair | ASSERTED / STUDY_RESULT |  | S5 |  |
| 35 | wearable_characteristics | HAS_MEMBER | reliability | ASSERTED / STUDY_RESULT |  | S5 |  |
| 36 | wearable_characteristics | HAS_MEMBER | stability5 | ASSERTED / STUDY_RESULT |  | S5 |  |
| 37 | wearable_characteristics | HAS_MEMBER | practicability | ASSERTED / STUDY_RESULT |  | S5 |  |
| 38 | methods | HAS_MEMBER | knot | ASSERTED / STUDY_RESULT |  | S5 |  |
| 39 | methods | HAS_MEMBER | incorporate | ASSERTED / STUDY_RESULT |  | S5 |  |
| 40 | methods | HAS_MEMBER | weave | ASSERTED / STUDY_RESULT |  | S5 |  |
| 41 | knot | ACTS_ON | fractured | ASSERTED / STUDY_RESULT |  | S5 |  |
| 42 | incorporate | ACTS_ON | sensors5 | ASSERTED / STUDY_RESULT |  | S5 |  |
| 43 | weave | ACTS_ON | network | ASSERTED / STUDY_RESULT |  | S5 |  |
| 44 | sensors5 | HAS_MORPHOLOGY | wiring | ASSERTED / STUDY_RESULT |  | S5 |  |
| 45 | network | INTEGRATED_IN | clothes5 | ASSERTED / STUDY_RESULT |  | S5 |  |
| 46 | fibers6 | HAS_PERFORMANCE | props | ASSERTED / STUDY_RESULT |  | S6 |  |
| 47 | fibers6 | HAS_PROPERTY | flex6 | ASSERTED / STUDY_RESULT |  | S6 |  |
| 48 | fibers6 | USED_FOR | applications | HYPOTHETICAL / OUTLOOK |  | S6 | The source says may provide; these applications are not demonstrated outcomes. |
| 49 | fibers6 | USED_FOR | monitor | HYPOTHETICAL / OUTLOOK |  | S6 | The source says may provide; these applications are not demonstrated outcomes. |
| 50 | fibers6 | USED_FOR | mobile | HYPOTHETICAL / OUTLOOK |  | S6 | The source says may provide; these applications are not demonstrated outcomes. |
| 51 | fibers6 | USED_FOR | hmi | HYPOTHETICAL / OUTLOOK |  | S6 | The source says may provide; these applications are not demonstrated outcomes. |

## Все identity decisions

| Left | Label | Right | Основание |
| --- | --- | --- | --- |
| sensor | SAME | sensor3 | The proposed/as-prepared fiber sensor and final wearable fibers refer back to the same described study platform; device instances are not merged across documents. |
| sensor | SAME | fibers | The proposed/as-prepared fiber sensor and final wearable fibers refer back to the same described study platform; device instances are not merged across documents. |
| sensor | SAME | fiber4 | The proposed/as-prepared fiber sensor and final wearable fibers refer back to the same described study platform; device instances are not merged across documents. |
| sensor | SAME | fibers6 | The proposed/as-prepared fiber sensor and final wearable fibers refer back to the same described study platform; device instances are not merged across documents. |
| cost | SAME | cost2 | Same low-cost property concept; separate bearer assertions remain separate. |
| flex | SAME | flex6 | Same flexibility property, intensity preserved in surface text. |
| clothes | SAME | clothes5 | Same generic clothes concept, no claim of the same physical garment. |
| rgo | DIFFERENT | zno | Explicitly named distinct constituents of the sensing layer. |
| textiles | BROADER | sensor | E-textiles is the background device class; the described fiber gas sensor is a specific e-textile platform, not the class itself. |
