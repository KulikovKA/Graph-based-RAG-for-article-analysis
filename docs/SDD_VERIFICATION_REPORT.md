# Исходная SDD-верификация

Репозиторий `KulikovKA/Graph-based-RAG-for-article-analysis`, ветка `main`, исходный локальный и удалённый SHA `9af3d0d186f9ff383720bb87f74be616dd82cda5`. Матрица описывает именно это состояние до реализации первой волны. Данные fixture evaluation закреплены в `eval/fixture.lock.json` (Git blob `26020007d5e2bfc3ffb458799caaa3250658080c`), исходный профиль моделей — `config/models.yaml` (Git blob `4e6eae4b45bceea230445ac05aa6d77ab3603fb9`). Продуктовый корпус и ML-качество не измерялись.

На старте tracked-файлы чисты. `AGENTS.md`, `.codex/config.toml` и прежний `SDD_BASELINE_VERIFICATION.md` существовали локально без коммитов. Первые два входят в документационный commit по SDD Gate, прежний отчёт остаётся локальным. Codex CLI `0.171.0` показывает устаревший `multi_agent` и отдельный `multi_agent_v2`. Применение локальных default keys к текущей сессии не подтверждено. Используется поддерживаемый в этой сессии вызов субагентов с явно заданными `gpt-6.1-terra` и `xhigh`, одновременно до шести. Модель оркестратора задаётся пользователем.

`PASS` относится к указанной выполненной проверке. `FAIL` означает наблюдаемое несоответствие. `BLOCKED` отражает конкретную недоступную зависимость. `NOT RUN` означает отсутствие прогона. Присутствие базового компонента и планируемых требований отражено отдельно от фактических результатов. Неначатые возможности остаются открытыми без оценки FAIL.

## Матрица 21 активной задачи

Карточки, hard-зависимости и критерии — [активный TASKS](../TASKS.md#активная-сводка-и-зависимости). Префиксы `I-*` и `G-*` ссылаются на таблицы в нём. Тесты в последней колонке относятся к фактическому исходному состоянию.

| TASK-ID | SPEC / норматив | Реализация на исходном SHA и пробел | Тесты | Результат и открытые gates |
| --- | --- | --- | --- | --- |
| RES-EVAL-001 | Карточка, EVALUATION, ADR-017 | В основном репозитории fixture lock/harness; статус MLflow и калибровки в RESEARCH не проверялся | `tests/eval/test_harness.py` | PASS структурный baseline; BLOCKED допуск RESEARCH по текущим границам работ, I-RES |
| RES-KG-001 | Карточка, план, GRAPH_SCHEMA | В плане есть ссылки на Stage 3A.5.7/8; утверждённый переносимый профиль не подтверждён | `test_graph_index.py` проверяет локальный граф, исследовательский прогон отложен | PASS базовые offsets/enum в основном приложении; BLOCKED воспроизводимость RESEARCH, I-RES |
| RES-AGENT-001 | Карточка, LLM_CONTRACTS, SECURITY | В основном приложении Planner/Analyst, научное сравнение bounded agent относится к RESEARCH | Парное исследовательское сравнение не запускалось | BLOCKED RESEARCH, I-RES/I-AGENT |
| INT-KG-001 | Карточка, GRAPH_SCHEMA, DATA_MODEL, ADR-013 | Есть Neo4j-проекция и pilot24, нет подтверждённого mapping утверждённого профиля и прогона миграции | `test_graph_index.py`; live `test_graph.py` не запускался | PASS базовая валидация; BLOCKED утверждённый RES-KG-001, I-KG/I-CORPUS |
| INT-RET-001 | Карточка, ARCHITECTURE, ADR-013 | Dense, metadata, graph channel, RRF и rerank/evidence; нет готового связывания и обхода путей от vector hits | `test_evidence_pack.py`, `test_retrieval.py` | PASS pack; BLOCKED runtime DB и утверждённая INT-KG-001, I-KG |
| INT-GROQ-001 | Карточка, LLM_CONTRACTS, ADR-014 | Ollama за `InferenceProvider`, Groq адаптер и общие лимиты ролей ещё предстоят | `tests/contract/test_inference.py`, `test_model_configuration.py` | PASS legacy mock/config; NOT RUN Groq, I-SEC/I-AGENT/I-EVAL/I-OBS |
| INT-LR-001 | Карточка, ADR-013, API_CONTRACTS | Extra, адаптер и graph context wiring остаются в baseline; сохраняется historical coverage | `test_lightrag.py`, часть с DB помечена skip | PASS легаси unit; BLOCKED регрессия DB и cutover до INT-RET/I-LR |
| CORPUS-001 | Активное уточнение, DATA_MODEL, ADR-002/009 | Backfill, source adapters, normalization и два ACK. Исторический отчёт хранит результаты micro10, текущее покрытие EPO/совместимость целевой проекции открыты | `test_corpus_backfill.py`, `test_ingestion_normalization.py` | PASS fixtures; NOT RUN живой ограниченный прогон, I-CORPUS |
| APP-CHAT-001 | Карточка, API_CONTRACTS, SECURITY | Есть создание, список и загрузка чатов, нет rename/delete и отдельной страницы истории исследований | `tests/contract/test_api.py`, `ui.spec.ts`; `test_isolation.py` не запускался | PASS mock UI; BLOCKED PostgreSQL проверки; NOT RUN rename/delete, I-MEM/I-UI |
| APP-GUARD-001 | Карточка, SECURITY, ADR-016 | Есть ownership, CORS, CSRF, source allowlists и redaction; нет полного tool policy, consent flow и проверки прямой/косвенной injection | `test_perimeter.py`, adversarial fixture eval | PASS компонентные защиты; NOT RUN целевой контур, I-SEC |
| APP-AIR-001 | Карточка, ARCHITECTURE, DATA_MODEL, ADR-015 | Нормализация, outbox и проекторы существуют. Планирование, durable interval checkpoint и DAG не реализованы | `test_ingestion_normalization.py`, `test_corpus_backfill.py` | PASS базовые fixtures; NOT RUN DAG, I-AIR после I-CORPUS |
| APP-MEM-001 | Карточка, MEMORY_AND_CACHE, DATA_MODEL | Версии идеи, snapshots, summary fields и Redis key adapter существуют; отсутствуют bounded context selection и runtime cache wiring | `test_memory_cache.py`, `test_idea_state.py` | PASS fake cache; BLOCKED история на PostgreSQL, I-MEM/I-OBS |
| APP-AGENT-001 | Карточка, LLM_CONTRACTS, ADR-011/016 | Planner/Analyst, queue и SSE; перенос стратегии, bounded tools и реальный Groq отсутствуют | `test_inference.py`, `test_api.py`, UI SSE | PASS component lifecycle; NOT RUN tool loop, I-RES/I-KG/I-SEC/I-AGENT/I-MEM |
| APP-GRAPH-001 | Карточка, API_CONTRACTS, GRAPH_SCHEMA | Run-scoped graph и public source metadata; нет самостоятельного поиска, pinned public scope и context refs | `test_graph_api.py`, `test_graph_index.py`, mock browser | PASS графовые fixtures и UI; BLOCKED run API без DB; NOT RUN Explorer API, I-KG/I-UI |
| APP-UI-001 | Карточка, план, API_CONTRACTS, ADR-016 | Адаптивный чат, документы результатов и run graph; отдельного режима Explorer ещё нет | Frontend typecheck/lint/unit, Playwright UI и GraphDemo | PASS существующие mock UI сценарии; NOT RUN live двухрежимная приёмка, I-UI/G-TEST |
| APP-EXPORT-001 | Карточка, API_CONTRACTS, DATA_MODEL | Сохранённый AnswerV1 и evidence доступны; переносимый отчёт, attachment и PDF отсутствуют | `test_api.py` для baseline; `test_harness.py` проверяет offline HTML evaluation | PASS компонентная экранизация eval; NOT RUN экспорт run, I-UI/G-TEST |
| OBS-001 | Карточка, ARCHITECTURE, ADR-017 | Liveness/readiness очереди и структурированные журналы, нет полного usage/cache/jobs coverage | `test_skeleton.py`, perimeter; нет целевых telemetry fixtures | PASS локальный health; NOT RUN сквозные метрики, I-OBS |
| EVAL-002 | Карточка, EVALUATION, ADR-017 | Fixture harness и file Judge, без продуктового сравнения четырёх режимов и калибровки живого Groq Judge | `test_harness.py` | PASS offline fixture/структура; NOT RUN frozen product pilot/holdout, I-EVAL/G-TEST |
| AUTH-002 | Карточка, SECURITY, DEPLOYMENT | Локальный TLS/CORS/perimeter; прежний runtime аудит обнаружил порты за пределами Caddy, публичный TLS и два аккаунта не подтверждены | `test_perimeter.py`, [прежний отчёт](validation/AUTH-002/README.md) | PASS компонентный perimeter; исторический FAIL runtime ports, BLOCKED внешний стенд, G-EXTERNAL |
| TEST-001 | Активное уточнение, SECURITY, API_CONTRACTS, release gates | Есть component/integration/browser suites и старые evidence reports; текущий end-to-end и restore не подтверждены | Целевые backend/static и mock Playwright; live browser, red-team и restore не запускались | PASS выполненные компоненты; NOT RUN полная сквозная приёмка, G-TEST |
| REL-001 | Активное уточнение, план, DEPLOYMENT | Есть Compose и инструкции прежней версии. Целевые clean install, restore, demo и release tag не подтверждены | Проверка релизной топологии не выполнялась | NOT RUN, G-FINAL зависит от G-TEST/G-EXTERNAL |

## Выполненные проверки

| Команда | Результат |
| --- | --- |
| `git status --short --branch`, `git rev-parse HEAD`, `git remote -v`, `git ls-remote origin refs/heads/main` | PASS идентичность основного репозитория, локальная и удалённая ветки равны |
| `codex --version`, `codex features list`, `docker compose ps --status running` | PASS инвентаризация; из сервисов Compose в исходном проекте наблюдались Neo4j и loopback-прокси |
| `& .venv/Scripts/python.exe -m pytest tests/test_skeleton.py tests/contract tests/security/test_perimeter.py tests/unit/test_memory_cache.py tests/unit/test_ingestion_normalization.py tests/unit/test_graph_index.py tests/unit/test_model_configuration.py tests/eval/test_harness.py --tb=short` | 106 PASS, 11 BLOCKED/skipped из-за неустановленных `TEST_DATABASE_URL`/`TEST_PROXY_URL`, 1 предупреждение Starlette |
| `& .venv/Scripts/python.exe -m pytest tests/integration/test_lightrag.py tests/integration/test_idea_state.py tests/integration/test_retrieval.py tests/unit/test_evidence_pack.py tests/unit/test_corpus_backfill.py --tb=short` | 20 PASS, 16 BLOCKED/skipped без тестовых сервисов |
| `ruff check src/app tests/contract tests/security/test_perimeter.py`, `mypy src/app/domain src/app/api` | PASS, mypy — 22 файла |
| В `frontend/`: `npm.cmd run typecheck`, `npm.cmd run lint`, `npm.cmd test` | PASS, 7 unit tests |
| В `frontend/`: `npx.cmd playwright test tests/browser/ui.spec.ts tests/browser/graph-demo.spec.ts --workers=1` | 23 PASS, 1 NOT RUN desktop-only pan на мобильном; API fixtures и локальный demo. Два перегенерированных PNG восстановлены до исходного состояния |

## Приоритеты и последующие проверки

1. P0. Свести INT-GROQ с I-SEC. Для отправки приватного контекста нужны проверки consent, budget, cancel/late reply, ограниченных инструментов и canary.
2. P0. Зафиксировать передаваемый профиль RES-KG → INT-KG → INT-RET, mapping версий и provenance. Параллельно подготовить Airflow на fixtures с проверкой двух ACK, идемпотентности и частичного сбоя.
3. P0. Закрепить измеримые контракты шести автономных компонентов, в частности Explorer API ↔ UI, export ↔ AnswerV1/snapshot, history ↔ scope Redis, Groq ↔ lifecycle. До этого этапа отдельных файлов `docs/specs/` для первой волны не было.
4. P0. Подготовить изолированные PostgreSQL, Redis, Qdrant и Neo4j для реальной регрессии, подобрать разрешённые входы EPO/OpenAlex и согласовать версионный evaluation plan.
5. P1. Повторить аудит портов в целевой топологии, внешний TLS и сценарий двух пользователей. В исходном аудите эта проверка BLOCKED.

Ни один из целевых gates не закрыт этой выборкой. Открыты I-RES, I-KG, I-CORPUS, I-AIR, I-SEC, I-AGENT, I-MEM, I-UI, I-EVAL, I-OBS, I-LR и G-MVP, G-TEST, G-EXTERNAL, G-FINAL. Работающий RESEARCH и сервисы не изменялись.
