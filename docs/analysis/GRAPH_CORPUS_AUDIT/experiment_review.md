# Независимая проверка GRAPH-002 / GRAPH-002-CAL и контрактов извлечения

Проверка 2026-10-02. Прочитаны существующие исходники и артефакты. Эксперименты, модели, ingestion и изменения баз данных не запускались. Это проверка валидности экспериментов; причины фрагментации самого корпуса устанавливаются отдельным чтением реальных EvidenceChunks.

## Точная выборка и происхождение

- Frozen manifest: `data/checkpoints/graph002-live-20261002.snapshot.json`, объект `snapshot`.
- Snapshot hash: `5b80378fa2d8312951446fcbb3ada7994d775f13d452ff08fd415377a5fcade0`. Независимый пересчёт SHA-256 JSON с `sort_keys=True`, `separators=(',', ':')`, `ensure_ascii=False`, без поля `snapshot_hash`, совпадает.
- Создан 2026-10-01 23:17:52 UTC / 2026-10-02 02:17:52 Europe/Moscow.
- 100 точных пар `document_id` / `revision_id`; все `source=openalex`, `kind=article`. 100 завершённых extraction states, 417 frozen `DISCLOSES_FEATURE` GraphFacts. Исключённых документов без завершённого состояния — 0.
- Все extraction states указывают `graph-extraction-v2:qwen3.5:4b-q4_K_M@2a654d98e6fba55d452b7043684e9b57a947e393bbffa62485a7aac05ee4eefd`; vocabulary `technical-feature-v1`, graph namespace `article-analysis-domain-v1`.
- Run `95f0e6c8-83b8-4788-9641-4c08b249e717`, resolver `graph002-technical-feature-v1`; checkpoint `data/checkpoints/graph002-live-20261002.json`, status `completed`.

`scripts/graph002_canonicalize.py::_capture_snapshot` выбирает последнее завершённое извлечение для active revision, сверяет число GraphFacts с extraction state и сохраняет IDs. `_restore_snapshot_facts` восстанавливает именно frozen IDs, независимо от последующего переключения active revision, и проверяет соответствие revision/document, наличия состояния, count и feature key. Manifest сохраняет факты и IDs, но не полный текст и не хэш каждого EvidenceChunk; поэтому полный corpus audit должен дополнительно проверять существующие PostgreSQL тексты/хэши, а не считать manifest самостоятельным архивом содержания.

## Пересчёт базовой структуры

417 frozen facts соответствуют 417 различным парам документ–feature: повторных incidences в этом snapshot нет. Распределение degree feature: 403 имеют один документ, 5 — два, 1 — четыре. Получается 409 features, 6 shared features (1.467%), 403 singleton (98.533%) и 8 дополнительных incidences. Число документальных пар с хотя бы одним общим feature равно 11.

Важны знаменатели:

- Среднее число различных извлечённых features на документ: **417/100 = 4.17**, как в `before.json`.
- **409/100 = 4.09** — число глобально уникальных labels на документ корпуса; это не среднее число features, присутствующих в документе.
- 417/89 = 4.685 edges на документ с фактами.
- 498 vertices = 89 документов с фактами + 409 features. Если включать 11 изолированных документов без фактов, вершин 509. `graph_metrics` включает эти 11 в 92 connected components; для подграфа только документов с фактами компонентов 81.

Структура действительно разрежена на уровне нынешней exact feature identity. Эти числа сами по себе не показывают тематическую разнородность корпуса, recall extractor или полезность графа для retrieval.

## Что показал GRAPH-002 v1

Источник: `docs/validation/GRAPH-002/{before,after,comparison,run-summary}.json`, `comparison.md`, checkpoint и `src/app/services/graph002.py`.

- Deterministic cleanup NFKC/case/whitespace/punctuation/hyphens сохраняет qualifiers, слова и числа; это presentation normalization, не ontology resolution.
- Candidate policy из checkpoint: top-k 8, cosine floor 0.60, 2,255 distinct candidate pairs. При 409 features полный pair space — 83,436 пар; candidate frame покрывает около 2.70% пространства. Это не оценка recall кандидатов: неизвестно, сколько реальных aliases за пределами frame.
- Model decisions: SAME 656, DIFFERENT 1,559, UNCERTAIN 40, protocol/run errors 0. «Errors 0» означает отсутствие зарегистрированных ошибок исполнения, а не отсутствие семантических ошибок.
- Merge policy v1 требует **label SAME, P(SAME) >= threshold и confidence >= threshold**. DIFFERENT создаёт cannot-link между любыми членами сливаемых компонентов; неизвестные пары внутри компонента не проверяются исчерпывающе, поэтому transitive false merge теоретически остаётся возможным.
- Threshold 0.95: 409 canonical nodes, net merges 0, компоненты 92, largest component 4 docs, connected pairs 11. Нулевое изменение — результат всей policy, а не доказательство отсутствия aliases.
- Sensitivity 0.90: 406 nodes, 3 net merges, 89 components, largest component 8 docs, connected pairs 17. Это рассчитанная sensitivity; материализованный результат выбранного run — 0.95.
- Суммарный classifier latency ~14,240.8 s = 3.956 h (около 6.315 s/candidate); feature embedding ~21.1 s; candidate retrieval ~18.1 s; total ~3.971 h. Это измерения этого локального run, не универсальный прогноз для другого CPU/батчинга/LLM. Почти всё время пришлось на pair classification.
- Контекст каждой normalized feature выбирается как **самая короткая** существующая quote, затем ограничивается 800 символами. Один representative context не гарантирует одинаковый технический смысл всех occurrences этого label.

## Что показал GRAPH-002-CAL

Источник: `docs/validation/GRAPH-002-CAL/*`, `scripts/graph002_calibration.py`, `src/app/services/feature_equivalence_v2.py`.

147 distinct existing v1 candidate pairs; 143 labeled, 4 пустых gold labels. Все стороны имеют короткий context. Gold file SHA-256 `dfa05987a13f20e1fb6a1eafed9c645e1c43e234a48a7dde70112887b4dc8dba`. 286 saved model decisions = 143 × 2 contracts. Model `tev1:4b`, digest `cef45ef93cf6df8bf32bdd689b0a8fd01f88ae9034d33ce890c54f77e4cd981e`.

Фактические strata после overlap/dedup: 40 high-similarity DIFFERENT, 40 UNCERTAIN, 25 SAME top-confidence/top-probability/medium-confidence, 10 SAME top-confidence/top-probability, 25 low-confidence SAME, 5 mandatory safety/alias cases, 2 mandatory contrasts. Это purposive stress sample по результатам v1, а не случайная репрезентативная выборка всех feature pairs. Gold: SAME 21, RELATED 62, BROADER_NARROWER 19, DIFFERENT 38, UNCERTAIN 3.

| Метрика | v2 strict 3-class | v2 5-class |
|---|---:|---:|
| SAME precision | 0.3393 = 19/56 | 0.3265 = 16/49 |
| SAME recall | 0.9048 = 19/21 | 0.7619 = 16/21 |
| SAME F1 | 0.4935 | 0.4571 |
| False SAME | 37 | 33 |
| Accuracy | 0.6923 | 0.4755 |
| Macro F1 | 0.4272 | 0.3798 |

Strict3 collapses RELATED/BROADER_NARROWER into DIFFERENT. Эти показатели относятся к **новым v2 prompts/contracts**, не являются прямой оценкой accuracy v1. При threshold 0.90 strict3 принял 9 пар, все false; при 0.95 принял 3, все false. В 5-class при 0.95 accepted=0: precision записана кодом как 0, но математически она не определена при отсутствии положительных решений; это также нулевая полезная recall.

Gate SAME precision >= 0.95 не пройден ни одним threshold. `selected_contract=3-class` — fallback по comparator, **не разрешение на full v2 canonicalization**: `selected_threshold=null`, `acceptance_gate_passed=false`.

### Ограничения и интерпретация

1. Precision/recall не переносится на весь корпус без representative sampling и известной candidate recall. Не оценивается extractor recall, число технических concepts в исходных текстах или downstream retrieval quality.
2. Выбор contract и threshold на том же gold set не является независимой holdout проверкой. Точных доверительных интервалов и межэкспертного agreement нет; для будущего acceptance 0.95 нужна новая adjudicated holdout выборка, достаточное число положительных решений и CI, а не только point estimate.
3. Некоторые gold SAME требуют повторной экспертной проверки на согласованность strict definition. Например `good selectivity` / `selectivity` теряет qualifier; `excellent reproducibility` / `repeatable` и `repeatable` / `sensor to sensor reproducible` смешивают внутри-сенсорную повторяемость с межсенсорной воспроизводимостью. Для последней пары один и тот же source sentence отдельно перечисляет обе характеристики. `excellent mechanical strength` / `mechanical robustness` также имеет scope/qualifier ambiguity. Это замечания к rubric, не автоматическая смена gold labels.
4. Четыре пустых gold labels исключаются правильно по `gold_label`, но только одна строка имеет `requires_manual_review=true`; в summary нужно считать review queue по blank gold, иначе метаданные вводят в заблуждение.
5. В sample только шесть `safety_critical=true`. Нулевое число safety-critical false SAME при thresholds не означает отсутствия других опасных semantic false merges: большинство ошибочных RELATED→SAME не маркированы этим флагом.
6. Threshold sweep считает pre-veto accepted pairs и отдельно veto count. В этом run veto count=0, поэтому итоговые counts совпадают; для будущих runs метрики после veto нужно считать отдельно.
7. JSONL cache key содержит contract и две phrases, но не digest, criteria version, source contexts или gold hash. Существующий report привязан к версиям/hash, но reuse после изменения prompt/context/model может дать stale decisions без строгой cache validation. Для данного run признаки stale cache не установлены.
8. Увеличение threshold ухудшает observed precision на этом stress sample. Это свидетельство непригодности данных scores как надёжного strict-equivalence gate для этих cases; нельзя объявлять их калиброванной вероятностью верного merge. Нужны reliability/held-out проверки, а не дальнейшее слепое повышение threshold.

## Контракт extractor: важные точности

`src/app/services/graph_index.py` и `src/app/domain/graph.py`:

- v2 LLM возвращает только edge_type, target_text, quote, confidence. Offsets/chunk ID добавляет deterministic code, а не LLM.
- Quote должна дословно встречаться **ровно один раз во всём переданном batch**. Повторная quote в одном или разных chunks отбрасывается как ambiguous provenance.
- target_text prompt просит exact phrase, но validator фактически проверяет **NFKC + casefold + whitespace canonical substring** внутри quote; не character-for-character raw target. Поэтому label уже нормализован по оформлению, но не по semantic aliases.
- Confidence >= 0.75; target <=160 chars, quote <=512 chars; alphanumeric content, корректные Unicode slice offsets, поддерживаемые endpoints/provenance.
- 6 chunks/batch, максимум32 drafts/batch, output-limit splitting до3 уровней; если single chunk всё ещё превышает лимит — exception, не успешный пустой результат. Фактическая config extractor: 2048 output tokens, context16384, timeout300 s; constructor defaults384 tokens/90s не следует выдавать за config этого corpus run.
- Prompt запрещает infer facts from background wording. Это может законно подавлять общие concepts из background/review текста; насколько именно — устанавливается raw-text audit.
- Невалидные drafts silently discarded; successful response with all rejected drafts может сохранить completed extraction state с count0. Поэтому completed zero state исключает «извлечение ещё не запускалось», но не различает LLM empty output, confidence filtering, ambiguous quote или invalid drafts. В persisted tables нет полного draft/reject trace.
- Онтология домена содержит и другие labels/relations (Technology, Classification, CITES, RELATED_TO и др.), но текущий extractor schema v2 ограничен DISCLOSES_FEATURE→TechnicalFeature. Нельзя приписывать extractor поддерживаемые в Enum отношения, которых нет в активном extraction contract.

Сохранение exact provenance полезно для проверки утверждения. Оно не требует использовать quoted phrase одновременно как единственную концептуальную identity. Добавление concepts/typed relations должно быть отдельным evidence-backed projection, а не разрушительным merge исходных фактов.

## Read-only пути доступа

Авторитетное содержание: PostgreSQL `source_documents` → frozen `document_revisions.id` → `evidence_chunks.revision_id`, frozen `graph_facts.id`/revision/extractor/vocabulary. В этом окружении уже запущены `article-analysis-postgres-1`, `article-analysis-qdrant-1`, `article-analysis-neo4j-1`; `ui-preview-api` находится в `article-analysis_backend`. Для анализа подходят `docker exec` существующего контейнера и PostgreSQL `BEGIN ... READ ONLY`; `docker compose up/run` не нужен и может активировать depends_on migration.

Qdrant article chunk collection вычисляется `src/app/integrations/qdrant.py::EmbeddingSpec` из namespace/model digest/dimension; payload содержит chunk/document/revision IDs. `POST /collections/{collection}/points/scroll` с `with_vector=true` читает существующие векторы. Shadow collection GRAPH-002 — `graph_feature_mentions_graph002_technical_featu_3dcc0a1ee166b09a5b67`; её feature embeddings нельзя выдавать за document embeddings.

## Вывод проверки экспериментов

Существующие артефакты надёжно подтверждают sparse exact-feature graph и неуспех текущей conservative semantic merge policy. CAL выявляет реальные strict-equivalence failures на targeted sample и обоснованно закрывает gate на full v2. Эти эксперименты **не позволяют выбрать corpus-limited / extraction-limited / ontology-limited диагноз без чтения корпуса**, не доказывают отсутствие общих concepts и не дают grounds увеличивать density как самоцель. Следующий архитектурный выбор должен опираться на raw-text overlap, тип/гранулярность features и evidence-backed retrieval outcomes.
