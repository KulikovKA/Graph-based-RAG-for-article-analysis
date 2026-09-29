# ARCH-002 — adversarial review planning package

Дата: 2026-09-29. Исходный baseline: `a9179f69d7268d0c8d133e1f51ad36afc6ec32b0` (ARCH-001, локальный и удалённый HEAD совпали). Review проводится отдельным проходом после ARCH-001: сначала регистрация дефектов без правок контрактов, затем исправления и повторная проверка. Это review документов тем же агентом в новом задании, не внешняя независимая экспертиза и не проверка работающего приложения.

## Замечания первого прохода

| ID | Приоритет | Дефект baseline и контрпример | Исправление / проверяемое следствие |
|---|---|---|---|
| R01 | P0 | ARCHITECTURE: Smart LLM error → failed; LLM/ANALYST: safe fallback. Один timeout даёт два разных terminal outcome | Единая state machine и типизированный outcome; failed только при невозможности сохранить/проверить безопасный результат |
| R02 | P0 | API допускает answer_delta до completed, LLM запрещает непроверенный поток; после reconnect старые deltas могут быть удалены | Публиковать только проверенный ответ после commit; определён snapshot reset для истёкшего SSE cursor |
| R03 | P0 | Нет analysis_jobs/session storage и idempotency scope; leases только у ingestion_jobs. Повтор запроса может создать два run | Добавить durable jobs, fencing, session и idempotency constraints; отмена и terminal commit через CAS |
| R04 | P0 | API имеет необязательную expected version, но intent определяется асинхронно; 409 после 202 невозможен | Версия обязательна на приёме, отдельный async conflict code, атомарный bind версии, один незавершённый run на conversation |
| R05 | P0 | DATA называет chunk stable citation ID, snapshot имеет ещё evidence_id; LLM matches и API feature_matches не совпадают | Один AnswerV1 DTO, явное различие chunk/evidence IDs, quoted spans и snapshot membership |
| R06 | P0 | sources/{document_id} обещает snippet IDs без run scope; объяснение старой ревизии конфликтует с active-only retrieval | Run-scoped evidence endpoint, явный source_run_id; исторические snapshots доступны только владельцу |
| R07 | P0 | Neo4j document key не содержит revision, uniqueness рёбер неполна для metadata; PG не хранит graph facts | Revision-specific graph nodes, durable graph_facts и provenance key; индексы восстанавливаются без повторной генерации |
| R08 | P0 | ING ждёт «все индексы», хотя IDX/GRAPH идут позже, а LightRAG P1; offline схема всё ещё требует custom KG | Обязательные ACK только Qdrant/domain graph, fake ACK gate ING и real gate GRAPH; optional LR не блокирует активацию |
| R09 | P0 | GRAPH использует LLM, IDX embedding, RANK rerank без LLM dependency; размеченный corpus только в позднем EVAL | Явные зависимости и ранняя небольшая fixture-задача; нет скрытого возврата к поздней задаче |
| R10 | P0 | API требует ownership/session до AUTH, UI зависит лишь от AUTH после API | Базовый auth раньше API; public exposure только после его gate |
| R11 | P0 | rerank cache key не содержит query, graph page key не содержит node/cursor, llm/rerank ключи без tenant | Полные scoped cache keys; авторизация до каждого cache lookup |
| R12 | P1 | Нет DTO graph nodes/edges/cursors; расширение может показывать evidence вне run | Ограниченный GraphV1, только snapshot provenance, подписанный контекстный cursor |
| R13 | P1 | OBS P1, но ранние INFRA/API требуют health; unknown CPU model делает обязательный health невозможным | Разделить bootstrap readiness и функциональные gates, минимальные логи в ранних задачах |
| R14 | P1 | Instant не является проверенным reasoning effort; общая оценка не выведена из карточек, EVAL смешивает harness и разметку 100 cases | Проверить официальные модели, сохранить заданные семейства, пересчитать трудозатраты и разнести крупный scope |

## Исправления и повторный проход

Все R01–R14 закрыты на уровне planning-контрактов. При повторном проходе уточнены ссылки на новые DB-002/LLM-002, durable SSE high-water, привязка исторического объяснения к исходной idea_version и удержание graph facts. Проверяемые последствия перенесены в приёмку соответствующих implementation-задач.

| Замечания | Исправленные документы | Решение / будущий gate |
|---|---|---|
| R01–R04 | [DATA_MODEL](DATA_MODEL.md), [API_CONTRACTS](API_CONTRACTS.md), [LLM_CONTRACTS](LLM_CONTRACTS.md), [ARCHITECTURE](ARCHITECTURE.md) | ADR-008; DB-002, PLAN-001, JOB-001/002, API-001 |
| R05–R06 | DATA_MODEL, API_CONTRACTS, LLM_CONTRACTS, [SECURITY](SECURITY.md) | ADR-009; RANK-001, ANALYST-001, API-001 |
| R07–R08 | DATA_MODEL, [GRAPH_SCHEMA](GRAPH_SCHEMA.md), ARCHITECTURE | ADR-009; ING-001 fake ACK, GRAPH-001 real activation/rebuild |
| R09–R10 | [TASKS](../TASKS.md), SECURITY, [DEPLOYMENT](DEPLOYMENT.md) | ADR-010; LLM-002, EVAL-000, AUTH-001 до API |
| R11–R12 | [MEMORY_AND_CACHE](MEMORY_AND_CACHE.md), API_CONTRACTS, GRAPH_SCHEMA | ADR-009/010; STATE-001, GRAPHUI-001 |
| R13–R14 | DEPLOYMENT, ARCHITECTURE, TASKS, [EVALUATION](EVALUATION.md) | ADR-010; INFRA/DB-002, LLM-002, EVAL-001/002 |

### Сверка сценариев между документами

Это ручной walkthrough контрактов; приложение ещё не написано, runtime-тестами эти результаты не являются.

| Контрпример | Согласованный результат |
|---|---|
| Повтор POST после создания новой версии идеи | Авторизация → lookup idempotency → прежний run; новый payload с тем же ключом даёт 409 |
| Worker упал после patch, затем истёк lease | planner_applied_at не допускает второй patch; устаревший fencing token запрещает публикацию |
| Cancel одновременно с завершением | Закоммиченный cancel flag до terminal CAS выигрывает; terminal immutable, повтор вычисления не означает повтор ответа |
| Версия изменилась после HTTP 202 | failed/IDEA_VERSION_CONFLICT в RunV1; второй HTTP 409 не обещается |
| Модель вернула invalid draft или timeout | До проверки текст не виден; один repair для invalid draft, проверенный fallback → completed, invalid fallback → failed |
| Успешный пустой поиск / отказ всех каналов | completed/no_evidence с пустыми findings / failed/RETRIEVAL_UNAVAILABLE; частичный отказ отражён в coverage |
| SSE reconnect после compaction | Durable high-water не сбрасывается; run_snapshot reset восстанавливает состояние, terminal закрывает поток |
| Объяснение старого источника после смены идеи и индекса | Явный source_run_id, его snapshot и idea_version; текущая идея не откатывается; historical=true |
| Чужой source_run_id или evidence UUID публичного документа | 404 до cache/Planner; public sources endpoint не выдаёт приватные snapshot IDs |
| Одинаковый текст в разных документах/ревизиях | Разные chunk UUID, revision-specific graph keys, evidence membership; donor reference_id не используется как наш UUID |
| Только один index ACK или отключён LightRAG | Частичный обязательный ACK не публикует revision; optional LR не блокирует полную пару Qdrant/domain graph |
| Обновление extractor и удаление старой Neo4j projection | Исторический view восстанавливается из удерживаемых PG facts по версиям run; новые факты не заменяют старые |
| Те же candidates при другом query; другой graph cursor | Ключи различаются по query/owner/config и node/cursor/version; каждый hit проходит ownership и membership |
| Кириллица/emoji в цитате | Chunk offsets и quote offsets имеют разные явно заданные начала; оба считаются в Unicode code points |

### Доноры и границы доказательств

Повторно получены четыре pinned commit/tree и 35 исходных файлов, SHA-256 совпали с [donors.lock.json](donors.lock.json). Все donor blob-ссылки в planning-документах входят в этот inventory. Smoke [ARCH-001](validation/ARCH-001/README.md) остаётся историческим свидетельством по закреплённым версиям: 6 проверок и 3 ограничения provenance; ARCH-002 его не выдаёт за новый прогон.

Custom KG LightRAG не переносит наш доменный provenance и не является обязательным индексом; разрешение его кандидатов требует собственного evidence store. PriorArtRAG используется как reference patterns; citation verifier не доказывает semantic entailment, его upstream scores не являются качеством нашей системы. Новых доноров, компонентов инфраструктуры и альтернативных RAG pipeline не добавлено.

## Модели и стоимость

Сохранены семейства из исходного задания: GPT-6 Astra, GPT-5.6 Sol и GPT-5.6 Luna. На 2026-09-29 проверены локальный каталог моделей и официальные страницы: [GPT-6 Astra](https://developers.openai.com/api/docs/models/gpt-6-astra), [GPT-5.6 Sol](https://developers.openai.com/api/docs/models/gpt-5.6-sol), [GPT-5.6 Luna](https://developers.openai.com/api/docs/models/gpt-5.6-luna), [модели Codex](https://developers.openai.com/codex/models). Режимы Low/Medium/High поддерживаются соответствующими семействами; Instant не используется как reasoning effort. Доступность зависит от клиента/аккаунта; план не переключает фактически работающую модель.

- Astra/High — 3 задачи: два архитектурных прохода и системный TEST-001. Для контрактов и финальной межкомпонентной проверки оправдан более дорогой review.
- Sol/High — 15 задач с транзакциями, безопасностью, LLM/graph интеграцией и валидаторами; Sol/Medium — 13 ограниченных задач с определёнными входами/выходами.
- Luna/Medium — одна OBS-001: метрики и retention поверх ранних health/redaction contracts. Решения по auth и очереди не отложены на эту дешёвую задачу.

Оценки ниже суммируются из 32 карточек скриптом, это плановые трудозатраты, не фактически затраченное время и не стоимость подписки/API:

| Объём | Агентская работа | Обычный review |
|---|---:|---:|
| Все 32 задачи, включая ARCH-001/002 | 43.5–83 ч | 1180 мин = 19 ч 40 мин |
| Оставшиеся 30 задач после ARCH-002 | 40.5–77 ч | 1105 мин = 18 ч 25 мин |

Для EVAL-002 отдельно заложены 8–16 часов человека на подготовку/экспертную разметку 100 случаев; они не включены в review. Загрузка весов/корпусов, ожидание credentials/квот и длительные inference-прогоны также не включены в агентские часы. Денежную сумму без фактических input/output/cache tokens, тарифного режима и подписки вычислить нельзя. При использовании API расход считать по usage и актуальной ставке выбранной модели; часы не преобразуются в токены.

Шесть новых карточек выделяют отдельные результаты: DB-002 — транзакционные repositories/outbox, LLM-002 — веса/CPU gate, EVAL-000 — ранняя разметка, JOB-002 — проверенные события/SSE, AUTH-002 — внешний периметр, EVAL-002 — полный baseline. Поэтому число задач выросло с 26 до 32. У 20 из 30 implementation-задач верхняя оценка ≤2 часов. SRC-001, ING-001, GRAPH-001, LR-001, PLAN-001, RET-001, ANALYST-001, API-001, UI-001 оставлены по 2–3/4 часа как связанные интеграционные результаты с собственной приёмкой; TEST-001 — 3–5 часов на конечный системный gate. Это явные риски оценки, а не обещание уложить каждый крупный gate в 120 минут. Содержательное разбиение устранило смешанные обязанности; дробление оставшихся интеграционных gates без новых проверяемых результатов не вводится.

## Автоматическая проверка и воспроизведение

Из корня репозитория, Python 3.11+, только standard library:

```powershell
python docs/validation/ARCH-002/check_plan.py --online --output docs/validation/ARCH-002/result.json
```

Без `--online` выполняется локальная проверка структуры. [Скрипт](validation/ARCH-002/check_plan.py) проверяет соответствие таблицы/карточек/Mermaid, известность зависимостей, отсутствие циклов, достижимость всех задач от ARCH-001, отсутствие P1 prerequisite у P0, наличие приёмки/ограничений/оценок, существование локальных link targets и закрепление donor URLs. Online-проход дополнительно сверяет GitHub commit/tree и SHA-256 файлов. Скрипт не проверяет содержание acceptance criteria, доступность всех внешних сайтов или runtime-поведение продукта; смысловая сверка описана выше.

[Машинный результат](validation/ARCH-002/result.json): passed; 32 задачи, 51 обязательная зависимость, 24 P0, таблица и Mermaid согласованы. Четыре donor commit/tree и все 35 файлов подтверждены. Финальный `git diff --check` проверяет whitespace; staged review исключает локальные данные/веса/секреты и постороннее изменение task.md.

## Итог и оставшиеся gates

Критерии review выполнены; planning baseline зафиксирован решениями ADR-008–010. ARCH-002 опубликована: коммит `d06c8d88aff7555ac0b1cea46284884562a9b392`, push в origin/main успешен; local HEAD и remote refs/heads/main совпали. Статус обновлён после этой проверки согласно task.md. Следующая отдельная задача — SKEL-001.

Неизмеренные CPU/RSS/latency, реальная транзакционная изоляция/ownership, качество русского grounding, доступ EPO/OpenAlex, восстановление и 100-case baseline остаются явными implementation gates в TASKS. Planning review не подтверждает их прохождение. Production-код не добавлялся; новый Python-файл проверяет только документацию и source pins.
