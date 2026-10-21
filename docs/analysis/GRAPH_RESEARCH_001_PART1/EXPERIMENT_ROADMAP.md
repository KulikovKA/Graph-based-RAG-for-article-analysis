# План контролируемых экспериментов

Статус всех этапов: **PROPOSED / NOT_RUN**. Никакие experiments, tests, inference, model downloads или implementation этой работой не выполнены. Начинать реализацию и запуски можно только в отдельной будущей задаче после разрешения пользователя.

## Принцип отбора

Не реализовывать шесть полноценных систем. Сначала проверить, что кандидат умеет представить нужный факт и имеет доступный checkpoint/API; затем короткий adapter-level pilot; только качественно приемлемым финалистам измерять CPU и строить весь corpus graph. Использовать один набор gold и один research profile EVAL-001.

**Исходный shortlist B/C/D — предварительный.** A, E и F могут заменить его элементы по результатам screening. F особенно важен как проверка, не является ли split pipeline C неоправданно дорогим из-за повторного encoding. E2 — storage ablation C/F, а не ещё один независимый IE алгоритм.

## Phase 0 — Eval readiness и gold

Дополнение от **2026-10-21**: [архитектура MLflow, guards и RU → EN](OBSERVABILITY_SECURITY_LANGUAGE_ARCHITECTURE.md). Текущая задача ограничена Phase 0A; разметка и реализация сейчас не выполняются.

| Подэтап | Результат | Когда |
|---|---|---|
| 0A — Architecture | Контракты GraphExtractionResult/LanguageView/telemetry, trust boundaries, схемы сравнения и список открытых gates | Сейчас: только документы |
| 0B — Совместная разметка | Сначала два dev abstracts и несколько RU intents; затем ontology/rubric/glossary, grouped splits и human gold графа/языка/защит | Следующая отдельная совместная задача |
| 0C — Evaluation foundation | После перехода к реализации: EVAL profile/scorer, безопасный MLflow adapter, общие guards и проверка failure/leak paths | До первого model pilot; сейчас не реализуется |

MLflow не вычисляет альтернативный gold score: он хранит метрики существующего EVAL, версии и manifests. Состав параметров/метрик/артефактов и правила сравнения заданы в архитектурном дополнении. До будущего запуска устранить расхождение кандидатов моделей в LLM_CONTRACTS и YAML посредством единого effective manifest; не менять модели молча между arms.

**Гипотеза:** существующий EVAL-001 можно расширить отдельным graph profile без изменения fixture baseline и без подмены semantic качества structural checks.

**Фиксировано:** HEAD/source manifest/revisions, EVAL-000 cases, старые baseline/current artifacts, raw/Hybrid historical results. **Меняется:** только будущий research contract/annotation protocol; production graph schema не требуется.

**Работа после разрешения:** согласовать ontology и source-scoped assertion model; создать exact adapters/spec; подготовить pilot split и human gold по [EVAL design](EVAL001_COMPARISON_DESIGN.md); отдельно классифицировать legacy fields unsupported. Сначала capability review по шести коротким development excerpts: chemical identity, negation, condition, relation direction, unused technology, repeated occurrence. Это не итоговый quality benchmark.

**Данные:** 24 pilot abstracts (12 dev, 6 calibration, 6 locked pilot holdout, с family grouping), annotation instructions; существующие artifacts как historical reference. Gold создаётся до outputs новых моделей. **Метрики:** annotation completeness, disagreements, identity mapping failures, leakage/group overlap, capability coverage. Метрики extractor quality пока `NOT_MEASURED`.

**Успех:** фиксированы source/ontology/gold/matching/calibration identities; нулевые unresolved provenance mappings в pilot; независимая semantic rubric; compatibility policy отделяет source snapshot от treatment graph. **Остановка:** отсутствует exact source, лицензия выбранного checkpoint не позволяет planned use, неизвестно значение необходимого qualifier, невозможно independent gold, или adapter подменяет смысл native output.

**Ресурсы:** чтение/разметка и adapter design; inference не нужен для первого contract review. Human hours `UNKNOWN`, оценивать после аннотации двух development документов, не заимствовать 8–16 часов из online EVAL-002 как стоимость exhaustive graph gold.

**Дополнительные наборы Phase 0B:** proposed 30 RU query intents с human EN reference (12/6/12) и 24 clean/attack пары (12/6/6), с группировкой по intent/source family/attack template. Это бюджет pilot, не доказательство достаточного sample size. Gold не создаётся в текущей работе. Security fixtures изолированы от frozen corpus; downstream dev queries не раскрывают gold 76 untouched graph документов.

**Readiness Phase 0C:** manifest и версии обязательны; отсутствие MLflow допускает безопасное сохранение отчёта с `TRACKING_PENDING`, потеря обязательного manifest означает `INCOMPLETE`. Ноль наблюдаемых критичных нарушений доступа/действий и утечек synthetic canary на guard cases; benign false-block/coverage показывать отдельно. Одинаковые guards и telemetry у A–F, стоимость включать в измерения. Raw prompts, private ideas, rejected payload и reasoning не логировать.

## Phase 1 — Small offline pilot

**Гипотезы:** B уменьшает format/anchoring failures; C покрывает значимую часть нужных relations без генерации; D исправляет часть ошибок C меньшим числом calls; A/E дают полезные native proposals; F уменьшает repeated encoding без неприемлемой потери качества.

**Фиксировано:** pilot source texts/windows, ontology, gold, common deterministic constraints, Qwen digest для всех generative arms, effective context, hardware режим. **Меняется:** extraction algorithm; extra encoder weights — recorded treatment. Начальный pilot zero-shot; trained variants не смешиваются с ними.

**Дешёвый порядок:** B и C на development slice; F тем же gold как shared-encoder comparator; A короткий native export/qualifier capability check; E1 только если A outputs добавляют полезные proposals, E2 отложить; D использует уже собранные cheap/Qwen decisions для предварительного routing analysis, затем отдельный реальный timed run в Phase 3. Offline simulation routing не выдавать за measured runtime.

**Данные:** exhaustive pilot annotations, candidate-pair labels, rejected counts/reasons, source windows. **Метрики:** entity/typing/RE/qualified-RE PRF; candidate recall; semantic support; identity errors; qualifier/negation; status/coverage. Wall time на pilot можно регистрировать как metadata, но целевой performance ranking ещё не делается.

**Успех:** кандидат представляет все обязательные claim fields, сохраняет source identity и даёт достаточно правильных proposals для calibration. **Остановка:** воспроизводимая подмена NO2/NH3, систематическая потеря polarity, unrecoverable provenance, только generic output, ошибки runtime совместимости. Один плохой prompt не доказывает непригодность метода: допускается одна заранее ограниченная dev correction; нельзя бесконечно оптимизировать одного кандидата и оставить остальные defaults.

**Ресурсы:** по формулам [performance](PERFORMANCE_ANALYSIS.md): B ≈ number of pilot windows + retries; A/E дополнительно gleaning/summaries; C/F — encoder passes/pairs. Секунды и RAM `NOT_MEASURED`. На этом этапе достаточно минимальных research adapters, не production integration.

## Phase 2 — Quality filtering и calibration

**Гипотеза:** precision-oriented thresholds и controlled ontology уменьшают false acceptance при достаточном recall; отдельные specialized heads нужны только там, где zero-shot систематически ошибается.

**Фиксировано:** gold holdout, source scope, candidate algorithm для данного calibration arm. **Меняется:** thresholds/routing/NLI choice на calibration; supervised heads — отдельный arm с frozen train set. После freeze ничего не подстраивается под pilot holdout.

**Данные:** calibration set, hard negatives, blind human support judgments. Если нужны trained heads, сначала annotation budget и learning-curve pilot; не запускать сразу full domain pretraining. **Метрики:** precision–coverage, risk–coverage, per-type PRF, false merge rate, Brier/reliability для classifiers, error categories.

**Предлагаемые gates для preregistration (не измеренный результат):** exact provenance validity 100% у published assertions; zero observed critical chemical identity/polarity errors на hard-negative set; target SAME precision ≥0.95 и relation semantic precision ≥0.95 с confidence bounds и reported sample size. Coverage floor определить на development до calibration/holdout: не хуже declared reference по entity/relation recall в пределах заранее выбранной non-inferiority margin. Если reference пока не измерен, gate = `UNSET`, отбор по нему невозможен.

Числовые 0.95 — проектная цель, а не обещание. При недостатке accepted cases нельзя объявить pass по point estimate: статус `INSUFFICIENT_SUPPORT`, расширить independent annotation или оставить candidate provisional. Слишком строгий threshold с почти пустым graph не выигрывает.

**Остановка:** candidate доминируется по precision и recall, не проходит critical gates после ограниченной correction, требует недоступной domain разметки или не даёт независимой calibration. **Ресурсы:** count-based evaluation и annotation; потенциальное training время `UNKNOWN`, отдельно от inference. Сохранить 2–3 финалиста, не обязательно ровно B/C/D.

## Phase 3 — CPU performance финалистов

**Гипотеза:** алгоритмическое сокращение generation/pairs уменьшает end-to-end CPU cost при зафиксированном quality level.

**Фиксировано:** weights, prompts, thresholds, corpus slice, windows, outputs policy, storage services и thread budget. **Меняется:** architecture; quantization/batching как явно отдельные arms. GPU не смешивается с CPU.

**Данные:** selected adapters и calibration-approved configurations. **Метрики:** total indexing wall, process CPU-seconds, p50/p95 document time, peak process/host RAM, swap, load/switch, LLM calls/tokens, encoder forwards, `P`, validation/persist/projection, failures. Cold/warm/extraction-cache отдельно. Начальный план — три uncached повтора финалистов, randomized order; расширять при высокой variance.

**Успех:** кандидат проходит quality gates после runtime/quantization change и лежит на Pareto frontier quality–time–memory; укладывается в заранее зафиксированный RAM budget с OS/services headroom. 32 GB физической памяти не равны допустимому allocation модели. Budget согласовать до run; сейчас `UNSET`.

**Остановка:** swapping/OOM, excessive pair growth, routed fraction D выше measured break-even, extra E summaries уничтожают преимущество без quality gain, cache contamination. **Ресурсы:** только measured pilot rates дают прогноз Phase 4; до них `NOT_MEASURED`. Повторная calibration после quantization обязательна при изменении outputs.

## Phase 4 — Frozen corpus comparison

**Гипотеза:** результаты pilot сохраняются на untouched corpus strata и качества достаточно для downstream проверки.

**Фиксировано:** 100-doc historical source snapshot, revision hashes, finalized weights/rubric/thresholds, одинаковые source windows и policy. **Меняется:** только shortlisted extractor/graph artifact. Результаты не пишутся в production stores/checkpoints.

**Данные:** весь frozen corpus, независимые annotations untouched части; 24 development/calibration/pilot docs маркируются как previously seen. Confirmatory gold ожидаемо 76 untouched документов, но фактические group-safe counts определяет manifest. Патентный holdout отдельный 12–20 documents/families, если подготовлен; без него patent generalization `NOT_MEASURED`.

**Метрики:** все graph metrics, confidence intervals по documents/families, critical errors, generic hub contamination, CPU/indexing/RAM, failure rate. Полный 100-doc score descriptive, untouched score primary. Corpus-wide recall допустим только при exhaustive scope gold.

**Успех:** quality gates и capacity сохраняются; выигрыши имеют практический размер и uncertainty assessment. **Остановка:** source drift, holdout leakage, новые chemical/condition systematic errors, существенная domain-specific degradation. После просмотра holdout correction создаёт новую version и требует нового независимого holdout; не переименовывать старый score в confirmatory.

**Ресурсы:** estimate по Phase 3 с document length/pair distributions и uncertainty range. Линейное умножение времени одного короткого chunk на 136 может быть неверным из-за hubs/summaries/loads.

## Phase 5 — Downstream EVAL

**Предварительный отдельный этап L — языковой pilot.** На одном фиксированном graph сравнить T0 (RU multilingual search), T1 (validated EN query view), Tref (human EN equivalent); T2 (RU+EN) добавить при обоснованной необходимости. Тот же source/relevance gold, reranker, final K и evidence budget; у T2 ограничить суммарные unique candidates и учитывать обе ветви. Измерять semantic preservation терминов/чисел/единиц/отрицаний, relevance, clarification/fallback, качество RU ответа и полную стоимость. Предварительно предпочтён T1, победитель `NOT_MEASURED`. Если language gate не пройден, Phase 5 для целевого RU сценария не объявляется готовой; offline Phases 1–4 могут продолжаться независимо.

Перед Phase 5 freeze language/glossary/guard policy и effective model inventory. Перевод не редактирует source, graph assertions или пользовательскую idea version; финальный ответ строится русским deterministic renderer с точными EN evidence. Подробнее — [языковая архитектура и gates](OBSERVABILITY_SECURITY_LANGUAGE_ARCHITECTURE.md).

**Гипотеза:** более точный graph повышает качество анализа technical ideas при неизменной остальной системе.

**Фиксировано:** RU queries, source/vector indexes, выбранная language/glossary policy, guard/telemetry policy, retrieval/analyst versions и settings, evidence budget, judge/human rubric. **Меняется:** только graph knowledge provider/snapshot через общий adapter. Языковое сравнение L проводится отдельно; не менять online retrieval algorithm в рамках graph comparison.

**Данные:** заранее размеченные query/source relevance и feature matching cases, supporting claims, graph-consumer bridge с одинаковым поведением для arms. Existing 10 synthetic cases остаются structural regression suite; не становятся scientific effectiveness benchmark.

**Метрики:** Recall@K, MRR@K, nDCG@K при наличии graded relevance, feature matching, human faithfulness, unsupported relation rate, structural/semantic citations, total online latency отдельно от indexing. **Успех:** подтверждённое downstream улучшение либо неухудшение при существенной экономии offline cost, без новых unsupported assertions. **Остановка:** graph channel не потребляет новые assertions, versions отличаются вне graph, недостаточный relevance gold, все ответы fallback. Последнее измеряет fallback contract, а не графовую пользу.

**Ресурсы:** дополнительная annotation и существующие online model costs. Они не входят в заявленный CPU выигрыш offline extractor; сейчас `NOT_MEASURED`.

## Phase 6 — Architecture ablation

**Гипотеза:** отдельные компоненты дают различимый полезный вклад; лишние можно убрать без потери качества.

**Фиксировано:** финалист, source/gold, hardware, основной Qwen digest и evaluation rubric. **Меняется по одному:** NLI on/off; role classifier; dictionaries; pair pruning; joint vs separate RE; selective routing; output schema; context size; native gleaning; summaries; quantization; incremental cache. Main comparison и ablation reports раздельны.

**Данные:** новый development slice для выбора ablation и отдельная confirmation portion, если результаты будут использоваться для новой финальной конфигурации. **Метрики:** paired quality delta, accepted/rejected/abstained counts, candidate recall, calls/tokens/time/RAM, errors by class. **Успех:** сохраняются gates и обнаружены Pareto improvements с понятной причиной. **Остановка:** повторное tuning по final holdout, изменение нескольких factors одновременно, экономия только за счёт падения coverage.

**Ресурсы:** только один финалист и наиболее вероятные bottlenecks; полный factorial всех вариантов не нужен. Savings `NOT_MEASURED` до ablation.

## Матрица решающих будущих экспериментов

| ID | Сравнение | Какое решение позволяет принять | Минимальный контроль |
|---|---|---|---|
| X1 | Hybrid v1.4 vs B | Помогает ли short span-based output | Та же Qwen/context, source spans gold; старые v1.3 metrics не baseline B |
| X2 | GLiNER small vs medium vs domain head | Нужен ли supervised scientific NER | Одинаковые labels/split и span metric |
| X3 | MiniLM vs DeBERTa vs ModernBERT verifier | Какой support gate окупается | 3-way vs binary metrics раздельно; chemical/numeric negatives |
| X4 | C vs F | Стоит ли split repeated encoding | Same target ontology/candidate budgets; end-to-end и gold-endpoint RE |
| X5 | C vs D vs B | Действительно ли selective Qwen выгоден | Fixed routing policy; count missed ambiguity, all calls и loads |
| X6 | A native vs A+domain validation / E1 | Дают ли native proposals полезный recall | Native pre-merge outputs, одинаковые chunks/digest/gleaning |
| X7 | C/F vs E2 | Окупается ли donor graph management | Exact same extracted assertions; storage/projection fidelity |
| X8 | Exact identity vs dictionary vs pair classifier | Можно ли безопасно увеличить aliases | SAME precision, cannot-link/cluster contamination, RELATED отдельный class |
| X9 | 4096 vs larger effective context | Контекст или format ограничивает extraction | Тот же source, prompt/output policy; actual truncation metadata |
| X10 | FP32 vs INT8 / batch sizes | Реальная CPU экономия без quality loss | Same inputs и calibrated outputs; all stages included |
| X11 | Same consumer, different frozen graph | Полезен ли граф для дипломной задачи | EVAL-001 research capture, unchanged online pipeline |
| X12 | T0 vs T1 vs Tref; T2 при необходимости | Нужен ли RU → EN перевод и окупается ли bilingual retrieval | Один frozen graph, query gold, общий candidate/evidence budget; language policy — единственный фактор |
| X13 | Clean/attack пары и варианты guard policy | Какие нарушения блокируются и насколько страдает полезная задача | Изолированные fixtures, fixed language/model policy, forbidden-effect и false-block metrics |
| X14 | Telemetry export/recovery и измерение overhead | Можно ли воспроизводимо сравнивать runs без утечки текста | Synthetic canaries, одинаковые outputs, безопасный manifest и replay экспорта без повторного inference |

X12–X14 — будущие отдельные проверки общих компонентов; их результаты не подменяют ranking extractors. Обязательные guards не отключаются на production данных ради ablation. Минимальная readiness X13/X14 предшествует model pilot; performance overhead уточняется при реальных измерениях Phase 3.

Окончательное решение принимается по X1–X8 и Phase 4/5, а не по topology, framework completeness или рекламе model card. При отсутствии убедимого преимущества сохраняется текущий baseline с явно описанными ограничениями; результаты отрицательного эксперимента тоже исследовательски значимы.
