# EVAL-001 — offline harness и regression report

Дата: 2026-10-19. Статус: **выполнена и опубликована**.

Коммит реализации: `43e7adf17365963f4e3ed451bd429bb76eeeb23b`. Push в main
успешен; `git ls-remote origin refs/heads/main` подтвердил этот SHA после push.

Реализация: [eval/README.md](../../../eval/README.md). Cases EVAL-000 и исходные
fixtures не изменены; добавлен canonical-text SHA-256 lock. Judge является
отдельным offline компонентом и не подключён к production request path.

## Приёмка

- Frozen corpus/index: восемь synthetic документов, 10 dev cases, hash drift
  отвергается; expected IDs/spans не выбирают retrieval results.
- Версионированные run.json/results.jsonl/validated.jsonl: git HEAD/dirty,
  canonical file hashes, model configuration, prompt/schema/adapter versions,
  case/query, structured idea, candidate IDs, selected evidence, validated outputs.
- Grounding: membership, exact Unicode spans, document/revision/chunk IDs;
  no-evidence denominator=N/A; safe fallback без rejected relations.
- PublicAnalysis/Answer consistency и canonical renderer проверяются отдельно.
  Full/partial/conflicting/uncertain synthetic cases подтверждают структурные
  gates, а не семантическую истинность relation.
- Structured judge: closed scores 0–4, case ID, problem spans, rationale code,
  confidence, один schema retry, explicit disabled/unavailable/invalid status.
- Baseline diff требует одинаковые snapshot/cases/profile/judge; отмечает новые
  defects, Recall@10 и faithfulness regression, содержит per-case errors/outcomes.
- Replay: duplicate delivery, reset, lost terminal, text/hash matching.
- Negative tests: phantom/empty citations, fabricated quote/offset, same-text
  different revision, public-only claim, invalid/unsupported fallback, hidden
  reasoning extra field и rejected-value sentinel без записи в artifacts.
- Необязательное хранение eval_* атомарно; SQLite test проверяет case reuse и
  rollback всего run при drift последнего case. Live PostgreSQL write в этой
  задаче не выполнялся; существующая миграция/schema не менялась.

## Прогон и проверки

`baseline/` и `current/` содержат два fixture contract run; второй сравнивается
с первым. Полные синтетические validated outputs опубликованы вместе с отчётом.
Git dirty=true при создании acceptance artifacts ожидаем: добавляемый код
идентифицирован собственными SHA-256 до его коммита.

- Два прогона: **10/10 structural gates**, **0 baseline regressions**.
  [Markdown отчёт](current/report.md), [HTML отчёт](current/report.html),
  [run metadata](current/run.json), [validated observations](current/validated.jsonl).
- Recall@10 = **0.888889**, MRR = **1.0** на девяти непустых gold cases.
  DEV-007/008 дают Recall@10=0.5: lexical fixture не находит второй связанный
  источник. Метрика опубликована без оптимизации retrieval по этому dev gold.
- Citation validity = **1.0**, denominator **19 quote occurrences**; DEV-009
  возвращает no_evidence и citation validity=N/A. Девять остальных — safe_fallback.
- `python -m pytest tests/eval -o addopts='' -q`: **26 passed** после итоговых изменений.
- `python -m pytest -o addopts='' -q`: **343 passed, 49 skipped**, один существующий
  Starlette/anyio warning. Пропуски требуют внешних test URLs/credentials либо
  дополнительных интеграционных зависимостей; они не считаются успешными checks.
- `ruff check .`: passed. `mypy src eval`: **66 files, passed**.
- Frontend lint/typecheck/build: passed; unit tests **7 passed**.
- `docker compose config --quiet`, `git diff --check`: passed.
- SHA-256 всех версий кода в baseline/current сверены с итоговыми файлами.

## Ограничения

Fixture использует настоящий lexical fallback и `Analyst.analyze` с typed
unavailable provider. Все непустые ответы — deterministic safe_fallback;
это **не** production-модельный benchmark и не proof качества Tev1/GPT-OSS.
Judge отключён, semantic faithfulness=null. TTFT/tokens/RAM/model switch/browser
timings не измерены; latency gate UNSET. Импорт observations поддерживает
нормализованные fixture identities, а не произвольный live database export.
HTTP proxy, настоящая SSE доставка, DB-backed fencing и restart требуют внешних
integration checks; локальная replay-проверка их не заменяет.

EVAL-002 (100 размеченных кейсов и human-calibrated baseline), CORPUS-001,
AUTH-002 и release readiness этой задачей не закрываются.

Для снятия исходного publication blocker отдельный подготовительный коммит
`9634766` исправил Ruff formatting диагностических scripts, сохранил стандартные
исключения Ruff, явно разрешил отсутствующие optional ML imports для mypy,
убрал устаревшие ignores и сузил nullable chunk_id в graph route. Модели,
архитектура, production данные и checkpoints не менялись.
