# Модель данных PostgreSQL

PostgreSQL — источник истины для приложения. Внешние индексы Qdrant/Neo4j восстанавливаются из нормализованных записей и outbox. Все ID UUID, UTC timestamps, миграции Alembic. `owner_user_id` проверяется в каждом запросе через репозиторий и в интеграционных тестах.

| Таблица | Ключевые поля и связи | Инвариант |
|---|---|---|
| users | id, email_normalized, password_hash/auth_subject, created_at, disabled_at | email/subject unique; нет plaintext password |
| conversations | id, owner_user_id FK, title, created_at, updated_at | только владелец читает/меняет |
| messages | id, conversation_id FK, role, content, created_at, run_id? | append-only; лимит размера |
| ideas | id, conversation_id FK, current_version_id, created_at | одна текущая версия, принадлежность через conversation |
| idea_versions | id, idea_id FK, version_no, parent_version_id?, normalized_json, state_hash, created_by_message_id, created_at | `(idea_id, version_no)` unique; immutable; optimistic update по version_no |
| analysis_runs | id, conversation_id, idea_version_id, status, query, evidence_snapshot_json, answer_json, config_versions_json, created_at, completed_at, error_code | immutable входы/результат после terminal status |
| run_events | run_id, sequence_no, event_type, payload_json, created_at | `(run_id, sequence_no)` unique; SSE replay |
| source_documents | id, source, external_id, canonical_url, kind, title, publication_date, active_revision_id | `(source, external_id)` unique; no user ownership для публичного корпуса |
| document_revisions | id, document_id, source_updated_at, content_hash, normalized_json, ingest_state, retrieved_at | revision immutable; active после индексации |
| evidence_chunks | id, revision_id, section, ordinal, text, offsets, hash, language | stable citation ID; source location/provenance обязательны |
| ingestion_jobs | id, source, external_id, status, attempts, lease_until, error_code, created_at | идемпотентный retry; один active lease |
| outbox_events | id, aggregate_id, kind, payload, processed_at, attempts | atomic с revision commit |
| eval_cases/runs/results | case ID, input, expected evidence, snapshot refs, scores, versions | отделены от production run |

`normalized_json` идеи: `domain`, массив `features[{id, text, normalized_term?, weight}]`, `technologies[]`, `constraints[]`, `language`. Текст без уверенного происхождения не перезаписывает исходную формулировку. Patch добавляет/удаляет/заменяет признаки по ID, не по позиции. `state_hash` — SHA-256 канонического JSON, включая schema version; не содержит личных ID. Сравнение версий позволяет показать изменение C→D.

Evidence snapshot хранит список `{evidence_id, document_id, revision_id, chunk_id, quoted_span, source_url, retrieval_score, rerank_score, index_version}`. Ответ ссылается только на evidence IDs snapshot. Для воспроизводимости старые ревизии не удаляются, пока есть ссылки из run; retention и экспорт задаются отдельной политикой. Сообщение пользователя, run и idea version создаются атомарно там, где возможно; ошибки внешних сервисов не откатывают исходное сообщение.

Индексы: conversations(owner_user_id, updated_at), messages(conversation_id, created_at), idea_versions(idea_id, version_no desc), analysis_runs(conversation_id, created_at desc), source_documents(source, external_id), evidence_chunks(revision_id, section), ingestion_jobs(status, lease_until). PII минимизировать: использовать auth subject, шифрование диска хоста/backup и право на удаление пользовательских данных с учётом зависимых run.
