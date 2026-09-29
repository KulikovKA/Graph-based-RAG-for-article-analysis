# Архитектурные решения

Формат: статус, контекст, решение, последствия. Изменения фиксировать новой записью, старые решения не переписывать без следа.

## ADR-001 — Модульный монолит, 2026-09-28, accepted

Один FastAPI пакет и worker с общей кодовой базой; инфраструктура через Compose. Малое число пользователей и один ПК не оправдывают микросервисы. Последствие: нужны чёткие Python интерфейсы и запрет прямых зависимостей domain от API adapters.

## ADR-002 — PostgreSQL истина, 2026-09-28, accepted

Versions/runs/evidence живут в транзакционном хранилище. Redis только cache, Neo4j/Qdrant — производные индексы. Последствие: outbox, идемпотентная переиндексация, backup PostgreSQL.

## ADR-003 — LightRAG context adapter, 2026-09-28, conditional

Использовать подтверждённые query/context и custom-KG интерфейсы LightRAG после integration spike. Доменная типизация и ownership принадлежат приложению. Последствие: дополнительные storage namespace и версия зависимости; если custom KG не соблюдает provenance, ограничить LightRAG контекстным поиском. См. [REPO_MAP.md](REPO_MAP.md).

### Уточнение ADR-003 по ARCH-001, 2026-09-29, accepted with restrictions

Исходное conditional-решение выше сохранено как история. На commit `453dce83d6d0354a06e46c8d4029a0895c4e054b` выполнен [smoke Neo4j/Qdrant](validation/ARCH-001/README.md): `ainsert_custom_kg`, `aquery(only_need_context=True)`, `aquery_data`, отсутствие LLM-вызовов при заданных keywords, стабильное число векторов при повторе, пустой второй workspace.

Custom KG не удовлетворяет нашим provenance invariants: один alias сохраняет связь только с последним чанком, одинаковый текст перезаписывает принадлежность документу, путь сокращается до basename. В коде также прямо отсутствует document-level crash recovery guarantee для этого метода. Принимаем предусмотренный fallback: LightRAG — отключаемый дополнительный context adapter только для публичного корпуса. Наш доменный Neo4j, PostgreSQL revisions/offsets/evidence и ownership остаются авторитетными. Результаты LightRAG допускаются в evidence pack только после однозначного разрешения и проверки в нашем хранилище; устаревшие/неразрешимые результаты отбрасываются. `reference_id` донора не является нашим evidence ID.

Не использовать прямой custom KG импорт как перенос доменного графа. LightRAG namespaces/коллекции отделить от продукта; исключить случайные `NEO4J_WORKSPACE`/`QDRANT_WORKSPACE` overrides. LR-001 сохраняет gates на update/delete/revision mapping, timeout и работу основного retrieval при отключённом адаптере. Этот smoke не подтверждает качество поиска, безопасность всех tenant-сценариев или восстановление после сбоя.

## ADR-004 — Caddy + статический React, 2026-09-28, accepted

Vite/React/TypeScript даёт достаточно интерактивности для чата/графа без server-side frontend runtime. Caddy упрощает TLS. Sigma из LightRAG служит референсом, наш UI показывает только scoped subgraph.

## ADR-005 — SSE и PostgreSQL job queue, 2026-09-28, accepted

Поток статуса/ответа односторонний; SSE проще WebSocket. `run_events` обеспечивает reconnect. Одного worker достаточно для CPU inference; Redis не становится обязательной очередью. Последствие: нужно ограничить retention event deltas и вводить backpressure.

## ADR-006 — Проверяемый вывод, 2026-09-28, accepted

Каждое существенное утверждение содержит evidence ID из immutable snapshot; ответ формулируется в пределах найденного корпуса, без вывода о юридической новизне. Сбой/пробел источника явно показывается пользователю.

## ADR-007 — Замена prior-art reference donor, 2026-09-29, accepted

`nimajz/Prior-Art-Engine` был проверен и оказался недоступен через GitHub; его код и LICENSE не подтверждены, поэтому зависимость от него исключена. Найден доступный replacement `ABHIJEET-MUNESHWAR/PriorArtRAG`, pinned commit `fcaad8482c7df5d8106d4041c45d732f18d8c295`, LICENSE MIT. Используем только проверенные retrieval/decomposition/fusion/grounding/citation/evaluation patterns из путей, перечисленных в [REPO_MAP.md](REPO_MAP.md). Он не является основой приложения. Не переносить его BM25/HNSW/sharding, GraphQL/Kafka/Prometheus/Grafana/CQRS; сохранять upstream copyright/license при буквальном копировании. Наша архитектура остаётся Qdrant + Neo4j + optional LightRAG context.

### Уточнение ADR-007 по ARCH-001, 2026-09-29, accepted

Закреплённый commit, MIT notice и все используемые файлы повторно проверены; SHA-256 в [inventory](donors.lock.json). Контракты decomposition/fusion/pipeline/reranker/grounding/ports разобраны в [отчёте](validation/ARCH-001/README.md). Реальный repair loop расположен в `app/service.py`, лимит настраивается в `config/settings.py` (default 1). В нашем контракте остаётся `LLM drafts → deterministic citation/evidence validator → repair once → deterministic safe fallback`.

CitationVerifier проверяет маркировку и буквальные цитаты, а не semantic entailment; английские regex нельзя считать достаточными для русского текста. Default FeatureReranker не задаёт выбор нашей CPU-модели. Pipeline деградирует при `RerankerUnavailableError`, но не гарантирует fallback для всех retrieval ошибок. Численные результаты upstream EVALUATION не являются нашими измерениями. Ограничения архитектурного reuse из исходного ADR сохранены.

## ADR-008 — Run lifecycle и публикация после проверки, 2026-09-29, accepted

ARCH-002 выявил конфликт failed/fallback и streaming до валидации (R01–R04). Единые statuses: pending/running/completed/failed/cancelled, outcome отдельно: analysis/safe_fallback/no_evidence/clarification. Проверенный fallback — completed; invalid fallback — failed. Сырой draft/repair не выходит из worker. AnswerV1, terminal state и events коммитятся атомарно с lease fencing/cancel CAS. Idempotency scoped owner+conversation; один нетерминальный run на conversation. expected_idea_version проверяется при приёме и через CAS при асинхронном patch. После SSE compaction клиент получает snapshot/high-water reset. Точный контракт — DATA_MODEL/API_CONTRACTS. Последствие: видимый текст приходит после валидации, model TTFT не равен времени до ответа UI.

## ADR-009 — Evidence, historical scope и восстанавливаемый граф, 2026-09-29, accepted

R05–R08/R12: chunk UUID указывает на revision, evidence UUID — на выбранный span конкретного snapshot. Единый AnswerV1 использует ClaimV1 без API-переименования полей. Snapshot rows с FK удерживают старые chunks; source_run_id той же conversation разрешает historical follow-up. Public metadata endpoint не раскрывает private evidence IDs. Graph facts сначала сохраняются в PG; Neo4j — projection с revision-specific document keys. Optional LightRAG не участвует в обязательном activation barrier Qdrant+domain graph. Generation membership фиксируется на retrieval и проверяется в PG после чтения индексов. UI graph ограничен evidence того же run. Это уточняет ADR-002/003/006, не меняя состав системы.

## ADR-010 — План зависимостей и scope freeze, 2026-09-29, accepted

R09–R14: auth/session gate перенесён до API; embedding/graph/rerank получают явную dependency на provider/CPU gate. Введён ранний 10-case dev fixture, полный 100-case evaluation отделён от harness и экспертной разметки. DB schema/repositories, provider/веса, jobs/events и sessions/внешний периметр разбиты на отдельно проверяемые deliverables. Mermaid и сводка генерируются из одинаковых Depends карточек и проверяются на циклы. Cache keys учитывают owner/query/generation/config/cursor. Bootstrap Compose до весов работает локально; минимальные health/redaction входят в ранние задачи. Детальный список дефектов, оценка моделей/стоимости и проверка — [ARCH_REVIEW](ARCH_REVIEW.md). Freeze относится к контрактам planning package; production readiness требует оставшихся implementation gates.
