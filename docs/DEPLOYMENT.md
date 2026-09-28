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

Проверки M1: `docker compose config`, health всех контейнеров, отсутствие опубликованных портов Postgres/Redis/Neo4j/Qdrant/inference. Перед внешним demo: TLS, login, CSRF/CORS, rate limits и восстановление backup.
