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
| inference | provider-specific | нет | 16 GiB / 8 GiB для отдельного контейнерного профиля; один concurrent generation |

Сумма limits контейнерного профиля ~29 ГБ; лимиты не равны фактическому расходу памяти. Для проверенного host Ollama профиль `cpu` не запускается: проектные контейнеры занимали около 1.7 ГБ, а модели измерялись как процессы Windows. CPU inference может быть медленным; см. фактические значения ниже. У контейнерного inference volume с весами вне Git. Базы имеют отдельные volumes и health checks. Для разработки разрешён ручной доступ к БД лишь через `docker compose exec`, без публичного port mapping.

Конфиг: `.env.example` без значений секретов, реальные `.env` игнорируются Git; EPO client credentials, DB passwords, session keys, provider endpoints — через env/secrets. Миграции БД идут отдельной командой перед api/worker. Backup: PostgreSQL dump + Neo4j/Qdrant snapshots или переиндексация из сохранённых нормализованных ревизий; регулярная проба восстановления обязательна перед release. Redis в backup не нужен.

Вынос GPU: заменить `INFERENCE_BASE_URL` и профиль Compose, оставить `InferenceProvider` и контракты неизменными. Связь к удалённому inference — приватная сеть/TLS и auth; API не принимает произвольный inference URL от клиента. Ingestion worker и API можно позже разнести без разделения кода или введения Kafka/Kubernetes.

Проверки M1: `docker compose config`, health баз и bootstrap api/worker, отсутствие опубликованных портов Postgres/Redis/Neo4j/Qdrant/inference. До LLM-002 inference запускается опциональным profile: отсутствие весов не ломает bootstrap health. DB-001 применяет Alembic schema upgrade; DB-002 добавляет транзакционные репозитории и реальный queue heartbeat. Полный CPU profile с весами получает собственный gate LLM-002. Минимальные health/redaction не откладываются до OBS-001.

До AUTH-001 Caddy слушает только loopback; после auth/isolation gate допускается доверенный LAN. Перед внешним demo: TLS, login, CSRF/CORS, rate limits и восстановление backup. Один worker обслуживает analysis и ingestion очереди; отдельный общий semaphore ограничивает **все** генеративные роли (planner, extractor, analyst), а embedding/rerank имеют собственные RAM/batch лимиты. Ingestion не запускает вторую тяжёлую генерацию в обход очереди. Budget 6k input не гарантирует размещение двух моделей; загрузку/выгрузку и RSS измерить в LLM-002.

## CPU baseline LLM-002 на локальном Ollama

Проверенный путь на Windows использует уже установленный Ollama 0.34.4 на host. Контейнеры приложения получают фиксированный `INFERENCE_BASE_URL=http://host.docker.internal:11434`; доступ из Compose API-контейнера к `/api/version` проверен (HTTP 200). Ollama не публикуется через Caddy. Отдельный `inference` profile с собственным volume не содержит скачанных пользователем весов и **не является проверенным runtime** этих измерений. Его лимит 16 GiB основан на наблюдаемом RSS 14.17 ГБ плюс запас; перед выбором этого пути требуется отдельный запуск с закреплёнными весами и достаточной памятью Docker Desktop. На текущем Docker Desktop доступно 15.28 GiB, поэтому этот профиль с Analyst не проверялся.

Версии, digest, quantization, размер, license и SHA файлов reranker записаны в [model inventory](model_inventory.json). Короткий воспроизводимый gate запускается `python scripts/benchmark_inference.py <phase>`; результаты Gemma и ограничения приведены в [отчёте LLM-002](validation/LLM-002/README.md), прежние замеры `gpt-oss:20b` — в [историческом отчёте](validation/LLM-002/measurements_gpt-oss_20b.json). Перед benchmark reranker надо один раз скачать официальный `Qwen/Qwen3-Reranker-0.6B` по revision из inventory через `huggingface_hub.snapshot_download`; далее скрипт использует `local_files_only=True` и offline flags. Веса и HF/Ollama cache находятся вне Git. Ollama-модели сверяются по digest до измерений.

| Роль | Cold / warm latency | Пик RSS | Наблюдение |
|---|---:|---:|---|
| Embedding, 3 текста | 3.70 / 1.99 с | 1.30 ГБ Ollama tree | API вернул 1024 dimensions, batch и повтор стабильны |
| Reranker, 3 passages | 9.82 / 1.29 с | 1.78 ГБ child process | RU query ранжирует EN technical passage первым |
| Planner | 10.49 / 2.50 с | 5.39 ГБ Ollama tree | русский запрос, structured JSON валиден; обрезанный JSON отклонён и одна repair-попытка успешна |
| Analyst | 46.25 / 26.22 с | 14.18 ГБ Ollama tree | AnalysisV1 с точной цитатой и offsets, final без raw reasoning; TTFT 23.70 / 0.45 с |

Для Analyst host used достиг 30.64 ГБ в первом прогоне; в повторном прогоне с проверкой цитаты peak составил 28.31 ГБ, а суммарный peak проектных Compose-контейнеров — 2.04 ГБ. Pagefile used в первом прогоне вырос примерно с 3.47 до 4.70 ГБ, в повторном оставался около 4.65 ГБ; Windows API здесь не дал счётчиков page-in/page-out. Это реальный риск latency/памяти на 32 ГБ, а не обещание безопасной одновременной загрузки. Planner→Analyst→Planner дал примерно 9.76→23.16→9.89 с с одним загруженным генеративным model ID на каждом шаге. Отмена тёплого Analyst вернула `InferenceCancelled` за 2.54 с, `/api/ps` подтвердил выгрузку, слот остался доступен. `reasoning_tokens` и duration остаются `null`: Ollama не отдаёт их как отдельные надёжные метрики. Model TTFT отличается от времени готового проверенного результата; последний появится в JOB-002/OBS-001. Один ранний Analyst вызов дал невалидный JSON и был отклонён; повтор с `temperature=0` дал валидный AnalysisV1. Это подтверждает необходимость одного repair и fallback, а не гарантию каждого draft.

Предпочтительный `sentence-transformers CrossEncoder` в локальной связке 5.3.0/Transformers 5.1.0 создал отсутствующий в checkpoint `score.weight` и не обработал batch без padding token. Этот путь не используется для relevance. Baseline reranker — [официальная схема Qwen](https://huggingface.co/Qwen/Qwen3-Reranker-0.6B) с causal-LM yes/no logits через Transformers, в отдельном CPU-процессе с принудительной остановкой при cancel/timeout. Offline startup и ранжирование проверены на закреплённом snapshot. Mini retrieval на EVAL-000: 8 synthetic documents, 9 непустых cases, MRR 1.0; Recall@10/20 = 1.0 тривиален при восьми документах. Для RU case 008 reranker сохранил релевантный источник на первом месте и поменял порядок двух менее релевантных кандидатов. Это smoke, а не сравнительная оценка качества моделей.

## CPU lifecycle по ADR-011

Фактические IDs, quantization и digests Planner/Analyst закреплены в model inventory. Прежний container limit 12 GiB меньше измеренного RSS Analyst; увеличенный лимит 16 GiB остаётся непроверенным для отдельного Docker runtime. При OOM или активном свопе workload gate требует повторного измерения и настройки. MoE active parameters не равны объёму всех весов в памяти.

Один worker и общий semaphore удерживаются на время generation и остановки backend request. Lifecycle: загрузить Planner → получить/проверить JSON, при необходимости repair → выгрузить Planner → retrieval/embedding/rerank → загрузить Analyst → structured analysis/единственный repair → выгрузить Analyst → deterministic validation/render/commit. Между двумя Analyst calls того же bounded repair допускается оставить модель загруженной. Ingestion/extractor подчиняется тому же semaphore; release lease или HTTP disconnect не доказывает остановку вычисления. После cancel/timeout подтверждать остановку либо блокировать новые генерации до recovery; нельзя запускать вторую модель поверх зависшей первой.

Для Ollama deployment-кандидат: `OLLAMA_MAX_LOADED_MODELS=1`, `OLLAMA_NUM_PARALLEL=1`; `keep_alive=0` при завершении роли/переключении. Это adapter/deployment policy, не поля domain/API. Документация описывает лимит одновременно загруженных моделей и выгрузку через keep_alive; соответствие pinned image проверяется в LLM-002. Если embedding/rerank используют тот же runtime, они тоже участвуют в загрузке/вытеснении. Источник: [Ollama FAQ](https://docs.ollama.com/faq), проверено 2026-09-29.

Benchmark отдельно измеряет cold start, warm same-model call, Planner→Analyst и Analyst→Planner switch, load/unload time, process RSS и peak container/host RAM, swap, model TTFT и время до validated result. Нужен реальный полный workload с базами, а не только CLI одной модели. Warm keep-alive после run — только ограниченная настройка по результатам gate; одновременно держать обе генеративные модели не требуется. Веса и raw provider dumps в Git не входят. Совместимость thinking + structured output проверяется для конкретной пары runtime/model: [thinking](https://docs.ollama.com/capabilities/thinking), [structured outputs](https://docs.ollama.com/capabilities/structured-outputs). Это источники для adapter tests, не обещание возможностей установленного образа.

SSE использует существующий Caddy/API. API-001 проверяет flush и отсутствие buffering на реальном proxy, heartbeat и reconnect при долгом inference; write timeout/backpressure ограничены, disconnect клиента не удерживает worker. Публикация уже committed ответа не держит generation semaphore. Никаких WebSocket/Kafka или новых сервисов.

## Compose bootstrap (INFRA-001)

Скопируйте `.env.example` в `.env`. Оставленные пустыми пароли используют известные dev-only значения: сервисы не публикуют свои порты, а Caddy привязан к loopback. Перед сохранением реальных данных замените все три пароля на длинные URL-safe случайные значения. Не задавайте `CADDY_BIND_ADDRESS=0.0.0.0` до AUTH-001 и security gate.

- Проверка конфигурации: `docker compose config`.
- Bootstrap с веб-прокси: `docker compose --profile dev up --build -d`. Открыть `http://127.0.0.1:8080`; единственная опубликованная служба — Caddy. PostgreSQL, Redis, Neo4j и Qdrant доступны только в закрытой backend-сети.
- Остановить контейнеры без удаления данных: `docker compose down`.
- Профиль `prod` использует Caddy с TLS и loopback-публикацией на `8081/8443` по умолчанию. `PUBLIC_DOMAIN` надо настроить отдельно; доступ извне и смена bind address остаются закрыты до auth/security gate.
- Ollama включается отдельно: `docker compose --profile cpu up -d inference`. Профиль не загружает модели; веса хранятся в отдельном Docker volume вне Git. CPU smoke и выбор модели относятся к LLM-002.

`migrate` — отдельный одноразовый контейнер-зависимость перед API/worker и запускает `alembic upgrade head`. Интеграционный round-trip тест запускается отдельно: `docker compose --profile tools run --build --rm db-test`; он создаёт временную PostgreSQL-схему, проверяет миграцию и constraints, затем удаляет только эту схему. API container healthcheck проверяет liveness; `/health/ready` остаётся 503 до появления реальных schema/queue readiness gates в DB-002. Worker healthcheck подтверждает только жизнь bootstrap процесса, а не наличие durable queue.

Начальные образы закреплены тегами в `compose.yaml` и `docker/Dockerfile.*`; обновлять их следует отдельным review с повторной проверкой поддержки, лицензий и конфигурации. Docker Desktop memory allocation должен быть достаточен для суммарных лимитов сервисов; отдельный inference profile по умолчанию не запускается.
