# APP-AIR-001 — инкремент Airflow

Опоры: [ARCHITECTURE](../ARCHITECTURE.md), [DATA_MODEL](../DATA_MODEL.md), ADR-002/015, INT-KG и I-CORPUS. DAG вызывает переиспользуемые source adapters, ingestion, extraction/indexing и существующие outbox/ACK в офлайн-контуре. Первая волна работает через внедряемые порты на fixtures. Расписание/Compose, реальные подключения, урегулирование квот и публикация на готовом корпусе относятся к I-AIR.

Вход — interval с UTC bounds, разрешённые EPO/OpenAlex scope/config и последнее durable состояние. Discovery выдаёт страницу source IDs/revisions и позицию страницы или watermark. Нормализация/ingestion использует source/external ID/content hash. Неизменные ревизии не требуют повторной проекции. Идемпотентная заявка сохраняет revision и отправляет отдельные задания KG и vector. Завершение страницы/интервала и переключение поколения разрешены только после QA и обоих подтверждений для изменённых ревизий. При частичном сбое повтор восстанавливается по durable checkpoint/outbox; предыдущая опубликованная версия остаётся читаемой.

Настройки подключений получаются через механизм секретов/Connections Airflow либо текущие защищённые env adapters. Payload логов и XCom ограничен stage, статусом, счётчиками и неприватными идентификаторами. Произвольные источники/URL и пользовательские данные не входят в DAG inputs. Пределы на интервалы, страницы, запросы и retries задаются конфигурацией. Повтор использует тот же стабильный набор IDs и revision keys.

| ID | Given → When → Then | Проверка |
| --- | --- | --- |
| AIR-1 | EPO/OpenAlex fixtures дают новые, повторные и изменённые документы → bounded discovery/ingestion → обработаны только новые/изменённые ревизии, пустая страница завершает цикл | Fixture source и реестр вызовов |
| AIR-2 | Изменённая ревизия → ingestion/chunks/extraction → прежними портами ставятся обе проекции с pinned revision/provenance | Test doubles projectors и фикстуры ingestion |
| AIR-3 | Векторный или KG ACK отсутствует → DAG повторяет нужную работу → publish/checkpoint наступает после обоих ACK/QA и повтор интервала идемпотентен | Failure injection и replay |
| AIR-4 | Неразрешённый source, невалидный документ, квота или сбой зависимости → safe failure, bounded retry, checkpoint не обгоняет данные → секреты и raw payload не публикуются | Negative fixture/log/canary |
| AIR-5 | Запущен DAG на разрешённом замороженном снимке → инкремент виден в обоих online indexes после publish → прежняя версия читается в случае partial projection | Live I-AIR после I-CORPUS, без полного backfill |

Файлы первой волны — `airflow/` (DAG и bridge), fixtures и targeted tests. Общий `compose.yaml`, online worker и публикацию поколения в рабочей инфраструктуре соединяет оркестратор на I-AIR. Откат останавливает расписание; durable outbox и текущее поколение доступны для возобновления.
