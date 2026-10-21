# Сравнение graph construction через расширение EVAL-001

**Только дизайн.** Не добавлены Python adapters, schemas, tests, fixtures или новые runs. Предлагается расширить существующий harness отдельным research profile; действующий EVAL-000/001 baseline и production contracts сохраняются.

## 1. Реальные возможности и пробелы

| Компонент | Сейчас, по коду | Для graph comparison |
|---|---|---|
| [eval/run.py](../../../eval/run.py) | Frozen fixture loading; versions; fixture/captured profile; отдельный output directory; optional judge results; local artifacts и optional DB persistence | Новый явно выбранный `graph-extraction-research-v1` profile с другим input manifest; по умолчанию существующий path |
| [eval/harness.py](../../../eval/harness.py) | `Observation`: idea/candidates/evidence/analysis/answer/public/presentation; exact fixture identity/spans, safe fallback и structural gates; Recall@10 и reciprocal rank | Отдельный `GraphExtractionResult` DTO, mapping/scorer, graph annotations; не перегружать AnswerV1 |
| [eval/judge.py](../../../eval/judge.py) | Closed 0–4 rubric, evidence problem spans, retry; disabled/unavailable/invalid статусы | Reuse structural validation для downstream; human gold для extraction. NLI из extractor не становится его собственным gold judge |
| [eval/report.py](../../../eval/report.py) | Aggregate metrics, stable defects, baseline compatibility, Markdown/HTML diff | Дополнительные graph metrics и profile-specific compare; прежние fields/thresholds остаются прежними |
| [Published run](../../validation/EVAL-001/README.md) | 8 synthetic docs, 10 cases; 9 safe_fallback, 1 no_evidence; judge disabled | Сохраняется как contract regression baseline; не включается в рейтинг graph quality |

Существующий importer требует fixture-derived UUID и ровно десять cases. Он не является универсальным импортом native PG/LightRAG entities. В `report.compare` проверяется одинаковый `index_snapshot`; graph arms с разными graph indexes нельзя сравнить простым снятием этого ограничения во всех профилях.

## 2. Минимальный GraphExtractionResult

Ниже проект полей, **не реализованная schema**. Каждый field получает строгий type и version; свободные provider bodies/reasoning отсутствуют.

| Группа | Поля и смысл |
|---|---|
| Envelope | `schema_version`, `run_id`, `architecture_id`, `corpus_snapshot_id`, `ontology_version`, `adapter_version` |
| Source | `document_id`, `revision_id`, `chunk_id`, `source_text_sha256`, `section`, `language`, `chunk_section_start/end`; optional `window_id` с mapping на исходные chunks |
| Status | `extraction_status`: `SUCCESS`, `EMPTY`, `PARTIAL`, `ALL_REJECTED`, `FAILED`, `ABSTAINED`, `UNSUPPORTED_CAPABILITY`, `BUDGET_EXHAUSTED`; `reason_codes`; known/unknown counts |
| Entities | `entity_local_id`, `mention_id`, `surface_text`, `entity_kind`, `contextual_role`, `source_spans[]`, `concept_ref`, `raw_score`, `calibrated_score`, `decision_status` |
| Source span | `span_id`, document/revision/chunk IDs, `[start,end)` in original Unicode codepoints, exact `text`, text hash; tokenizer offsets только auxiliary |
| Concepts | `concept_id`, `canonical_name`, `kind`, `normalization_version`, `alias_decision_refs`, `instance_scope`; canonical ID не участвует в gold matching как arbitrary string |
| Relations/assertions | `assertion_id`, `head_mention_refs`, `tail_mention_refs`, canonical endpoints при наличии, directed `relation_type`, `polarity`, `modality`, `assertion_scope`, `qualifiers[]`, `evidence_refs[]`, `support_decision`, `decision_status` |
| Qualifiers | `qualifier_type`, `raw_text`, raw/norm value, comparator/range, unit, conversion version, `applies_to_assertion_id`, `evidence_refs[]`, `status`; неизвестное значение явно unknown |
| Identity decisions | Pair/cluster refs, `SAME/RELATED/BROADER/NARROWER/DIFFERENT/ABSTAIN`, evidence, rule/model identity, score и calibrated policy ID |
| Provenance mapping | Native IDs→research IDs; sanitized/tokenized window→original codepoint mapping; `mapping_status`; каждый mapping many-to-many явно сохраняется |
| Execution | Wall/CPU ms по стадиям, peak RSS/aggregate RAM и способ измерения, input/output tokens, encoder forwards, candidate pairs, LLM extraction/summary/retry calls, cache/load status; missing = null + reason |
| Model/config identity | Qwen model/digest, все encoder IDs/revisions/weight hashes, tokenizer, dtype/quantization, runtime/backend/version, thread/batch/sequence budgets, prompt/schema/rules/dictionary/calibration hashes, Git HEAD/dirty и code hashes |

`EMPTY` допускается только после успешного полного прохода с пустым предложением. Timeout, parse failure и all-rejected — не empty. При частично потерянных outputs counts могут быть `UNKNOWN`; partial known counts сохраняются без выдуманного равенства. Dedup counts отдельно от rejects. `source_spans[]` допускает discontinuous/multi-sentence evidence; relation evidence не обязано совпадать только со spans endpoint entities.

Для qualifiers различать `NOT_APPLICABLE`, `EXPLICIT`, `UNKNOWN`, `UNSUPPORTED_CAPABILITY`. Отсутствие поддержки поля у architecture не должно приносить ей perfect qualifier accuracy на пустом знаменателе: gold-positive qualifier становится FN в end-to-end qualified relation score.

## 3. Adapter contracts

| Arm | Вход | Где снимать output | Обязательная проверка / невозможность |
|---|---|---|---|
| A | Те же frozen chunks, Qwen digest, LightRAG source SHA и prompt config | Parsed native entities/relations **до merge**, hook trace и sidecar; donor graph как auxiliary | Sanitization mapping, name/type collisions, direction и qualifiers. Невосстановимые claims пометить unsupported, не угадывать из summaries |
| B | Source windows + candidate span inventory | Short Qwen selection/claim result после deterministic grounding, до publication | New span exact occurrence; все dropped candidates counts; semantic gate version |
| C | Source text и explicit model/label versions | NER spans, candidate pairs, RE decisions, linking и NLI results | Token→codepoint mapping; отдельно candidate recall и accepted quality; zero LLM calls проверяется metadata |
| D | То же, плюс frozen routing policy | Outputs cheap path и Qwen path с `route_reason` и shared final gate | Дедуп origins, audit zero-output windows, учёт всех fallback calls; сравнивать при фиксированном routing budget |
| E1 | Native source плюс NER inventory | Before/after domain classifier hook и external assertion records | Не считать filter correction новым extracted fact без происхождения; count native generation полностью |
| E2 | External C/F assertions | Custom KG input и readback projection mapping | Same extractor outputs для storage ablation; donor summary не authoritative |
| F | Frozen windows и joint model label schema | Joint spans/pairs до scope rules, затем final qualified assertions | Shared encoder cost отдельно от P scoring, nested/overlapping spans, unknown polarity без default positive |
| Historical Hybrid | Сохранённые mentions/concepts с их version | Legacy result mapping | Inter-concept RE capability отсутствует: mention metrics доступны, RE отмечается unsupported, а не сравнивается как полноценный extractor |

Adapters только нормализуют representation и сохраняют provenance. Они не добавляют отношения из gold и не «исправляют» canonical identity по expected annotations. Общая deterministic validation допустима, но её effect публикуется отдельно для каждого arm.

## 4. Gold: структура, отбор и разметка

**Pilot-предложение:** 24 abstracts из frozen 100 с балансом original zero/nonzero, review/experimental, chemistry/mechanism, коротких/длинных, Unicode и repeated mentions. Из них 12 development, 6 calibration, 6 locked pilot holdout; близкие near-duplicates и document families распределяются группами. При невозможности такого split из-за family leakage уменьшить pilot и явно записать состав. Эти объёмы — рабочий старт, не статистическая гарантия.

До просмотра outputs новых arms аннотаторы читают **все spans и assertions в выбранных текстах**, а не только model proposals. Запись gold содержит:

1. Document/revision/chunk IDs, immutable text hash и annotation version.
2. Entity spans, kind, contextual role, normalized concept и local coreference clusters.
3. Directed predicates с endpoints; evidence spans; polarity, modality/status; qualifiers и attachment.
4. Identity pairs `SAME/RELATED/BROADER/NARROWER/DIFFERENT/UNCERTAIN`, grounded aliases и cannot-link constraints.
5. Completeness scope: какие sentences/relations исчерпывающе размечены; unresolved adjudication не становится negative gold.
6. Annotator IDs, blind independent decisions, disagreement/adjudication и рубрика.

Два человека независимо размечают минимум difficult slice и 25% обычных pilot документов; все disagreements adjudicated. Если доступен только один эксперт, это фиксируется как limitation, а не «multi-annotator gold». AI помогает подготовить инструменты/кандидаты только в development; holdout gold не образуется ответами тестируемых систем. Existing AI concept audit и 143 CAL pairs требуют review, их нельзя автоматически считать gold.

Предложенный initial error screen: 300–500 relation candidates и 150–300 identity pairs, с hard negatives; это дополнение к exhaustive document annotations, **не замена recall gold**. Число positive accepted decisions по редким predicates может оказаться недостаточным для confidence bounds.

Для Phase 4 можно прогнать все 100 documents, но 24 pilot документа уже contaminated tuning. Основной confirmatory score — на оставшихся **76 untouched** при group leakage control; агрегат 100 — descriptive. Если family grouping переносит документы между частями, реальные counts фиксируются заново. Разметить эти holdout тексты до просмотра outputs финалистов. Если бюджет позволяет лишь sample, precision оценивать с известной sampling scheme, а exhaustive recall для неразмеченной части оставить `NOT_MEASURED`.

**Patents:** отдельный будущий diagnostic holdout, например 12–20 разрешённых документов/семейств с claims и descriptions. Не добавлять его в исторический 100-document score. Сначала установить доступность текста, язык, provenance и права использования; сейчас документы не скачиваются. Метрики reports по patents/scientific abstracts раздельны.

## 5. Обязательные hard negatives

| Срез | Что должно различаться | Проверяемая ошибка |
|---|---|---|
| NO2 / NH3 | Разные chemical identities; generic `gas` не конкретный analyte | False canonical identity и relation endpoint substitution |
| Negation | `detects` / `does not detect`; `not only` pseudo-negation | Polarity и scope |
| Generic hubs | sensor/gas/material/performance vs конкретное понятие | Unsupported narrowing; artificial connectivity |
| Conditions | 25 °C / 200 °C; ppm / ppb; dry / humid | False claim merge, unit/value attachment |
| RELATED vs SAME | graphene / graphene oxide; property / material | Equivalence collapse |
| Unused technology | not used / considered / compared with / implemented | Mention превращён в usage |
| Role | reagent vs analyte vs device material | Type/role conflation |
| Revision | Same text different document/revision; repeated occurrence | Wrong provenance, first-match anchoring |
| Cross-sentence | Correct and ambiguous antecedent | Invented coreference или recall loss |
| Numeric scope | Range/comparator и несколько devices в предложении | Property другого endpoint |

Adversarial minimal pairs и естественная representative выборка оцениваются отдельно. Искусственное увеличение доли hard negatives не должно выдаваться за population false-merge rate.

## 6. Метрики offline graph extraction

Для PRF: `P=TP/(TP+FP)`, `R=TP/(TP+FN)`, `F1=2PR/(P+R)`. Нулевые/неприменимые знаменатели публикуются с counts и policy. При gold positives и пустом prediction recall=0, F1=0; precision undefined, не 1. Unknown annotations исключаются только по заранее определённой policy, с отдельным count.

| Метрика | Matching и знаменатель |
|---|---|
| Entity exact PRF | One-to-one exact source spans и kind; отдельно span-only. Не сравнивать arbitrary concept IDs |
| Entity relaxed PRF | Auxiliary overlap/head matching с frozen rule; primary exact score не заменяется им |
| Typing accuracy | Correct kind/role на matched gold spans / matched spans; end-to-end typed entity F1 рядом, чтобы не скрыть misses |
| Relation PRF | Matched endpoint mentions/clusters + directed predicate; no co-occurrence credit. Отдельно relation-only при gold endpoints и end-to-end |
| Qualified relation PRF | Endpoints + predicate + polarity + обязательные gold qualifiers/attachment; core relation без conditions не полноценный TP |
| Canonicalization pair precision | True SAME decisions / all predicted SAME decisions на independently labeled pairs |
| False merge rate | False SAME / predicted SAME; дополнительно false SAME / evaluated non-SAME pairs как distinct false-positive rate. Не смешивать со старым 37/143 |
| Cluster contamination | Gold incompatible mention pairs внутри predicted clusters / all within-cluster pairs; report cannot-link violations и размер крупнейшего ошибочного cluster |
| Grounding validity | Exact valid source references / all emitted source references; наличие текста отдельно от смысла |
| Semantic support rate | Human-supported accepted assertions / all reviewed accepted assertions; UNRESOLVED отдельно. Не использовать NLI score как human truth |
| Qualifier accuracy/F1 | Correct values/units/polarity scope и attachment / gold/predicted qualifiers; exact raw и allowed normalized equivalence отдельно |
| Negation | Per-class polarity PRF на assertions; accuracy дополнительно, чтобы majority positive не скрывала ошибки |
| Coverage | Document output coverage; gold concept recall; gold relation recall; source-window coverage — четыре разных показателя |
| Candidate recall | Gold relations, whose endpoints/pair survive proposal stage / all gold relations; upper bound для downstream classifier |
| Generic hub contamination | Fraction accepted mentions/edges attached to rubric-marked generic concepts; доля document pairs, связанных **только** generic concepts. Также доля неправильно специфичных generic identities |
| Rejection cost | Counts/reasons pre/post validation, abstention rate, unsupported capability, failed windows; quality и coverage условно по статусам |

High-degree node сам по себе не ошибочен. `graphene` может быть законным общим material. Generic contamination определяется рубрикой и задачей технического сопоставления, не произвольным threshold degree. Document pair counts — diagnostic graph topology, не metric factual correctness.

Micro и macro-document показатели сообщаются вместе с counts; confidence intervals/bootstrap по документам или families, не treating overlapping spans as iid. Paired comparisons на одном holdout; adjustment/multiplicity policy для многих arms регистрируется заранее. Precision-first shortlist требует также coverage floor, иначе пустой граф выиграет.

## 7. Downstream EVAL: меняется только graph knowledge

Для финалистов фиксируются: source corpus/revisions, query cases, vector/text index, embedding/reranker versions, planner/analyst и их prompts, evidence budget, retrieval logic и judge rubric. Изменяется **graph snapshot + extraction adapter**, с одинаковым интерфейсом технических facts. Online algorithms здесь не перепроектируются.

Имеется важный prerequisite: если текущий downstream consumer использует только raw `DISCLOSES_FEATURE` и игнорирует research assertions, смена графа не проверяет их пользу. До запуска нужен один общий bridge, одинаковый для всех arms, с recorded channel contributions. Если bridge ещё отсутствует, downstream result = `NOT_MEASURED`, а не доказательство отсутствия пользы графа.

Показатели: Recall@K, MRR@K (текущий reciprocal rank ограничен top-10), nDCG@K с заранее размеченными relevance grades, correct technical feature matching, human evidence faithfulness, unsupported relation rate, citation correctness и total analysis latency. Последние citation metrics делятся на **structural validity** и **semantic correctness**. При отсутствии relevance grades nDCG=`NOT_MEASURED`, не binary proxy без объявления.

Structured judge reuse возможен для итоговой rubric 0–4. Для count-based unsupported relation rate и per-feature correctness нужна дополнительная atom-level human annotation; один rationale `UNSUPPORTED_RELATION` не даёт знаменателя числа утверждений. Judge disabled остаётся допустимым structural status, но semantic quality не объявляется passed. Analysis latency не включает offline graph indexing.

## 8. Совместимость baselines и metadata

Предложение research compatibility identity:

- **Должно совпадать:** schema/profile, source corpus hash, gold/case IDs и annotation version, ontology и matching policy, input revision map, non-graph index config, downstream pipeline config, judge rubric identity, hardware/run regime для performance.
- **Разрешено различаться как treatment:** architecture/extractor config, encoder weights (recorded), graph artifact hash, extraction time и routing policy.
- **Нельзя скрывать:** model size/context change, different corpus, cached/uncached, CPU/GPU, re-chunking, fine-tuning data или downstream policy drift.

Существующие `fixture-contract-replay` и `captured-observations` compatibility checks **не ослабляются**. Для нового profile `source_snapshot` отделяется от `graph_artifact_snapshot`, и compare использует отдельный whitelisted treatment set. `index_snapshot` старых run.json не переименовывать задним числом. Explicit profile mismatch должен отклонять сравнение, а не падать обратно на fixture rules.

Минимальные будущие изменения: profile dispatch в `eval/run.py`; отдельные graph DTO/adapters/scorers рядом с harness; manifest/gold readers; report extension; comparison policy; downstream capture bridge. Существующие persistence tables можно не менять: research artifacts сначала file-based в новом каталоге, без DB migration. Сейчас ни один из этих модулей не создаётся.

## 9. Честность и воспроизводимость

1. Один frozen source corpus, exact hashes, stable revision IDs; gold независимо от candidate outputs.
2. Основной Qwen digest одинаков; effective context, output cap, thinking, temperature и retries фиксированы. Если prompt не помещается — logged failure/re-windowing по общей policy, без silent truncation.
3. Все classifier/tokenizer/rule/dictionary versions и training/calibration split hashes сохранены. Fine-tuning не использует pilot/confirmatory holdout.
4. Общий evidence budget; raw and accepted result scores; limitations unsupported fields не прячутся.
5. Cold/warm/cache regimes раздельно; same CPU threads/concurrency; GPU отдельный эксперимент.
6. Failures входят в coverage/recall, их документы не удаляются из сравнения. Human review blinded к architecture labels.
7. Performance includes every auxiliary model/summary/retry, indexing отдельно от online analysis.
8. Existing privacy contract сохраняется: validated evidence и allowlisted metadata; raw reasoning/provider bodies/rejected source dumps не публикуются. Gold хранит разрешённый source evidence, rejected diagnostics — counts/reason codes. Детальная forensic review требует отдельного согласованного retention design, а не тайного изменения логирования.

Порядок реализации/запуска — только после будущего разрешения, по [EXPERIMENT_ROADMAP](EXPERIMENT_ROADMAP.md).

## 10. Дополнение 2026-10-21: tracking, safety и язык

Контракт дополняется [архитектурой MLflow, guards и LanguageView](OBSERVABILITY_SECURITY_LANGUAGE_ARCHITECTURE.md); это спецификация будущего расширения, без новых модулей или запусков.

- **Один scorer:** EVAL-001 формирует authoritative report; MLflow хранит его безопасную проекцию, manifest hashes, versions, scalar metrics и denominators. Независимый MLflow judge не добавляется. Пересчёт старых predictions новым scorer получает новый evaluation run, а не перезаписывает результат.
- **Разные profiles:** `graph_extraction`, `crosslingual_retrieval`, `security_regression`; существующий fixture profile сохраняется. Graph comparison фиксирует language/guard policy; language comparison фиксирует graph snapshot; security comparison использует отдельные clean/attack fixtures. Совпадение campaign ID не делает profiles сравнимыми.
- **Manifest:** дополнительно effective model inventory, language/translator/glossary identity, guard policy, telemetry policy, split grouping и human annotation provenance. Несогласованные версии docs/config/runtime — readiness failure до эксперимента.
- **Языковые метрики:** term/number/unit/negation preservation и human semantic adequacy; paired retrieval delta к human EN reference; end-to-end RU answer support, ambiguity, fallback и latency. Отдельный aligned RU/EN query gold; exact evidence spans остаются английскими.
- **Safety метрики:** forbidden-effect rate на attempted cases с reached/completed counts; clean utility/false-block rate; утечка synthetic canary в logs/artifacts/error paths. Quarantine и translation failure учитываются в coverage, не исчезают из выборки. Успешная валидация JSON не считается успешной защитой или доказанной faithfulness.
- **Неизмеренные поля:** отсутствующие значения не экспортируются в MLflow как нули. Status/denominator/CI хранятся явно; пустые accepted outputs не выигрывают по precision. `TRACKING_PENDING` отделён от execution status; потеря обязательных данных даёт `INCOMPLETE`.
- **Privacy:** private query/translation text хранится только в контролируемом application/annotation store; в MLflow — IDs и разрешённые агрегаты. Raw reasoning/provider/rejected bodies запрещены и в trace attributes, previews, exception paths, и в локальном export buffer.

Начальный объём дополнительного gold и порядок совместной разметки указаны в Phase 0B roadmap. До разметки все новые quality/security показатели остаются `NOT_MEASURED`; целевые пределы benign degradation и retrieval non-inferiority — `UNSET` до preregistration на development.
