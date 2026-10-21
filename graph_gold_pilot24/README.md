# GRAPH GOLD PILOT 24 — текущий Gold Dataset и исторический подготовительный пакет

Актуальный релиз: **pilot24-owner-reviewed-gold-v1-20261021**. Владелец проекта подтвердил в чате личную ручную проверку всех 24 документов. Статусы: `HUMAN_REVIEWED`, `human_review_status=APPROVED`; разметчик `project_owner`, дата `2026-10-21`, метод `manual_owner_review`. Второго разметчика не было (`secondary_annotator=null`). Это ручная проверка владельцем AI-generated разметки, без независимой двойной аннотации.

Текущее состояние: `annotations/CURRENT_DATASET.json`; отчёт по всем документам: `owner_review_v1/REPORT.md`. В `annotations/gold/` находятся 18 DEV/CALIBRATION документов. Шесть HOLDOUT Gold-файлов, их labels и evidence остаются в закрытом локальном хранилище вне Git. Все 23 abstentions и содержание аннотаций сохранены. Ontology v1.0 и hashes её заморозки неизменны. Предыдущие AI drafts и отчёты сохранены как история; их прежний статус NOT_REVIEWED относится к моменту выпуска соответствующего AI-релиза.

Стандарт текущих данных — `HUMAN_REVIEWED_GOLD_STANDARD`, допуск — `OWNER_APPROVED_FOR_EVALUATION`. Подробности происхождения и проверки: `owner_review_v1/README.md`. Эксперименты A/B/F/C/D этой публикацией не запускаются.

Далее сохранено описание первоначального подготовительного пакета; оно отражает исторический этап до получения source chunks и разметки.

**Первоначальный подготовительный пакет не содержал золотой разметки:** на том этапе тексты EvidenceChunks ещё не были получены. Он включал исследовательскую выборку и read-only скрипт для получения ровно этих frozen revisions из PostgreSQL оригинального проекта.

- `pilot24_manifest.csv` — 24 фиксированных документа из GitHub-аудита `GRAPH_CORPUS_AUDIT`, 12/6/6, OpenAlex IDs и точные document/revision UUID.
- `export_pilot24.py` — только SELECT из PostgreSQL, сохраняет текст chunks, IDs, offsets, hashes и метаданные в JSONL. Запускать в оригинальном репозитории с установленными Python-зависимостями и `DATABASE_URL`; без Ollama.
- `ANNOTATION_GUIDE.md` — правила ручной/ассистированной разметки и QA.

Из корня оригинального репозитория (пример):

```bash
export DATABASE_URL='postgresql+psycopg://USER:PASSWORD@HOST:5432/DBNAME'
python /path/to/export_pilot24.py --manifest /path/to/pilot24_manifest.csv --out /path/to/pilot24_sources.jsonl
```

Фактическую строку подключения взять из локальной конфигурации; не публиковать её и не прикладывать `.env`. Скрипт не проверяет весь 100-doc frozen snapshot hash: он требует точного совпадения UUID ревизии и OpenAlex ID для каждой из 24 записей. Перед окончательным gold заморозить и дополнительно подтвердить глобальный snapshot `5b80378fa2d8312951446fcbb3ada7994d775f13d452ff08fd415377a5fcade0` по original manifest.

После получения `pilot24_sources.jsonl` прикрепить этот один файл в чат. Затем можно реально размечать DEV по source spans и готовить human-reviewable gold. Holdout не использовать для изменений extraction prompt.

- `gold_annotation_template.jsonl` — 24 полностью пустых карточки со статусом `NOT_STARTED`; это **не** отрицательные или размеченные примеры.
