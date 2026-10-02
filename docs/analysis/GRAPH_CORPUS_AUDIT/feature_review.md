# Полный аудит типов и гранулярности 409 TechnicalFeatures

Проверка 2026-10-02, тот же frozen snapshot `5b80378fa2d8312951446fcbb3ada7994d775f13d452ff08fd415377a5fcade0`. Сначала прочитаны source EvidenceChunks всех 100 документов из PostgreSQL export, затем labels с исходными quotes. Базы и исходные GraphFacts не изменялись.

**Покрытие: все 409 unique feature identities / 417 facts**, а не keyword sample. `feature_type_audit.csv` и `feature_granularity_sample.csv` содержат одинаковую полную таблицу: основной и дополнительные semantic kinds, granularity, признаки неоднозначности/слишком специфичной фразы/обрезки, полный feature key, document и GraphFact IDs, исходную quote и chunk ID. Feature IDs F001–F409 назначены по сортировке frozen raw feature texts. Document codes D001–D100 следуют порядку `corpus_export.json`.

## Метод и границы достоверности

Каждый label рассмотрен индивидуально AI-архитектором с уже прочитанными реальными текстами и доступной quote. Код лишь переносит **явно назначенные вручную списки feature IDs** в CSV и проверяет покрытие/дубликаты; семантического keyword classifier или length threshold для назначения типов/гранулярности нет. Это **одна экспертная AI-разметка**, не независимый gold от нескольких людей: повторная предметная adjudication может изменить пограничные labels, и точные проценты не следует выдавать за объективный стандарт онтологии.

Primary kind — доминирующий смысл label в source context. PROPERTY означает внутреннее физическое/химическое/функциональное свойство; PERFORMANCE — sensing/device result или показатель эффективности. Например optical transparency — PROPERTY, detection limit — PERFORMANCE. MORPHOLOGY — геометрия/размер/кристаллическая организация; MATERIAL — состав/семейство материала/субстрат; PROCESS — синтез/нанесение/модификация; TECHNOLOGY — аналитический/вычислительный метод или прикладная технологическая область; DEVICE — сенсор/аппарат/элемент; ANALYTE — газ/смесь для обнаружения; OPERATING_CONDITION — температура/испытательная концентрация/среда/режим. OTHER — vague/economic claims. Один primary kind нужен для неперекрывающегося распределения; `secondary_kinds` явно сохраняет содержание сложных phrases.

Granularity:

- ATOMIC_NARROW — один устойчивый именованный concept, включая обычные составные названия (room temperature, density of states, reduced graphene oxide, atomic force microscopy).
- QUALIFIED_CONCEPT — один concept с rating, analyte/material/condition qualifier, конкретным составом/числом/сравнением. Длинный корректный материал или прибор автоматически не считается proposition.
- PROPOSITION — clause/результат/каузальное утверждение, для представления которого нужны несколько slots/relations; сюда включены подтверждённые обрезанные clauses.
- `over_specific_phrase=true` отдельно отмечает 20 слишком детализированных QUALIFIED_CONCEPT phrases. Поэтому для вопроса «propositions **или** overly specific phrases» нужно объединять этот флаг с PROPOSITION.

Различие PROPERTY/PERFORMANCE и MATERIAL/MORPHOLOGY зависит от контекста. Например sensor stability vs intrinsic material stability, nanofiber composition vs shape. В CSV отражены явные дополнительные kinds, но это не исчерпывающая многоосевая онтология. Для shared labels показана короткая representative quote, а все fact IDs позволяют сверить другие occurrences; наличие общего label не гарантирует одинаковый role каждого occurrence.

## Semantic kind distribution

| Primary kind | Features | % от 409 |
|---|---:|---:|
| PERFORMANCE | 109 | 26.65 |
| PROPERTY | 84 | 20.54 |
| MATERIAL | 51 | 12.47 |
| PROCESS | 37 | 9.05 |
| DEVICE | 33 | 8.07 |
| MORPHOLOGY | 32 | 7.82 |
| MECHANISM | 18 | 4.40 |
| TECHNOLOGY | 18 | 4.40 |
| OPERATING_CONDITION | 12 | 2.93 |
| ANALYTE | 10 | 2.44 |
| OTHER | 5 | 1.22 |
| **Всего** | **409** | **100.00** |

68 labels (16.63%) явно соединяют несколько semantic kinds. Смешение присутствует и между отдельными nodes: в одном плоском TechnicalFeature одновременно встречаются `graphene`, `NO2`, `22 °C`, `hydrothermal method`, `watch`, `high sensitivity` и причинные clauses. Поэтому flat equivalence между любыми двумя близкими labels — некорректный общий способ строить связи. Material↔property, material↔mechanism, sensor↔condition обычно требует typed relation, а не SAME merge.

## Granularity distribution

| Granularity | Features | % |
|---|---:|---:|
| ATOMIC_NARROW | 101 | 24.69 |
| QUALIFIED_CONCEPT | 270 | 66.01 |
| PROPOSITION | 38 | 9.29 |

Из 270 qualified phrases 20 отмечены как overly specific (4.89% всего). Значит, укрупнённое распределение по запрошенным категориям: **101 atomic/narrow (24.69%), 250 прочих qualified (61.12%), 58 propositions/overly specific (14.18%)**. Это оценка по rubric, не результат автоматической проверки длины. Средняя длина label — 5.313 whitespace-separated tokens, max26; max160 Unicode chars. Длина сама по себе не показывает качество.

36 labels (8.80%) требуют исходной quote для правильного прочтения роли/параметра. Примеры: `160 ppb`, `25 ppm`, `33 in 2 s`, `about an order of magnitude`, `almost 9 times`, `>60% in the visible region`, `up to 80%`, `∼1400 ppb`. Число без parameter name, analyte, baseline и unit context плохо подходит как переносимая концептуальная identity. Quotes сохраняют evidence; label не сохраняет достаточный semantic role.

## Подтверждённая обрезка и чрезмерная детализация

| Feature | Source | Frozen label tail | Продолжение в source quote | Значение |
|---|---|---|---|---|
| F235 | D010 | `...p-type ti 3 c` | `Ti 3 C 2 Tx Mxene` | Chemical composition оборвана внутри формулы |
| F370 | D069 | `...90% response within 60 s at 1` | `at 1000 ppm and 80% recovery within 90 s...` | Значение концентрации отрезано до первой цифры |
| F385 | D076 | `...emitting current ∼4` | `∼470 μA cm−2 at 3 V μm−1` | Значение тока/единица/условие отрезаны |

Три labels (0.73%) имеют подтверждённую смысловую обрезку, согласующуюся с ограничением target <=160 chars. Это не доказательство parser truncation: source quotes содержат продолжение. Exact-substring validator допускает такой prefix и не проверяет целостность chemical formula/числового токена. Это существенный локальный defect feature representation, даже при правильном цитировании.

Не все длинные features ошибочны: F047 длиной157 chars — полное сложное название sensor/material/fabrication сочетания; F372 длиной153 chars — полное предложение о sensing performance. Однако использование таких целых assertions как shared node identity почти гарантирует singleton даже у тематически близких работ. Корректное будущее представление: separate material/process/performance slots плюс qualifier/value/units/condition и provenance.

Примеры propositions:

- F133 D061: graphene buffer transports electrons from Cu for Pd nucleation — mechanism + material + process.
- F235 D010: modulation of p–n heterojunctions via accumulation/depletion layers — mechanism и carrier/material roles.
- F368 D076: nanorod diameter/density can be tuned by seed-solution concentration — morphology + process control.
- F378 D026: Ti3C2Tx sensors exhibit detection limit50–100 ppb for VOCs at room temperature — device + performance + analyte + condition.

Эти утверждения могут быть верными и полезными, но exact sentence-as-feature не заменяет общий concept graph.

## Реальные lexical alias opportunities и ограничения merge

После чтения texts следующие feature contrasts выглядят как aliases либо очевидные presentation variants и заслуживают отдельного typed resolution review:

| Features | Source docs | Role |
|---|---|---|
| F206 `laser-induced graphene` / F207 `laser-induced graphene (lig)` | D094 / D070 | Material name/acronym |
| F277 `polyimide substrate` / F278 `polyimide substrates` | D050 / D070,D094 | Singular/plural substrate |
| F250 `nh(3)` / F251 `nh3` | D088 / D063 | Chemical notation |
| F253 `no(2)` / F254 `no2` | D088 / D063 | Chemical notation |
| F209 `light weight` / F210 `lightweight` | D001 / D058 | Lexical form of property |
| F382 `transparency` / F383 `transparent` | D011 / D002 | Noun/adjective property wording |
| F324 `scanning electron microscopy` / F325 `scanning electron microscopy (sem)` | D083 / D066 | Method/acronym |

Это evidence of **существования** canonicalization opportunities, не оценка их числа во всём корпусе. Qualified `high sensitivity` / `high sensitivity to NO2` / `high sensitivity to gas adsorption` нельзя объединять в одну strict identity, теряя analyte/scope; можно связывать через общий Property concept и сохранять qualification. `high selectivity` / `low selectivity` требуют общей оси свойства, а не SAME. `repeatable` и `sensor-to-sensor reproducible` различают repeatability и cross-device reproducibility; source D079 перечисляет их отдельно.

F405 `x-ray photoelectron microscopy (xps)` воспроизводит формулировку D066, тогда как F406 — `x-ray photoelectron spectroscopy` D083. Вероятный terminological source error нельзя выдавать за ошибку extractor или молча исправлять authoritative quote. Семантический слой может предложить alias с review/evidence, сохранив source text.

## Связь с причинами фрагментации

Многообразие semantic kinds, 66% qualified labels, 14.18% propositions/overly specific phrases и explicit aliases объясняют, почему exact feature identity не отображает все связи между papers. Это совместимо с ontology/canonicalization contribution. Основной extraction contribution требует отдельной таблицы raw shared concepts: многие source papers явно обсуждают материалы, gas sensing и mechanisms, но один `graphene` node присутствует только в D043. Такая неравномерность видимости общих concepts не исправляется merge только существующих 409 labels.

Приведённые доли — **доли labels**, не причинные проценты потери графовых связей. Нельзя заключить «14% fragmentation вызвано гранулярностью» или точно разложить причинный вклад без разметки source concept opportunities и контрфактического extraction/normalization comparison. Density не является target quality metric. Полезные критерии — сохранение смысла/provenance и retrieval evidence quality для научных вопросов.
