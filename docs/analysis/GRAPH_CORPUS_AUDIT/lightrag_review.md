# Pinned LightRAG: независимая проверка кода

Дата аудита: 2026-10-02. Проверен локальный исходный код `HKUDS/LightRAG` commit `453dce83d6d0354a06e46c8d4029a0895c4e054b`, tree `20a23b48c2382ee944700a87cb6d2941fc4d6838`, в `data/arch001/HKUDS-LightRAG-453dce8/`. Pin также задан в `pyproject.toml:40`. SHA-256 всех 12 файлов LightRAG, перечисленных в `docs/donors.lock.json`, совпали с lock. Дополнительно прочитаны `prompt.py`, `constants.py`, `utils_graph.py` из этого же локального дерева. Ветка upstream main не использовалась.

Проверка ограничена чтением кода, существующего ARCH-001 smoke и production adapter. LightRAG не инициализировался; ingestion, вызовы моделей, установка зависимостей, изменения БД/индексов/конфигурации не выполнялись. Этот файл не устанавливает причины fragmentation реальных 100 документов: причинный вывод должен следовать из отдельного чтения PostgreSQL corpus и сопоставления с GraphFacts.

Пути `lightrag/...` далее относятся только к указанному pinned дереву. Диапазоны строк приведены для проверяемости, а не как ссылка на текущую версию upstream.

## Действующая integration boundary

`src/app/integrations/lightrag_adapter.py:222–239` вставляет только chunks: `entities=[]`, `relationships=[]`. Поэтому **этот adapter не запускает native extraction и сам не добавляет semantic nodes/relations в доменный граф**. Вставляемый текст получает suffix с opaque evidence key, предотвращающий совпадение donor text hashes для одинакового текста разных PostgreSQL chunks; исходный PostgreSQL текст возвращается после resolution, без suffix.

Query использует `mode="mix"`, `only_need_context=True`, отключённый donor rerank и заранее заданные high-/low-level keywords (`lightrag_adapter.py:71–84`). Конструктор передаёт функцию, падающую при любой попытке LLM generation (`:109–123`). Это также означает, что простое переключение на native insertion через данный production runtime не даст native extraction: для эксперимента понадобится отдельный runtime с extraction/summary LLM.

`PostgresEvidenceResolver` принимает только `evidence-<chunk UUID>`, повторно загружает chunk/revision/document и проверяет членство в конкретной index generation и public source (`:134–175`). Query доверяет donor только как rank/lookup hint; содержимое evidence и IDs берёт из PostgreSQL (`:266–284`). Неизвестный/устаревший reference отбрасывается. Global workspace overrides отвергаются (`:101–107`, `:287–294`). Это обоснованная граница reuse, но не доказательство фактической чистоты или полноты существующего donor workspace.

## Ответы на 10 вопросов

### 1. Что native entity extraction действительно делает?

Для каждого chunk вызывает extraction-role LLM с содержимым и optional section breadcrumb; просит named entities, тип и свободное описание, затем бинарные relations с keywords и описанием. Доступны delimiter-text и JSON parsing. Gleaning запускается максимум одним дополнительным вызовом при `entity_extract_max_gleaning > 0`; input budget может его пропустить. Initial и gleaning outputs разбираются в словари entities/edges; при совпадении key выбирается более длинное описание. Это эвристика полноты описания, не проверка фактической корректности.

Доказательства: `lightrag/operate.py:3942–4054`, `:4094–4110`, `:4177–4253`, `:4282–4343`; prompt contract `lightrag/prompt.py:56–109`. Default caps — 100 total records и 40 entities на ответ, default gleaning 1 (`lightrag/constants.py:15–27`). Количество nodes поэтому не является unbiased оценкой количества concepts в тексте.

Поля native extraction **не требуют exact target_text, exact quote или Unicode offsets**. Проверяется форма, непустое имя/описание, допустимая строка type; есть optional `kg_extraction_validator`, по умолчанию отсутствующий (`operate.py:3981–3983`). Инструкция «based solely on input» — prompt requirement, а не equivalent строгому GraphFact provenance validator.

### 2. Какие entity types поддерживаются?

Default guidance: `Person`, `Creature`, `Organization`, `Location`, `Event`, `Concept`, `Method`, `Content`, `Data`, `Artifact`, `NaturalObject`; fallback `Other` (`prompt.py:17–34`). Это универсальная taxonomy, а не готовая ontology Material/Property/Analyte/OperatingCondition/Process научных документов.

Guidance можно переопределить через `addon_params['entity_types_guidance']` / prompt profile (`prompt.py:790–849`, `operate.py:4010–4019`). Parser нормализует type в lowercase без пробелов, отбрасывает structural/reserved values и при comma берёт первый непустой token (`operate.py:662–707`). **Он не проверяет membership в перечне default типов.** Typed guidance можно задать, но это потребует отдельной оценки качества типов; оно не создаёт автоматически валидируемую доменную ontology. Старый `ENTITY_TYPES` env отвергается (`lightrag/lightrag.py:1643–1648`).

### 3. Как canonicalizes entity names?

Prompt просит consistent naming и title case для case-insensitive names (`prompt.py:63`, `:71–72`). Реальный `normalize_entity_name` вызывает formatting sanitizer: HTML/control cleanup, full-width symbols, Chinese spacing/punctuation, внешние кавычки, некоторые NBSP, trimming; фильтруются короткие numeric-only identifiers (`utils.py:5808–5970`). **Обязательного lower-/uppercase/casefold, lemmatization, synonym dictionary или ontology-aware canonicalization в этой функции нет.** Title case зависит от LLM.

Text parser ограничивает entity identifiers по длине (`operate.py:1613–1643`, default 256 chars в `constants.py:18`). Разные длинные identifiers могут стать одинаковыми после truncation; за этим необходимо следить в quality audit. Такие ограничения не равны semantic identity resolution.

### 4. Делает ли semantic entity deduplication?

**Автоматической semantic alias deduplication в исследованном native ingestion path нет.** Key — строка normalized entity name: collection `all_nodes[entity_name]` (`operate.py:3642–3649`), lookup существующего node через `get_node(entity_name)` (`:2456–2457`), entity vector ID — hash имени (`:2743–2746`). В этом потоке нет candidate embeddings → equivalence classifier → conservative clustering, соответствующих GRAPH-002.

Embeddings entity descriptions служат retrieval; само наличие entity vector store не означает использование similarity для объединения entities. Description string dedup и LLM summary агрегируют сведения **об уже совпавшем имени**, не решают, являются ли два разных имени alias.

API `amerge_entities(source_entities, target_entity)` существует (`lightrag.py:8303–8349`, `utils_graph.py:3440–3468`). Список source names задаёт caller. API умеет перенести relations/trackings, но не обнаруживает семантическую эквивалентность самостоятельно. Смешивать manual merge API и automatic entity resolution нельзя.

Практическое следствие: `transparent`/`transparency` могут остаться разными nodes; `Graphene` может чаще повторяться благодаря LLM naming, но это лишь возможность, требующая измерения. Наоборот, одинаковые normalized names разных значений/типов могут слиться: key не включает semantic kind или контекст.

### 5. Как работает merge entities при ingestion?

Native flow группирует chunk outputs по имени, читает existing node, объединяет source chunk IDs, хранит полный tracking list отдельно, затем ограничивает graph `source_id`. Type выбирается по highest count среди новых types и existing type; existing historical node даёт один type vote, не все historical mentions (`operate.py:2456–2522`, `:2576–2583`). Описания дедуплицируются буквально и concatenated/summarized; при превышении budget/числа fragments запускается LLM summary (`:2585–2632`; summary helper `:372–446`). Результат записывается в graph и entity VDB (`:2727–2772`).

Итого это **name-based aggregation**, а не equivalence inference. Название не включает entity type; category conflicts могут скрыться в выбранном большинстве. Summary может сгладить различия, условия и противоречия; хранить его как authoritative source claim нельзя.

Custom KG имеет другой contract: в одной вставке повтор entity name оставляет последнюю declaration (`lightrag.py:4526–4565`), а не использует native summary merge. Текущий adapter вообще не передаёт entities.

### 6. Как строятся relations?

LLM выбирает direct/clearly stated meaningful бинарные связи между extracted entities, n-ary statement декомпозируется. Поля: source name, target name, keywords, свободное description; text extraction weight = 1.0 (`prompt.py:67–74`, `operate.py:774–840`). Self-loops отбрасываются.

Native collection сортирует endpoint pair и объединяет outputs независимо от direction (`operate.py:3651–3654`); keywords объединяются, descriptions агрегируются, distinct contributing sources влияют на weight (`:2979–3019`, `:3021–3065`). Missing endpoint может быть создан как `UNKNOWN` с relation description (`:3158–3173`). Neo4j backend использует undirected pattern `MERGE (source)-[r:DIRECTED]-(target)` (`kg/neo4j_impl.py:1277–1282`): имя relation `DIRECTED` здесь **не обеспечивает направленность**.

Это pair relation graph с descriptions/keywords, не multi-relational domain KG с независимо валидируемыми `DISCLOSES_FEATURE`, `USES_MATERIAL`, `DETECTS_ANALYTE`, `OPERATES_AT`. Несколько семантически различных claims об одной pair агрегируются в одно ребро. Нужную направленную ontology нельзя получить простым копированием этих relations в доменный Neo4j.

### 7. Сохраняется ли source provenance?

**Chunk-level attribution сохраняется; строгий GraphFact contract не сохраняется автоматически.** Native entity/relation records получают source chunk key и file path (`operate.py:753–759`, `:831–839`). `entity_chunks`/`relation_chunks` tracking может хранить полный список, тогда как graph source IDs и file paths имеют caps (`:2490–2532`, `:2634–2689`; default max source IDs 200 в `constants.py:71–72`). Retrieval reference не является stable fact/revision/offset identifier.

Важное различие API: `ainsert_custom_kg` hash-ит **только chunk text**, один source alias указывает на последний chunk, `file_path` нормализуется до basename (`lightrag.py:4468–4496`; `utils_pipeline.py:248–258`). Native-extraction API `ainsert_custom_chunks` hash-ит `(doc_id, chunk_content)`, journaled и recoverable; одинаковый текст разных документов не разделяет chunk row (`lightrag.py:2394–2461`). Он, однако, deduplicates одинаковый текст внутри одного document, sanitizes strings и не принимает наш complete EvidenceChunk offset contract. Для точного PostgreSQL provenance требуется отдельное соответствие native chunk → document/revision/evidence IDs, включая one-to-many mapping при одинаковых occurrences, и resolution через PostgreSQL. В эксперименте нельзя подставлять произвольный первый occurrence.

Native document merge предварительно пишет recovery anchors (`operate.py:3666–3720`), поэтому custom-KG caveat не следует механически переносить на весь native pipeline. При этом cross-store transaction graph/KV/VDB/doc-status отсутствует (pinned `AGENTS.md`, section Consistency without transactions).

### 8. Насколько это решает нашу конкретную проблему?

На уровне кода LightRAG способен строить дополнительный concept/entity graph шире единственного `document → exact feature` relation; повторяющиеся имена и relations между concepts могут помочь retrieval. Этот механизм может обнаружить omitted concepts и связать documents через material/device/method names, **если** model извлечёт их корректно и одинаково.

Он не гарантирует strict alias precision, не устраняет flat ontology автоматически, не выполняет GRAPH-002 classifier calibration и не возвращает exact quotes/offsets. Более высокая density native graph может отражать полезный shared concept, generic hub или ошибочный merge. Поэтому density и largest component нельзя использовать как самостоятельный acceptance criterion. Эффект на эти 100 документов ещё не измерен; ответ зависит от независимого corpus audit, не от названия библиотеки.

### 9. Какие риски уже выявил ARCH-001?

Исторический smoke — plumbing test с constant 4-D embeddings, character tokenizer и LLM stub, падающим при вызове; он **не проверял native extraction или retrieval quality** (`docs/validation/ARCH-001/README.md:16–37`). Записанные counterexamples и ограничения:

| Риск | Evidence | Значение |
|---|---|---|
| URL/file path превращается в basename | ARCH-001 README:41; `utils_pipeline.py:248–258` | Нельзя доверять `file_path` как full source URI |
| Повтор source alias выбирает последний chunk | README:42; `lightrag.py:4496` | Потеря attribution при неоднозначном custom-KG alias |
| Одинаковый text другого document перезаписывает provenance | README:43; `lightrag.py:4482–4495` | Text-only custom-KG chunk identity не document-safe |
| Custom KG без durable journal/prewrite anchors | README:47; `lightrag.py:4353–4362` | Repeat vector count не доказывает crash-safe идемпотентность/cleanup |
| Undirected pair и последняя custom declaration | README:48; `lightrag.py:4568–4576` | Непригоден для прямого authoritative ontology import |
| Поле `source_chunk_index` игнорируется | README:49; `lightrag.py:4477–4480` | Нужен фактический `chunk_order_index` |
| Query refs не равны revision/offset/owner contract | README:50 и сохранённый `result.json` | Reference ID заново назначается в ответе; нужна PG resolution |
| Context-only query ещё может нуждаться в keyword LLM | README:51 | Нужно фиксировать keywords либо учитывать этот вызов |
| Workspace не заменяет ownership/auth | README:59 | Backend globals могут переопределить workspace; требуется isolation |
| Import backend может устанавливать отсутствующие packages; version drift | README:61 | Эксперимент не должен неожиданно скачать зависимости или изменить среду |

Production adapter адресует несколько caveats opaque evidence keys, suffix, public source/generation validation, no-generation и запретом globals. Это не лицензия на authoritative native graph replacement; и не доказательство, что все recovery/revision cleanup gates пройдены.

### 10. Имеет ли смысл native A/B на тех же 100 docs?

**Да, как последующий isolated quality/retrieval experiment; реализация и запуск не выполнялись.** Он полезен для вопроса «помогает ли graph с entities и concept relations извлекать source-supported контекст», а не как доказательство готовой semantic canonicalization.

Контрольируемый дизайн после corpus audit:

1. Зафиксировать exact manifest: 100 document IDs, active revision IDs, EvidenceChunk IDs/order, hashes PostgreSQL text, existing GraphFact baseline, index generation. Не скачивать заново EPO/OpenAlex и не обновлять production corpus.
2. Сначала оценить небольшой стратифицированный pilot: близкие pairs, разные темы и zero-fact documents. Затем, только после оценки, использовать те же 100 documents. Заранее записать acceptance gates и CPU budget.
3. A0: текущий raw graph + существующий vector retrieval. A1: тот же retrieval плюс native LightRAG extraction graph. Для изоляции graph эффекта дополнительно сравнить LightRAG chunk-only/naive и native graph/mix при одинаковых chunks/embeddings/budget. Генерацию final answer держать одинаковой или отключить в retrieval benchmark.
4. Native arm должен вызывать extraction API, а не `ainsert_custom_kg(entities=[], relationships=[])`. В этом pin `ainsert_custom_chunks` позволяет сохранить те же chunk boundaries и даёт document-scoped chunk identity/journal (`lightrag.py:2394–2461`, `:2811–2821`); API deprecated, поэтому это средство фиксированного эксперимента, не новая production dependency contract. Хранить mapping вне source text. Sanitation и intra-document dedup отражать в mapping и coverage stats. Альтернатива `ainsert` меняет chunking, что делает experiment менее причинно чистым.
5. Использовать отдельный disposable namespace и storage endpoints без product credentials/production access. Перед запуском проверить отсутствие global overrides и migration/automatic-install side effects. Working directory/JSON KV также должны быть отдельными; один workspace label не является полной изоляцией.
6. Зафиксировать тот же Qwen extraction model/digest и qwen3-embedding model/dimension; отдельной новой модели native LightRAG не требует. Нужны extract и summary role callbacks, которых нет в production adapter. Tev1 не нужен для native name merge. Default universal types и domain-guided types сравнивать как отдельные arms, не смешивать скрытую ontology customization с эффектом библиотеки.
7. Сохранить prompt profiles, temperature/seed если поддерживаются, chunk sanitation, caps, gleaning, retries/timeouts, LLM raw outputs, extraction/summary token counts и wall time. Повторить небольшой subset для variability; fixed cached outputs нужны для reproducibility. CPU cost нельзя честно оценить числом без измерения: native path добавляет один или два extraction calls на chunk и возможные summary calls для hubs.
8. Независимо разметить source support и semantic kind у sample entities/relations, проверить strict alias false merges и homonyms. Gold из manual source-text pair audit нельзя получать из результата native extraction. Отдельно оценивать related/broader relations: это полезные links, но не SAME.
9. Метрики: source-supported concept precision/recall на проверенных pairs; type accuracy; false merges; fraction resolvable PostgreSQL provenance; zero-fact concept recovery; documents sharing корректный concept; retrieval Recall@k/nDCG и evidence coverage при одинаковом token budget; latency/CPU/RAM/LLM calls; failed/truncated chunks. Density/component size — secondary descriptive stats. Для strict SAME reusable gate остаётся precision ≥0.95; native name merge не считается прошедшим его автоматически. Малый sample с нулём ошибок не доказывает этот уровень для всего corpus; нужны sample sizes и confidence intervals.
10. Принять результат только если полезность retrieval/coverage растёт при приемлемой source-support precision и provenance. Generic high-degree hub, рост числа edges или красивый viewer без этих улучшений не являются успехом.

## Вывод для архитектурных вариантов

| Вариант | Что LightRAG добавляет | Главный риск / стоимость |
|---|---|---|
| Сохранить raw exact graph | Optional additional public chunk retrieval в существующей integration boundary | Не устранит missing/alias concepts, если corpus audit их обнаружит |
| Typed semantic layer над raw GraphFacts | Может остаться лишь retrieval consumer; typed normalization/alias control принадлежит отдельному слою | Нужна калиброванная equivalence policy и RELATED/BROADER без false SAME |
| Native LightRAG как отдельный graph builder | Извлечение entities и inter-concept relations, name aggregation, graph/vector retrieval | Свободные descriptions, coarse attribution, type/name collisions, summary LLM cost; строгий domain KG не заменяет |
| Hybrid raw facts + concept graph + LightRAG retrieval | Сохраняет exact evidence и допускает дополнительные semantic links с PG resolution | Самая высокая integration/evaluation complexity; overlap каналов требует ablation |

На 1k/10k/100k documents пригодность native builder зависит от total chunks, model throughput, hubs и summary work, а не только document count. Дефолтные file-backed stores в pinned `AGENTS.md` допускаются для small-scale validation; серверные graph/vector/KV/doc-status backends, отдельная durability/recovery evaluation и измерение cost потребуются для больших объёмов. Числа ingestion time и RAM в этом read-only audit не измерялись. Дополнительный LLM model не обязателен, но дополнительные LLM calls неизбежны, если включать native extraction.

Здесь подтверждена архитектура механизма, а не превосходство LightRAG на реальном corpus. После ручного чтения sources root audit должен решить, нужен ли вообще semantic layer и какое именно ограничение он должен устранять. Ни production switch, ни native 100-document ingestion, ни автоматическое слияние по Tev1 confidence этот отчёт не авторизует.
