# APP-EXPORT-001 — экспорт исследования

Опоры: [API_CONTRACTS](../API_CONTRACTS.md), [DATA_MODEL](../DATA_MODEL.md), ADR-006/009/011/016. Базовый переносимый формат первой волны — UTF-8 HTML attachment. Доступ по `GET /api/v1/runs/{run_id}/export` с действующей сессией. Неизвестный или чужой run — одинаковый 404. Свой незавершённый или завершившийся ошибкой run — 409 `RUN_NOT_COMPLETED`. Повреждённые сохранённые данные — безопасный 503. Ответ владельцу использует `Cache-Control: no-store` и фиксированное имя файла из UUID.

Источник истины — completed RunV1/AnswerV1, pinned idea version, сохранённые metadata/references в run snapshot и RunEvidence, проверенные по owner/run/document/revision. Документ включает итоговые выводы, сравнение признаков (feature labels из pinned idea version при наличии, иначе ID), таблицу патентов и публикаций, citations/evidence с точными quotes, идентификаторы версий, coverage и ограничения. Смещения цитаты относятся к исходному Unicode chunk и лежат внутри границ сохранённого span согласно реализации Analyst. Корректные no_evidence/clarification имеют осмысленный отчёт с пустыми фактами. Legacy completed с валидным AnswerV1 экспортируется без обязательных ADR-011 проекций. HTTPS ссылки проходят используемый allowlist, строки экранируются, активное содержимое отсутствует.

| ID | Given → When → Then | Проверка |
| --- | --- | --- |
| EXP-1 | Completed run с анализом → GET владельца → UTF-8 attachment с выводами, сравнением, таблицей, источниками, ограничениями и версиями | Contract attachment и детерминированная service fixture |
| EXP-2 | Индекс и текущая версия идеи изменились → экспорт исходного run → отчёт повторяет сохранённые source revisions, цитаты и coverage | Historical fixture и regression |
| EXP-3 | Неизвестный/чужой, незавершённый либо потерянная сессия → 404/409/401 → частный payload отсутствует | Contract ownership/status |
| EXP-4 | Поля содержат HTML, неподходящий URL или citation вне snapshot → экранирование либо безопасная обработка ошибки → в файле отсутствует активный контент | Negative rendering/evidence unit+contract |
| EXP-5 | Legacy completed или no_evidence → сохранённый результат экспортируется в допустимом виде → inference, актуальный индекс и обработка очереди не вызываются | Legacy/empty test и проверка зависимостей |

Расширение сохраняет `GET /api/v1/runs/{run_id}/export` с HTML по умолчанию и принимает `?format=html|pdf`. PDF выдаётся как `application/pdf` attachment с UUID в имени и `no-store`. Оба формата используют сохранённые источники, evidence и версионированную проекцию подграфа из того же run, с типами рёбер и ограниченным объёмом. Для исторического run без сохранённой проекции отчёт явно сообщает её отсутствие. Рендеринг выполняется локально, без внешних ресурсов и inference. PDF содержит встроенный шрифт с кириллицей и читаемые цитаты.

| ID | Given → When → Then | Проверка |
| --- | --- | --- |
| EXP-6 | Completed run с кириллицей и сохранённым подграфом → PDF/HTML экспорт → одинаковые pinned источники и визуализация; PDF читается при извлечении текста и визуальном просмотре | Сохранённый тестовый run, извлечение и рендеринг PDF |

`evidence_snapshot_json.graph_projection` использует `schema_version=1`, `run_id`, `graph_version`, `nodes`, `edges`, `truncated` и `next_cursor=null`. Проекция ограничена 30 узлами и 50 рёбрами. Capture должен происходить в том же scope поколения и той же выборки `RunEvidence`. В рёбрах `RELATED_TO`, `SIMILAR_TO`, `HAS_SHARED_CONCEPT` и синтетическом `HAS_FEATURE` evidence отсутствует. Остальные рёбра требуют сохранённых evidence IDs. `MATCHES` отображается как аналитическое сопоставление. При историческом follow-up копируется проекция с обновлением `run_id` на текущий run и сохранением версии графа, ревизий и evidence. Запись новой проекции в поисковой цепочке относится к подключению Graph-RAG.

Файлы — `src/app/api/routes/runs.py`, сервис экспорта, зависимости рендеринга и tests. Оркестратор сверяет OpenAPI после интеграции. Откат расширения сохраняет данные и исходный HTML. UI-кнопка и браузер — I-UI. PDF и визуализация подграфа входят в финальный G-TEST. Экспорт остаётся предварительным техническим исследованием.
