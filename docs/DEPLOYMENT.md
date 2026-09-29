# Развёртывание

Первый профиль — Docker Compose на одном ПК (Ryzen 7 8845HS, 32 ГБ RAM). Отдельные контейнеры: `caddy`, `api`, `worker`, `postgres`, `redis`, `neo4j`, `qdrant`, `inference`. `web` собирается Vite и раздаётся Caddy как статика. Caddy выбран за простую конфигурацию HTTPS; для LAN без доверенного домена использовать HTTP только в доверенной сети или локальный сертификат, не обходить предупреждения браузера. Внешний доступ включать лишь после настройки домена, публично доверенного TLS, auth и rate limits.

| Сервис | Порт внутри Compose | Публикация | Начальный memory limit / reservation |
|---|---:|---|---:|
| caddy | 80/443 | 80/443; dev LAN только нужный порт | 256 / 64 MiB |
| api | 8000 | нет | 1.5 GiB / 512 MiB |
| worker | внутренний | нет | 1.5 GiB / 512 MiB |
| postgres | 5432 | нет | 2 GiB / 512 MiB |
| redis | 6379 | нет | 512 / 128 MiB; maxmemory 256 MiB |
| neo4j | 7687/7474 | нет | 4 GiB / 2 GiB; heap 1 GiB, page cache 1 GiB |
| qdrant | 6333 | нет | 3 GiB / 1 GiB |
| inference | provider-specific | нет | 12 GiB / 6 GiB, один concurrent generation |

Сумма limits ~25 ГБ, оставляет память ОС/Docker. Значения — стартовые гипотезы: после benchmark на реальной модели проверить RSS, swap, холодный запуск, одновременный ingestion/search и пиковый индекс. CPU inference может быть медленным; не обещать latency до замеров. У inference volume с весами вне Git. Базы имеют отдельные volumes и health checks. Запуск `docker compose --profile cpu up -d`; сервисы должны восстанавливаться после restart. Для разработки разрешён ручной доступ к БД лишь через `docker compose exec`, без публичного port mapping.

Конфиг: `.env.example` без значений секретов, реальные `.env` игнорируются Git; EPO client credentials, DB passwords, session keys, provider endpoints — через env/secrets. Миграции БД идут отдельной командой перед api/worker. Backup: PostgreSQL dump + Neo4j/Qdrant snapshots или переиндексация из сохранённых нормализованных ревизий; регулярная проба восстановления обязательна перед release. Redis в backup не нужен.

Вынос GPU: заменить `INFERENCE_BASE_URL` и профиль Compose, оставить `InferenceProvider` и контракты неизменными. Связь к удалённому inference — приватная сеть/TLS и auth; API не принимает произвольный inference URL от клиента. Ingestion worker и API можно позже разнести без разделения кода или введения Kafka/Kubernetes.

Проверки M1: `docker compose config`, health баз и bootstrap api/worker, отсутствие опубликованных портов Postgres/Redis/Neo4j/Qdrant/inference. До LLM-002 inference запускается опциональным profile: отсутствие весов не ломает bootstrap health. До DB-001 миграционный entrypoint — stub; DB-001 проверяет schema upgrade, DB-002 — реальный queue heartbeat. Полный CPU profile с весами получает собственный gate LLM-002. Минимальные health/redaction не откладываются до OBS-001.

До AUTH-001 Caddy слушает только loopback; после auth/isolation gate допускается доверенный LAN. Перед внешним demo: TLS, login, CSRF/CORS, rate limits и восстановление backup. Один worker обслуживает analysis и ingestion очереди; отдельный общий semaphore ограничивает **все** генеративные роли (planner, extractor, analyst), а embedding/rerank имеют собственные RAM/batch лимиты. Ingestion не запускает вторую тяжёлую генерацию в обход очереди. Budget 6k input не гарантирует размещение двух моделей; загрузку/выгрузку и RSS измерить в LLM-002.

## Compose bootstrap (INFRA-001)

Скопируйте `.env.example` в `.env`. Оставленные пустыми пароли используют известные dev-only значения: сервисы не публикуют свои порты, а Caddy привязан к loopback. Перед сохранением реальных данных замените все три пароля на длинные URL-safe случайные значения. Не задавайте `CADDY_BIND_ADDRESS=0.0.0.0` до AUTH-001 и security gate.

- Проверка конфигурации: `docker compose config`.
- Bootstrap с веб-прокси: `docker compose --profile dev up --build -d`. Открыть `http://127.0.0.1:8080`; единственная опубликованная служба — Caddy. PostgreSQL, Redis, Neo4j и Qdrant доступны только в закрытой backend-сети.
- Остановить контейнеры без удаления данных: `docker compose down`.
- Профиль `prod` использует Caddy с TLS и loopback-публикацией на `8081/8443` по умолчанию. `PUBLIC_DOMAIN` надо настроить отдельно; доступ извне и смена bind address остаются закрыты до auth/security gate.
- Ollama включается отдельно: `docker compose --profile cpu up -d inference`. Профиль не загружает модели; веса хранятся в отдельном Docker volume вне Git. CPU smoke и выбор модели относятся к LLM-002.

`migrate` — отдельный одноразовый контейнер-зависимость перед API/worker. До DB-001 он только сообщает, что схема ещё не определена. API container healthcheck проверяет liveness; `/health/ready` остаётся 503 до появления реальных schema/queue readiness gates в DB-001/DB-002. Worker healthcheck подтверждает только жизнь bootstrap процесса, а не наличие durable queue.

Начальные образы закреплены тегами в `compose.yaml` и `docker/Dockerfile.*`; обновлять их следует отдельным review с повторной проверкой поддержки, лицензий и конфигурации. Docker Desktop memory allocation должен быть достаточен для суммарных лимитов сервисов; inference с лимитом 12 GiB по умолчанию не запускается.
