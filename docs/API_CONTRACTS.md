# Контракты API v1

JSON UTF-8, даты ISO 8601 UTC, собственные IDs — UUID. Session cookie `HttpOnly; Secure; SameSite=Lax` на HTTPS, CSRF для mutations. HTTP допускается только в явно включённом dev-профиле; Secure настраивается отдельно. Сервер определяет user ID из сессии и проверяет ownership до кеша/индекса. Все ответы имеют `X-Request-ID`. Неизвестный и чужой объект возвращают одинаковый 404.

## Endpoints

| Метод / путь | Запрос | Успех |
|---|---|---|
| `POST /api/v1/auth/login` | `{email,password}`, проверка Origin | 200 session cookie + `{user_id,csrf_token}` |
| `GET /api/v1/auth/session` | session cookie | 200 `{user_id,csrf_token}` для reload UI |
| `POST /api/v1/auth/logout` | CSRF header | 204, revoke session |
| `GET /api/v1/conversations` | cursor, limit≤50 | `{items,next_cursor}` |
| `POST /api/v1/conversations` | `{title?}` | 201 `{id,title}` |
| `GET /api/v1/conversations/{id}` | — | conversation, current idea/version, last runs |
| `GET /api/v1/conversations/{id}/messages` | cursor, limit≤100 | paginated messages |
| `POST /api/v1/conversations/{id}/messages` | `{content,expected_idea_version,source_run_id?,analyze:true}`; `Idempotency-Key` | 202 `{message_id,run_id,status_url,events_url}` |
| `GET /api/v1/runs/{id}` | — | RunV1 |
| `GET /api/v1/runs/{id}/events` | `Last-Event-ID?` | `text/event-stream` |
| `POST /api/v1/runs/{id}/cancel` | CSRF header | 202 `{status,cancel_requested:true}`; уже terminal → 200 текущий status |
| `GET /api/v1/runs/{id}/evidence/{evidence_id}` | — | EvidenceV1 только из snapshot этого run |
| `GET /api/v1/runs/{id}/graph` | — | GraphV1 после GRAPHUI-001 |
| `GET /api/v1/runs/{id}/graph/neighbors` | node_id, cursor?, limit≤20 | GraphV1 page после GRAPHUI-001 |
| `GET /api/v1/sources/{document_id}` | authenticated session | Public metadata + validated URL; без приватных run/evidence IDs |
| `GET /health/live`, `/health/ready` | — | 200/503 согласно ARCHITECTURE; без адресов/секретов зависимостей |

Локальные аккаунты создаются операторской CLI-командой в AUTH-001; открытая регистрация и provider-token login вне MVP. OIDC подключается позже через auth interface. Лимит content — 8 KiB UTF-8; request envelope также ограничен. MVP принимает только analyze=true; произвольный client user_id запрещён.

`expected_idea_version` обязателен для всех новых сообщений: 0 до создания идеи, затем текущий version_no. Проверка синхронная: 409 VERSION_CONFLICT, либо RUN_IN_PROGRESS для второго нетерминального run conversation. Повтор того же idempotency key/payload возвращает тот же run даже после изменения текущей версии; другой payload с тем же ключом — 409 IDEMPOTENCY_CONFLICT. Проверки и unique constraints описаны в [DATA_MODEL](DATA_MODEL.md). `source_run_id` обязателен для объяснения сохранённого источника; UI передаёт run, на карточке которого задан вопрос. Если текст предполагает такой intent без source_run_id, planner возвращает clarification, а не угадывает чужой/случайный snapshot. Поздний worker conflict после 202 возвращается в run.error_code, не новым HTTP 409.

## RunV1 и единый AnswerV1

Если передан source_run_id, его ownership и принадлежность conversation проверяются при приёме: чужой/неизвестный или из другой conversation → 404; нетерминальный/неуспешный source run → 409 SOURCE_RUN_NOT_COMPLETED. Отсутствие source_run_id при распознанном explain intent даёт completed/clarification. Историческое объяснение связывается с idea_version исходного run, сохраняя current version conversation.

RunV1: `{id,status,stage,idea_version_id?,source_run_id?,outcome?,answer?,sources,coverage,graph_url?,created_at,completed_at?,error_code?}`. `status ∈ {pending,running,completed,failed,cancelled}`; authoritative state machine — DATA_MODEL. До completed answer/outcome null. `sources` пуст до snapshot commit; после него содержит metadata только из разрешённого snapshot. `graph_url=null` до GRAPHUI-001 или при отсутствии graph view. GET существующего failed run возвращает 200 с error_code.

Общий для LLM validator, хранения и API AnswerV1 (без переименования matches):

- `schema_version: 1`.
- `summary: ClaimV1[]`.
- `matches: {feature_id,document_id,claims:ClaimV1[]}[]`.
- `differences: {feature_id,claims:ClaimV1[]}[]`.
- `limitations: {code,message}[]` — shell-generated coverage/validation notices из allowlist, не произвольный LLM текст.
- `followup_suggestions: string[]` — только вопросы/предложения действия, без новых фактических выводов.

ClaimV1: `{text,evidence_ids:UUID[],quotes:[{evidence_id,start,end,text}]}`. Содержательные claims имеют непустые evidence_ids из snapshot текущего run; quote start/end — code-point offsets внутри EvidenceV1.quoted_span, точное совпадение обязательно. Для matches все evidence entries принадлежат указанному document_id; feature_id принадлежит связанной idea_version. Validator не доказывает смысловую верность пересказа: uncertainty не позволяет обойти проверку IDs/quotes.

Для no_evidence/clarification summary/matches/differences пусты; ограничения/уточняющий вопрос строит shell. Для safe_fallback — проверенные короткие выдержки с IDs и allowlist notice о деградации; проверяется тем же валидатором. Для `outcome=analysis` LLM draft становится AnswerV1 только после проверки и добавления shell limitations. Coverage: `{sources:[{source,status,reason_code?}],channels:[{channel,status,reason_code?}],partial,historical}`; source status `ok|empty|unavailable|not_configured|not_requested`, channel status `ok|empty|unavailable|disabled`. Источник, не вызванный при работе по локальному snapshot, имеет not_requested; это не утверждение, что внешний API проверен. partial вычисляет shell по недоступным необходимым источникам/каналам, отключённый optional LightRAG сам по себе partial не создаёт.

Sources: `{document_id,revision_id,title,kind,publication_date?,url,evidence_ids}`. EvidenceV1: `{evidence_id,document_id,revision_id,chunk_id,section,span_start,span_end,quoted_span,source_url}`. Membership и ownership проверяются независимо от того, что исходный документ публичен. Старые snapshots сохраняют старые metadata/offsets; endpoint sources показывает актуальную публичную metadata и не заменяет run-scoped карточку.

## GraphV1 (P1)

`{run_id,graph_version,nodes,edges,next_cursor?,truncated}`. Узел: `{id,type,label,document_id?,revision_id?,feature_id?,evidence_ids}`; ребро: `{id,source,target,type,evidence_ids}`. id — opaque строка API, не internal Neo4j ID. Allowlist типов и исключения synthetic edges — [GRAPH_SCHEMA](GRAPH_SCHEMA.md). Неизвестный/не входящий в view node_id — 404; неверный cursor — 400. Cursor подписан и привязан к owner/run/graph_version/node/filter/limit. Раскрытие не добавляет источники вне snapshot run. Начальный cap 30 nodes/50 edges, page cap 20 новых nodes/40 edges, один hop; полный UI view cap 100 nodes/200 edges с предложением отдельного поиска для расширения.

## SSE и публикация

События: `run_started`, `planning`, `idea_updated`, `retrieving`, `reranking`, `analyzing`, `run_requeued`, `sources_ready`, `graph_ready`, `answer_delta`, `completed`, `failed`, `cancelled`; graph_ready только при включённом P1 view. Envelope `{run_id,seq,at,payload}`, SSE id = sequence_no внутри run. UI дедуплицирует `(run_id,seq)`.

Модельный draft/repair не попадает в SSE или messages. После валидации транзакция сохраняет AnswerV1, terminal status, проверенные answer_delta (если нужны) и completed. Только после commit publisher отдаёт эти события. До этого разрешены лишь progress и проверенные source metadata. answer_delta — фрагменты уже утверждённого отображения ответа; окончательный DTO берётся из GET run/completed. TTFT модели и время до видимого ответа — разные метрики.

После Last-Event-ID отдавать сохранённые события с большим seq и terminal event, затем закрыть stream. Heartbeat comment ~15 секунд. Начальный retention событий — 24 часа после terminal; snapshot хранится по run retention. Для отсутствующего/устаревшего cursor после compaction сервер отдаёт transport-событие `run_snapshot` с RunV1, текущим high-water seq и `reset=true`, затем события после high-water; terminal snapshot закрывает поток. Для ещё действительного cursor replay обычный. Cursor больше high-water — 400. Snapshot/high-water читаются согласованно, чтобы reconnect не потерял terminal state.

## Ошибки и gates

`{error:{code,message,request_id,details?}}`: 400 invalid cursor/input, 401 unauthenticated, 403 invalid CSRF, 404 unknown/other owner, 409 conflict, 413 oversized, 422 schema, 429 rate limit с Retry-After, 503 durable queue unavailable. Не выдавать stack traces, prompts, raw source responses. OpenAPI snapshot и негативные тесты обязательны в API-001; GraphV1 routes получают отдельный P1 gate GRAPHUI-001 и не блокируют P0 API.
