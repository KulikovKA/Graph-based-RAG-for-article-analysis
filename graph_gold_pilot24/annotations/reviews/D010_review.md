# D010 — Room-Temperature Ammonia Gas Sensor Based on Ti3C2Tx MXene/Graphene Oxide/CuO/ZnO Nanocomposite

**AI draft — HUMAN_REVIEW=NOT_REVIEWED; не human gold.**

Document `136d5083-0254-4930-a35e-88441bb802a0`, revision `fbd87a44-35d0-4f51-80d6-39abd117d01f`, split `DEV`, rubric `pilot24-rubric-0.3-AUTO-FROZEN`.

Chunks 2; sentences 7; mentions 105; assertions 99; unique canonical triples 77; questions 0; validation PASS.

Полный AI-проход завершён. exhaustive_entities=True; exhaustive_relations=True; неразрешённые кандидаты не являются negative gold.

## Исходные frozen EvidenceChunks

### `510e3540-e579-4536-a4ea-dae9b47eb024`

SHA-256 `64d799ca2abc5b0e0227acb9ed7866ea179d19a4e47cc2aaaebd797fdd0de985`, section `abstract`; [0, 901).

Two-dimensional (2D) Ti 3 C 2 Tx Mxene has currently demonstrated significant potential for gas sensing application with a high signal-to-noise ratio at room temperature. Herein, we present the mixture of popular NH 3 sensing materials such as graphene oxide (GO), copper oxide (CuO), and zinc oxide (ZnO) into Ti 3 C 2 Tx Mxene to be a high-performance NH 3 gas sensor at room temperature. Various nanocomposites such as Mxene/GO, Mxene/ZnO, Mxene/CuO, Mxene/GO/ZnO, Mxene/GO/CuO, Mxene/ZnO/CuO, and Mxene/GO/ZnO/CuO were synthesized via the hydrothermal method and used as NH 3 sensing materials in room-temperature gas sensors. The Ti 3 C 2 Tx MXene/GO/CuO/ZnO nanocomposite gas sensor exhibited the best NH 3 gas sensor. The effects on the weight ratios of Ti 3 C 2 Tx MXene/GO/CuO/ZnO were also investigated, and the optimal Ti 3 C 2 Tx MXene/GO/CuO/ZnO weight ratio was determined to be 9:1:5:5.

### `761f757f-5005-4417-bf90-f2c5200f7600`

SHA-256 `c96d836b51f3c30b23d69406198bde211107fed455cd9631385c370269084ab3`, section `abstract`; [902, 1490).

The optimal Ti 3 C 2 Tx MXene/GO/CuO/ZnO based gas sensor showed a high response of 96% at 200 ppm of NH 3, humidity independence in the range of 30–70%RH, good linear relationship ( R 2 = 0.998), low limit of detection of 4.1 ppm, and high selectivity to NH 3 over several gases/VOCs including formaldehyde, ethanol, methanol, isopropanol, toluene, and acetone. The NH 3 -sensing mechanism was proposed based on the modulation of complex p–n heterojunctions via the electron accumulation layer in the n-type of GO/CuO/ZnO and the electron depletion layer in the p-type Ti 3 C 2 Tx Mxene.

## Semantic self-audit

All source sentences reviewed in curated first pass.
Q1/Q2/Q3 schema decisions applied; repeated triples counted separately from source assertions.
D001 room-temperature scope and D010 best/proposed mechanism audited in Q1_FOLLOWUP_AUDIT.md.

## Mentions

| Key | Sentence | Span | Surface | Kind / role | Canonical |
| --- | --- | --- | --- | --- | --- |
| mxene | S1 | [21,38) | Ti 3 C 2 Tx Mxene | MATERIAL / technical_material | Ti3C2Tx MXene |
| dim | S1 | [0,20) | Two-dimensional (2D) | MORPHOLOGY / technical_morphology | two-dimensional morphology |
| application | S1 | [92,115) | gas sensing application | APPLICATION / technical_application | gas sensing |
| snr | S1 | [123,149) | high signal-to-noise ratio | PERFORMANCE / technical_performance | signal-to-noise ratio |
| temp | S1 | [153,169) | room temperature | OPERATING_CONDITION / technical_operating_condition | room temperature |
| mixture | S2 | [194,201) | mixture | MATERIAL / technical_material | Ti3C2Tx MXene/GO/CuO/ZnO nanocomposite |
| nh3_material | S2 | [213,217) | NH 3 | ANALYTE / target_analyte | ammonia |
| go | S2 | [244,258) | graphene oxide | MATERIAL / technical_material | graphene oxide |
| go_alias | S2 | [260,262) | GO | MATERIAL / technical_material | graphene oxide |
| cuo | S2 | [265,277) | copper oxide | MATERIAL / technical_material | copper oxide (CuO) |
| cuo_alias | S2 | [279,282) | CuO | MATERIAL / technical_material | copper oxide (CuO) |
| zno | S2 | [289,299) | zinc oxide | MATERIAL / technical_material | zinc oxide |
| zno_alias | S2 | [301,304) | ZnO | MATERIAL / technical_material | zinc oxide |
| mxene2 | S2 | [311,328) | Ti 3 C 2 Tx Mxene | MATERIAL / technical_material | Ti3C2Tx MXene |
| sensor | S2 | [354,369) | NH 3 gas sensor | DEVICE / technical_device | study four-component nanocomposite gas sensor |
| nh3_2 | S2 | [354,358) | NH 3 | ANALYTE / target_analyte | ammonia |
| high | S2 | [337,353) | high-performance | PERFORMANCE / technical_performance | high sensing performance |
| temp2 | S2 | [373,389) | room temperature | OPERATING_CONDITION / technical_operating_condition | room temperature |
| composites | S3 | [399,413) | nanocomposites | MATERIAL / technical_material | investigated nanocomposite collection |
| mg | S3 | [422,430) | Mxene/GO | MATERIAL / sensing_material | MXene/GO |
| mz | S3 | [432,441) | Mxene/ZnO | MATERIAL / sensing_material | MXene/ZnO |
| mc | S3 | [443,452) | Mxene/CuO | MATERIAL / technical_material | MXene/CuO |
| mgz | S3 | [454,466) | Mxene/GO/ZnO | MATERIAL / sensing_material | MXene/GO/ZnO |
| mgc | S3 | [468,480) | Mxene/GO/CuO | MATERIAL / technical_material | MXene/GO/CuO |
| mzc | S3 | [482,495) | Mxene/ZnO/CuO | MATERIAL / technical_material | MXene/ZnO/CuO |
| mgzc | S3 | [501,517) | Mxene/GO/ZnO/CuO | MATERIAL / technical_material | Ti3C2Tx MXene/GO/CuO/ZnO nanocomposite |
| hydro | S3 | [543,562) | hydrothermal method | PROCESS / technical_process | hydrothermal synthesis |
| nh3_3 | S3 | [575,579) | NH 3 | ANALYTE / target_analyte | ammonia |
| materials3 | S3 | [580,597) | sensing materials | MATERIAL / technical_material | investigated nanocomposite collection |
| temp3 | S3 | [601,617) | room-temperature | OPERATING_CONDITION / technical_operating_condition | room temperature |
| sensors3 | S3 | [618,629) | gas sensors | DEVICE / technical_device | investigated room-temperature gas sensors |
| sensor4 | S4 | [635,688) | Ti 3 C 2 Tx MXene/GO/CuO/ZnO nanocomposite gas sensor | DEVICE / technical_device | study four-component nanocomposite gas sensor |
| material4 | S4 | [635,663) | Ti 3 C 2 Tx MXene/GO/CuO/ZnO | MATERIAL / technical_material | Ti3C2Tx MXene/GO/CuO/ZnO nanocomposite |
| best | S4 | [703,707) | best | PERFORMANCE / technical_performance | best NH3 sensor (unspecified comparison metric) |
| nh3_4 | S4 | [708,712) | NH 3 | ANALYTE / target_analyte | ammonia |
| ratios | S5 | [744,757) | weight ratios | PROPERTY / technical_property | component weight ratio |
| mat5a | S5 | [761,789) | Ti 3 C 2 Tx MXene/GO/CuO/ZnO | MATERIAL / sensing_material | Ti3C2Tx MXene/GO/CuO/ZnO nanocomposite |
| mat5b | S5 | [830,858) | Ti 3 C 2 Tx MXene/GO/CuO/ZnO | MATERIAL / sensing_material | Ti3C2Tx MXene/GO/CuO/ZnO nanocomposite |
| ratio | S5 | [859,871) | weight ratio | PROPERTY / composition_ratio | component weight ratio |
| sensor6 | S6 | [4,57) | optimal Ti 3 C 2 Tx MXene/GO/CuO/ZnO based gas sensor | DEVICE / technical_device | optimal four-component nanocomposite gas sensor |
| mat6 | S6 | [12,40) | Ti 3 C 2 Tx MXene/GO/CuO/ZnO | MATERIAL / technical_material | Ti3C2Tx MXene/GO/CuO/ZnO nanocomposite |
| resp | S6 | [67,80) | high response | PERFORMANCE / technical_performance | sensor response |
| nh3_6a | S6 | [102,106) | NH 3 | ANALYTE / target_analyte | ammonia |
| humidity | S6 | [108,129) | humidity independence | PERFORMANCE / technical_performance | humidity independence |
| rh | S6 | [146,154) | 30–70%RH | OPERATING_CONDITION / technical_operating_condition | relative humidity range 30–70%RH |
| linear | S6 | [156,180) | good linear relationship | PERFORMANCE / technical_performance | linear calibration relationship (variables unspecified) |
| r2 | S6 | [183,186) | R 2 | PERFORMANCE / technical_performance | coefficient of determination |
| lod | S6 | [197,219) | low limit of detection | PERFORMANCE / technical_performance | detection limit |
| sel | S6 | [236,252) | high selectivity | PERFORMANCE / technical_performance | NH3 selectivity |
| nh3_6b | S6 | [256,260) | NH 3 | ANALYTE / target_analyte | ammonia |
| gases | S6 | [274,284) | gases/VOCs | ANALYTE / comparison_analyte_group | comparison gases/VOCs |
| form | S6 | [295,307) | formaldehyde | ANALYTE / comparison_analyte | formaldehyde |
| eth | S6 | [309,316) | ethanol | ANALYTE / comparison_analyte | ethanol |
| meth | S6 | [318,326) | methanol | ANALYTE / comparison_analyte | methanol |
| iso | S6 | [328,339) | isopropanol | ANALYTE / comparison_analyte | isopropanol |
| tol | S6 | [341,348) | toluene | ANALYTE / comparison_analyte | toluene |
| ace | S6 | [354,361) | acetone | ANALYTE / comparison_analyte | acetone |
| nh3_7 | S7 | [367,371) | NH 3 | ANALYTE / target_analyte | ammonia |
| mechanism | S7 | [367,390) | NH 3 -sensing mechanism | MECHANISM / technical_mechanism | proposed NH3 sensing mechanism |
| modulation | S7 | [417,458) | modulation of complex p–n heterojunctions | MECHANISM / technical_mechanism | p–n heterojunction modulation |
| junction | S7 | [431,458) | complex p–n heterojunctions | MORPHOLOGY / electronic_interface | complex p–n heterojunction structure |
| acc | S7 | [467,494) | electron accumulation layer | MORPHOLOGY / electronic_charge_region | electron accumulation layer |
| ntype | S7 | [502,508) | n-type | PROPERTY / technical_property | n-type conductivity |
| gcz | S7 | [512,522) | GO/CuO/ZnO | MATERIAL / technical_material | GO/CuO/ZnO subcomposite |
| dep | S7 | [531,555) | electron depletion layer | MORPHOLOGY / electronic_charge_region | electron depletion layer |
| ptype | S7 | [563,569) | p-type | PROPERTY / technical_property | p-type conductivity |
| mxene7 | S7 | [570,587) | Ti 3 C 2 Tx Mxene | MATERIAL / technical_material | Ti3C2Tx MXene |
| mg_mxene | S3 | [422,427) | Mxene | MATERIAL / named_composite_constituent | Ti3C2Tx MXene |
| mg_go | S3 | [428,430) | GO | MATERIAL / named_composite_constituent | graphene oxide |
| mz_mxene | S3 | [432,437) | Mxene | MATERIAL / named_composite_constituent | Ti3C2Tx MXene |
| mz_zno | S3 | [438,441) | ZnO | MATERIAL / named_composite_constituent | zinc oxide |
| mc_mxene | S3 | [443,448) | Mxene | MATERIAL / named_composite_constituent | Ti3C2Tx MXene |
| mc_cuo | S3 | [449,452) | CuO | MATERIAL / named_composite_constituent | copper oxide (CuO) |
| mgz_mxene | S3 | [454,459) | Mxene | MATERIAL / named_composite_constituent | Ti3C2Tx MXene |
| mgz_go | S3 | [460,462) | GO | MATERIAL / named_composite_constituent | graphene oxide |
| mgz_zno | S3 | [463,466) | ZnO | MATERIAL / named_composite_constituent | zinc oxide |
| mgc_mxene | S3 | [468,473) | Mxene | MATERIAL / named_composite_constituent | Ti3C2Tx MXene |
| mgc_go | S3 | [474,476) | GO | MATERIAL / named_composite_constituent | graphene oxide |
| mgc_cuo | S3 | [477,480) | CuO | MATERIAL / named_composite_constituent | copper oxide (CuO) |
| mzc_mxene | S3 | [482,487) | Mxene | MATERIAL / named_composite_constituent | Ti3C2Tx MXene |
| mzc_cuo | S3 | [492,495) | CuO | MATERIAL / named_composite_constituent | copper oxide (CuO) |
| mzc_zno | S3 | [488,491) | ZnO | MATERIAL / named_composite_constituent | zinc oxide |
| mgzc_mxene | S3 | [501,506) | Mxene | MATERIAL / named_composite_constituent | Ti3C2Tx MXene |
| mgzc_go | S3 | [507,509) | GO | MATERIAL / named_composite_constituent | graphene oxide |
| mgzc_cuo | S3 | [514,517) | CuO | MATERIAL / named_composite_constituent | copper oxide (CuO) |
| mgzc_zno | S3 | [510,513) | ZnO | MATERIAL / named_composite_constituent | zinc oxide |
| material4_mxene | S4 | [635,652) | Ti 3 C 2 Tx MXene | MATERIAL / named_composite_constituent | Ti3C2Tx MXene |
| material4_go | S4 | [653,655) | GO | MATERIAL / named_composite_constituent | graphene oxide |
| material4_cuo | S4 | [656,659) | CuO | MATERIAL / named_composite_constituent | copper oxide (CuO) |
| material4_zno | S4 | [660,663) | ZnO | MATERIAL / named_composite_constituent | zinc oxide |
| mat5a_mxene | S5 | [761,778) | Ti 3 C 2 Tx MXene | MATERIAL / named_composite_constituent | Ti3C2Tx MXene |
| mat5a_go | S5 | [779,781) | GO | MATERIAL / named_composite_constituent | graphene oxide |
| mat5a_cuo | S5 | [782,785) | CuO | MATERIAL / named_composite_constituent | copper oxide (CuO) |
| mat5a_zno | S5 | [786,789) | ZnO | MATERIAL / named_composite_constituent | zinc oxide |
| mat5b_mxene | S5 | [830,847) | Ti 3 C 2 Tx MXene | MATERIAL / named_composite_constituent | Ti3C2Tx MXene |
| mat5b_go | S5 | [848,850) | GO | MATERIAL / named_composite_constituent | graphene oxide |
| mat5b_cuo | S5 | [851,854) | CuO | MATERIAL / named_composite_constituent | copper oxide (CuO) |
| mat5b_zno | S5 | [855,858) | ZnO | MATERIAL / named_composite_constituent | zinc oxide |
| mat6_mxene | S6 | [12,29) | Ti 3 C 2 Tx MXene | MATERIAL / named_composite_constituent | Ti3C2Tx MXene |
| mat6_go | S6 | [30,32) | GO | MATERIAL / named_composite_constituent | graphene oxide |
| mat6_cuo | S6 | [33,36) | CuO | MATERIAL / named_composite_constituent | copper oxide (CuO) |
| mat6_zno | S6 | [37,40) | ZnO | MATERIAL / named_composite_constituent | zinc oxide |
| gcz_go | S7 | [512,514) | GO | MATERIAL / named_composite_constituent | graphene oxide |
| gcz_cuo | S7 | [515,518) | CuO | MATERIAL / named_composite_constituent | copper oxide (CuO) |
| gcz_zno | S7 | [519,522) | ZnO | MATERIAL / named_composite_constituent | zinc oxide |

## Assertions

| Head | Relation | Tail | Polarity | Modality / scope | Qualifiers | Evidence span IDs |
| --- | --- | --- | --- | --- | --- | --- |
| mxene | HAS_MORPHOLOGY | dim | POSITIVE | ASSERTED / BACKGROUND |  | d3840135-fa0a-5abf-8e9e-6fd0018f0c20 |
| mxene | USED_FOR | application | POSITIVE | ASSERTED / BACKGROUND |  | d3840135-fa0a-5abf-8e9e-6fd0018f0c20 |
| mxene | HAS_PERFORMANCE | snr | POSITIVE | ASSERTED / BACKGROUND | temperature: room temperature → room temperature | d3840135-fa0a-5abf-8e9e-6fd0018f0c20 |
| mixture | HAS_COMPONENT | go | POSITIVE | ASSERTED / STUDY_RESULT |  | 0a235b9d-ec9c-51b5-9ab7-1cb832c56445 |
| mixture | HAS_COMPONENT | cuo | POSITIVE | ASSERTED / STUDY_RESULT |  | 0a235b9d-ec9c-51b5-9ab7-1cb832c56445 |
| mixture | HAS_COMPONENT | zno | POSITIVE | ASSERTED / STUDY_RESULT |  | 0a235b9d-ec9c-51b5-9ab7-1cb832c56445 |
| mixture | HAS_COMPONENT | mxene2 | POSITIVE | ASSERTED / STUDY_RESULT |  | 0a235b9d-ec9c-51b5-9ab7-1cb832c56445 |
| sensor | USES_MATERIAL | mixture | POSITIVE | ASSERTED / STUDY_RESULT |  | 0a235b9d-ec9c-51b5-9ab7-1cb832c56445 |
| sensor | DETECTS | nh3_2 | POSITIVE | ASSERTED / STUDY_RESULT | temperature: room temperature → room temperature | 0a235b9d-ec9c-51b5-9ab7-1cb832c56445 |
| sensor | HAS_PERFORMANCE | high | POSITIVE | ASSERTED / STUDY_RESULT |  | 0a235b9d-ec9c-51b5-9ab7-1cb832c56445 |
| go | USED_FOR | nh3_material | POSITIVE | ASSERTED / BACKGROUND |  | 0a235b9d-ec9c-51b5-9ab7-1cb832c56445 |
| cuo | USED_FOR | nh3_material | POSITIVE | ASSERTED / BACKGROUND |  | 0a235b9d-ec9c-51b5-9ab7-1cb832c56445 |
| zno | USED_FOR | nh3_material | POSITIVE | ASSERTED / BACKGROUND |  | 0a235b9d-ec9c-51b5-9ab7-1cb832c56445 |
| composites | HAS_MEMBER | mg | POSITIVE | ASSERTED / STUDY_RESULT |  | 946eefc8-2674-5188-8ac3-0ff8fbdd6faf |
| mg | FABRICATED_BY | hydro | POSITIVE | ASSERTED / STUDY_RESULT |  | 946eefc8-2674-5188-8ac3-0ff8fbdd6faf |
| mg | USED_FOR | nh3_3 | POSITIVE | ASSERTED / STUDY_RESULT | temperature: room-temperature → room temperature | 946eefc8-2674-5188-8ac3-0ff8fbdd6faf |
| composites | HAS_MEMBER | mz | POSITIVE | ASSERTED / STUDY_RESULT |  | 946eefc8-2674-5188-8ac3-0ff8fbdd6faf |
| mz | FABRICATED_BY | hydro | POSITIVE | ASSERTED / STUDY_RESULT |  | 946eefc8-2674-5188-8ac3-0ff8fbdd6faf |
| mz | USED_FOR | nh3_3 | POSITIVE | ASSERTED / STUDY_RESULT | temperature: room-temperature → room temperature | 946eefc8-2674-5188-8ac3-0ff8fbdd6faf |
| composites | HAS_MEMBER | mc | POSITIVE | ASSERTED / STUDY_RESULT |  | 946eefc8-2674-5188-8ac3-0ff8fbdd6faf |
| mc | FABRICATED_BY | hydro | POSITIVE | ASSERTED / STUDY_RESULT |  | 946eefc8-2674-5188-8ac3-0ff8fbdd6faf |
| mc | USED_FOR | nh3_3 | POSITIVE | ASSERTED / STUDY_RESULT | temperature: room-temperature → room temperature | 946eefc8-2674-5188-8ac3-0ff8fbdd6faf |
| composites | HAS_MEMBER | mgz | POSITIVE | ASSERTED / STUDY_RESULT |  | 946eefc8-2674-5188-8ac3-0ff8fbdd6faf |
| mgz | FABRICATED_BY | hydro | POSITIVE | ASSERTED / STUDY_RESULT |  | 946eefc8-2674-5188-8ac3-0ff8fbdd6faf |
| mgz | USED_FOR | nh3_3 | POSITIVE | ASSERTED / STUDY_RESULT | temperature: room-temperature → room temperature | 946eefc8-2674-5188-8ac3-0ff8fbdd6faf |
| composites | HAS_MEMBER | mgc | POSITIVE | ASSERTED / STUDY_RESULT |  | 946eefc8-2674-5188-8ac3-0ff8fbdd6faf |
| mgc | FABRICATED_BY | hydro | POSITIVE | ASSERTED / STUDY_RESULT |  | 946eefc8-2674-5188-8ac3-0ff8fbdd6faf |
| mgc | USED_FOR | nh3_3 | POSITIVE | ASSERTED / STUDY_RESULT | temperature: room-temperature → room temperature | 946eefc8-2674-5188-8ac3-0ff8fbdd6faf |
| composites | HAS_MEMBER | mzc | POSITIVE | ASSERTED / STUDY_RESULT |  | 946eefc8-2674-5188-8ac3-0ff8fbdd6faf |
| mzc | FABRICATED_BY | hydro | POSITIVE | ASSERTED / STUDY_RESULT |  | 946eefc8-2674-5188-8ac3-0ff8fbdd6faf |
| mzc | USED_FOR | nh3_3 | POSITIVE | ASSERTED / STUDY_RESULT | temperature: room-temperature → room temperature | 946eefc8-2674-5188-8ac3-0ff8fbdd6faf |
| composites | HAS_MEMBER | mgzc | POSITIVE | ASSERTED / STUDY_RESULT |  | 946eefc8-2674-5188-8ac3-0ff8fbdd6faf |
| mgzc | FABRICATED_BY | hydro | POSITIVE | ASSERTED / STUDY_RESULT |  | 946eefc8-2674-5188-8ac3-0ff8fbdd6faf |
| mgzc | USED_FOR | nh3_3 | POSITIVE | ASSERTED / STUDY_RESULT | temperature: room-temperature → room temperature | 946eefc8-2674-5188-8ac3-0ff8fbdd6faf |
| sensors3 | USES_MATERIAL | materials3 | POSITIVE | ASSERTED / STUDY_RESULT |  | 946eefc8-2674-5188-8ac3-0ff8fbdd6faf |
| sensor4 | USES_MATERIAL | material4 | POSITIVE | ASSERTED / STUDY_RESULT |  | af3e822d-e3d4-5fc4-b186-3407958a2389 |
| sensor4 | DETECTS | nh3_4 | POSITIVE | ASSERTED / STUDY_RESULT |  | af3e822d-e3d4-5fc4-b186-3407958a2389 |
| sensor4 | HAS_PERFORMANCE | best | POSITIVE | COMPARED / STUDY_RESULT |  | af3e822d-e3d4-5fc4-b186-3407958a2389 |
| mat5b | HAS_PROPERTY | ratio | POSITIVE | ASSERTED / STUDY_RESULT | mass_ratio: 9:1:5:5 → 9:1:5:5; optimization_status: optimal → optimal | 38fd32f8-9fb6-54c3-8a2e-546bd9cb2aef |
| sensor6 | USES_MATERIAL | mat6 | POSITIVE | ASSERTED / STUDY_RESULT |  | 0febf276-9ca4-5ebb-b21a-7d5b14235fed |
| sensor6 | HAS_PERFORMANCE | resp | POSITIVE | ASSERTED / STUDY_RESULT | response: 96% → 96; analyte_concentration: 200 ppm of NH 3 → 200; temperature: room-temperature → room temperature | 946eefc8-2674-5188-8ac3-0ff8fbdd6faf; 0febf276-9ca4-5ebb-b21a-7d5b14235fed |
| sensor6 | DETECTS | nh3_6a | POSITIVE | ASSERTED / STUDY_RESULT | analyte_concentration: 200 ppm of NH 3 → 200; temperature: room-temperature → room temperature | 946eefc8-2674-5188-8ac3-0ff8fbdd6faf; 0febf276-9ca4-5ebb-b21a-7d5b14235fed |
| sensor6 | HAS_PERFORMANCE | humidity | POSITIVE | ASSERTED / STUDY_RESULT | relative_humidity_range: 30–70%RH → [30, 70]; temperature: room-temperature → room temperature | 946eefc8-2674-5188-8ac3-0ff8fbdd6faf; 0febf276-9ca4-5ebb-b21a-7d5b14235fed |
| sensor6 | HAS_PERFORMANCE | linear | POSITIVE | ASSERTED / STUDY_RESULT | coefficient_of_determination: R 2 = 0.998 → 0.998; temperature: room-temperature → room temperature | 946eefc8-2674-5188-8ac3-0ff8fbdd6faf; 0febf276-9ca4-5ebb-b21a-7d5b14235fed |
| sensor6 | HAS_PERFORMANCE | lod | POSITIVE | ASSERTED / STUDY_RESULT | detection_limit: 4.1 ppm → 4.1; temperature: room-temperature → room temperature | 946eefc8-2674-5188-8ac3-0ff8fbdd6faf; 0febf276-9ca4-5ebb-b21a-7d5b14235fed |
| sensor6 | HAS_PERFORMANCE | sel | POSITIVE | COMPARED / STUDY_RESULT | selectivity_comparison: NH 3 over several gases/VOCs including formaldehyde, ethanol, methanol, isopropanol, toluene, and acetone → NH3 versus formaldehyde, ethanol, methanol, isopropanol, toluene, acetone; temperature: room-temperature → room temperature | 946eefc8-2674-5188-8ac3-0ff8fbdd6faf; 0febf276-9ca4-5ebb-b21a-7d5b14235fed |
| gases | HAS_MEMBER | form | POSITIVE | ASSERTED / STUDY_RESULT |  | 0febf276-9ca4-5ebb-b21a-7d5b14235fed |
| gases | HAS_MEMBER | eth | POSITIVE | ASSERTED / STUDY_RESULT |  | 0febf276-9ca4-5ebb-b21a-7d5b14235fed |
| gases | HAS_MEMBER | meth | POSITIVE | ASSERTED / STUDY_RESULT |  | 0febf276-9ca4-5ebb-b21a-7d5b14235fed |
| gases | HAS_MEMBER | iso | POSITIVE | ASSERTED / STUDY_RESULT |  | 0febf276-9ca4-5ebb-b21a-7d5b14235fed |
| gases | HAS_MEMBER | tol | POSITIVE | ASSERTED / STUDY_RESULT |  | 0febf276-9ca4-5ebb-b21a-7d5b14235fed |
| gases | HAS_MEMBER | ace | POSITIVE | ASSERTED / STUDY_RESULT |  | 0febf276-9ca4-5ebb-b21a-7d5b14235fed |
| sensor6 | HAS_MECHANISM | mechanism | POSITIVE | PROPOSED / STUDY_RESULT |  | 0febf276-9ca4-5ebb-b21a-7d5b14235fed; 71ad8fbb-6182-5731-91b1-3386af058c29 |
| mechanism | MECHANISM_INVOLVES | modulation | POSITIVE | PROPOSED / STUDY_RESULT |  | 71ad8fbb-6182-5731-91b1-3386af058c29 |
| mechanism | MECHANISM_INVOLVES | acc | POSITIVE | PROPOSED / STUDY_RESULT |  | 71ad8fbb-6182-5731-91b1-3386af058c29 |
| mechanism | MECHANISM_INVOLVES | dep | POSITIVE | PROPOSED / STUDY_RESULT |  | 71ad8fbb-6182-5731-91b1-3386af058c29 |
| modulation | MECHANISM_INVOLVES | junction | POSITIVE | PROPOSED / STUDY_RESULT |  | 71ad8fbb-6182-5731-91b1-3386af058c29 |
| acc | LOCATED_IN | gcz | POSITIVE | PROPOSED / STUDY_RESULT |  | 71ad8fbb-6182-5731-91b1-3386af058c29 |
| dep | LOCATED_IN | mxene7 | POSITIVE | PROPOSED / STUDY_RESULT |  | 71ad8fbb-6182-5731-91b1-3386af058c29 |
| gcz | HAS_PROPERTY | ntype | POSITIVE | PROPOSED / STUDY_RESULT |  | 71ad8fbb-6182-5731-91b1-3386af058c29 |
| mxene7 | HAS_PROPERTY | ptype | POSITIVE | PROPOSED / STUDY_RESULT |  | 71ad8fbb-6182-5731-91b1-3386af058c29 |
| mg | HAS_COMPONENT | mg_mxene | POSITIVE | ASSERTED / STUDY_RESULT |  | 946eefc8-2674-5188-8ac3-0ff8fbdd6faf |
| mg | HAS_COMPONENT | mg_go | POSITIVE | ASSERTED / STUDY_RESULT |  | 946eefc8-2674-5188-8ac3-0ff8fbdd6faf |
| mz | HAS_COMPONENT | mz_mxene | POSITIVE | ASSERTED / STUDY_RESULT |  | 946eefc8-2674-5188-8ac3-0ff8fbdd6faf |
| mz | HAS_COMPONENT | mz_zno | POSITIVE | ASSERTED / STUDY_RESULT |  | 946eefc8-2674-5188-8ac3-0ff8fbdd6faf |
| mc | HAS_COMPONENT | mc_mxene | POSITIVE | ASSERTED / STUDY_RESULT |  | 946eefc8-2674-5188-8ac3-0ff8fbdd6faf |
| mc | HAS_COMPONENT | mc_cuo | POSITIVE | ASSERTED / STUDY_RESULT |  | 946eefc8-2674-5188-8ac3-0ff8fbdd6faf |
| mgz | HAS_COMPONENT | mgz_mxene | POSITIVE | ASSERTED / STUDY_RESULT |  | 946eefc8-2674-5188-8ac3-0ff8fbdd6faf |
| mgz | HAS_COMPONENT | mgz_go | POSITIVE | ASSERTED / STUDY_RESULT |  | 946eefc8-2674-5188-8ac3-0ff8fbdd6faf |
| mgz | HAS_COMPONENT | mgz_zno | POSITIVE | ASSERTED / STUDY_RESULT |  | 946eefc8-2674-5188-8ac3-0ff8fbdd6faf |
| mgc | HAS_COMPONENT | mgc_mxene | POSITIVE | ASSERTED / STUDY_RESULT |  | 946eefc8-2674-5188-8ac3-0ff8fbdd6faf |
| mgc | HAS_COMPONENT | mgc_go | POSITIVE | ASSERTED / STUDY_RESULT |  | 946eefc8-2674-5188-8ac3-0ff8fbdd6faf |
| mgc | HAS_COMPONENT | mgc_cuo | POSITIVE | ASSERTED / STUDY_RESULT |  | 946eefc8-2674-5188-8ac3-0ff8fbdd6faf |
| mzc | HAS_COMPONENT | mzc_mxene | POSITIVE | ASSERTED / STUDY_RESULT |  | 946eefc8-2674-5188-8ac3-0ff8fbdd6faf |
| mzc | HAS_COMPONENT | mzc_cuo | POSITIVE | ASSERTED / STUDY_RESULT |  | 946eefc8-2674-5188-8ac3-0ff8fbdd6faf |
| mzc | HAS_COMPONENT | mzc_zno | POSITIVE | ASSERTED / STUDY_RESULT |  | 946eefc8-2674-5188-8ac3-0ff8fbdd6faf |
| mgzc | HAS_COMPONENT | mgzc_mxene | POSITIVE | ASSERTED / STUDY_RESULT |  | 946eefc8-2674-5188-8ac3-0ff8fbdd6faf |
| mgzc | HAS_COMPONENT | mgzc_go | POSITIVE | ASSERTED / STUDY_RESULT |  | 946eefc8-2674-5188-8ac3-0ff8fbdd6faf |
| mgzc | HAS_COMPONENT | mgzc_cuo | POSITIVE | ASSERTED / STUDY_RESULT |  | 946eefc8-2674-5188-8ac3-0ff8fbdd6faf |
| mgzc | HAS_COMPONENT | mgzc_zno | POSITIVE | ASSERTED / STUDY_RESULT |  | 946eefc8-2674-5188-8ac3-0ff8fbdd6faf |
| material4 | HAS_COMPONENT | material4_mxene | POSITIVE | ASSERTED / STUDY_RESULT |  | af3e822d-e3d4-5fc4-b186-3407958a2389 |
| material4 | HAS_COMPONENT | material4_go | POSITIVE | ASSERTED / STUDY_RESULT |  | af3e822d-e3d4-5fc4-b186-3407958a2389 |
| material4 | HAS_COMPONENT | material4_cuo | POSITIVE | ASSERTED / STUDY_RESULT |  | af3e822d-e3d4-5fc4-b186-3407958a2389 |
| material4 | HAS_COMPONENT | material4_zno | POSITIVE | ASSERTED / STUDY_RESULT |  | af3e822d-e3d4-5fc4-b186-3407958a2389 |
| mat5a | HAS_COMPONENT | mat5a_mxene | POSITIVE | ASSERTED / STUDY_RESULT |  | 38fd32f8-9fb6-54c3-8a2e-546bd9cb2aef |
| mat5a | HAS_COMPONENT | mat5a_go | POSITIVE | ASSERTED / STUDY_RESULT |  | 38fd32f8-9fb6-54c3-8a2e-546bd9cb2aef |
| mat5a | HAS_COMPONENT | mat5a_cuo | POSITIVE | ASSERTED / STUDY_RESULT |  | 38fd32f8-9fb6-54c3-8a2e-546bd9cb2aef |
| mat5a | HAS_COMPONENT | mat5a_zno | POSITIVE | ASSERTED / STUDY_RESULT |  | 38fd32f8-9fb6-54c3-8a2e-546bd9cb2aef |
| mat5b | HAS_COMPONENT | mat5b_mxene | POSITIVE | ASSERTED / STUDY_RESULT |  | 38fd32f8-9fb6-54c3-8a2e-546bd9cb2aef |
| mat5b | HAS_COMPONENT | mat5b_go | POSITIVE | ASSERTED / STUDY_RESULT |  | 38fd32f8-9fb6-54c3-8a2e-546bd9cb2aef |
| mat5b | HAS_COMPONENT | mat5b_cuo | POSITIVE | ASSERTED / STUDY_RESULT |  | 38fd32f8-9fb6-54c3-8a2e-546bd9cb2aef |
| mat5b | HAS_COMPONENT | mat5b_zno | POSITIVE | ASSERTED / STUDY_RESULT |  | 38fd32f8-9fb6-54c3-8a2e-546bd9cb2aef |
| mat6 | HAS_COMPONENT | mat6_mxene | POSITIVE | ASSERTED / STUDY_RESULT |  | 0febf276-9ca4-5ebb-b21a-7d5b14235fed |
| mat6 | HAS_COMPONENT | mat6_go | POSITIVE | ASSERTED / STUDY_RESULT |  | 0febf276-9ca4-5ebb-b21a-7d5b14235fed |
| mat6 | HAS_COMPONENT | mat6_cuo | POSITIVE | ASSERTED / STUDY_RESULT |  | 0febf276-9ca4-5ebb-b21a-7d5b14235fed |
| mat6 | HAS_COMPONENT | mat6_zno | POSITIVE | ASSERTED / STUDY_RESULT |  | 0febf276-9ca4-5ebb-b21a-7d5b14235fed |
| gcz | HAS_COMPONENT | gcz_go | POSITIVE | PROPOSED / STUDY_RESULT |  | 71ad8fbb-6182-5731-91b1-3386af058c29 |
| gcz | HAS_COMPONENT | gcz_cuo | POSITIVE | PROPOSED / STUDY_RESULT |  | 71ad8fbb-6182-5731-91b1-3386af058c29 |
| gcz | HAS_COMPONENT | gcz_zno | POSITIVE | PROPOSED / STUDY_RESULT |  | 71ad8fbb-6182-5731-91b1-3386af058c29 |

## Identity decisions

| Left | Label | Right | Reason |
| --- | --- | --- | --- |
| nh3_6b | DIFFERENT | form | The source explicitly contrasts NH3 with this named comparison analyte; no inference of zero response. |
| nh3_6b | DIFFERENT | eth | The source explicitly contrasts NH3 with this named comparison analyte; no inference of zero response. |
| nh3_6b | DIFFERENT | meth | The source explicitly contrasts NH3 with this named comparison analyte; no inference of zero response. |
| nh3_6b | DIFFERENT | iso | The source explicitly contrasts NH3 with this named comparison analyte; no inference of zero response. |
| nh3_6b | DIFFERENT | tol | The source explicitly contrasts NH3 with this named comparison analyte; no inference of zero response. |
| nh3_6b | DIFFERENT | ace | The source explicitly contrasts NH3 with this named comparison analyte; no inference of zero response. |
| mxene | SAME | mxene2 | Repeated full Ti3C2Tx MXene name with case/spacing variation; background and proposed mechanism scopes remain distinct. |
| mxene | SAME | mxene7 | Repeated full Ti3C2Tx MXene name with case/spacing variation; background and proposed mechanism scopes remain distinct. |
| go | SAME | go_alias | Explicit local graphene oxide (GO) definition. |
| cuo | SAME | cuo_alias | Explicit local copper oxide (CuO) definition. |
| zno | SAME | zno_alias | Explicit local zinc oxide (ZnO) definition. |
| nh3_material | SAME | nh3_2 | Repeated explicit NH3 chemical formula; roles and measurement instances remain scoped. |
| nh3_material | SAME | nh3_3 | Repeated explicit NH3 chemical formula; roles and measurement instances remain scoped. |
| nh3_material | SAME | nh3_4 | Repeated explicit NH3 chemical formula; roles and measurement instances remain scoped. |
| nh3_material | SAME | nh3_6a | Repeated explicit NH3 chemical formula; roles and measurement instances remain scoped. |
| nh3_material | SAME | nh3_6b | Repeated explicit NH3 chemical formula; roles and measurement instances remain scoped. |
| nh3_material | SAME | nh3_7 | Repeated explicit NH3 chemical formula; roles and measurement instances remain scoped. |
| mgzc | SAME | material4 | Same four explicitly named constituents; listing order does not change material concept. Ratio is attached only where supplied; no equality of tested sample instances. |
| mgzc | SAME | mat5a | Same four explicitly named constituents; listing order does not change material concept. Ratio is attached only where supplied; no equality of tested sample instances. |
| mgzc | SAME | mat5b | Same four explicitly named constituents; listing order does not change material concept. Ratio is attached only where supplied; no equality of tested sample instances. |
| mgzc | SAME | mat6 | Same four explicitly named constituents; listing order does not change material concept. Ratio is attached only where supplied; no equality of tested sample instances. |
| mgzc | SAME | mixture | S2 names the same four constituents as the four-component nanocomposite; concept identity does not fix their weight ratio. |
| sensor4 | SAME | sensor | S2 introduces the four-component sensing mixture and its NH3 sensor; S4 repeats the full four-component sensor name. Optimal-ratio configuration remains separately scoped. |
| ratios | SAME | ratio | Plural/singular component weight-ratio property, not equality of numeric ratios. |
| temp | SAME | temp2 | Room-temperature wording; no numeric temperature inferred. |
| temp | SAME | temp3 | Room-temperature wording; no numeric temperature inferred. |
| composites | SAME | materials3 | Direct reference to the synthesized seven nanocomposites as sensing materials. |
| mxene | SAME | mg_mxene | Local full-name/formula definition and explicitly named constituent; no equivalence of whole composite and constituent. |
| go | SAME | mg_go | Local full-name/formula definition and explicitly named constituent; no equivalence of whole composite and constituent. |
| mxene | SAME | mz_mxene | Local full-name/formula definition and explicitly named constituent; no equivalence of whole composite and constituent. |
| zno | SAME | mz_zno | Local full-name/formula definition and explicitly named constituent; no equivalence of whole composite and constituent. |
| mxene | SAME | mc_mxene | Local full-name/formula definition and explicitly named constituent; no equivalence of whole composite and constituent. |
| cuo | SAME | mc_cuo | Local full-name/formula definition and explicitly named constituent; no equivalence of whole composite and constituent. |
| mxene | SAME | mgz_mxene | Local full-name/formula definition and explicitly named constituent; no equivalence of whole composite and constituent. |
| go | SAME | mgz_go | Local full-name/formula definition and explicitly named constituent; no equivalence of whole composite and constituent. |
| zno | SAME | mgz_zno | Local full-name/formula definition and explicitly named constituent; no equivalence of whole composite and constituent. |
| mxene | SAME | mgc_mxene | Local full-name/formula definition and explicitly named constituent; no equivalence of whole composite and constituent. |
| go | SAME | mgc_go | Local full-name/formula definition and explicitly named constituent; no equivalence of whole composite and constituent. |
| cuo | SAME | mgc_cuo | Local full-name/formula definition and explicitly named constituent; no equivalence of whole composite and constituent. |
| mxene | SAME | mzc_mxene | Local full-name/formula definition and explicitly named constituent; no equivalence of whole composite and constituent. |
| cuo | SAME | mzc_cuo | Local full-name/formula definition and explicitly named constituent; no equivalence of whole composite and constituent. |
| zno | SAME | mzc_zno | Local full-name/formula definition and explicitly named constituent; no equivalence of whole composite and constituent. |
| mxene | SAME | mgzc_mxene | Local full-name/formula definition and explicitly named constituent; no equivalence of whole composite and constituent. |
| go | SAME | mgzc_go | Local full-name/formula definition and explicitly named constituent; no equivalence of whole composite and constituent. |
| cuo | SAME | mgzc_cuo | Local full-name/formula definition and explicitly named constituent; no equivalence of whole composite and constituent. |
| zno | SAME | mgzc_zno | Local full-name/formula definition and explicitly named constituent; no equivalence of whole composite and constituent. |
| mxene | SAME | material4_mxene | Local full-name/formula definition and explicitly named constituent; no equivalence of whole composite and constituent. |
| go | SAME | material4_go | Local full-name/formula definition and explicitly named constituent; no equivalence of whole composite and constituent. |
| cuo | SAME | material4_cuo | Local full-name/formula definition and explicitly named constituent; no equivalence of whole composite and constituent. |
| zno | SAME | material4_zno | Local full-name/formula definition and explicitly named constituent; no equivalence of whole composite and constituent. |
| mxene | SAME | mat5a_mxene | Local full-name/formula definition and explicitly named constituent; no equivalence of whole composite and constituent. |
| go | SAME | mat5a_go | Local full-name/formula definition and explicitly named constituent; no equivalence of whole composite and constituent. |
| cuo | SAME | mat5a_cuo | Local full-name/formula definition and explicitly named constituent; no equivalence of whole composite and constituent. |
| zno | SAME | mat5a_zno | Local full-name/formula definition and explicitly named constituent; no equivalence of whole composite and constituent. |
| mxene | SAME | mat5b_mxene | Local full-name/formula definition and explicitly named constituent; no equivalence of whole composite and constituent. |
| go | SAME | mat5b_go | Local full-name/formula definition and explicitly named constituent; no equivalence of whole composite and constituent. |
| cuo | SAME | mat5b_cuo | Local full-name/formula definition and explicitly named constituent; no equivalence of whole composite and constituent. |
| zno | SAME | mat5b_zno | Local full-name/formula definition and explicitly named constituent; no equivalence of whole composite and constituent. |
| mxene | SAME | mat6_mxene | Local full-name/formula definition and explicitly named constituent; no equivalence of whole composite and constituent. |
| go | SAME | mat6_go | Local full-name/formula definition and explicitly named constituent; no equivalence of whole composite and constituent. |
| cuo | SAME | mat6_cuo | Local full-name/formula definition and explicitly named constituent; no equivalence of whole composite and constituent. |
| zno | SAME | mat6_zno | Local full-name/formula definition and explicitly named constituent; no equivalence of whole composite and constituent. |
| go | SAME | gcz_go | Local full-name/formula definition and explicitly named constituent; no equivalence of whole composite and constituent. |
| cuo | SAME | gcz_cuo | Local full-name/formula definition and explicitly named constituent; no equivalence of whole composite and constituent. |
| zno | SAME | gcz_zno | Local full-name/formula definition and explicitly named constituent; no equivalence of whole composite and constituent. |
| sensor4 | BROADER | sensor6 | Optimal-ratio sensor is a specified configuration of the four-component sensor; instance-level SAME is deliberately not assumed. |
| mg | DIFFERENT | mgzc | Different explicitly listed constituent set; retain separate composite concepts. |
| mz | DIFFERENT | mgzc | Different explicitly listed constituent set; retain separate composite concepts. |
| mc | DIFFERENT | mgzc | Different explicitly listed constituent set; retain separate composite concepts. |
| mgz | DIFFERENT | mgzc | Different explicitly listed constituent set; retain separate composite concepts. |
| mgc | DIFFERENT | mgzc | Different explicitly listed constituent set; retain separate composite concepts. |
| mzc | DIFFERENT | mgzc | Different explicitly listed constituent set; retain separate composite concepts. |
| go | DIFFERENT | cuo | Separately named chemical/material constituents, not aliases. |
| go | DIFFERENT | zno | Separately named chemical/material constituents, not aliases. |
| cuo | DIFFERENT | zno | Separately named chemical/material constituents, not aliases. |
| mxene | DIFFERENT | go | Separately named chemical/material constituents, not aliases. |

## Unresolved

# Вопросы документа

Все открытые вопросы UNRESOLVED. Они не блокировали автоматический проход. Q1/Q2/Q3 решены пользователем и находятся в adjudication_decisions.jsonl.
