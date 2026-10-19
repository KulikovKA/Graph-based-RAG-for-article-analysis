# Теоретическая производительность и ресурсные риски

Новых замеров не проводилось. Среда задана пользователем: Ryzen 7 8845HS, 32 GB RAM, Windows + WSL2, без дискретной GPU. Производительность A–F, peak RAM, energy и скорость ONNX kernels — `NOT_MEASURED`.

## 1. Что уже измерено исторически

[HYBRID-001/performance.json](../../validation/HYBRID-001/performance.json), run `d895217d-ebbe-4117-9066-8ae0ebcd0bdc`:

| Показатель | Сохранённое значение | Интерпретация |
|---|---:|---|
| LLM calls | 138 | Historical full Hybrid run, не новая оценка B |
| Semantic extraction total | 12601.2067 s | Сумма времени extraction по артефакту; не process CPU-seconds |
| Total runtime | 12988.994 s / 3.608 h | Wall time whole run |
| Median / p95 document seconds | 102.806 / 238.872 | Для тогдашнего corpus/config |
| Persisted/projected mentions | 747 | Не число semantic correct relations |
| PostgreSQL persistence time | null → `NOT_MEASURED` | Нельзя вычесть из total с точностью |
| Neo4j projection time | null → `NOT_MEASURED` | Нельзя объявить ingestion overhead нулевым |
| Peak process RSS | null → `NOT_MEASURED` | Размер файла модели не заменяет RAM |

Отношение 12601.2067/12988.994 ≈ 97.0% показывает, что сохранённый extraction timer занимал основную часть wall budget. Это арифметика по старому отчёту, **не** профилирование CPU и не доказательство того, что encoder даст 97% экономии. Новый v1.4 replay имеет другой состав (27 selected zeros), поэтому его нельзя напрямую сравнивать с этим full-corpus run.

## 2. Обозначения и стоимость

- `N` — число документов; `C` — число extraction windows/chunks; `L_i` — input tokens окна; `O_i` — output tokens генерации.
- `m_i` — entity mentions в окне; `P` — candidate directed pairs; `R` — candidate assertions; `M` — глобальное число mentions/concepts для linking; `k` — bounded shortlist.
- `E(L,b)` — время encoder batch, включая tokenizer и transfers; `G(L,O)` — generative call, включая prefill/decode; `S` — summary calls; `r` — retries; `a` — routed fraction.
- Реальные функции `E/G`, число candidate pairs и `a` пока `NOT_MEASURED`.

Для serial local inference:

`T_total = T_read + T_preprocess + T_load/switch + ΣT_model + T_validate/link + T_persist + T_project`.

Wall time и CPU-time различаются: parallel threads могут уменьшить wall time без уменьшения суммы CPU-seconds. Для CPU efficiency сообщать обе величины; при concurrent processes учитывать весь pipeline, а не только Python controller.

### Generative extraction

`T_gen = Σ [T_load_i + T_prefill(L_i) + Σ_{j=1..O_i} T_decode(L_i+j)]`.

Autoregressive output выполняется последовательно по токенам. Короткий structured result уменьшает `O`, но prompt candidate inventory увеличивает `L`; экономия появляется только если уменьшение decode/retry больше дополнительного prefill/tokenization. Удаление повторяющихся quote/UUID/offsets обоснованно как гипотеза, а не гарантированный speedup.

Для обычного dense attention prefill имеет квадратичный по длине attention term, encoder layer примерно `O(L·h² + L²·h)`. ModernBERT и hybrid/state-space generative architectures могут иметь другой attention pattern. **Эту формулу нельзя выдавать за точную cost model Qwen3.5**; backend profiling и действительный layout неизвестны. Расширение 4096→8192 не обязано ровно удваивать latency/RAM и не обязано улучшать extraction.

### NER и pairs

BIO/BILOU head линейный по tokens после encoding. Span head с max width `w` рассматривает до `O(Lw)` spans, полный span enumeration — `O(L²)`.

Без ограничений directed entity pairs в окне: `m_i(m_i−1)`, `P = Σ m_i(m_i−1)`. Для 12 entities это 132 пары, для 40 — 1560: **арифметические примеры**, не замер corpus. При explicit type/distance/top-k policy `P ≤ Σ m_i k`, но candidate recall может снизиться. Построение shortlist через exact all-pairs similarities всё ещё `O(M²)`; наличие top-k на выходе само по себе не уменьшает вычисление.

Pair cross-encoder стоит примерно `Σ_{p=1..P} E(L_p,1)` без batching; shared span encoder — `Σ E(L_i,b) + O(P·d)` для simple pair head. Batching уменьшает overhead и улучшает vectorization, но не делает `P` линейным автоматически. Dense labels по `q` relation types могут добавить factor `q`; NLI verbalization каждого label — `P·q` pair evaluations, в отличие от одного multiclass head.

### Linking, validation и graph writes

Dictionary/hash grouping ожидаемо `O(M)` при среднем O(1) hash lookup; sorting-based canonical groups — `O(M log M)`. Embedding ANN lookup practical sublinear average зависит от индекса; worst-case гарантии не обещаем. Для `M·k` pair checks отдельно считать retrieve recall и resolution cost.

Semantic NLI: примерно один premise/hypothesis на assertion; при декомпозиции n-ary claim может потребоваться несколько, но успешная проверка каждого fragment отдельно **не доказывает их правильное совместное attachment**. Span/chemical/units gates дешёвы и должны идти до дорогого NLI.

Persistence/projection: `O(V+E)` logical rows плюс индексы, network batches и transaction costs; фактическая сложность backend не сводится к этой оценке. Полный donor graph + PG authoritative + Neo4j projection увеличивают copies и recovery cost. При incremental updates стоимость зависит от изменённых chunks и связанных canonical clusters, а не только от новых документов.

## 3. Матрица затрат архитектур

Все формулы — structural estimates, не прогнозы секунд.

| Вариант | Generative calls | Encoder workload | Память/overhead | Главный bottleneck |
|---|---|---|---|---|
| A | `C + Glean + S + r`, где `0≤Glean≤C` в исследованном pin | Optional embeddings; NLI только выделенный A+ arm | Qwen + donor graph/KV/VDB + provenance sidecar | Output, summaries на hubs, export mapping |
| B | Обычно `C_B + r`, без summaries | `R` NLI; optional identity pairs | Qwen + один verifier; window batching ограничен | Decode остаётся, короткий output может сократить его |
| C | 0 | NER windows + `P` RE + `R` NLI + `M·k` linking | Несколько encoder sessions или sequential residency | Pair explosion, repeated context encoding |
| D | `a·C_D + r` для window routing; при pair routing другая единица счёта | Cheap branch C + verifier + routing | Encoders + Qwen residency/switching | Routed fraction и loading overhead |
| E1 | Как A, даже с validation hook | NER/RE/NLI поверх генерации | Наиболее много дублируемых компонентов | Double processing и summaries |
| E2 | 0 extraction; возможные `S` отдельно | Как C/F | External extractor + donor projection | Storage integration, не доказанная экономия IE |
| F | 0 | Shared encoding + pair head + optional NLI | Span/pair tensors, один основной encoder | Label count, span width, scope attachment |

При общем corpus 136 исходных chunks и без re-chunking native pin предполагает 136 initial extraction calls, до 136 gleaning calls, **плюс** summaries/retries. Это верхняя граница gleaning при данных предпосылках, не наблюдение и не полный call budget. Число summary calls заранее `UNKNOWN`.

## 4. Когда selective cascade действительно дешевле

Пусть direct B на окно стоит `g`, cheap branch D — `c`, ambiguous Qwen call — `g_a`, additional validation/switch overhead — `v+s`. Тогда:

`T_D/C ≈ c + a·g_a + v + s`, `T_B/C ≈ g + v_B`.

Условие выигрыша: `a < (g + v_B − c − v − s)/g_a`, если правая часть положительна. Если threshold для high precision отправляет почти всё в Qwen, D может оказаться медленнее B. Если cheap NER пропускает сущности, низкое `a` может быть признаком низкого recall, а не эффективности.

Практика будущего сравнения: сначала снять distribution `a` на calibration, затем выбрать fixed routing policy. Qwen calls группировать по ambiguity type и длине, чтобы amortize loading, но не объединять unrelated documents в один evidence scope. Считать time-to-index и queue delays отдельно. Проверять high-confidence false acceptance и missed ambiguity; routing quality — самостоятельная метрика.

## 5. RAM и quantization

`RAM_peak ≈ Σresident weights + activations/workspaces + tokenizer/runtime + attention/state cache + graph/vector indexes + storage services + OS/WSL overhead`.

Пример arithmetic lower bounds: Qwen 4B при идеальных 4 bits/parameter ≈2.0 GB weights; фактический Q4_K_M смешанный format и служебные данные дают другое число, а runtime RAM выше. Это **не** оценка exact file size текущего digest. MiniLM 82.1M FP32 ≈0.328 GB, DeBERTa 184.4M ≈0.738 GB, ModernBERT 149.6M ≈0.598 GB — только tensors, см. [model matrix](SMALL_CLASSIFIERS_REVIEW.md).

Для attention-only layers cache обычно растёт с sequence length, layers, KV heads и dtype; для hybrid models дополнительно есть recurrent/state buffers. Не использовать generic dense-transformer KV формулу как measured Qwen memory. Batch size и max length дают отдельные пики; несколько ONNX sessions могут держать свои arenas и преобразованные copies weights.

На 32 GB логично сначала проектировать последовательную загрузку одного generative и одного encoder stage либо ограниченную совместную residency. Это resource policy для pilot, не требование менять нынешний runtime. WSL memory, Docker services, host shared file mappings и swap измерять вместе; складывание RSS всех процессов может двойным счётом учитывать shared pages. Сообщать per-process RSS/peak и host/container aggregate с указанием метода.

INT8: начать с официальных ONNX MiniLM AVX2 и ModernBERT artifacts; ISA dispatch проверить на фактическом backend. Наличие аппаратных инструкций не гарантирует ускорение. FP16 на CPU не считать автоматически быстрее FP32. Для custom GLiNER/Relex/SpanMarker exporters отсутствие ошибки конвертации ещё не доказывает совпадение spans/labels: нужна будущая numeric/output parity и quality evaluation. Никакие экспорты в этой работе не выполнялись. [ORT documentation](https://onnxruntime.ai/docs/performance/model-optimizations/quantization.html).

## 6. Оптимизации и цена качества

| Изменение | Механизм экономии | Риск | Как отделить эффект |
|---|---|---|---|
| Span IDs вместо repeated JSON quotes | Меньше generated tokens и offset ошибок | Candidate inventory длиннее; missing spans | Same Qwen/windows, менять только output contract; сравнить tokens и recall |
| Deterministic offsets | Удалить model arithmetic и repairs | Повторные occurrences, sanitizer drift | Exact occurrence gold, отдельная error taxonomy |
| Sentence-level extraction | Короткий контекст, меньше pairs | Coreference и условия за границей | Same source corpus; отдельный cross-sentence slice |
| Context-aware/dynamic windows | Расширять только для antecedent/condition | Другая coverage и больше passes | Base frozen chunks unchanged; window mapping сохраняется |
| Batching encoders | Amortize tokenizer/session overhead | Padding и peak RAM | Length buckets, fixed total candidate set |
| Domain dictionaries | Zero neural calls для точных anchors | Alias polysemy, dictionary coverage ceiling | Report dictionary precision/coverage отдельно |
| Pair pruning | Сократить `P` | Скрытый recall ceiling | Gold candidate recall до classifier |
| Selective Qwen | Нет decoding для простых cases | Уверенные ошибки, высокий `a` | Risk–coverage и routed/accepted error strata |
| Отключить лишние summaries | Убрать `S` | Donor retrieval descriptions меняются | Для graph extraction оценивать claim records; downstream отдельной ablation |
| Incremental build | Переиспользовать unchanged chunks | Stale alias/qualifier decisions | Versioned dependency invalidation, snapshot identity |
| Smaller context | Меньше prefill/cache | Недостаточное evidence | Context budget одинаково контролируется во всех generative arms |

Для основной extractor comparison сначала держать исходные chunks и доступный контекст одинаковыми. Dynamic chunking — последующая ablation; иначе нельзя отнести выигрыш classifier architecture или большему evidence window.

## 7. Будущий measurement contract

После разрешения измерять: source documents/chars/tokens, windows, raw/accepted/rejected entities/claims, `P`, `R`, model passes, cold/warm loads, input/output tokens, retries, summary tokens, per-stage wall and process CPU time, peak RAM, swap, storage write duration, failures и unchanged-chunk cache reuse.

Cold uncached extraction, warm model uncached extraction и extraction-cache replay — **три разных режима**. Время annotation, training, index build и online analysis не смешивать. Три повтора на одинаковом input — первоначальный план для shortlisted performance arms, с order randomization и фиксированным thread budget; расширять повторы только при нестабильности. p95 на малом N сопровождать размером выборки.

GPU later: заменить execution provider/backend, сохранить weights identity или явно выделить dtype/quantization arm, DTO, ontology, gold, deterministic gates и source mapping. GPU throughput считать отдельно от CPU; ускорение не требует менять смысл графа. Transfer/batching может изменить numerical thresholds — повторная calibration/parity необходима.
