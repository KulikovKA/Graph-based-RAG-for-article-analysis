# D003 — Moisture-resistant, stretchable NOx gas sensors based on laser-induced graphene for environmental monitoring and breath analysis

**AI draft; human review NOT_REVIEWED. Не gold.**

Document `06066c66-1454-4813-b7b7-f366b9956035`; revision `7af46631-a38f-430d-a43c-bcfa0dccac9e`; split `DEV`.

Область: все доступные frozen abstract chunks. Полный текст статьи не заявляется доступным.

Chunks: 2; sentences: 7; mentions: 69; assertions: 45; concepts: 51; identity decisions: 22.

Структурная проверка: PASS. Семантическая проверка выполнена AI; независимой человеческой проверки не было.

Рубрика `pilot24-dev-rubric-0.2-WORKING`. Q1 решён для рабочей схемы DEV; human review не предоставлен. Открытые вопросы: Q2.

Полнота AI-прохода: entities=True, relations=False. UNRESOLVED candidates: 1; UNRESOLVED accepted assertions: 0.

Unique canonical triples: 42; qualified groups: 44. Source mentions/assertions не удалялись.

## Полный доступный исходный текст

### Chunk 0: `0ad16539-951a-4c6a-95df-0d92179b23eb`

Section `abstract`, section offsets [0, 1017); SHA-256 `93b3b8cd46f210f24559ada46e4094b348260a9b1c0be1b96965d77ac32e55ae`.

Abstract The accurate, continuous analysis of healthcare-relevant gases such as nitrogen oxides (NO x ) in a humid environment remains elusive for low-cost, stretchable gas sensing devices. This study presents the design and demonstration of a moisture-resistant, stretchable NO x gas sensor based on laser-induced graphene (LIG). Sandwiched between a soft elastomeric substrate and a moisture-resistant semipermeable encapsulant, the LIG sensing and electrode layer is first optimized by tuning laser processing parameters such as power, image density, and defocus distance. The gas sensor, using a needlelike LIG prepared with optimal laser processing parameters, exhibits a large response of 4.18‰ ppm −1 to NO and 6.66‰ ppm −1 to NO 2 , an ultralow detection limit of 8.3 ppb to NO and 4.0 ppb to NO 2 , fast response/recovery, and excellent selectivity. The design of a stretchable serpentine structure in the LIG electrode and strain isolation from the stiff island allows the gas sensor to be stretched by 30%.

### Chunk 1: `45f36916-7688-4edb-8dd1-2ac50ea13339`

Section `abstract`, section offsets [1018, 1516); SHA-256 `93b20b0f39df3ee410854241c279ea62bb58bb7097cf578d2413e403427c1a88`.

Combined with a moisture-resistant property against a relative humidity of 90%, the reported gas sensor has further been demonstrated to monitor the personal local environment during different times of the day and analyze human breath samples to classify patients with respiratory diseases from healthy volunteers. Moisture-resistant, stretchable NO x gas sensors can expand the capability of wearable devices to detect biomarkers from humans and exposed environments for early disease diagnostics.

## Проверка предложений

### S1: [0, 189)

Abstract The accurate, continuous analysis of healthcare-relevant gases such as nitrogen oxides (NO x ) in a humid environment remains elusive for low-cost, stretchable gas sensing devices.

Remains elusive describes an unmet background goal, not an explicit universally negative DETECTS claim. No achieved accuracy/continuous-analysis performance is assigned to these generic devices.

### S2: [190, 330)

This study presents the design and demonstration of a moisture-resistant, stretchable NO x gas sensor based on laser-induced graphene (LIG).

### S3: [331, 575)

Sandwiched between a soft elastomeric substrate and a moisture-resistant semipermeable encapsulant, the LIG sensing and electrode layer is first optimized by tuning laser processing parameters such as power, image density, and defocus distance.

Q2: tuning -> layer optimization is registered as an unresolved predicate candidate, not omitted negative gold. Positional sandwich information is explicit on HAS_COMPONENT(layer), without pretending between means inside either surrounding component.

### S4: [576, 858)

The gas sensor, using a needlelike LIG prepared with optimal laser processing parameters, exhibits a large response of 4.18‰ ppm −1 to NO and 6.66‰ ppm −1 to NO 2 , an ultralow detection limit of 8.3 ppb to NO and 4.0 ppb to NO 2 , fast response/recovery, and excellent selectivity.

### S5: [859, 1017)

The design of a stretchable serpentine structure in the LIG electrode and strain isolation from the stiff island allows the gas sensor to be stretched by 30%.

The 30% stretching capability is explained jointly by serpentine design and strain isolation. HAS_MECHANISM includes the explicit explained_capability qualifier; no claim that each mechanism alone achieves 30%.

### S6: [0, 314)

Combined with a moisture-resistant property against a relative humidity of 90%, the reported gas sensor has further been demonstrated to monitor the personal local environment during different times of the day and analyze human breath samples to classify patients with respiratory diseases from healthy volunteers.

### S7: [315, 498)

Moisture-resistant, stretchable NO x gas sensors can expand the capability of wearable devices to detect biomarkers from humans and exposed environments for early disease diagnostics.

## Все упоминания

| Key | Sentence | Span | Exact surface | Kind / role | Canonical concept |
| --- | --- | --- | --- | --- | --- |
| analysis | S1 | [13, 42) | accurate, continuous analysis | PROCESS / background_unmet_goal | accurate continuous gas analysis |
| gases | S1 | [46, 71) | healthcare-relevant gases | ANALYTE / background_analyte_class | healthcare-relevant gases |
| nox | S1 | [80, 95) | nitrogen oxides | ANALYTE / target_analyte_class | nitrogen oxides |
| nox_alias | S1 | [97, 101) | NO x | ANALYTE / target_analyte_class | nitrogen oxides |
| humid | S1 | [109, 126) | humid environment | OPERATING_CONDITION / technical_operating_condition | humid environment |
| cost | S1 | [147, 155) | low-cost | PROPERTY / technical_property | low cost |
| stretch1 | S1 | [157, 168) | stretchable | PROPERTY / technical_property | stretchability |
| devices | S1 | [169, 188) | gas sensing devices | DEVICE / technical_device | background low-cost stretchable gas sensors |
| sensor | S2 | [244, 291) | moisture-resistant, stretchable NO x gas sensor | DEVICE / technical_device | study stretchable LIG NOx sensor |
| moist | S2 | [244, 262) | moisture-resistant | PROPERTY / technical_property | moisture resistance |
| stretch2 | S2 | [264, 275) | stretchable | PROPERTY / technical_property | stretchability |
| nox2 | S2 | [276, 280) | NO x | ANALYTE / target_analyte_class | nitrogen oxides |
| lig | S2 | [301, 323) | laser-induced graphene | MATERIAL / technical_material | laser-induced graphene |
| lig_alias | S2 | [325, 328) | LIG | MATERIAL / technical_material | laser-induced graphene |
| substrate | S3 | [352, 378) | soft elastomeric substrate | DEVICE / support_component | elastomeric substrate |
| soft | S3 | [352, 356) | soft | PROPERTY / technical_property | softness |
| elastomer | S3 | [357, 368) | elastomeric | MATERIAL / substrate_material_class | elastomer (unspecified) |
| encap | S3 | [385, 429) | moisture-resistant semipermeable encapsulant | DEVICE / encapsulation_component | semipermeable encapsulant |
| encap_moist | S3 | [385, 403) | moisture-resistant | PROPERTY / technical_property | moisture resistance |
| semi | S3 | [404, 417) | semipermeable | PROPERTY / technical_property | semipermeability |
| layer | S3 | [435, 466) | LIG sensing and electrode layer | DEVICE / dual_function_layer | LIG sensing/electrode layer |
| lig3 | S3 | [435, 438) | LIG | MATERIAL / technical_material | laser-induced graphene |
| tuning | S3 | [489, 523) | tuning laser processing parameters | PROCESS / technical_process | laser parameter tuning |
| laser | S3 | [496, 512) | laser processing | PROCESS / technical_process | laser processing |
| parameters | S3 | [496, 523) | laser processing parameters | PROPERTY / technical_property | laser processing parameter group |
| power | S3 | [532, 537) | power | PROPERTY / fabrication_parameter | laser power |
| density | S3 | [539, 552) | image density | PROPERTY / fabrication_parameter | laser image density |
| defocus | S3 | [558, 574) | defocus distance | PROPERTY / fabrication_parameter | laser defocus distance |
| sensor4 | S4 | [580, 590) | gas sensor | DEVICE / technical_device | study stretchable LIG NOx sensor |
| lig4 | S4 | [600, 614) | needlelike LIG | MATERIAL / technical_material | needlelike laser-induced graphene |
| needle | S4 | [600, 610) | needlelike | MORPHOLOGY / technical_morphology | needlelike morphology |
| laser4 | S4 | [637, 653) | laser processing | PROCESS / technical_process | laser processing |
| settings | S4 | [629, 664) | optimal laser processing parameters | PROPERTY / technical_property | optimal laser processing parameters |
| response | S4 | [677, 691) | large response | PERFORMANCE / technical_performance | gas response per concentration |
| no_resp | S4 | [711, 713) | NO | ANALYTE / target_analyte | nitric oxide |
| no2_resp | S4 | [734, 738) | NO 2 | ANALYTE / target_analyte | nitrogen dioxide |
| lod | S4 | [744, 768) | ultralow detection limit | PERFORMANCE / technical_performance | detection limit |
| no_lod | S4 | [783, 785) | NO | ANALYTE / target_analyte | nitric oxide |
| no2_lod | S4 | [801, 805) | NO 2 | ANALYTE / target_analyte | nitrogen dioxide |
| speed | S4 | [808, 830) | fast response/recovery | PERFORMANCE / technical_performance | response/recovery speed |
| selectivity | S4 | [836, 857) | excellent selectivity | PERFORMANCE / technical_performance | selectivity |
| design | S5 | [863, 907) | design of a stretchable serpentine structure | PROCESS / technical_process | serpentine structure design |
| mechanism5 | S5 | [863, 971) | design of a stretchable serpentine structure in the LIG electrode and strain isolation from the stiff island | MECHANISM / technical_mechanism | combined serpentine design and strain isolation |
| serpentine | S5 | [875, 907) | stretchable serpentine structure | MORPHOLOGY / technical_morphology | stretchable serpentine structure |
| electrode | S5 | [915, 928) | LIG electrode | DEVICE / technical_device | LIG electrode |
| lig5 | S5 | [915, 918) | LIG | MATERIAL / technical_material | laser-induced graphene |
| isolation | S5 | [933, 949) | strain isolation | MECHANISM / technical_mechanism | strain isolation |
| island | S5 | [959, 971) | stiff island | DEVICE / mechanical_isolation_component | stiff island |
| stiff | S5 | [959, 964) | stiff | PROPERTY / technical_property | stiffness |
| sensor5 | S5 | [983, 993) | gas sensor | DEVICE / technical_device | study stretchable LIG NOx sensor |
| stretch5 | S5 | [1000, 1016) | stretched by 30% | PERFORMANCE / technical_performance | demonstrated stretching capability |
| moist6 | S6 | [16, 43) | moisture-resistant property | PROPERTY / technical_property | moisture resistance |
| rh | S6 | [54, 78) | relative humidity of 90% | OPERATING_CONDITION / technical_operating_condition | relative humidity 90% |
| sensor6 | S6 | [93, 103) | gas sensor | DEVICE / technical_device | study stretchable LIG NOx sensor |
| monitor | S6 | [137, 175) | monitor the personal local environment | APPLICATION / technical_application | personal local environmental monitoring |
| time | S6 | [183, 209) | different times of the day | OPERATING_CONDITION / technical_operating_condition | different times of day |
| breath | S6 | [214, 242) | analyze human breath samples | APPLICATION / technical_application | human breath analysis |
| samples | S6 | [222, 242) | human breath samples | ANALYTE / sample_matrix | human breath samples |
| classify | S6 | [246, 313) | classify patients with respiratory diseases from healthy volunteers | APPLICATION / technical_application | classification of respiratory-disease patients versus healthy volunteers |
| disease | S6 | [269, 289) | respiratory diseases | OTHER / clinical_target | respiratory diseases |
| healthy | S6 | [295, 313) | healthy volunteers | OTHER / comparison_population | healthy volunteers |
| sensor7 | S7 | [315, 363) | Moisture-resistant, stretchable NO x gas sensors | DEVICE / technical_device | study stretchable LIG NOx sensor |
| moist7 | S7 | [315, 333) | Moisture-resistant | PROPERTY / technical_property | moisture resistance |
| stretch7 | S7 | [335, 346) | stretchable | PROPERTY / technical_property | stretchability |
| nox7 | S7 | [347, 351) | NO x | ANALYTE / target_analyte_class | nitrogen oxides |
| wearables | S7 | [393, 409) | wearable devices | DEVICE / prospective_device_class | wearable devices |
| biomarkers | S7 | [420, 430) | biomarkers | ANALYTE / prospective_target_class | biomarkers (unspecified) |
| environments | S7 | [447, 467) | exposed environments | OTHER / prospective_sampling_context | exposed environments |
| diagnostics | S7 | [472, 497) | early disease diagnostics | APPLICATION / technical_application | early disease diagnostics |

## Все утверждения

Направление каждой строки: head → tail. Полные UUID и evidence находятся в JSONL.

| # | Head | Relation | Tail | Modality / scope | Qualifiers | Evidence sentences | Semantic note |
| --- | --- | --- | --- | --- | --- | --- | --- |
| 1 | devices | HAS_PROPERTY | cost | ASSERTED / BACKGROUND |  | S1 |  |
| 2 | devices | HAS_PROPERTY | stretch1 | ASSERTED / BACKGROUND |  | S1 |  |
| 3 | sensor | HAS_PROPERTY | moist | ASSERTED / STUDY_RESULT |  | S2 |  |
| 4 | sensor | HAS_PROPERTY | stretch2 | ASSERTED / STUDY_RESULT |  | S2 |  |
| 5 | sensor | USES_MATERIAL | lig | ASSERTED / STUDY_RESULT |  | S2 |  |
| 6 | sensor | DETECTS | nox2 | ASSERTED / STUDY_RESULT |  | S2 |  |
| 7 | substrate | HAS_PROPERTY | soft | ASSERTED / STUDY_RESULT |  | S3 |  |
| 8 | substrate | USES_MATERIAL | elastomer | ASSERTED / STUDY_RESULT |  | S3 |  |
| 9 | encap | HAS_PROPERTY | encap_moist | ASSERTED / STUDY_RESULT |  | S3 |  |
| 10 | encap | HAS_PROPERTY | semi | ASSERTED / STUDY_RESULT |  | S3 |  |
| 11 | layer | USES_MATERIAL | lig3 | ASSERTED / STUDY_RESULT |  | S3 |  |
| 12 | sensor | HAS_COMPONENT | substrate | ASSERTED / STUDY_RESULT |  | S2, S3 |  |
| 13 | sensor | HAS_COMPONENT | encap | ASSERTED / STUDY_RESULT |  | S2, S3 |  |
| 14 | sensor | HAS_COMPONENT | layer | ASSERTED / STUDY_RESULT | layer_position: Sandwiched between a soft elastomeric substrate and a moisture-resistant semipermeable encapsulant | S2, S3 |  |
| 15 | parameters | HAS_MEMBER | power | ASSERTED / STUDY_RESULT |  | S3 |  |
| 16 | laser | HAS_PROPERTY | power | ASSERTED / STUDY_RESULT |  | S3 |  |
| 17 | parameters | HAS_MEMBER | density | ASSERTED / STUDY_RESULT |  | S3 |  |
| 18 | laser | HAS_PROPERTY | density | ASSERTED / STUDY_RESULT |  | S3 |  |
| 19 | parameters | HAS_MEMBER | defocus | ASSERTED / STUDY_RESULT |  | S3 |  |
| 20 | laser | HAS_PROPERTY | defocus | ASSERTED / STUDY_RESULT |  | S3 |  |
| 21 | sensor4 | USES_MATERIAL | lig4 | ASSERTED / STUDY_RESULT |  | S4 |  |
| 22 | lig4 | HAS_MORPHOLOGY | needle | ASSERTED / STUDY_RESULT |  | S4 |  |
| 23 | lig4 | FABRICATED_BY | laser4 | ASSERTED / STUDY_RESULT | parameter_selection: optimal laser processing parameters | S4 |  |
| 24 | sensor4 | DETECTS | no_resp | ASSERTED / STUDY_RESULT | response_per_concentration: 4.18‰ ppm −1 to NO | S4 |  |
| 25 | sensor4 | DETECTS | no2_resp | ASSERTED / STUDY_RESULT | response_per_concentration: 6.66‰ ppm −1 to NO 2 | S4 |  |
| 26 | sensor4 | HAS_PERFORMANCE | response | ASSERTED / STUDY_RESULT | NO_response_per_concentration: 4.18‰ ppm −1 to NO; NO2_response_per_concentration: 6.66‰ ppm −1 to NO 2 | S4 |  |
| 27 | sensor4 | HAS_PERFORMANCE | lod | ASSERTED / STUDY_RESULT | NO_detection_limit: 8.3 ppb to NO; NO2_detection_limit: 4.0 ppb to NO 2 | S4 |  |
| 28 | sensor4 | HAS_PERFORMANCE | speed | ASSERTED / STUDY_RESULT |  | S4 |  |
| 29 | sensor4 | HAS_PERFORMANCE | selectivity | ASSERTED / STUDY_RESULT |  | S4 | No numerical response/recovery time or named comparison analyte is given. |
| 30 | electrode | USES_MATERIAL | lig5 | ASSERTED / STUDY_RESULT |  | S5 |  |
| 31 | electrode | HAS_MORPHOLOGY | serpentine | ASSERTED / STUDY_RESULT |  | S5 |  |
| 32 | island | HAS_PROPERTY | stiff | ASSERTED / STUDY_RESULT |  | S5 |  |
| 33 | sensor5 | HAS_PERFORMANCE | stretch5 | ASSERTED / STUDY_RESULT | stretch: 30% | S5 |  |
| 34 | sensor5 | HAS_MECHANISM | mechanism5 | ASSERTED / STUDY_RESULT | explained_capability: stretched by 30% | S5 | Mechanical explanation for stretchability, not a proposed gas-response mechanism; design and isolation are collective. |
| 35 | mechanism5 | MECHANISM_INVOLVES | design | ASSERTED / STUDY_RESULT |  | S5 |  |
| 36 | mechanism5 | MECHANISM_INVOLVES | serpentine | ASSERTED / STUDY_RESULT |  | S5 |  |
| 37 | mechanism5 | MECHANISM_INVOLVES | isolation | ASSERTED / STUDY_RESULT | isolation_reference: from the stiff island | S5 |  |
| 38 | sensor6 | HAS_PROPERTY | moist6 | ASSERTED / STUDY_RESULT | relative_humidity: relative humidity of 90% | S6 |  |
| 39 | sensor6 | USED_FOR | monitor | ASSERTED / STUDY_RESULT | monitoring_times: different times of the day | S6 |  |
| 40 | sensor6 | USED_FOR | breath | ASSERTED / STUDY_RESULT |  | S6 |  |
| 41 | sensor6 | USED_FOR | classify | ASSERTED / STUDY_RESULT |  | S6 | Reported demonstration, not clinical diagnostic accuracy. No diagnostic sensitivity/specificity is supplied. |
| 42 | sensor7 | HAS_PROPERTY | moist7 | ASSERTED / STUDY_RESULT |  | S7 |  |
| 43 | sensor7 | HAS_PROPERTY | stretch7 | ASSERTED / STUDY_RESULT |  | S7 |  |
| 44 | sensor7 | USED_FOR | diagnostics | HYPOTHETICAL / OUTLOOK |  | S7 |  |
| 45 | wearables | DETECTS | biomarkers | HYPOTHETICAL / OUTLOOK |  | S7 | Prospective capability, not demonstrated detection of every biomarker or confirmed diagnosis. |

## Все identity decisions

| Left | Label | Right | Основание |
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

## Нерешённые кандидаты

**Q2: Source explicitly optimizes a device layer by tuning. IMPROVES only permits PROPERTY/PERFORMANCE tails, and no optimized metric is named.**

Sandwiched between a soft elastomeric substrate and a moisture-resistant semipermeable encapsulant, the LIG sensing and electrode layer is first optimized by tuning laser processing parameters such as power, image density, and defocus distance.

Варианты и перевод: `questions_Q2_Q3.md`. Кандидат не превращён в accepted assertion.

