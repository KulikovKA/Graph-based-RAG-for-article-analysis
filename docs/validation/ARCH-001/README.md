# ARCH-001: проверка доноров

Дата проверки: 2026-09-29. Выполнен изолированный исследовательский smoke; production-код приложения не создавался. Источник версий и контрольных сумм всех прочитанных файлов — [donors.lock.json](../../donors.lock.json). Ссылки в [REPO_MAP](../../REPO_MAP.md) закреплены на commit, а не на ветку. Commit и tree SHA различаются; прежняя подпись «просмотренное дерево» для LightRAG/PQAI исправлена.

## Версии и лицензии

| Донор | Commit | Проверенный LICENSE / copyright | Использование |
|---|---|---|---|
| LightRAG | `453dce83d6d0354a06e46c8d4029a0895c4e054b` | MIT; 2025 LightRAG Team | Кандидат для optional context adapter |
| PQAI | `56342aaac5d9bf626f9413e5e49819e70709ce2f` | MIT; 2021 AT&T Intellectual Property, All other rights reserved | Только reference |
| PriorArtRAG | `fcaad8482c7df5d8106d4041c45d732f18d8c295` | MIT; 2025 Abhijeet Ashok Muneshwar | Только reference |
| mcp-prior-art | `eae73ff170b058772ca74e97b13eade853420e83` | MIT; 2026 Chase Hughes | Дополнительный source adapter reference |

У всех четырёх прочитаны полные MIT notices, включая требование сохранения copyright/permission notice. Каждый файл inventory получен с закреплённой ревизии; записан SHA-256. Исходники доноров в проект не перенесены. MIT корневого репозитория не означает проверку лицензий его моделей, корпусов и всех транзитивных зависимостей; их inventory требуется при фактическом включении в приложение.

## LightRAG: фактический smoke

[smoke.py](smoke.py) выполнялся с установленным из закреплённого исходного кода `lightrag-hku==1.5.8`. Результат — [result.json](result.json), exit code **0**. `pip check`: **No broken requirements found**. Это проверка API/storage plumbing, без оценки качества поиска: embedding — постоянный четырёхмерный вектор, tokenizer — символы, LLM stub падает при любом вызове. Реальные запросы шли только в временные Neo4j/Qdrant; внешние LLM и EPO не вызывались.

| Среда | Фактически использовано |
|---|---|
| Host / containers | Windows, Docker Desktop; Linux/amd64 |
| Python | 3.12.13 |
| Neo4j / driver | 5.26.23 / 6.3.1 |
| Qdrant / client | 1.17.1 / 1.17.1 |
| Python dependencies | [requirements.freeze.txt](requirements.freeze.txt), снимок установленной среды |

| Проверка | Результат |
|---|---|
| `await initialize_storages()`; `await ainsert_custom_kg(kg, full_doc_id=...)` | Успех; исходный payload не изменён |
| `source_id` alias → graph source chunk ID → KV `full_doc_id` и `chunk_order_index` | Подтверждено для одного уникального текста/alias |
| `await aquery(query, QueryParam(mode="mix", only_need_context=True, ...))` | Строковый контекст содержит fixture |
| `await aquery_data(query, param=...)` | `status=success`; 2 entities, 1 relationship, 1 chunk, reference `1` |
| Повторная вставка того же KG | Число Qdrant points не увеличилось; это не доказательство crash-safe идемпотентности |
| Второй пустой workspace | Узел отсутствует, query не возвращает чужие chunks |
| `hl_keywords`, `ll_keywords` заданы; `enable_rerank=False` | 0 вызовов LLM |
| `await finalize_storages()` | Успех |

**Контрпримеры provenance, воспроизведённые smoke:**

1. `file_path="fixture://patent-A/revision-1/chunk-7"` становится `chunk-7`. Это basename, не сохранённый URL/устойчивый evidence ID. Первый smoke обнаружил это несовпадение; финальная проверка явно фиксирует ограничение.
2. Два разных чанка с одним `source_id` оставляют у сущности ссылку только на последний: `chunk_to_source_map[source_id] = chunk_id`.
3. Chunk ID вычисляется из текста. Одинаковый текст другого документа в том же workspace перезаписывает `full_doc_id` в KV; связь с первым документом теряется.

**Дополнительно подтверждено чтением кода:**

- `ainsert_custom_kg` прямо исключён из document-level recovery guarantee: нет durable operation journal и предварительных `full_entities/full_relations` anchors. Проверку падения процесса/переиндексации/удаления эта задача не подменяет.
- Связи обрабатываются как неориентированные; повтор одного endpoint pair оставляет последнюю декларацию. Типизированную доменную онтологию так переносить нельзя.
- `source_chunk_index` из части upstream example не читается этим методом; фактическое поле — `chunk_order_index`.
- `aquery_data` возвращает `chunk_id`, `file_path`, `reference_id`, но не полный наш revision/offset/owner contract. `reference_id` пересчитывается для ответа. Docstring обещает `reference_id` у entities/relationships, фактический ответ этого поля там не содержит.
- `only_need_context` исключает финальную генерацию, но без заданных keywords может потребоваться keyword LLM. Нулевой LLM в smoke не является обещанием для любого запроса.

**Решение:** ADR-003 разрешает только дополнительный контекстный поиск по публичным данным в отдельном индексе. Доменный граф, immutable revisions и evidence остаются нашими. Перед включением в evidence pack каждый результат повторно разрешается и проверяется по PostgreSQL/нашему retrieval; неоднозначный, устаревший или неразрешимый источник исключается. Прямой custom KG импорт не считается безопасным переносом доменного provenance.

### Storage configuration

Проверенные имена классов: `Neo4JStorage`, `QdrantVectorDBStorage`; KV/doc status в smoke — default JSON storage во временной директории. Neo4j: `NEO4J_URI`, `NEO4J_USERNAME`, `NEO4J_PASSWORD`, `NEO4J_DATABASE=neo4j`. Qdrant: `QDRANT_URL`, при защищённом сервере `QDRANT_API_KEY`. Временные серверы не публиковали host-порты, Neo4j работал с `NEO4J_AUTH=none`; это только конфигурация disposable smoke.

Workspace передаётся конструктору. `NEO4J_WORKSPACE` и `QDRANT_WORKSPACE` имеют приоритет над ним: в smoke они запрещены assert-ом. Neo4j использует workspace label; Qdrant — payload filter `workspace_id`, коллекции имеют suffix модели и размерности: `lightrag_vdb_{entities,relationships,chunks}_arch001_fixture_4d`. Поэтому workspace не равен отдельной коллекции и не заменяет авторизацию. Собственные коллекции продукта отделить от префикса LightRAG; запретить случайные глобальные workspace overrides. Проверка двух namespaces не заменяет multi-user security tests.

Модули backend используют `pipmaster` для установки отсутствующих библиотек при импорте. Драйверы следует устанавливать заранее из проверенного lock. Первая установка разрешила qdrant-client 1.19.1 при локальном сервере 1.17.1 и выдала compatibility warning; для финального smoke клиент закреплён на 1.17.1, предупреждение устранено. Не смешивать плавающие server/client версии.

## PQAI: границы reuse

Проверены `core/search.py`, `reranking.py`, `snippet.py`, `highlighter.py`, `documents.py`, `api.py` и `requirements.txt` из inventory.

- `Searcher.search` / `VectorIndexSearcher` — поиск по одному/нескольким индексам, дедупликация и сортировка; reference для работы с кандидатами.
- `Ranker.rank`, `CustomRanker`, `ConceptMatchRanker` требуют локальных embedding/model assets. `CustomRanker` использует взаимодействия векторов и поправку на длину, `ConceptMatchRanker` — WMD/концепты. Они не выбраны как наша CPU-модель.
- `SnippetExtractor` создаёт rankers при импорте; контекст вокруг предложения использует `randrange`, эвристика предложений ориентирована на английский. Нужны собственные детерминированные offsets и экранированная подсветка.
- `core/api.py` запускает vector-search thread и обращается к AWS env/S3 при импорте. Весь сервис не импортировать.
- `requirements.txt` включает TensorFlow/Torch/CUDA и старые жёсткие pins. Их совместимость с нашим стеком не проверялась; файл не становится зависимостями проекта. PQAI runtime не запускался.

## PriorArtRAG: проверенные контракты

Основные permalinks — в REPO_MAP, дополнительные: [app/service.py](https://github.com/ABHIJEET-MUNESHWAR/PriorArtRAG/blob/fcaad8482c7df5d8106d4041c45d732f18d8c295/priorartrag/app/service.py), [config/settings.py](https://github.com/ABHIJEET-MUNESHWAR/PriorArtRAG/blob/fcaad8482c7df5d8106d4041c45d732f18d8c295/priorartrag/config/settings.py).

| Контракт | Подтверждение и ограничение |
|---|---|
| `QueryPlanner.plan` | Исходный query включён всегда; default `max_subqueries=6`, `min_element_terms=2`, веса original/element/CPC: 1.5/1/0.5; пустые/повторяющие исходный запрос элементы пропускаются. Сохранение original не гарантирует неизменный recall после fusion |
| `reciprocal_rank_fusion` | `weight/(k+rank)`, default k=60; дедуп внутри списка, tie-break по passage ID, contributors. Есть отдельная min-max linear fusion |
| `HybridRetriever.search` | Lexical+dense → fusion → rerank → parent aggregation; bounded rerank window, дополнение нереранжированным хвостом. Только `RerankerUnavailableError` превращается в `rerank_unavailable`; произвольный сбой lexical/dense здесь не подавляется |
| `StageTimings` | Стадии измеряются отдельно, но `fusion_ms` измеряет финальное слияние subqueries, не всю работу `_fuse` внутри цикла. Не копировать трактовку метрик без проверки |
| `Reranker` | Protocol и `FeatureReranker` с ручными весами; это не выбранный обученный cross-encoder для нашего приложения |
| `EvidenceSet` / `CitationVerifier` | Проверяет наличие `[Pn]`, допустимый индекс, распознанные буквальные цитаты и длину; не доказывает semantic entailment. Splitter ориентирован на английский; regex цитат охватывает определённые кавычки и 3–400 символов |
| `AnalysisGenerator.generate` | Draft + optional feedback. Верификатор вызывается снаружи генератора |
| `AnalysisService._ground` в `app/service.py` | Бюджет `max_repair_attempts + 1` (default repairs=1), затем template fallback; исключение генератора переводит в fallback. Наш фиксированный лимит — одна repair-попытка с общим timeout/budget |
| `template_analysis` | Непустой fallback проверяется с `check_quotes=False`; пустой evidence возвращает отдельное сообщение с заранее заданным report. Это не универсальный валидатор всех фактов |
| `app/ports.py` | Protocol для document repository, cache, encoder, generator и др.; используем принцип узких границ |
| `EVALUATION.md` | Каталог регрессий: повтор кандидата, parent aggregation, невалидные citations, fallback. Числа upstream не измерялись нами и не являются результатом проекта |

Не переносить patent-examiner prompt с юридической оценкой, BM25/HNSW/sharding, GraphQL/Kafka/Prometheus/Grafana/CQRS. Наши evidence IDs должны указывать на immutable snapshot, а проверка русского текста/кавычек требует собственных кейсов. Runtime PriorArtRAG не запускался; выводы этого раздела получены чтением закреплённых файлов.

## EPO reference против официального OPS

Сверены [OPS overview](https://www.epo.org/en/searching-for-patents/data/web-services/ops), [Reference Guide 1.3.20, June 2024, §§2.3.1–2.3.3](https://link.epo.org/web/searching-for-patents/data/en-ops-v3.2-documentation-version-1.3.20.pdf) и [fair-use charter](https://www.epo.org/en/service-support/ordering/fair-use), доступные на дату проверки. Это review адаптера, без запросов к платному/авторизованному API.

| В `mcp-prior-art/epo.py` | Вывод для SRC-001 |
|---|---|
| OAuth client credentials, Basic auth, Bearer | Структура соответствует guide. Глобальный token без expiry ошибочен: учитывать `expires_in`, invalid-token response и синхронизацию обновления |
| `tenacity`, 3 попытки, backoff 1–10 секунд | Нужна классификация ошибок: не повторять безусловно неверный CQL, auth и исчерпанную квоту |
| Нет quota/throttle обработки | Guide определяет `X-IndividualQuotaPerHour-Used`, `X-RegisteredQuotaPerWeek-Used`, `X-RegisteredPayingQuotaPerWeek-Used`, `X-Rejection-Reason`, `X-Throttling-Control`, suspension/`Retry-After`; необходим общий scheduler с учётом наиболее строгого ответа |
| CQL через f-string; только первая страница до 25 | Валидировать/экранировать значения, проверить query fields, paging и диапазоны по OPS fixtures |
| JSON parser, abstract обрезается до 500 символов, первый applicant | Проверить singleton/list и языковые варианты, XML/JSON shapes; не выдавать усечённый abstract за полный источник |
| Нет credentials или HTTP 404 → `[]` | Разделить «не настроен», «нет результатов» и ошибку источника; не скрывать деградацию |

Fair use: бесплатный порог OPS — 4 GB за календарную неделю GMT, приблизительный максимум трафика 1 Mbit/s; условия могут меняться. Автоматизация идёт через REST, с регистрацией и соблюдением текущих квот. Адаптер донора не реализует это полностью; берём структуру, не импортируем MCP server.

## Воспроизведение smoke

Снимок Python-зависимостей не является production lock или полным supply-chain audit. Команды ниже используют отдельные имена контейнеров; при занятом имени сначала разберите предыдущий запуск. Нужен доступ к GitHub/PyPI только для установки. Из корня проекта в PowerShell:

```powershell
$ErrorActionPreference = 'Stop'
docker network create arch001-smoke
docker run -d --name arch001-neo4j --network arch001-smoke -e NEO4J_AUTH=none neo4j@sha256:40bf5ae9282213087e4d6036aab3ec443fe9c974d3dd4f14a11892c63157238f
docker run -d --name arch001-qdrant --network arch001-smoke qdrant/qdrant@sha256:94728574965d17c6485dd361aa3c0818b325b9016dac5ea6afec7b4b2700865f
docker run -d --name arch001-python --network arch001-smoke --mount "type=bind,source=$($PWD.Path),target=/workspace,readonly" python@sha256:423ed6ab25b1921a477529254bfeeabf5855151dc2c3141699a1bfc852199fbf sleep 14400
docker exec arch001-python pip install -r /workspace/docs/validation/ARCH-001/requirements.freeze.txt
docker exec arch001-python pip install --no-deps https://api.github.com/repos/HKUDS/LightRAG/tarball/453dce83d6d0354a06e46c8d4029a0895c4e054b
docker exec arch001-python pip check
docker logs arch001-neo4j --tail 10
# Дождаться сообщения Started у Neo4j, затем:
docker exec -w /tmp -e NEO4J_URI=bolt://arch001-neo4j:7687 -e NEO4J_USERNAME=neo4j -e NEO4J_PASSWORD=smoke-only -e NEO4J_DATABASE=neo4j -e QDRANT_URL=http://arch001-qdrant:6333 arch001-python python /workspace/docs/validation/ARCH-001/smoke.py
if ($LASTEXITCODE -ne 0) { throw 'Smoke failed' }
docker exec arch001-python cat /tmp/arch001-result.json
# После сохранения нужных результатов удалить только ресурсы этого smoke:
docker rm -f -v arch001-python arch001-neo4j arch001-qdrant
docker network rm arch001-smoke
```

`run_id`, timestamps и общий счётчик points меняются между повторениями на тех же серверах; asserts сравнивают состояние до/после вставки. Не ожидайте побайтного совпадения JSON. Test fixture не содержит пользовательских данных. Исходники и диагностические логи установочного запуска находятся в игнорируемом `data/arch001`; они не включаются в коммит.

## Закрытие критериев

- Проверка inventory прошла: 4 commit IDs, 35 файлов с SHA-256, MIT notices; все donor permalinks и локальные ссылки изменённых документов разрешаются. `git diff --check` прошёл.
- Реальный LightRAG insert/query на Neo4j/Qdrant выполнен, ограничения provenance записаны и отражены в ADR-003.
- PriorArtRAG contracts и EPO reference проверены; ADR-007 уточнён.
- Дальнейшие интеграционные, crash recovery, ownership и retrieval-quality проверки принадлежат LR-001/TEST-001/EVAL-001. ARCH-002 и implementation tasks не выполнялись.
- Публикация результата выполняется отдельным русскоязычным коммитом с push и сверкой HEAD удалённой ветки согласно `task.md`.
