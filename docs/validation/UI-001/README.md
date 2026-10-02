# UI-001 — адаптивный чат и источники

Проверено 2026-10-02. API-001 предварительно реализована и опубликована по указанию
пользователя (commit 7bfc784). UI подключён к реальному API по same-origin `/api/v1`.

Изменения: login/session/logout, история и создание диалогов, чат и optimistic
acceptance, indicator версии идеи, follow-up и source_run_id, SSE status/elapsed/counts,
cancel, проверенный сворачиваемый «Ход анализа», постепенное отображение сохранённых
фрагментов, карточки/evidence/external URLs, partial/fallback/no-evidence notices.
Дедупликация по run+seq, проверка chunk_index/presentation_id/SHA-256; при gap/hash
mismatch запрос GET, reset заменяет частичный ответ/summary. Completed заменяет DTO
и сразу показывает полный ответ; cancel при presentation не стирает completed result.

Секреты и приватная история не сохраняются в browser storage. React отображает
ответ/цитаты обычным текстом; сырой HTML не исполняется. URL разрешены только для
HTTPS первоисточников EPO/OpenAlex/DOI/Google Patents с noopener/noreferrer. Hash
проверяется локально через закреплённый @noble/hashes, включая HTTP dev на LAN без
Web Crypto secure context. Веса моделей и пользовательские данные не добавлялись.

Критерии приёмки:

- [x] Login, новый запрос и follow-up на ширинах 375 и 1280 px.
- [x] Citation открывает run-scoped evidence карточки; external URL безопасен.
- [x] Вопрос по второму источнику отправляет source_run_id и текущую idea version.
- [x] Фактические стадии/counts, elapsed, cancel; нет выдуманных процентов.
- [x] Verified summary и gradual answer; reduced-motion и «Показать целиком».
- [x] Reconnect передаёт Last-Event-ID, не дублирует ответ; reset заменяет состояние.
- [x] Gap, wrong run/chunk/hash отклоняются; чужие unknown event fields не выводятся.
- [x] Partial/no-evidence/fallback/historical follow-up отображаются явно.
- [x] Logout очищает private UI state; источники с HTML показаны безопасным текстом.
- [x] Browser display marks отдельно для first_progress/summary/delta после paint.
- [x] Сквозной собранный UI → Caddy → Uvicorn/API → PostgreSQL → synthetic worker.

Проверки:

- `npm test`: 7 тестов reducer/parser, включая UTF-8/CRLF network boundaries.
- `npm run test:e2e`: 18 fixture browser checks (9 сценариев × 2 viewport).
- `UI_SMOKE_URL=... npm run test:e2e -- live.spec.ts`: 2 live checks без route mocks.
  Настоящий login, CSRF, POST/202, SSE publication, follow-up, версия 1→2 и reload
  durable history проходят. БД и API не опубликованы; только временный Caddy на
  loopback:5180. Временные контейнеры и схема удалены после проверки.
- TypeScript, ESLint, production build, Ruff/strict mypy smoke script проходят.
- Build: JS около 223 kB / 72 kB gzip, CSS около 14 kB / 4 kB gzip; SSR нет.

Визуально проверены [desktop](desktop.png) и [mobile](mobile.png). Это synthetic
fixtures, не пользовательские данные. Скриншоты содержат буквальный HTML sentinel
в цитате для проверки отсутствия исполнения. Horizontal overflow отсутствует.

Display hooks: Performance marks `analysis:<run_id>:first_progress_display`,
`first_summary_display`, `first_delta_display`. Они измеряют появление элементов
после browser paint, не provider TTFT. Для результата, полученного целиком через GET,
delta mark может отсутствовать: неизвестное значение не подменяется нулём.

Воспроизведение live smoke: scripts/ui_api_smoke.py создаёт собственную схему через
Alembic и тестовый аккаунт ui-smoke@example.test с synthetic-smoke-password, запускает
API:8000 и ограниченный synthetic worker. Настроить UI_SMOKE_ORIGIN под URL Caddy,
проксирующего `api:8000` и раздающего frontend/dist; TEST_DATABASE_URL передать через
env. API должен иметь private network alias `api`. Caddy подключить к private и egress
сетям; publish только на loopback. Завершить smoke API штатно (SIGTERM) для cleanup.
Live tests используют UI_SMOKE_URL; по умолчанию эти два теста skipped.

Ограничения: live smoke проверяет UI/transport/storage с synthetic no-evidence result;
качество моделей не переоценивалось. Graph UI остаётся GRAPHUI-001, external TLS gate
— AUTH-002. Карточки показывают plain text вместо интерпретации произвольного Markdown.
Полная history загружается через paginated API; при 429 отображается Retry-After.

Источники: [Playwright visual testing](https://playwright.dev/docs/test-snapshots),
[Readable stream decoding](https://developer.mozilla.org/en-US/docs/Web/API/TextDecoderStream).
