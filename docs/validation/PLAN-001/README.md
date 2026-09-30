# PLAN-001 — Intent planner и versioned patch

Проверено 2026-09-30. Реализация готова; до проверки push статус — «ожидает публикации».

## Выполненные критерии

- [x] Закрытый PlannerV1: строгие типы, обязательные поля, непустые строки, bounded arrays,
  уникальные ID, непересекающиеся remove/replace; контекстная проверка ID и base version.
- [x] OCR → barcode сохраняет ID заменяемого признака и остальные признаки. Add назначает UUID
  в shell; replace сбрасывает устаревший normalized_term. Новая идея в занятом диалоге запрещена.
- [x] JSON/schema/контекстная ошибка допускает один repair в оставшемся deadline, затем clarify
  без patch. Отказ provider сразу даёт clarify; cancellation и configuration error передаются выше.
  Repair получает исходный вход и коды/пути ошибок, без rejected values или thinking.
- [x] requires_retrieval вычисляет shell: semantic state hash, generation, retrieval config hash,
  query hash и наличие сохранённого evidence. suggested_retrieval не управляет решением.
- [x] «Второй патент» связывается с сохранённым порядком sources и разрешёнными evidence IDs.
  Историческое объяснение копирует snapshot и run_evidence с прежними IDs/generation, привязывает
  исходную idea_version и не меняет current_version диалога, даже после OCR → barcode.
- [x] Применение выполняется в транзакции под действующим lease и CAS. planner_applied_at
  и сохранённое решение обеспечивают повтор без второго patch, включая clarify без идеи.
  Проверены rollback, чужой владелец, устаревшая версия, отмена и истёкший lease.
- [x] Проверки ниже завершились успешно.
- [ ] Commit опубликован и подтверждён в origin/main.

## Границы интеграции

`IntentPlanner` получает общий `InferenceProvider`, model ID и содержимое `prompts/planner_v1.txt`.
Prompt входит в API/test Docker images. Provider сохраняет владение общим generation gate.
Контекст перед LLM читается через `IdeaStateService.context(owner_id, run_id)`; `apply` повторно
проверяет его в транзакции `session.begin()` и требует worker/lease_token. Сетевых вызовов внутри
транзакции нет. В JOB-001 worker свяжет эти операции с остальными стадиями run и обработкой ошибок.

В `config_versions_json.planner_v1` сохраняются только проверенное решение shell, prompt version,
focus IDs и retrieval fingerprint. Сам ответ модели и rationale туда не записываются. Повтор `apply`
возвращает это решение и ранее привязанную версию, игнорируя повторно вычисленный patch.
Для обычного повторного поиска query_hash должен учитывать вопрос и retrieval inputs согласно
MEMORY_AND_CACHE; передавать его должен доверенный shell. Redis cache этой задачей не вводится.

Hash идеи — SHA-256 канонического JSON семантических полей, с нормализацией Unicode NFC/пробелов
и порядка коллекций, без UUID. Различные query/config/generation требуют retrieval. Исторический
explain — отдельная ветвь: она использует completed source_run той же conversation независимо
от актуального индекса. Наличие только suggested_retrieval=false недостаточно для reuse.

Для порядковых ссылок snapshot может содержать `sources` в порядке показанных карточек;
каждая запись содержит document_id, title, evidence_ids (остальная metadata сохраняется как есть).
Соответствие ID проверяется по run_evidence. Без валидного сохранённого порядка prompt требует
уточнение для «второго» источника; прямые известные evidence IDs остаются допустимы. Порядок UUID
не интерпретируется как порядок документов. Копируется полный snapshot; focus только сужает вопрос.

`JobRepository.fenced_run` использует прежний порядок блокировок job → run; populate_existing
обновляет заранее загруженные ORM объекты, чтобы отмена из другой сессии не осталась незамеченной.
Затем блокируется conversation и проверяется current/base version. Сервис не публикует answer,
SSE или terminal status — это JOB-001/002. Новая миграция для PLAN-001 не потребовалась.

## Проверки и воспроизведение

```text
docker compose run --rm --no-deps -v .:/opt/app db-test pytest tests/unit/test_planner.py tests/integration/test_idea_state.py tests/integration/test_repositories.py tests/contract/test_inference.py
57 passed in 6.74s

python -m ruff check src/app/domain/planner.py src/app/services/idea_state.py src/app/storage/jobs.py tests/unit/test_planner.py tests/integration/test_idea_state.py
All checks passed!

python -m mypy src/app/domain/planner.py src/app/services/idea_state.py src/app/storage/jobs.py
Success: no issues found in 3 source files

git diff --check
exit 0
```

Compose PostgreSQL использован с отдельной временной схемой на каждый тест; схема удаляется
после проверки. Inference проверен через настоящий Ollama adapter с httpx fake transport,
включая malformed JSON, repair, ошибку provider, cancellation и отбрасывание thinking sentinel.
На Windows дополнительно запущены unit/contract tests в локальной Python 3.11 среде.

## Ограничения

Fake provider проверяет контракт и поведение shell; качество смысловой классификации локальной
модели этим тестом не измеряется. Schema validation не доказывает, что replacement точно передаёт
намерение пользователя. Входной summary и названия источников остаются недоверенными данными.
Полный worker/API путь и terminal mapping version conflict относятся к JOB-001/002.

Работа выполнена текущей моделью сессии GPT-6; рекомендованная Sol/High автоматически не включалась.
Делегирование не использовалось.
Существующие локальные изменения LR-001 исключаются из коммита PLAN-001.
