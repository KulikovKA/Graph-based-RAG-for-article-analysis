# Контракты моделей и deterministic shell

Две роли: маленькая локальная модель планирует intent/patch, Smart Qwen синтезирует ответ. Конкретные веса, quantization, context window и CPU latency выбираются отдельным benchmark на целевом хосте; нельзя обещать производительность без измерения. Интерфейс `InferenceProvider` скрывает local CPU, remote GPU и API provider. Методам передаются `model_id`, `prompt_version`, `timeout`, `request_id`; возвращаются text/JSON, token usage, TTFT и finish reason. Контролируемый single-worker queue не даёт нескольким тяжёлым генерациям превысить RAM.

## Planner v1

Вход: последнее сообщение, текущая structured idea + version, краткая сводка, перечень сохранённых evidence IDs (без полного корпуса). Выход строго JSON:

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

Prompt planner: «Верни только JSON по схеме. Сохраняй смысл неизменённых признаков. Не добавляй факты, не указанные пользователем. Для вопроса о сохранённом источнике укажи evidence ID. Не делай вывод о новизне». Версия prompt хранится в run.

## Analyst v1

Вход: структурированная версия идеи, evidence pack с `evidence_id`, document metadata, section и коротким фрагментом, coverage и допустимый token budget. Выход JSON `summary`, `matches[{feature_id,document_id,evidence_ids,explanation}]`, `differences[{feature_id,evidence_ids,explanation}]`, `limitations`, `followup_suggestions`; поток не отправляется клиенту до проверки citations. Максимум 10–15 документов, выбранные 1–3 фрагмента на документ, суммарный budget конфигурируем (начальный ориентир 6k входных токенов). При переполнении сокращать по rerank score с сохранением разнообразия источников.

Prompt analyst: «Сравни признаки только с данными evidence pack. Каждый существенный вывод снабди существующим evidence_id. Если информация отсутствует, скажи, чего не хватает. Не утверждай юридическую патентную новизну или отсутствие всех аналогов». Граница доверия: **LLM drafts → deterministic citation/evidence validator → repair once → deterministic safe fallback**. Валидатор проверяет, что каждое содержательное утверждение имеет существующие evidence IDs в текущем snapshot, цитируемый фрагмент действительно в evidence, а дословная цитата совпадает с источником. При нарушении даётся один repair с конкретными violation details. Если draft или repair не проходит, детерминированный renderer строит ограниченный ответ только из проверенных evidence фрагментов; при пустом evidence он сообщает об отсутствии источников и не формулирует findings. Проверить renderer тем же валидатором; ошибки и результаты проверки сохранить в run без полного prompt. Это reference pattern, не требование копировать PriorArtRAG 1:1.

Embeddings и reranker — отдельные версии провайдера, не те же две генеративные роли. Embedding dimension фиксируется на уровне коллекции Qdrant; смена модели означает новую коллекцию и reindex. Все prompts, модели, tokenizer, retrieval config и schema versions записываются в `analysis_runs.config_versions_json`.
