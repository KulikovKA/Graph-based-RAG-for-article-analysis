# Карта донорских репозиториев

Срез проверки: 2026-09-29. В implementation tasks закреплять проверенные версии/commit SHA. Ссылки на PriorArtRAG ниже все ведут на один commit `fcaad8482c7df5d8106d4041c45d732f18d8c295`, чтобы upstream drift не менял смысл references.

## LightRAG — основной Graph-RAG кандидат

Источник: [HKUDS/LightRAG](https://github.com/HKUDS/LightRAG), ветка main, просмотренное дерево `453dce83d6d0354a06e46c8d4029a0895c4e054b`. [Лицензия MIT](https://github.com/HKUDS/LightRAG/blob/main/LICENSE). В текущем коде есть Neo4j/Qdrant storage, query modes и получение контекста без генерации ответа.

| Путь | Что подтверждено | Решение |
|---|---|---|
| [lightrag/lightrag.py](https://github.com/HKUDS/LightRAG/blob/main/lightrag/lightrag.py) | Оркестратор ingestion/query и storage configuration | Обернуть в `integrations/lightrag_adapter.py`, не копировать |
| [lightrag/base.py](https://github.com/HKUDS/LightRAG/blob/main/lightrag/base.py) | `QueryParam`, `only_need_context`, `mode=mix`, лимиты токенов, `enable_rerank` | Использовать context-only, валидировать результат и source IDs |
| [lightrag/operate.py](https://github.com/HKUDS/LightRAG/blob/main/lightrag/operate.py) | KG query, extraction, provenance/context assembly | Изучить при integration spike; не вызывать внутренние функции напрямую |
| [lightrag/kg/neo4j_impl.py](https://github.com/HKUDS/LightRAG/blob/main/lightrag/kg/neo4j_impl.py) | Реальная реализация Neo4j storage/workspace | Отдельный namespace, не смешивать с доменным графом |
| [lightrag/kg/qdrant_impl.py](https://github.com/HKUDS/LightRAG/blob/main/lightrag/kg/qdrant_impl.py) | Реальная реализация Qdrant storage/workspace | Проверить совместимость коллекций и embedding dimensions |
| [examples/insert_custom_kg.py](https://github.com/HKUDS/LightRAG/blob/main/examples/insert_custom_kg.py) | Custom entities, relationships, chunks с `source_id` | Spike для импорта валидированных данных |
| [lightrag/rerank.py](https://github.com/HKUDS/LightRAG/blob/main/lightrag/rerank.py) | Rerank чанков с budget/window | Сравнить с нашим лёгким reranker, не дублировать без измерения |
| [lightrag_webui/src/features/GraphViewer.tsx](https://github.com/HKUDS/LightRAG/blob/main/lightrag_webui/src/features/GraphViewer.tsx) | React/Sigma graph viewer | Идеи взаимодействия; собственный scoped API/UI |

Ограничения: автоматическое извлечение свободных entity types не гарантирует фиксированную патентную онтологию; встроенный WebUI и auth не являются auth продукта; workspace не заменяет row-level ownership; версия LightRAG может меняться. В фазе 0 проверить API `ainsert_custom_kg`/`aquery` на выбранном релизе, idempotency и очистку provenance. Если custom KG не сохраняет нужные invariant, использовать LightRAG только для публичного контекста, а доменный graph retrieval оставить в собственном адаптере. Не импортировать весь сервер.

## PQAI — патентные эвристики

Источник: [pqaidevteam/pqai](https://github.com/pqaidevteam/pqai), ветка master, просмотренное дерево `56342aaac5d9bf626f9413e5e49819e70709ce2f`. [Лицензия MIT](https://github.com/pqaidevteam/pqai/blob/master/LICENSE), copyright AT&T. Код полезен как reference; полноценный сервис зависит от заранее построенных индексов, model assets и AWS/S3.

| Путь | Проверенный механизм | Решение |
|---|---|---|
| [core/api.py](https://github.com/pqaidevteam/pqai/blob/master/core/api.py) | Patent/NPL search, фильтры, snippets, mapping; импорт требует AWS env/S3 | Не переносить сервис; взять UX/контрактные идеи |
| [core/search.py](https://github.com/pqaidevteam/pqai/blob/master/core/search.py) | Поиск по индексам и ranking кандидатов | Reference для patent candidate retrieval/ranking; fusion reference — PriorArtRAG |
| [core/reranking.py](https://github.com/pqaidevteam/pqai/blob/master/core/reranking.py) | `Ranker`, `CustomRanker`, `ConceptMatchRanker` с model assets | Проверить методику, выбрать компактный локальный reranker измерением |
| [core/snippet.py](https://github.com/pqaidevteam/pqai/blob/master/core/snippet.py) | Sentence/span extraction и feature mapping | Переосмыслить с детерминированным span + offsets; код использует случайный контекст и тяжёлые импорты |
| [core/highlighter.py](https://github.com/pqaidevteam/pqai/blob/master/core/highlighter.py) | Подсветка терминов | Не копировать HTML replacement; безопасная подсветка на клиенте |
| [core/documents.py](https://github.com/pqaidevteam/pqai/blob/master/core/documents.py) | Модель Patent/Document | Reference для нормализации, не схема хранения |

## PriorArtRAG — decomposition, retrieval и grounding patterns

Основной третий reference: [ABHIJEET-MUNESHWAR/PriorArtRAG на проверенном commit](https://github.com/ABHIJEET-MUNESHWAR/PriorArtRAG/tree/fcaad8482c7df5d8106d4041c45d732f18d8c295), SHA `fcaad8482c7df5d8106d4041c45d732f18d8c295` (commit от 2026-08-02). Проверены существование repository и commit, дерево файлов и [MIT LICENSE](https://github.com/ABHIJEET-MUNESHWAR/PriorArtRAG/blob/fcaad8482c7df5d8106d4041c45d732f18d8c295/LICENSE).

| Pinned upstream file | Проверенный pattern | Использование в нашем проекте |
|---|---|---|
| [priorartrag/domain/decompose.py](https://github.com/ABHIJEET-MUNESHWAR/PriorArtRAG/blob/fcaad8482c7df5d8106d4041c45d732f18d8c295/priorartrag/domain/decompose.py) | Bounded subqueries по элементам disclosure/claim; исходный query всегда сохраняется, есть fallback при пустой декомпозиции | Reference для декомпозиции технических признаков в RET-001; ограничить число запросов и сохранять исходный запрос |
| [priorartrag/domain/pipeline.py](https://github.com/ABHIJEET-MUNESHWAR/PriorArtRAG/blob/fcaad8482c7df5d8106d4041c45d732f18d8c295/priorartrag/domain/pipeline.py) | Композиция lexical+dense → fusion → rerank → aggregate; результаты стадий и timings | Reference для границ стадий, timings и degradation behavior retrieval pipeline; не импортировать реализацию индекса |
| [priorartrag/domain/fusion.py](https://github.com/ABHIJEET-MUNESHWAR/PriorArtRAG/blob/fcaad8482c7df5d8106d4041c45d732f18d8c295/priorartrag/domain/fusion.py) | Reciprocal-rank fusion и weighted/linear fusion | Reference для candidate fusion; оценить на нашем размеченном наборе и наших каналах |
| [priorartrag/domain/rerank.py](https://github.com/ABHIJEET-MUNESHWAR/PriorArtRAG/blob/fcaad8482c7df5d8106d4041c45d732f18d8c295/priorartrag/domain/rerank.py) | Отдельный типизированный Protocol reranker и explainable score contributions | Reference для контракта стадии; CPU-модель/алгоритм выбираем отдельно benchmark-ом |
| [priorartrag/domain/grounding.py](https://github.com/ABHIJEET-MUNESHWAR/PriorArtRAG/blob/fcaad8482c7df5d8106d4041c45d732f18d8c295/priorartrag/domain/grounding.py) | `EvidenceSet`, `CitationVerifier`; выявление uncited assertions, phantom citations и fabricated quotes; один repair attempt и deterministic template fallback | Ключевой reference для ANALYST-001 и проверки evidence до показа ответа; адаптировать к нашим стабильным evidence IDs и API DTO |
| [priorartrag/adapters/llm/generator.py](https://github.com/ABHIJEET-MUNESHWAR/PriorArtRAG/blob/fcaad8482c7df5d8106d4041c45d732f18d8c295/priorartrag/adapters/llm/generator.py) | Генератор создаёт draft, а verifier остаётся отдельной доверенной границей | Reference для Smart Qwen → deterministic validator |
| [priorartrag/app/ports.py](https://github.com/ABHIJEET-MUNESHWAR/PriorArtRAG/blob/fcaad8482c7df5d8106d4041c45d732f18d8c295/priorartrag/app/ports.py) | Outbound зависимости оформлены как Python Protocol ports | Reference для `InferenceProvider`, source/storage/cache interfaces |
| [EVALUATION.md](https://github.com/ABHIJEET-MUNESHWAR/PriorArtRAG/blob/fcaad8482c7df5d8106d4041c45d732f18d8c295/EVALUATION.md) | Retrieval/grounding gates, regressions и каталог failure cases | Reference для citation/grounding tests и отчёта EVAL-001; не копировать заявленные чужие численные результаты |

Ограничения reuse: не переносить собственные BM25/HNSW/sharding реализации вместо Qdrant; не переносить GraphQL/Kafka/Prometheus/Grafana/CQRS целиком; не использовать PriorArtRAG как основу приложения. Наша архитектура остаётся собственной: EPO/OpenAlex adapters, PostgreSQL, Qdrant + Neo4j, optional LightRAG context, наши retrieval/fusion/rerank/evidence/LLM/API contracts. PriorArtRAG — reference для decomposition/retrieval/fusion/grounding/citation/evaluation patterns. Если буквально копировать MIT-код, сохранить copyright и LICENSE notice и указать изменённые файлы.

### Историческая заметка: nimajz/Prior-Art-Engine

URL [nimajz/Prior-Art-Engine](https://github.com/nimajz/Prior-Art-Engine) был проверен 2026-09-28 и оказался недоступен через GitHub (404). Его исходники и LICENSE не подтверждались; он исключён из активных donors и implementation dependencies. Replacement — доступный и pinned PriorArtRAG выше.

## Дополнительный reference для source adapters: mcp-prior-art

Не основной донор и не runtime/architecture dependency: [chasewhughes/mcp-prior-art](https://github.com/chasewhughes/mcp-prior-art). Проверенный файл [`src/mcp_prior_art/apis/epo.py`](https://github.com/chasewhughes/mcp-prior-art/blob/main/src/mcp_prior_art/apis/epo.py) использует async `httpx`, EPO OAuth2 client-credentials flow, `tenacity` retry/backoff, CQL search и parsing OPS response. Использовать только как reference для SRC-001 adapter structure. Перепроверять OAuth, endpoints, XML/JSON shapes, quota headers, retries и обработку ошибок по [официальной документации EPO OPS](https://www.epo.org/en/searching-for-patents/data/web-services/ops) и [fair-use policy](https://www.epo.org/en/service-support/ordering/fair-use); не копировать его детали без проверки. EPO реализация не должна зависеть от MCP server.

## Внешние API

- [EPO OPS](https://www.epo.org/en/searching-for-patents/data/web-services/ops): XML/REST, регистрация, OAuth и отдельные условия. [Fair use](https://www.epo.org/en/service-support/ordering/fair-use): недельная квота и throttling; соблюдать текущие заголовки и ограничения. Не публиковать скачанный корпус как есть.
- [OpenAlex API](https://developers.openalex.org/): брать метаданные и доступные abstract, сохранять source ID, дату обновления и URL. Проверить актуальные auth/usage limits при реализации; не планировать полный snapshot на 32 ГБ машине.

При включении стороннего кода сохранить оригинальные copyright/license notices и записать точную версию и изменённые файлы в dependency inventory.
