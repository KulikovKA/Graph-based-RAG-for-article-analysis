# D042 — Pt-doped armchair graphene nanoribbon as a promising gas sensor for CO and CO2: DFT study

**AI draft — HUMAN_REVIEW=NOT_REVIEWED; не human gold.**

Document `75f1a531-496e-44ff-9a26-97fd0b24dd90`, revision `fd3e8337-cb3f-46ee-b7d1-13ced4632d36`, split `CALIBRATION`, rubric `pilot24-rubric-0.3-AUTO-FROZEN`.

Chunks 2; sentences 8; mentions 51; assertions 19; unique canonical triples 15; questions 2; validation PASS.

Полный AI-проход завершён. exhaustive_entities=True; exhaustive_relations=False; неразрешённые кандидаты не являются negative gold.

## Исходные frozen EvidenceChunks

### `14dc13ed-82ff-4e60-afb9-cf5948a983fc`

SHA-256 `26664be9229a402dd1df22cb02722ace55e4b65974e71afd39352edd9071ebb0`, section `abstract`; [0, 1110).

In this work, four armchair graphene nanoribbon (AGNR) based sensor materials were built using Atomistic ToolKit Virtual NanoLab (ATK-VNL) and utilized to detect carbon monoxide (CO) and carbon dioxide (CO2) gases. First, the effect of passivating AGNR on the sensing performance toward CO and CO2 gases has been investigated, where AGNR was passivated with hydrogen (H-AGNR) and nitrogen (N-AGNR). The obtained results reflected no significant changes in the adsorption parameters of CO and CO2 molecules on H-AGNR and N-AGNR. Particularly, the adsorption energies between H-AGNR and N-AGNR systems and CO were found to be −0.446 and −0.436 eV, while for the case of CO2, the adsorption energies were found to be −0.426 and −0.432 eV, respectively. To enhance the sensing performance, both H-AGNR and N-AGNR systems were doped with platinum (Pt) forming another two systems: Pt–H-AGNR, and Pt–N-AGNR. After doping, the results revealed a significant increase in the adsorption energy to almost 9 times than the non-doped systems for the cases of CO on Pt–N-AGNR as well as CO2 on both Pt–H-AGNR and Pt–N-AGNR.

### `75b4b1e7-248b-4be4-a085-24624b89a1ef`

SHA-256 `b6cdc8531948b05755cfba526e745221729774aa6872fb2a018641fac8f9bacb`, section `abstract`; [1111, 1454).

Moreover, an increase of almost 13 times was observed in the adsorption energy for the case of CO on Pt–H-AGNR. Besides to the adsorption energy (Eads), the adsorption distance ((D), charge transfer (ΔQ), the density of states (DOS), as well as the band structure have been examined to confirm the adsorption of CO and CO2 on the four systems.

## Semantic self-audit

All four negative energies preserve respectively mapping and sign. No 9x/13x absolute energies derived.
Four modeled systems are not experimentally fabricated sensors; no significant changes is a scoped negative.
ATK-VNL is a modeling tool, not a physical synthesis method.

## Mentions

| Key | Sentence | Span | Surface | Kind / role | Canonical |
| --- | --- | --- | --- | --- | --- |
| agnr | S1 | [19,47) | armchair graphene nanoribbon | MATERIAL / technical_material | armchair graphene nanoribbon |
| alias | S1 | [49,53) | AGNR | MATERIAL / technical_material | armchair graphene nanoribbon |
| materials | S1 | [61,77) | sensor materials | MATERIAL / technical_material | four AGNR sensor-material group |
| tool | S1 | [95,138) | Atomistic ToolKit Virtual NanoLab (ATK-VNL) | TECHNOLOGY / technical_technology | ATK-VNL |
| co | S1 | [162,177) | carbon monoxide | ANALYTE / technical_analyte | carbon monoxide |
| coalias | S1 | [179,181) | CO | ANALYTE / chemical_alias | carbon monoxide |
| co2 | S1 | [187,201) | carbon dioxide | ANALYTE / technical_analyte | carbon dioxide |
| co2alias | S1 | [203,206) | CO2 | ANALYTE / technical_analyte | carbon dioxide |
| passivate | S2 | [236,252) | passivating AGNR | PROCESS / technical_process | AGNR passivation |
| performance | S2 | [260,279) | sensing performance | PERFORMANCE / technical_performance | sensing performance |
| hydrogen | S2 | [358,366) | hydrogen | MATERIAL / passivant | hydrogen passivant |
| nitrogen | S2 | [380,388) | nitrogen | MATERIAL / passivant | nitrogen passivant |
| h | S2 | [368,374) | H-AGNR | MATERIAL / technical_material | H-passivated AGNR |
| n | S2 | [390,396) | N-AGNR | MATERIAL / technical_material | N-passivated AGNR |
| changes | S3 | [433,452) | significant changes | PROCESS / technical_process | significant adsorption-parameter change |
| parameters | S3 | [460,481) | adsorption parameters | PROPERTY / technical_property | adsorption parameters |
| co3 | S3 | [485,487) | CO | ANALYTE / target_analyte | carbon monoxide |
| co23 | S3 | [492,495) | CO2 | ANALYTE / technical_analyte | carbon dioxide |
| h3 | S3 | [509,515) | H-AGNR | MATERIAL / technical_material | H-passivated AGNR |
| n3 | S3 | [520,526) | N-AGNR | MATERIAL / technical_material | N-passivated AGNR |
| energy | S4 | [546,565) | adsorption energies | PROPERTY / metric | adsorption energy |
| h4 | S4 | [574,580) | H-AGNR | MATERIAL / technical_material | H-passivated AGNR |
| n4 | S4 | [585,591) | N-AGNR | MATERIAL / technical_material | N-passivated AGNR |
| co4 | S4 | [604,606) | CO | ANALYTE / target_analyte | carbon monoxide |
| co24 | S4 | [668,671) | CO2 | ANALYTE / technical_analyte | carbon dioxide |
| doping | S5 | [822,846) | doped with platinum (Pt) | PROCESS / technical_process | Pt doping |
| pt | S5 | [833,841) | platinum | MATERIAL / dopant | platinum |
| ptalias | S5 | [843,845) | Pt | MATERIAL / dopant | platinum |
| h5 | S5 | [791,797) | H-AGNR | MATERIAL / material | H-passivated AGNR |
| n5 | S5 | [802,808) | N-AGNR | MATERIAL / material | N-passivated AGNR |
| pth | S5 | [876,885) | Pt–H-AGNR | MATERIAL / technical_material | Pt-doped H-AGNR |
| ptn | S5 | [891,900) | Pt–N-AGNR | MATERIAL / technical_material | Pt-doped N-AGNR |
| energy6 | S6 | [967,984) | adsorption energy | PROPERTY / technical_property | adsorption energy |
| co6 | S6 | [1047,1049) | CO | ANALYTE / target_analyte | carbon monoxide |
| ptn6 | S6 | [1053,1062) | Pt–N-AGNR | MATERIAL / material | Pt-doped N-AGNR |
| co26 | S6 | [1074,1077) | CO2 | ANALYTE / technical_analyte | carbon dioxide |
| pth6 | S6 | [1086,1095) | Pt–H-AGNR | MATERIAL / technical_material | Pt-doped H-AGNR |
| ptn6b | S6 | [1100,1109) | Pt–N-AGNR | MATERIAL / material | Pt-doped N-AGNR |
| energy7 | S7 | [61,78) | adsorption energy | PROPERTY / technical_property | adsorption energy |
| co7 | S7 | [95,97) | CO | ANALYTE / technical_analyte | carbon monoxide |
| pth7 | S7 | [101,110) | Pt–H-AGNR | MATERIAL / technical_material | Pt-doped H-AGNR |
| energy8 | S8 | [127,144) | adsorption energy | PROPERTY / technical_property | adsorption energy |
| eads | S8 | [146,150) | Eads | PROPERTY / technical_property | adsorption energy |
| distance | S8 | [157,176) | adsorption distance | PROPERTY / technical_property | adsorption distance |
| d_alias | S8 | [179,180) | D | PROPERTY / metric_alias | adsorption distance |
| charge | S8 | [183,198) | charge transfer | PROPERTY / technical_property | charge transfer |
| delta | S8 | [200,202) | ΔQ | PROPERTY / technical_property | charge transfer |
| dos | S8 | [209,226) | density of states | PROPERTY / technical_property | density of states |
| dosalias | S8 | [228,231) | DOS | PROPERTY / technical_property | density of states |
| band | S8 | [249,263) | band structure | PROPERTY / technical_property | band structure |
| systems | S8 | [330,342) | four systems | MATERIAL / technical_material | four AGNR sensor-material group |

## Assertions

| Head | Relation | Tail | Polarity | Modality / scope | Qualifiers | Evidence span IDs |
| --- | --- | --- | --- | --- | --- | --- |
| materials | USED_FOR | co | POSITIVE | ASSERTED / COMPUTATIONAL_RESULT | computational_tool: Atomistic ToolKit Virtual NanoLab (ATK-VNL) → Atomistic ToolKit Virtual NanoLab (ATK-VNL) | ac44e687-a1ef-5761-9d73-b4ad2830746d |
| materials | USED_FOR | co2 | POSITIVE | ASSERTED / COMPUTATIONAL_RESULT | computational_tool: Atomistic ToolKit Virtual NanoLab (ATK-VNL) → Atomistic ToolKit Virtual NanoLab (ATK-VNL) | ac44e687-a1ef-5761-9d73-b4ad2830746d |
| h | FABRICATED_BY | passivate | POSITIVE | ASSERTED / COMPUTATIONAL_RESULT | passivant: hydrogen → hydrogen | d05ea9d6-ae4c-581a-9851-1077412eacb0 |
| n | FABRICATED_BY | passivate | POSITIVE | ASSERTED / COMPUTATIONAL_RESULT | passivant: nitrogen → nitrogen | d05ea9d6-ae4c-581a-9851-1077412eacb0 |
| h4 | HAS_PROPERTY | energy | POSITIVE | ASSERTED / COMPUTATIONAL_RESULT | adsorption_energy: −0.446 → -0.446; energy_unit: −0.446 and −0.436 eV → eV; analyte: and CO were → CO | f02c20c6-514f-5528-acad-02fa70d58e9a |
| n4 | HAS_PROPERTY | energy | POSITIVE | ASSERTED / COMPUTATIONAL_RESULT | adsorption_energy: −0.436 → -0.436; energy_unit: −0.446 and −0.436 eV → eV; analyte: and CO were → CO | f02c20c6-514f-5528-acad-02fa70d58e9a |
| h4 | HAS_PROPERTY | energy | POSITIVE | ASSERTED / COMPUTATIONAL_RESULT | adsorption_energy: −0.426 → -0.426; energy_unit: −0.426 and −0.432 eV → eV; analyte: case of CO2 → CO2 | f02c20c6-514f-5528-acad-02fa70d58e9a |
| n4 | HAS_PROPERTY | energy | POSITIVE | ASSERTED / COMPUTATIONAL_RESULT | adsorption_energy: −0.432 → -0.432; energy_unit: −0.426 and −0.432 eV → eV; analyte: case of CO2 → CO2 | f02c20c6-514f-5528-acad-02fa70d58e9a |
| pth | FABRICATED_BY | doping | POSITIVE | ASSERTED / COMPUTATIONAL_RESULT |  | af584610-42af-57ad-b42e-3c6ae79529ad |
| ptn | FABRICATED_BY | doping | POSITIVE | ASSERTED / COMPUTATIONAL_RESULT |  | af584610-42af-57ad-b42e-3c6ae79529ad |
| ptn6 | HAS_PROPERTY | energy6 | POSITIVE | COMPARED / COMPUTATIONAL_RESULT | relative_energy: almost 9 times → almost 9 times; analyte: CO on Pt–N-AGNR → CO; comparison: non-doped systems → non-doped systems | 078709bf-82ab-5bda-b67c-9c963adaa9fe |
| pth6 | HAS_PROPERTY | energy6 | POSITIVE | COMPARED / COMPUTATIONAL_RESULT | relative_energy: almost 9 times → almost 9 times; analyte: CO2 on both Pt–H-AGNR and Pt–N-AGNR → CO2; comparison: non-doped systems → non-doped systems | 078709bf-82ab-5bda-b67c-9c963adaa9fe |
| ptn6b | HAS_PROPERTY | energy6 | POSITIVE | COMPARED / COMPUTATIONAL_RESULT | relative_energy: almost 9 times → almost 9 times; analyte: CO2 on both Pt–H-AGNR and Pt–N-AGNR → CO2; comparison: non-doped systems → non-doped systems | 078709bf-82ab-5bda-b67c-9c963adaa9fe |
| pth7 | HAS_PROPERTY | energy7 | POSITIVE | COMPARED / COMPUTATIONAL_RESULT | relative_energy: almost 13 times → almost 13 times; analyte: CO → CO | 2b049779-2b2b-5752-9977-59ee596c611f |
| systems | HAS_PROPERTY | energy8 | POSITIVE | ASSERTED / COMPUTATIONAL_ANALYSIS |  | 58779863-2495-5009-ab3f-19c1edb11d3b |
| systems | HAS_PROPERTY | distance | POSITIVE | ASSERTED / COMPUTATIONAL_ANALYSIS |  | 58779863-2495-5009-ab3f-19c1edb11d3b |
| systems | HAS_PROPERTY | charge | POSITIVE | ASSERTED / COMPUTATIONAL_ANALYSIS |  | 58779863-2495-5009-ab3f-19c1edb11d3b |
| systems | HAS_PROPERTY | dos | POSITIVE | ASSERTED / COMPUTATIONAL_ANALYSIS |  | 58779863-2495-5009-ab3f-19c1edb11d3b |
| systems | HAS_PROPERTY | band | POSITIVE | ASSERTED / COMPUTATIONAL_ANALYSIS |  | 58779863-2495-5009-ab3f-19c1edb11d3b |

## Identity decisions

| Left | Label | Right | Reason |
| --- | --- | --- | --- |
| h | DIFFERENT | n | Hydrogen and nitrogen passivation are separate systems. |
| h | DIFFERENT | pth | Pt-doped material not SAME as undoped H-AGNR. |
| n | DIFFERENT | ptn | Pt-doped material not SAME as undoped N-AGNR. |
| agnr | SAME | alias | Curated source-local repetition/explicit alias; conditions and physical instances remain separate. |
| materials | SAME | systems | Curated source-local repetition/explicit alias; conditions and physical instances remain separate. |
| co | SAME | coalias | Curated source-local repetition/explicit alias; conditions and physical instances remain separate. |
| co | SAME | co3 | Curated source-local repetition/explicit alias; conditions and physical instances remain separate. |
| co | SAME | co4 | Curated source-local repetition/explicit alias; conditions and physical instances remain separate. |
| co | SAME | co6 | Curated source-local repetition/explicit alias; conditions and physical instances remain separate. |
| co | SAME | co7 | Curated source-local repetition/explicit alias; conditions and physical instances remain separate. |
| co2 | SAME | co2alias | Curated source-local repetition/explicit alias; conditions and physical instances remain separate. |
| co2 | SAME | co23 | Curated source-local repetition/explicit alias; conditions and physical instances remain separate. |
| co2 | SAME | co24 | Curated source-local repetition/explicit alias; conditions and physical instances remain separate. |
| co2 | SAME | co26 | Curated source-local repetition/explicit alias; conditions and physical instances remain separate. |
| h | SAME | h3 | Curated source-local repetition/explicit alias; conditions and physical instances remain separate. |
| h | SAME | h4 | Curated source-local repetition/explicit alias; conditions and physical instances remain separate. |
| h | SAME | h5 | Curated source-local repetition/explicit alias; conditions and physical instances remain separate. |
| n | SAME | n3 | Curated source-local repetition/explicit alias; conditions and physical instances remain separate. |
| n | SAME | n4 | Curated source-local repetition/explicit alias; conditions and physical instances remain separate. |
| n | SAME | n5 | Curated source-local repetition/explicit alias; conditions and physical instances remain separate. |
| energy | SAME | energy6 | Curated source-local repetition/explicit alias; conditions and physical instances remain separate. |
| energy | SAME | energy7 | Curated source-local repetition/explicit alias; conditions and physical instances remain separate. |
| energy | SAME | energy8 | Curated source-local repetition/explicit alias; conditions and physical instances remain separate. |
| energy | SAME | eads | Curated source-local repetition/explicit alias; conditions and physical instances remain separate. |
| pt | SAME | ptalias | Curated source-local repetition/explicit alias; conditions and physical instances remain separate. |
| pth | SAME | pth6 | Curated source-local repetition/explicit alias; conditions and physical instances remain separate. |
| pth | SAME | pth7 | Curated source-local repetition/explicit alias; conditions and physical instances remain separate. |
| ptn | SAME | ptn6 | Curated source-local repetition/explicit alias; conditions and physical instances remain separate. |
| ptn | SAME | ptn6b | Curated source-local repetition/explicit alias; conditions and physical instances remain separate. |
| distance | SAME | d_alias | Curated source-local repetition/explicit alias; conditions and physical instances remain separate. |
| charge | SAME | delta | Curated source-local repetition/explicit alias; conditions and physical instances remain separate. |
| dos | SAME | dosalias | Curated source-local repetition/explicit alias; conditions and physical instances remain separate. |

## Unresolved

# Вопросы документа

Все открытые вопросы UNRESOLVED. Они не блокировали автоматический проход. Q1/Q2/Q3 решены пользователем и находятся в adjudication_decisions.jsonl.

## D042-Q4 — D042

**Статья:** Pt-doped armchair graphene nanoribbon as a promising gas sensor for CO and CO2: DFT study.

Document `75f1a531-496e-44ff-9a26-97fd0b24dd90`; revision `fd3e8337-cb3f-46ee-b7d1-13ced4632d36`; split `CALIBRATION`.

**Точный оригинал:**

> First, the effect of passivating AGNR on the sensing performance toward CO and CO2 gases has been investigated, where AGNR was passivated with hydrogen (H-AGNR) and nitrogen (N-AGNR).
> The obtained results reflected no significant changes in the adsorption parameters of CO and CO2 molecules on H-AGNR and N-AGNR.

**Перевод и смысл:** В тексте описан причинный переход: исходный процесс/механизм приводит к указанному результату. FACILITATES не сохраняет эту более сильную формулировку.

**Что неоднозначно/непокрыто:** No significant changes is the explicit result; not a blanket no adsorption/no sensing claim.

A. Представить CAUSES после отдельного согласования схемы.

B. Сохранить существующую схему и учитывать как непокрытое отношение.

C. Оставить UNRESOLVED до содержательной проверки.

**Предварительное предложение:** A для DEV при подтверждении семантики; B для CALIBRATION/HOLDOUT без изменения схемы.

| Head | Proposed relation | Tail | Modality / polarity |
| --- | --- | --- | --- |
| passivating AGNR | CAUSES | significant changes | ASSERTED / NEGATIVE |

## D042-QENERGY — D042

**Статья:** Pt-doped armchair graphene nanoribbon as a promising gas sensor for CO and CO2: DFT study.

Document `75f1a531-496e-44ff-9a26-97fd0b24dd90`; revision `fd3e8337-cb3f-46ee-b7d1-13ced4632d36`; split `CALIBRATION`.

**Точный оригинал:**

> Particularly, the adsorption energies between H-AGNR and N-AGNR systems and CO were found to be −0.446 and −0.436 eV, while for the case of CO2, the adsorption energies were found to be −0.426 and −0.432 eV, respectively.
> After doping, the results revealed a significant increase in the adsorption energy to almost 9 times than the non-doped systems for the cases of CO on Pt–N-AGNR as well as CO2 on both Pt–H-AGNR and Pt–N-AGNR.
> Moreover, an increase of almost 13 times was observed in the adsorption energy for the case of CO on Pt–H-AGNR.

**Перевод и смысл:** Начальные энергии отрицательные. Последующее increase в 9/13 раз не определяет, сравнивают ли авторы модуль энергии или её signed value. Численные eV значения не вычислялись из этих факторов.

**Что неоднозначно/непокрыто:** Negative initial energies and subsequent increase by almost 9/13 times do not specify signed-value versus magnitude convention; literal ratios retained without converting to new eV values.

A. Читать increase как рост модуля энергии связывания.

B. Читать increase как арифметический рост signed energy.

C. Сохранить буквальные factors без нормализации.

**Предварительное предложение:** C
