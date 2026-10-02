# Диагноз фрагментации frozen corpus

Дата: 2026-10-02. Вывод сделан после чтения реальных PostgreSQL EvidenceChunks всех 100 документов, измерения существующих document vectors и независимого разбора ближайших пар, zero-fact документов, features и pinned implementation. Никакой production replay или semantic merge не выполнен.

**CASE E — MIXED. Основные ограничения: ontology/representation и selective extraction/coverage; дополнительно lexical canonicalization и реальные различия конкретных claims. Corpus-limited-only не объясняет почти полное отсутствие тематических связей в этом corpus.** Это не утверждение, что разные устройства имеют одинаковые технические признаки или численные результаты.

## Что действительно исследовано

Manifest `data/checkpoints/graph002-live-20261002.snapshot.json`, snapshot hash `5b80378fa2d8312951446fcbb3ada7994d775f13d452ff08fd415377a5fcade0`, frozen 2026-10-02 02:17:52 по Москве. Проверены 100 document/revision pairs, 417 frozen fact IDs и endpoints в PostgreSQL. Реальные тексты взяты из repeatable-read read-only транзакции PostgreSQL, не из feature labels или нового source download.

100 OpenAlex articles, 100 revisions, 136 abstract chunks. Полных текстов статей в доступном normalized corpus нет. Все 136 chunk SHA-256 совпадают, Unicode slice offsets соответствуют normalized sections; все nonwhitespace символы abstracts покрыты chunks. Все 417 facts имеют согласованные revision/chunk spans и normalized target substring в quote. Это проверка происхождения и representation, не независимая оценка истинности научного утверждения.

Neo4j прочитан только через MATCH/RETURN в read session: 100 ScientificWork + 409 TechnicalFeature = **509 baseline nodes**, 417 DISCLOSES_FEATURE edges; fact IDs и endpoints совпадают с PostgreSQL. Число 498 в исходной статистике означает только incident vertices: 89 документов с фактами + 409 features. Одиннадцать zero-fact document nodes фактически присутствуют в Neo4j.

## Evidence против corpus-limited-only

Индуктивная primary-topic разметка даёт 13 групп, из которых 87 документов относятся к gas sensing/adsorption и 13 — к смежным material/physics/sensor/membrane темам. Большие повторяющиеся семьи: oxide/graphene hybrids 14, flexible/integrated devices 13, electronic reduction/doping/interface studies 15, first-principles/mechanism works 11, gas-sensor reviews 20. Число групп зависит от рубрики, это не объективная уникальная кластеризация.

По существующим 1024d chunk embeddings NN median=0.777574, p75=0.807553, p90=0.835865, p95=0.855277. Все 4,950 document pairs: median=0.600321. Внутри primary clusters mean=0.669826 против 0.583871 между ними; 60/100 top-1 neighbors лежат в той же primary группе. Остальные 40 не являются автоматически другой технологией: primary groups разделяют материал, метод, review/device purpose, а secondary concepts пересекаются. Сходство не переводится в probability SAME.

Pooling sensitivity: character-length-weighted chunk means дают NN median=0.781297; 82/100 top-1 и 26/30 top pairs совпадают с equal-chunk вариантом. Primary результаты и pair selection явно зафиксированы; short residual chunks могут менять отдельные rankings.

**Все 30 ближайших distinct пар (31 документ) аналитически прочитаны до просмотра feature labels. Во всех 30 есть source-supported общая техническая тема; во всех 30 exact feature overlap=0.** 12 пар включают хотя бы один zero-fact документ; 18 пар состоят из двух документов с фактами. Это strong mismatch между thematic/concept similarity и exact-feature graph. Выборка целенаправленно состоит из ближайших пар; она не даёт prevalence или recall для всех 100 документов.

В frozen reference metadata есть 406 directed in-corpus citations после удаления трёх self-references. Undirected citation components: 99 + 1 документов. Это подтверждает полезность отдельного citation navigation channel; citation не является evidence одинакового материала, признака или поддержки claim.

## Где теряются связи: конкретные примеры

| Пара | Cosine | Общие concepts в abstract | Что реально видит raw graph | Импликация |
|---|---:|---|---|---|
| D060–D078 | 0.885447 | graphene sensors, molecular doping, NO2/NH3 interactions | D060: три numeric/comparative labels; D078: три mechanistic/device clauses; shared=0 | Общая тема видна, но NH3 response различается по polarity; нужна роль, не merge |
| D035–D092 | 0.881460 | DFT, doped graphene, adsorption energy, gases | D035: `b–n codoping on graphene`; D092: 0 facts | Canonicalization не восстановит отсутствующий concept/fact |
| D057–D067 | 0.855277 | epitaxial/quasi-free-standing graphene, SiC, NO2, ppb | D057: comparative sensitivity/Fermi energy; D067: sensitivity/response/detection limit; shared=0 | Общая platform/axis при разных conditions/results, ontology slots необходимы |
| D040–D064 | 0.827307 | rGO, pyrrole reduction, NH3, repeatability | D040: только `>10 μm`; D064: 0 facts | Выраженная selective coverage gap, а не только aliases |
| D019–D084 | 0.824843 | graphene gas sensing, surface area, conductivity | Оба review, оба 0 facts | Законный strict-disclosure zero совместим с полезными MENTIONS |
| D017–D039 | 0.808311 | 2D gas sensors, GO, chalcogenides, phosphorene | D017: surface properties; D039: bandgap/semiconductive nature/surface ratio | Material/topic names не представлены как common concept identity |
| D004–D037 | 0.807300 | graphene/SnO2 particle/composite platform | Различные morphology/process/performance propositions, shared=0 | NO2 versus propanal и electrical versus CTL нельзя потерять |
| D011–D100 | 0.801927 | all-graphene sensor, transparency/flexibility, bending, NO2 | `transparency`, `flexibility`, `bending strain` versus numeric optical/kinetic/bending phrases | Общие dimensions требуют qualification-preserving links; heating role различается |

В [manual_pair_audit.csv](manual_pair_audit.csv) представлены все 30 пар, а [manual_concept_details.csv](manual_concept_details.csv) содержит 124 topic annotations с 248 exact source anchors/chunk IDs/Unicode offsets. После peer QA выбран explicit-label-only mapping: topic явно назван label или его narrower qualified family; surrounding quote не используется для восстановления antecedent. Supplemental 18 both-selected / 106 отсутствующих selected mappings не являются extractor recall, true coverage или causal percentages. Quotes могут содержать больше concepts, чем labels, а rubric boundary остаётся экспертным.

## Ontology и granularity

Индивидуально рассмотрены **все 409 features**, после source reading. По одной AI-экспертной рубрике: PERFORMANCE109, PROPERTY84, MATERIAL51, PROCESS37, DEVICE33, MORPHOLOGY32, MECHANISM18, TECHNOLOGY18, OPERATING_CONDITION12, ANALYTE10, OTHER5. 68 labels смешивают несколько kinds. Это явное смешение принципиально разных семантических объектов под одним TechnicalFeature.

101 atomic/narrow (24.69%), 270 qualified (66.01%), 38 propositions (9.29%). Среди qualified ещё 20 overly specific: объединённо 58 propositions/overly-specific phrases (14.18%). 36 labels требуют quote context, в том числе bare numbers, concentration/response fragments и comparative multipliers. Они могут иметь хорошую evidence quote, но плохую переносимую node identity.

Три labels подтверждённо обрезаны внутри химического/числового содержания: F235 D010 `...p-type ti 3 c`; F370 D069 `...90% response within 60 s at 1`; F385 D076 `...emitting current ∼4`. Source quotes содержат полное продолжение. Это дефект representation; конкретный runtime mechanism не доказан. Prefix совместим с target length limit и всё ещё проходит substring provenance validation. Остальные длинные labels не следует считать ошибочными автоматически.

Полные counts, source examples и ambiguous cases: [feature_review.md](feature_review.md). Это single-rater AI annotation, не human multi-annotator ontology gold.

## Extraction и zero facts

Все 11 zero-fact revisions indexed, имеют completed extraction state, nonempty abstract и полное nonwhitespace chunk coverage. Поэтому absent text и потеря normalized text при chunking не объясняют эти 11.

Разбор: D013 — sparse generic source; D019/D023/D041/D048/D059/D084 — review/roadmap scope, conservative zero правдоподобен; D007/D064/D092 — конкретные explicit candidates, high-priority coverage gaps; D015 — retrospective methods с неоднозначной disclosure policy. Details и candidate offsets в [zero_fact_audit.csv](zero_fact_audit.csv), [zero_fact_review.md](zero_fact_review.md).

Persisted completed state не различает model-empty, confidence filtering, invalid draft или quote-uniqueness rejection. По коду invalid drafts могут быть silently discarded. Фактическая cause каждого zero без raw outputs/reject traces не установлена; error/truncation всех 11 не утверждается. Некоторые zeros разумны для strict disclosure, но не для topic discovery: эти задачи следует разделить.

## Canonicalization contribution

Существуют реальные lexical opportunities: `transparency`/`transparent`, `light weight`/`lightweight`, `polyimide substrate`/`polyimide substrates`, `laser-induced graphene`/`laser-induced graphene (lig)`, `nh(3)`/`nh3`, `no(2)`/`no2`, SEM/acronym variants. Это доказывает существование alias splitting, но не число безопасных merges в 409 nodes.

GRAPH-002 v1: 2,255 candidates, threshold0.95 даёт net merges0; threshold0.90 sensitivity — только3. CAL v2 на purposive143 labeled pairs не проходит strict SAME precision>=0.95: 19/56 strict3, 16/49 five-class; strict3 при0.95 принял3 и всеfalse. Эти данные нельзя переносить на v1 или всю pair population; gold rubric тоже требует повторной adjudication. Поднятие threshold не устранило ошибки related/property/material equality на этой выборке.

Следовательно, безопасная canonicalization нужна лишь для typed genuine aliases. Она не может заменить omission recovery, hierarchy, material–property relations или scoped performance claims. Значительное число RELATED/BROADER_NARROWER в CAL — аргумент сохранять разные отношения, не превращать их в SAME.

## Почему именно 409 features / 417 edges

Identity — normalized lexical target phrase, часто qualified/propositional. После conservative selection vocabulary почти не переиспользуется: 403 features degree1, пять degree2 и один degree4. Shared features=6/409=1.467%, дополнительные incidences=(5×1)+(1×3)=8. Distinct document pairs со shared feature=11 из4,950; 92 document components, largest4. Exact detailed claims объективно могут различаться; большинство source/topic связей этой identity не представлены.

4.09=409/100 — глобально уникальные labels на corpus document; **actual mean features per document=417/100=4.17**. 4.685=417/89 — edges на fact-bearing document. Это исправляет знаменатели, не улучшает graph quality.

## Вклад факторов, серьёзность и границы вывода

| Фактор | Оценка роли по evidence | Чего данные не доказывают |
|---|---|---|
| Ontology/representation | Основной: flat kinds, qualified/clauses, missing roles, base-concept identity | Точный процент lost links без контрфактической projection |
| Selective extraction/policy/validation | Основной: конкретные zero cases и missing source concepts; 12/30 selected pairs имеют zero side | Разложение model versus validator versus intentional background filtering |
| Lexical canonicalization | Вторичный, реальный: конкретные alias-like variants | Общую долю безопасных merges или candidate recall |
| Corpus heterogeneity | Реальна: 13 peripheral/adjacent docs, различия analyte/material/conditions/claim polarity внутри core | Что 87 core documents тематически изолированы |

Процент причинного вклада этих факторов честно не идентифицируется: причины взаимодействуют, corpus/source concept gold неполон, а extraction/typed/alias interventions не выполнялись. Приведённые label/pair proportions — descriptive sample evidence, не проценты causality. Приблизительное приоритетное ранжирование: ontology + selective coverage в первую очередь; safe lexical aliases во вторую; corpus-periphery влияет на локальные связи, не объясняя полную thematic fragmentation.

Серьёзность **высокая, если graph должен находить и сравнивать технические аналоги**. Для текущего evidence registry проблема умеренная: exact provenance сохранена и vector search даёт semantic discovery, но downstream quality в этом аудите не измерялась. Сохранять sparse exact-claim graph разумно; целиться в density не нужно. Целиться в source-grounded comparison dimensions и retrieval usefulness — нужно, если это задача диплома.

Уверенность высокая в scope/counts/source preservation, sparse baseline и невидимости shared themes у nearest sample; умеренно высокая в mixed architectural diagnosis; средняя в single-rater type/cluster boundaries; низкая в индивидуальных runtime causes и количественном retrieval gain вариантов. Не сделан вывод о полном тексте статей или универсальном качестве scientific extraction.

Следующие данные: independent subject-matter adjudication и holdout gold, raw model outputs/reject/truncation traces, scoped concept/claim spans, реальные query relevance judgments, measured CPU/token/RAM/latency, повтор небольшой fixed subset. Полные тексты потребуются только если целевой claim coverage должен выходить за abstracts; их отсутствие не отменяет уже наблюдаемых общих concepts в локальном корпусе. Архитектурные варианты и fixed24-doc pilot: [architecture_options.md](architecture_options.md).
