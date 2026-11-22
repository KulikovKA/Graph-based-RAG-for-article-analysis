# Типизированный граф Neo4j

Граф публикаций и патентов публичный; пользовательские идеи **не пишутся в общий граф**. Узел `Idea` и его `HAS_FEATURE` для UI формируются из конкретной `idea_version` в памяти запроса. Так исключается утечка между пользователями и бесконтрольное дублирование идей. `Applicant`/`Inventor` добавлять только при наличии source IDs; для научной работы использовать `Author`, а не смешивать авторов с изобретателями.

Разделы «Узлы» и «Рёбра» описывают исходную схему основного приложения. Целевой перенос проверяется отдельно.

## Узлы

`Patent{key, document_id, revision_id, publication_number, title, publication_date, source_url}`, `ScientificWork{key, document_id, revision_id, openalex_id, title, publication_date, source_url}`, `TechnicalFeature{key, canonical_text, vocabulary_version}`, `Technology{key, name, vocabulary_version}`, `Classification{key, scheme, code}`, `Applicant{key, name}`, `Inventor{key, name}`, `Author{key, name}`. У всех key — namespace-prefixed string, source и updated_at. Document node key включает revision UUID (`patent:{document_id}:rev:{revision_id}` / `work:...`), поэтому новая ревизия не перезаписывает старые связи. Feature/technology key включает vocabulary_version; identity-resolution version включается в ключи лиц. Поверхностные упоминания без source identity остаются в evidence.

## Рёбра

`DISCLOSES_FEATURE` (document→feature), `USES_TECHNOLOGY` (document/feature→technology), `CLASSIFIED_AS` (patent→classification), `CITES` (document→document), `APPLIED_BY` (patent→applicant), `INVENTED_BY` (patent→inventor), `AUTHORED_BY` (work→author), `RELATED_TO` (feature↔feature, только curated rule). `DISCUSSES` как общий тип исключён: он не даёт проверяемой семантики. Не создавать LLM-generated новые типы узлов/рёбер.

GRAPH-002 экспериментально добавляет отдельную shadow-проекцию `CanonicalTechnicalFeature` и `DISCLOSES_CANONICAL_FEATURE`. Она связывается с теми же revision-specific `Patent`/`ScientificWork` узлами, но использует собственные `canonical_feature_id`, `run_id` и `resolver_version`. `evidence_count` сворачивает несколько GraphFacts одного документа в один semantic edge; исходные provenance и resolutions остаются в PostgreSQL. Эксперимент не заменяет `TechnicalFeature`/`DISCLOSES_FEATURE` и не входит в production retrieval.

Каждое доказательное ребро содержит `fact_id`, `evidence_chunk_id`, `document_revision_id`, span offsets, `extractor_version`, `confidence`, `validated_at`. Это chunk provenance, не run-specific evidence_id. Несколько источников/ревизий создают отдельные facts. Без chunk ID допустима только deterministic metadata с `provenance_kind=source_metadata`, document_revision_id и JSON pointer в immutable normalized_json. Логический unique key: `(from_key,type,to_key,document_revision_id,provenance_key,extractor_version)`, где provenance_key — chunk UUID + span или metadata pointer. Это устраняет коллизии nullable chunk IDs.

Валидированные facts сохраняются в PostgreSQL `graph_facts`, затем идемпотентно проецируются в Neo4j по fact_id. Restore не вызывает LLM заново. `CITES` относится к revision источника; target связывается с revision, разрешённой index generation запроса, либо остаётся библиографической ссылкой на document_id без traversal до её индексации. Запросы не переходят в inactive revision без явного historical snapshot.

Ограничения: `key` unique для каждой label; индексы на `document_id`, `revision_id`, `publication_number`, `openalex_id`, classification `scheme+code`. Точные Cypher migrations и query plans проверить на выбранной версии Neo4j. Писать только параметризованные запросы; labels/types выбираются из enum приложения. Извлечение признаков: LLM предлагает объект строго по Pydantic схеме, validator проверяет evidence span, allowed type, нормализацию и confidence threshold; сомнительные кандидаты остаются неподтверждёнными. Удаление ревизии снимает только её provenance, а узел без рёбер можно очистить фоново.

Explanation subgraph строится из связанной с run idea_version и его immutable evidence, включая historical revision. Сопоставление fact.chunk_id/span → evidence_id проверяется в snapshot; metadata edges включаются только для документов этого snapshot. Начальный лимит 30 nodes/50 edges; page — 20 новых nodes/40 edges, один hop; общий view cap 100/200. Раскрытие остаётся внутри snapshot, новые источники требуют отдельного retrieval run. GraphV1 и cursor contract — [API_CONTRACTS](API_CONTRACTS.md#graphv1-p1).

UI allowlist: Idea, IdeaFeature, Patent, ScientificWork и перечисленные выше публичные типы. Synthetic `HAS_FEATURE` связывает Idea→IdeaFeature по конкретной idea_version; `MATCHES` связывает IdeaFeature→document только по validated answer.matches. У HAS_FEATURE evidence_ids могут быть пустыми (это пользовательский ввод, не внешнее утверждение); у MATCHES и document nodes — непустые snapshot IDs. Публичные TechnicalFeature не смешивать с приватными IdeaFeature. Metadata edges могут иметь пустые evidence_ids, но DTO несёт только разрешённые document nodes. UI не получает internal Neo4j IDs/properties или чужую идею. Graph projection version фиксируется в run, чтобы поздняя смена extractor не меняла исторический view.

`config_versions_json` run фиксирует graph projection/extractor/vocabulary versions. Facts этих версий и revisions удерживаются в PostgreSQL, пока на них ссылается сохранённый run; новые версии facts добавляются без перезаписи прежних. После удаления старой Neo4j projection historical GraphV1 восстанавливается из PG facts и snapshot, без LLM и без подмены текущей projection. Garbage collection проверяет ссылки run перед удалением facts/revisions.

## Целевая совместимость с RESEARCH

| Область | Что сопоставляет INT-KG-001 |
| --- | --- |
| Сущности и онтология | Текущие `Patent/ScientificWork/TechnicalFeature`, [pilot24 v1](../graph_gold_pilot24/ontology/v1.0/INTEGRATION.md) и типы выбранного KG RESEARCH. Проверить домен/диапазон, направленность, значения полярности и модальности, ключи и разрешение сущностей |
| Фактические связи | Сопоставить исследовательские `RELEX_REL` с допустимым предикатом и сохранить исходный source triple, тип, направление и происхождение. Строка без подтверждённого mapping и источника остаётся вне factual projection |
| Семантика и навигация | `SIMILAR_TO` и `HAS_SHARED_CONCEPT` могут вести к документам или новым фактическим рёбрам, но не становятся фактом и не наследуют доказательство соседнего ребра |
| Provenance | Внешний source ID → document/revision UUID, hash нормализованного текста, section/chunk UUID, пересчёт document offsets в chunk offsets и проверка исходной строки. При разрыве окна через границу чанка требуется явное представление с точными spans либо отказ от mapping |
| Версии и исторический доступ | Namespace, snapshot fingerprint, ontology/extractor/index versions и membership. Отдельная проекция с parity tests, запись поколения и fallback на прежний профиль при миграции |

Наличие ontology v1, shadow canonicalization или высокого similarity score не подтверждает совместимость. Допуск требует точных контрольных цитат, Unicode тестов, проверки same-text/different-revision, идемпотентного импорта и исторического GraphV1 после смены поколения. Не сопоставлять окно с документом только по совпадающему тексту.

Explorer по опубликованной версии читает разрешённый публичный корпус. Исторический режим читает сохранённый контекст. Начальные caps GraphV1 относятся к run-scoped API; для самостоятельного поиска APP-GRAPH-001 фиксирует отдельные лимиты поиска, обхода, разбиения на страницы и обращения к evidence. Документы, найденные dense-каналом, расширяются в graph seeds только по проверенной revision в том же опубликованном поколении. [API Explorer](API_CONTRACTS.md#целевые-расширения-api)
