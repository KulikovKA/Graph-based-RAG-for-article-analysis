# Контракты моделей и deterministic shell

Две роли: Planner классифицирует intent, извлекает признаки и предлагает patch/retrieval; reasoning-capable Smart Analyst сравнивает evidence. Предпочтительные локальные кандидаты — `LFM2.5-8B-A1B` и `gpt-oss:20b` соответственно. Planner не выполняет глубокий patent reasoning. Конкретные веса, quantization, context window и CPU latency проходят LLM-002 на целевом хосте. Ни имя кандидата, ни MoE не гарантируют размещение в RAM. `InferenceProvider` скрывает local CPU, remote GPU и API provider; общий single-generation semaphore охватывает все генеративные роли.

## Planner v1

Вход: последнее сообщение, текущая structured idea + version, краткая сводка, source_run_id и перечень его разрешённых evidence IDs (без полного корпуса). Выход строго JSON:

```json
{
  "schema_version": 1,
  "intent": "modify_idea",
  "base_idea_version": 2,
  "add_features": [{"text": "barcode recognition", "rationale": "user requested"}],
  "remove_feature_ids": ["uuid-of-OCR-feature"],
  "replace_features": [],
  "focus_evidence_ids": [],
  "suggested_retrieval": true,
  "confidence": 0.93
}
```

Enum intents: `new_idea`, `modify_idea`, `explain_evidence`, `clarify`, `general_followup`. Pydantic запрещает лишние поля, пустые строки, неизвестные feature/evidence IDs, patch при неверной версии. `suggested_retrieval` — лишь подсказка: shell сравнивает state hash, index/config versions и наличие evidence, затем принимает решение. Если модель вернула invalid JSON, один repair prompt с validation errors; затем deterministic fallback в `clarify`/ошибка без изменения идеи. Не выполнять произвольные инструменты по тексту модели.

`replace_features` имеет элементы `{feature_id,text,rationale}`; add создаёт новые UUID в shell, remove/replace разрешены только для base version и не пересекаются. `new_idea` при существующей идее требует новой conversation или явного modify_idea, без неявного удаления прежних признаков. Для explain_evidence patch-массивы пусты; source_run_id должен быть completed run той же conversation (ownership/status проверяет API до Planner). Если ID не передан, shell выбирает clarification. Исторические snapshot и idea_version этого run разрешено переиспользовать при изменившемся индексе/текущей идее; текущая conversation не откатывается. Новые факты/patch требуют нового retrieval. Shell применяет patch однократно через planner_applied_at/CAS из DATA_MODEL.

Prompt planner: «Верни только JSON по схеме. Сохраняй смысл неизменённых признаков. Не добавляй факты, не указанные пользователем. Для вопроса о сохранённом источнике укажи evidence ID. Не делай вывод о новизне». Версия prompt хранится в run.

## Analyst v1

Вход: структурированная версия идеи, immutable evidence pack с `evidence_id`, document/revision metadata, section и quoted_span, coverage и token budget. Evidence IDs выдаёт shell, совпадение с chunk_id или donor reference_id не предполагается. Максимум 10–15 документов, 1–3 фрагмента на документ; начальный ориентир — 6k входных токенов **всего prompt**, с резервом на internal reasoning и final structured output в context window выбранной модели. Budget считает её tokenizer, включая инструкции/идею/schema; пределы output и deadline обязательны. Усечение pack происходит до snapshot commit и выдачи IDs Analyst; менять snapshot после draft запрещено.

RANK-001 сортирует уникальные documents по score с deterministic tie-break. Для выбранного документа evidence pack берёт до трёх совпадающих предложений из исходного section/chunk; quote всегда точная срезка исходного текста, offsets — Unicode code-point полуинтервал внутри chunk. HTML источника остаётся данными и никогда не исполняется. Token counter должен принадлежать выбранному Analyst tokenizer; он считает собранный prompt целиком (prefix, idea/instructions/schema, evidence и suffix) при каждом добавлении. Evidence IDs назначаются при упаковке уже выбранных span; snapshot не меняет исходные document/revision/chunk IDs.

Prompt analyst: «Верни AnalysisV1. Сравни признаки только с evidence pack; для каждой связи укажи evidence IDs и точные quotes. Отметь частичное совпадение, конфликт или неопределённость. Не утверждай юридическую патентную новизну или отсутствие всех аналогов». Граница доверия ADR-011: **internal reasoning → AnalysisV1 draft → deterministic validation → repair once → deterministic renderer → validation всех проекций → atomic commit → SSE**. При исчерпании repair используется deterministic safe fallback из точных evidence excerpts без модельных relations. Repair получает только structured draft и violation codes/paths, без raw reasoning. Общий лимит — одна repair-попытка на Analyst, а не отдельная на каждый DTO. Ошибка deterministic renderer не лечится новой генерацией: fallback либо failed.

### AnalysisV1: минимальный закрытый DTO

Это итог структурированного сравнения, не transcript рассуждений и не отдельный публичный ответ. Strict schema (`extra=forbid`):

```text
{schema_version:1,
 relations:[{feature_id:UUID, document_id:UUID,
             relation:full|partial|conflicting|uncertain,
             evidence_ids:UUID[], quotes:QuoteV1[]}],
 unresolved_feature_ids:UUID[]}
```

Для каждой уникальной пары feature/document обязательны непустые evidence_ids и quotes; каждый evidence_id покрыт хотя бы одной точной цитатой из того же документа. QuoteV1 и Unicode offsets общие с AnswerV1. `full` относится лишь к одному признаку в выбранных фрагментах. `unresolved_feature_ids` — ровно признаки входной idea_version без full/partial relation; conflicting/uncertain не считаются подтверждением. Нельзя указать неизвестный feature, дубликат пары, противоречивую relation для одной пары или неполный набор unresolved IDs. Лимиты массивов определяются числом признаков и документов bounded pack; размер JSON ограничивается до разбора.

Feature gaps shell выводит из этого множества, document comparisons — группировкой relations по документу, uncertainty — из partial/conflicting/uncertain. Coverage observations и conclusion constraints (`selected_evidence_only`, `no_legal_novelty`, historical/partial) добавляет shell из входного coverage. Отдельные свободные model-generated summary, rationale и conclusion не нужны: они создавали бы вторую поверхность непроверенных утверждений. Отсутствие связи означает только «в выбранных фрагментах подтверждение не установлено», а не отсутствие признака в полном патенте или мире. Отсутствие всех признаков в одном документе допустимо описывать только как отсутствие полной группы full relations в текущем pack, без юридического вывода.

### Проверка и deterministic rendering

Validator сохраняет прежние требования: membership текущего snapshot, соответствие feature/document/revision, непустые citations, точные quotes по offsets. Затем renderer по versioned allowlist templates строит AnswerV1: full/partial → matches; conflicting/uncertain → differences с evidence; summary — ограниченная выборка тех же claims. Текст claims составляется из шаблона, feature label, проверенной metadata, relation enum и буквальных quotes. Никакой свободный текст модели не копируется. Shell-generated limitations содержат coverage, gaps и ограничения вывода; followup_suggestions — только шаблонные вопросы. `PublicAnalysisV1` берёт подмножество тех же claims и limitations (API_CONTRACTS), без усиления формулировок. Для gaps без evidence разрешён только scoped limitation, не ClaimV1 с пустым evidence_ids.

Проверить AnalysisV1, AnswerV1, public analysis и presentation до публикации. Проверка проекций подтверждает соответствие шаблону/входным полям, совпадение claim/notice с AnswerV1 и отсутствие новых facts, ссылок или URL. Renderer не вызывает LLM и не добавляет сравнения, которых нет во входных relations. По-прежнему нельзя доказать semantic entailment одним citation validator: модель может неверно классифицировать relation даже с точной цитатой. Публичные формулировки обозначают результат сопоставления в выбранных фрагментах и uncertainty; качество этих связей обязательно проверяется offline. «Проверено» означает проверку структуры/provenance/цитат, не доказательство истинности. Обещание нулевых смысловых ошибок недопустимо.

Fallback не использует rejected relations, частичный JSON или thinking: только точные excerpts из committed snapshot, allowlist notice о деградации и coverage. При пустом evidence findings пусты. Все fallback проекции проходят тот же validator. Для safe_fallback/no_evidence/clarification AnalysisV1 отсутствует, публичная проекция всё равно выводится из проверенного AnswerV1. Только проверенные артефакты сохраняются; диагностические codes/counts не включают значения rejected полей.

### InferenceProvider: переносимость reasoning

Сохраняются методы `complete_json`, `stream_text`, `embed`, `rerank`. Расширяется существующий complete_json, без отдельного Ollama/domain API:

- Вход: прежние model_id/prompt_version/request_id/prompt, schema, общий deadline/timeout, cancellation signal, output budget и необязательный `reasoning_effort: default|low|medium|high`. Значения нормализованы; adapter сообщает capabilities. Неподдержанный явно заданный effort даёт typed configuration error до вызова, не молча игнорируется.
- Результат: `{value, metadata}`; value — только законченный final JSON, metadata — allowlist provider/model revision, finish_reason, usage и timings. JSON mode не заменяет domain validation. Truncated/timeout/cancelled output никогда не считается готовым JSON, даже если префикс парсится.
- Adapter может потреблять streaming backend внутри complete_json для отмены/таймингов. Raw thinking/analysis channel отбрасывается сразу, без накопления, логов, traces, exception bodies и durable storage. В domain/API нет канала reasoning tokens. Неразделимые или неизвестные channel frames → typed protocol error; regex удаления `<think>` из смешанного текста недостаточно.
- `stream_text` остаётся внутренним методом для final-content chunks и не используется для пользовательского SSE Analyst. Он тоже не экспортирует reasoning. Внешний SSE читает только committed run_events.
- Metadata: model TTFT (первый model token, включая reasoning, когда доступен), reasoning duration/tokens, final-output duration/tokens, total call/load time. Недоступное или неоднозначное измерение = null с reason code; общий eval token count нельзя объявлять reasoning count. Raw provider payload не прикладывается к metadata.
- Deadline включает очередь, загрузку, reasoning, final output и допустимые transport retries; repair/fallback работают в оставшемся run budget. Cancellation передаётся adapter, поздний ответ отбрасывается. Слот не отдаётся следующей генерации до подтверждённого завершения/остановки backend request; при неопределённости worker блокирует новые генерации до восстановления backend. Lease heartbeat не зависит от прихода model tokens.

Capabilities и корректное разделение каналов проверяет LLM-001 на fake providers, LLM-002 — на выбранных runtime/весах. Замена Ollama CPU на vLLM/GPU/compatible API требует adapter/config и этих же contract tests, без изменения AnalysisV1/AnswerV1/SSE. Поддержка конкретного runtime не предполагается только по названию модели.

Embeddings и reranker — отдельные версии провайдера, не те же две генеративные роли. Embedding dimension фиксируется на уровне коллекции Qdrant; смена модели означает новую коллекцию и reindex. Все prompts, модели, tokenizer, retrieval config и schema versions записываются в `analysis_runs.config_versions_json`.

Уточнение ARCH-002: validator проверяет membership IDs, соответствие feature/document, непустые citation arrays и точные quotes по offsets. Он не может доказать смысловую поддержку любого свободного пересказа; такие ошибки проверяются offline faithfulness/ручной разметкой. Для русского текста нужны кейсы с кириллицей, «кавычками», сокращениями и surrogate pairs. `no_evidence`/`clarification` не содержат findings и проходят отдельную строгую ветку того же schema validator.

Невалидный draft → не более одного repair; network error/timeout → сразу deterministic safe_fallback, если его возможно построить в оставшемся deadline. Невалидный fallback → failed/VALIDATION_FAILED, answer=null. Проверенный fallback → completed/safe_fallback; successful empty retrieval → completed/no_evidence. Отмена → cancelled без fallback. Outcomes и state machine общие с DATA_MODEL/API. Provider transport retries входят в общий budget, не создают дополнительные repair rounds; диагностические коды/счётчики сохраняются без сырого prompt/draft.
