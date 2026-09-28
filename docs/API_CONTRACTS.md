# Контракты API v1

JSON UTF-8, даты ISO 8601 UTC, UUID IDs. Все приватные endpoints требуют session cookie `HttpOnly; Secure; SameSite=Lax` (на HTTPS) и CSRF-защиту для mutations; на локальном HTTP dev-профиле Secure настраивается отдельно. `Idempotency-Key` обязателен для создания анализа. Ownership проверяется до обращения к кешу/индексу. API возвращает `X-Request-ID`.

| Метод / путь | Запрос | Успех |
|---|---|---|
| `POST /api/v1/auth/login` | email/password или provider token | session cookie + `{user_id}` |
| `POST /api/v1/auth/logout` | CSRF token | 204 |
| `GET /api/v1/conversations` | cursor, limit≤50 | `{items,next_cursor}` |
| `POST /api/v1/conversations` | `{title?}` | 201 `{id,title}` |
| `GET /api/v1/conversations/{id}` | — | conversation, idea current version, last runs |
| `GET /api/v1/conversations/{id}/messages` | cursor, limit≤100 | paginated messages |
| `POST /api/v1/conversations/{id}/messages` | `{content, expected_idea_version?, analyze:true}` | 202 `{message_id,run_id,status_url,events_url}` |
| `GET /api/v1/runs/{id}` | — | status, idea version, answer, source cards, graph summary |
| `GET /api/v1/runs/{id}/events` | `Last-Event-ID?` | `text/event-stream` |
| `POST /api/v1/runs/{id}/cancel` | — | 202 status |
| `GET /api/v1/runs/{id}/graph` | — | explanation subgraph |
| `GET /api/v1/runs/{id}/graph/neighbors` | node_id, cursor, limit≤20 | authorized next page |
| `GET /api/v1/sources/{document_id}` | — | metadata, allowed snippet IDs, validated external URL |
| `GET /health/live`, `/health/ready` | — | status/dependency summary |

Сообщение ограничить 8 KiB/запрос; браузер не посылает user ID. `expected_idea_version` обязателен для patch существующей идеи; при конфликте `409` с текущей версией. В ответе `run` fields: `id,status,idea_version_id,summary,feature_matches[{feature_id,evidence_ids}],differences[],sources[{document_id,title,kind,publication_date,url,evidence_ids}],coverage{sources_checked,partial,reason?},graph_url,created_at`. `summary` и `differences` имеют ссылки на evidence; неподтверждённые утверждения помечаются uncertainty.

SSE события с монотонным `id`: `run_started`, `planning`, `idea_updated`, `retrieving`, `reranking`, `analyzing`, `answer_delta`, `sources_ready`, `graph_ready`, `completed`, `failed`, `cancelled`. `data` — JSON `{run_id,seq,at,payload}`. После reconnect повторить события после `Last-Event-ID`; terminal event закрывает поток. `answer_delta` не считается финальным до `completed`. Heartbeat comment каждые ~15 секунд; не сохранять токены бесконечно, compact older deltas в snapshot после terminal state.

Ошибки: `{error:{code,message,request_id,details?}}`. `400` invalid input, `401` unauthenticated, `403` forbidden, `404` unknown/other user's object (допускается единый 404), `409` version conflict, `413` oversized, `422` schema error, `429` rate limit (`Retry-After`), `503` dependency unavailable. Не раскрывать внутренние пути, stack trace, model prompt, сырой EPO response. Контракт OpenAPI генерируется из Pydantic и фиксируется snapshot test.
