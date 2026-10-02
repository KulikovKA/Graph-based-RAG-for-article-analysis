# API-001 — API v1 и durable SSE

Проверено 2026-10-02 перед UI-001 по указанию пользователя.

Реализованы conversations/messages с пагинацией, atomic acceptance и Idempotency-Key,
GET run, cancel, scoped evidence, public sources и DB queue readiness. Все предметные
маршруты используют AUTH-001; чужие/неизвестные объекты возвращают одинаковый 404
до чтения private данных. Входы ограничены 8 KiB UTF-8 content / 16 KiB envelope,
неизвестные поля запрещены. Ошибки 400/401/403/404/409/413/422/429/503 имеют request ID
и не содержат rejected values, SQL, prompts или private drafts.

RunV1 расширен существующими публичными projections. SSE использует только durable
события из JOB-002, allowlist Pydantic payloads, Last-Event-ID и snapshot reset.
Shared-lock транзакция связывает ownership, snapshot и high-water с compaction.
Live tail опрашивает БД после коротких транзакций; race replay/tail не теряет commit.
Сессия перепроверяется перед выдачей каждого frame и при polling. Пакет ограничен
16 events, отдельной очереди клиента нет, ASGI send имеет timeout 10 секунд;
disconnect не отменяет run. Heartbeat каждые 15 секунд, Caddy flush_interval=-1.
ASGI middleware добавляет request ID без дополнительной очереди поверх SSE.

Критерии приёмки:

- [x] 202/409/413/429/503 и безопасные validation errors.
- [x] Owner scope на conversations, runs, evidence, SSE replay/reset/cancel.
- [x] GET completed доступен до presentation delivery; поздний cancel сохраняет ответ.
- [x] Valid/missing/stale/future/terminal cursor; compaction заменяет snapshot.
- [x] Revoked session закрывает live stream; slow send закрывает iterator.
- [x] Public DTO/SSE не содержат приватных AnalysisV1/config fields.
- [x] OpenAPI snapshot: tests/fixtures/api/openapi.json; typed SSE fixture: sse.json.
- [x] Настоящий Caddy: первый frame получен при pending run менее чем за 2 секунды,
  затем terminal commit передаёт deltas и completed на том же соединении.

Воспроизведение: `python -m pytest tests/unit tests/contract tests/security`:
190 passed, 8 PostgreSQL/proxy tests skipped на host. PostgreSQL tests запускаются
в изолированных схемах с TEST_DATABASE_URL; проверка proxy дополнительно требует
TEST_PROXY_URL, Caddy, обращающийся к API на port 8000, и свободный port 8000 внутри
test container. Test fixture поднимает настоящий Uvicorn и затем останавливает его.
Регрессия PostgreSQL/API/JOB/STATE/AUTH: 59 passed без skips, включая Caddy.
Ruff и strict mypy изменённых модулей проходят.

Ограничения: GraphV1 остаётся GRAPHUI-001, graph_url=null. Нет inference generation
в HTTP handlers: analysis продолжает обслуживать существующий worker. Проверка Caddy
использует synthetic result и реальные DB commits; качество моделей не переоценивалось.
Полноценный external TLS gate остаётся AUTH-002. Readiness проверяет DB queue;
расширенные degraded checks зависимостей относятся к OBS-001.

Источники: [FastAPI error handling](https://fastapi.tiangolo.com/tutorial/handling-errors/),
[Starlette StreamingResponse](https://www.starlette.dev/responses/).
