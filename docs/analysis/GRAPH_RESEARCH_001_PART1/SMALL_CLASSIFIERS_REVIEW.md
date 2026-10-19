# Малые NER, RE, NLI и linking модели

Проверка model cards и metadata API: 2026-10-19. Веса не загружались, inference/export/quantization не выполнялись. На нашем corpus для всех новых моделей precision, recall, latency, peak RAM — **`NOT_MEASURED`**. Ни размер модели, ни наличие ONNX файла не доказывают end-to-end преимущество.

## 1. Конкретные checkpoints

`FP32 / INT8` ниже — арифметический объём **только параметров** в decimal GB (`4P / P` bytes), а не требуемая RAM. INT8 число предполагает идеальную квантизацию всех weights, без scales и FP32 остатков; наличие рабочего INT8 runtime подтверждается отдельно. Лицензия библиотеки и лицензия checkpoint не взаимозаменяемы.

| Checkpoint и первичный источник | Реальная задача и domain | Parameters / weights FP32; INT8 | Лицензия, язык | Обучение и CPU/ONNX |
|---|---|---|---|---|
| [urchade/gliner_small-v2.1](https://huggingface.co/urchade/gliner_small-v2.1) | Готовый label-conditioned NER, generic synthetic training | 166M по card; ≈0.664 / 0.166 GB | Apache-2.0; EN | Zero-shot labels возможны. CPU PyTorch; framework export path, но в проверенном repo ONNX нет; конкретный export `UNKNOWN` |
| [urchade/gliner_medium-v2.1](https://huggingface.co/urchade/gliner_medium-v2.1) | Более ёмкий generic NER; не scientific specialist | Card family table 209M, API safetensors 195,175,936; для bounds ≈0.781 / 0.195 GB по API | Apache-2.0; EN | Сравнить small/medium при одинаковых labels. Разницу card/API не скрывать. CPU/export как выше |
| [allenai/scibert_scivocab_uncased](https://huggingface.co/allenai/scibert_scivocab_uncased) | Scientific **base encoder**, не готовая NER/RE голова | ≈110M BERT-base; ≈0.44 / 0.11 GB, точный tensor count `UNKNOWN` | Upstream [Apache-2.0](https://github.com/allenai/scibert); HF license field пуст; EN science | Требует head и fine-tuning. BERT ONNX путь возможен, task export не проверен |
| [m3rg-iitd/matscibert](https://huggingface.co/m3rg-iitd/matscibert) | Materials **fill-mask base**, domain initialization | 109,951,602; ≈0.440 / 0.110 GB | MIT; EN | Для нашей NER/RE нужен supervised head. Не называть этот ID готовой моделью scientific NER |
| [pranav-s/MaterialsBERT](https://huggingface.co/pranav-s/MaterialsBERT) | Materials base encoder | Exact count `UNKNOWN`; BERT-scale estimate только после config verification | HF `other`; custom GTRC terms; EN | Не NER. Сначала проверить условия [лицензии](https://github.com/Ramprasad-Group/polymer_information_extraction/blob/main/LICENSE) |
| [pranav-s/PolymerNER](https://huggingface.co/pranav-s/PolymerNER) | **Готовый polymer NER** с material/property-oriented labels | Exact count/RAM `UNKNOWN` | `other`, custom terms; EN polymers | Полезный domain comparator; chemical sensor ontology не совпадает. ONNX export `UNKNOWN` |
| [tomaarsen/span-marker-bert-base-fewnerd-fine-super](https://huggingface.co/tomaarsen/span-marker-bert-base-fewnerd-fine-super) | Готовый SpanMarker NER, Few-NERD | 108,415,299; ≈0.434 / 0.108 GB | **CC BY-SA 4.0** weights; EN | CPU применим; не scientific checkpoint. Fine-tune labels; custom span machinery/export `UNKNOWN` |
| [answerdotai/ModernBERT-base](https://huggingface.co/answerdotai/ModernBERT-base) | Masked-LM **base**, не NER | 149,655,232; ≈0.599 / 0.150 GB | Apache-2.0; EN | Есть ONNX artifacts base модели; они не содержат обученную scientific NER head. CPU execution provider и export новой head проверять отдельно |
| [jackboyla/glirel-large-v0](https://huggingface.co/jackboyla/glirel-large-v0) | Zero-shot relations по supplied entities | Exact API tensor count `UNKNOWN`; DeBERTa-large-scale family, не «маленький 20M» | **CC BY-NC-SA 4.0 в README**, metadata field пуст; преимущественно EN | Готовый RE comparator; NO_RELATION/threshold policy адаптировать. CPU feasible по архитектуре; cost/export `NOT_MEASURED`/`UNKNOWN` |
| [knowledgator/gliner-relex-base-v1.0](https://huggingface.co/knowledgator/gliner-relex-base-v1.0) | Готовый joint NER+RE | 225,086,211; ≈0.900 / 0.225 GB | Apache-2.0; language metadata отсутствует — multilingual claim для base `UNKNOWN` | Zero-shot typed labels; task training optional для pilot. Exact CPU ONNX export `UNKNOWN` |
| [knowledgator/gliner-relex-multi-v1.0](https://huggingface.co/knowledgator/gliner-relex-multi-v1.0) | Joint multilingual NER+RE | 318,859,779; ≈1.275 / 0.319 GB | Apache-2.0; multilingual по card | Кандидат для языкового расширения; русский technical score `NOT_MEASURED`. ONNX artifacts не обнаружены |
| [fastino/gliner2-base-v1](https://huggingface.co/fastino/gliner2-base-v1) | Schema IE: NER/classification/structured fields, relation support заявлен card | 208,476,821 API; card округляет до 205M; ≈0.834 / 0.208 GB | Apache-2.0; EN | CPU-oriented implementation, один shared encoder. Заявленные автором speedups не переносим. ONNX конкретного checkpoint `UNKNOWN` |
| [cross-encoder/nli-MiniLM2-L6-H768](https://huggingface.co/cross-encoder/nli-MiniLM2-L6-H768) | Готовый 3-way NLI; SNLI/MultiNLI, **не** chemical RE | 82,121,221; ≈0.328 / 0.082 GB | Apache-2.0; EN | В repo есть ONNX, AVX2/AVX512 INT8 варианты. Хороший CPU screening candidate; label ordering читать из config, domain calibration обязательна |
| [MoritzLaurer/DeBERTa-v3-base-mnli-fever-anli](https://huggingface.co/MoritzLaurer/DeBERTa-v3-base-mnli-fever-anli) | 3-way NLI: entailment, neutral, contradiction | **184,424,963 total**, ≈0.738 / 0.184 GB; не путать 86M backbone с total включая embeddings | MIT; EN | Готовый validator comparator; CPU PyTorch, ONNX файл в repo не обнаружен, export verification нужен |
| [MoritzLaurer/ModernBERT-base-zeroshot-v2.0](https://huggingface.co/MoritzLaurer/ModernBERT-base-zeroshot-v2.0) | **2-way** entailment / not_entailment | 149,606,402; ≈0.598 / 0.150 GB | Apache-2.0; основной training context EN, metadata language пуст | Есть ONNX int8/uint8/FP16 artifacts. Не может отдельным label вернуть contradiction против neutral; это verifier поддержки, не полный NLI triage |
| [cambridgeltl/SapBERT-from-PubMedBERT-fulltext](https://huggingface.co/cambridgeltl/SapBERT-from-PubMedBERT-fulltext) | Biomedical synonym embeddings для dictionary linking | 109,482,752; ≈0.438 / 0.109 GB | Apache-2.0; EN/UMLS | Пример linking training, не готовый chemical/device SAME judge. Corpus-specific dictionary и candidate validation нужны |

Универсального компактного fine-tuned checkpoint для всех типов `MATERIAL/DEVICE/PROCESS/ANALYTE/PROPERTY/OPERATING_CONDITION/MECHANISM` и технических `DETECTS/OPERATES_AT` данное исследование не подтвердило: **`UNKNOWN`**, а не «моделей не существует». Есть готовые generic zero-shot модели и специализированные модели соседних доменов.

### Проверенные revisions для воспроизводимого pilot

Метаданные получены через `https://huggingface.co/api/models/<id>` без скачивания файлов weights. Перед будущим запуском сохранить также tokenizer/config/weights hashes и license text конкретного SHA.

| ID (сокращение из таблицы) | Наблюдавшийся repo SHA |
|---|---|
| gliner_small-v2.1 | `4e091416cf7c3481db542c2a3d26156916f3a47f` |
| gliner_medium-v2.1 | `40ec419335d09393f298636f471328b722c6da9e` |
| scibert_scivocab_uncased | `24f92d32b1bfb0bcaf9ab193ff3ad01e87732fc1` |
| matscibert | `ced9d8f5f208712c4a90f98a246fe32155b29995` |
| MaterialsBERT | `8a7378e9cdeae17fb808482ae367e4bd995fe223` |
| PolymerNER | `4f7bb8bd55724ec523e22d6c9793b59ab7e299d0` |
| span-marker-bert-base-fewnerd-fine-super | `2e7094f235dca14bdc77d682442fc3889a041898` |
| ModernBERT-base | `8949b909ec900327062f0ebf497f51aef5e6f0c8` |
| glirel-large-v0 | `40a523e12a8432d6da364cf2a195a28755ff04d3` |
| gliner-relex-base-v1.0 | `e6a880049a19c5cc222a7a479c32e84b0d8cdd9a` |
| gliner-relex-multi-v1.0 | `e990d9ba6f471b846f7d78bf7e4b4dab11761ada` |
| gliner2-base-v1 | `f9634218e53580c56edf0de97ca1a7d3f1c2354e` |
| nli-MiniLM2-L6-H768 | `b95119ce93d3e065de6214e38cd4a97b0f2f2c6d` |
| DeBERTa-v3-base-mnli-fever-anli | `6f5cf0a2b59cabb106aca4c287eed12e357e90eb` |
| ModernBERT-base-zeroshot-v2.0 | `d421c4545a438fd006fb43f8b981c5d908faa1e1` |
| SapBERT-from-PubMedBERT-fulltext | `090663c3ae57bf35ffe4d0d468a2a88d03051a4d` |

## 2. NER и typing: какая задача у модели

**BIO/BILOU token classification:** линейное число token labels, удобный CPU baseline. Проблемы — subword alignment, nested entities, discontinuous spans и длинные compound names. Нельзя автоматически отбрасывать nested `graphene` внутри `graphene sensor`: это может быть material mention и device mention с разными spans.

**Span classification:** оцениваются contiguous spans до width `w`, примерно `O(nw)` кандидатов. SpanMarker и GLiNER поддерживают другой inductive bias, чем BIO; `w` и max entities — параметры recall. Разные label descriptions и max length должны фиксироваться вместе с weights.

**Scientific encoders:** SciBERT/MatSciBERT имеют доменный pretraining, но нулевое task training не делает их NER. Их следует сравнить как initialization одного и того же NER/RE head на одном gold, не против fully trained GLiNER под названием «pretrained NER».

**Отдельный type classifier** имеет смысл при хорошем span recall и неоднозначных ролях: `NH3` как analyte в sensing, reagent в synthesis, adsorbate в simulation. Предпочтительно хранить stable entity kind `CHEMICAL` и contextual role на mention/claim. Адаптер существующего `ANALYTE` должен отражать роль, а не считать вещество разными химическими identities. Сначала измерить ошибки typing: отдельная модель удваивает overhead без гарантии выигрыша. Context-aware head или совместный label-conditioned NER могут оказаться достаточными.

Обучать type classifier на cropped mention без предложения нельзя для role disambiguation. Вход: marked span + sentence и при необходимости соседнее предложение; prediction включает `UNKNOWN/ABSTAIN`. Scope source section (experimental/background/claim) — отдельный feature, не доказательство роли.

## 3. Relation extraction и negative labels

Для C предлагается sentence-level marked-pair classifier на SciBERT/MatSciBERT как supervised endpoint; zero-shot pilot допускает GLiREL или label-conditioned NLI, но это отдельные arms. Вход должен содержать оба отмеченных spans, направление и контекст; выход — controlled relation либо `NO_RELATION/ABSTAIN`. Directional `USED_IN` и `DETECTS` не симметричны.

Candidate generation: compatible type/role pairs, same clause/sentence, затем ограниченный cross-sentence/coreference fallback. Нельзя жёстко удалять все дальние пары и объявлять высокую precision без подсчёта потерянных gold relations. Сначала measure candidate recall, потом classifier recall conditional on candidates, затем end-to-end recall.

**PURE-style pair model** делает проход на пару (с возможной approximate batching); **SpERT/Relex-style** reuse одного encoding и лёгкий pair head. Это разная стоимость. GLiREL умеет unseen relation labels, но не превращает scores в доказательство relation support. Число labels, число entity pairs и длина окна входят в compute budget.

Негативные примеры: same sentence без связи; reversed endpoints; wrong analyte; rejected technique; property другого device; correct relation при другом temperature; `RELATED` вместо `SAME`. Не использовать только случайные далёкие пары: на них модель учится слишком простой задаче. Многозначные pairs допускают multi-label RE; не заставлять одно отношение вытеснять другое валидное.

## 4. NLI: verifier, а не источник истины

Предлагаемый вход: premise = минимальное достаточное source evidence, hypothesis = deterministic verbalization **всего** claim (endpoints, predicate, value, unit, polarity, conditions, modality). Например, проверка «sensor detects NH3 at 25 °C» по тексту «sensor detects NH3 at 200 °C» должна отвергать именно qualified claim.

MiniLM — первый дешёвый screening, DeBERTa-base — более ёмкий comparator; ModernBERT binary verifier — отдельный speed/quality arm. Для отсутствующего evidence `neutral/not_entailment` означает недостаточную поддержку, а не ложность физического утверждения. Нельзя превращать любой non-entailment в negative relation.

Риски generic NLI: lexical overlap (`NO2`/`NH3`), числа/единицы, отрицательный scope, отношения между компонентами, условные statements, cross-sentence antecedent. Deterministic chemical/value/unit checks дополняют NLI; они не заменяют смысловое сравнение. Коррелированные ошибки extractor и verifier сохраняются, даже если models разные. Нужен human reference, а не второй model vote.

## 5. Linking без больших LLM

1. Exact surface + safe Unicode identity normalization; source text неизменен. Химические case, заряд и числа сохраняются domain-specific parser-ом.
2. Dictionary lookup и локально доказанные abbreviations; версия словаря и scope в decision trace.
3. Candidate retrieval по blocking keys / embeddings; top-k только формирует shortlist.
4. Compact context-pair classifier: `SAME`, `RELATED`, `BROADER`, `NARROWER`, `DIFFERENT`, `ABSTAIN`.
5. Threshold calibration и cluster consistency: нельзя автоматически делать transitive union всех accepted pairs, если A–C содержит cannot-link. Допустимы conservative representative/complete-link checks и отдельные unresolved aliases.

`graphene` vs `graphene oxide`, `NO2` vs `NH3`, `sensor` vs `gas sensor`, material vs device — hard negatives. Identity понятия не требует одинаковых experimental conditions; **identity claims** требует их сохранения. Не следует дробить один chemical concept по температуре или сливать разные experiment claims через общий chemical node.

SapBERT демонстрирует возможность научить embedding synonyms, но UMLS coverage не соответствует engineering. Existing qwen3-embedding:0.6b можно оставить только candidate retriever для честного базового сравнения; дополнительный linking encoder добавлять после ablation.

## 6. Qualifiers и negation

Детерминированно извлекать numeric spans, знаки сравнения, диапазоны, temperature scales, concentrations, единицы и exact evidence. Unit normalization хранит и исходное значение, и преобразованное; `room temperature` не превращать автоматически в 25 °C. `% response` не равен ppm; missing condition — `UNKNOWN`, не отсутствие условия.

Scope отрицания и modality сначала rules/dependency cues: `not`, `without`, `failed to`, `may`, `suggest`, `compared with`; pseudo-negation `not only` — отдельный случай. NegBio/scispaCy полезны как method references, но их biomedical rules не считаются валидированными для патентов. Устройства, использованные/предложенные/отвергнутые/упомянутые в related work, должны иметь разные status labels. Условия привязываются к assertion, а не ко всем соседним entities.

## 7. Исполнитель по задаче: алгоритм, encoder, Qwen, комбинация

| Задача | Предпочтительный первый механизм | Training / zero-shot | Проходы и batching | Semantic risk / будущая проверка |
|---|---|---|---|---|
| Source identity/hash/offsets | Детерминированный | Не нужен | Один линейный проход | Unicode/normalization mapping; exact span gold |
| Sentence/claim boundaries | Rules + parser | Parser pretrained, domain tuning возможно | Batch по документам | Длинные claims и сокращения; boundary error audit |
| Entities/spans | GLiNER small, словарь; сравнить domain NER | Zero-shot pilot, fine-tune после ошибок | 1 encoding/window, bounded spans | Оmission/nesting; entity PRF по domain strata |
| Entity kind/role | Joint head или compact marked-span classifier | Для target role надёжного ready checkpoint нет | Один batch spans; shared encoding предпочтителен | Role vs intrinsic type; confusion matrix |
| Relations | Rules для строгих patterns + pair/span classifier | GLiREL/Relex zero-shot; SciBERT head supervised | `P` pair evaluations либо shared encoder | Co-occurrence, direction, negation; relation PRF и candidate recall |
| Canonical identity | Dictionary + context pair classifier | Rules без training; learned stage требует gold | `M·k` candidates, batching | False merges, cluster closure; separate SAME precision |
| Unit/range values | Rules / domain parsers | Не нужен | Линейно по тексту | Value attachment остаётся semantic task |
| Negation/modality | Scope rules → classifier при неоднозначности | Domain gold желателен | Window batch | Missing cue, scope leakage; polarity PRF |
| Semantic support | MiniLM/DeBERTa NLI + hard constraints | Готовая NLI, domain calibration нужна | Один pair на claim; составные claims могут требовать несколько | Chemical/numeric entailment; human support labels |
| Ambiguous coreference/role/relation | Selective та же Qwen3.5 4B | Prompt-based, без обязательного fine-tuning | Один короткий structured call на группу ambiguity, не на каждый token | Hallucination; вернуть только span IDs/closed labels, повторно validate |

Это **гипотеза распределения работы**. В CPU comparison считать все auxiliary models, serialization, tokenizer time, repeated passes и loading. Encoder pipeline может быть медленнее при quadratic pairs; маленькая отдельная модель плоха, когда решает редко встречающуюся задачу, требует слабого gold, повторяет уже имеющееся encoding или добавляет больше ошибок interface, чем исправляет.

## 8. Calibration и объём разметки

Протокол: split по документам/семействам до настройки; train heads на train; fit temperature/Platt на calibration; thresholds по relation type — на calibration; holdout использовать один раз. Reliability curves, Brier/NLL, precision–coverage и risk–coverage публиковать вместе. Isotonic regression требует больше данных и может переобучиться на малой выборке; temperature scaling проще, но не исправляет ranking. Model-generated confidence Qwen не эквивалентен logit probability.

**Плановые объёмы, не доказанная достаточность:** pilot 20–24 документов с exhaustive spans/relations; 300–500 candidate relation judgments и 150–300 identity pairs как начальный error screen, с добавлением редких классов. Для supervised RE/NER начать с 1000–3000 размеченных предложений только если pilot показывает необходимость обучения; строить learning curves 25/50/100% training, а не обещать конкретный score от этого размера.

Для precision 0.95 недостаточно 10 безошибочных решений. При iid Bernoulli и **заранее фиксированном** threshold 59 независимых accepted decisions без ошибок дают одностороннюю exact 95% lower bound около 0.9505 (`0.05^(1/59)`). Это иллюстрация объёма доказательства, не разрешение объявить quality по 59 коррелированным mentions из нескольких abstracts. На практике bootstrap по документам/families, rare relations могут остаться `INSUFFICIENT_SUPPORT`; не подгонять threshold на той же группе, которой доказывается precision. Для двухстороннего интервала требования другие.

Дополнительные fine-tuned heads и quantized exports получают новую identity и повторную calibration. No-loss quantization нельзя предполагать. При замене языка или evidence length пороги считаются непроверенными до нового domain slice evaluation.

## 9. Практический shortlist моделей

Первый минимальный набор: **GLiNER small v2.1**, **MiniLM NLI**, существующая **Qwen3.5 4B**. Comparator этапа validation — **DeBERTa-v3-base NLI**. Для C supervised endpoint — **MatSciBERT/SciBERT + небольшой RE head**, для F — **GLiNER-Relex base** с **GLiNER2 base** как альтернативой. GLiREL полезен исследовательски, но его NC-SA license и более крупный encoder делают его не автоматическим default. PolymerNER и SapBERT — domain transfer controls, а не готовые универсальные решения.

Увеличение generative model size не входит в основную стратегию. Сначала сравнить алгоритмы при одном зафиксированном Qwen digest; дополнительный ≤8B model arm допустим только позже как отдельный controlled factor, если алгоритмические варианты не достигли целей.
