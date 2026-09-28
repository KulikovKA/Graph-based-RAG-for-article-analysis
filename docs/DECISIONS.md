# Архитектурные решения

Формат: статус, контекст, решение, последствия. Изменения фиксировать новой записью, старые решения не переписывать без следа.

## ADR-001 — Модульный монолит, 2026-09-28, accepted

Один FastAPI пакет и worker с общей кодовой базой; инфраструктура через Compose. Малое число пользователей и один ПК не оправдывают микросервисы. Последствие: нужны чёткие Python интерфейсы и запрет прямых зависимостей domain от API adapters.

## ADR-002 — PostgreSQL истина, 2026-09-28, accepted

Versions/runs/evidence живут в транзакционном хранилище. Redis только cache, Neo4j/Qdrant — производные индексы. Последствие: outbox, идемпотентная переиндексация, backup PostgreSQL.

## ADR-003 — LightRAG context adapter, 2026-09-28, conditional

Использовать подтверждённые query/context и custom-KG интерфейсы LightRAG после integration spike. Доменная типизация и ownership принадлежат приложению. Последствие: дополнительные storage namespace и версия зависимости; если custom KG не соблюдает provenance, ограничить LightRAG контекстным поиском. См. [REPO_MAP.md](REPO_MAP.md).

## ADR-004 — Caddy + статический React, 2026-09-28, accepted

Vite/React/TypeScript даёт достаточно интерактивности для чата/графа без server-side frontend runtime. Caddy упрощает TLS. Sigma из LightRAG служит референсом, наш UI показывает только scoped subgraph.

## ADR-005 — SSE и PostgreSQL job queue, 2026-09-28, accepted

Поток статуса/ответа односторонний; SSE проще WebSocket. `run_events` обеспечивает reconnect. Одного worker достаточно для CPU inference; Redis не становится обязательной очередью. Последствие: нужно ограничить retention event deltas и вводить backpressure.

## ADR-006 — Проверяемый вывод, 2026-09-28, accepted

Каждое существенное утверждение содержит evidence ID из immutable snapshot; ответ формулируется в пределах найденного корпуса, без вывода о юридической новизне. Сбой/пробел источника явно показывается пользователю.

## ADR-007 — Замена prior-art reference donor, 2026-09-29, accepted

`nimajz/Prior-Art-Engine` был проверен и оказался недоступен через GitHub; его код и LICENSE не подтверждены, поэтому зависимость от него исключена. Найден доступный replacement `ABHIJEET-MUNESHWAR/PriorArtRAG`, pinned commit `fcaad8482c7df5d8106d4041c45d732f18d8c295`, LICENSE MIT. Используем только проверенные retrieval/decomposition/fusion/grounding/citation/evaluation patterns из путей, перечисленных в [REPO_MAP.md](REPO_MAP.md). Он не является основой приложения. Не переносить его BM25/HNSW/sharding, GraphQL/Kafka/Prometheus/Grafana/CQRS; сохранять upstream copyright/license при буквальном копировании. Наша архитектура остаётся Qdrant + Neo4j + optional LightRAG context.
