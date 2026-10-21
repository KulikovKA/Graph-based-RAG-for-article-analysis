# GRAPH-GOLD-PILOT24 — checkpoint 2026-10-21

**Работа не завершена: первичный проход 2/24, human gold 0/24.**

## Источники

Проверены все 24 документа, 24 ревизии, 35 chunks и split 12/6/6. Архив подготовки распакован без изменения его пяти файлов.

Исходные тексты взяты без восстановления из hash-verified corpus_export.json от 2026-10-02. Затем все выбранные source-поля сверены с работающей PostgreSQL: полное совпадение. Подробности: `source_integrity.json` (первичная offline-проверка) и `live_source_verification.json` (последующая live-проверка, заменяет первоначальный статус недоступности БД).

Глобальный snapshot `5b80378fa2d8312951446fcbb3ada7994d775f13d452ff08fd415377a5fcade0` независимо пересчитан по сохранённому snapshot. Его файл не изменён. Source artifact SHA-256 сверён с artifact_hashes.json. Хеши revisions и chunks и соответствие section offsets проверены.

Docker Engine 29.2.1 доступен; запущен только сервис postgres. Предоставленный export_pilot24.py был вызван через обёртку с read-only транзакциями. TCP-подключение отклонено: password authentication failed for user article_app. Пароль из .env корректно экранирован и совпадает с окружением существующего контейнера, но не принимается ролью в сохранённой базе. Пароль не менялся. Альтернативная SELECT-сверка выполнена через локальный Unix socket в REPEATABLE READ READ ONLY.

Ollama, LightRAG, worker и extraction pipelines не запускались. Model facts/predictions не выводились в контекст разметки и не использовались для меток. Snapshot целиком хешировался программно; его facts не использовались как источники annotations.

## Первичный проход

| Document | Chunks | Sentences | Mentions | Assertions | Concepts | Identity | Validation | Human review |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| D001 | 2 | 6 | 61 | 51 | 54 | 9 | PASS | NOT_REVIEWED |
| D010 | 2 | 7 | 105 | 99 | 46 | 76 | PASS | NOT_REVIEWED |

Все 13 предложений прочитаны в source-only AI-проходе. Spans включают повторные и вложенные упоминания; численные qualifiers сохраняют source evidence и attachment. Неизвестные параметры не дополнены догадками.

Общий вопрос Q1 — согласование словаря 16 predicates и границ rubric. Он отмечен UNRESOLVED в обеих карточках, но это **один** вопрос, не два разных технических спора. Нерешённых assertion candidates нет: явно неподтверждённые отношения не создавались.

Заявленная exhaustive-разметка — результат AI-прохода, а не измеренная полнота gold. Синтаксическая валидация не подтверждает семантику. Независимый primary/secondary human review не проводился, подписи null. Каталог gold пуст.

## Следующий шаг

Согласовать Q1 в reviews/questions.md, записать фактический ответ в adjudication_decisions.jsonl и применить необходимые изменения. Только затем переходить к остальным 10 DEV. После DEV заморозить rubric; CALIBRATION и HOLDOUT размечать отдельно. Проверка publication/author/family duplicates до закрытия HOLDOUT ещё не выполнена. HOLDOUT не использован для настройки правил.

## Воспроизведение

Из корня репозитория:

```powershell
.\.venv\Scripts\python.exe graph_gold_pilot24/prepare_archived_sources.py
.\.venv\Scripts\python.exe graph_gold_pilot24/verify_live_socket.py
.\.venv\Scripts\python.exe graph_gold_pilot24/validate_annotations.py
.\.venv\Scripts\python.exe graph_gold_pilot24/write_review_packets.py
```

`build_dev_pair.py` содержит вручную заданные AI-решения и воспроизводит первичный draft; не использовать его для перезаписи будущей human-adjudicated версии. Семантический анализ не является результатом regex/extraction pipeline: поиск текста используется только для вычисления offsets заранее выбранных spans.
