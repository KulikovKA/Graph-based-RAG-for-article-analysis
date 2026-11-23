# Запуск Airflow и MLflow

MAIN владеет Compose-проектом `article-tracking`. Он имеет собственные сеть, две базы PostgreSQL и тома. У существующего приложения и у RESEARCH нет зависимости от их запуска. Изменения в продуктовой базе и индексах не требуются. Профили можно поднимать по очереди. Клиент использует стандартную библиотеку Python 3.11.

## Развёртывание на локальном компьютере

Заполните блок переменных из конца `.env.example` в отдельном `.env.tracking`, исключённом из Git. Для каждой переменной с паролем и для ключа webserver сгенерируйте отдельное значение. Для Fernet подойдёт `base64.urlsafe_b64encode(secrets.token_bytes(32)).decode()`. Пароли ролей в URI должны быть URL-safe. Смена пароля bootstrap существующей БД требует согласованной смены в PostgreSQL. Контейнер приложения работает с отдельной ролью runtime. Оба UI доступны доверенным пользователям этого компьютера. Прокси для внешнего доступа в этой конфигурации отсутствует.

```powershell
$stack = @('--env-file','.env.tracking','-f','compose.tracking.yaml')
docker compose @stack --profile airflow --profile observability config --quiet
docker compose @stack --profile observability up -d --build
docker compose @stack --profile airflow up -d --build
docker compose @stack --profile airflow --profile observability ps -a
docker compose @stack exec airflow-scheduler airflow dags list-import-errors
docker compose @stack exec airflow-scheduler airflow dags list
```

Airflow UI доступен по http://127.0.0.1:8085 с учётной записью из `.env.tracking`. При первом создании `public_corpus_increment` приостановлен. Включение, trigger и backfill в процедуру проверки не входят. Для уже зарегистрированного DAG проверьте `is_paused`. Если он включён, зафиксируйте состояние и выполните `docker compose @stack exec airflow-scheduler airflow dags pause public_corpus_increment`. Остановка расписания не отменяет уже исполняющуюся задачу.

MLflow UI и REST используют http://127.0.0.1:5000. В сети Compose URI равен `http://mlflow:5000`. Служба mlflow-init идемпотентно создаёт прикладные experiments, служебный Default MLflow сохраняется. Ключи источников данных, API и prompts не нужны. Режим доверенного однопользовательского хоста не даёт изоляции разных пользователей одной машины.

## Подключение клиента и повторная отправка

Установите только клиент из `src/project_tracking` или добавьте каталог MAIN/src в PYTHONPATH. Используйте отдельный постоянный файл SQLite на локальном диске для каждого владельца событий. Все процессы, которые пишут один внешний ID, должны разделять одну очередь. На двух независимых машинах одновременные search/create могут создать дубликаты. Пример настройки для исследовательского процесса в PowerShell:

```powershell
$env:MLFLOW_TRACKING_URI = 'http://127.0.0.1:5000'
$env:TRACKING_ENABLED = 'true'
$env:TRACKING_ALLOW_CREATE = 'false'
$env:TRACKING_OUTBOX = Join-Path $env:LOCALAPPDATA 'graph-rag-tracking/research.sqlite3'
python -m project_tracking.client replay
```

Вызов `record(experiment, external_id, params, metrics, tags, status, parent_run_id)` возвращает delivered, queued, disabled либо error. Используйте уникальный внешний ID из оркестратора, один на логический run. Приватный ввод и внешние файлы в API отсутствуют. Валидатор проверяет схему и форму идентификаторов. Берите идентификаторы моделей и конфигурации из контролируемого manifest. Содержимое строки с формально допустимыми символами само по себе не подтверждает её безопасность.

При недоступном сервере клиент пишет предупреждение и сохраняет валидированное событие перед HTTP. После восстановления выполните replay для очереди соответствующего клиента. Для DAG это `docker compose @stack exec airflow-scheduler python -m project_tracking.client replay`. Статус error требует проверки доступности файла очереди и корректности payload. Артефакт tracking-event.json создаётся из разрешённых полей того же события. [Схема v1](specs/tracking-schema.md)

## Резервная копия и откат

Перед обновлением приостановите отправителей, scheduler и webserver. Остановите mlflow, оставив базы работающими. Сохраните отдельно pg_dump обеих баз и pg_dumpall --roles-only для каждого экземпляра, тома artifacts, outbox и logs, исходные версии образов, код и секреты в защищённом хранилище. Для восстановления используйте отдельный Compose-проект, сохранённые роли/секреты и совместимые образы, восстановите dump и соответствующие тома, проверьте чтение JSON предыдущего run и состояние paused перед подключением клиентов. Копия хранится до защиты проекта, удаление согласует владелец. При откате остановите профили через stop, сохраните тома и поставьте предыдущую проверенную версию кода. Полное восстановление из копии проверяется в G-TEST отдельно от рестарта.

В Airflow 2.11 колонка Next Run на главной странице показывает logical_date, соответствующую началу окна. Сравнивайте её с next_dagrun_create_after в metadata DB. Чтобы сопоставить run в data_expansion с Airflow, найдите в параметре run_id SHA-256 от UTF-8 строки Airflow run_id. Исходный пользовательский ID ручного запуска в tracking не отправляется.

## Проверка 24 ноября 2026 года

На Windows с Docker Desktop запускались только службы проекта article-tracking. База исходного кода MAIN — b338dff. Образы содержали Airflow 2.11.0, MLflow 3.10.0 и PostgreSQL 17.11. Команды из каталога MAIN:

```powershell
.\.venv\Scripts\python -m pytest tests/unit/test_airflow_increment.py tests/unit/test_airflow_sources.py tests/unit/test_airflow_timetable.py tests/unit/test_tracking_client.py tests/unit/test_tracking_schema.py tests/unit/test_ingestion_normalization.py -ra
.\.venv\Scripts\ruff check airflow src/app/domain/external_ids.py src/app/services/ingestion.py src/project_tracking tests/unit/test_airflow_increment.py tests/unit/test_airflow_timetable.py tests/unit/test_tracking_client.py tests/unit/test_tracking_schema.py
.\.venv\Scripts\mypy src/project_tracking src/app/services/ingestion.py
Get-Content -Raw -Encoding utf8 tests/unit/test_airflow_timetable.py | docker exec -i -e PYTHONPATH=/opt/airflow/dags:/opt/project/src article-tracking-airflow-scheduler-1 python -
docker exec article-tracking-airflow-db-1 psql -U airflow -d airflow -Atc "select dag_id,is_paused,next_dagrun,next_dagrun_data_interval_start,next_dagrun_data_interval_end,next_dagrun_create_after from dag"
docker exec article-tracking-airflow-db-1 psql -U airflow -d airflow -Atc "select (select count(*) from dag_run),(select count(*) from import_error)"
```

| Проверка | Статус | Наблюдение |
|---|---|---|
| Компоненты MAIN | PASS | 49 passed. Один тест timetable пропущен на Windows и отдельно выполнен в контейнере. Ruff и mypy прошли. Повтор страниц, partial failure и оба ACK проверены на подставных портах. |
| AIR-6, реальный scheduler и UI | PASS | В базе paused=true, 0 runs и 0 import errors. Для logical_date 23 ноября 00:00 UTC разрешённый момент 24 ноября 00:00 UTC. В Chromium с зоной America/Los_Angeles после входа UI показал MSK (+03:00), в меню Local отображался PST. |
| EVAL-1 | PASS | Через один REST URI созданы три experiments. Записаны params, metrics, tags и JSON синтетического Judge. После остановки сервера, рестарта mlflow-db и запуска сервера прочитан тот же run 23f94bfcb884446fa5813bb19c10dabb с теми же значениями и содержимым artifact. SHA-256 канонизированного JSON b17184db4f18c91d0dff3849587bb03a52356312f6540d275f7daa32476cd0a8. |
| EVAL-2/EVAL-5, транспорт | PASS | При недоступном endpoint событие попало в SQLite. После replay на живой сервер дочерний run 944974d5f70d409f8fdab114f717b83f перешёл из FAILED в FINISHED, сохранив ID и связь с родителем. Проверены отклонение неизвестных полей и безопасный XCom на fixtures. |
| I-AIR | BLOCKED | Рабочие окна источников и атомарный publish/checkpoint после QA и двух ACK ожидают I-CORPUS. Запуск DAG и unpause в проверку не входили. |
| I-OBS, I-RES, G-TEST | NOT RUN полностью | Онлайн-телеметрия всех продуктовых компонентов, полная исследовательская оценка, восстановление из отдельной резервной копии и выпускная регрессия имеют самостоятельные критерии. |
