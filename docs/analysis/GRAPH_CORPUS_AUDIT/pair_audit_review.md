# Независимая QA ручного аудита 30 пар

Дата: 2026-10-02. Проверены `manual_pair_audit.csv`, `manual_concept_details.csv`, `raw_pair_annotations.json`, вручную выбранный `REPRESENTED` в `scripts/analysis/graph_corpus_pair_audit.py` и соответствующие source chunks/GraphFacts в `corpus_export.json`. Все 30 pair assessments сопоставлены с доступными текстами. Они охватывают 31 уникальный документ. Это source-grounded review разметки; reviewer видел существующую разметку и labels, поэтому проверка не является вторым независимым слепым gold annotator.

QA не изменяла CSV, source annotations, scripts или production state. Во время review основной автор исправил несколько mappings и формулировок concepts; ниже отдельно описаны исходный и проверенный исправленный состояния. Анализ использует локальный PostgreSQL export с `manifest_sha256=2842cf0909f29c7850a190a5418032548e67e0e220e4b15a539ca277ffb7b8bc`; external full-text fetching не выполнялся. Прочитаны доступные abstract chunks, а не полные publisher articles.

## Проверенные механические инварианты

- 30 строк pair summary, 124 concept-pair annotations, 248 source-side anchors.
- Все проверенные `quote` в точности равны `chunk.text[unicode_start:unicode_end]`; chunk принадлежит active revision правильного document.
- Все выбранные fact IDs существуют, принадлежат правильной active revision, а decoded `to_key` равен записанному `selected_label`.
- Exact intersection существующих feature labels пуст во всех 30 парах.
- В 12 из 30 пар хотя бы одна revision не имеет GraphFacts.
- Все 30 пар относятся к общей тематической области, хотя часть разделяет только broader technology/material family или review topic. Это не 30 эквивалентных устройств/claims.

Проверка anchors подтверждает место фрагмента в сохранённом тексте. Она не доказывает, что короткий фрагмент самостоятельно подтверждает весь составной concept или что в обоих текстах одинаковы polarity, cause, numerical result и role.

## Как понимать 100/124 и исправленный supplementary tally

В исходной таблице арифметика была верна: 24 из 124 concept-pair annotations имели вручную выбранный соответствующий fact на обеих сторонах, а 100 — нет, то есть **80.645% не имели двух selected mappings**. Это не extractor recall, не действительное полное concept coverage и не causal contribution extraction к fragmentation.

После исправлений автора финальная механическая проверка таблицы дала 18 both-selected и 106 lacking-at-least-one-selected. Все 248 anchors и selected fact IDs/labels остались корректными. Это изменение демонстрирует чувствительность tally к rubric и субъективному выбору. Ни исходные 80.6%, ни исправленная доля не должны становиться заголовочным утверждением о доле «пропущенных extractor concepts».

Причины ограничения:

1. Top-30 similarities — намеренно выбранные наиболее близкие пары, не случайная выборка corpus. Одни документы повторяются, особенно zero-fact revision D092; concept-pair instances не независимы и не равны уникальным concepts.
2. Разметка не исчерпывает все допустимые technical facts источника и объединяет topics, materials, methods, analytes, positive/negative properties, broader families и иногда несколько analytes в одной строке.
3. Не установлено, какие из этих mentions обязан извлекать действующий deliberately conservative GraphFact contract. Background mentions, review scope, research methods и related materials могут намеренно не становиться standalone TechnicalFeature.
4. `REPRESENTED` — ручной выбор, а не exhaustive semantic matcher. Отсутствие выбранного fact не доказывает отсутствие подходящей информации в других labels или в provenance quote.
5. Concept может быть explicit в label, присутствовать только внутри полного fact quote, требовать antecedent из соседней строки или выводиться из broader/narrower taxonomy. Эти случаи имеют разное значение. Исходная версия местами смешивала их.
6. Corpus heterogeneity, extractor selection, label granularity и ontology interactions нельзя оценить причинными процентами из этой таблицы. Нельзя интерпретировать 80.6% как extraction contribution и оставшуюся долю как canonicalization contribution.

Поддерживаемая формулировка: «В целевой выборке 30 наиболее близких пар при ручном чтении обнаружены общие темы/concepts, но ни одна пара не разделяет exact TechnicalFeature key. Supplemental label mapping показывает разрыв между выбранными raw topics и lexical feature representation; он не является recall benchmark». Число 12 zero-fact-involved pairs дополнительно прозрачно описывает эту выборку.

## Исправления, выполненные автором после QA

Приняты ограничения: label selection только по explicit содержимому label или обоснованному narrower qualified family; без восстановления subject из surrounding quote. Удалены mappings hexagonal structure → graphene/atomic thinness, bandgap/semiconductive nature → graphene family/2D device, full recovery → NO2 sensing, chemiresistor → gas sensing и highly sensitive → comparative improved. Raw concept rank 21 расширен до transition-metal chalcogenide family; rank 22 больше не объявляет SnO2 nanoparticles там, где явно указаны SnO2 particles и secondary SnOx nanoparticles. Rank 18 graphene/gas interaction platform точнее описывает общую связь между device и mechanism texts. Rank 15 chemical anchor исправлен на полную первую sentence D056, включая TeX-bearing chemical list; его offsets повторно проверены.

Это улучшает воспроизводимость и предотвращает property-to-material false equivalence. Explicit narrower-in-label relation всё равно является **concept projection**, а не strict alias или утверждением одинаковой polarity/measurement.

## Границы rubric и принятые уточнения

| Pair / concept | Что требует осторожности | Рекомендуемая граница |
|---|---|---|
| 15, NH3/CO/NO2/NO analytes | Первоначальный короткий A anchor не включал chemical list; это исправлено и повторно проверено | Сохранить полный chemical sentence. Compound analyte topic не равен одному homogeneous analyte claim |
| 18 и 26, NO2 as discussed analyte | Автор заменил прежние sensing/detection concepts на общий analyte topic. Labels `preferential adsorption...` и `charge transfer...` явно называют NO2 | Mapping корректен для mention/topic; он не утверждает common detection/sensing performance |
| 19, gas sensing → chemiresistor-type sensor | Chemiresistor обозначает устройство chemical/resistive sensing, но label не указывает gas medium; mapping удалён | Сохранить отсутствие strict label mapping; context association можно оценивать отдельно |
| 23, improved sensing performance → highly sensitive/rapidly responding label | High performance не устанавливает comparative improvement к baseline; mapping удалён | Сохранить отсутствие strict label mapping; improvement виден в raw source, но требует comparator |
| 28, reduced graphene oxide material family | Автор заменил прежний sensor concept; labels явно сохраняют rGO material family | Mapping корректен для material family; отдельная строка gas sensors сохраняет device topic |
| 30, electronic doping (polarity retained) | Автор убрал graphene subject из общего concept; D099 label явно содержит p-doping | Mapping корректен для doping topic; n-/p-polarities остаются разными claims |
| 3, ppb detection | D057 сообщает sensitivity better than experimental limit, D067 — reported detection limit 1 ppb | Это общая ppb-scale performance тема; не равные измеренные LOD и не числовой strict alias |
| 7, response/recovery kinetics | Long recovery limitation и extremely fast recovery improvement противоположны по polarity | Разрешено одно unsigned property topic; outcomes остаются разными claims |
| 11, graphene family | Graphene oxide и graphene — family relationship; bandgap antecedent относится к sulfides/selenides, а graphene описан как semimetal | GO не alias graphene; нельзя переносить bandgap/semiconductivity на graphene через topic normalization |

Важные omitted selections при первоначальном quote-based подходе (например, D060 fact quote явно содержит NH3 adsorption/electrical resistance response, D100 optical quote содержит all-graphene subject) **не надо добавлять в исправленный label-only tally**: сами labels этих topics не сохраняют. Это evidence того, почему label-only representation и доступность concept в fact provenance нужно считать раздельно.

Для строгой последующей разметки полезно разделить `representation_level`: `explicit_label`, `typed_narrower_label`, `fact_quote_only`, `surrounding_source_only`, `none`, а также `role/polarity/certainty/comparator`. Сейчас supplementary selections можно оставить прозрачными субъективными examples, если не выдавать их за measured recall.

## Проверка всех 30 assessments

| Rank | Пара | QA темы и scope |
|---|---|---|
| 1 | D060–D078 | Molecular-doped graphene sensors подтверждены. NH3 positive response и complete no-response противоположны; shared analyte mention не общий positive claim |
| 2 | D035–D092 | DFT, doped graphene и gas adsorption подтверждены. B–N co-doping и single B/N dopants/defects — разные implementations |
| 3 | D057–D067 | Особенно близкий epitaxial/quasi-free-standing/SiC platform. Comparative sensitivity ranking и meaning of 1-ppb experimental floor различаются |
| 4 | D035–D045 | Общая computational adsorption тема. B/N individual doping и B–N co-doping нельзя сливать; gases/dopant conclusions scoped |
| 5 | D085–D092 | Общая graphene/doping/adsorption область подтверждена. Electrical response experiment и computed electronic properties не один measurement |
| 6 | D060–D092 | Graphene gas sensing, NH3/NO2 и doping есть в обоих. Molecular adsorbate doping отличается от substitutional dopants и defects |
| 7 | D046–D068 | Review metal-oxide/graphene strategy и WO3/S-rGO device связаны. Poor/slow baseline properties не equivalent superior outcomes |
| 8 | D045–D092 | Общие DFT B/N-doped graphene и adsorption topics подтверждены; не все dopants или adsorption results общие |
| 9 | D036–D086 | Graphene sensor review topic подтверждён. CNT — related material/competitor; graphite, sp2 bonding и honeycomb structure не aliases graphene |
| 10 | D060–D085 | NO2 interaction/doping и electrical response общие. NO2 dopant для NH3 sensor отличается от NO2 target analyte |
| 11 | D039–D043 | Broad materials/review overlap подтверждён. GO vs graphene и MoS2 vs chalcogenide family — broader/narrower, не strict SAME |
| 12 | D040–D064 | Очень конкретный rGO/pyrrole/NH3 overlap подтверждён. Au-electrode assembly, reduction method comparisons и performance values различаются |
| 13 | D008–D064 | rGO, room-temperature gas sensing и GO precursor подтверждены. NO и NH3 разные analytes; N-rGO и pyrrole-reduced rGO разные qualified materials |
| 14 | D019–D084 | Graphene gas-sensor review, conductivity/area/preparation совпадают тематически; две zero-fact revisions. Не утверждать одинаковую synthesis procedure |
| 15 | D056–D092 | Theory/adsorption/electronic-property overlap подтверждён полными chunks. Pristine и doped/defective models различаются; composite chemical anchor требует полного предложения |
| 16 | D014–D099 | Graphene NH3 sensing общая тема. Review of functionalization и mica/SiO2 experimental substrate comparison имеют разную scope |
| 17 | D078–D092 | Doped graphene и first-principles gas interaction есть в обоих. D078 отрицательная NH3 response не positive sensing fact |
| 18 | D078–D085 | Graphene/gas interaction platform и NO2 analyte mention подтверждены. Adsorption/charge transfer topics не автоматически detection claim; current response polarity/device modes разные |
| 19 | D008–D082 | Modified rGO sensing общая область. Nitrogen doping, sulfonation, NO, NO2/NH3 и temperature-dependent selectivity различаются |
| 20 | D014–D041 | Overlapping reviews, NH3 и room-temperature/sensing mechanisms подтверждены. Narrow NH3 review не equivalent всему multi-gas scope |
| 21 | D017–D039 | GO, phosphorene и chalcogenide-family sensing подтверждены. Corrected umbrella избегает ложного сведения всех dichalcogenides к sulfides |
| 22 | D004–D037 | Graphene/SnO2-containing particle platform подтверждён. NO2 electrical sensor и propanal CTL sensor разные mechanisms/analytes; SnOx и SnO2 distinction сохраняется |
| 23 | D013–D068 | Общая metal-oxide/graphene composite стратегия подтверждена. D013 имеет однострочный abstract: нельзя утверждать его конкретные measured properties или mechanism |
| 24 | D064–D082 | rGO/NH3/sensitivity/selectivity/fast-response topics подтверждены. Pyrrole reduction и 3D sulfonated hydrogel не aliases; D082 применяет microheater |
| 25 | D014–D078 | Functionalized graphene sensor topic есть в обоих. NH3 detection review и absence of NH3 response opposite polarity; selectivity subject/conditions не одинаковы |
| 26 | D067–D078 | Graphene NO2 sensor area и corrected NO2 analyte topic подтверждены. Epitaxial/SiC и molecular n-doped device, ppb и ppq limits различаются; adsorption mechanism не самостоятельная detection metric |
| 27 | D060–D099 | Особенно близкая graphene NH3/electrical-resistance область. NO2 molecular dopant и mica-induced p-doping разные interventions |
| 28 | D006–D068 | Corrected rGO material family, NO2 sensitivity и gas sensor topics подтверждены. Electrospun scaffold и WO3/S-rGO composite разные devices; material label не complete sensor claim |
| 29 | D011–D100 | All-graphene flexible/transparent NO2 sensing подтверждено. Self-activation without external heating и integrated heater несовместимы как одинаковый operating claim |
| 30 | D078–D099 | Graphene/doping/gas-interaction темы общие. NO-response NH3 и positive NH3 response, n-/p-doping различаются; нельзя создавать common positive NH3 sensing fact |

## Итог QA

Самый устойчивый результат выдержал проверку: среди 30 наиболее близких пар source texts имеют общие темы, а exact graph overlap равен нулю во всех 30. Общая технологическая область не требует одинаковых условий, материалов, механизмов или signed outcomes. Эти пары подходят для будущего typed concept/retrieval benchmark; они не являются gold SAME merges.

Разрыв label-level representation полезен как qualitative diagnosis, но quantitative extractor recall потребует заранее определённой eligibility policy, exhaustive independent gold annotations, role/polarity/type controls, completeness проверки mappings и репрезентативного sampling. Текущие selected-mapping percentages не заменяют этих требований.
