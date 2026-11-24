# Локальное администрирование MAIN

Конфигурация относится к `MAIN-INFRA-003` и использует проекты `article-analysis` и `article-tracking`, их существующие сети и тома. Прокси не меняют конфигурацию и тома баз. Запускать из MAIN после подготовки `.env` и защищённого `.env.secrets` по `docs/TRACKING.md`. Оба файла обязательны. Значения из `.env.secrets` имеют приоритет над `.env`; скрипт отклоняет наличие в окружении процесса любой переменной интерполяции Compose и переменных `COMPOSE_FILE`, `COMPOSE_PROJECT_NAME`, `COMPOSE_PROFILES`, `COMPOSE_ENV_FILES`, `COMPOSE_DISABLE_ENV_FILE`. Удалите конфликтующие переменные из процесса, а не печатайте их значения.

```powershell
.\scripts\start-local-infra.ps1
```

Скрипт сначала проверяет конфигурацию, затем запускает базы, выделенные прокси и Redis Insight без сборки образов и пересоздания существующих контейнеров. До этого он проверяет наличие контейнеров tracking и успешное завершение airflow-db-provision, airflow-init и mlflow-db-provision. Далее он запускает только существующие контейнеры баз tracking и UI через docker start, без повторного bootstrap или пересоздания зависимостей. Если контейнеры отсутствуют или первоначальная инициализация не подтверждена, запуск останавливается; первичный bootstrap выполняется отдельно по docs/TRACKING.md. Заранее должны быть доступны образы tracking; для новых прокси и Redis Insight Docker может скачать образы. Скрипт не запускает worker, модели или scheduler. Уже работающий scheduler он не останавливает: отдельно убедитесь, что DAG приостановлен. Настройка Airflow оставляет новые DAG приостановленными; существующий статус не изменяется. `--no-recreate` также означает, что изменения env не применятся к уже работающим контейнерам автоматически. Не используйте одновременно старый `compose.local.yaml`, публикующий те же порты баз.

| Сервис | Windows | Назначение и учётные данные |
| --- | --- | --- |
| Qdrant | http://127.0.0.1:6333/dashboard | Индекс приложения; доступ без дополнительной аутентификации, только доверенный локальный пользователь |
| PostgreSQL | `127.0.0.1:5432` | БД `POSTGRES_DB` (по умолчанию `article_analysis`), роль `POSTGRES_USER` (по умолчанию `article_app`), пароль `POSTGRES_PASSWORD` |
| Redis | `127.0.0.1:6379` | Кэш, пароль `REDIS_PASSWORD` |
| Redis Insight | http://127.0.0.1:5540 | Добавьте соединение вручную: host `redis`, порт `6379`, пароль `REDIS_PASSWORD`. Пароль не передаётся в настройки контейнера; данные Insight находятся в tmpfs и теряются при остановке контейнера; вводите пароль заново |
| Neo4j Browser | http://127.0.0.1:17474 | Имя `neo4j`, пароль `NEO4J_PASSWORD`, URI подключения `bolt://127.0.0.1:17687`; используются существующие прокси `compose.neo4j-browser.yaml` |
| Airflow | http://127.0.0.1:8085 | UI: `AIRFLOW_ADMIN_USERNAME`, `AIRFLOW_ADMIN_PASSWORD`. Metadata: БД `airflow`, роли `airflow` и `airflow_runtime`, пароли `AIRFLOW_DB_PASSWORD` и `AIRFLOW_DB_RUNTIME_PASSWORD` |
| MLflow | http://127.0.0.1:5000 | UI без аутентификации; metadata: БД `mlflow`, роли `mlflow` и `mlflow_runtime`, пароли `MLFLOW_DB_PASSWORD` и `MLFLOW_DB_RUNTIME_PASSWORD` |

Все адреса опубликованы только на `127.0.0.1`. Это административные интерфейсы, а не внешний периметр безопасности. MLflow и Qdrant доступны другим локальным пользователям компьютера. Не пересылайте пароли в командной строке или журналы. Фактический пароль существующей БД может отличаться от переменной файла: подтверждайте его аутентификацией, не меняя автоматически.

Безопасные проверки из Windows не раскрывают содержимое баз и секреты:

```powershell
Test-NetConnection 127.0.0.1 -Port 5432 -InformationLevel Quiet
Test-NetConnection 127.0.0.1 -Port 6379 -InformationLevel Quiet
Test-NetConnection 127.0.0.1 -Port 17687 -InformationLevel Quiet
Invoke-WebRequest http://127.0.0.1:6333/healthz -UseBasicParsing
Invoke-WebRequest http://127.0.0.1:17474 -UseBasicParsing
Invoke-WebRequest http://127.0.0.1:5540 -UseBasicParsing
Invoke-WebRequest http://127.0.0.1:8085/health -UseBasicParsing
Invoke-WebRequest http://127.0.0.1:5000/health -UseBasicParsing
```

Проверка портов и health не подтверждает авторизацию. Состояние DAG и число запусков проверьте в Airflow UI до и после запуска; не включайте расписание при этой проверке. Отказ привязки порта разрешайте после выяснения владельца, не останавливая чужие контейнеры автоматически.

Для отката остановите и удалите только ненужные контейнеры прокси и Redis Insight через Docker Desktop; существующие Neo4j-прокси могут использоваться другими процессами. Не удаляйте volumes и не выполняйте `docker compose down -v`. Данные баз остаются в прежних томах; восстановите прежний способ доступа отдельно.
