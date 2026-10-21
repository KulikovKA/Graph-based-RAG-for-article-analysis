# D001 — Reduced Graphene Oxide/Mesoporous ZnO NSs Hybrid Fibers for Flexible, Stretchable, Twisted, and Wearable NO2 E-Textile Gas Sensor

**AI draft — HUMAN_REVIEW=NOT_REVIEWED; не human gold.**

Document `00f9cfc7-459f-4c4d-8131-b425d01527dc`, revision `7664effe-8f20-46e8-b694-224b75bea829`, split `DEV`, rubric `pilot24-rubric-0.3-AUTO-FROZEN`.

Chunks 2; sentences 6; mentions 61; assertions 51; unique canonical triples 50; questions 0; validation PASS.

Полный AI-проход завершён. exhaustive_entities=True; exhaustive_relations=True; неразрешённые кандидаты не являются negative gold.

## Исходные frozen EvidenceChunks

### `6319af2d-0fe1-4daa-87c6-131c379a75c9`

SHA-256 `51d6b3595cc1b465fba348487a2c2784ee54f3ce01e850c9bea6eb5d424b0831`, section `abstract`; [0, 928).

E-textiles are gaining growing popularity recently due to low cost, light weight, and conformable compatibility with clothes in wearable and portable smart electronics. Here, an easy-handing, low cost, and scalable fabricating strategy is reported to fabricate conductive, highly flexible, and mechanically stretchable/twisted fiber gas sensor with great wearability and knittability. The proposed gas sensor is built using commercially available cotton/elastic threads as flexible/stretchable templates and reduced graphene oxide/mesoporous zinc oxide nanosheets as sensing layers to form conducting fibers. The as-prepared fiber demonstrates sensitive sensing response, excellent long-term stability (84 days), low theoretical detection limit (43.5 ppb NO 2 ), great mechanical deformation tolerance (3000 bending cycles, 1000 twisting cycles and 65% strain strength), and washing durability in room-temperature gas detection.

### `e9796bf6-68c8-440f-a814-ca185157cce3`

SHA-256 `272bcd1547345d4fa14705d9e0af1c56a2d5692244e2bb2b8f3b8b04b12da3a3`, section `abstract`; [929, 1490).

More significantly, scalable wearable characteristics including repairability, reliability, stability, and practicability have been efficiently improved, which are achieved by knotting the fractured fibers, incorporating multiple sensors in series/parallel and weaving multisensor array networks integrated into clothes. The good sensing properties, superior flexibility, and scalable applications of wearable fibers may provide a broad window for widespread monitoring of numerous human activities in personal mobile electronics and human–machine interactions.

## Semantic self-audit

All source sentences reviewed in curated first pass.
Q1/Q2/Q3 schema decisions applied; repeated triples counted separately from source assertions.
D001 room-temperature scope and D010 best/proposed mechanism audited in Q1_FOLLOWUP_AUDIT.md.

## Mentions

| Key | Sentence | Span | Surface | Kind / role | Canonical |
| --- | --- | --- | --- | --- | --- |
| textiles | S1 | [0,10) | E-textiles | DEVICE / background_device_class | e-textile |
| cost | S1 | [58,66) | low cost | PROPERTY / technical_property | low cost |
| weight | S1 | [68,80) | light weight | PROPERTY / technical_property | light weight |
| compat | S1 | [86,124) | conformable compatibility with clothes | PROPERTY / technical_property | conformable compatibility with clothes |
| clothes | S1 | [117,124) | clothes | OTHER / integration_host | clothes |
| wearable | S1 | [128,167) | wearable and portable smart electronics | APPLICATION / technical_application | wearable and portable smart electronics |
| strategy | S2 | [215,235) | fabricating strategy | PROCESS / technical_process | fabricating strategy |
| easy | S2 | [178,190) | easy-handing | PROPERTY / technical_property | easy-handing |
| cost2 | S2 | [192,200) | low cost | PROPERTY / technical_property | low cost |
| scalable | S2 | [206,214) | scalable | PROPERTY / technical_property | scalability |
| sensor | S2 | [327,343) | fiber gas sensor | DEVICE / technical_device | study fiber gas sensor |
| conductive | S2 | [261,271) | conductive | PROPERTY / technical_property | electrical conductivity |
| flex | S2 | [273,288) | highly flexible | PROPERTY / technical_property | flexibility |
| stretch | S2 | [294,326) | mechanically stretchable/twisted | PROPERTY / technical_property | mechanical stretchability and twistability |
| wearability | S2 | [349,366) | great wearability | PROPERTY / technical_property | wearability |
| knit | S2 | [371,383) | knittability | PROPERTY / technical_property | knittability |
| sensor3 | S3 | [398,408) | gas sensor | DEVICE / technical_device | study fiber gas sensor |
| threads | S3 | [447,469) | cotton/elastic threads | MATERIAL / fabrication_template | cotton/elastic threads |
| available | S3 | [424,446) | commercially available | PROPERTY / technical_property | commercial availability |
| templates | S3 | [473,503) | flexible/stretchable templates | OTHER / template_function | flexible/stretchable templates |
| template_flex | S3 | [473,493) | flexible/stretchable | PROPERTY / technical_property | template flexibility/stretchability |
| layer_material | S3 | [508,563) | reduced graphene oxide/mesoporous zinc oxide nanosheets | MATERIAL / sensing_material | reduced graphene oxide/mesoporous zinc oxide nanosheets |
| rgo | S3 | [508,530) | reduced graphene oxide | MATERIAL / sensing_component | reduced graphene oxide |
| zno | S3 | [531,563) | mesoporous zinc oxide nanosheets | MATERIAL / sensing_component | mesoporous zinc oxide nanosheets |
| mesoporous | S3 | [531,541) | mesoporous | MORPHOLOGY / technical_morphology | mesoporosity |
| sheets | S3 | [553,563) | nanosheets | MORPHOLOGY / technical_morphology | nanosheet morphology |
| layers | S3 | [567,581) | sensing layers | DEVICE / functional_layer | sensing layer |
| fibers | S3 | [590,607) | conducting fibers | DEVICE / technical_device | study fiber gas sensor |
| fiber4 | S4 | [613,630) | as-prepared fiber | DEVICE / technical_device | study fiber gas sensor |
| response | S4 | [644,670) | sensitive sensing response | PERFORMANCE / technical_performance | sensing response |
| stability | S4 | [672,701) | excellent long-term stability | PERFORMANCE / technical_performance | long-term stability |
| lod | S4 | [713,744) | low theoretical detection limit | PERFORMANCE / technical_performance | theoretical detection limit |
| no2 | S4 | [755,759) | NO 2 | ANALYTE / target_analyte | nitrogen dioxide |
| tolerance | S4 | [763,801) | great mechanical deformation tolerance | PERFORMANCE / technical_performance | mechanical deformation tolerance |
| bend | S4 | [808,822) | bending cycles | PROCESS / technical_process | bending test |
| twist | S4 | [829,844) | twisting cycles | PROCESS / technical_process | twisting test |
| strain | S4 | [853,868) | strain strength | PERFORMANCE / technical_performance | strain strength (source wording) |
| wash | S4 | [875,893) | washing durability | PERFORMANCE / technical_performance | washing durability |
| temp | S4 | [897,913) | room-temperature | OPERATING_CONDITION / technical_operating_condition | room temperature |
| detection | S4 | [914,927) | gas detection | PROCESS / technical_process | gas detection |
| wearable_characteristics | S5 | [64,121) | repairability, reliability, stability, and practicability | PROPERTY / technical_property | wearable characteristic bundle |
| repair | S5 | [64,77) | repairability | PROPERTY / technical_property | repairability |
| reliability | S5 | [79,90) | reliability | PROPERTY / technical_property | reliability |
| stability5 | S5 | [92,101) | stability | PROPERTY / technical_property | wearable stability |
| practicability | S5 | [107,121) | practicability | PROPERTY / technical_property | practicability |
| methods | S5 | [176,319) | knotting the fractured fibers, incorporating multiple sensors in series/parallel and weaving multisensor array networks integrated into clothes | PROCESS / technical_process | wearable improvement procedure bundle |
| knot | S5 | [176,205) | knotting the fractured fibers | PROCESS / technical_process | knotting fractured fibers |
| fractured | S5 | [189,205) | fractured fibers | DEVICE / technical_device | fractured sensing fibers |
| incorporate | S5 | [207,256) | incorporating multiple sensors in series/parallel | PROCESS / technical_process | series/parallel sensor incorporation |
| sensors5 | S5 | [221,237) | multiple sensors | DEVICE / technical_device | multiple sensing devices |
| wiring | S5 | [241,256) | series/parallel | MORPHOLOGY / technical_morphology | series/parallel sensor arrangement |
| weave | S5 | [261,319) | weaving multisensor array networks integrated into clothes | PROCESS / technical_process | weaving sensor networks into clothes |
| network | S5 | [269,295) | multisensor array networks | DEVICE / technical_device | multisensor array network |
| clothes5 | S5 | [312,319) | clothes | OTHER / integration_host | clothes |
| props | S6 | [325,348) | good sensing properties | PERFORMANCE / technical_performance | sensing performance |
| flex6 | S6 | [350,370) | superior flexibility | PROPERTY / technical_property | flexibility |
| applications | S6 | [376,397) | scalable applications | APPLICATION / technical_application | scalable wearable fiber applications |
| fibers6 | S6 | [401,416) | wearable fibers | DEVICE / technical_device | study fiber gas sensor |
| monitor | S6 | [459,498) | monitoring of numerous human activities | APPLICATION / technical_application | human activity monitoring |
| mobile | S6 | [502,529) | personal mobile electronics | APPLICATION / technical_application | personal mobile electronics |
| hmi | S6 | [534,560) | human–machine interactions | APPLICATION / technical_application | human–machine interactions |

## Assertions

| Head | Relation | Tail | Polarity | Modality / scope | Qualifiers | Evidence span IDs |
| --- | --- | --- | --- | --- | --- | --- |
| textiles | HAS_PROPERTY | cost | POSITIVE | ASSERTED / BACKGROUND |  | 4ad6880f-0cba-5980-92a5-669c69042710 |
| textiles | HAS_PROPERTY | weight | POSITIVE | ASSERTED / BACKGROUND |  | 4ad6880f-0cba-5980-92a5-669c69042710 |
| textiles | HAS_PROPERTY | compat | POSITIVE | ASSERTED / BACKGROUND |  | 4ad6880f-0cba-5980-92a5-669c69042710 |
| textiles | USED_FOR | wearable | POSITIVE | ASSERTED / BACKGROUND |  | 4ad6880f-0cba-5980-92a5-669c69042710 |
| sensor | FABRICATED_BY | strategy | POSITIVE | ASSERTED / STUDY_RESULT |  | d07bf71f-db7c-5701-bc5b-fcfc2796a393 |
| strategy | HAS_PROPERTY | easy | POSITIVE | ASSERTED / STUDY_RESULT |  | d07bf71f-db7c-5701-bc5b-fcfc2796a393 |
| strategy | HAS_PROPERTY | cost2 | POSITIVE | ASSERTED / STUDY_RESULT |  | d07bf71f-db7c-5701-bc5b-fcfc2796a393 |
| strategy | HAS_PROPERTY | scalable | POSITIVE | ASSERTED / STUDY_RESULT |  | d07bf71f-db7c-5701-bc5b-fcfc2796a393 |
| sensor | HAS_PROPERTY | conductive | POSITIVE | ASSERTED / STUDY_RESULT |  | d07bf71f-db7c-5701-bc5b-fcfc2796a393 |
| sensor | HAS_PROPERTY | flex | POSITIVE | ASSERTED / STUDY_RESULT |  | d07bf71f-db7c-5701-bc5b-fcfc2796a393 |
| sensor | HAS_PROPERTY | stretch | POSITIVE | ASSERTED / STUDY_RESULT |  | d07bf71f-db7c-5701-bc5b-fcfc2796a393 |
| sensor | HAS_PROPERTY | wearability | POSITIVE | ASSERTED / STUDY_RESULT |  | d07bf71f-db7c-5701-bc5b-fcfc2796a393 |
| sensor | HAS_PROPERTY | knit | POSITIVE | ASSERTED / STUDY_RESULT |  | d07bf71f-db7c-5701-bc5b-fcfc2796a393 |
| sensor3 | USES_MATERIAL | threads | POSITIVE | ASSERTED / STUDY_RESULT |  | e4355556-02d0-5f32-9f45-e05222058885 |
| threads | FUNCTIONS_AS | templates | POSITIVE | ASSERTED / STUDY_RESULT |  | e4355556-02d0-5f32-9f45-e05222058885 |
| threads | HAS_PROPERTY | available | POSITIVE | ASSERTED / STUDY_RESULT |  | e4355556-02d0-5f32-9f45-e05222058885 |
| templates | HAS_PROPERTY | template_flex | POSITIVE | ASSERTED / STUDY_RESULT |  | e4355556-02d0-5f32-9f45-e05222058885 |
| sensor3 | USES_MATERIAL | layer_material | POSITIVE | ASSERTED / STUDY_RESULT |  | e4355556-02d0-5f32-9f45-e05222058885 |
| layer_material | HAS_COMPONENT | rgo | POSITIVE | ASSERTED / STUDY_RESULT |  | e4355556-02d0-5f32-9f45-e05222058885 |
| layer_material | HAS_COMPONENT | zno | POSITIVE | ASSERTED / STUDY_RESULT |  | e4355556-02d0-5f32-9f45-e05222058885 |
| zno | HAS_MORPHOLOGY | mesoporous | POSITIVE | ASSERTED / STUDY_RESULT |  | e4355556-02d0-5f32-9f45-e05222058885 |
| zno | HAS_MORPHOLOGY | sheets | POSITIVE | ASSERTED / STUDY_RESULT |  | e4355556-02d0-5f32-9f45-e05222058885 |
| layer_material | FUNCTIONS_AS | layers | POSITIVE | ASSERTED / STUDY_RESULT |  | e4355556-02d0-5f32-9f45-e05222058885 |
| sensor3 | HAS_COMPONENT | layers | POSITIVE | ASSERTED / STUDY_RESULT |  | e4355556-02d0-5f32-9f45-e05222058885 |
| fiber4 | HAS_PERFORMANCE | response | POSITIVE | ASSERTED / STUDY_RESULT |  | aadcaf5c-4da9-5afb-9ffc-adb72fc324c0 |
| fiber4 | HAS_PERFORMANCE | stability | POSITIVE | ASSERTED / STUDY_RESULT | duration: 84 days → 84 | aadcaf5c-4da9-5afb-9ffc-adb72fc324c0 |
| fiber4 | HAS_PERFORMANCE | lod | POSITIVE | ASSERTED / STUDY_RESULT | detection_limit: 43.5 ppb NO 2 → 43.5; estimation_status: theoretical → theoretical | aadcaf5c-4da9-5afb-9ffc-adb72fc324c0 |
| fiber4 | DETECTS | no2 | POSITIVE | ASSERTED / STUDY_RESULT | temperature: room-temperature → room temperature | aadcaf5c-4da9-5afb-9ffc-adb72fc324c0 |
| fiber4 | HAS_PERFORMANCE | tolerance | POSITIVE | ASSERTED / STUDY_RESULT | bending_cycles: 3000 bending cycles → 3000; twisting_cycles: 1000 twisting cycles → 1000; strain: 65% strain strength → 65 | aadcaf5c-4da9-5afb-9ffc-adb72fc324c0 |
| fiber4 | HAS_PERFORMANCE | strain | POSITIVE | ASSERTED / STUDY_RESULT | strain: 65% strain strength → 65 | aadcaf5c-4da9-5afb-9ffc-adb72fc324c0 |
| fiber4 | HAS_PERFORMANCE | wash | POSITIVE | ASSERTED / STUDY_RESULT |  | aadcaf5c-4da9-5afb-9ffc-adb72fc324c0 |
| fiber4 | USED_FOR | detection | POSITIVE | ASSERTED / STUDY_RESULT | temperature: room-temperature → room temperature | aadcaf5c-4da9-5afb-9ffc-adb72fc324c0 |
| methods | IMPROVES | wearable_characteristics | POSITIVE | ASSERTED / STUDY_RESULT |  | 36fac382-92d6-5f57-8be2-567420efdf00 |
| wearable_characteristics | HAS_MEMBER | repair | POSITIVE | ASSERTED / STUDY_RESULT |  | 36fac382-92d6-5f57-8be2-567420efdf00 |
| wearable_characteristics | HAS_MEMBER | reliability | POSITIVE | ASSERTED / STUDY_RESULT |  | 36fac382-92d6-5f57-8be2-567420efdf00 |
| wearable_characteristics | HAS_MEMBER | stability5 | POSITIVE | ASSERTED / STUDY_RESULT |  | 36fac382-92d6-5f57-8be2-567420efdf00 |
| wearable_characteristics | HAS_MEMBER | practicability | POSITIVE | ASSERTED / STUDY_RESULT |  | 36fac382-92d6-5f57-8be2-567420efdf00 |
| methods | HAS_MEMBER | knot | POSITIVE | ASSERTED / STUDY_RESULT |  | 36fac382-92d6-5f57-8be2-567420efdf00 |
| methods | HAS_MEMBER | incorporate | POSITIVE | ASSERTED / STUDY_RESULT |  | 36fac382-92d6-5f57-8be2-567420efdf00 |
| methods | HAS_MEMBER | weave | POSITIVE | ASSERTED / STUDY_RESULT |  | 36fac382-92d6-5f57-8be2-567420efdf00 |
| knot | ACTS_ON | fractured | POSITIVE | ASSERTED / STUDY_RESULT |  | 36fac382-92d6-5f57-8be2-567420efdf00 |
| incorporate | ACTS_ON | sensors5 | POSITIVE | ASSERTED / STUDY_RESULT |  | 36fac382-92d6-5f57-8be2-567420efdf00 |
| weave | ACTS_ON | network | POSITIVE | ASSERTED / STUDY_RESULT |  | 36fac382-92d6-5f57-8be2-567420efdf00 |
| sensors5 | HAS_MORPHOLOGY | wiring | POSITIVE | ASSERTED / STUDY_RESULT |  | 36fac382-92d6-5f57-8be2-567420efdf00 |
| network | INTEGRATED_IN | clothes5 | POSITIVE | ASSERTED / STUDY_RESULT |  | 36fac382-92d6-5f57-8be2-567420efdf00 |
| fibers6 | HAS_PERFORMANCE | props | POSITIVE | ASSERTED / STUDY_RESULT |  | 80563c4f-9b75-51ad-9e13-3a68fd07272a |
| fibers6 | HAS_PROPERTY | flex6 | POSITIVE | ASSERTED / STUDY_RESULT |  | 80563c4f-9b75-51ad-9e13-3a68fd07272a |
| fibers6 | USED_FOR | applications | POSITIVE | HYPOTHETICAL / OUTLOOK |  | 80563c4f-9b75-51ad-9e13-3a68fd07272a |
| fibers6 | USED_FOR | monitor | POSITIVE | HYPOTHETICAL / OUTLOOK |  | 80563c4f-9b75-51ad-9e13-3a68fd07272a |
| fibers6 | USED_FOR | mobile | POSITIVE | HYPOTHETICAL / OUTLOOK |  | 80563c4f-9b75-51ad-9e13-3a68fd07272a |
| fibers6 | USED_FOR | hmi | POSITIVE | HYPOTHETICAL / OUTLOOK |  | 80563c4f-9b75-51ad-9e13-3a68fd07272a |

## Identity decisions

| Left | Label | Right | Reason |
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

## Unresolved

# Вопросы документа

Все открытые вопросы UNRESOLVED. Они не блокировали автоматический проход. Q1/Q2/Q3 решены пользователем и находятся в adjudication_decisions.jsonl.
