# D093 — Optical Graphene Gas Sensors Based on Microfibers: A Review

**AI draft — HUMAN_REVIEW=NOT_REVIEWED; не human gold.**

Document `ed63ad4b-96aa-4ba5-a8fa-581f76e5723d`, revision `ab07453e-131f-4424-a7d8-787b08f59f40`, split `CALIBRATION`, rubric `pilot24-rubric-0.3-AUTO-FROZEN`.

Chunks 1; sentences 4; mentions 23; assertions 14; unique canonical triples 14; questions 1; validation PASS.

Полный AI-проход завершён. exhaustive_entities=True; exhaustive_relations=False; неразрешённые кандидаты не являются negative gold.

## Исходные frozen EvidenceChunks

### `9887bde2-5015-49ba-adb3-6f399019dc00`

SHA-256 `3b1e5ae3d6efecffb8eca2de86bc292ed2346e162866ef5e7a13eac4684574c0`, section `abstract`; [0, 803).

Graphene has become a bridge across optoelectronics, mechanics, and bio-chemical sensing due to its unique photoelectric characteristics. Moreover, benefiting from its two-dimensional nature, this atomically thick film with full flexibility has been widely incorporated with optical waveguides such as fibers, realizing novel photonic devices including polarizers, lasers, and sensors. Among the graphene-based optical devices, sensor is one of the most important branch, especially for gas sensing, as rapid progress has been made in both sensing structures and devices in recent years. This article presents a comprehensive and systematic overview of graphene-based microfiber gas sensors regarding many aspects including sensing principles, properties, fabrication, interrogating and implementations.

## Semantic self-audit

Atomically thick is preserved literally, without converting to an exact atomic-layer count.
Review topics are generic review scope; no invented LOD/sensitivity or specific sensing mechanism.

## Mentions

| Key | Sentence | Span | Surface | Kind / role | Canonical |
| --- | --- | --- | --- | --- | --- |
| graphene | S1 | [0,8) | Graphene | MATERIAL / technical_material | graphene |
| opto | S1 | [36,51) | optoelectronics | APPLICATION / technical_application | optoelectronics |
| mechanics | S1 | [53,62) | mechanics | APPLICATION / technical_application | mechanics |
| biochem | S1 | [68,88) | bio-chemical sensing | APPLICATION / technical_application | biochemical sensing |
| photo | S1 | [100,136) | unique photoelectric characteristics | PROPERTY / technical_property | photoelectric characteristics |
| two | S2 | [168,190) | two-dimensional nature | MORPHOLOGY / technical_morphology | two-dimensional morphology |
| film | S2 | [197,218) | atomically thick film | MATERIAL / technical_material | graphene |
| flex | S2 | [224,240) | full flexibility | PROPERTY / technical_property | flexibility |
| waveguide | S2 | [275,293) | optical waveguides | DEVICE / technical_device | optical waveguide |
| fiber | S2 | [302,308) | fibers | DEVICE / technical_device | optical fiber |
| polarizer | S2 | [353,363) | polarizers | DEVICE / technical_device | graphene photonic polarizer |
| laser | S2 | [365,371) | lasers | DEVICE / technical_device | graphene photonic laser |
| sensor | S2 | [377,384) | sensors | DEVICE / technical_device | graphene optical sensor |
| devices | S3 | [396,426) | graphene-based optical devices | DEVICE / technical_device | graphene optical device class |
| sensor3 | S3 | [428,434) | sensor | DEVICE / technical_device | graphene optical sensor |
| gas | S3 | [487,498) | gas sensing | APPLICATION / technical_application | gas sensing |
| structures | S3 | [540,558) | sensing structures | MORPHOLOGY / technical_morphology | sensing structure class |
| micro | S4 | [653,690) | graphene-based microfiber gas sensors | DEVICE / technical_device | graphene microfiber gas sensor |
| principles | S4 | [724,742) | sensing principles | MECHANISM / technical_mechanism | gas sensing principles unspecified |
| properties | S4 | [744,754) | properties | PROPERTY / technical_property | sensor properties unspecified |
| fabrication | S4 | [756,767) | fabrication | PROCESS / technical_process | microfiber gas sensor fabrication |
| interrogation | S4 | [769,782) | interrogating | PROCESS / technical_process | optical interrogation |
| implementation | S4 | [787,802) | implementations | APPLICATION / technical_application | microfiber sensor implementations |

## Assertions

| Head | Relation | Tail | Polarity | Modality / scope | Qualifiers | Evidence span IDs |
| --- | --- | --- | --- | --- | --- | --- |
| graphene | HAS_PROPERTY | photo | POSITIVE | ASSERTED / REVIEW_BACKGROUND |  | 398369a5-c677-5706-99ae-93d98db987ba |
| graphene | USED_FOR | opto | POSITIVE | ASSERTED / REVIEW_BACKGROUND |  | 398369a5-c677-5706-99ae-93d98db987ba |
| graphene | USED_FOR | mechanics | POSITIVE | ASSERTED / REVIEW_BACKGROUND |  | 398369a5-c677-5706-99ae-93d98db987ba |
| graphene | USED_FOR | biochem | POSITIVE | ASSERTED / REVIEW_BACKGROUND |  | 398369a5-c677-5706-99ae-93d98db987ba |
| film | HAS_MORPHOLOGY | two | POSITIVE | ASSERTED / REVIEW_BACKGROUND |  | cbd7d930-dcdd-5f16-b822-ee42c3f63d34 |
| film | HAS_PROPERTY | flex | POSITIVE | ASSERTED / REVIEW_BACKGROUND |  | cbd7d930-dcdd-5f16-b822-ee42c3f63d34 |
| polarizer | USES_MATERIAL | film | POSITIVE | ASSERTED / REVIEW_BACKGROUND |  | cbd7d930-dcdd-5f16-b822-ee42c3f63d34 |
| laser | USES_MATERIAL | film | POSITIVE | ASSERTED / REVIEW_BACKGROUND |  | cbd7d930-dcdd-5f16-b822-ee42c3f63d34 |
| sensor | USES_MATERIAL | film | POSITIVE | ASSERTED / REVIEW_BACKGROUND |  | cbd7d930-dcdd-5f16-b822-ee42c3f63d34 |
| sensor3 | USED_FOR | gas | POSITIVE | ASSERTED / REVIEW_BACKGROUND |  | fcc9cf28-1c79-5e8c-9876-bc191f54f7e7 |
| micro | HAS_MECHANISM | principles | POSITIVE | ASSERTED / REVIEW_SCOPE |  | 96c180e4-8154-5860-b596-0f3c52e901c4 |
| micro | HAS_PROPERTY | properties | POSITIVE | ASSERTED / REVIEW_SCOPE |  | 96c180e4-8154-5860-b596-0f3c52e901c4 |
| micro | FABRICATED_BY | fabrication | POSITIVE | ASSERTED / REVIEW_SCOPE |  | 96c180e4-8154-5860-b596-0f3c52e901c4 |
| micro | USED_FOR | implementation | POSITIVE | ASSERTED / REVIEW_SCOPE |  | 96c180e4-8154-5860-b596-0f3c52e901c4 |

## Identity decisions

| Left | Label | Right | Reason |
| --- | --- | --- | --- |
| fiber | NARROWER | waveguide | Fibers are explicitly examples of optical waveguides; not all waveguides are fibers. |
| graphene | SAME | film | Curated source-local repetition/explicit alias; conditions and physical instances remain separate. |
| sensor | SAME | sensor3 | Curated source-local repetition/explicit alias; conditions and physical instances remain separate. |

## Unresolved

# Вопросы документа

Все открытые вопросы UNRESOLVED. Они не блокировали автоматический проход. Q1/Q2/Q3 решены пользователем и находятся в adjudication_decisions.jsonl.

## D093-Q4 — D093

**Статья:** Optical Graphene Gas Sensors Based on Microfibers: A Review.

Document `ed63ad4b-96aa-4ba5-a8fa-581f76e5723d`; revision `ab07453e-131f-4424-a7d8-787b08f59f40`; split `CALIBRATION`.

**Точный оригинал:**

> Moreover, benefiting from its two-dimensional nature, this atomically thick film with full flexibility has been widely incorporated with optical waveguides such as fibers, realizing novel photonic devices including polarizers, lasers, and sensors.

**Перевод и смысл:** Материал интегрирован с оптическим устройством; INTEGRATED_IN допускает только DEVICE в качестве head.

**Что неоднозначно/непокрыто:** Graphene MATERIAL integrated with an optical waveguide; frozen INTEGRATED_IN only permits DEVICE heads.

A. Представить INTEGRATED_IN после отдельного согласования схемы.

B. Сохранить существующую схему и учитывать как непокрытое отношение.

C. Оставить UNRESOLVED до содержательной проверки.

**Предварительное предложение:** A для DEV при подтверждении семантики; B для CALIBRATION/HOLDOUT без изменения схемы.

| Head | Proposed relation | Tail | Modality / polarity |
| --- | --- | --- | --- |
| atomically thick film | INTEGRATED_IN | optical waveguides | ASSERTED / POSITIVE |
