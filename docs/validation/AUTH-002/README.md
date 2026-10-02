# AUTH-002 — периметр и внешний HTTPS gate

Дата: 2026-10-02. Статус: **ожидает внешнего доступа**. Код и локальные проверки
готовы; внешний demo не разрешён. Публичный домен/TLS не предоставлен и не проверен,
а аудит работающих контейнеров выявил публикации инфраструктурных портов.

Изменения:

- `docker/Caddyfile.prod`: явные TLS 1.2–1.3, HSTS на HTTPS; оба Caddyfile отключают
  admin API. Loopback-публикации Compose сохранены.
- API: CORS с точным allowlist из AuthSettings, credentials и ограниченным списком
  методов/headers; неверный и повторяющийся Origin получает 403 до чтения маршрутов.
  GET без Origin остаётся доступен только с действующей сессией; CSRF mutations
  сохраняется. ASGI middleware не буферизует SSE.
- `tests/security/test_perimeter.py`: SSRF redirect matrix (пять HTTP redirect codes
  × восемь опасных URL), запрет URL вместо source ID, CORS/CSRF, общие rate limits,
  закрытие уже открытого SSE после revoke, запрет SSE/evidence после ротации,
  logout/disable, проверки Compose и runtime port audit.
- `scripts/audit_perimeter.py`: реальные port bindings и host network без env/секретов;
  `scripts/check_perimeter_tls.py`: проверка сертификата и proxy через TLS без
  `verify=False`. Dockerfile.tests включает файлы для автономного запуска новых тестов.
- OpenAPI fixture дополнен двумя уже существовавшими graph-маршрутами. Проверка
  выявила устаревший snapshot; публичные DTO и маршруты не изменялись.

## Проверки

- PostgreSQL в закрытой Compose network, временные схемы с миграциями и очисткой:
  **97 passed, 1 skipped**. Запущены perimeter/isolation, API/graph contracts,
  OpenAlex/EPO integration и skeleton. Затем пропущенный live SSE flush smoke
  из API-001 выполнен отдельно: **1 passed** с `TEST_PROXY_URL=http://auth002-proxy`
  через временный Caddy в существующей backend network без host port mapping.
  Подтверждён первый frame до terminal commit и последующая выдача answer_delta/completed.
  Временный upstream направлялся на тестовый API; production Caddy не перенастраивался.
  Sidecar и временный файл конфигурации удалены.
- Автономный image из `docker/Dockerfile.tests` собран; без workspace mounts
  весь `tests/security/test_perimeter.py` прошёл на PostgreSQL: **52 passed**.
- Ruff: изменённые Python-файлы проходят. Mypy: main/middleware и оба новых скрипта
  проходят. Предупреждение Starlette о deprecated AnyIO alias существующее.
- `docker compose --profile prod config --quiet`: успешно с synthetic значением
  обязательной NEO4J_PASSWORD; конфигурация с секретами в отчёт не выводилась.
- Оба Caddyfile прошли `caddy validate` в существующем image, Caddy **2.11.4**.
- Отдельный временный Caddy с production Caddyfile, двумя проектными networks и
  loopback-портами 18081/18443: TLS 1.2 и 1.3 с проверкой hostname/цепочки через
  явно указанный локальный тестовый CA; HTTPS `/health/live` = 200, HTTP redirect = 308,
  HSTS/nosniff/DENY проверены. [Результат](tls-local.json) явно указывает
  `public_trust_checked=false`. Контейнер и временный файл CA удалены.
- [Runtime port audit](ports.json): **gate не пройден**, exit code 1.
  Neo4j-прокси проекта публикуют 17474/17687 на loopback; сторонние `graph_rag_*`
  публикуют 5432, 6333/6334, 7474/7687 на IPv4/IPv6 wildcard. Проверка Windows
  listeners подтверждает эти порты; host Ollama 11434 слушает 127.0.0.1.
  Исходный compose.yaml публикует только Caddy, но работающие overrides нарушают gate.
  Существующие контейнеры и firewall не изменялись.

## Приёмка

- [x] Локальный TLS profile и CORS allowlist реализованы и проверены.
- [x] Неверный Origin/CSRF блокируется; внутренний URL не запрашивается адаптерами.
- [x] Ротация/login fixation, logout, disable и общие rate limits проверены.
- [x] Отозванная сессия не читает SSE/evidence; открытый stream прекращается до
  следующего data event.
- [x] Аудит реальных port bindings выполнен, блокеры записаны.
- [ ] На целевом host доступны только Caddy 80/443: устранить найденные публикации,
  перепроверить Docker, нативные listeners, firewall/NAT и scan с внешнего узла.
- [ ] Реальный домен с публично доверенным TLS и HTTPS smoke двух пользователей,
  revoke/CSRF/rate limits/SSE/evidence на внешнем адресе.

Порядок устранения блокеров и команды повторной проверки приведены в
[DEPLOYMENT](../../DEPLOYMENT.md#периметр-auth-002-и-внешний-tls-gate).
Прохождение AUTH-002 не заменяет последующие TEST-001/REL-001 gates.

Проверенные первичные источники:
[Caddy TLS](https://caddyserver.com/docs/caddyfile/directives/tls),
[Caddy global options](https://caddyserver.com/docs/caddyfile/options),
[Starlette CORS](https://www.starlette.io/middleware/#corsmiddleware).
Поведение проверялось на установленном Caddy и закреплённой версии Starlette.
