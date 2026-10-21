# Итоговые рекомендации

**Рекомендация — сначала сравнить B, C и D, сохранив A/E/F как конкурентов короткого screening.** Это выбор информативных экспериментов при CPU-ограничениях, не утверждение об уже достигнутом превосходстве. Варианты A–F на данном corpus не запускались; все их численные quality/performance показатели **`NOT_MEASURED`**.

Главный предметный вывод: более точный graph требует отдельной верификации **span presence, concept identity и qualified relation support**. Существующие PostgreSQL revisions, evidence anchoring и восстановимые projections полезно сохранить. Переписывать весь проект сейчас оснований нет.

## 1. Общая матрица архитектур

Обозначения: A — native LightRAG; B — improved source-grounded Hybrid; C — classifier pipeline; D — selective cascade; E — LightRAG + classifiers; F — joint span/relation encoder. Все strengths/weaknesses — исследовательские ожидания, не измеренные результаты.

| Критерий | A | B | C | D | E | F |
|---|---|---|---|---|---|---|
| Entity extraction mechanism | Native Qwen entities | Qwen selection of exact spans | Scientific/label-conditioned NER | NER/rules, Qwen по uncertainty | NER + native proposals E1 | Shared joint encoder |
| Relation extraction mechanism | Native descriptions → typed export | Short directed closed-schema claims | Marked pairs/span pairs + NO_RELATION | Cheap RE, Qwen ambiguous decisions | Native RE + domain checks; E2 external | Joint span-pair label scoring |
| Canonicalization | Native names; strict sidecar identity | Source anchor + dictionary/abbreviation | Blocking, dictionary, calibrated pair head | Как C + selective arbitration | Domain identity вне donor merge | Как C |
| Semantic validation | Constraints; A+NLI отдельный arm | NLI + chemistry/units gates | Compact RE/NLI + rules | Shared gate для обоих routes | Pre-merge domain RE/NLI | Rules + optional NLI |
| Source grounding | Нужен sanitizer/occurrence sidecar | Deterministic original-codepoint spans | Token/span→source mapping | Общие spans/claim records | Sidecar authoritative; donor refs auxiliary | Source spans из joint output |
| Small classifier usage | Необязателен, выделить arm | Основной verifier | NER/type/RE/linking/NLI | Те же плюс routing | NER/RE/NLI поверх framework | Один main encoder + verifier |
| LLM calls | C + gleaning + summaries + retries | C_B + retries | 0 | Routed subset + retries | E1 как A; E2 0 extraction | 0 |
| CPU feasibility | Технически возможна, cost неизвестен | Возможна на том же Qwen | Зависит от P и batching | Зависит от route fraction и loads | E1 может быть наиболее дорогим | Зависит от span/pair tensors |
| RAM requirements | Qwen + donor stores + sidecar | Qwen + verifier | Несколько encoders или sequential stages | Encoders + Qwen resident/switch | Models + два representations | Joint encoder + optional NLI |
| Expected accuracy strengths | Broad relation proposals | Прямой контроль provenance и schema | Узкая ontology, explicit negatives | Precision cheap path + context fallback | Native discovery с domain filter | Общий context entities/relations |
| Expected recall weaknesses | Rejection после native parsing; missing qualifiers | Copy/select omissions; strict validation | NER omissions, pair pruning | Необнаруженные уверенные ошибки | Cascaded filters и parse loss | Span width/caps, scope errors |
| Complexity | Средняя/высокая | Средняя | Средняя/высокая, gold/training | Высокая, routing/calibration | Высокая, dual state | Средняя, task adaptation |
| Risks | Name merge, summaries, direction/qualifiers | NLI domain shift, cost per window | Error propagation, pair explosion | Routing blind spots, model switching | Double processing, donor provenance | Correlated errors, new API/export |
| EVAL-001 compatibility | Новый native adapter/profile | Research adapter и schema | Research adapter и span mapping | Research adapter с route metadata | Native/external adapter + sidecar | Joint-output adapter |

Peak RAM во всех столбцах `NOT_MEASURED`; таблица перечисляет компоненты, а не обещает fit по сумме размеров weights. Formal compute expressions и исторический baseline: [PERFORMANCE_ANALYSIS](PERFORMANCE_ANALYSIS.md).

## 2. Shortlist и основания выбора

**B — приоритет precision/provenance.** Исторический audit обнаружил format/anchoring проблемы и разрыв quote→canonical identity; текущий v1.4 закрывает только часть. B сокращает model-generated metadata и проверяет qualified statements. Это наименьший conceptual шаг от текущих immutable evidence contracts. Не доказано, что NLI повысит precision сильнее, чем снизит recall; это X1/X3.

**C — приоритет CPU-efficiency.** Отсутствие autoregressive decoding и возможность batching дают ясную гипотезу экономии. PURE/SpERT/GLiNER обосновывают feasibility подхода, но не target accuracy. C необходим как независимый контраст B и как cheap branch D. Если pair count или supervised annotation слишком дороги, F может его заменить по X4.

**D — приоритет баланса.** Сочетает cheap extraction и ту же Qwen для ambiguity. Рекомендуется только после calibration и measured break-even; до этого более сложный pipeline не является преимуществом. Решающий X5 должен измерить missed ambiguity, accepted error и calls/time вместе.

**Почему A не объявлен победителем:** native extraction ещё не используется в текущем adapter; обязательные qualifiers/direction требуют адаптации. При этом A нужен для проверки, не теряем ли мы полезные relation proposals, выбрав только hand-built approach. **Почему E не первый full implementation:** E1 суммирует стоимости, E2 может дублировать C/F; нужна измеримая добавленная ценность donor management. **Почему F сохранён:** joint encoder — реально другая compute strategy, доступные checkpoint candidates позволяют дешёвый screening.

Top 3 может измениться после Phase 1/2. Выбор основан на независимости гипотез, пригодности существующих contracts и известных failure modes, а не на stars, популярности или предпочтении framework.

## 3. Матрица рисков

| Риск | Где вероятен | Что обнаруживает | Решение / остаточный риск |
|---|---|---|---|
| Exact quote с неверным смыслом | Все generative/encoder arms | Human support gold, chemical/role negatives | Раздельные support и grounding gates; NLI остаётся ошибочным |
| False SAME и transitive cluster collapse | A native names; C/D/E/F learned linking | Pair precision + cluster contamination | Conservative merge, cannot-link, abstention; меньше alias recall |
| Условия потеряны при merge | A/E summaries; любой binary-only graph | Qualified relation PRF, readback fidelity | Source-scoped assertion sidecar; donor descriptions не authoritative |
| Negation или unused technology стали positive | Все | Polarity hard negatives, scope annotations | Rules + classifier + abstain; rules не универсальны |
| NER recall ceiling | C/D/F | Candidate recall и end-to-end PRF | Missing-candidate cues, span width ablation; дополнительный cost |
| Quadratic pair cost | C/F и linking | P/window, CPU-seconds, RAM | Type/distance blocking, shared encoding; контролировать candidate recall |
| Уверенная ошибка не попала Qwen | D | Blind sample high-confidence/zero windows | Routing calibration/OOD cues; гарантий полного обнаружения нет |
| Двойная обработка без пользы | E1 | Paired accuracy delta vs all-stage cost | Отсечь E1 или оставить только independent external extraction E2 |
| Generic hubs создают красивую связность | Все | Generic-only document pair contamination | Разделять topical navigation и technical assertion graph |
| Domain shift science→patent/RU | Все | Separate document-family/language strata | Independent holdout; при отсутствии данных UNKNOWN |
| ONNX/quantization меняет labels | Compact models | Output parity и quality after export | Recalibration, version pin; CPU speed не предполагать |
| Gold leakage / модель оценивает себя | Все | Annotation lineage и grouped splits | Blind human gold; own NLI не gold judge |
| Corpus/version/cache mismatch | Все | EVAL compatibility manifest | Новый research profile, frozen source, split cache regimes |

## 4. Ответы на 15 исследовательских вопросов

### 1. Может ли маленький NER работать лучше Qwen 4B на entities?

**Может, но на данном corpus это не установлено.** Label-conditioned span models непосредственно выбирают spans и не должны копировать длинный JSON; domain encoders можно обучить целевой разметке. GLiNER benchmarks подтверждают подход, но не chemical roles здесь. Нужен X2 с exact/typed PRF, nested spans и source coverage; entity-only победа не означает лучший relation graph. [Модели и источники](SMALL_CLASSIFIERS_REVIEW.md).

### 2. Может ли compact relation classifier заменить часть generation?

**Да, как проверяемая архитектурная гипотеза для закрытого набора predicates.** PURE, SpERT, GLiREL и Relex предлагают реальные механизмы. Обязательны NO_RELATION, directional endpoints и negative examples; generic semantic similarity classifier недостаточен. Замена оценивается end-to-end с NER errors, а не только по gold entity pairs. [Обзор IE](LITERATURE_REVIEW.md).

### 3. Когда отдельная маленькая модель — плохая идея?

Когда задача редкая, domain gold слаб, модель повторяет encoding для каждой пары, её ошибки трудно обнаружить или loading превышает сэкономленную генерацию. Отдельный type classifier без контекста хуже подходит для reagent/analyte роли. Проверять ablation one encoder vs multiple; не превращать каждое поле DTO в отдельный neural service. [Compute analysis](PERFORMANCE_ANALYSIS.md).

### 4. Нужно ли обучать specialized models на своём corpus?

Не до zero-shot pilot. GLiNER/Relex/NLI уже дают starting point; calibration всё равно нужна. Если выявлены систематические target-label/role/chemistry ошибки, supervised head на SciBERT/MatSciBERT обоснованнее полного generative fine-tuning. Объём определяется learning curves; 100 документов не гарантируют достаточных примеров редких relations. Holdout не участвует в обучении.

### 5. Можно ли получить высокий precision encoder + rules + selective LLM?

Это наиболее содержательная гипотеза D: exact constraints ограничивают invalid proposals, compact models классифицируют типовые cases, Qwen получает contextual ambiguity. Но abstention может искусственно поднять precision ценой recall. Нужны precision–coverage, document coverage, critical error rate и calibrated routing, а не только один precision score.

### 6. Почему существующий Hybrid пропускает очевидные concepts?

Исторические причины 27 нулей **UNKNOWN**. Current v1.4 replay выявил 111 exact-occurrence rejects, 37 unsupported-canonical, 15 ambiguity и 1 quote/surface reject; 6 документов остались all-rejected, 21 получил accepted concepts. Эти категории показывают текущие failure gates, но retained traces не позволяют восстановить семантику rejected candidates. Caps, generation format и context — гипотезы для X1/X9, не доказанные исторические причины. [Аудит](CURRENT_PIPELINE_AUDIT.md).

### 7. Почему exact quotes не остановили false semantic identities?

Старый validator проверял surface/quote/offsets, но canonical name мог быть `NH3` при surface `gas`. Это разрыв между text presence и identity. v1.4 добавил lexical canonical gate и отвергает восемь сохранённых случаев; type, role, qualifiers и relation entailment этим не доказываются. Новая архитектура должна разделять эти проверки, а не лишь ужесточить quote matching.

### 8. Может ли native LightRAG исправить проблемы?

Он может дать другие entity/relation proposals и coverage. Но native name aggregation, descriptions и source chunk refs не гарантируют chemical identity, negation и exact provenance. В pin уже есть pre-merge hook; для authoritative qualified claims нужен adapter/sidecar. Native качество на той же Qwen — `NOT_MEASURED`; решают X6 и Phase 4, а не готовность framework. [Code audit](CURRENT_PIPELINE_AUDIT.md).

### 9. Что требует semantic understanding, а что алгоритмизируется?

Hashes, IDs, exact offsets, numeric parsing, unit conversion, schema/domain-range checks, dictionary lookup и snapshot consistency детерминируются. Роли, relation meaning, coreference, modality scope, condition attachment и contextual identity требуют linguistic/semantic решения; часть покрывается строгими patterns, остальное classifier/LLM с abstention. Детерминированная normal form не является entailment.

### 10. Где выгоднее использовать 4B?

Предварительно — на **ambiguous cases** с коротким evidence и closed choices, потому что explicit patterns/spans дешёвы, а generation dominates исторический wall budget. B сохраняет full extraction как обязательный control: selective overhead может не окупиться. Для identity нельзя использовать Qwen self-confidence как calibrated SAME probability. Итог определит X5 и measured break-even.

### 11. Может ли split pipeline уменьшить суммарный CPU-time?

Да, если экономия sequential decode больше encoder/pair/loading overhead. При `m(m−1)` pairs это условие легко нарушить; shared encoding F может оказаться лучше. Нужны CPU-seconds всего pipeline, wall time и peak RAM, а не только latency одного NER call. [Формулы и ограничения](PERFORMANCE_ANALYSIS.md).

### 12. Какие новые ошибки создаёт multi-model pipeline?

NER пропускает endpoint → RE его не увидит; type gate исключает правильную пару; разные tokenizers смещают spans; mapping term/role schemas теряет смысл; independently calibrated scores не дают calibrated joint correctness; verifier разделяет domain bias extractor; routing пропускает confident mistakes. Поэтому нужны intermediate candidate recall, interface identity и единый end-to-end gold.

### 13. Какие методы подходят именно technical patents/publications?

Scientific span IE, materials-adapted encoders, material–property–value–condition n-ary records, SAO/FOP для функциональных отношений, domain dictionaries/abbreviations, dependency scope rules и document-level evidence. SciERC/DocRED/POLYIE дают разные образцы разметки, но ни один не полностью совпадает с нашим доменом. Патентные dependent claims и modality требуют отдельного holdout. [Первоисточники](LITERATURE_REVIEW.md).

### 14. Какой вариант удобнее сравнивать через EVAL-001?

**B — самый прямой первый integration control**, поскольку использует существующие immutable chunks и source-grounded contracts. Но текущий EVAL не оценивает ни B, ни C/A автоматически: нужен общий research DTO/scorer/profile. После нормализации A–F сравниваются одинаково; выбирать алгоритм только по удобству adapter неправильно. [EVAL design](EVAL001_COMPARISON_DESIGN.md).

### 15. Какие architectures наиболее достойны реализации?

B/C/D как три независимые гипотезы; F может заменить C после joint-vs-split screening. A нужен как короткий native challenger. E следует реализовывать глубже только после измеримой пользы native proposals/management. Это последовательный отбор, не обещание реализовать всё и не итоговая победа Hybrid.

## 5. Что именно остаётся неизвестным

- Human entity/relation/qualifier gold и full v1.4 quality на 100 abstracts: **NOT_MEASURED**.
- Причины исторических 27 zero-concept outputs: **UNKNOWN**.
- Precision, recall, speed, RAM и стоимость всех A–F: **NOT_MEASURED**.
- Historical whole-run effective config за пределами сохранённых traces и нынешнее состояние live stores/runtime: **UNKNOWN**; сервисы не опрашивались.
- Transfer на patent claims, русский technical язык, long full texts: **NOT_MEASURED**.
- Достаточность existing 143 identity pairs для нового domain classifier и calibration: **UNKNOWN**, требуется human review и sampling assessment.
- Реальная CPU ONNX совместимость custom span/joint heads: **UNKNOWN**; наличие exporter documentation не заменяет проверку конкретного graph.
- Downstream польза graph assertions при unchanged consumer: **NOT_MEASURED**; нужен общий bridge и gold queries.

## 6. Первое последующее действие

После текущей доработки архитектуры следующий отдельный этап — **Phase 0B: совместная разметка development примеров**, уточнение ontology, GraphExtractionResult, RU–EN glossary/rubric и human gold. Затем Phase 0C с EVAL/MLflow/guards и минимальный screening B/C/F и native A capability. Не увеличивать generative model как основной способ улучшения, не делать новый full backfill и не менять production graph до quality gates. Полный порядок и критерии остановки: [EXPERIMENT_ROADMAP](EXPERIMENT_ROADMAP.md).

## 7. Архитектурное дополнение от 2026-10-21

Принять как проект общие компоненты из [MLflow, guards и RU → EN](OBSERVABILITY_SECURITY_LANGUAGE_ARCHITECTURE.md):

1. **MLflow:** версии данных/моделей/правил, параметры, quality/coverage, stage timings/CPU/RAM, отказы и безопасные артефакты EVAL. Явное логирование без автоматического захвата prompts/responses/reasoning; MLflow не заменяет scorer.
2. **Минимальные guards:** границы system/data, ограниченные полномочия моделей, schema/provenance/output validation, source quarantine по policy, bounded repair и безопасная телеметрия. Detector — дополнительный сигнал; гарантия устранения prompt injection не заявляется.
3. **RU → EN:** отдельный validated search view русских признаков с protected terms/numbers/units/negation. Английские source spans неизменны; русский ответ — через deterministic renderer с EN цитатами. T1 (перевод) — предварительный кандидат, T0 (прямой multilingual search) — обязательный контроль, Tref — human reference.
4. **Независимые сравнения:** сначала выбрать language policy на одном graph; затем фиксировать её при graph downstream evaluation. Guard policy также фиксирована. Стоимость translator/guards/logging входит в end-to-end измерение.
5. **Следующая разметка:** graph assertions, aligned RU/EN queries и clean/attack пары, с независимыми grouped splits. Сейчас определён только протокол, сами данные ещё не размечены.

Перед будущим запуском требуется согласовать effective model inventory: текущие LLM_CONTRACTS и YAML называют разные кандидаты Planner/Analyst. Это обнаруженное расхождение документации и конфигурации; runtime в этой работе не проверялся и не изменялся. Эффективность всех новых компонентов — `NOT_MEASURED`.

Исследование завершено на уровне документов. Commit/push, inference, tests, benchmarks, скачивание weights/datasets и изменения runtime не выполнялись.
