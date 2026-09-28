# Типизированный граф Neo4j

Граф публикаций и патентов публичный; пользовательские идеи **не пишутся в общий граф**. Узел `Idea` и его `HAS_FEATURE` для UI формируются из конкретной `idea_version` в памяти запроса. Так исключается утечка между пользователями и бесконтрольное дублирование идей. `Applicant`/`Inventor` добавлять только при наличии source IDs; для научной работы использовать `Author`, а не смешивать авторов с изобретателями.

## Узлы

`Patent{key, document_id, revision_id, publication_number, title, publication_date, source_url}`, `ScientificWork{key, document_id, revision_id, openalex_id, title, publication_date, source_url}`, `TechnicalFeature{key, canonical_text, vocabulary_version}`, `Technology{key, name, vocabulary_version}`, `Classification{key, scheme, code}`, `Applicant{key, name}`, `Inventor{key, name}`, `Author{key, name}`. У всех `key` — стабильный namespace-prefixed canonical ID, `source` и `updated_at`. Поверхностные упоминания без identity resolution остаются в evidence, не становятся глобальными лицами.

## Рёбра

`DISCLOSES_FEATURE` (document→feature), `USES_TECHNOLOGY` (document/feature→technology), `CLASSIFIED_AS` (patent→classification), `CITES` (document→document), `APPLIED_BY` (patent→applicant), `INVENTED_BY` (patent→inventor), `AUTHORED_BY` (work→author), `RELATED_TO` (feature↔feature, только curated rule). `DISCUSSES` как общий тип исключён: он не даёт проверяемой семантики. Не создавать LLM-generated новые типы узлов/рёбер.

Каждое доказательное ребро содержит `evidence_chunk_id`, `document_revision_id`, `extractor_version`, `confidence`, `validated_at`; один факт из нескольких источников — несколько provenance записей/рёбер с разными evidence IDs. Relationship без chunk ID допустим только для deterministic библиографической метадаты и маркируется `provenance_kind=source_metadata`. Логически уникальная связь `(from_key,type,to_key,evidence_chunk_id)`.

Ограничения: `key` unique для каждой label; индексы на `document_id`, `revision_id`, `publication_number`, `openalex_id`, classification `scheme+code`. Точные Cypher migrations и query plans проверить на выбранной версии Neo4j. Писать только параметризованные запросы; labels/types выбираются из enum приложения. Извлечение признаков: LLM предлагает объект строго по Pydantic схеме, validator проверяет evidence span, allowed type, нормализацию и confidence threshold; сомнительные кандидаты остаются неподтверждёнными. Удаление ревизии снимает только её provenance, а узел без рёбер можно очистить фоново.

Explanation subgraph строится сервером из текущей идеи и top evidence: не более 30 узлов/50 рёбер первоначально, максимум 20 новых узлов на запрос раскрытия, один hop, allowlist типов. Каждый document node несёт цитируемый `evidence_id`; UI не получает внутренние graph properties, чужие idea ID или полный граф.
