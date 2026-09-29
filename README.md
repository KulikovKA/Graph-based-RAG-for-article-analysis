# Graph-based RAG for article analysis

Локальное веб-приложение для поиска и анализа технических решений по патентам и научным публикациям. Backend и frontend сейчас представлены минимальным каркасом; предметная логика будет добавляться задачами из плана.

Начните с [TASKS.md](TASKS.md): там указаны зависимости, критерии готовности и контекст для каждой задачи. Общий порядок работы и обязательный push после каждой задачи — в [task.md](task.md).

## Разработка

- Python 3.11 или 3.12: `python -m pip install -e ".[dev]"`, `uvicorn app.main:app --app-dir src`, `ruff check .`, `mypy src`, `pytest`.
- Node.js/npm: `cd frontend`, `npm install`, `npm run dev`; проверки: `npm run lint`, `npm run typecheck`, `npm run build`, `npm test`.
- `GET /health/live` проверяет процесс; `/health/ready` остаётся 503 до появления проверок PostgreSQL и очереди в DB-002.
- Никогда не помещайте секреты в `.env.example`; локальный `.env` игнорируется Git.
- Состав, версии и лицензии зависимостей SKEL-001 перечислены в [docs/LICENSES.md](docs/LICENSES.md).

## Документы

- [Архитектура](docs/ARCHITECTURE.md) и [решения](docs/DECISIONS.md)
- [Карта донорских репозиториев](docs/REPO_MAP.md)
- [Модель данных](docs/DATA_MODEL.md), [схема графа](docs/GRAPH_SCHEMA.md)
- [API](docs/API_CONTRACTS.md), [LLM](docs/LLM_CONTRACTS.md), [память и кеш](docs/MEMORY_AND_CACHE.md)
- [Развёртывание](docs/DEPLOYMENT.md), [безопасность](docs/SECURITY.md), [оценка качества](docs/EVALUATION.md)
- [ARCH-002: замечания, исправления и проверка согласованности](docs/ARCH_REVIEW.md)

Planning baseline после ARCH-001/ARCH-002: 2026-09-29. Каркас и Compose bootstrap описаны в [TASKS.md](TASKS.md) и [документации развёртывания](docs/DEPLOYMENT.md). Следующая задача — DB-002. Перед реализацией интеграций проверяйте актуальные версии API и условия источников; завершённый planning review не означает готовность production-системы.
