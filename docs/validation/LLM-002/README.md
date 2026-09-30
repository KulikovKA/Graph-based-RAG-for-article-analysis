# LLM-002 — Gemma 4 CPU smoke

Проверено 2026-09-30 на Ollama 0.34.4, Windows host, полном активном Compose проекта.
Выбранный Analyst: `gemma4:26b-a4b-it-mtp-q4_K_M`, digest
`001e5dafc3c77684c2307ebc6ab8e336e10c9b18eca52acf547d72fc83c3ca8c`, размер
18,731,025,629 bytes, Q4_K_M. Ollama сообщает 25.2B параметров, контекст 262,144,
capabilities completion/vision/tools/thinking. Лицензия модели в Ollama Modelfile —
Apache-2.0. Прежний отчет GPT-OSS сохранен отдельно в
[`measurements_gpt-oss_20b.json`](measurements_gpt-oss_20b.json).

## Результаты

- AnalysisV1 strict JSON и точные citation offsets: cold и warm валидны, по одной
  relation, ремонт не потребовался. Thinking не попал в JSON result. `think=low`
  принят; reasoning duration/token counts Ollama отдельно не сообщает.
- Analyst TTFT: 30.69 s cold / 0.61 s warm; полная генерация: 119.95 s / 113.11 s.
  Cold загрузка заняла 24.72 s. Validated-result latency пока отсутствует: этот
  участок появляется в JOB-002.
- Peak Ollama RSS: около 20.3 GB cold / 20.6 GB warm; host used: 31.4 / 32.5 GB;
  Docker Compose total: 2.19 / 2.15 GB. Измеренный swap: 5.59 / 5.32 GB.
- Cancellation вернула `InferenceCancelled`, generation gate не заблокирован,
  модель выгружена. Переключение Planner → Analyst → Planner прошло; за раз
  загружен один генератор.
- Planner cold/warm schema checks прошли. Embeddings стабильны: dimension 1024,
  повторный max delta 0. Reranker cold/warm поставил релевантный документ первым.
  Мини retrieval fixture: Recall@10/20, MRR и top-3 hit rate — 1.0 на 9 кейсах.

Полные метаданные и замеры без текста модели: [`measurements.json`](measurements.json).
Generation token count и reasoning token count Ollama в этих прогонах не отделяет;
сумма prompt/output latency не заменяет validated-result latency.
