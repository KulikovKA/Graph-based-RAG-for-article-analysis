# Память и кеш

Durable memory: PostgreSQL хранит conversation, сообщения, immutable idea versions, run и evidence snapshot. Новое сообщение формирует patch против явной версии идеи; optimistic concurrency предотвращает lost update. Краткая `conversation_summary` — вычисляемая подсказка LLM, не истина; исходные сообщения сохраняются по retention policy. Объяснение старого патента читает evidence старого run. Смена признаков требует новую версию и, если semantic state hash изменился, новый retrieval.

Redis хранит только восстановимые результаты и rate-limit counters. Ключи всегда с префиксом версии и hash: `retr:v1:{tenant_scope}:{idea_hash}:{index_version}:{retrieval_config_hash}`, `rerank:v1:{candidate_hash}:{model_version}`, `graph:v1:{run_id}:{page}`, `llm:v1:{role}:{input_hash}:{model}:{prompt_version}`. User-specific данные не попадают в shared cache; tenant_scope — HMAC user ID, не email. Кешированный ответ можно использовать только после отдельной проверки ownership run и совпадения всех версий.

| Слой | Начальный TTL | Инвалидация |
|---|---:|---|
| public metadata | 24 ч | новая source revision |
| retrieval candidates | 30 мин | новая active index version |
| rerank scores | 24 ч | model/config version |
| graph page | 10 мин | новый run/graph version |
| selected LLM output | выключен для MVP | включать лишь для детерминированного identical input, model/prompt version |
| rate limits | скользящее окно | expiry |

Job status и SSE events находятся в PostgreSQL; Redis pub/sub может лишь ускорять доставку. При потере Redis система работает медленнее, но не теряет idea state или результаты. Избегать кеша полного сырого prompt и любых секретов. `cache hit/miss` логируется без содержимого.
