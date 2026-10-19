# Продолжение после HYBRID-002: canonical identity и диагностика

Дата: 2026-10-03, Europe/Moscow. Исходный HEAD `0c7838a`, рабочее дерево
до изменений чистое. Последние пять коммитов: `0c7838a`, `3543f0c`, `86e5e02`,
`14470be`, `66e78ef`. Прочитаны `task.md`, `TASKS.md`, forensic-аудит,
контракт, runner, inference adapter, миграция `0007` и связанные тесты.

Обновление 2026-10-19: **опубликовано** (`8fb0326`, в main).
Исходные общие Ruff/mypy blockers устранены коммитом `9634766` при завершении
EVAL-001; push и удалённая main проверены. Ниже сохранено состояние проверок
на момент подготовки refinement 2026-10-03.

Исторический статус: **ожидает публикации**. Общие Ruff/mypy gates не проходят на исходных
файлах; пользователь разрешил push только после прохождения проверок.
Сетевой push поэтому не выполнялся; ошибки транспорта или авторизации не установлены.

## Подтверждённая причина

В исходном `src/app/services/technical_concepts.py::validate_grounding` проверялись
точный codepoint slice, наличие quote в chunk и принадлежность surface выбранному
вхождению quote. `canonical_name` участвовал только в схеме и вычислении identity;
проверки его соответствия grounded surface не было. Поэтому точное `gas` принималось
как `NO2` или `NH3`, а `concept_identity` создавал специфический узел по canonical name.

До исправления новые adversarial-тесты дали **7 failed, 15 passed**: ни прямой
validator, ни путь reanchor не отвергали неподтверждённую identity. После исправления
эти проверки проходят. Существующий validator дополнен gate:
непустой `normalize_concept_name(canonical_name)` должен совпадать с
`normalize_concept_name(surface_text)`. Код отказа — `UNSUPPORTED_CANONICAL_NAME`.
Синонимы и chemical aliases не добавлены. Exact quote/surface и offsets проверяются
на исходном Unicode-тексте до нормализации identity. NFKC/casefold/punctuation
normalization применяется симметрично к identity и surface, без изменения evidence.

Это консервативный gate: корректный синоним с иной normalized surface тоже будет
отклонён. `NH₃`/`NH3` и fullwidth/case-варианты принимаются по прежней нормализации.
Gate не доказывает concept type, роль вещества, qualifiers или semantic faithfulness.
Расширение политики aliases требует отдельного доказательства; corpus-wide улучшение
качества или recall в этой работе не измерялось.

## Восемь исторических случаев

Использованы существующие локальные, git-ignored `live_read.json` и
`data/checkpoints/hybrid-001-full-v1.3.json`, публичный
[`accepted_semantic_findings.csv`](../../analysis/HYBRID_ZERO_AUDIT/accepted_semantic_findings.csv).
Проверялись только восемь mentions и их четыре chunks, без повторного аудита корпуса,
подключения к базам или extraction.

| Документ | Mention ID | Chunk ID | Canonical / surface | Исходный span |
|---|---|---|---|---|
| D094 | `1f879e1f93c057821891efb2e0cf4532fe2cb4a7c4197be73fb42dd8344819b0` | `1ecb24ee-8566-413b-877c-3db364e8d60e` | NO2 / gas | 1094:1097 |
| D013 | `30ede8dab3b39ef59697fd04abcf5bb8984ce21f06fe2af54ffa4962f338e422` | `c0fd9d14-3ff1-4e78-9188-d3040f5ddaba` | NH3 / gas | 124:127 |
| D005 | `523d57ad1113986f491260b8388f9b941f9f1d970529c636723fd2fb466e82c0` | `496eab91-ffa7-4e93-9be0-dba1a282191a` | NH3 / liquids | 354:361 |
| D034 | `58ee270a1420d9f27281607eee76c7902e13597324d8e4572e99f879aa54e980` | `62c66b5d-75c5-457c-98b6-34a78e0ae054` | NH3 / gas | 131:134 |
| D005 | `6ca47b6f5b103a28ef72c081abfe8197d7c2fc40b4f7ed8ffb13202d81431b94` | `496eab91-ffa7-4e93-9be0-dba1a282191a` | NO2 / gases | 344:349 |
| D034 | `af117970e6a3a0b97a37664e85bf88371d33fd79a0e6918e58a9b6e050b7ff89` | `62c66b5d-75c5-457c-98b6-34a78e0ae054` | NO2 / gas | 131:134 |
| D013 | `b762fb818b7024b0721111bb50b9546bc7dc97cbc196a9d9325c6922786d1552` | `c0fd9d14-3ff1-4e78-9188-d3040f5ddaba` | NO2 / gas | 124:127 |
| D094 | `e8ee9004a9e66c282a8738e06228dacfa34ebc41a3a1e4d95859bc3009e79e66` | `1ecb24ee-8566-413b-877c-3db364e8d60e` | NH3 / gas | 1094:1097 |

Для каждой строки подтверждено: SHA-256 source chunk совпадает с сохранённым hash;
chunk/revision/surface/quote/offsets совпадают между checkpoint и PostgreSQL export;
сохранённые accepted поля проходят исходную валидацию; новая валидация отвергает
их с `UNSUPPORTED_CANONICAL_NAME` (**8/8**).

Цепочка кода: полный `chunk.text` → JSON-string в prompt `_extract` → массив
`result.value['mentions']` → `validate_or_reanchor_draft(draft, chunk.text)` →
`TechnicalConceptMentionV1` и `validate_grounding` → `(chunk, mention)` в runner →
identity из canonical name → `concept_mentions` с теми же chunk/revision/offsets.
PostgreSQL сохраняет accepted row до Neo4j projection; составной FK связывает
mention с chunk/revision/document. Model draft не содержит authoritative chunk ID:
он берётся из локального `EvidenceChunk`, не из ответа модели.

**Точный blocker для полного исторического replay:** исходные model candidates,
provider content и reported offsets до reanchor не сохранены. Протестированы
retained accepted поля, а не выдуманный оригинальный payload. Момент появления
ложного canonical name и первоначальная коррекция offsets невосстановимы.
Причины 27 исторических нулей остаются UNKNOWN.

Остальные проверенные гипотезы: exact quote и surface/quote membership уже проверялись;
offsets относятся к неизменному chunk в Python codepoints; reanchor сохраняет
существующий контракт уникального exact occurrence и пересчитывает end; prompt
не обрезает evidence и не меняет его Unicode. Они не нужны для воспроизведения
подтверждённого пропуска canonical identity gate. Prompt теперь явно описывает gate;
extractor повышен до `v1.4`, resume checkpoint `v1.3` отклоняется прежней проверкой
config identity. Новые запуски должны использовать новый checkpoint path.

## Диагностика новых запусков

Миграция `0007` уже хранит authoritative per-document status/outer attempts/error;
исторический checkpoint хранит лишь accepted mentions и суммарные rejects.
По предложению observer/sidecar из HYBRID-002 расширен существующий файловый
checkpoint workflow. Отдельный `<checkpoint stem>.diagnostics.json` находится рядом
с checkpoint (при стандартном расположении — под git-ignored `data/checkpoints`).
Новая таблица или миграция не требуется; sidecar не является source of truth для facts.

Ключи — run/document/revision, внутри документа сохраняется история outer attempts,
внутри attempt — chunk ID и статусы каждого inference attempt. Resume добавляет
попытку, не удаляя предыдущую ошибку. Счётчики:

- `candidate_count`, `accepted_candidate_count`, `rejected_candidate_count`;
- `accepted_mentions` после commit/dedup, отдельно `duplicate_count`;
- `rejection_reasons` со стабильными кодами validator/schema;
- `document_attempt`, `document_retries`, `inference_attempts`, `inference_retries`;
- `status` processing/completed/failed и `outcome` MODEL_EMPTY/ALL_REJECTED/
  PARTIALLY_ACCEPTED/ACCEPTED/NO_CHUNKS либо код ошибки.

При полном parseable результате `candidate_count = accepted_candidate_count +
rejected_candidate_count`; dedup не является отказом validator. Если не все ожидаемые
chunks дали parseable массив, итоговые candidate/rejected counts — null, известные
частичные счётчики сохраняются в chunk records. Если обработаны все chunks, но
persistence завершился ошибкой, известные counts сохраняются и при failed status.
2048→3072 length retry хранится отдельно; raw counts
относятся к финальному успешно разобранному массиву, без смешивания retry prefix.
Пустой `mentions: []` отличается от UNPARSEABLE_RESULT и INVALID_ENVELOPE;
прочие протокольные ошибки сохраняются как PROTOCOL_ERROR. Пустой final content,
который inference adapter не может разобрать, попадает в UNPARSEABLE_RESULT:
его нельзя выдавать за валидное `mentions: []`.

Sidecar не содержит prompts, chunks, model/rejected values, reasoning или exception
bodies. В failures/checkpoint/DB error записываются allowlisted коды вместо `str(exc)`.
Запись атомарна через временный файл; ошибка чтения/формата или записи сообщает
статический `DIAGNOSTICS_*_FAILED` и не блокирует authoritative persistence.
При недоступности sidecar история наблюдений может отсутствовать; его номера
outer attempts отражают сохранённые наблюдения, а не реконструкцию потерянных попыток.
Жёсткий crash оставляет processing record; он не объявляется completed.

## Проверки и ограничения

- Целевые tests: **43 passed**. Проверяются false canonical identity, все восемь
  публичных quote/surface pairs на минимальных excerpt chunks, positive mentions,
  astral/combining/subscript/fullwidth Unicode, exact quote и границы occurrence,
  ambiguity/reanchor, count conservation, invalid envelope, timeout/unparseable,
  successful/failed length retry, dedup, история failed→resume→success, отсутствие
  секретных sentinels, повреждённый sidecar и запись sidecar с OSError.
- Полный pytest: **312 passed, 49 skipped**, один существующий Starlette warning.
  Внешние integration/security проверки пропущены без TEST_* URLs/credentials;
  inference/model smoke не запускался. Synthetic runner tests используют настоящий
  EvidenceChunk/JsonResult, fake provider и fake persistence; реального DB round-trip
  новых запусков нет.
- Ruff для всех изменённых Python-файлов и mypy для изменённых production-файлов —
  passed; `git diff --check` — passed.
- `docker compose config --quiet` — passed. Frontend lint/typecheck/build — passed;
  unit tests **7 passed**. E2E не повторялись: UI не изменён.
- Обязательный `ruff check .`: **205 ошибок в 13 неизменённых файлах**, включая
  три локальных `.git/*.py` и старые audit/benchmark scripts. Для всех tracked
  файлов с ошибками содержимое сверено с исходным HEAD; ошибок в изменённых файлах нет.
- Обязательный `mypy src`: **8 ошибок в 3 неизменённых файлах**:
  `evidence_pack.py:57` (tokenizers/import и unused-ignore), `reranker_local.py:26–36`
  (torch/transformers/import и unused-ignore), `api/routes/graph.py:231`
  (`UUID | None` вместо `UUID`). Эти файлы не изменены. Inference dependencies
  в локальной `.venv` не установлены; модели и пакеты для их запуска не загружались.

Production DB/Neo4j, старые mentions/checkpoints и raw GraphFacts не изменялись.
Full-corpus rerun и production extraction не выполнялись. LightRAG, retrieval,
env/config и архитектура не менялись. Публикация заблокирована общими проверками;
исправление посторонних defects не включено в этот запрос.

## TASKS.md и публикация

В TASKS.md нет карточек HYBRID-001/HYBRID-002 или разрешённой карточки для этого
follow-up. EVAL-001 и OBS-001 разрешены по завершённым dependencies, CORPUS-001
остаётся в работе; TEST-001/REL-001 заблокированы prerequisites. GRAPH-002 указан
как завершённый, хотя CORPUS-001 dependency ещё в работе; статус не исправлялся
и не использовался как разрешение нового corpus experiment.
Пользовательский follow-up записан без придуманного ID, со статусом
«ожидает публикации». Existing task acceptance/status не подменены этой работой.
После исправления исходных общих gates требуется повторить Ruff/mypy,
проверить состав отдельного русского коммита, выполнить push и сверить remote SHA.
