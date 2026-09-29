# Офлайн оценка качества

Система judge не вызывается из production request path. Датасет около 100 случаев: новые идеи, изменение признака, уточнение по найденному патенту, отсутствие релевантных результатов, конфликтующие evidence, частичный отказ источника, multi-user isolation и нарушения grounding (uncited assertion, phantom citation, fabricated quote, неуспешный repair и deterministic fallback). Каждый case имеет `case_id`, query, previous state/messages, expected feature patch, допустимые/обязательные source IDs, проверяемые claims и rubric. Собрать из легально доступных данных, обезличить пользовательские идеи. Разделить 70/15/15 dev/validation/holdout и не подгонять по holdout.

Eval run фиксирует git commit, pipeline version, corpus/index snapshot, source adapter version, модель/quantization/prompt schema, retrieval settings, latency/TTFT/tokens, structured idea, candidate IDs, selected evidence, final answer, judge result и operator notes. Хранить JSONL артефакт плюс таблицы eval_runs/eval_results. Сравнивать одинаковые кейсы и corpus snapshot между версиями; не сравнивать разные архитектуры RAG ради эксперимента.

Метрики: planner intent accuracy и patch validity; retrieval Recall@10/MRR на размеченных source IDs; citation validity (100% ссылок существуют в snapshot); доля uncited assertions, phantom citations и fabricated quotes; доля нарушений, исправленных одним repair; safe fallback validity; faithfulness, relevance, completeness, feature matching, conclusion validity по шкале 0–4; latency p50/p95 и failure rate. Judge возвращает Pydantic JSON `{case_id, scores, cited_problem_spans, rationale, confidence}`; один retry при invalid schema. Ручная калибровка на 15–20 случаях и blind review спорных оценок, поскольку judge сам ошибается. Юридическая «новизна» не метрика.

Регрессия: на каждом релизном кандидате прогнать все 100 случаев на зафиксированном корпусе; fail при citation validity <100%, падении retrieval Recall@10 >5 п.п., среднем faithfulness >0.25 балла ниже baseline, новых cross-user leaks или p95 > согласованного budget. Численные пороги пересмотреть после первой baseline, но не задним числом для текущего сравнения. Отчёт содержит diff по case IDs, failed examples, версии и ссылки на source evidence. `docs/EVALUATION.md` обновлять вместе с rubric.

## Порядок подготовки и проверки

- EVAL-000 (P0, после ING-001): 10 небольших synthetic/licensed dev cases и frozen fixtures. Expected source IDs и точные spans готовы **до RANK-001**; это вход для двух компактных reranker вариантов, а не зависимость от ещё не написанного полного harness.
- EVAL-001 (P1, после API-001): harness, versioned artifacts, judge/schema и negative regression tests на dev fixture. Не объявляет 100-case baseline выполненным.
- EVAL-002 (P1): 100 размеченных случаев и полный baseline/report. Первые 10 остаются внутри 70 dev; никакого overlap с 15 validation/15 holdout. Подготовка/экспертная разметка — отдельно оценённые 8–16 часов человека сверх обычного code review; генерация 100 непроверенных queries не закрывает этот gate.

Регрессии ARCH-002: различать completed/safe_fallback, completed/no_evidence, failed и cancelled; проверять отсутствие draft в GET/SSE, истёкший replay cursor, stale worker fencing, same-text/different-revision provenance, чужой source_run_id, восстановление graph из PG facts, invalid source membership и Unicode offsets. Semantic faithfulness оценивается отдельно от структурной citation validity. Для ответа без findings citation denominator=0 помечается N/A и отдельно проверяется no-evidence schema; это не искусственные 100% citations. Quoted-span validity не допускает расхождений с исходным snapshot.

LLM результат не обязан совпадать побайтно: воспроизводимы inputs, IDs, versions и evaluation protocol. Первый measured baseline и p95 budget утверждаются до release comparison; пока latency budget не измерен в LLM-002/EVAL-002, отчёт явно помечает latency gate как неустановленный и REL-001 не считается готовым.

## Критерии reasoning / streaming (ADR-011)

Это требования к будущим LLM-002, ANALYST/JOB/API/UI tests и EVAL-001/002, а не результат выполненного benchmark/evaluation. Eval сохраняет только validated AnalysisV1, AnswerV1, PublicAnalysisV1, presentation, версии и allowlist metadata. Raw reasoning, prompt/response dumps и rejected draft не становятся eval artifacts; synthetic leakage sentinels допустимы только как тестовые входы.

| Проверка | Gate / метод |
|---|---|
| Public analysis faithfulness | Rubric 0–4 отдельно для full/partial/conflicting/uncertain relations; ручная калибровка. Цитата должна поддерживать показанное сопоставление; semantic support не подменяется membership |
| Unsupported public statements | Ни одного uncited/phantom/fabricated statement в contract/adversarial fixtures. В размеченном baseline считать отдельно unsupported relation rate; любое подтверждённое unsupported публичное утверждение — блокирующий дефект кейса, а не допустимый «проверенный» результат |
| Summary ↔ AnswerV1 | 100% summary claims/limitations — те же элементы AnswerV1; scoped gap не превращается в глобальное отсутствие аналога; renderer не добавляет фактов |
| Citations / quotes | Прежние 100% membership/span gates и N/A для пустых findings; русский текст, emoji/Unicode, разные revisions, document/feature mismatch |
| No reasoning leakage | Synthetic sentinel в thinking, split frames, extra JSON fields, truncated output, exceptions, repair/timeout/cancel; ноль sentinel bytes в GET/SSE/messages/DB/logs/traces/eval artifacts |
| Replay / reset | Disconnect между любыми chunks; повторная доставка не дублирует текст; stale/missing cursor после compaction восстанавливает summary/progress/full text; hash совпадает; terminal не теряется |
| Cancellation / crash | Cancel во время model load/reasoning/final JSON/repair и перед terminal CAS; crash до и после commit; expired lease и поздний provider response не создают events/results |
| Desktop / mobile | Реальный proxy flush, counts/stages до результата, elapsed без фиктивных процентов, summary после проверки, gradual answer, reduced motion, show-all, reconnect/cancel во время presentation |
| Peak RAM / model switch | LLM-002: cold/warm, оба направления Planner↔Analyst, RSS процесса плюс container/host peak и swap с базами и embedding/rerank. Не утверждать gate по размеру файла весов |

Latency report разделяет `queue_wait`, `planner`, `retrieval`, `rerank`, `analyst_call`, `analyst_reasoning`, `analyst_final_output`, `validation`, `final_rendering`, `terminal_commit` и `total_run` (accepted_at → terminal commit). Timings вызовов — monotonic durations; persisted timestamps UTC. Model TTFT — от dispatch до первого model token (включая reasoning, если backend позволяет измерить); неизвестный boundary → null/reason. Reasoning/output tokens раздельно только при надёжной поддержке provider.

User timings от accepted_at: first visible progress, validated analysis summary, first answer delta, full answer display. Сервер отдельно фиксирует commit/availability этих событий; browser instrumentation измеряет реальные receive/display timings с учётом часов/transport. При reconnect результат уже мог быть готов: пометить reconnect и не смешивать с cold initial-request p50/p95. Summary latency может практически совпадать с first delta, потому что оба публикуются одной транзакцией; UI animation не считается model latency. Для failed/cancelled отсутствующие milestones = N/A, не ноль. Первые измерения LLM-002 утверждают ресурсный/latency budget до сравнения EVAL-002; safety gates выше не ослабляются ради CPU latency.
