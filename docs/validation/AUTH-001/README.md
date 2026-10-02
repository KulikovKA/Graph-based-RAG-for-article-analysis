# AUTH-001 — сессии и базовая изоляция

Дата проверки: 2026-10-02. Объём: только AUTH-001.

Реализация опубликована в `origin/main`: `ec22c0a349148e4fbc0eedeb4f0bb199b34ff427`.
Успешный push и совпадение SHA через `git ls-remote` подтверждены до отметки выполнения.

Реализованы три auth endpoints, Argon2id, operator create/disable CLI, DB sessions
с хешами token/CSRF, expiry и revoke, смена токена при повторном login, проверка
Origin/CSRF, общий PostgreSQL fixed-window rate limiter, owner dependency и scoped
conversation helper. Публичной регистрации нет. HTTP разрешён только explicit dev
opt-in, Secure cookie по умолчанию включена. Auth errors не содержат ввода пользователя.

Критерии приёмки:

- [x] Два пользователя изолированы в реальных PostgreSQL repositories и тестовом route.
- [x] Неверный/отсутствующий CSRF и недоверенный/отсутствующий Origin отклоняются.
- [x] Logout и disable отзывают сессии; expiry и forged token дают 401.
- [x] Повторный login меняет session token, прежний токен больше не действует.
- [x] HTTP по умолчанию запрещён; opt-in проверен положительным тестом.
- [x] Лимиты user/IP/email дают 429 и Retry-After; конкурентный PostgreSQL upsert
  допускает ровно пять из двадцати запросов при лимите пять.
- [x] CLI создаёт/отключает аккаунт; пароль не попадает в stdout/argv.

Проверки: pytest tests/security tests/unit tests/contract — 187 passed, один PostgreSQL
тест skipped на host; отдельно tests/security,
tests/integration/test_repositories.py и tests/integration/test_db.py на PostgreSQL 17
в изолированных временных схемах — 21 passed, без skips. Alembic upgrade/downgrade проверены существующим
round-trip тестом. Ruff и strict mypy для изменённых auth/API/CLI модулей проходят.
Зависимости скачивались на host; PostgreSQL тесты запускались offline в
article-analysis-tests:local на private network с read-only mount проекта.
`docker compose config --quiet` и валидация Caddyfile проходят.

Решения: csrf_token — односторонняя производная случайного session token с отдельным
prefix; БД хранит только её хеш, GET session воспроизводит значение без хранения raw
secret. Сессионные токены имеют 256 бит случайности. Общий limiter переживает рестарт
API и работает между процессами; окна минутные, на границе окна возможен burst.

Оставшийся объём по плану: API-001 подключает зависимости ко всем предметным routes,
проверяет полный IDOR и отзыв на SSE; GRAPHUI-001 проверяет graph IDOR; AUTH-002
проверяет внешний TLS/perimeter. Текущий Caddy остаётся HTTP loopback профилем.
Все контейнеры закрытой backend network должны быть доверенными: Uvicorn принимает
proxy headers от этой сети, Caddy перезаписывает клиентские forwarded headers.

Проверенные первичные источники:
[argon2-cffi API](https://argon2-cffi.readthedocs.io/en/stable/api.html),
[FastAPI proxy headers](https://fastapi.tiangolo.com/advanced/behind-a-proxy/).
