# Модель данных PostgreSQL

PostgreSQL — источник истины. Qdrant/Neo4j восстанавливаются из нормализованных записей, сохранённых graph facts и outbox. Собственные primary IDs — UUID, timestamps — UTC; внешние source IDs и Neo4j keys остаются строками. Миграции Alembic. Ownership проверяется в репозитории до обращения к кешу/индексам.

| Таблица | Ключевые поля и связи | Инвариант |
|---|---|---|
| users | id, email_normalized, password_hash/auth_subject, created_at, disabled_at | unique email/subject, нет plaintext password |
| auth_sessions | id, user_id, token_hash, csrf_secret_hash, expires_at, revoked_at | В БД только hash bearer token; revoke при logout/disable |
| conversations | id, owner_user_id, title, summary_json?, summary_until_message_id?, created_at, updated_at | summary — derivation; исходные messages сохраняются |
| messages | id, conversation_id, role, content, created_at, run_id? | append-only; size limit |
| ideas | id, conversation_id, current_version_id, created_at | Одна идея на conversation, optimistic current pointer |
| idea_versions | id, idea_id, version_no, parent_version_id?, normalized_json, state_hash, created_by_message_id, created_at | unique `(idea_id,version_no)`; immutable |
| analysis_runs | id, conversation_id, owner_user_id, message_id, source_run_id?, base_idea_version_id?, expected_idea_version, idea_version_id?, planner_applied_at?, status, stage, outcome?, query, index_generation_id?, evidence_snapshot_json?, answer_json?, analysis_json?, public_analysis_json?, answer_presentation_json?, progress_json, coverage_json, event_seq_high_water, config_versions_json, idempotency_key, request_hash, cancel_requested_at?, created_at, completed_at?, error_code? | См. lifecycle ниже и planned ADR-011 extension; owner обязан совпадать с conversation |
| analysis_jobs | run_id PK/FK, attempts, lease_owner?, lease_token, lease_until?, next_attempt_at, heartbeat_at? | status принадлежит run; fencing token растёт при каждом захвате |
| run_events | run_id, sequence_no, event_type, payload_json, created_at | PK `(run_id,sequence_no)`; одна terminal запись; seq выделяется атомарно из run.event_seq_high_water, compaction не сбрасывает счётчик |
| run_evidence | run_id, evidence_id, document_id, revision_id, chunk_id, span_start, span_end, quoted_span, source_url, retrieval_score?, rerank_score?, index_generation_id | PK `(run_id,evidence_id)`; FK chunk/revision/document согласованы; immutable после snapshot commit |
| source_documents | id, source, external_id, canonical_url, kind, title, publication_date, active_revision_id? | unique `(source,external_id)`; только публичный корпус |
| document_revisions | id, document_id, source_updated_at?, content_hash, normalized_json, ingest_state, retrieved_at | Content immutable, ingest_state меняется отдельно; metadata для старого run берётся из его revision |
| evidence_chunks | id, revision_id, section, ordinal, text, section_start, section_end, hash, language | UUID scoped to revision/section/ordinal/hash, не hash текста между документами |
| graph_facts | id, revision_id, from_key, edge_type, to_key, chunk_id?, span_start?, span_end?, metadata_pointer?, provenance_key, logical_key_hash, provenance_kind, extractor_version, vocabulary_version, confidence?, validated_at | Валидированные факты — durable источник Neo4j; `logical_key_hash` уникален для logical fact key и предотвращает дубли при retry; identity/provenance см. GRAPH_SCHEMA |
| graph_extraction_states | revision_id, extractor_version, vocabulary_version, fact_count, completed_at | Маркер успешно сохранённого результата извлечения, в том числе пустого; projection recovery не вызывает LLM повторно |
| revision_index_acks | revision_id, backend, indexer_version, projection_version, acknowledged_at | unique `(revision_id,backend,indexer_version,projection_version)` |
| index_generations | id, parent_id?, config_versions_json, created_at | Immutable published manifest; указатель current переключается атомарно |
| index_catalog | id, current_generation_id | Один указатель на опубликованное поколение корпуса, transactional CAS |
| index_members | generation_id, document_id, revision_id | PK `(generation_id,document_id)`; FK на точную revision |
| ingestion_jobs | id, source, external_id, payload_hash, status, attempts, lease_token, lease_until?, error_code?, created_at | Повтор одного payload идемпотентен; fencing аналогичен analysis |
| outbox_events / outbox_acks | event id, aggregate_id, kind, payload; `(event_id,consumer)` ACK | Atomic с revision/fact commit; независимый durable ACK каждого consumer, повторная доставка допустима |
| eval_cases/runs/results | case ID, input, expected evidence, snapshot refs, scores, versions | Отделены от production run |

## Идея и приём сообщения

`normalized_json`: `schema_version`, `domain`, `features[{id,text,normalized_term?,weight}]`, `technologies[]`, `constraints[]`, `language`. Feature IDs — UUID, назначаемые shell; patch оперирует ID, а не позициями. Replace сохраняет ID логического признака, изменение текста меняет state hash; удалённые ID повторно не использовать. `state_hash` — SHA-256 канонического JSON семантических полей + schema version, исключая personal/feature UUID и timestamps; порядок нормализуется детерминированно.

В MVP один нетерминальный run на conversation: partial unique index по conversation при status pending/running. Сообщение, run и analysis job создаются одной транзакцией после ownership, quota и проверки `expected_idea_version` (0, если идеи ещё нет). Unique `(owner_user_id,conversation_id,idempotency_key)` возвращает прежний run при том же каноническом request_hash; иной payload с тем же ключом — 409. Idempotency lookup предшествует проверке занятого conversation/текущей версии; авторизация всегда раньше lookup. Ключ живёт столько же, сколько run.

Planner работает асинхронно. `base_idea_version_id`, query, request/config inputs фиксируются при приёме. Worker в одной транзакции делает CAS current version, создаёт новую version при реальном patch и однократно связывает `idea_version_id`/`planner_applied_at`. Retry не применяет patch повторно. Поздний конфликт завершает run failed с `IDEA_VERSION_CONFLICT`; он не меняет уже отправленный HTTP 202. Для clarify без существующей идеи `idea_version_id=null`, outcome=clarification. Внешний сбой не удаляет исходное сообщение.

## Run lifecycle — единственный enum для DATA/API/JOB

| Переход | Условие |
|---|---|
| pending → running | Захват job lease с новым fencing token |
| running → pending | Только ограниченный retry транзиентного сбоя/истёкшего lease; сохраняются immutable inputs и уже применённый patch |
| pending/running → cancelled | CAS по нетерминальному status и cancel request; результат не публикуется |
| running → completed | Проверенные AnswerV1 + snapshot + outcome и terminal events сохранены одной транзакцией |
| pending/running → failed | Исчерпан retry, version conflict, обязательная dependency недоступна или safe fallback невалиден |

Terminal states неизменяемы; повтор анализа после них создаёт новый run. Worker продлевает lease; запись результата разрешена только текущему lease_token, с проверкой cancel_requested_at и нетерминального status. Отмена выигрывает, если её флаг закоммичен до terminal CAS. Устаревший worker не может записать answer/events. Повтор вычисления после crash допустим, двойная публикация — нет. Retry/deadline budget задаётся в config и записывается в run; отмена не вызывает fallback.

Для completed `outcome ∈ {analysis,safe_fallback,no_evidence,clarification}`; для failed/cancelled outcome и answer null. Coverage и warnings — данные результата, не дополнительные statuses. Ошибка LLM → проверенный safe_fallback; отсутствие результатов успешного поиска → no_evidence; отказ всех разрешённых retrieval channels → failed/RETRIEVAL_UNAVAILABLE. При частичном отказе оставшихся каналов достаточно для анализа только с явным coverage.partial.

## Evidence и сохранённые запуски

### Planned extension ADR-011: результат и replay

Текущие `src/app/storage/models.py`, `repositories.py`, `jobs.py` и миграции `0001_initial_schema`/`0002_outbox_acks` проверены: AnalysisRun уже содержит answer_json/snapshot/coverage/high-water, RunEvent — JSONB payload, sequence PK и partial unique terminal. Новых колонок ниже пока нет. `JobRepository.complete` лишь сохраняет terminal answer под fence; он не валидирует результат и не создаёт run_events. Поэтому существование этих primitives не закрывает JOB-001/002. Production-код и старые миграции этим architecture change не меняются.

JOB-002 добавляет следующую свободную Alembic migration и расширяет models/repositories:

- `analysis_json nullable JSONB`: только validated AnalysisV1 для outcome=analysis, закрыт от API. Для остальных outcomes null. Это проверенный вход renderer, без model transcript.
- `public_analysis_json nullable JSONB`: точная PublicAnalysisV1 проекция AnswerV1, та же, что analysis_summary.
- `answer_presentation_json nullable JSONB`: versioned полный text/hash/chunk_count из API; после compaction не нужен новый renderer или LLM.
- `progress_json JSONB`: последний ProgressV1 и накопленные известные counts текущей попытки; durable snapshot для active reconnect. При retry сохранить только counts от реально переиспользуемых committed этапов; остальные удалить. stage и progress.stage согласованы.

Для новых ADR-011 runs completed требует answer_json/public_analysis_json/answer_presentation_json; analysis_json обязателен лишь при outcome=analysis. Для pending/running/failed/cancelled все четыре result-поля null. Валидированный draft до commit находится только в ограниченной памяти worker. Все projections immutable после terminal. Config versions включают `publication_contract=adr011`, analysis schema, renderer, validator, prompt/model/tokenizer, reasoning config и budgets. Миграция не придумывает AnalysisV1 для старых completed runs: legacy marker, null новых projections, старый AnswerV1 остаётся доступен; API/UI явно поддерживают отсутствие нового summary. Upgrade/downgrade/legacy read проверяются на fixture БД в JOB-002.

Единая fenced transaction сохраняет результат, diagnostics codes/counts, projections, terminal status, assistant message (если создаётся) и полный bounded event batch. Последовательности выделяются под блокировкой run из event_seq_high_water; сохраняются все chunks и ровно один terminal event. `is_terminal=true` только для completed/failed/cancelled; после него новых событий run нет. Progress/state/events до terminal также пишутся атомарно и требуют действующего lease, nonterminal status и отсутствия cancel. Recovery/cancel writer использует тот же порядок блокировок job → run и CAS; stale worker не может даже опубликовать progress. Уникальный terminal index защищает от дубля, service transaction гарантирует наличие terminal event.

Crash до commit оставляет только прежний progress/snapshot: ограниченный retry заново вычисляет analysis, без повторного patch и смены evidence. Crash после commit до доставки требует только replay, без повторного inference. При неопределённом исходе commit worker сначала перечитывает run; completed не исполняется повторно. Cancel до terminal CAS выигрывает и оставляет result-поля null; поздний ответ provider отбрасывается. Cancel после commit ничего не меняет, даже если клиент получил не все chunks. Deadline после reasoning до законченного JSON ведёт к fallback по snapshot, без сохранения промежуточного reasoning.

Retention событий — по API (24 часа после terminal как начальная настройка); компактация не удаляет run projections и не сбрасывает high-water. Run retention удаляет projections/events вместе с private run; собственные evidence FK и source_run_id сохраняют прежние правила. PublicAnalysis означает доступность владельцу, а не всему Интернету. Публичный source endpoint не возвращает эти поля.

`chunk_id` — FK на конкретную ревизию. `evidence_id` — UUID выбранного span в snapshot, назначается shell и не равен donor reference_id. Один chunk может давать несколько evidence entries. `span_start/span_end` — полуинтервал Unicode code-point offsets в **chunk.text**, `quoted_span == chunk.text[start:end]`; `section_start/end` chunks — offsets в нормализованном тексте section данной revision. Нормализация версионирована; frontend получает готовый span, не пересчитывает Python offsets как UTF-16 indices.

`evidence_snapshot_json` — каноническая сериализация run_evidence и metadata соответствующих revisions; записывается атомарно с этими строками до Analyst, затем immutable. Ответ может ссылаться только на snapshot своего run. FK run_evidence запрещает удалить revision/chunk с активными ссылками. После удаления личного run удаляются его snapshot/ссылки; разрешённые публичные документы остаются по retention policy.

`explain_evidence` требует `source_run_id` той же conversation, ownership и completed source run. Копируется его snapshot с прежними evidence IDs и явно отмеченным historical context; run.idea_version_id связывается с версией исходного run, current_version conversation не меняется. expected_idea_version при приёме всё равно проверяет текущую conversation, base_idea_version_id сохраняет этот вход; новая active index generation не инвалидирует такой вопрос. Нельзя одновременно применять смысловой patch и трактовать результат как объяснение прежнего snapshot. Для новой идеи/изменения признака/общего нового поиска используется текущая generation; старый run остаётся воспроизводимым по данным, без обещания побайтно повторить LLM-генерацию.

## Индексация и чтение

ING фиксирует revision/chunks/outbox. GRAPH сохраняет валидированные graph_facts до Neo4j projection. Барьер активации ждёт только обязательные `qdrant` и `domain_graph` ACK одной revision и ожидаемых версий. Новая revision без признаков допускает ACK пустой валидной graph projection. Optional LightRAG обновляется независимо и никогда не блокирует публикацию.

После ACK PostgreSQL одной транзакцией меняет active_revision_id и current index generation с immutable membership. RET фиксирует generation в начале поиска, ограничивает запросы доступными revision IDs и обязательно отбрасывает кандидаты вне её membership после чтения индексов. При недоступной проекции сообщает degradation; не подменяет revision новой. Индексы сохраняют необходимые поколения на время активных searches; исторический evidence читается из PostgreSQL. Смена embedding модели/размерности создаёт новую коллекцию и generation после полного reindex; версии словаря/extractor также фиксируются.

Нужны индексы conversations(owner_user_id,updated_at), messages(conversation_id,created_at), idea_versions(idea_id,version_no), runs(conversation_id,created_at), jobs(next_attempt_at,lease_until), chunks(revision_id,section), graph_facts(revision_id), memberships(generation_id,revision_id), sessions(token_hash). Межтабличные owner/idea/run/chunk соответствия проверяются FK/unique constraints где возможно, иначе в одной транзакции repository и негативными integration tests. PII минимизируется; disk/backup encryption и удаление пользователя учитывают зависимые run и sessions.
