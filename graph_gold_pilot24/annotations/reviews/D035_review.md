# D035 — B–N@Graphene: Highly Sensitive and Selective Gas Sensor

**AI draft — HUMAN_REVIEW=NOT_REVIEWED; не human gold.**

Document `5f698fb2-5265-4343-a012-0c0fb3c6e9c4`, revision `6612f9ab-0007-4924-a4da-dc7e0bafdba3`, split `DEV`, rubric `pilot24-rubric-0.3-AUTO-FROZEN`.

Chunks 1; sentences 4; mentions 32; assertions 25; unique canonical triples 25; questions 0; validation PASS.

Полный AI-проход завершён. exhaustive_entities=True; exhaustive_relations=True; неразрешённые кандидаты не являются negative gold.

## Исходные frozen EvidenceChunks

### `4f0f0e24-163f-4d49-a509-72a2393efd6a`

SHA-256 `dc77ce8cc6bc90047c157e3478fef185677252383873f9ccd1db64ae3daab659`, section `abstract`; [0, 646).

We have performed density functional theory (DFT) calculations to study the gas (CO, CO 2, NO, and NO 2 ) sensing mechanism of pure and doped (B@, N@, and B–N@) graphene surfaces. The calculated adsorption energies of the various toxic gases (CO, CO 2, NO, and NO 2 ) on the pure and doped graphene surfaces show, doping improves adsorption energy and selectivity. The electronic properties of the B–N@graphene surfaces change significantly compared to pure and B@ and N@graphene surfaces, while selective gas molecules are adsorbed. So, we report B–N codoping on graphene can be highly sensitive and selective for semiconductor-based gas sensor.

## Semantic self-audit

DFT study, no numerical energy or device performance invented.
Distinct pristine/B/N/B,N surfaces retained; no fabricated experiment inferred.

## Mentions

| Key | Sentence | Span | Surface | Kind / role | Canonical |
| --- | --- | --- | --- | --- | --- |
| dft | S1 | [18,62) | density functional theory (DFT) calculations | TECHNOLOGY / technical_technology | density functional theory |
| mechanism | S1 | [106,123) | sensing mechanism | MECHANISM / technical_mechanism | gas sensing mechanism |
| co | S1 | [81,83) | CO | ANALYTE / target_analyte | carbon monoxide |
| co2 | S1 | [85,89) | CO 2 | ANALYTE / technical_analyte | carbon dioxide |
| no | S1 | [91,93) | NO | ANALYTE / target_analyte | nitric oxide |
| no2 | S1 | [99,103) | NO 2 | ANALYTE / technical_analyte | nitrogen dioxide |
| pure | S1 | [127,131) | pure | MATERIAL / technical_material | pristine graphene |
| b | S1 | [143,145) | B@ | MATERIAL / technical_material | B-doped graphene |
| n | S1 | [147,149) | N@ | MATERIAL / material | N-doped graphene |
| bn | S1 | [155,159) | B–N@ | MATERIAL / technical_material | B,N-codoped graphene |
| surfaces | S1 | [161,178) | graphene surfaces | MORPHOLOGY / technical_morphology | graphene surface |
| energies | S2 | [195,214) | adsorption energies | PROPERTY / technical_property | adsorption energy |
| gases | S2 | [230,241) | toxic gases | ANALYTE / technical_analyte | CO/CO2/NO/NO2 gas group |
| co_2 | S2 | [243,245) | CO | ANALYTE / target_analyte | carbon monoxide |
| co2_2 | S2 | [247,251) | CO 2 | ANALYTE / technical_analyte | carbon dioxide |
| no_2 | S2 | [253,255) | NO | ANALYTE / target_analyte | nitric oxide |
| no2_2 | S2 | [261,265) | NO 2 | ANALYTE / technical_analyte | nitrogen dioxide |
| pure2 | S2 | [275,279) | pure | MATERIAL / technical_material | pristine graphene |
| doped | S2 | [284,298) | doped graphene | MATERIAL / technical_material | doped graphene class |
| doping | S2 | [314,320) | doping | PROCESS / technical_process | graphene doping |
| energy2 | S2 | [330,347) | adsorption energy | PROPERTY / technical_property | adsorption energy |
| selectivity | S2 | [352,363) | selectivity | PERFORMANCE / technical_performance | gas selectivity |
| electronic | S3 | [369,390) | electronic properties | PROPERTY / technical_property | electronic properties |
| bn3 | S3 | [398,410) | B–N@graphene | MATERIAL / technical_material | B,N-codoped graphene |
| pure3 | S3 | [453,457) | pure | MATERIAL / technical_material | pristine graphene |
| b3 | S3 | [462,464) | B@ | MATERIAL / technical_material | B-doped graphene |
| n3 | S3 | [469,479) | N@graphene | MATERIAL / material | N-doped graphene |
| adsorb | S3 | [524,532) | adsorbed | PROCESS / technical_process | gas adsorption |
| codoping | S4 | [548,560) | B–N codoping | PROCESS / technical_process | B,N codoping |
| graphene | S4 | [564,572) | graphene | MATERIAL / technical_material | graphene |
| sensitive | S4 | [580,610) | highly sensitive and selective | PERFORMANCE / technical_performance | high sensitivity and selectivity |
| sensor | S4 | [615,645) | semiconductor-based gas sensor | DEVICE / technical_device | semiconductor-based gas sensor |

## Assertions

| Head | Relation | Tail | Polarity | Modality / scope | Qualifiers | Evidence span IDs |
| --- | --- | --- | --- | --- | --- | --- |
| doping | IMPROVES | energy2 | POSITIVE | COMPARED / COMPUTATIONAL_RESULT | epistemic_basis: calculated → calculated | 2c596287-17e9-5269-b1cc-a8f3b66c06d9 |
| doping | IMPROVES | selectivity | POSITIVE | COMPARED / COMPUTATIONAL_RESULT | epistemic_basis: calculated → calculated | 2c596287-17e9-5269-b1cc-a8f3b66c06d9 |
| gases | HAS_MEMBER | co_2 | POSITIVE | ASSERTED / COMPUTATIONAL_RESULT |  | 2c596287-17e9-5269-b1cc-a8f3b66c06d9 |
| gases | HAS_MEMBER | co2_2 | POSITIVE | ASSERTED / COMPUTATIONAL_RESULT |  | 2c596287-17e9-5269-b1cc-a8f3b66c06d9 |
| gases | HAS_MEMBER | no_2 | POSITIVE | ASSERTED / COMPUTATIONAL_RESULT |  | 2c596287-17e9-5269-b1cc-a8f3b66c06d9 |
| gases | HAS_MEMBER | no2_2 | POSITIVE | ASSERTED / COMPUTATIONAL_RESULT |  | 2c596287-17e9-5269-b1cc-a8f3b66c06d9 |
| bn3 | HAS_PROPERTY | electronic | POSITIVE | COMPARED / COMPUTATIONAL_RESULT | change: change significantly → change significantly; comparison: compared to pure and B@ and N@graphene surfaces → compared to pure and B@ and N@graphene surfaces | 2fdcda55-ad05-540b-9651-0b52cb5ee5d0 |
| bn3 | HAS_PERFORMANCE | sensitive | POSITIVE | HYPOTHETICAL / COMPUTATIONAL_RESULT |  | 2fdcda55-ad05-540b-9651-0b52cb5ee5d0; 6d4f8332-d9b3-5184-9ad9-45381c0d8d9c |
| sensor | USES_MATERIAL | bn3 | POSITIVE | HYPOTHETICAL / COMPUTATIONAL_RESULT |  | 2fdcda55-ad05-540b-9651-0b52cb5ee5d0; 6d4f8332-d9b3-5184-9ad9-45381c0d8d9c |
| pure | USED_FOR | co | POSITIVE | PROPOSED / COMPUTATIONAL_RESULT | study_method: density functional theory (DFT) calculations → density functional theory (DFT) calculations | b0a1fe2f-3b7e-5c93-bbcf-a4e163ab4fe5 |
| pure | USED_FOR | co2 | POSITIVE | PROPOSED / COMPUTATIONAL_RESULT | study_method: density functional theory (DFT) calculations → density functional theory (DFT) calculations | b0a1fe2f-3b7e-5c93-bbcf-a4e163ab4fe5 |
| pure | USED_FOR | no | POSITIVE | PROPOSED / COMPUTATIONAL_RESULT | study_method: density functional theory (DFT) calculations → density functional theory (DFT) calculations | b0a1fe2f-3b7e-5c93-bbcf-a4e163ab4fe5 |
| pure | USED_FOR | no2 | POSITIVE | PROPOSED / COMPUTATIONAL_RESULT | study_method: density functional theory (DFT) calculations → density functional theory (DFT) calculations | b0a1fe2f-3b7e-5c93-bbcf-a4e163ab4fe5 |
| b | USED_FOR | co | POSITIVE | PROPOSED / COMPUTATIONAL_RESULT | study_method: density functional theory (DFT) calculations → density functional theory (DFT) calculations | b0a1fe2f-3b7e-5c93-bbcf-a4e163ab4fe5 |
| b | USED_FOR | co2 | POSITIVE | PROPOSED / COMPUTATIONAL_RESULT | study_method: density functional theory (DFT) calculations → density functional theory (DFT) calculations | b0a1fe2f-3b7e-5c93-bbcf-a4e163ab4fe5 |
| b | USED_FOR | no | POSITIVE | PROPOSED / COMPUTATIONAL_RESULT | study_method: density functional theory (DFT) calculations → density functional theory (DFT) calculations | b0a1fe2f-3b7e-5c93-bbcf-a4e163ab4fe5 |
| b | USED_FOR | no2 | POSITIVE | PROPOSED / COMPUTATIONAL_RESULT | study_method: density functional theory (DFT) calculations → density functional theory (DFT) calculations | b0a1fe2f-3b7e-5c93-bbcf-a4e163ab4fe5 |
| n | USED_FOR | co | POSITIVE | PROPOSED / COMPUTATIONAL_RESULT | study_method: density functional theory (DFT) calculations → density functional theory (DFT) calculations | b0a1fe2f-3b7e-5c93-bbcf-a4e163ab4fe5 |
| n | USED_FOR | co2 | POSITIVE | PROPOSED / COMPUTATIONAL_RESULT | study_method: density functional theory (DFT) calculations → density functional theory (DFT) calculations | b0a1fe2f-3b7e-5c93-bbcf-a4e163ab4fe5 |
| n | USED_FOR | no | POSITIVE | PROPOSED / COMPUTATIONAL_RESULT | study_method: density functional theory (DFT) calculations → density functional theory (DFT) calculations | b0a1fe2f-3b7e-5c93-bbcf-a4e163ab4fe5 |
| n | USED_FOR | no2 | POSITIVE | PROPOSED / COMPUTATIONAL_RESULT | study_method: density functional theory (DFT) calculations → density functional theory (DFT) calculations | b0a1fe2f-3b7e-5c93-bbcf-a4e163ab4fe5 |
| bn | USED_FOR | co | POSITIVE | PROPOSED / COMPUTATIONAL_RESULT | study_method: density functional theory (DFT) calculations → density functional theory (DFT) calculations | b0a1fe2f-3b7e-5c93-bbcf-a4e163ab4fe5 |
| bn | USED_FOR | co2 | POSITIVE | PROPOSED / COMPUTATIONAL_RESULT | study_method: density functional theory (DFT) calculations → density functional theory (DFT) calculations | b0a1fe2f-3b7e-5c93-bbcf-a4e163ab4fe5 |
| bn | USED_FOR | no | POSITIVE | PROPOSED / COMPUTATIONAL_RESULT | study_method: density functional theory (DFT) calculations → density functional theory (DFT) calculations | b0a1fe2f-3b7e-5c93-bbcf-a4e163ab4fe5 |
| bn | USED_FOR | no2 | POSITIVE | PROPOSED / COMPUTATIONAL_RESULT | study_method: density functional theory (DFT) calculations → density functional theory (DFT) calculations | b0a1fe2f-3b7e-5c93-bbcf-a4e163ab4fe5 |

## Identity decisions

| Left | Label | Right | Reason |
| --- | --- | --- | --- |
| bn | DIFFERENT | b | B,N codoping is not B-only doping. |
| bn | DIFFERENT | n | B,N codoping is not N-only doping. |
| co | DIFFERENT | co2 | CO and CO2 are distinct explicitly listed analytes. |
| no | DIFFERENT | no2 | NO and NO2 are distinct explicitly listed analytes. |
| co | SAME | co_2 | Curated source-local repetition/explicit alias; conditions and physical instances remain separate. |
| co2 | SAME | co2_2 | Curated source-local repetition/explicit alias; conditions and physical instances remain separate. |
| no | SAME | no_2 | Curated source-local repetition/explicit alias; conditions and physical instances remain separate. |
| no2 | SAME | no2_2 | Curated source-local repetition/explicit alias; conditions and physical instances remain separate. |
| pure | SAME | pure2 | Curated source-local repetition/explicit alias; conditions and physical instances remain separate. |
| pure | SAME | pure3 | Curated source-local repetition/explicit alias; conditions and physical instances remain separate. |
| b | SAME | b3 | Curated source-local repetition/explicit alias; conditions and physical instances remain separate. |
| n | SAME | n3 | Curated source-local repetition/explicit alias; conditions and physical instances remain separate. |
| bn | SAME | bn3 | Curated source-local repetition/explicit alias; conditions and physical instances remain separate. |
| energies | SAME | energy2 | Curated source-local repetition/explicit alias; conditions and physical instances remain separate. |

## Unresolved

# Вопросы документа

Все открытые вопросы UNRESOLVED. Они не блокировали автоматический проход. Q1/Q2/Q3 решены пользователем и находятся в adjudication_decisions.jsonl.
