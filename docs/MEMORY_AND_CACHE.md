# Память и кеш

Durable memory: PostgreSQL хранит conversation, сообщения, immutable idea versions, run и evidence snapshot. Новое сообщение принимается с expected_idea_version и создаёт durable job; patch применяется один раз через CAS. `conversations.summary_json` с summary_until_message_id — вычисляемая подсказка, не истина. Объяснение старого патента требует source_run_id той же conversation и копирует его historical snapshot, даже если индекс обновлён. Смена признаков требует новую версию и при изменении semantic state hash — новый retrieval. State machine и правила повторов — DATA_MODEL.

Redis хранит только восстановимые результаты и rate-limit counters. tenant_scope — HMAC user ID с версией ключа, не email. Ключи:

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
