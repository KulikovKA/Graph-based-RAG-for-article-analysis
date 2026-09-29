# Контракты моделей и deterministic shell

Две роли: маленькая локальная модель планирует intent/patch, Smart Qwen синтезирует ответ. Конкретные веса, quantization, context window и CPU latency выбираются отдельным benchmark на целевом хосте; нельзя обещать производительность без измерения. Интерфейс `InferenceProvider` скрывает local CPU, remote GPU и API provider. Методам передаются `model_id`, `prompt_version`, `timeout`, `request_id`; возвращаются text/JSON, token usage, TTFT и finish reason. Контролируемый single-worker queue не даёт нескольким тяжёлым генерациям превысить RAM.

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

Вход: структурированная версия идеи, immutable evidence pack с `evidence_id`, document/revision metadata, section и quoted_span, coverage и token budget. Draft использует `schema_version`, `summary:ClaimV1[]`, `matches[{feature_id,document_id,claims:ClaimV1[]}]`, `differences[{feature_id,claims:ClaimV1[]}]`, `followup_suggestions` из [AnswerV1](API_CONTRACTS.md#runv1-и-единый-answerv1). `limitations` добавляет shell из coverage/validation codes, модель не может их подменить. Evidence IDs выдаёт shell, совпадение с chunk_id или donor reference_id не предполагается. Поток не отправляется клиенту до проверки и terminal commit. Максимум 10–15 документов, 1–3 фрагмента на документ; начальный ориентир — 6k входных токенов **всего prompt**, с резервом на output в context window выбранной модели. Budget считает её tokenizer, включая инструкции/идею/schema. Усечение pack происходит до snapshot commit и выдачи IDs Analyst; менять snapshot после draft запрещено.

Prompt analyst: «Сравни признаки только с данными evidence pack. Каждый существенный вывод снабди существующим evidence_id. Если информация отсутствует, скажи, чего не хватает. Не утверждай юридическую патентную новизну или отсутствие всех аналогов». Граница доверия: **LLM drafts → deterministic citation/evidence validator → repair once → deterministic safe fallback**. Валидатор проверяет, что каждое содержательное утверждение имеет существующие evidence IDs в текущем snapshot, цитируемый фрагмент действительно в evidence, а дословная цитата совпадает с источником. При нарушении даётся один repair с конкретными violation details. Если draft или repair не проходит, детерминированный renderer строит ограниченный ответ только из проверенных evidence фрагментов; при пустом evidence он сообщает об отсутствии источников и не формулирует findings. Проверить renderer тем же валидатором; ошибки и результаты проверки сохранить в run без полного prompt. Это reference pattern, не требование копировать PriorArtRAG 1:1.

Embeddings и reranker — отдельные версии провайдера, не те же две генеративные роли. Embedding dimension фиксируется на уровне коллекции Qdrant; смена модели означает новую коллекцию и reindex. Все prompts, модели, tokenizer, retrieval config и schema versions записываются в `analysis_runs.config_versions_json`.

Уточнение ARCH-002: validator проверяет membership IDs, соответствие feature/document, непустые citation arrays и точные quotes по offsets. Он не может доказать смысловую поддержку любого свободного пересказа; такие ошибки проверяются offline faithfulness/ручной разметкой. Для русского текста нужны кейсы с кириллицей, «кавычками», сокращениями и surrogate pairs. `no_evidence`/`clarification` не содержат findings и проходят отдельную строгую ветку того же schema validator.

Невалидный draft → не более одного repair; network error/timeout → сразу deterministic safe_fallback, если его возможно построить в оставшемся deadline. Невалидный fallback → failed/VALIDATION_FAILED, answer=null. Проверенный fallback → completed/safe_fallback; successful empty retrieval → completed/no_evidence. Отмена → cancelled без fallback. Outcomes и state machine общие с DATA_MODEL/API. Provider transport retries входят в общий budget, не создают дополнительные repair rounds; диагностические коды/счётчики сохраняются без сырого prompt/draft.
