# Независимый аудит corpus и Graph-RAG

**Вывод: CASE E — MIXED. Корпус тематически связан; текущий flat exact-feature graph плохо показывает эти связи. Основные ограничения — ontology/representation и selective extraction; lexical canonicalization тоже влияет. Разреженность exact claims допустима, увеличение плотности графа не является целью.**

Дата: 2026-10-02, Europe/Moscow. Выполнен только аудит. Production-код, конфигурация, БД, индексы и модели не изменялись. Ingestion/backfill, native LightRAG extraction и новые model calls не запускались. Во время аудита commit не создавался; публикация отчёта разрешена отдельным последующим запросом. Созданы analysis artifacts и одноразовые read-only/offline scripts.

## Проверенные результаты

| Проверка | Результат |
|---|---|
| Frozen corpus | 100 document/revision pairs, все OpenAlex articles |
| Доступный текст | 100 abstracts, 136 chunks; полных текстов нет |
| Source integrity | 136 chunk SHA-256 и offsets подтверждены; весь nonwhitespace abstract text покрыт chunks |
| PostgreSQL | Все 417 frozen fact IDs/revisions/keys совпали; quotes и normalized targets проверены |
| Neo4j | 509 baseline nodes = 100 docs + 409 features; 417 edges совпали с PostgreSQL |
| Incident vertices | 498 = 89 документов с фактами + 409 features; 11 zero-fact nodes присутствуют отдельно |
| Темы | 13 inductive primary groups; 87 gas-sensing/adsorption core, 13 adjacent/peripheral |
| Similarity | 4,950 pairs; NN median 0.777574, p75 0.807553, p90 0.835865, p95 0.855277 |
| Nearest output | Top-3 для каждого документа: 300 rows |
| Ручной pair audit | 30 пар, 31 документ; все тематически связаны, exact shared features = 0 во всех |
| Source concepts | 124 topic annotations, 248 exact quote anchors с Unicode spans |
| Zero-fact audit | Все 11: sparse source 1; review/roadmap 6; explicit candidates 3; retrospective policy case 1 |
| Типы features | Все 409 индивидуально размечены; 11 semantic kinds; 68 mixed-kind labels |
| Granularity | 101 atomic, 270 qualified, 38 propositions; ещё 20 qualified overly specific |
| Повреждённые labels | 3 подтверждённо обрезаны внутри формулы/числового содержания |
| Feature degree | 403 singleton, 5 degree-2, 1 degree-4; shared 6/409 = 1.467%; excess incidences 8 |
| Citation metadata | 406 directed in-corpus links; undirected components 99 + 1; 3 self-links исключены |

Разметка тем, пар и features — аналитическое чтение ассистентом с peer QA другими агентами, а не independent human gold. Численные расчёты воспроизводимы; экспертные taxonomy/scope решения требуют предметной adjudication. Общая техническая тема не означает равенства всех claims.

## Ответы по запрошенной структуре

1. **Какой corpus исследован.** Manifest `data/checkpoints/graph002-live-20261002.snapshot.json`, snapshot hash `5b80378fa2d8312951446fcbb3ada7994d775f13d452ff08fd415377a5fcade0`. Snapshot создан 2026-10-02 в 02:17:52 по Москве. Все 100 document/revision pairs и 417 frozen facts сверены с PostgreSQL. Прочитаны реальные stored abstracts/chunks; полнотекстовых секций нет.

2. **Source types.** 100 OpenAlex articles; EPO patents и uploaded PDFs отсутствуют. Titles, external IDs, normalized metadata и abstract status сохранены в локальном export. Новых запросов OpenAlex/EPO не было.

3. **Основные темы.** Oxide/graphene gas hybrids — 14; flexible/wearable/integrated devices — 13; electronic reduction/doping/interfaces — 15; 3D/patterned/array gas architectures — 5; metal nanoparticle sensors — 4; optical/electrochemical gas sensing — 4; first-principles/adsorption/mechanisms — 11; gas-sensor reviews — 20; metallic MXene channel — 1; broader synthesis/material applications — 7; physics/mechanics/roadmaps — 4; bio/chemical sensors — 1; gas membranes — 1. Primary partition имеет secondary overlaps и не является единственной правильной taxonomy. Все titles/rationales: [topic_clusters.csv](topic_clusters.csv), [corpus_composition.md](corpus_composition.md).

4. **Сходство документов.** Existing 1024d chunk vectors нормализованы; их equal-weight mean на документ снова нормализован; similarity — cosine. NN median 0.777574, p75 0.807553, p90 0.835865, p95 0.855277; all-pair median 0.600321. NN distribution: 15 документов в [.6,.7), 52 в [.7,.8), 26 в [.8,.85), 7 в [.85,.9). Внутри primary groups mean 0.669826, между ними 0.583871; 60/100 top-1 neighbors в той же primary группе. Char-weighted sensitivity даёт median 0.781297, совпадение top-1 82/100 и top-30 pairs 26/30. Это модельное сходство, не вероятность SAME. [nearest_documents.csv](nearest_documents.csv), [similarity_stats.json](similarity_stats.json).

5. **Реальные shared concepts.** Да: molecular doping/graphene sensing у D060–D078; epitaxial graphene/SiC/NO2 у D057–D067; rGO/pyrrole/NH3 у D040–D064; transparency/flexibility/bending/NO2 у D011–D100. Проверены 30 ближайших пар и 124 topic annotations по исходному тексту до feature comparison. Shared analyte может иметь отрицательный ответ, material family не равен strict alias. [manual_pair_audit.csv](manual_pair_audit.csv), [manual_concept_details.csv](manual_concept_details.csv), [pair_audit_review.md](pair_audit_review.md).

6. **Что видит graph.** Ни одна из 30 ближайших пар не имеет общего exact TechnicalFeature. У 18 пар facts есть с обеих сторон, у 12 хотя бы одна сторона zero-fact. Общие concepts иногда встроены в разные qualified/propositional labels, иногда отсутствуют. Quote может содержать больше concepts, чем label. Supplemental selected-label counts не являются extractor recall или причинной долей потерь.

7. **Почему 409 features / 417 edges.** Lexical identity редко переиспользуется: 403 degree-1, пять degree-2, один degree-4. Разные формулировки, параметры, составы и propositions создают singleton; отсутствие base concepts/roles и selective extraction скрывает meaningful links. Excess incidences = 8, shared features = 6/409. Correct mean features/document = **417/100 = 4.17**; 409/100 = 4.09 означает globally unique vocabulary/document. Document components = 92, largest = 4; лишь 11 document pairs имеют shared feature.

8. **Все 11 zero-fact docs.** D007, D013, D015, D019, D023, D041, D048, D059, D064, D084, D092. У всех есть complete indexed abstract, completed state = 0, сохранён весь normalized nonwhitespace text. D013 — sparse; D019/D023/D041/D048/D059/D084 — review scope, conservative zeros правдоподобны; D007/D064/D092 — сильные explicit candidates; D015 — retrospective methods с неоднозначной disclosure policy. Runtime failure/truncation или конкретный validator cause без logs не установлен. [zero_fact_audit.csv](zero_fact_audit.csv), [zero_fact_review.md](zero_fact_review.md).

9. **Главный bottleneck.** MIXED: ontology/representation плюс selective extraction/policy/validation; safe aliases — дополнительный фактор. Corpus heterogeneity реальна в 13 peripheral docs и различиях specific claims внутри core, но не объясняет всю thematic fragmentation. Точные проценты причинного вклада не идентифицируются без gold opportunities и controlled interventions. [diagnosis.md](diagnosis.md).

10. **Серьёзность.** Высокая для graph-only поиска и сравнения технических аналогов. Для provenance registry умеренная: source evidence сохранена, vectors могут находить похожие документы. Downstream retrieval/answer quality в этом аудите не измерялась. Feature types: PERFORMANCE 109, PROPERTY 84, MATERIAL 51, PROCESS 37, DEVICE 33, MORPHOLOGY 32, MECHANISM 18, TECHNOLOGY 18, CONDITION 12, ANALYTE 10, OTHER 5. Granularity и defects: [feature_review.md](feature_review.md).

11. **Нужно ли повышать connectivity.** Не как самостоятельную метрику. Sparse exact-claim graph допустим. Для поставленной задачи нужно повышать видимость source-supported comparison dimensions и retrieval relevance, сохраняя qualifiers/conditions/polarity. CITES, topic hierarchy и MENTIONS имеют отдельный смысл и не доказывают claim identity.

12. **Архитектурные варианты.** (1) Raw + vectors; (2) typed semantic layer с 2A над facts и 2B source-grounded mentions; (3) native LightRAG как independent builder; (4) hybrid raw + concepts + LightRAG; (5) raw + vectors + citation/taxonomy. Полное сравнение всех запрошенных quality/cost/provenance/scalability/reuse/diploma dimensions: [architecture_options.md](architecture_options.md).

13. **Pros/cons.** (1) Проверяемый дешёвый baseline, слабые concept links. (2) Осмысленные types/roles при exact evidence, нужны rubric и source extraction для omissions. (3) Широкий graph retrieval, слабее claim provenance и нет automatic semantic alias gate. (4) Гибкость, высокая цена и сложность attribution. (5) Дешёвые metadata links, technical claims не восстанавливаются. Численных CPU/quality прогнозов без measurements нет. Новая модель не обязательна, но 2B/3/4 добавляют LLM calls.

14. **Native LightRAG.** Проверен commit `453dce83d6d0354a06e46c8d4029a0895c4e054b`. Native path извлекает entities/types/descriptions и binary relations; merge идёт по normalized name, без automatic strict semantic equivalence разных aliases. Name key не включает type. Chunk attribution сохраняется, exact quote/offsets не обязательны. Production adapter вставляет только chunks и блокирует generation. Native arm имеет смысл как isolated A/B; ARCH-001 plumbing не доказывает качество. [lightrag_review.md](lightrag_review.md), первичный [pinned operate.py](https://github.com/HKUDS/LightRAG/blob/453dce83d6d0354a06e46c8d4029a0895c4e054b/lightrag/operate.py).

15. **Рекомендация.** Вариант 2A + 2B в ограниченном evidence-backed pilot; вариант 1 сохраняется baseline, вариант 5 — отдельный дешёвый control. Hybrid 4 — после проверки marginal usefulness; native 3 — отдельная comparison arm. Это предложение, не реализация.

16. **Почему.** Подход адресует наблюдённые omissions и flat semantic kinds, сохраняет authoritative raw evidence и допускает topic links без разрушительных SAME merges. Только 2A над labels не восстановит 11 zero docs; только citation не даст typed claims; LightRAG не гарантирует alias precision/roles.

17. **Минимальный следующий experiment.** Fixed 24-doc diagnostic pilot со всеми 11 zeros, близкими парами, reviews, DFT и periphery; точный список в architecture_options.md. Сравнить raw + vectors, metadata expansion, typed mapping 2A, source concepts 2B. На D007/D064/D092 сохранить drafts/reject/token traces. Далее по gates рассмотреть native arm и те же 100 docs. Метрики: source/role precision, span resolution, Recall@10/nDCG@10, evidence budget, CPU/latency. Gold/holdout заранее; density secondary. Ничего из этого сейчас не запущено.

18. **Что не делать.** Не снижать Tev1 threshold в production; не merge RELATED/BROADER в SAME; не терять NO versus NO2, NH3 positive versus negative, material/property и operation/synthesis conditions. Не заменять PG facts donor descriptions, не заявлять 11 pipeline failures, не backfill/reindex/delete baseline ради density. Не скачивать модели и не обновлять pin в рамках аудита.

19. **Уверенность.** Высокая в snapshot/counts/text integrity и nearest-pair mismatch; умеренно высокая в mixed diagnosis; средняя в single-rater topic/type boundaries; низкая в runtime causes каждого zero и количественном gain вариантов. Доли labels — rubric estimates, не causal percentages.

20. **Недостающие данные.** Независимая предметная adjudication concepts/claims и held-out gold; original extractor outputs/reject reasons/token-limit logs; реальные query relevance judgments; CPU/RAM/LLM/latency measurements и variability replay. Полные тексты нужны для оценки покрытия за пределами abstracts; текущих abstracts достаточно для установленного thematic overlap.

## Артефакты и воспроизводимость

Обязательные deliverables: этот README, [corpus_stats.json](corpus_stats.json), [topic_clusters.csv](topic_clusters.csv), [nearest_documents.csv](nearest_documents.csv), [manual_pair_audit.csv](manual_pair_audit.csv), [zero_fact_audit.csv](zero_fact_audit.csv), [feature_type_audit.csv](feature_type_audit.csv), [feature_granularity_sample.csv](feature_granularity_sample.csv), [diagnosis.md](diagnosis.md), [architecture_options.md](architecture_options.md).

Дополнительно сохранены local corpus/vector exports, raw reading files, all-pair similarities, Unicode anchors, content coverage, read-only Neo4j results, citation metadata links, pinned-code/experiment/feature/peer reviews и [artifact_hashes.json](artifact_hashes.json). Это audit bundle, не product projection. Полные выгрузки `corpus_export.json`, `existing_chunk_vectors.json`, `neo4j_projection_read.json`, `raw_corpus_reading.txt` и `top30_pairs_raw_first.txt` остаются локальными и исключены из Git через `.gitignore` этой директории. В репозиторий входят отчёты, аналитические таблицы и scripts; hashes также фиксируют локальные исключённые файлы для проверки исходного audit bundle.

Scripts в `scripts/analysis/`: `graph_corpus_readonly.py` (SELECT в read-only transaction + GET/scroll existing vectors), `graph_corpus_projection_readonly.py` (MATCH-only), `graph_corpus_similarity.py`, `graph_corpus_pair_audit.py`, `graph_corpus_integrity.py`, `graph_corpus_summary.py` (остальные offline). Экспорт не вызывает bootstrap/ensure_schema, source clients или model endpoints. Использованы уже работающие контейнеры; docker compose up/run не выполнялись.

CSV — UTF-8 BOM для Windows; JSON/Markdown — UTF-8. D001–D100 следуют sorted document UUID order, F001–F409 — sorted raw feature text order. Snapshot manifest SHA-256, vector export SHA-256 и итоговые artifact hashes сохранены. Для повторения primary similarity достаточно local exports; новые embeddings не нужны.
