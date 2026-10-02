# Архитектурные варианты после чтения frozen corpus

Дата: 2026-10-02. Это предложения для сравнения архитектур, без реализации или запуска эксперимента. Основания: 100 OpenAlex abstracts/136 chunks, 87 документов gas-sensing core, 30 ближайших пар с общими техническими темами и нулевым exact overlap, разбор всех 11 zero-fact документов, типизация существующих features, проверка GRAPH-002/CAL и pinned LightRAG.

Критерий успеха — полезный, подтверждённый источником retrieval при сохранении различий между material, analyte, condition и утверждением. Рост edges или largest component сам по себе не является успехом. MENTIONS(topic) и DISCLOSES_FEATURE(claim) должны иметь разные значения. NO и NO2, graphene и rGO, повторяемость и межсенсорная воспроизводимость, «NH3 response» и «no NH3 response» нельзя считать strict aliases.

## Сравнение пяти вариантов

| Вариант | Ожидаемая польза | Сложность | Дополнительный CPU/ingestion | Provenance | Главный риск |
|---|---|---|---|---|---|
| 1. Raw exact graph + vector retrieval | Надёжные evidence; semantic discovery остаётся у vectors | Низкая | Почти без нового ingestion; текущий baseline cost | Exact quotes/offsets сохраняются | Слабая graph-only cross-document coverage |
| 2A/2B. Typed concept layer + raw facts | Нормализованные comparison dimensions; 2B возвращает omitted concepts | Средняя/высокая | 2A mapping; 2B дополнительные chunk extraction calls | Высокая при обязательных span anchors и PG resolution | Неверный type/scope, broadening под видом SAME |
| 3. Native LightRAG как отдельный builder | Более широкий entity/relation retrieval, потенциально полезные links | Средняя для pilot, высокая для production | Extraction + optional gleaning + hub summaries | Chunk attribution; exact spans требуют внешнего слоя | Name/type collisions, aliases, generic hubs, summaries |
| 4. Raw + typed concepts + LightRAG retrieval | Полное разделение claims, topics и дополнительных retrieval channels | Высокая | Цена 2B плюс native arm только если оправдан | Exact raw + PG-resolved semantic/context evidence | Дублирование каналов, сложная evaluation/recovery |
| 5. Raw + vectors + citation metadata + taxonomy | Дешёвая навигация/расширение кандидатов, минимальные semantic merges | Низкая/средняя | Metadata projection; LLM не обязателен | Ссылки на frozen metadata/chunks; citation не равна proof | Topic/citation expansion может вернуть нерелевантные документы |

## 1. Сохранить exact/provenance graph

Оставить его как проверяемый слой source-supported technical claims. Искать прежде всего существующими chunk vectors и reranker; sparse graph использовать для evidence inspection и точных traversal, не как единственный поиск технических аналогов.

Quality: сильная проверяемость уже сохранённых фактов, слабая concept recall. Это приемлемый baseline для диплома и обязательный control любого A/B. CPU cost и ingestion time новых channels почти отсутствуют; текущую цену graph extraction нельзя вывести из плотности графа. Provenance/interpretability максимальны в смысле exact source spans; произвольный длинный feature остаётся труден для семантического сравнения. Риск новых false merges отсутствует, существующая lexical identity всё равно не является гарантией одного смысла.

Reuse: PostgreSQL revisions/chunks/GraphFacts, Qdrant, Neo4j, planner/evidence pack, reranker и текущий context-only adapter. Удалять компоненты не требуется. GRAPH-002 можно сохранить исследовательским результатом с закрытым gate, без production semantic merge. Новая модель не нужна. На 1k/10k/100k масштабируется обычный indexed vector retrieval и linear chunk ingestion; cross-document graph usefulness сама по себе не вырастет. Численных runtime прогнозов без throughput measurements нет.

## 2. Typed semantic layer: разделить 2A и 2B

**2A — projection только над существующими facts.** Raw TechnicalFeature остаётся immutable evidence-bearing occurrence/claim. Mapping добавляет Material, Property, Performance, OperatingCondition, Process, Mechanism, Morphology, Device, Analyte; base concept и qualifiers хранятся отдельно. Alias/SAME, RELATED и BROADER_THAN не смешиваются. Один raw fact может содержать несколько concepts и роли, поэтому one-to-one merge недостаточен.

**2B — отдельные source-grounded concept mentions из chunks.** Этот шаг необходим для D007/D064/D092 и для общих concepts, которых нет в labels. Нормализация 417 имеющихся facts не создаст fact или mention у 11 zero-fact документов. Review MENTIONS(material/topic) может быть полезен для retrieval даже при законном отсутствии paper-specific DISCLOSES_FEATURE. Вариант 2B должен привязывать mention к revision/chunk/Unicode span; modeled, reviewed, proposed и experimentally measured claims различать явно.

Пример: «response of 105.1%», «high sensitivity to NO2» и «6 fold increase in NO2 sensitivity...» не SAME. Сравнимы через отдельно представленные device/material, analyte, response/sensitivity dimension, concentration/temperature и reference baseline. Значение, единицы, направление эффекта и условия остаются частью claim. `transparency` и `transparent` могут иметь один property concept; `high optical transparency` сохраняет qualification; numeric transmittance не становится alias произвольной transparency claim.

Quality: ожидается лучший retrieval по проверенным comparison dimensions; превосходство ещё не измерено. Complexity средняя для небольшого vocabulary, высокая для универсальной ontology. CPU: deterministic/curated mapping дешёв, LLM disambiguation и 2B chunk calls добавляют время. Для этого read-only audit runtime не измерялся. Прямой попарный classifier всех concepts избегать: GRAPH-002 уже потратил около 3.96 h classifier time на 2,255 candidates с практически нулевым безопасным приростом.

Provenance высока при обязательном evidence mapping, interpretability лучше flat feature. False merges ограничивать typed blocking, abstention, adjudicated aliases, отдельными related/hierarchy edges и контекстом; semantic similarity не является strict identity gate. На 1k vocabulary mapping может быть полуэкспертным; на 10k нужны versioned IDs, bounded candidates и incremental resolution; на 100k — batch/stream processing, sharding/queues, мониторинг hub/type/scope errors. Всепарное сравнение квадратично и не подходит. CPU cost зависит от chunks и candidates, а не числа graph nodes.

Reuse: все authoritative stores и current evidence validator; embeddings можно использовать для candidates, текущий Tev1 для automatic SAME gate не использовать. Не требуется удалять raw facts или БД. Потребуются новые projection/evaluation contracts и observability, но сейчас они не реализуются. Дополнительная модель не обязательна: начать с текущего Qwen и ограниченного dictionary, затем сравнивать качество отдельно. Для диплома этот вариант даёт ясную проверяемую гипотезу: чем concept/role layer помогает относительно vector baseline.

## 3. Native LightRAG как независимый builder

Извлекать из тех же frozen chunks entities, types, descriptions и relations; хранить результат в изолированных storages. Domain Neo4j и GraphFacts не заменять. Default entity guidance универсальна; domain-guided types — отдельная experimental arm, иначе эффект ontology customization будет ошибочно приписан библиотеке.

Pinned native ingestion агрегирует совпавшие normalized names, но автоматически не проверяет разные имена на strict semantic equivalence. Name key не содержит type. Alias splitting и homonym/type collisions возможны одновременно. Relations — endpoint pairs с descriptions/keywords, без обязательных domain role, exact quote и offsets. Более плотный graph может появиться, но правильность и retrieval gain надо измерять. [Pinned operate.py](https://github.com/HKUDS/LightRAG/blob/453dce83d6d0354a06e46c8d4029a0895c4e054b/lightrag/operate.py).

CPU/ingestion: initial extract на chunk, optional gleaning (обычно до одного дополнительного вызова), summaries при merge hubs, embeddings и storage IO. На 136 chunks исходного snapshot при одинаковых boundaries это порядка 136 initial calls плюс до 136 gleaning calls и variable summaries; это плановая оценка числа вызовов, не измеренный runtime. Новая модель не обязательна, но extraction/summary callbacks нужны: production adapter сейчас блокирует все LLM generation calls.

Quality/provenance: native chunk attribution пригодна как retrieval hint при PG evidence re-resolution, слабее GraphFact claim proof. Interpretability хороша для topics, хуже для exact conditions/polarity. False name merges library не закрывает calibration gate. На 1k допустим isolated pilot с серверными либо проверенными experimental stores; на 10k нужны throughput, hub-summary cost и recovery measurements; на 100k default file-backed storage нельзя считать заранее подходящим production backend. Cross-store transaction отсутствует, version/revision deletion и source tracking требуют проверки.

Reuse: pinned dependency, source exports, current models/vectors по experimental bridge, PG resolver. Переделывать production adapter в native ingestion сейчас не требуется; отдельный runtime лучше отделяет extraction от context-only adapter. Для диплома годится как экспериментальная comparison arm, слабее как обоснованный drop-in authoritative KG. Все десять code/API вопросов и ARCH-001 caveats разобраны в [lightrag_review.md](lightrag_review.md).

## 4. Hybrid raw + concepts + LightRAG retrieval

PostgreSQL остаётся source of truth; raw Neo4j graph — evidence claims; typed concept projection — explicit topics/roles; LightRAG — optional additional retrieval. Все channels возвращают candidates с PG IDs и resolvable provenance, dedup/rerank под единым evidence budget. Объединение rank scores не должно считать повтор одного документа в трёх channels тремя независимыми подтверждениями.

Quality потенциально выше по recall, но нужен ablation: vectors, vectors+typed, vectors+LightRAG, все channels. Это самая сложная архитектура: additional calls, projections, failure modes, revision sync и evaluation. Provenance остаётся высокой только если donor descriptions не попадают в authoritative answer как первичный источник. False merge риск typed/native слоёв не исчезает от слова hybrid.

Reuse почти всего baseline плюс результаты 2B/3; удалять current stores не надо. Переработать потребуется orchestration/evidence budget и проекционные lifecycle contracts. Новая модель не обязательна; суммарные LLM/CPU расходы выше. На 1k осуществимо при ограниченных channels; на 10k/100k нужны независимые queues/storage/recovery и стоимость каждой arm. Для диплома слишком широк для первого шага: он затрудняет причинную оценку, какой именно channel помог. Рассматривать после подтверждённой marginal usefulness каждого слоя.

## 5. Metadata citation/taxonomy layer над sparse KG

В frozen normalized metadata уже есть 406 directed ссылок между corpus documents; после исключения трёх self-links 99 документов связаны в одной undirected citation component. Это локально проверенные metadata, а не новые запросы OpenAlex. CITES можно позже проектировать отдельно с указанием source metadata и direction. Цитирование не означает одинаковый признак, поддержку утверждения, отсутствие критики или прямую технологическую совместимость.

Topic classification/hierarchy — navigation и candidate blocking; manual primary clusters из этого аудита не следует превращать в уникальную ontology truth. Existing OpenAlex topics можно использовать как source-reported labels, явно отличая их от собственных классификаций. Candidate expansion по citation/topic ограничивать hops/fanout и rerank, не считать connectedness evidence качества.

Quality: ожидается дешёвое расширение релевантных документов, но retrieval lift пока не измерен; технические comparison dimensions и omission recovery не решает. CPU/ingestion низкие: metadata processing, LLM не обязателен. Provenance прозрачна на уровне metadata. Interpretability высокая как navigation, false alias merges не нужны. На 1k/10k/100k стоимость зависит от числа references и fanout, при индексировании/ограниченном expansion линейная projection реалистичнее all-pairs semantic merging. Популярные обзоры создадут hubs; требуются limits.

Reuse: PostgreSQL metadata, existing ontology enums CITES/Classification/Technology, Neo4j/Qdrant/evidence pipeline. Новые source downloads/индексы/модели для разработки гипотезы не нужны; никаких новых graph edges сейчас не записано. Это сильный low-cost control для диплома и рациональный промежуточный шаг, хотя само по себе не устраняет ontology/extraction bottleneck.

## Рекомендация и минимальный следующий эксперимент

Рекомендую **вариант 2A + обязательный 2B в исследовательском pilot**, сохраняя вариант 1 baseline и добавляя вариант 5 как дешёвый отдельный control. Вариант 4 оставить последующим направлением; вариант 3 проверить независимо, не принимать как готовое решение. Одна только normalization существующих labels для этого corpus недостаточна.

Минимальный pilot — 24 frozen документа: D003, D004, D007, D013, D014, D015, D019, D023, D024, D039, D041, D043, D046, D048, D057, D059, D060, D064, D067, D068, D078, D084, D092, D100. Включены все 11 zero-fact документов, близкие пары, reviews, конкретные эксперименты, DFT и периферийная membrane study. Это fixed purposive diagnostic set, не representative evaluation corpus. Документальные IDs есть в topic_clusters.csv. После pilot перейти на те же 100 только при заранее согласованных quality/cost gates.

До любого replay два независимых предметных рецензента уточняют rubric: MENTIONS versus paper-specific disclosure; modeled/reviewed/proposed/measured; материал versus свойство; qualifier/condition/polarity; SAME versus broader/related. Использовать отдельный held-out subset для итоговых acceptance, не выбирать threshold на том же gold.

1. A0: existing raw + vectors; A5: A0 + metadata expansion; A2A: A0 + typed mapping existing facts; A2B: A2A + source-grounded mentions. Native LightRAG arm добавить после первичной оценки, либо отдельно как comparison на тех же frozen chunks.
2. Replay текущего extractor на D007/D064/D092 и policy-controls в disposable environment с raw outputs, per-candidate reject reasons, token/truncation traces. Только так различить empty model answer и validator rejection. Production ничего не переизвлекает.
3. На source gold оценивать mention/role support, exact span resolution, zero-fact recovery, false aliases/type/polarity mistakes; отдельно existing raw-claim precision. На фиксированных query tasks измерять Recall@10, nDCG@10, relevant evidence per token budget, grounded answer support и latency/CPU/RAM/LLM calls. Numeric claims без analyte/concentration/condition не считать правильным comparison.
4. Require 100% resolvable PG provenance у используемых evidence. Для automatic strict SAME — независимый precision gate >=0.95 с confidence interval и достаточной выборкой; до него abstain/curated aliases. Одна положительная точечная оценка на малой выборке недостаточна. RELATED/BROADER edges оценивать отдельно.
5. Продолжать только если recall/evidence usefulness растёт при сохранении source support, qualifiers и приемлемой цене. Density — diagnostic output, не gate.

Не следует: снижать Tev1 threshold в production; сливать RELATED/BROADER как SAME; заменять raw facts descriptions из LightRAG; утверждать loss/truncation всех zero docs по одному count; объединять разные analytes/polarity для плотности; запускать 100/1k/10k backfill без pilot и CPU measurements; удалять baseline, менять pinned dependency или скачивать модели в рамках этого аудита. Ни один предложенный эксперимент сейчас не запущен.
