# D003 — Moisture-resistant, stretchable NOx gas sensors based on laser-induced graphene for environmental monitoring and breath analysis

**AI draft — HUMAN_REVIEW=NOT_REVIEWED; не human gold.**

Document `06066c66-1454-4813-b7b7-f366b9956035`, revision `7af46631-a38f-430d-a43c-bcfa0dccac9e`, split `DEV`, rubric `pilot24-rubric-0.3-AUTO-FROZEN`.

Chunks 2; sentences 7; mentions 69; assertions 46; unique canonical triples 43; questions 0; validation PASS.

Полный AI-проход завершён. exhaustive_entities=True; exhaustive_relations=True; неразрешённые кандидаты не являются negative gold.

## Исходные frozen EvidenceChunks

### `0ad16539-951a-4c6a-95df-0d92179b23eb`

SHA-256 `93b3b8cd46f210f24559ada46e4094b348260a9b1c0be1b96965d77ac32e55ae`, section `abstract`; [0, 1017).

Abstract The accurate, continuous analysis of healthcare-relevant gases such as nitrogen oxides (NO x ) in a humid environment remains elusive for low-cost, stretchable gas sensing devices. This study presents the design and demonstration of a moisture-resistant, stretchable NO x gas sensor based on laser-induced graphene (LIG). Sandwiched between a soft elastomeric substrate and a moisture-resistant semipermeable encapsulant, the LIG sensing and electrode layer is first optimized by tuning laser processing parameters such as power, image density, and defocus distance. The gas sensor, using a needlelike LIG prepared with optimal laser processing parameters, exhibits a large response of 4.18‰ ppm −1 to NO and 6.66‰ ppm −1 to NO 2 , an ultralow detection limit of 8.3 ppb to NO and 4.0 ppb to NO 2 , fast response/recovery, and excellent selectivity. The design of a stretchable serpentine structure in the LIG electrode and strain isolation from the stiff island allows the gas sensor to be stretched by 30%.

### `45f36916-7688-4edb-8dd1-2ac50ea13339`

SHA-256 `93b20b0f39df3ee410854241c279ea62bb58bb7097cf578d2413e403427c1a88`, section `abstract`; [1018, 1516).

Combined with a moisture-resistant property against a relative humidity of 90%, the reported gas sensor has further been demonstrated to monitor the personal local environment during different times of the day and analyze human breath samples to classify patients with respiratory diseases from healthy volunteers. Moisture-resistant, stretchable NO x gas sensors can expand the capability of wearable devices to detect biomarkers from humans and exposed environments for early disease diagnostics.

## Semantic self-audit

All source sentences reviewed in curated first pass.
Q1/Q2/Q3 schema decisions applied; repeated triples counted separately from source assertions.
D001 room-temperature scope and D010 best/proposed mechanism audited in Q1_FOLLOWUP_AUDIT.md.

## Mentions

| Key | Sentence | Span | Surface | Kind / role | Canonical |
| --- | --- | --- | --- | --- | --- |
| analysis | S1 | [13,42) | accurate, continuous analysis | PROCESS / background_unmet_goal | accurate continuous gas analysis |
| gases | S1 | [46,71) | healthcare-relevant gases | ANALYTE / background_analyte_class | healthcare-relevant gases |
| nox | S1 | [80,95) | nitrogen oxides | ANALYTE / target_analyte_class | nitrogen oxides |
| nox_alias | S1 | [97,101) | NO x | ANALYTE / target_analyte_class | nitrogen oxides |
| humid | S1 | [109,126) | humid environment | OPERATING_CONDITION / technical_operating_condition | humid environment |
| cost | S1 | [147,155) | low-cost | PROPERTY / technical_property | low cost |
| stretch1 | S1 | [157,168) | stretchable | PROPERTY / technical_property | stretchability |
| devices | S1 | [169,188) | gas sensing devices | DEVICE / technical_device | background low-cost stretchable gas sensors |
| sensor | S2 | [244,291) | moisture-resistant, stretchable NO x gas sensor | DEVICE / technical_device | study stretchable LIG NOx sensor |
| moist | S2 | [244,262) | moisture-resistant | PROPERTY / technical_property | moisture resistance |
| stretch2 | S2 | [264,275) | stretchable | PROPERTY / technical_property | stretchability |
| nox2 | S2 | [276,280) | NO x | ANALYTE / target_analyte_class | nitrogen oxides |
| lig | S2 | [301,323) | laser-induced graphene | MATERIAL / technical_material | laser-induced graphene |
| lig_alias | S2 | [325,328) | LIG | MATERIAL / technical_material | laser-induced graphene |
| substrate | S3 | [352,378) | soft elastomeric substrate | DEVICE / support_component | elastomeric substrate |
| soft | S3 | [352,356) | soft | PROPERTY / technical_property | softness |
| elastomer | S3 | [357,368) | elastomeric | MATERIAL / substrate_material_class | elastomer (unspecified) |
| encap | S3 | [385,429) | moisture-resistant semipermeable encapsulant | DEVICE / encapsulation_component | semipermeable encapsulant |
| encap_moist | S3 | [385,403) | moisture-resistant | PROPERTY / technical_property | moisture resistance |
| semi | S3 | [404,417) | semipermeable | PROPERTY / technical_property | semipermeability |
| layer | S3 | [435,466) | LIG sensing and electrode layer | DEVICE / dual_function_layer | LIG sensing/electrode layer |
| lig3 | S3 | [435,438) | LIG | MATERIAL / technical_material | laser-induced graphene |
| tuning | S3 | [489,523) | tuning laser processing parameters | PROCESS / technical_process | laser parameter tuning |
| laser | S3 | [496,512) | laser processing | PROCESS / technical_process | laser processing |
| parameters | S3 | [496,523) | laser processing parameters | PROPERTY / technical_property | laser processing parameter group |
| power | S3 | [532,537) | power | PROPERTY / fabrication_parameter | laser power |
| density | S3 | [539,552) | image density | PROPERTY / fabrication_parameter | laser image density |
| defocus | S3 | [558,574) | defocus distance | PROPERTY / fabrication_parameter | laser defocus distance |
| sensor4 | S4 | [580,590) | gas sensor | DEVICE / technical_device | study stretchable LIG NOx sensor |
| lig4 | S4 | [600,614) | needlelike LIG | MATERIAL / technical_material | needlelike laser-induced graphene |
| needle | S4 | [600,610) | needlelike | MORPHOLOGY / technical_morphology | needlelike morphology |
| laser4 | S4 | [637,653) | laser processing | PROCESS / technical_process | laser processing |
| settings | S4 | [629,664) | optimal laser processing parameters | PROPERTY / technical_property | optimal laser processing parameters |
| response | S4 | [677,691) | large response | PERFORMANCE / technical_performance | gas response per concentration |
| no_resp | S4 | [711,713) | NO | ANALYTE / target_analyte | nitric oxide |
| no2_resp | S4 | [734,738) | NO 2 | ANALYTE / target_analyte | nitrogen dioxide |
| lod | S4 | [744,768) | ultralow detection limit | PERFORMANCE / technical_performance | detection limit |
| no_lod | S4 | [783,785) | NO | ANALYTE / target_analyte | nitric oxide |
| no2_lod | S4 | [801,805) | NO 2 | ANALYTE / target_analyte | nitrogen dioxide |
| speed | S4 | [808,830) | fast response/recovery | PERFORMANCE / technical_performance | response/recovery speed |
| selectivity | S4 | [836,857) | excellent selectivity | PERFORMANCE / technical_performance | selectivity |
| design | S5 | [863,907) | design of a stretchable serpentine structure | PROCESS / technical_process | serpentine structure design |
| mechanism5 | S5 | [863,971) | design of a stretchable serpentine structure in the LIG electrode and strain isolation from the stiff island | MECHANISM / technical_mechanism | combined serpentine design and strain isolation |
| serpentine | S5 | [875,907) | stretchable serpentine structure | MORPHOLOGY / technical_morphology | stretchable serpentine structure |
| electrode | S5 | [915,928) | LIG electrode | DEVICE / technical_device | LIG electrode |
| lig5 | S5 | [915,918) | LIG | MATERIAL / technical_material | laser-induced graphene |
| isolation | S5 | [933,949) | strain isolation | MECHANISM / technical_mechanism | strain isolation |
| island | S5 | [959,971) | stiff island | DEVICE / mechanical_isolation_component | stiff island |
| stiff | S5 | [959,964) | stiff | PROPERTY / technical_property | stiffness |
| sensor5 | S5 | [983,993) | gas sensor | DEVICE / technical_device | study stretchable LIG NOx sensor |
| stretch5 | S5 | [1000,1016) | stretched by 30% | PERFORMANCE / technical_performance | demonstrated stretching capability |
| moist6 | S6 | [16,43) | moisture-resistant property | PROPERTY / technical_property | moisture resistance |
| rh | S6 | [54,78) | relative humidity of 90% | OPERATING_CONDITION / technical_operating_condition | relative humidity 90% |
| sensor6 | S6 | [93,103) | gas sensor | DEVICE / technical_device | study stretchable LIG NOx sensor |
| monitor | S6 | [137,175) | monitor the personal local environment | APPLICATION / technical_application | personal local environmental monitoring |
| time | S6 | [183,209) | different times of the day | OPERATING_CONDITION / technical_operating_condition | different times of day |
| breath | S6 | [214,242) | analyze human breath samples | APPLICATION / technical_application | human breath analysis |
| samples | S6 | [222,242) | human breath samples | ANALYTE / sample_matrix | human breath samples |
| classify | S6 | [246,313) | classify patients with respiratory diseases from healthy volunteers | APPLICATION / technical_application | classification of respiratory-disease patients versus healthy volunteers |
| disease | S6 | [269,289) | respiratory diseases | OTHER / clinical_target | respiratory diseases |
| healthy | S6 | [295,313) | healthy volunteers | OTHER / comparison_population | healthy volunteers |
| sensor7 | S7 | [315,363) | Moisture-resistant, stretchable NO x gas sensors | DEVICE / technical_device | study stretchable LIG NOx sensor |
| moist7 | S7 | [315,333) | Moisture-resistant | PROPERTY / technical_property | moisture resistance |
| stretch7 | S7 | [335,346) | stretchable | PROPERTY / technical_property | stretchability |
| nox7 | S7 | [347,351) | NO x | ANALYTE / target_analyte_class | nitrogen oxides |
| wearables | S7 | [393,409) | wearable devices | DEVICE / prospective_device_class | wearable devices |
| biomarkers | S7 | [420,430) | biomarkers | ANALYTE / prospective_target_class | biomarkers (unspecified) |
| environments | S7 | [447,467) | exposed environments | OTHER / prospective_sampling_context | exposed environments |
| diagnostics | S7 | [472,497) | early disease diagnostics | APPLICATION / technical_application | early disease diagnostics |

## Assertions

| Head | Relation | Tail | Polarity | Modality / scope | Qualifiers | Evidence span IDs |
| --- | --- | --- | --- | --- | --- | --- |
| devices | HAS_PROPERTY | cost | POSITIVE | ASSERTED / BACKGROUND |  | 72d788e6-48ec-5848-875f-8b34a1dcb91c |
| devices | HAS_PROPERTY | stretch1 | POSITIVE | ASSERTED / BACKGROUND |  | 72d788e6-48ec-5848-875f-8b34a1dcb91c |
| sensor | HAS_PROPERTY | moist | POSITIVE | ASSERTED / STUDY_RESULT |  | 73113aa1-86d2-55d0-acf5-9945e1cdf6b1 |
| sensor | HAS_PROPERTY | stretch2 | POSITIVE | ASSERTED / STUDY_RESULT |  | 73113aa1-86d2-55d0-acf5-9945e1cdf6b1 |
| sensor | USES_MATERIAL | lig | POSITIVE | ASSERTED / STUDY_RESULT |  | 73113aa1-86d2-55d0-acf5-9945e1cdf6b1 |
| sensor | DETECTS | nox2 | POSITIVE | ASSERTED / STUDY_RESULT |  | 73113aa1-86d2-55d0-acf5-9945e1cdf6b1 |
| substrate | HAS_PROPERTY | soft | POSITIVE | ASSERTED / STUDY_RESULT |  | e832c7c7-01f3-55df-80b0-87db32986efa |
| substrate | USES_MATERIAL | elastomer | POSITIVE | ASSERTED / STUDY_RESULT |  | e832c7c7-01f3-55df-80b0-87db32986efa |
| encap | HAS_PROPERTY | encap_moist | POSITIVE | ASSERTED / STUDY_RESULT |  | e832c7c7-01f3-55df-80b0-87db32986efa |
| encap | HAS_PROPERTY | semi | POSITIVE | ASSERTED / STUDY_RESULT |  | e832c7c7-01f3-55df-80b0-87db32986efa |
| layer | USES_MATERIAL | lig3 | POSITIVE | ASSERTED / STUDY_RESULT |  | e832c7c7-01f3-55df-80b0-87db32986efa |
| sensor | HAS_COMPONENT | substrate | POSITIVE | ASSERTED / STUDY_RESULT |  | 73113aa1-86d2-55d0-acf5-9945e1cdf6b1; e832c7c7-01f3-55df-80b0-87db32986efa |
| sensor | HAS_COMPONENT | encap | POSITIVE | ASSERTED / STUDY_RESULT |  | 73113aa1-86d2-55d0-acf5-9945e1cdf6b1; e832c7c7-01f3-55df-80b0-87db32986efa |
| sensor | HAS_COMPONENT | layer | POSITIVE | ASSERTED / STUDY_RESULT | layer_position: Sandwiched between a soft elastomeric substrate and a moisture-resistant semipermeable encapsulant → LIG sensing/electrode layer between substrate and encapsulant | 73113aa1-86d2-55d0-acf5-9945e1cdf6b1; e832c7c7-01f3-55df-80b0-87db32986efa |
| parameters | HAS_MEMBER | power | POSITIVE | ASSERTED / STUDY_RESULT |  | e832c7c7-01f3-55df-80b0-87db32986efa |
| laser | HAS_PROPERTY | power | POSITIVE | ASSERTED / STUDY_RESULT |  | e832c7c7-01f3-55df-80b0-87db32986efa |
| parameters | HAS_MEMBER | density | POSITIVE | ASSERTED / STUDY_RESULT |  | e832c7c7-01f3-55df-80b0-87db32986efa |
| laser | HAS_PROPERTY | density | POSITIVE | ASSERTED / STUDY_RESULT |  | e832c7c7-01f3-55df-80b0-87db32986efa |
| parameters | HAS_MEMBER | defocus | POSITIVE | ASSERTED / STUDY_RESULT |  | e832c7c7-01f3-55df-80b0-87db32986efa |
| laser | HAS_PROPERTY | defocus | POSITIVE | ASSERTED / STUDY_RESULT |  | e832c7c7-01f3-55df-80b0-87db32986efa |
| sensor4 | USES_MATERIAL | lig4 | POSITIVE | ASSERTED / STUDY_RESULT |  | d8f1c3e3-9373-5f3f-951d-8e659b2d20dc |
| lig4 | HAS_MORPHOLOGY | needle | POSITIVE | ASSERTED / STUDY_RESULT |  | d8f1c3e3-9373-5f3f-951d-8e659b2d20dc |
| lig4 | FABRICATED_BY | laser4 | POSITIVE | ASSERTED / STUDY_RESULT | parameter_selection: optimal laser processing parameters → optimal (values unspecified) | d8f1c3e3-9373-5f3f-951d-8e659b2d20dc |
| sensor4 | DETECTS | no_resp | POSITIVE | ASSERTED / STUDY_RESULT | response_per_concentration: 4.18‰ ppm −1 to NO → 4.18 | d8f1c3e3-9373-5f3f-951d-8e659b2d20dc |
| sensor4 | DETECTS | no2_resp | POSITIVE | ASSERTED / STUDY_RESULT | response_per_concentration: 6.66‰ ppm −1 to NO 2 → 6.66 | d8f1c3e3-9373-5f3f-951d-8e659b2d20dc |
| sensor4 | HAS_PERFORMANCE | response | POSITIVE | ASSERTED / STUDY_RESULT | NO_response_per_concentration: 4.18‰ ppm −1 to NO → 4.18; NO2_response_per_concentration: 6.66‰ ppm −1 to NO 2 → 6.66 | d8f1c3e3-9373-5f3f-951d-8e659b2d20dc |
| sensor4 | HAS_PERFORMANCE | lod | POSITIVE | ASSERTED / STUDY_RESULT | NO_detection_limit: 8.3 ppb to NO → 8.3; NO2_detection_limit: 4.0 ppb to NO 2 → 4.0 | d8f1c3e3-9373-5f3f-951d-8e659b2d20dc |
| sensor4 | HAS_PERFORMANCE | speed | POSITIVE | ASSERTED / STUDY_RESULT |  | d8f1c3e3-9373-5f3f-951d-8e659b2d20dc |
| sensor4 | HAS_PERFORMANCE | selectivity | POSITIVE | ASSERTED / STUDY_RESULT |  | d8f1c3e3-9373-5f3f-951d-8e659b2d20dc |
| electrode | USES_MATERIAL | lig5 | POSITIVE | ASSERTED / STUDY_RESULT |  | 065cf8f6-8363-53ff-8baf-8edf6f90f04c |
| electrode | HAS_MORPHOLOGY | serpentine | POSITIVE | ASSERTED / STUDY_RESULT |  | 065cf8f6-8363-53ff-8baf-8edf6f90f04c |
| island | HAS_PROPERTY | stiff | POSITIVE | ASSERTED / STUDY_RESULT |  | 065cf8f6-8363-53ff-8baf-8edf6f90f04c |
| sensor5 | HAS_PERFORMANCE | stretch5 | POSITIVE | ASSERTED / STUDY_RESULT | stretch: 30% → 30 | 065cf8f6-8363-53ff-8baf-8edf6f90f04c |
| sensor5 | HAS_MECHANISM | mechanism5 | POSITIVE | ASSERTED / STUDY_RESULT | explained_capability: stretched by 30% → stretching by 30% | 065cf8f6-8363-53ff-8baf-8edf6f90f04c |
| mechanism5 | MECHANISM_INVOLVES | design | POSITIVE | ASSERTED / STUDY_RESULT |  | 065cf8f6-8363-53ff-8baf-8edf6f90f04c |
| mechanism5 | MECHANISM_INVOLVES | serpentine | POSITIVE | ASSERTED / STUDY_RESULT |  | 065cf8f6-8363-53ff-8baf-8edf6f90f04c |
| mechanism5 | MECHANISM_INVOLVES | isolation | POSITIVE | ASSERTED / STUDY_RESULT | isolation_reference: from the stiff island → stiff island | 065cf8f6-8363-53ff-8baf-8edf6f90f04c |
| sensor6 | HAS_PROPERTY | moist6 | POSITIVE | ASSERTED / STUDY_RESULT | relative_humidity: relative humidity of 90% → 90 | e7d14908-0d6c-52fb-88ef-f0410a21a8c4 |
| sensor6 | USED_FOR | monitor | POSITIVE | ASSERTED / STUDY_RESULT | monitoring_times: different times of the day → different times of day | e7d14908-0d6c-52fb-88ef-f0410a21a8c4 |
| sensor6 | USED_FOR | breath | POSITIVE | ASSERTED / STUDY_RESULT |  | e7d14908-0d6c-52fb-88ef-f0410a21a8c4 |
| sensor6 | USED_FOR | classify | POSITIVE | ASSERTED / STUDY_RESULT |  | e7d14908-0d6c-52fb-88ef-f0410a21a8c4 |
| sensor7 | HAS_PROPERTY | moist7 | POSITIVE | ASSERTED / STUDY_RESULT |  | 35614777-893b-57e0-9c21-3c32fd90477a |
| sensor7 | HAS_PROPERTY | stretch7 | POSITIVE | ASSERTED / STUDY_RESULT |  | 35614777-893b-57e0-9c21-3c32fd90477a |
| sensor7 | USED_FOR | diagnostics | POSITIVE | HYPOTHETICAL / OUTLOOK |  | 35614777-893b-57e0-9c21-3c32fd90477a |
| wearables | DETECTS | biomarkers | POSITIVE | HYPOTHETICAL / OUTLOOK |  | 35614777-893b-57e0-9c21-3c32fd90477a |
| tuning | OPTIMIZES | layer | POSITIVE | ASSERTED / STUDY_RESULT |  | e832c7c7-01f3-55df-80b0-87db32986efa |

## Identity decisions

| Left | Label | Right | Reason |
| --- | --- | --- | --- |
| sensor | SAME | sensor4 | Repeated study gas sensor/platform; source scopes and configurations remain local. |
| sensor | SAME | sensor5 | Repeated study gas sensor/platform; source scopes and configurations remain local. |
| sensor | SAME | sensor6 | Repeated study gas sensor/platform; source scopes and configurations remain local. |
| sensor | SAME | sensor7 | Repeated study gas sensor/platform; source scopes and configurations remain local. |
| lig | SAME | lig_alias | Explicit laser-induced graphene (LIG) definition and repeated acronym. |
| lig | SAME | lig3 | Explicit laser-induced graphene (LIG) definition and repeated acronym. |
| lig | SAME | lig5 | Explicit laser-induced graphene (LIG) definition and repeated acronym. |
| lig | BROADER | lig4 | Needlelike LIG specifies morphology; generic LIG is not narrowed everywhere. |
| nox | SAME | nox_alias | Explicit nitrogen oxides (NOx) definition; remains a family, not specifically NO2. |
| nox | SAME | nox2 | Explicit nitrogen oxides (NOx) definition; remains a family, not specifically NO2. |
| nox | SAME | nox7 | Explicit nitrogen oxides (NOx) definition; remains a family, not specifically NO2. |
| no_resp | SAME | no_lod | Repeated NO formula in analyte-specific response/LOD values. |
| no2_resp | SAME | no2_lod | Repeated NO2 formula; not NO. |
| no_resp | DIFFERENT | no2_resp | Explicit separate response and detection-limit entries for NO and NO2. |
| nox | BROADER | no_resp | NO is one of the named targets of this NOx device; the family is not collapsed into one target. |
| nox | BROADER | no2_resp | NO2 is one of the named targets of this NOx device; the family is not collapsed into one target. |
| stretch1 | SAME | stretch2 | Same stretchability property concept; the background and study devices remain distinct. |
| stretch1 | SAME | stretch7 | Same stretchability property concept; the background and study devices remain distinct. |
| moist | SAME | encap_moist | Same moisture-resistance property; device versus encapsulant bearer and RH qualifier remain separate. |
| moist | SAME | moist6 | Same moisture-resistance property; device versus encapsulant bearer and RH qualifier remain separate. |
| moist | SAME | moist7 | Same moisture-resistance property; device versus encapsulant bearer and RH qualifier remain separate. |
| laser | SAME | laser4 | Same laser-processing concept; tuning parameters are not merged into the process. |

## Unresolved

# Вопросы документа

Все открытые вопросы UNRESOLVED. Они не блокировали автоматический проход. Q1/Q2/Q3 решены пользователем и находятся в adjudication_decisions.jsonl.
