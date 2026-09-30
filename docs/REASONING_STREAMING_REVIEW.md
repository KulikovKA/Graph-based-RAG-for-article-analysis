# Review: reasoning Analyst и validated streaming

Дата: 2026-09-29. Scope: только planning package; решение — [ADR-011](DECISIONS.md). Production-код, migrations и benchmark не исполнялись/не менялись в рамках этого изменения. Review выполнен отдельным проходом перед редактированием контрактов; таблица фиксирует выявленные риски и принятые решения.

## Исходное состояние

Прочитаны task.md, TASKS.md, ARCHITECTURE, API_CONTRACTS, LLM_CONTRACTS, DATA_MODEL, DECISIONS, DEPLOYMENT, EVALUATION и SECURITY. Проверены domain/contracts.py/ports.py, storage/models.py/repositories.py/jobs.py, миграции 0001/0002 и существующие repository tests. Схема уже имеет immutable snapshots, terminal answer constraint, event high-water, sequence PK, terminal unique index и lease primitives. Provider — пока Protocol, RunV1 — skeleton прежней версии. Atomic result/events writer, replay и inference pipeline ещё ожидают реализации. Нельзя выдавать наличие таблиц за готовый streaming.

## Adversarial вопросы и решения

| Вопрос / атака | Решение | Будущий gate |
|---|---|---|
| 1. Progress без raw CoT? | Только фактические этапы/счётчики и elapsed. Heartbeat подтверждает соединение, не семантический прогресс | JOB-001/002, UI-001 |
| 2. Полезный streaming до validation? | Сначала pipeline progress; factual summary/answer только после проверки и общего commit. Выбран B, presentation chunks не являются provider tokens | ANALYST-001, JOB-002 |
| 3. Что durable? | Snapshot, AnswerV1/outcome, validated AnalysisV1, public summary, versioned presentation и последний progress; события до compaction | JOB-002 migration/replay |
| 4. Что authoritative? | Completed run в PostgreSQL с AnswerV1 и evidence/coverage. Остальные result DTO — согласованные immutable projections, не независимые ответы | JOB-002, API-001 |
| 5. Claim без evidence в summary? | Запрещён. Статистика и scoped gap — shell notices; factual items только из проверенных AnswerV1 claims с IDs/quotes | ANALYST-001, EVAL |
| 6. Renderer добавляет факт? | Шаблоны + relation enum + literal quotes + проверенная metadata; второй LLM pass отсутствует. Projection validator проверяет соответствие AnswerV1 | ANALYST-001 |
| 7. Cancel во время reasoning? | Отмена без fallback; fence запрещает результат и progress, late response отбрасывается. Слот занят до остановки backend, при зависании recovery | LLM-001, JOB-001/002 |
| 8. Crash после validation до доставки? | До commit retry по immutable inputs; после commit replay всех сохранённых chunks/terminal. При uncertain commit сначала read-back | JOB-002 |
| 9. Reconnecting client? | Valid cursor: seq replay/dedupe. Missing/stale после compaction: consistent RunV1/high-water reset заменяет partial view. Terminal cursor закрывает stream | API-001, UI-001 |
| 10. Timeout после thinking до final JSON? | Thinking и partial JSON отбрасываются. Safe fallback только из committed evidence в оставшемся budget; иначе failed | LLM-001, ANALYST-001 |
| 11. Как безопасен fallback? | Точные excerpts + scoped shell notices, без rejected relations; прежний validator для всех public projections. Пустой успешный поиск = no_evidence; отмена = cancelled | ANALYST-001, JOB-001 |
| 12. Новая привязка к конкретной Ollama-модели? | Options/metadata в complete_json, capabilities проверяются adapter; DTO/events не знают provider channels. Имена моделей — кандидаты gate | LLM-001/002 |

## Дополнительные найденные риски

1. **Валидная citation не доказывает relation.** Даже точная цитата может не поддерживать full match. AnalysisV1 убирает свободные rationale/summary, renderer ограничивает формулировки, но semantic faithfulness требует разметки/ручного review. Нулевой уровень смысловых ошибок нельзя обещать архитектурой. Evidence validator не ослаблен.
2. **Summary до verification противоречит требованию безопасности.** Порядок уточнён: verification started → общая проверка/commit → verification completed → summary → answer chunks. Поиск и reasoning показывают progress раньше, semantic statements не показывают.
3. **Terminal уже достигнут, а браузер ещё анимирует текст.** Cancel возвращает completed; delivery не часть job lease и не повод повторить inference. UI не удерживает terminal processing ради анимации.
4. **RAM и модельный swap могут съесть выигрыш UX.** Bootstrap 12 GiB не подтверждены для прежнего `gpt-oss:20b`; его замеры не относятся к выбранному кандидату `gemma4:26b-a4b-it-mtp-q4_K_M`. Последовательная загрузка уменьшает одновременное потребление, но добавляет latency; full-host gate обязателен. Новый кандидат ожидает загрузки и измерения.
5. **Abort HTTP не равен остановке CPU generation.** После lease expiry/worker crash recovery не начинает новую генерацию, пока backend state неизвестен; adapter/deployment gate проверяет фактическое освобождение слота.
6. **Утечка через диагностику.** Раздельные channels недостаточны при body logging/tracing. Metadata allowlist и synthetic sentinel tests распространяются на error/repair/timeout/cancel и eval artifacts.
7. **Replay может зависеть от нового renderer.** Persisted full presentation и public summary устраняют необходимость рендерить старый результат заново. Legacy runs явно сохраняют прежнюю схему без выдуманного AnalysisV1.
8. **Большой terminal batch / slow reader.** Bounded text/chunks проверяются до транзакции; backpressure ограничен на клиент, reconnect читает durable events. Нет удержания inference semaphore до SSE delivery.

## Границы изменения и проверка плана

Новых задач не требуется. LLM-001/002 закрывают provider и host gate; ANALYST-001 — DTO/validator/renderer; JOB-001 — orchestration/progress callbacks; JOB-002 — новая миграция, publication и replay; API/UI — wire contract и desktop/mobile; OBS/TEST/EVAL — метрики и проверки. JOB-002 уже транзитивно зависит от DB-002 и Analyst; API зависит от JOB-002; UI зависит от API. OBS не становится P0 prerequisite: ранние timings/redaction hooks принадлежат P0 tasks, OBS их агрегирует. Новых рёбер/циклов нет.

Прежние оценки времени карточек — исходные ориентиры, а не новые обязательства: ANALYST-001 и JOB-002 выросли за счёт projections/migration, UI-001 за счёт replay/stream UX. Перед реализацией уточнить оценку по этим acceptance criteria; не закрывать card частичной реализацией. Завершённые DB/ARCH задачи не переоткрываются и не маскируют новый scope.

Проверки этого изменения: существующий `docs/validation/ARCH-002/check_plan.py` сверяет cards/table/Mermaid, DAG/P0 и локальные ссылки; отдельная сверка diff подтверждает неизменность старых ADR и production-файлов. Результат проверки плана сохраняется в [validation/ADR-011/plan-check.json](validation/ADR-011/plan-check.json). Runtime/CPU/EVAL gates этим отчётом не объявляются пройденными.
