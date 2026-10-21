# GRAPH-RESEARCH-001 — часть 1

Исследование offline построения технического графа знаний. Дата исходного исследования: **2026-10-19**, Europe/Moscow. Исследованный HEAD: `868bccc` (полный SHA фиксируется в аудите). Режим: **RESEARCH ONLY**. Дополнение архитектуры от **2026-10-21** включает MLflow, минимальные защиты и RU → EN language adapter; его точечная сверка выполнена на HEAD `946f232`. Новые inference, tests, benchmarks, загрузки весов и обращения к базам не выполнялись. Изменялись только Markdown-документы в этом каталоге; production, конфигурация, старые checkpoints, Git commits и remote не изменялись.

## Основной ответ

**Есть обоснованные кандидаты на более точный и дешёвый граф, но превосходство над Hybrid пока не установлено.** Наиболее полезное изменение предметной модели — разделить точное упоминание, идентичность понятия и подтверждённое утверждение с условиями. Framework, увеличение числа рёбер и сам факт присутствия цитаты не заменяют эти три проверки.

Для первого полноценного сравнения предложены **B — Improved Source-grounded Hybrid, C — Small Classifier Pipeline, D — Selective LLM Cascade**. Они проверяют разные гипотезы: эффект упрощения генерации, возможность отказаться от генерации и пользу условного обращения к той же Qwen. A, E и дополнительный F остаются конкурентами на коротком предварительном screening, а не объявляются заведомо хуже.

| Исследовательский приоритет | Кандидат | Основание и ограничение |
|---|---|---|
| Precision/provenance | B | Явные spans, закрытые predicates и отказ при неподтверждённой связи; качество semantic validator ещё `NOT_MEASURED` |
| CPU-efficiency | C | Нет autoregressive decoding; выигрыш зависит от числа entity pairs и recall NER, `NOT_MEASURED` |
| Баланс | D | Использует C для простых случаев и Qwen для трудных; routing и стоимость переключений должны пройти отдельную проверку |
| Сильный дополнительный конкурент | F | Совместный encoder для entities/relations сокращает повторные проходы; новый domain benchmark отсутствует |

Это выбор **для экспериментов**, не итоговый рейтинг качества.

## Что изменилось относительно исходной постановки

- Реальный extractor: `qwen3.5:4b-q4_K_M`, digest `2a654d98e6fba55d452b7043684e9b57a947e393bbffa62485a7aac05ee4eefd`.
- Исторические 100 документов — **OpenAlex abstracts, 136 chunks**, а не смешанный патентно-научный корпус. Выводы о патентных claims потребуют отдельного holdout.
- Hybrid v1.4 уже запрещает canonical name, не совпадающий с нормализованным source surface. Исторические восемь подмен `gas/liquids → NO2/NH3` этим gate отвергаются по сохранённому отчёту. Полноценной semantic entailment проверки это не даёт.
- Уже проведённый isolated replay 27 исторических zero документов дал 21 документ с accepted mentions и 6 `ALL_REJECTED`. Историческая причинность остаётся `UNKNOWN`.
- Текущий LightRAG adapter вставляет chunks с пустыми entities/relationships и запрещает генерацию. Native graph extraction **ещё не является текущим baseline**.
- EVAL-001 опубликован, но его acceptance profile — 10 synthetic cases с lexical retrieval и unavailable-provider fallback. Это не graph extraction benchmark. Подробные основания: [аудит](CURRENT_PIPELINE_AUDIT.md).

## Состав исследования

**Дополнение по запросу пользователя:** [архитектура MLflow, защит и RU → EN](OBSERVABILITY_SECURITY_LANGUAGE_ARCHITECTURE.md). Здесь определены состав логов, границы доверия, перевод технических признаков, отдельные сравнения языка и протокол будущей совместной разметки. Все компоненты пока проектируются; реализации нет.

| Документ | Содержание |
|---|---|
| [CURRENT_PIPELINE_AUDIT.md](CURRENT_PIPELINE_AUDIT.md) | Код, исторические метрики, последние изменения, версии, диагностика и ограничения |
| [LITERATURE_REVIEW.md](LITERATURE_REVIEW.md) | Graph-RAG, scientific/patent IE, joint/span methods, правила, calibration, первоисточники |
| [SMALL_CLASSIFIERS_REVIEW.md](SMALL_CLASSIFIERS_REVIEW.md) | Конкретные checkpoints, лицензии, языки, обучение, ONNX, RAM, выбор исполнителя по задаче |
| [ARCHITECTURE_CANDIDATES.md](ARCHITECTURE_CANDIDATES.md) | Шесть различных pipelines A–F, ontology, provenance, примеры, риски |
| [OBSERVABILITY_SECURITY_LANGUAGE_ARCHITECTURE.md](OBSERVABILITY_SECURITY_LANGUAGE_ARCHITECTURE.md) | Общая архитектура MLflow/guards/language adapter, схема логов, T0–T2/Tref, будущая разметка |
| [PERFORMANCE_ANALYSIS.md](PERFORMANCE_ANALYSIS.md) | Исторические затраты, асимптотика, break-even каскада, CPU/RAM и план измерений |
| [EVAL001_COMPARISON_DESIGN.md](EVAL001_COMPARISON_DESIGN.md) | GraphExtractionResult, adapters A–F, метрики, gold и совместимое расширение harness |
| [EXPERIMENT_ROADMAP.md](EXPERIMENT_ROADMAP.md) | Phases 0–6, контролируемые переменные, критерии отбора и остановки |
| [FINAL_RECOMMENDATIONS.md](FINAL_RECOMMENDATIONS.md) | Матрица A–F, shortlist, ответы на 15 исследовательских вопросов |

## Уровни доказательности

**Факт кода** — установлен чтением конкретной реализации. **Историческое измерение** — взято из сохранённого артефакта и не воспроизведено в этой работе. **Внешний результат** — относится только к условиям цитируемой публикации. **Гипотеза** — предложение данного исследования. `NOT_MEASURED` означает отсутствие измерения; `UNKNOWN` — отсутствие достоверно установленного факта. `N/A` используется только при неприменимости метрики, например нулевом знаменателе citations.

Источники проверялись по официальным репозиториям, model cards, API метаданных, ACL Anthology, статьям и документации. Читались только тексты и метаданные: модели, датасеты и пакеты не скачивались. Различаются опубликованный release, source commit, архитектура encoder и обученный task checkpoint. Для наиболее важных моделей приведены наблюдавшиеся revisions; это исследовательская фиксация, не изменение dependency lock.

## Чего не хватает

Нет независимого human gold для entities/relations/roles/qualifiers на frozen corpus; нет patent holdout, измерений A–F, калибровки classifiers на данном домене, peak RAM альтернатив и подтверждения semantic precision текущего полного v1.4 corpus. Нет также RU–EN query gold и guard regression gold. Старые AI annotations полезны для поиска сложных случаев, но не заменяют gold. Следующий отдельный этап — **совместная разметка development примеров и уточнение rubric/glossary в Phase 0B**. Реализация EVAL/MLflow/guards начинается позднее в Phase 0C, до первых model experiments. Полную реализацию всех шести вариантов заранее планировать не требуется.
