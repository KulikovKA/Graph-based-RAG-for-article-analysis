# D078 — Ultrasensitive N-Channel Graphene Gas Sensors by Nondestructive Molecular Doping

**AI draft — HUMAN_REVIEW=NOT_REVIEWED; не human gold.**

Document `c56c60ec-74f3-44d5-83e6-f83d87b921f5`, revision `85c8c16f-76e7-45fb-a9b2-6124974a51e9`, split `DEV`, rubric `pilot24-rubric-0.3-AUTO-FROZEN`.

Chunks 2; sentences 9; mentions 63; assertions 24; unique canonical triples 23; questions 6; validation PASS.

Полный AI-проход завершён. exhaustive_entities=True; exhaustive_relations=False; неразрешённые кандидаты не являются negative gold.

## Исходные frozen EvidenceChunks

### `8e528f95-22fc-4b9a-8b16-90391b584bc3`

SHA-256 `b0f5211d8a7b056bc9d7cccb1c371076afd5e4dc80f88e80baf6e7c51c26a088`, section `abstract`; [0, 1033).

Sensitive and selective detection of target gases is the ultimate goal for commercialization of graphene gas sensors. Here, ultrasensitive n-channel graphene gas sensors were developed by using n-doped graphene with ethylene amines. The exposure of the n-doped graphene to oxidizing gases such as NO 2 leads to a current decrease that depends strongly on the number of amine functional groups in various types of ethylene amines. Graphene doped with diethylenetriamine (DETA) exhibits the highest response, recovery, and long-term sensing stability to NO 2, with an average detection limit of 0.83 parts per quadrillion (ppq, 10 –15 ), due to the attractive electrostatic interaction between electron-rich graphene and electron-deficient NO 2 . Our first-principles calculation supported a preferential adsorption of NO 2 on n-doped graphene. In addition, gas molecules on the n-channel graphene provide charged impurities, thereby intensifying the current decrease for an excellent response to oxidizing gases such as NO 2 or SO 2 .

### `509195ce-f818-487d-8196-eb0511b0acaf`

SHA-256 `8cf72195f178a68bd7e6a2d2169cfb9fb999fd60e210183af6018a2992bca0e5`, section `abstract`; [1034, 1686).

On the contrary, absence of such a strong interaction between NH 3 and DETA-doped graphene and combined effects of current increase by n-doping and mobility decrease by charged impurities result in a completely no response to NH 3 . Because the n-channel is easily induced by a top-molecular dopant, a flexible graphene sensor with outstanding NO 2 detection capability was successfully fabricated on plastic without vertical stacks of gate-electrode and gate-dielectric. Our gate-free graphene gas sensors enabled by nondestructive molecular n-doping could be used for the selective detection of subppq-level NO 2 in a gas mixture with reducing gases.

## Semantic self-audit

No NH3 response and no gate stacks are explicit negatives.
0.83 ppq preserved without exponent conversion; NO2 and SO2 are distinct; theory and could be used are modal.
Mechanistic/property dependencies outside 18 types are retained unresolved.

## Mentions

| Key | Sentence | Span | Surface | Kind / role | Canonical |
| --- | --- | --- | --- | --- | --- |
| detect | S1 | [0,33) | Sensitive and selective detection | APPLICATION / technical_application | sensitive selective gas detection |
| gases | S1 | [37,49) | target gases | ANALYTE / technical_analyte | target gases unspecified |
| sensor | S1 | [96,116) | graphene gas sensors | DEVICE / technical_device | generic graphene gas sensor |
| commercial | S1 | [75,92) | commercialization | APPLICATION / technical_application | commercialization |
| sensor2 | S2 | [139,169) | n-channel graphene gas sensors | DEVICE / technical_device | n-channel graphene gas sensor |
| ultra | S2 | [124,138) | ultrasensitive | PERFORMANCE / technical_performance | high gas sensitivity |
| ndoped | S2 | [194,210) | n-doped graphene | MATERIAL / technical_material | ethylene-amine n-doped graphene |
| amines | S2 | [216,231) | ethylene amines | MATERIAL / dopant | ethylene amines |
| expose | S3 | [237,288) | exposure of the n-doped graphene to oxidizing gases | PROCESS / technical_process | oxidizing gas exposure |
| ndoped3 | S3 | [253,269) | n-doped graphene | MATERIAL / technical_material | ethylene-amine n-doped graphene |
| oxidants | S3 | [273,288) | oxidizing gases | ANALYTE / technical_analyte | oxidizing gases |
| no2 | S3 | [297,301) | NO 2 | ANALYTE / technical_analyte | nitrogen dioxide |
| decrease | S3 | [313,329) | current decrease | PROPERTY / technical_property | current decrease |
| number | S3 | [359,392) | number of amine functional groups | PROPERTY / technical_property | amine functional-group count |
| groups | S3 | [369,392) | amine functional groups | MORPHOLOGY / technical_morphology | amine functional groups |
| amines3 | S3 | [413,428) | ethylene amines | MATERIAL / technical_material | ethylene amines |
| deta_mat | S4 | [430,475) | Graphene doped with diethylenetriamine (DETA) | MATERIAL / technical_material | DETA-doped graphene |
| deta | S4 | [450,468) | diethylenetriamine | MATERIAL / dopant | diethylenetriamine |
| deta_alias | S4 | [470,474) | DETA | MATERIAL / dopant | diethylenetriamine |
| response | S4 | [489,505) | highest response | PERFORMANCE / technical_performance | response |
| recovery | S4 | [507,515) | recovery | PERFORMANCE / technical_performance | recovery |
| stability | S4 | [521,548) | long-term sensing stability | PERFORMANCE / technical_performance | long-term sensing stability |
| no24 | S4 | [552,556) | NO 2 | ANALYTE / target_analyte | nitrogen dioxide |
| lod | S4 | [566,589) | average detection limit | PERFORMANCE / technical_performance | average detection limit |
| interaction | S4 | [647,683) | attractive electrostatic interaction | MECHANISM / technical_mechanism | attractive electrostatic interaction |
| rich | S4 | [692,714) | electron-rich graphene | MATERIAL / technical_material | electron-rich graphene |
| deficient | S4 | [719,742) | electron-deficient NO 2 | ANALYTE / technical_analyte | electron-deficient nitrogen dioxide |
| calculation | S5 | [749,777) | first-principles calculation | TECHNOLOGY / technical_technology | first-principles calculation |
| adsorption | S5 | [790,813) | preferential adsorption | PROCESS / technical_process | preferential NO2 adsorption |
| no25 | S5 | [817,821) | NO 2 | ANALYTE / technical_analyte | nitrogen dioxide |
| ndoped5 | S5 | [825,841) | n-doped graphene | MATERIAL / technical_material | ethylene-amine n-doped graphene |
| molecules | S6 | [856,869) | gas molecules | ANALYTE / technical_analyte | gas molecules unspecified |
| channel | S6 | [877,895) | n-channel graphene | MATERIAL / technical_material | n-channel graphene |
| impurities | S6 | [904,922) | charged impurities | MORPHOLOGY / charged_scattering_center | charged impurities |
| decrease6 | S6 | [949,965) | current decrease | PROPERTY / technical_property | current decrease |
| response6 | S6 | [973,991) | excellent response | PERFORMANCE / technical_performance | response |
| oxidants6 | S6 | [995,1010) | oxidizing gases | ANALYTE / technical_analyte | oxidizing gases |
| no26 | S6 | [1019,1023) | NO 2 | ANALYTE / technical_analyte | nitrogen dioxide |
| so2 | S6 | [1027,1031) | SO 2 | ANALYTE / technical_analyte | sulfur dioxide |
| nh3 | S7 | [62,66) | NH 3 | ANALYTE / target_analyte | ammonia |
| interaction7 | S7 | [35,53) | strong interaction | MECHANISM / technical_mechanism | strong NH3–DETA graphene interaction |
| deta7 | S7 | [71,90) | DETA-doped graphene | MATERIAL / technical_material | DETA-doped graphene |
| effects | S7 | [95,187) | combined effects of current increase by n-doping and mobility decrease by charged impurities | MECHANISM / technical_mechanism | combined opposing electronic effects |
| increase | S7 | [115,131) | current increase | PROPERTY / technical_property | current increase |
| ndoping | S7 | [135,143) | n-doping | PROCESS / technical_process | molecular n-doping |
| mobility | S7 | [148,165) | mobility decrease | PROPERTY / technical_property | mobility decrease |
| impurities7 | S7 | [169,187) | charged impurities | MORPHOLOGY / charged_scattering_center | charged impurities |
| no_response | S7 | [200,222) | completely no response | PERFORMANCE / technical_performance | NH3 response |
| nh37 | S7 | [226,230) | NH 3 | ANALYTE / target_analyte | ammonia |
| flex_sensor | S8 | [302,326) | flexible graphene sensor | DEVICE / technical_device | flexible gate-free graphene sensor |
| flex | S8 | [302,310) | flexible | PROPERTY / technical_property | flexibility |
| no28 | S8 | [344,348) | NO 2 | ANALYTE / technical_analyte | nitrogen dioxide |
| plastic | S8 | [401,408) | plastic | MATERIAL / technical_material | plastic substrate |
| stacks | S8 | [417,470) | vertical stacks of gate-electrode and gate-dielectric | DEVICE / technical_device | vertical gate stacks |
| gate | S8 | [436,450) | gate-electrode | DEVICE / technical_device | gate electrode |
| dielectric | S8 | [455,470) | gate-dielectric | DEVICE / technical_device | gate dielectric |
| dopant | S8 | [278,298) | top-molecular dopant | MATERIAL / technical_material | top molecular dopant |
| gatefree | S9 | [476,506) | gate-free graphene gas sensors | DEVICE / technical_device | flexible gate-free graphene sensor |
| doping9 | S9 | [518,551) | nondestructive molecular n-doping | PROCESS / technical_process | molecular n-doping |
| application | S9 | [574,593) | selective detection | APPLICATION / technical_application | selective subppq NO2 detection |
| no29 | S9 | [610,614) | NO 2 | ANALYTE / technical_analyte | nitrogen dioxide |
| mixture | S9 | [620,651) | gas mixture with reducing gases | OPERATING_CONDITION / technical_operating_condition | gas mixture with reducing gases |
| reducing | S9 | [637,651) | reducing gases | ANALYTE / technical_analyte | reducing gases |

## Assertions

| Head | Relation | Tail | Polarity | Modality / scope | Qualifiers | Evidence span IDs |
| --- | --- | --- | --- | --- | --- | --- |
| sensor | USED_FOR | detect | POSITIVE | HYPOTHETICAL / BACKGROUND |  | 2b071bc2-9e18-5b40-88bc-701b0069d428 |
| sensor2 | USES_MATERIAL | ndoped | POSITIVE | ASSERTED / STUDY_RESULT |  | 9343e34d-7c40-5cfc-8928-3e6567817872 |
| sensor2 | HAS_PERFORMANCE | ultra | POSITIVE | ASSERTED / STUDY_RESULT |  | 9343e34d-7c40-5cfc-8928-3e6567817872 |
| ndoped | HAS_COMPONENT | amines | POSITIVE | ASSERTED / STUDY_RESULT |  | 9343e34d-7c40-5cfc-8928-3e6567817872 |
| expose | ACTS_ON | ndoped3 | POSITIVE | ASSERTED / STUDY_RESULT |  | e39657f3-4e0f-5648-8d2f-f836a2156b68 |
| ndoped3 | HAS_PROPERTY | decrease | POSITIVE | ASSERTED / STUDY_RESULT |  | e39657f3-4e0f-5648-8d2f-f836a2156b68 |
| amines3 | HAS_PROPERTY | number | POSITIVE | ASSERTED / STUDY_RESULT |  | e39657f3-4e0f-5648-8d2f-f836a2156b68 |
| deta_mat | HAS_COMPONENT | deta | POSITIVE | COMPARED / STUDY_RESULT |  | 6bc86077-5e9b-5be5-b86d-d9725303728d |
| deta_mat | HAS_PERFORMANCE | response | POSITIVE | COMPARED / STUDY_RESULT |  | 6bc86077-5e9b-5be5-b86d-d9725303728d |
| deta_mat | HAS_PERFORMANCE | recovery | POSITIVE | COMPARED / STUDY_RESULT |  | 6bc86077-5e9b-5be5-b86d-d9725303728d |
| deta_mat | HAS_PERFORMANCE | stability | POSITIVE | COMPARED / STUDY_RESULT |  | 6bc86077-5e9b-5be5-b86d-d9725303728d |
| deta_mat | USED_FOR | no24 | POSITIVE | COMPARED / STUDY_RESULT |  | 6bc86077-5e9b-5be5-b86d-d9725303728d |
| deta_mat | HAS_PERFORMANCE | lod | POSITIVE | ASSERTED / STUDY_RESULT | detection_limit: 0.83 parts per quadrillion (ppq, 10 –15 ) → 0.83 | 6bc86077-5e9b-5be5-b86d-d9725303728d |
| adsorption | ACTS_ON | ndoped5 | POSITIVE | PROPOSED / STUDY_RESULT | support_method: first-principles calculation → first-principles calculation | 8a2e869c-7b43-50c7-89f7-78ff9de1b117 |
| channel | HAS_MORPHOLOGY | impurities | POSITIVE | ASSERTED / STUDY_RESULT |  | 3655e5c8-916a-5d23-9618-6396a91a2fc8 |
| channel | HAS_PERFORMANCE | response6 | POSITIVE | ASSERTED / STUDY_RESULT | analyte_scope: NO 2 or SO 2 → NO 2 or SO 2 | 3655e5c8-916a-5d23-9618-6396a91a2fc8 |
| deta7 | HAS_PERFORMANCE | no_response | NEGATIVE | ASSERTED / STUDY_RESULT |  | 6ea09abb-6aac-5328-899f-4d4efc26f2df |
| sensor2 | DETECTS | nh37 | NEGATIVE | ASSERTED / STUDY_RESULT | material_configuration: DETA-doped graphene → DETA-doped graphene | 9343e34d-7c40-5cfc-8928-3e6567817872; 6ea09abb-6aac-5328-899f-4d4efc26f2df |
| flex_sensor | HAS_PROPERTY | flex | POSITIVE | ASSERTED / STUDY_RESULT |  | 46be847f-de63-5489-91d8-123f798e0804 |
| flex_sensor | DETECTS | no28 | POSITIVE | ASSERTED / STUDY_RESULT |  | 46be847f-de63-5489-91d8-123f798e0804 |
| flex_sensor | USES_MATERIAL | plastic | POSITIVE | ASSERTED / STUDY_RESULT |  | 46be847f-de63-5489-91d8-123f798e0804 |
| flex_sensor | HAS_COMPONENT | stacks | NEGATIVE | ASSERTED / STUDY_RESULT |  | 46be847f-de63-5489-91d8-123f798e0804 |
| gatefree | USED_FOR | application | POSITIVE | HYPOTHETICAL / STUDY_RESULT | concentration_regime: subppq-level → subppq-level; sample_condition: gas mixture with reducing gases → gas mixture with reducing gases | b0bdd00f-761e-55f3-ac45-a744b98fe221 |
| gatefree | DETECTS | no29 | POSITIVE | HYPOTHETICAL / STUDY_RESULT | concentration_regime: subppq-level → subppq-level | b0bdd00f-761e-55f3-ac45-a744b98fe221 |

## Identity decisions

| Left | Label | Right | Reason |
| --- | --- | --- | --- |
| no2 | DIFFERENT | nh3 | Oxidizing NO2 and reducing NH3 are explicitly distinguished; negative NH3 result preserved. |
| deta | NARROWER | amines | DETA is one named ethylene amine; the class is not SAME. |
| ndoped | SAME | ndoped3 | Curated source-local repetition/explicit alias; conditions and physical instances remain separate. |
| ndoped | SAME | ndoped5 | Curated source-local repetition/explicit alias; conditions and physical instances remain separate. |
| amines | SAME | amines3 | Curated source-local repetition/explicit alias; conditions and physical instances remain separate. |
| oxidants | SAME | oxidants6 | Curated source-local repetition/explicit alias; conditions and physical instances remain separate. |
| no2 | SAME | no24 | Curated source-local repetition/explicit alias; conditions and physical instances remain separate. |
| no2 | SAME | no25 | Curated source-local repetition/explicit alias; conditions and physical instances remain separate. |
| no2 | SAME | no26 | Curated source-local repetition/explicit alias; conditions and physical instances remain separate. |
| no2 | SAME | no28 | Curated source-local repetition/explicit alias; conditions and physical instances remain separate. |
| no2 | SAME | no29 | Curated source-local repetition/explicit alias; conditions and physical instances remain separate. |
| decrease | SAME | decrease6 | Curated source-local repetition/explicit alias; conditions and physical instances remain separate. |
| deta_mat | SAME | deta7 | Curated source-local repetition/explicit alias; conditions and physical instances remain separate. |
| deta | SAME | deta_alias | Curated source-local repetition/explicit alias; conditions and physical instances remain separate. |
| response | SAME | response6 | Curated source-local repetition/explicit alias; conditions and physical instances remain separate. |
| impurities | SAME | impurities7 | Curated source-local repetition/explicit alias; conditions and physical instances remain separate. |
| nh3 | SAME | nh37 | Curated source-local repetition/explicit alias; conditions and physical instances remain separate. |
| ndoping | SAME | doping9 | Curated source-local repetition/explicit alias; conditions and physical instances remain separate. |
| flex_sensor | SAME | gatefree | Curated source-local repetition/explicit alias; conditions and physical instances remain separate. |

## Unresolved

# Вопросы документа

Все открытые вопросы UNRESOLVED. Они не блокировали автоматический проход. Q1/Q2/Q3 решены пользователем и находятся в adjudication_decisions.jsonl.

## D078-Q4 — D078

**Статья:** Ultrasensitive N-Channel Graphene Gas Sensors by Nondestructive Molecular Doping.

Document `c56c60ec-74f3-44d5-83e6-f83d87b921f5`; revision `85c8c16f-76e7-45fb-a9b2-6124974a51e9`; split `DEV`.

**Точный оригинал:**

> The exposure of the n-doped graphene to oxidizing gases such as NO 2 leads to a current decrease that depends strongly on the number of amine functional groups in various types of ethylene amines.

**Перевод и смысл:** В тексте описан причинный переход: исходный процесс/механизм приводит к указанному результату. FACILITATES не сохраняет эту более сильную формулировку.

**Что неоднозначно/непокрыто:** Gas exposure causes a current decrease; PROPERTY endpoint is outside FACILITATES.

A. Представить CAUSES после отдельного согласования схемы.

B. Сохранить существующую схему и учитывать как непокрытое отношение.

C. Оставить UNRESOLVED до содержательной проверки.

**Предварительное предложение:** A для DEV при подтверждении семантики; B для CALIBRATION/HOLDOUT без изменения схемы.

| Head | Proposed relation | Tail | Modality / polarity |
| --- | --- | --- | --- |
| exposure of the n-doped graphene to oxidizing gases | CAUSES | current decrease | ASSERTED / POSITIVE |

## D078-Q5 — D078

**Статья:** Ultrasensitive N-Channel Graphene Gas Sensors by Nondestructive Molecular Doping.

Document `c56c60ec-74f3-44d5-83e6-f83d87b921f5`; revision `85c8c16f-76e7-45fb-a9b2-6124974a51e9`; split `DEV`.

**Точный оригинал:**

> The exposure of the n-doped graphene to oxidizing gases such as NO 2 leads to a current decrease that depends strongly on the number of amine functional groups in various types of ethylene amines.

**Перевод и смысл:** Значение характеристики явно зависит от структуры, конфигурации или параметра. Словарь не выражает такую зависимость.

**Что неоднозначно/непокрыто:** Явная зависимость current decrease от числа amine groups; не SAME и не HAS_COMPONENT.

A. Представить DEPENDS_ON после отдельного согласования схемы.

B. Сохранить существующую схему и учитывать как непокрытое отношение.

C. Оставить UNRESOLVED до содержательной проверки.

**Предварительное предложение:** A для DEV при подтверждении семантики; B для CALIBRATION/HOLDOUT без изменения схемы.

| Head | Proposed relation | Tail | Modality / polarity |
| --- | --- | --- | --- |
| current decrease | DEPENDS_ON | number of amine functional groups | ASSERTED / POSITIVE |

## D078-Q6 — D078

**Статья:** Ultrasensitive N-Channel Graphene Gas Sensors by Nondestructive Molecular Doping.

Document `c56c60ec-74f3-44d5-83e6-f83d87b921f5`; revision `85c8c16f-76e7-45fb-a9b2-6124974a51e9`; split `DEV`.

**Точный оригинал:**

> Graphene doped with diethylenetriamine (DETA) exhibits the highest response, recovery, and long-term sensing stability to NO 2, with an average detection limit of 0.83 parts per quadrillion (ppq, 10 –15 ), due to the attractive electrostatic interaction between electron-rich graphene and electron-deficient NO 2 .

**Перевод и смысл:** В тексте механизм относится к материалу, тогда как принятый HAS_MECHANISM допускает только DEVICE. Подмена материала устройством исказила бы тип.

**Что неоднозначно/непокрыто:** Материал, а не названный DEVICE, является носителем объяснения. Требуется расширение domain HAS_MECHANISM.

A. Представить HAS_MECHANISM после отдельного согласования схемы.

B. Сохранить существующую схему и учитывать как непокрытое отношение.

C. Оставить UNRESOLVED до содержательной проверки.

**Предварительное предложение:** A для DEV при подтверждении семантики; B для CALIBRATION/HOLDOUT без изменения схемы.

| Head | Proposed relation | Tail | Modality / polarity |
| --- | --- | --- | --- |
| Graphene doped with diethylenetriamine (DETA) | HAS_MECHANISM | attractive electrostatic interaction | ASSERTED / POSITIVE |

## D078-Q7 — D078

**Статья:** Ultrasensitive N-Channel Graphene Gas Sensors by Nondestructive Molecular Doping.

Document `c56c60ec-74f3-44d5-83e6-f83d87b921f5`; revision `85c8c16f-76e7-45fb-a9b2-6124974a51e9`; split `DEV`.

**Точный оригинал:**

> In addition, gas molecules on the n-channel graphene provide charged impurities, thereby intensifying the current decrease for an excellent response to oxidizing gases such as NO 2 or SO 2 .

**Перевод и смысл:** Величина явно увеличивается под действием указанного фактора. Это направление изменения; оно не всегда равнозначно улучшению качества.

**Что неоднозначно/непокрыто:** Charged impurities intensify current decrease; electronic structure → electrical property effect is uncovered.

A. Представить INCREASES после отдельного согласования схемы.

B. Сохранить существующую схему и учитывать как непокрытое отношение.

C. Оставить UNRESOLVED до содержательной проверки.

**Предварительное предложение:** A для DEV при подтверждении семантики; B для CALIBRATION/HOLDOUT без изменения схемы.

| Head | Proposed relation | Tail | Modality / polarity |
| --- | --- | --- | --- |
| charged impurities | INCREASES | current decrease | ASSERTED / POSITIVE |

## D078-Q8 — D078

**Статья:** Ultrasensitive N-Channel Graphene Gas Sensors by Nondestructive Molecular Doping.

Document `c56c60ec-74f3-44d5-83e6-f83d87b921f5`; revision `85c8c16f-76e7-45fb-a9b2-6124974a51e9`; split `DEV`.

**Точный оригинал:**

> On the contrary, absence of such a strong interaction between NH 3 and DETA-doped graphene and combined effects of current increase by n-doping and mobility decrease by charged impurities result in a completely no response to NH 3 .

**Перевод и смысл:** В тексте механизм относится к материалу, тогда как принятый HAS_MECHANISM допускает только DEVICE. Подмена материала устройством исказила бы тип.

**Что неоднозначно/непокрыто:** Absence of strong interaction is explicit; candidate domain extension, polarity retained separately.

A. Представить HAS_MECHANISM после отдельного согласования схемы.

B. Сохранить существующую схему и учитывать как непокрытое отношение.

C. Оставить UNRESOLVED до содержательной проверки.

**Предварительное предложение:** A для DEV при подтверждении семантики; B для CALIBRATION/HOLDOUT без изменения схемы.

| Head | Proposed relation | Tail | Modality / polarity |
| --- | --- | --- | --- |
| DETA-doped graphene | HAS_MECHANISM | strong interaction | ASSERTED / NEGATIVE |

## D078-Q9 — D078

**Статья:** Ultrasensitive N-Channel Graphene Gas Sensors by Nondestructive Molecular Doping.

Document `c56c60ec-74f3-44d5-83e6-f83d87b921f5`; revision `85c8c16f-76e7-45fb-a9b2-6124974a51e9`; split `DEV`.

**Точный оригинал:**

> On the contrary, absence of such a strong interaction between NH 3 and DETA-doped graphene and combined effects of current increase by n-doping and mobility decrease by charged impurities result in a completely no response to NH 3 .

**Перевод и смысл:** В тексте механизм относится к материалу, тогда как принятый HAS_MECHANISM допускает только DEVICE. Подмена материала устройством исказила бы тип.

**Что неоднозначно/непокрыто:** The combined current-increase and mobility-decrease effects explain the NH3 nonresponse; frozen MATERIAL-domain gap, not an independently measured quantitative cancellation.

A. Представить HAS_MECHANISM после отдельного согласования схемы.

B. Сохранить существующую схему и учитывать как непокрытое отношение.

C. Оставить UNRESOLVED до содержательной проверки.

**Предварительное предложение:** A для DEV при подтверждении семантики; B для CALIBRATION/HOLDOUT без изменения схемы.

| Head | Proposed relation | Tail | Modality / polarity |
| --- | --- | --- | --- |
| DETA-doped graphene | HAS_MECHANISM | combined effects of current increase by n-doping and mobility decrease by charged impurities | ASSERTED / POSITIVE |
