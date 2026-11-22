# Память и кеш

PostgreSQL уже хранит сообщения, версионную идею и исследования. [Сервис чатов](../src/app/services/conversations.py) предоставляет поля и операции сводки, worker читает её при подготовке контекста. Обновление summaries, выбор релевантной истории и подключение [существующего Redis-адаптера](../src/app/integrations/redis_cache.py) к пайплайну входят в APP-MEM-001. Переименование и удаление относятся к APP-CHAT-001.

Durable memory: PostgreSQL хранит conversation, сообщения, immutable idea versions, run и evidence snapshot. Новое сообщение принимается с expected_idea_version и создаёт durable job; patch применяется один раз через CAS. `conversations.summary_json` с summary_until_message_id — вычисляемая подсказка, не истина. Объяснение старого патента требует source_run_id той же conversation и копирует его historical snapshot, даже если индекс обновлён. Смена признаков требует новую версию и при изменении semantic state hash — новый retrieval. State machine и правила повторов — DATA_MODEL.

В целевом профиле Redis хранит восстановимые результаты и вспомогательные rate-limit counters. `tenant_scope` — HMAC user ID с версией ключа. Формы ключей ниже описывают прежний адаптер:

- `retr:v2:{tenant_scope}:{query_hash}:{idea_hash}:{generation_id}:{retrieval_config_hash}`.
- `rerank:v2:{tenant_scope}:{query_hash}:{candidate_revision_span_hash}:{model_version}:{rerank_config_hash}`.
- `graph:v2:{tenant_scope}:{run_id}:{graph_version}:{node_id}:{cursor_hash}:{filter_limit_hash}`.
- `llm:v2:{tenant_scope}:{role}:{idea_version_id}:{snapshot_hash}:{input_hash}:{model}:{prompt_version}:{schema_version}` — выключен в MVP.

query_hash учитывает текст вопроса, constraints и bounded subqueries; candidate hash — упорядоченные IDs/revisions/spans. Retrieval cache хранит candidate refs, не персональные feature_matches; после hit всё равно проверяется generation membership, evidence создаётся для нового run. Перед любым cache lookup проверять сессию/ownership; перед выдачей результата — snapshot membership. Ни query-dependent rerank, ни частный graph view не попадают в shared cache. Только публичная metadata кешируется отдельно по source/revision. При удалении пользователя инвалидировать tenant scope; TTL не заменяет revoke/ownership.

| Слой | Начальный TTL | Инвалидация |
|---|---:|---|
| public metadata | 24 ч | новая source revision |
| retrieval candidates | 30 мин | новая active index version |
| rerank scores | 24 ч | model/config version |
| graph page | 10 мин | новый run/graph version |
| selected LLM output | выключен для MVP | включать лишь для детерминированного identical input, model/prompt version |
| rate limits | скользящее окно | expiry |

Job status и SSE events находятся в PostgreSQL; Redis pub/sub может лишь ускорять доставку. При потере Redis система работает медленнее, но не теряет idea state или результаты. Избегать кеша полного сырого prompt и любых секретов. `cache hit/miss` логируется без содержимого.

## Целевые дополнения

- Контекст подбирается внутри той же conversation после авторизации. Текущая idea_version, явный source/run ref, последние сообщения и прежние релевантные фрагменты имеют приоритет перед краткой summary. Сводка хранит watermark и версии сборки и может быть восстановлена из исходных сообщений. Она не заменяет доказательство и не включает приватные рассуждения.
- Вопрос о сохранённом источнике повторно использует точный snapshot и версию связанного исследования даже после перезапуска. Если источник нельзя однозначно восстановить из разрешённой истории, запрашивается уточнение. Смена смыслового признака или запроса на новые сведения запускает поиск с подходящей generation.
- При wiring кэшей добавляется `conversation_id` или иной явный scope, если ключ зависит от приватного контекста. Версия ключей и инвалидация учитывают membership/generation, revisions, embeddings/linker/reranker, graph namespace и конфигурацию. Для Explorer ключ включает scope, graph version, node, фильтры и cursor. Hit перечитывает разрешённые ссылки, точные evidence всегда подтверждаются по durable snapshot. Изменение конфигурации не подменяет исторический snapshot.
- Удаление чата отзывает доступ и инвалидирует его кэши до фоновой очистки; проверяется защита от stale worker. Отказ Redis означает miss для кэшей. Обязательная авторизация и бюджеты продолжают действовать через приложение и PostgreSQL. [Модель данных](DATA_MODEL.md) · [Безопасность](SECURITY.md)
