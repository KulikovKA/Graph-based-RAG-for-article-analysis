# GRAPH-GOLD-PILOT24 — полный автоматический проход

**AI drafts 24/24; structural PASS 24/24; human review 0; approved human gold 0.**

Mentions 1004; assertion occurrences 584; unique canonical triples 546; source chunks 35; reviewed sentences 153.

UNRESOLVED: 36 вопросов в 16 документах; 43 relation candidates. Наличие вопросов не блокировало проход.

| Document | Split | Chunks | Mentions | Assertions | Unique canonical triples | Unresolved | Validation |
| --- | --- | --- | --- | --- | --- | --- | --- |
| D001 | DEV | 2 | 61 | 51 | 50 | 0 | PASS |
| D003 | DEV | 2 | 69 | 46 | 43 | 0 | PASS |
| D004 | DEV | 2 | 46 | 18 | 16 | 3 | PASS |
| D010 | DEV | 2 | 105 | 99 | 77 | 0 | PASS |
| D060 | DEV | 1 | 23 | 10 | 10 | 2 | PASS |
| D078 | DEV | 2 | 63 | 24 | 23 | 6 | PASS |
| D035 | DEV | 1 | 32 | 25 | 25 | 0 | PASS |
| D092 | DEV | 1 | 41 | 13 | 13 | 2 | PASS |
| D017 | DEV | 2 | 37 | 29 | 28 | 0 | PASS |
| D038 | DEV | 1 | 27 | 16 | 16 | 1 | PASS |
| D026 | DEV | 1 | 30 | 12 | 12 | 2 | PASS |
| D024 | DEV | 2 | 39 | 15 | 14 | 4 | PASS |
| D018 | CALIBRATION | 2 | 44 | 20 | 20 | 3 | PASS |
| D050 | CALIBRATION | 1 | 30 | 16 | 16 | 4 | PASS |
| D029 | CALIBRATION | 1 | 32 | 16 | 16 | 1 | PASS |
| D042 | CALIBRATION | 2 | 51 | 19 | 15 | 2 | PASS |
| D021 | CALIBRATION | 1 | 24 | 16 | 16 | 1 | PASS |
| D093 | CALIBRATION | 1 | 23 | 14 | 14 | 1 | PASS |
| D068 | HOLDOUT | 2 | 42 | 24 | 24 | 0 | PASS |
| D070 | HOLDOUT | 1 | 36 | 21 | 21 | 2 | PASS |
| D098 | HOLDOUT | 1 | 29 | 16 | 16 | 1 | PASS |
| D088 | HOLDOUT | 2 | 49 | 27 | 24 | 1 | PASS |
| D061 | HOLDOUT | 1 | 47 | 23 | 23 | 0 | PASS |
| D090 | HOLDOUT | 1 | 24 | 14 | 14 | 0 | PASS |

## Источники и независимость

24 frozen revisions / 35 original EvidenceChunks сверены с manifest, хешами архива и live PostgreSQL через read-only socket. Глобальный snapshot hash пересчитан; исходные файлы не заменены. Подробности source_integrity.json и live_source_verification.json.

Аннотации выполнены по исходным текстам. Ollama и сравниваемые extraction pipelines не запускались; predictions не использовались. Источники ограничены abstracts: полнота статей не заявляется.

## Схема, вопросы и качество

Q1/Q2/Q3 применены в рубрике 0.3. После DEV закреплены 18 predicates; непокрытие сохранено отдельно. Отчёт DEV_ONTOLOGY_FREEZE.json содержит ограничение хронологии: первая запись freeze не удалась, CALIBRATION text был показан до повторной успешной записи; принятые определения не менялись по evaluation text.

JSON Schema, Unicode offsets, exact evidence, UUID, endpoints, directions, qualifier attachment, source hashes, sentence coverage и canonical conflicts проверены. Каждый документ прошёл AI semantic self-audit отдельно от structural validation. Это не независимая проверка истинности и не доказательство идеального recall.

Качественные best/high не получили придуманных чисел; proposed mechanisms и вычислительные результаты сохраняют свою область действия; отрицания и not only обработаны по контексту. Повторные source occurrences сохранены; counts canonical triples и qualified claims доступны отдельно.

Все вопросы DEV/CALIBRATION: ../reviews/questions.md. Полный локальный список, включая HOLDOUT, находится в закрытом каталоге. Все 24 документа требуют human review: ../reviews/human_review_queue.json.

## Раздельное хранение и ограничения

18 drafts и несекретные отчёты находятся в репозитории. 6 HOLDOUT drafts, их specifications, evidence-bearing review packets, вопросы и подробные triple audits находятся вне репозитория. В публичных артефактах HOLDOUT представлен только техническими counts/status. Gold пуст.

Риск publication/author/family leakage проверяется в leakage_audit.json. Общий автор не доказывает дубликат; отсутствие совпадений не доказывает независимость семейств. Итоговые результаты ещё не являются confirmatory evaluation.

## Возобновление

Файлы каждого завершённого draft сохранены отдельно. Не перегенерировать готовые labels без необходимости; повторная валидация: python graph_gold_pilot24/validate_annotations.py. Пересчёт отчётов: python graph_gold_pilot24/audit_canonical_claims.py и python graph_gold_pilot24/finalize_campaign.py. Private HOLDOUT location задаётся локальным ignored-файлом или стандартным закрытым каталогом профиля пользователя.
