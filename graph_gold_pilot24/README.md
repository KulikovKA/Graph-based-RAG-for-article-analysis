# GRAPH GOLD PILOT 24 — подготовительный пакет

**Не содержит золотой разметки:** полный исходный текст 24 статей ещё отсутствует в текущем чате. Содержит обоснованную исследовательскую выборку и read-only скрипт для получения ровно этих frozen revisions из PostgreSQL оригинального проекта.

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
