# D017 — Gas sensing in 2D materials

**AI draft — HUMAN_REVIEW=NOT_REVIEWED; не human gold.**

Document `2860ed7f-a2a8-4e76-9250-e3558d092f23`, revision `d80633dc-c57a-4253-8754-29c9366084f5`, split `DEV`, rubric `pilot24-rubric-0.3-AUTO-FROZEN`.

Chunks 2; sentences 7; mentions 37; assertions 29; unique canonical triples 28; questions 0; validation PASS.

Полный AI-проход завершён. exhaustive_entities=True; exhaustive_relations=True; неразрешённые кандидаты не являются negative gold.

## Исходные frozen EvidenceChunks

### `52c7bac2-feff-4316-934f-2726c4842540`

SHA-256 `651d394d86153236deeb8d70507215a9e8b8d77ab04eec43518a0daabf9003e2`, section `abstract`; [0, 1105).

Two-dimensional (2D) layered inorganic nanomaterials have attracted huge attention due to their unique electronic structures, as well as extraordinary physical and chemical properties for use in electronics, optoelectronics, spintronics, catalysts, energy generation and storage, and chemical sensors. Graphene and related layered inorganic analogues have shown great potential for gas-sensing applications because of their large specific surface areas and strong surface activities. This review aims to discuss the latest advancements in the 2D layered inorganic materials for gas sensors. We first elaborate the gas-sensing mechanisms and introduce various types of gas-sensing devices. Then, we describe the basic parameters and influence factors of the gas sensors to further enhance their performance. Moreover, we systematically present the current gas-sensing applications based on graphene, graphene oxide (GO), reduced graphene oxide (rGO), functionalized GO or rGO, transition metal dichalcogenides, layered III-VI semiconductors, layered metal oxides, phosphorene, hexagonal boron nitride, etc.

### `60c46884-0b00-408c-a0d7-693eeae8beca`

SHA-256 `e52aca9b25835eb15b142479046e050ec9f21ae5aedcd22b3e2294c658206c41`, section `abstract`; [1106, 1213).

Finally, we conclude the future prospects of these layered inorganic materials in gas-sensing applications.

## Semantic self-audit

Review scope is explicit; no generic topics converted into measured experimental findings.
Graphene, GO, rGO, functionalized materials and analogues remain distinct.

## Mentions

| Key | Sentence | Span | Surface | Kind / role | Canonical |
| --- | --- | --- | --- | --- | --- |
| materials | S1 | [0,52) | Two-dimensional (2D) layered inorganic nanomaterials | MATERIAL / technical_material | 2D layered inorganic nanomaterials |
| dimension | S1 | [0,28) | Two-dimensional (2D) layered | MORPHOLOGY / technical_morphology | 2D layered morphology |
| electronic | S1 | [96,124) | unique electronic structures | MORPHOLOGY / technical_morphology | electronic structure |
| properties | S1 | [137,183) | extraordinary physical and chemical properties | PROPERTY / technical_property | physical/chemical property group |
| electronics | S1 | [195,206) | electronics | APPLICATION / application | electronics |
| opto | S1 | [208,223) | optoelectronics | APPLICATION / technical_application | optoelectronics |
| spin | S1 | [225,236) | spintronics | APPLICATION / technical_application | spintronics |
| catalysts | S1 | [238,247) | catalysts | APPLICATION / technical_application | catalysis |
| energy | S1 | [249,278) | energy generation and storage | APPLICATION / technical_application | energy generation/storage |
| sensors | S1 | [284,300) | chemical sensors | DEVICE / technical_device | chemical sensor |
| graphene | S2 | [302,310) | Graphene | MATERIAL / technical_material | graphene |
| analogues | S2 | [315,350) | related layered inorganic analogues | MATERIAL / technical_material | layered inorganic analogue class |
| application | S2 | [382,406) | gas-sensing applications | APPLICATION / technical_application | gas sensing |
| area | S2 | [424,452) | large specific surface areas | PROPERTY / technical_property | specific surface area |
| activity | S2 | [457,482) | strong surface activities | PROPERTY / technical_property | surface activity |
| materials3 | S3 | [543,573) | 2D layered inorganic materials | MATERIAL / technical_material | 2D layered inorganic nanomaterials |
| sensors3 | S3 | [578,589) | gas sensors | DEVICE / technical_device | gas sensor |
| mechanisms | S4 | [614,636) | gas-sensing mechanisms | MECHANISM / technical_mechanism | gas sensing mechanisms unspecified |
| devices | S4 | [668,687) | gas-sensing devices | DEVICE / technical_device | gas sensor |
| parameters | S5 | [711,727) | basic parameters | PROPERTY / technical_property | gas sensor parameters unspecified |
| influences | S5 | [732,749) | influence factors | OTHER / technical_other | gas sensor influence factors unspecified |
| sensors5 | S5 | [757,768) | gas sensors | DEVICE / technical_device | gas sensor |
| performance | S5 | [794,805) | performance | PERFORMANCE / technical_performance | gas sensing performance |
| application6 | S6 | [855,879) | gas-sensing applications | APPLICATION / technical_application | gas sensing |
| graphene6 | S6 | [889,897) | graphene | MATERIAL / material | graphene |
| go | S6 | [899,913) | graphene oxide | MATERIAL / material | graphene oxide |
| go_alias | S6 | [915,917) | GO | MATERIAL / material_alias | graphene oxide |
| rgo | S6 | [920,942) | reduced graphene oxide | MATERIAL / technical_material | reduced graphene oxide |
| rgo_alias | S6 | [944,947) | rGO | MATERIAL / material_alias | reduced graphene oxide |
| functional | S6 | [950,974) | functionalized GO or rGO | MATERIAL / technical_material | functionalized GO/rGO class |
| tmd | S6 | [976,1008) | transition metal dichalcogenides | MATERIAL / technical_material | transition metal dichalcogenides |
| iii | S6 | [1010,1039) | layered III-VI semiconductors | MATERIAL / technical_material | layered III-VI semiconductors |
| oxides | S6 | [1041,1061) | layered metal oxides | MATERIAL / technical_material | layered metal oxides |
| phosphorene | S6 | [1063,1074) | phosphorene | MATERIAL / technical_material | phosphorene |
| hbn | S6 | [1076,1099) | hexagonal boron nitride | MATERIAL / technical_material | hexagonal boron nitride |
| materials7 | S7 | [51,78) | layered inorganic materials | MATERIAL / technical_material | 2D layered inorganic nanomaterials |
| application7 | S7 | [82,106) | gas-sensing applications | APPLICATION / technical_application | gas sensing |

## Assertions

| Head | Relation | Tail | Polarity | Modality / scope | Qualifiers | Evidence span IDs |
| --- | --- | --- | --- | --- | --- | --- |
| materials | HAS_MORPHOLOGY | dimension | POSITIVE | ASSERTED / REVIEW_BACKGROUND |  | 3717541e-8f23-53cf-96b4-5b120c77b862 |
| materials | HAS_MORPHOLOGY | electronic | POSITIVE | ASSERTED / REVIEW_BACKGROUND |  | 3717541e-8f23-53cf-96b4-5b120c77b862 |
| materials | HAS_PROPERTY | properties | POSITIVE | ASSERTED / REVIEW_BACKGROUND |  | 3717541e-8f23-53cf-96b4-5b120c77b862 |
| sensors | USES_MATERIAL | materials | POSITIVE | ASSERTED / REVIEW_BACKGROUND |  | 3717541e-8f23-53cf-96b4-5b120c77b862 |
| materials | USED_FOR | electronics | POSITIVE | ASSERTED / REVIEW_BACKGROUND |  | 3717541e-8f23-53cf-96b4-5b120c77b862 |
| materials | USED_FOR | opto | POSITIVE | ASSERTED / REVIEW_BACKGROUND |  | 3717541e-8f23-53cf-96b4-5b120c77b862 |
| materials | USED_FOR | spin | POSITIVE | ASSERTED / REVIEW_BACKGROUND |  | 3717541e-8f23-53cf-96b4-5b120c77b862 |
| materials | USED_FOR | catalysts | POSITIVE | ASSERTED / REVIEW_BACKGROUND |  | 3717541e-8f23-53cf-96b4-5b120c77b862 |
| materials | USED_FOR | energy | POSITIVE | ASSERTED / REVIEW_BACKGROUND |  | 3717541e-8f23-53cf-96b4-5b120c77b862 |
| graphene | USED_FOR | application | POSITIVE | ASSERTED / REVIEW_BACKGROUND |  | 2e335b03-14de-5ac4-b436-c67cfa109c13 |
| graphene | HAS_PROPERTY | area | POSITIVE | ASSERTED / REVIEW_BACKGROUND |  | 2e335b03-14de-5ac4-b436-c67cfa109c13 |
| graphene | HAS_PROPERTY | activity | POSITIVE | ASSERTED / REVIEW_BACKGROUND |  | 2e335b03-14de-5ac4-b436-c67cfa109c13 |
| analogues | USED_FOR | application | POSITIVE | ASSERTED / REVIEW_BACKGROUND |  | 2e335b03-14de-5ac4-b436-c67cfa109c13 |
| analogues | HAS_PROPERTY | area | POSITIVE | ASSERTED / REVIEW_BACKGROUND |  | 2e335b03-14de-5ac4-b436-c67cfa109c13 |
| analogues | HAS_PROPERTY | activity | POSITIVE | ASSERTED / REVIEW_BACKGROUND |  | 2e335b03-14de-5ac4-b436-c67cfa109c13 |
| sensors3 | USES_MATERIAL | materials3 | POSITIVE | ASSERTED / REVIEW_SCOPE |  | 39a8a563-6053-561e-bb3c-fff573d2a434 |
| devices | HAS_MECHANISM | mechanisms | POSITIVE | ASSERTED / REVIEW_SCOPE |  | f664c07a-f398-594d-93fc-dfc9a2217824 |
| sensors5 | HAS_PROPERTY | parameters | POSITIVE | ASSERTED / REVIEW_SCOPE |  | 034db30a-4b2a-523c-be9c-22622cad8cb2 |
| sensors5 | HAS_PERFORMANCE | performance | POSITIVE | ASSERTED / REVIEW_SCOPE |  | 034db30a-4b2a-523c-be9c-22622cad8cb2 |
| graphene6 | USED_FOR | application6 | POSITIVE | ASSERTED / REVIEW_SCOPE |  | fb5460ec-be4b-56e6-a6c5-479691001538 |
| go | USED_FOR | application6 | POSITIVE | ASSERTED / REVIEW_SCOPE |  | fb5460ec-be4b-56e6-a6c5-479691001538 |
| rgo | USED_FOR | application6 | POSITIVE | ASSERTED / REVIEW_SCOPE |  | fb5460ec-be4b-56e6-a6c5-479691001538 |
| functional | USED_FOR | application6 | POSITIVE | ASSERTED / REVIEW_SCOPE |  | fb5460ec-be4b-56e6-a6c5-479691001538 |
| tmd | USED_FOR | application6 | POSITIVE | ASSERTED / REVIEW_SCOPE |  | fb5460ec-be4b-56e6-a6c5-479691001538 |
| iii | USED_FOR | application6 | POSITIVE | ASSERTED / REVIEW_SCOPE |  | fb5460ec-be4b-56e6-a6c5-479691001538 |
| oxides | USED_FOR | application6 | POSITIVE | ASSERTED / REVIEW_SCOPE |  | fb5460ec-be4b-56e6-a6c5-479691001538 |
| phosphorene | USED_FOR | application6 | POSITIVE | ASSERTED / REVIEW_SCOPE |  | fb5460ec-be4b-56e6-a6c5-479691001538 |
| hbn | USED_FOR | application6 | POSITIVE | ASSERTED / REVIEW_SCOPE |  | fb5460ec-be4b-56e6-a6c5-479691001538 |
| materials7 | USED_FOR | application7 | POSITIVE | HYPOTHETICAL / REVIEW_OUTLOOK |  | f7dafe6b-d76f-5294-a83c-3170d8b1af0c |

## Identity decisions

| Left | Label | Right | Reason |
| --- | --- | --- | --- |
| graphene | DIFFERENT | go | Distinct material forms listed by the review; functionalized class not merged with unmodified material. |
| go | DIFFERENT | rgo | Distinct material forms listed by the review; functionalized class not merged with unmodified material. |
| rgo | DIFFERENT | functional | Distinct material forms listed by the review; functionalized class not merged with unmodified material. |
| materials | SAME | materials3 | Curated source-local repetition/explicit alias; conditions and physical instances remain separate. |
| materials | SAME | materials7 | Curated source-local repetition/explicit alias; conditions and physical instances remain separate. |
| graphene | SAME | graphene6 | Curated source-local repetition/explicit alias; conditions and physical instances remain separate. |
| application | SAME | application6 | Curated source-local repetition/explicit alias; conditions and physical instances remain separate. |
| application | SAME | application7 | Curated source-local repetition/explicit alias; conditions and physical instances remain separate. |
| sensors3 | SAME | devices | Curated source-local repetition/explicit alias; conditions and physical instances remain separate. |
| sensors3 | SAME | sensors5 | Curated source-local repetition/explicit alias; conditions and physical instances remain separate. |
| go | SAME | go_alias | Curated source-local repetition/explicit alias; conditions and physical instances remain separate. |
| rgo | SAME | rgo_alias | Curated source-local repetition/explicit alias; conditions and physical instances remain separate. |

## Unresolved

# Вопросы документа

Все открытые вопросы UNRESOLVED. Они не блокировали автоматический проход. Q1/Q2/Q3 решены пользователем и находятся в adjudication_decisions.jsonl.
