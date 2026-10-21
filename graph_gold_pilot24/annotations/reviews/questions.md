# Открытые вопросы DEV / CALIBRATION

Все открытые вопросы UNRESOLVED. Они не блокировали автоматический проход. Q1/Q2/Q3 решены пользователем и находятся в adjudication_decisions.jsonl.

## D004-Q4 — D004

**Статья:** Microwave-Assisted Synthesis of Graphene–SnO2 Nanocomposites and Their Applications in Gas Sensors.

Document `08d58bd1-a89e-4b70-b817-821df8428bc7`; revision `5afc0eeb-3c76-40cf-99be-e70f066beb2b`; split `DEV`.

**Точный оригинал:**

> We suggest that the generation of SnO x nanoparticles and the SnO x phase in the matrix results in the formation of SnO 2 /SnO 2 homojunctions, SnO 2 /SnO x ( x < 2) heterojunctions, and SnO 2 /graphene heterojunctions, which are responsible for the excellent sensitivity of the graphene–SnO 2 nanocomposites to NO 2 gas.

**Перевод и смысл:** В тексте описан причинный переход: исходный процесс/механизм приводит к указанному результату. FACILITATES не сохраняет эту более сильную формулировку.

**Что неоднозначно/непокрыто:** Авторы предполагают образование junctions при генерации SnOx; FACILITATES не сохраняет утверждение results in.

A. Представить CAUSES после отдельного согласования схемы.

B. Сохранить существующую схему и учитывать как непокрытое отношение.

C. Оставить UNRESOLVED до содержательной проверки.

**Предварительное предложение:** A для DEV при подтверждении семантики; B для CALIBRATION/HOLDOUT без изменения схемы.

| Head | Proposed relation | Tail | Modality / polarity |
| --- | --- | --- | --- |
| generation of SnO x nanoparticles and the SnO x phase in the matrix | CAUSES | formation of SnO 2 /SnO 2 homojunctions, SnO 2 /SnO x ( x < 2) heterojunctions, and SnO 2 /graphene heterojunctions | PROPOSED / POSITIVE |

## D004-Q5 — D004

**Статья:** Microwave-Assisted Synthesis of Graphene–SnO2 Nanocomposites and Their Applications in Gas Sensors.

Document `08d58bd1-a89e-4b70-b817-821df8428bc7`; revision `5afc0eeb-3c76-40cf-99be-e70f066beb2b`; split `DEV`.

**Точный оригинал:**

> We suggest that the generation of SnO x nanoparticles and the SnO x phase in the matrix results in the formation of SnO 2 /SnO 2 homojunctions, SnO 2 /SnO x ( x < 2) heterojunctions, and SnO 2 /graphene heterojunctions, which are responsible for the excellent sensitivity of the graphene–SnO 2 nanocomposites to NO 2 gas.

**Перевод и смысл:** Авторы связывают названную структуру, свойство или процесс с объяснением наблюдаемой характеристики. Текущая схема не содержит подходящего направленного отношения с такими endpoints.

**Что неоднозначно/непокрыто:** Электронный интерфейс объясняет чувствительность; допустимого MORPHOLOGY → PERFORMANCE predicate нет.

A. Представить EXPLAINS после отдельного согласования схемы.

B. Сохранить существующую схему и учитывать как непокрытое отношение.

C. Оставить UNRESOLVED до содержательной проверки.

**Предварительное предложение:** A для DEV при подтверждении семантики; B для CALIBRATION/HOLDOUT без изменения схемы.

| Head | Proposed relation | Tail | Modality / polarity |
| --- | --- | --- | --- |
| SnO 2 /SnO 2 homojunctions | EXPLAINS | excellent sensitivity | PROPOSED / POSITIVE |
| SnO 2 /SnO x ( x < 2) heterojunctions | EXPLAINS | excellent sensitivity | PROPOSED / POSITIVE |
| SnO 2 /graphene heterojunctions | EXPLAINS | excellent sensitivity | PROPOSED / POSITIVE |

## D004-Q6 — D004

**Статья:** Microwave-Assisted Synthesis of Graphene–SnO2 Nanocomposites and Their Applications in Gas Sensors.

Document `08d58bd1-a89e-4b70-b817-821df8428bc7`; revision `5afc0eeb-3c76-40cf-99be-e70f066beb2b`; split `DEV`.

**Точный оригинал:**

> In addition, the generation of surface Sn interstitial defects is also partly responsible for the excellent NO 2 sensing performance observed in this study.

**Перевод и смысл:** Авторы связывают названную структуру, свойство или процесс с объяснением наблюдаемой характеристики. Текущая схема не содержит подходящего направленного отношения с такими endpoints.

**Что неоднозначно/непокрыто:** Частичный вклад дефектов в sensing performance; не равен общему процессу изготовления или измеренному IMPROVES.

A. Представить EXPLAINS после отдельного согласования схемы.

B. Сохранить существующую схему и учитывать как непокрытое отношение.

C. Оставить UNRESOLVED до содержательной проверки.

**Предварительное предложение:** A для DEV при подтверждении семантики; B для CALIBRATION/HOLDOUT без изменения схемы.

| Head | Proposed relation | Tail | Modality / polarity |
| --- | --- | --- | --- |
| generation of surface Sn interstitial defects | EXPLAINS | excellent NO 2 sensing performance | PROPOSED / POSITIVE |

## D060-Q4 — D060

**Статья:** Enhanced sensitivity of graphene ammonia gas sensors using molecular doping.

Document `96575fc6-1212-4cb1-889f-179dd9515854`; revision `61ce4e43-1d79-4cee-af6c-43026828532a`; split `DEV`.

**Точный оригинал:**

> Electrical characterization and Raman spectroscopy measurements on graphene field-effect transistors show that adsorption of NO2 molecules significantly increases hole concentration in graphene, which results in the observed sensitivity enhancement.

**Перевод и смысл:** Величина явно увеличивается под действием указанного фактора. Это направление изменения; оно не всегда равнозначно улучшению качества.

**Что неоднозначно/непокрыто:** Увеличение концентрации носителей — направление изменения; не тождественно улучшению качества.

A. Представить INCREASES после отдельного согласования схемы.

B. Сохранить существующую схему и учитывать как непокрытое отношение.

C. Оставить UNRESOLVED до содержательной проверки.

**Предварительное предложение:** A для DEV при подтверждении семантики; B для CALIBRATION/HOLDOUT без изменения схемы.

| Head | Proposed relation | Tail | Modality / polarity |
| --- | --- | --- | --- |
| adsorption of NO2 molecules | INCREASES | hole concentration | ASSERTED / POSITIVE |

## D060-Q5 — D060

**Статья:** Enhanced sensitivity of graphene ammonia gas sensors using molecular doping.

Document `96575fc6-1212-4cb1-889f-179dd9515854`; revision `61ce4e43-1d79-4cee-af6c-43026828532a`; split `DEV`.

**Точный оригинал:**

> Electrical characterization and Raman spectroscopy measurements on graphene field-effect transistors show that adsorption of NO2 molecules significantly increases hole concentration in graphene, which results in the observed sensitivity enhancement.

**Перевод и смысл:** Авторы связывают названную структуру, свойство или процесс с объяснением наблюдаемой характеристики. Текущая схема не содержит подходящего направленного отношения с такими endpoints.

**Что неоднозначно/непокрыто:** Адсорбция NO2 через повышение hole concentration объясняет усиление чувствительности; причинный effect не выражается ACTS_ON.

A. Представить EXPLAINS после отдельного согласования схемы.

B. Сохранить существующую схему и учитывать как непокрытое отношение.

C. Оставить UNRESOLVED до содержательной проверки.

**Предварительное предложение:** A для DEV при подтверждении семантики; B для CALIBRATION/HOLDOUT без изменения схемы.

| Head | Proposed relation | Tail | Modality / polarity |
| --- | --- | --- | --- |
| adsorption of NO2 molecules | EXPLAINS | sensitivity enhancement | ASSERTED / POSITIVE |

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

## D038-Q4 — D038

**Статья:** 3D Architectured Graphene/Metal Oxide Hybrids for Gas Sensors: A Review.

Document `6a675d0d-8256-4c8f-b2ae-7c95c1bcabf8`; revision `b6535766-c337-4abd-9925-8381f0acc7fa`; split `DEV`.

**Точный оригинал:**

> Graphene/metal oxide-based materials have been demonstrated as promising candidates for gas sensing applications due to the enhanced sensing performance and synergetic effects of the two components.

**Перевод и смысл:** В тексте механизм относится к материалу, тогда как принятый HAS_MECHANISM допускает только DEVICE. Подмена материала устройством исказила бы тип.

**Что неоднозначно/непокрыто:** Материал является носителем заявленной synergy; HAS_MECHANISM domain сейчас DEVICE.

A. Представить HAS_MECHANISM после отдельного согласования схемы.

B. Сохранить существующую схему и учитывать как непокрытое отношение.

C. Оставить UNRESOLVED до содержательной проверки.

**Предварительное предложение:** A для DEV при подтверждении семантики; B для CALIBRATION/HOLDOUT без изменения схемы.

| Head | Proposed relation | Tail | Modality / polarity |
| --- | --- | --- | --- |
| Graphene/metal oxide-based materials | HAS_MECHANISM | synergetic effects | ASSERTED / POSITIVE |

## D026-Q4 — D026

**Статья:** Metallic Ti3C2T x MXene Gas Sensors with Ultrahigh Signal-to-Noise Ratio.

Document `3df9cd7a-940f-400e-b03a-a72459a5558f`; revision `3ed28d1a-4b30-4ea4-bf03-3a69308fb8ba`; split `DEV`.

**Точный оригинал:**

> To obtain high sensitivity, two requirements need to be simultaneously satisfied: (i) low electrical noise and (ii) strong signal, which existing sensor materials cannot meet.

**Перевод и смысл:** Отрицание относится к совместному выполнению двух требований: низкий шум И сильный сигнал. Нельзя превращать его в два независимых отрицания.

**Что неоднозначно/непокрыто:** Cannot simultaneously meet low noise and strong signal: group negation must not become two independent failures.

A. Представить MEETS_REQUIREMENT после отдельного согласования схемы.

B. Сохранить существующую схему и учитывать как непокрытое отношение.

C. Оставить UNRESOLVED до содержательной проверки.

**Предварительное предложение:** A для DEV при подтверждении семантики; B для CALIBRATION/HOLDOUT без изменения схемы.

| Head | Proposed relation | Tail | Modality / polarity |
| --- | --- | --- | --- |
| existing sensor materials | MEETS_REQUIREMENT | low electrical noise | ASSERTED / NEGATIVE |

## D026-Q5 — D026

**Статья:** Metallic Ti3C2T x MXene Gas Sensors with Ultrahigh Signal-to-Noise Ratio.

Document `3df9cd7a-940f-400e-b03a-a72459a5558f`; revision `3ed28d1a-4b30-4ea4-bf03-3a69308fb8ba`; split `DEV`.

**Точный оригинал:**

> Also, the extremely low noise led to a signal-to-noise ratio 2 orders of magnitude higher than that of other 2D materials, surpassing the best sensors known.

**Перевод и смысл:** Авторы связывают названную структуру, свойство или процесс с объяснением наблюдаемой характеристики. Текущая схема не содержит подходящего направленного отношения с такими endpoints.

**Что неоднозначно/непокрыто:** Low noise led to SNR advantage; PROPERTY → PERFORMANCE causal effect cannot be replaced by HAS_PROPERTY.

A. Представить EXPLAINS после отдельного согласования схемы.

B. Сохранить существующую схему и учитывать как непокрытое отношение.

C. Оставить UNRESOLVED до содержательной проверки.

**Предварительное предложение:** A для DEV при подтверждении семантики; B для CALIBRATION/HOLDOUT без изменения схемы.

| Head | Proposed relation | Tail | Modality / polarity |
| --- | --- | --- | --- |
| extremely low noise | EXPLAINS | signal-to-noise ratio | ASSERTED / POSITIVE |

## D024-Q4 — D024

**Статья:** Porous Graphene as the Ultimate Membrane for Gas Separation.

Document `3a5a587d-5ddf-49b9-aa34-bd081fb0d04b`; revision `95f3f5a0-077c-4f5d-859f-37fc344f12f0`; split `DEV`.

**Точный оригинал:**

> We find extremely high selectivity on the order of 10(23) for H(2)/CH(4) for an all-hydrogen passivated pore whose small width (at 2.5 A) presents a formidable barrier (1.6 eV) for CH(4) but easily surmountable for H(2) (0.22 eV).

**Перевод и смысл:** Свойство явно относится к структуре MORPHOLOGY, но у HAS_PROPERTY такой тип носителя не разрешён.

**Что неоднозначно/непокрыто:** MORPHOLOGY → PROPERTY endpoint gap; keep source unit A without silent Angstrom normalization.

A. Представить HAS_PROPERTY после отдельного согласования схемы.

B. Сохранить существующую схему и учитывать как непокрытое отношение.

C. Оставить UNRESOLVED до содержательной проверки.

**Предварительное предложение:** A для DEV при подтверждении семантики; B для CALIBRATION/HOLDOUT без изменения схемы.

| Head | Proposed relation | Tail | Modality / polarity |
| --- | --- | --- | --- |
| all-hydrogen passivated pore | HAS_PROPERTY | small width | ASSERTED / POSITIVE |

## D024-Q5 — D024

**Статья:** Porous Graphene as the Ultimate Membrane for Gas Separation.

Document `3a5a587d-5ddf-49b9-aa34-bd081fb0d04b`; revision `95f3f5a0-077c-4f5d-859f-37fc344f12f0`; split `DEV`.

**Точный оригинал:**

> These results suggest that these pores are far superior to traditional polymer and silica membranes, where bulk solubility and diffusivity dominate the transport of gas molecules through the material.

**Перевод и смысл:** Названное свойство определяет преобладающий вклад в перенос молекул. Это иной смысл, чем принадлежность свойства или действие на материал.

**Что неоднозначно/непокрыто:** Transport dominated by bulk solubility/diffusivity; PROPERTY → PROCESS dominance is not FACILITATES.

A. Представить DOMINATES после отдельного согласования схемы.

B. Сохранить существующую схему и учитывать как непокрытое отношение.

C. Оставить UNRESOLVED до содержательной проверки.

**Предварительное предложение:** A для DEV при подтверждении семантики; B для CALIBRATION/HOLDOUT без изменения схемы.

| Head | Proposed relation | Tail | Modality / polarity |
| --- | --- | --- | --- |
| bulk solubility | DOMINATES | transport of gas molecules | ASSERTED / POSITIVE |
| diffusivity | DOMINATES | transport of gas molecules | ASSERTED / POSITIVE |

## D024-Q6 — D024

**Статья:** Porous Graphene as the Ultimate Membrane for Gas Separation.

Document `3a5a587d-5ddf-49b9-aa34-bd081fb0d04b`; revision `95f3f5a0-077c-4f5d-859f-37fc344f12f0`; split `DEV`.

**Точный оригинал:**

> Hence, we propose using porous graphene sheets as one-atom-thin, highly efficient, and highly selective membranes for gas separation.
> Such a pore could have widespread impact on numerous energy and technological applications; including carbon sequestration, fuel cells, and gas sensors.

**Перевод и смысл:** Указано перспективное применение материала в названном устройстве. Текущие tail kinds USED_FOR не включают DEVICE; физический состав устройства не утверждён.

**Что неоднозначно/непокрыто:** Prospective application to fuel cells; material-to-device use is outside allowed USED_FOR tails, and a physical component relation is not explicitly asserted.

A. Представить USED_FOR после отдельного согласования схемы.

B. Сохранить существующую схему и учитывать как непокрытое отношение.

C. Оставить UNRESOLVED до содержательной проверки.

**Предварительное предложение:** A для DEV при подтверждении семантики; B для CALIBRATION/HOLDOUT без изменения схемы.

| Head | Proposed relation | Tail | Modality / polarity |
| --- | --- | --- | --- |
| porous graphene sheets | USED_FOR | fuel cells | HYPOTHETICAL / POSITIVE |

## D024-Q7 — D024

**Статья:** Porous Graphene as the Ultimate Membrane for Gas Separation.

Document `3a5a587d-5ddf-49b9-aa34-bd081fb0d04b`; revision `95f3f5a0-077c-4f5d-859f-37fc344f12f0`; split `DEV`.

**Точный оригинал:**

> Hence, we propose using porous graphene sheets as one-atom-thin, highly efficient, and highly selective membranes for gas separation.
> Such a pore could have widespread impact on numerous energy and technological applications; including carbon sequestration, fuel cells, and gas sensors.

**Перевод и смысл:** Указано перспективное применение материала в названном устройстве. Текущие tail kinds USED_FOR не включают DEVICE; физический состав устройства не утверждён.

**Что неоднозначно/непокрыто:** Prospective application to gas sensors; no separately fabricated component is asserted.

A. Представить USED_FOR после отдельного согласования схемы.

B. Сохранить существующую схему и учитывать как непокрытое отношение.

C. Оставить UNRESOLVED до содержательной проверки.

**Предварительное предложение:** A для DEV при подтверждении семантики; B для CALIBRATION/HOLDOUT без изменения схемы.

| Head | Proposed relation | Tail | Modality / polarity |
| --- | --- | --- | --- |
| porous graphene sheets | USED_FOR | gas sensors | HYPOTHETICAL / POSITIVE |

## D018-Q4 — D018

**Статья:** Reduced Graphene Oxide Conjugated Cu2O Nanowire Mesocrystals for High-Performance NO2 Gas Sensor.

Document `298b9ec6-547c-4544-ad9b-1d7796ef32c1`; revision `c3e96320-21ac-4704-a4fb-19af06571af0`; split `CALIBRATION`.

**Точный оригинал:**

> The mechanisms underlying the sequential formation of the mesocrystals are as follows: first, GO-promoted agglomeration of amorphous spherical Cu(2)O nanoparticles at the initial stage, leading to the transition of growth mechanism from conventional ion-by-ion growth to particle-mediated crystallization; second, the evolution of the amorphous microspheres into hierarchical structure, and finally to nanowire mesocrystals through mesoscale transformation, where Ostwald ripening is responsible for the growth of the nanowire building blocks; third, large-scale self-organization of the mesocrystals and the reduction of GO (at high GO concentration) occur simultaneously, resulting in an integrated hybrid architecture where porous three-dimensional (3D) framework structures interspersed among two-dimensional (2D) rGO sheets.

**Перевод и смысл:** В ходе формирования меняется сам механизм роста: ion-by-ion growth переходит в particle-mediated crystallization.

**Что неоднозначно/непокрыто:** Переход growth mechanism ion-by-ion → particle-mediated; frozen types do not encode transition. Agglomeration is the stated preceding trigger, not the mechanism being transformed.

A. Представить TRANSITIONS_TO после отдельного согласования схемы.

B. Сохранить существующую схему и учитывать как непокрытое отношение.

C. Оставить UNRESOLVED до содержательной проверки.

**Предварительное предложение:** A для DEV при подтверждении семантики; B для CALIBRATION/HOLDOUT без изменения схемы.

| Head | Proposed relation | Tail | Modality / polarity |
| --- | --- | --- | --- |
| conventional ion-by-ion growth | TRANSITIONS_TO | particle-mediated crystallization | ASSERTED / POSITIVE |

## D018-Q5 — D018

**Статья:** Reduced Graphene Oxide Conjugated Cu2O Nanowire Mesocrystals for High-Performance NO2 Gas Sensor.

Document `298b9ec6-547c-4544-ad9b-1d7796ef32c1`; revision `c3e96320-21ac-4704-a4fb-19af06571af0`; split `CALIBRATION`.

**Точный оригинал:**

> The resultant mesocrystals are comprised of highly anisotropic nanowires as building blocks and possess a distinct octahedral morphology with eight {111} equivalent crystal faces.
> The mechanisms underlying the sequential formation of the mesocrystals are as follows: first, GO-promoted agglomeration of amorphous spherical Cu(2)O nanoparticles at the initial stage, leading to the transition of growth mechanism from conventional ion-by-ion growth to particle-mediated crystallization; second, the evolution of the amorphous microspheres into hierarchical structure, and finally to nanowire mesocrystals through mesoscale transformation, where Ostwald ripening is responsible for the growth of the nanowire building blocks; third, large-scale self-organization of the mesocrystals and the reduction of GO (at high GO concentration) occur simultaneously, resulting in an integrated hybrid architecture where porous three-dimensional (3D) framework structures interspersed among two-dimensional (2D) rGO sheets.

**Перевод и смысл:** В тексте механизм относится к материалу, тогда как принятый HAS_MECHANISM допускает только DEVICE. Подмена материала устройством исказила бы тип.

**Что неоднозначно/непокрыто:** Formation mechanism is attached to a MATERIAL rather than a DEVICE; frozen domain gap.

A. Представить HAS_MECHANISM после отдельного согласования схемы.

B. Сохранить существующую схему и учитывать как непокрытое отношение.

C. Оставить UNRESOLVED до содержательной проверки.

**Предварительное предложение:** A для DEV при подтверждении семантики; B для CALIBRATION/HOLDOUT без изменения схемы.

| Head | Proposed relation | Tail | Modality / polarity |
| --- | --- | --- | --- |
| mesocrystals | HAS_MECHANISM | mechanisms underlying the sequential formation | ASSERTED / POSITIVE |

## D018-Q6 — D018

**Статья:** Reduced Graphene Oxide Conjugated Cu2O Nanowire Mesocrystals for High-Performance NO2 Gas Sensor.

Document `298b9ec6-547c-4544-ad9b-1d7796ef32c1`; revision `c3e96320-21ac-4704-a4fb-19af06571af0`; split `CALIBRATION`.

**Точный оригинал:**

> Furthermore, the interior nanowire architecture of these mesocrystals can be kinetically controlled by careful variation of growth conditions.

**Перевод и смысл:** Условия роста позволяют кинетически контролировать внутреннюю архитектуру. PROCESS → MORPHOLOGY control не выражается OPTIMIZES технического объекта.

**Что неоднозначно/непокрыто:** Kinetic control of interior architecture; PROCESS → MORPHOLOGY control not expressible as OPTIMIZES DEVICE/MATERIAL.

A. Представить CONTROLS после отдельного согласования схемы.

B. Сохранить существующую схему и учитывать как непокрытое отношение.

C. Оставить UNRESOLVED до содержательной проверки.

**Предварительное предложение:** A для DEV при подтверждении семантики; B для CALIBRATION/HOLDOUT без изменения схемы.

| Head | Proposed relation | Tail | Modality / polarity |
| --- | --- | --- | --- |
| careful variation of growth conditions | CONTROLS | interior nanowire architecture | HYPOTHETICAL / POSITIVE |

## D050-Q4 — D050

**Статья:** Flexible room-temperature NO2 gas sensors based on carbon nanotubes/reduced graphene hybrid films.

Document `87775318-a9f1-457c-891c-6d910ac56175`; revision `f3937e44-f446-490b-8c4e-7b95768fca8a`; split `CALIBRATION`.

**Точный оригинал:**

> The reduced graphene film alone showed a negligible sensor response, exhibiting abnormal N–P transitions during the initial NO2 injection.

**Перевод и смысл:** В тексте механизм относится к материалу, тогда как принятый HAS_MECHANISM допускает только DEVICE. Подмена материала устройством исказила бы тип.

**Что неоднозначно/непокрыто:** Material N–P transition and initial-injection scope cannot be represented by DEVICE-only HAS_MECHANISM.

A. Представить HAS_MECHANISM после отдельного согласования схемы.

B. Сохранить существующую схему и учитывать как непокрытое отношение.

C. Оставить UNRESOLVED до содержательной проверки.

**Предварительное предложение:** A для DEV при подтверждении семантики; B для CALIBRATION/HOLDOUT без изменения схемы.

| Head | Proposed relation | Tail | Modality / polarity |
| --- | --- | --- | --- |
| reduced graphene film | HAS_MECHANISM | abnormal N–P transitions | ASSERTED / POSITIVE |

## D050-Q5 — D050

**Статья:** Flexible room-temperature NO2 gas sensors based on carbon nanotubes/reduced graphene hybrid films.

Document `87775318-a9f1-457c-891c-6d910ac56175`; revision `f3937e44-f446-490b-8c4e-7b95768fca8a`; split `CALIBRATION`.

**Точный оригинал:**

> A hybrid film, formed by the growth of a vertically aligned CNT array (with CNTs 20 μm in length) on the reduced graphene film surface, exhibited remarkably enhanced sensitivities with weak N–P transitions.

**Перевод и смысл:** В тексте механизм относится к материалу, тогда как принятый HAS_MECHANISM допускает только DEVICE. Подмена материала устройством исказила бы тип.

**Что неоднозначно/непокрыто:** Weak N–P transitions observed in hybrid material; frozen HAS_MECHANISM domain excludes MATERIAL.

A. Представить HAS_MECHANISM после отдельного согласования схемы.

B. Сохранить существующую схему и учитывать как непокрытое отношение.

C. Оставить UNRESOLVED до содержательной проверки.

**Предварительное предложение:** A для DEV при подтверждении семантики; B для CALIBRATION/HOLDOUT без изменения схемы.

| Head | Proposed relation | Tail | Modality / polarity |
| --- | --- | --- | --- |
| hybrid film | HAS_MECHANISM | weak N–P transitions | ASSERTED / POSITIVE |

## D050-Q6 — D050

**Статья:** Flexible room-temperature NO2 gas sensors based on carbon nanotubes/reduced graphene hybrid films.

Document `87775318-a9f1-457c-891c-6d910ac56175`; revision `f3937e44-f446-490b-8c4e-7b95768fca8a`; split `CALIBRATION`.

**Точный оригинал:**

> The increase in sensitivity was mainly attributed to the high sensitivity of the CNT arrays.

**Перевод и смысл:** Авторы связывают названную структуру, свойство или процесс с объяснением наблюдаемой характеристики. Текущая схема не содержит подходящего направленного отношения с такими endpoints.

**Что неоднозначно/непокрыто:** Attribution to CNT-array sensitivity is a PERFORMANCE → PERFORMANCE explanatory link, absent from frozen schema.

A. Представить EXPLAINS после отдельного согласования схемы.

B. Сохранить существующую схему и учитывать как непокрытое отношение.

C. Оставить UNRESOLVED до содержательной проверки.

**Предварительное предложение:** A для DEV при подтверждении семантики; B для CALIBRATION/HOLDOUT без изменения схемы.

| Head | Proposed relation | Tail | Modality / polarity |
| --- | --- | --- | --- |
| high sensitivity | EXPLAINS | increase in sensitivity | ASSERTED / POSITIVE |

## D050-Q7 — D050

**Статья:** Flexible room-temperature NO2 gas sensors based on carbon nanotubes/reduced graphene hybrid films.

Document `87775318-a9f1-457c-891c-6d910ac56175`; revision `f3937e44-f446-490b-8c4e-7b95768fca8a`; split `CALIBRATION`.

**Точный оригинал:**

> The outstanding flexibility of the reduced graphene films ensured stable sensing performances in devices submitted to extreme bending stress.

**Перевод и смысл:** Авторы связывают названную структуру, свойство или процесс с объяснением наблюдаемой характеристики. Текущая схема не содержит подходящего направленного отношения с такими endpoints.

**Что неоднозначно/непокрыто:** Flexibility ensures stable performance under bending; property-to-performance explanation is uncovered.

A. Представить EXPLAINS после отдельного согласования схемы.

B. Сохранить существующую схему и учитывать как непокрытое отношение.

C. Оставить UNRESOLVED до содержательной проверки.

**Предварительное предложение:** A для DEV при подтверждении семантики; B для CALIBRATION/HOLDOUT без изменения схемы.

| Head | Proposed relation | Tail | Modality / polarity |
| --- | --- | --- | --- |
| outstanding flexibility | EXPLAINS | stable sensing performances | ASSERTED / POSITIVE |

## D029-Q4 — D029

**Статья:** NO2 and NH3 Sensing Characteristics of Inkjet Printing Graphene Gas Sensors.

Document `4a17444d-09e0-4cad-becb-0ad9e9a95b73`; revision `94abe07d-65fd-4ac6-96c3-0c65e777ed09`; split `CALIBRATION`.

**Точный оригинал:**

> The presented results highlight the importance of tuning the layer thickness and achieving good film homogeneity in order to maximize the sensitivity of the sensor.

**Перевод и смысл:** Авторы связывают названную структуру, свойство или процесс с объяснением наблюдаемой характеристики. Текущая схема не содержит подходящего направленного отношения с такими endpoints.

**Что неоднозначно/непокрыто:** Importance of film homogeneity for sensitivity is a PROPERTY → PERFORMANCE effect, not a measured numeric relation.

A. Представить EXPLAINS после отдельного согласования схемы.

B. Сохранить существующую схему и учитывать как непокрытое отношение.

C. Оставить UNRESOLVED до содержательной проверки.

**Предварительное предложение:** A для DEV при подтверждении семантики; B для CALIBRATION/HOLDOUT без изменения схемы.

| Head | Proposed relation | Tail | Modality / polarity |
| --- | --- | --- | --- |
| good film homogeneity | EXPLAINS | sensitivity | ASSERTED / POSITIVE |

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

## D021-Q4 — D021

**Статья:** Synthesis, properties, and applications of graphene oxide/reduced graphene oxide and their nanocomposites.

Document `2f7fb8d1-42b1-433b-9091-7d13fc6493b1`; revision `48ba5b53-f32b-43a8-ae85-ea7232a2975d`; split `CALIBRATION`.

**Точный оригинал:**

> Herein, we review the synthesis techniques most commonly used to produce these graphene derivatives, discuss how synthesis affects their key material properties, and highlight some examples of nanocomposites with unique and impressive properties.

**Перевод и смысл:** Способ синтеза влияет на свойства материала; направление улучшения не указано, поэтому IMPROVES был бы сильнее исходного текста.

**Что неоднозначно/непокрыто:** Synthesis affects material properties without stating improvement direction; not IMPROVES.

A. Представить AFFECTS после отдельного согласования схемы.

B. Сохранить существующую схему и учитывать как непокрытое отношение.

C. Оставить UNRESOLVED до содержательной проверки.

**Предварительное предложение:** A для DEV при подтверждении семантики; B для CALIBRATION/HOLDOUT без изменения схемы.

| Head | Proposed relation | Tail | Modality / polarity |
| --- | --- | --- | --- |
| synthesis techniques | AFFECTS | key material properties | ASSERTED / POSITIVE |

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
