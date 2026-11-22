# Graph-based RAG for article analysis

Веб-приложение для предварительного исследования технических идей по патентам EPO и научным публикациям OpenAlex. Цель диплома — два режима на общей инфраструктуре: самостоятельный Knowledge Graph Explorer и Patent Research Assistant с поиском, сравнением признаков и ссылками на доказательства. Выводы относятся к найденному корпусу и имеют технический характер.

Сейчас работают базовый гибридный поиск по чанкам и графу, проверяемый анализ, сохранённые чаты и подграф конкретного анализа. Самостоятельный Explorer, переход генерации на Groq, офлайн-DAG Airflow и полноценное агентное расширение описаны как план работ. Эксперименты остаются в [RESEARCH](https://github.com/KulikovKA/Graph-RAG-news-analytics-system-RESEARCH). [Окончательный план и срез реализации](docs/FINAL_PROJECT_PLAN.md) · [Рабочий backlog](TASKS.md) · [Правила выполнения и публикации](task.md)

## Разработка

- Python 3.11 или 3.12: `python -m pip install -e ".[dev]"`, `uvicorn app.main:app --app-dir src`, `ruff check .`, `mypy src`, `pytest`.
- Node.js/npm: `cd frontend`, `npm install`, `npm run dev`; проверки: `npm run lint`, `npm run typecheck`, `npm run build`, `npm test`.
- `GET /health/live` проверяет процесс, `/health/ready` — доступ к таблице очереди PostgreSQL.
- Никогда не помещайте секреты в `.env.example`; локальный `.env` игнорируется Git.
- Состав, версии и лицензии зависимостей SKEL-001 перечислены в [docs/LICENSES.md](docs/LICENSES.md).

## Документы

- [Архитектура](docs/ARCHITECTURE.md) и [решения](docs/DECISIONS.md)
- [Карта донорских репозиториев](docs/REPO_MAP.md)
- [Модель данных](docs/DATA_MODEL.md), [схема графа](docs/GRAPH_SCHEMA.md)
- [API](docs/API_CONTRACTS.md), [LLM](docs/LLM_CONTRACTS.md), [память и кеш](docs/MEMORY_AND_CACHE.md)
- [Развёртывание](docs/DEPLOYMENT.md), [безопасность](docs/SECURITY.md), [оценка качества](docs/EVALUATION.md)
- [ARCH-002: замечания, исправления и проверка согласованности](docs/ARCH_REVIEW.md)

История прежнего baseline и результаты завершённых задач сохранены в [TASKS.md](TASKS.md#история-прежнего-baseline). Целевая архитектура и команды для текущего переходного runtime описаны отдельно в [документации развёртывания](docs/DEPLOYMENT.md).
