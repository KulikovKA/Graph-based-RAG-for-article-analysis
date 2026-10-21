# D092 — Improving gas sensing properties of graphene by introducing dopants and defects: a first-principles study

**AI draft — HUMAN_REVIEW=NOT_REVIEWED; не human gold.**

Document `ea87c55e-72ef-439c-aa6b-7285edc49095`, revision `19bedd9d-3827-402c-894b-e8ca762ecff7`, split `DEV`, rubric `pilot24-rubric-0.3-AUTO-FROZEN`.

Chunks 1; sentences 7; mentions 41; assertions 13; unique canonical triples 13; questions 2; validation PASS.

Полный AI-проход завершён. exhaustive_entities=True; exhaustive_relations=False; неразрешённые кандидаты не являются negative gold.

## Исходные frozen EvidenceChunks

### `8c72db49-9f37-4151-a3be-46a88d5af916`

SHA-256 `3cd403a29f08ece6f4d4437796b82391cb5783184abead4225be5fad86bc9f15`, section `abstract`; [0, 1191).

The interactions between four different graphenes (including pristine, B- or N-doped and defective graphenes) and small gas molecules (CO, NO, NO(2) and NH(3)) were investigated by using density functional computations to exploit their potential applications as gas sensors. The structural and electronic properties of the graphene-molecule adsorption adducts are strongly dependent on the graphene structure and the molecular adsorption configuration. All four gas molecules show much stronger adsorption on the doped or defective graphenes than that on the pristine graphene. The defective graphene shows the highest adsorption energy with CO, NO and NO(2) molecules, while the B-doped graphene gives the tightest binding with NH(3). Meanwhile, the strong interactions between the adsorbed molecules and the modified graphenes induce dramatic changes to graphene's electronic properties. The transport behavior of a gas sensor using B-doped graphene shows a sensitivity two orders of magnitude higher than that of pristine graphene. This work reveals that the sensitivity of graphene-based chemical gas sensors could be drastically improved by introducing the appropriate dopant or defect.

## Semantic self-audit

Theory context retained; no experimental temperature/LOD inferred.
Adsorption comparisons preserve gas scope; sensitivity ratio not assigned to an unspecified target.

## Mentions

| Key | Sentence | Span | Surface | Kind / role | Canonical |
| --- | --- | --- | --- | --- | --- |
| pristine | S1 | [61,69) | pristine | MATERIAL / technical_material | pristine graphene |
| b | S1 | [71,73) | B- | MATERIAL / technical_material | B-doped graphene |
| n | S1 | [77,84) | N-doped | MATERIAL / technical_material | N-doped graphene |
| defective | S1 | [89,108) | defective graphenes | MATERIAL / technical_material | defective graphene |
| co | S1 | [135,137) | CO | ANALYTE / technical_analyte | carbon monoxide |
| no | S1 | [139,141) | NO | ANALYTE / target_analyte | nitric oxide |
| no2 | S1 | [143,148) | NO(2) | ANALYTE / technical_analyte | nitrogen dioxide |
| nh3 | S1 | [153,158) | NH(3) | ANALYTE / technical_analyte | ammonia |
| dft | S1 | [187,218) | density functional computations | TECHNOLOGY / technical_technology | density functional theory |
| sensor | S1 | [262,273) | gas sensors | DEVICE / technical_device | prospective graphene gas sensor |
| adduct | S2 | [323,359) | graphene-molecule adsorption adducts | MATERIAL / technical_material | graphene–molecule adsorption adduct |
| structural | S2 | [279,289) | structural | PROPERTY / technical_property | structural properties |
| electronic | S2 | [294,315) | electronic properties | PROPERTY / technical_property | electronic properties |
| structure | S2 | [390,408) | graphene structure | MORPHOLOGY / technical_morphology | graphene structure |
| configuration | S2 | [417,451) | molecular adsorption configuration | MORPHOLOGY / technical_morphology | adsorption configuration |
| gases | S3 | [457,475) | four gas molecules | ANALYTE / technical_analyte | CO/NO/NO2/NH3 gas group |
| adsorption | S3 | [481,505) | much stronger adsorption | PERFORMANCE / technical_performance | adsorption strength |
| doped | S3 | [513,518) | doped | MATERIAL / technical_material | doped graphene class |
| defective3 | S3 | [522,541) | defective graphenes | MATERIAL / technical_material | defective graphene |
| pristine3 | S3 | [559,576) | pristine graphene | MATERIAL / technical_material | pristine graphene |
| defective4 | S4 | [582,600) | defective graphene | MATERIAL / technical_material | defective graphene |
| energy | S4 | [611,636) | highest adsorption energy | PROPERTY / technical_property | adsorption energy |
| co4 | S4 | [642,644) | CO | ANALYTE / technical_analyte | carbon monoxide |
| no4 | S4 | [646,648) | NO | ANALYTE / target_analyte | nitric oxide |
| no24 | S4 | [653,658) | NO(2) | ANALYTE / technical_analyte | nitrogen dioxide |
| b4 | S4 | [680,696) | B-doped graphene | MATERIAL / technical_material | B-doped graphene |
| binding | S4 | [707,723) | tightest binding | PERFORMANCE / technical_performance | binding strength |
| nh34 | S4 | [729,734) | NH(3) | ANALYTE / technical_analyte | ammonia |
| interaction | S5 | [751,770) | strong interactions | MECHANISM / technical_mechanism | gas–modified graphene interactions |
| modified | S5 | [810,828) | modified graphenes | MATERIAL / technical_material | modified graphene class |
| changes | S5 | [836,852) | dramatic changes | PROCESS / technical_process | electronic property change |
| electronic5 | S5 | [867,888) | electronic properties | PROPERTY / technical_property | electronic properties |
| sensor6 | S6 | [918,928) | gas sensor | DEVICE / technical_device | B-doped graphene gas sensor |
| b6 | S6 | [935,951) | B-doped graphene | MATERIAL / technical_material | B-doped graphene |
| sensitivity | S6 | [960,971) | sensitivity | PERFORMANCE / technical_performance | sensitivity |
| pristine6 | S6 | [1016,1033) | pristine graphene | MATERIAL / technical_material | pristine graphene |
| sensitivity7 | S7 | [1062,1073) | sensitivity | PERFORMANCE / technical_performance | sensitivity |
| sensor7 | S7 | [1077,1112) | graphene-based chemical gas sensors | DEVICE / technical_device | graphene chemical gas sensor |
| introduce | S7 | [1146,1190) | introducing the appropriate dopant or defect | PROCESS / technical_process | dopant/defect introduction |
| dopant | S7 | [1174,1180) | dopant | MATERIAL / technical_material | dopant unspecified |
| defect | S7 | [1184,1190) | defect | MORPHOLOGY / technical_morphology | graphene defect |

## Assertions

| Head | Relation | Tail | Polarity | Modality / scope | Qualifiers | Evidence span IDs |
| --- | --- | --- | --- | --- | --- | --- |
| sensor | USES_MATERIAL | pristine | POSITIVE | HYPOTHETICAL / COMPUTATIONAL_RESULT |  | 055089dc-901a-59c1-9125-927fb793b2d1 |
| sensor | USES_MATERIAL | b | POSITIVE | HYPOTHETICAL / COMPUTATIONAL_RESULT |  | 055089dc-901a-59c1-9125-927fb793b2d1 |
| sensor | USES_MATERIAL | n | POSITIVE | HYPOTHETICAL / COMPUTATIONAL_RESULT |  | 055089dc-901a-59c1-9125-927fb793b2d1 |
| sensor | USES_MATERIAL | defective | POSITIVE | HYPOTHETICAL / COMPUTATIONAL_RESULT |  | 055089dc-901a-59c1-9125-927fb793b2d1 |
| adduct | HAS_PROPERTY | structural | POSITIVE | ASSERTED / COMPUTATIONAL_RESULT |  | 71ceb744-39f5-59c1-9f5f-902e6b61ef0d |
| adduct | HAS_PROPERTY | electronic | POSITIVE | ASSERTED / COMPUTATIONAL_RESULT |  | 71ceb744-39f5-59c1-9f5f-902e6b61ef0d |
| doped | HAS_PERFORMANCE | adsorption | POSITIVE | COMPARED / COMPUTATIONAL_RESULT | comparison: than that on the pristine graphene → than that on the pristine graphene | 502062c5-347e-55ae-84ce-51cd211feb2d |
| defective3 | HAS_PERFORMANCE | adsorption | POSITIVE | COMPARED / COMPUTATIONAL_RESULT | comparison: than that on the pristine graphene → than that on the pristine graphene | 502062c5-347e-55ae-84ce-51cd211feb2d |
| defective4 | HAS_PROPERTY | energy | POSITIVE | COMPARED / COMPUTATIONAL_RESULT | analyte_scope: CO, NO and NO(2) molecules → CO, NO and NO(2) molecules | 56e80a3f-5194-5692-9a64-5df99818d717 |
| b4 | HAS_PERFORMANCE | binding | POSITIVE | COMPARED / COMPUTATIONAL_RESULT | analyte_scope: NH(3) → NH(3) | 56e80a3f-5194-5692-9a64-5df99818d717 |
| sensor6 | USES_MATERIAL | b6 | POSITIVE | ASSERTED / COMPUTATIONAL_RESULT |  | e3e2ae4d-a800-5e5b-a71d-ccfca06400f6 |
| sensor6 | HAS_PERFORMANCE | sensitivity | POSITIVE | COMPARED / COMPUTATIONAL_RESULT | relative_sensitivity: two orders of magnitude higher → two orders of magnitude higher; comparison: than that of pristine graphene → than that of pristine graphene | e3e2ae4d-a800-5e5b-a71d-ccfca06400f6 |
| introduce | IMPROVES | sensitivity7 | POSITIVE | HYPOTHETICAL / COMPUTATIONAL_RESULT |  | c6a7990d-cf91-5f8f-ab05-6bd5932bd5c8 |

## Identity decisions

| Left | Label | Right | Reason |
| --- | --- | --- | --- |
| pristine | DIFFERENT | b | Explicitly distinct graphene variants; do not normalize to generic graphene. |
| b | DIFFERENT | n | Explicitly distinct graphene variants; do not normalize to generic graphene. |
| n | DIFFERENT | defective | Explicitly distinct graphene variants; do not normalize to generic graphene. |
| pristine | SAME | pristine3 | Curated source-local repetition/explicit alias; conditions and physical instances remain separate. |
| pristine | SAME | pristine6 | Curated source-local repetition/explicit alias; conditions and physical instances remain separate. |
| b | SAME | b4 | Curated source-local repetition/explicit alias; conditions and physical instances remain separate. |
| b | SAME | b6 | Curated source-local repetition/explicit alias; conditions and physical instances remain separate. |
| defective | SAME | defective3 | Curated source-local repetition/explicit alias; conditions and physical instances remain separate. |
| defective | SAME | defective4 | Curated source-local repetition/explicit alias; conditions and physical instances remain separate. |
| co | SAME | co4 | Curated source-local repetition/explicit alias; conditions and physical instances remain separate. |
| no | SAME | no4 | Curated source-local repetition/explicit alias; conditions and physical instances remain separate. |
| no2 | SAME | no24 | Curated source-local repetition/explicit alias; conditions and physical instances remain separate. |
| nh3 | SAME | nh34 | Curated source-local repetition/explicit alias; conditions and physical instances remain separate. |
| electronic | SAME | electronic5 | Curated source-local repetition/explicit alias; conditions and physical instances remain separate. |
| sensitivity | SAME | sensitivity7 | Curated source-local repetition/explicit alias; conditions and physical instances remain separate. |

## Unresolved

# Вопросы документа

Все открытые вопросы UNRESOLVED. Они не блокировали автоматический проход. Q1/Q2/Q3 решены пользователем и находятся в adjudication_decisions.jsonl.

## D092-Q4 — D092

**Статья:** Improving gas sensing properties of graphene by introducing dopants and defects: a first-principles study.

Document `ea87c55e-72ef-439c-aa6b-7285edc49095`; revision `19bedd9d-3827-402c-894b-e8ca762ecff7`; split `DEV`.

**Точный оригинал:**

> The structural and electronic properties of the graphene-molecule adsorption adducts are strongly dependent on the graphene structure and the molecular adsorption configuration.

**Перевод и смысл:** Значение характеристики явно зависит от структуры, конфигурации или параметра. Словарь не выражает такую зависимость.

**Что неоднозначно/непокрыто:** Явная зависимость свойств adduct от структуры и конфигурации; текущие predicates не выражают зависимость.

A. Представить DEPENDS_ON после отдельного согласования схемы.

B. Сохранить существующую схему и учитывать как непокрытое отношение.

C. Оставить UNRESOLVED до содержательной проверки.

**Предварительное предложение:** A для DEV при подтверждении семантики; B для CALIBRATION/HOLDOUT без изменения схемы.

| Head | Proposed relation | Tail | Modality / polarity |
| --- | --- | --- | --- |
| structural | DEPENDS_ON | graphene structure | ASSERTED / POSITIVE |
| structural | DEPENDS_ON | molecular adsorption configuration | ASSERTED / POSITIVE |
| electronic properties | DEPENDS_ON | graphene structure | ASSERTED / POSITIVE |
| electronic properties | DEPENDS_ON | molecular adsorption configuration | ASSERTED / POSITIVE |

## D092-Q5 — D092

**Статья:** Improving gas sensing properties of graphene by introducing dopants and defects: a first-principles study.

Document `ea87c55e-72ef-439c-aa6b-7285edc49095`; revision `19bedd9d-3827-402c-894b-e8ca762ecff7`; split `DEV`.

**Точный оригинал:**

> Meanwhile, the strong interactions between the adsorbed molecules and the modified graphenes induce dramatic changes to graphene's electronic properties.

**Перевод и смысл:** В тексте описан причинный переход: исходный процесс/механизм приводит к указанному результату. FACILITATES не сохраняет эту более сильную формулировку.

**Что неоднозначно/непокрыто:** Source says interactions induce electronic changes; causal structure is not HAS_PROPERTY.

A. Представить CAUSES после отдельного согласования схемы.

B. Сохранить существующую схему и учитывать как непокрытое отношение.

C. Оставить UNRESOLVED до содержательной проверки.

**Предварительное предложение:** A для DEV при подтверждении семантики; B для CALIBRATION/HOLDOUT без изменения схемы.

| Head | Proposed relation | Tail | Modality / polarity |
| --- | --- | --- | --- |
| strong interactions | CAUSES | dramatic changes | ASSERTED / POSITIVE |
