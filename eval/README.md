# EVAL-001: offline harness

Запуск из корня после `python -m pip install -e ".[dev]"`:

```powershell
python -m eval.run --output data/eval/baseline
python -m eval.run --output data/eval/current --baseline data/eval/baseline/run.json
python -m pytest tests/eval
```

Выход: `run.json`, `results.jsonl`, `validated.jsonl`, `report.md`, `report.html`.
Новый output-каталог обязателен: старые результаты не перезаписываются.
Exit codes: 0 — structural gates и baseline diff пройдены; 1 — дефект/регрессия;
2 — несовместимые/некорректные inputs или ошибка хранения. `DISABLED` judge и
`UNSET` latency gate явно показаны в отчёте; exit 0 не означает готовность релиза.

## Что измеряет fixture profile

Используются неизменённые 10 dev cases EVAL-000 и восемь синтетических документов.
`fixture.lock.json` закрепляет cases/schema/manifest/source fixtures. SHA-256 всех
текстовых входов и кода считается после CRLF→LF, чтобы Git checkout на Windows
и Linux не менял identity. Изменение текста, JSON или порядка cases отвергается.
Quoted spans дополнительно проверяются как точные Unicode code-point срезы.

Строится один фиксированный lexical index из title/abstract восьми документов;
его источник — locked manifest. Production `lexical_scores` ранжирует документы;
фиксированный stopword/term-overlap gate отбрасывает запросы без предметных слов.
Source status fixture имитирует недоступность/пустоту адаптера. Expected source IDs
и gold spans используются только scorer-ом, не retrieval. Это облегчённый
контрактный профиль, **не production Qdrant/Neo4j/model benchmark**.

Выбранные полные abstract передаются в настоящий `Analyst.analyze` с провайдером,
возвращающим typed unavailable: проверяются production safe fallback/no-evidence,
renderer, точные цитаты и публичные проекции. Модели не загружаются и не вызываются.
Planner gold отсутствует в EVAL-000; planner accuracy = null/reason. TTFT, tokens,
RAM, model switch, stage и browser timings здесь не измерены, а не равны нулю.
Recorded reset/terminal replay проверяет восстановление публичного текста;
доставка по настоящему proxy/HTTP и worker fencing остаются в JOB/API/TEST tests.

## Импорт наблюдений

```powershell
python -m eval.run --observations data/eval/capture.json --output data/eval/imported
```

Capture envelope: только `snapshot`, `versions`, `observations`.
`snapshot` должен совпадать с `fixture.lock.json`; `observations` — ровно десять
уникальных объектов `Observation` из `eval/harness.py`. Все поля обязательны,
кроме nullable elapsed_ms/timing_reason/replay defaults. `versions`:

```json
{
  "pipeline_version": "my-pipeline-v1",
  "model_config_sha256": "64-lowercase-hex-characters",
  "prompt_schema_sha256": "64-lowercase-hex-characters",
  "retrieval_config_sha256": "64-lowercase-hex-characters"
}
```

В `validated.jsonl` находится пример observation schema. Импорт требует
нормализованных fixture IDs: document UUID = `uid(external_id)`, revision UUID =
`uid(external_id + SHA256(section text))`, chunk UUID = `uid(external_id + '/chunk/0')`.
Native production IDs необходимо сопоставить отдельно с проверкой provenance;
импорт не является автоматическим export из живой базы. Только committed,
validated AnalysisV1/AnswerV1/public/presentation; никаких raw thinking/drafts,
provider bodies, prompts, exception bodies или секретов. Extra fields запрещены.
Invalid observations не копируются в артефакты: остаются только стабильные коды.
Сведения о внешнем pipeline предоставлены оператором, live inference не проверяется.

`replay` содержит `ReplayFrame`: `kind=delta|reset|terminal`, sequence, optional
chunk_index, text. Для completed результата обязательны восстановленный текст,
правильный SHA-256 и terminal. Повтор одного sequence допускает только тот же
payload; reset заменяет текст и задаёт индекс следующего chunk.

## Structured judge

По умолчанию отключён. `judge_case` принимает отдельный offline callable, строго
проверяет `JudgeResult` и делает один retry при invalid schema/case/span. CLI умеет
читать предварительно подготовленные оценки:

```powershell
python -m eval.run --output data/eval/reviewed --judge-results data/eval/judgments.json --judge-id reviewer-rubric-v1
```

Файл — mapping case_id → JudgeResult: пять целых scores 0–4 (`faithfulness`,
`relevance`, `completeness`, `feature_matching`, `conclusion_validity`),
`cited_problem_spans` с evidence_id/start/end, `rationale` из enum в judge.py,
`confidence` 0–1. Свободный текст/рассуждения judge не сохраняются. UNKNOWN/
некорректный результат блокирует прогон. `UNSUPPORTED_RELATION` или faithfulness
0–1 — дефект. Structured citation validity не превращается в semantic faithfulness.
Ручная калибровка 15–20 примеров и baseline 100 кейсов — EVAL-002; synthetic
judge tests не объявляются такой калибровкой.

Baseline требует одинаковые snapshot/case IDs/profile/judge identity. Изменения
модели/prompt/pipeline фиксируются версиями и допускают сравнение. Judge identity
обозначает неизменный rubric/метод; hash файла конкретных оценок записывается
отдельно. Gates: новые structural failures, Recall@10 ниже на >5 п.п.,
faithfulness ниже на >0.25 или утрата измеренного faithfulness. Citation validity
считает quote occurrences во всех claim projections; нулевой denominator = N/A.

## Хранение и ограничения

Без параметров БД harness пишет только локальные файлы. Для выделенной БД с уже
применёнными миграциями можно указать `--database-env EVAL_DATABASE_URL`:
за одну транзакцию сохраняются eval_cases/eval_runs/eval_results. URL и ошибки
драйвера не попадают в отчёты. UUID run в JSON и БД одинаковый. Повторное сохранение
того же run UUID отвергается; новый run переиспользует неизменные case rows.

Runtime artifacts хранить под git-ignored `data/eval`. В docs опубликован только
синтетический acceptance run. Judge не импортируется production-кодом. EVAL-001
не закрывает EVAL-002, production quality/latency budget или внешний demo gate.
