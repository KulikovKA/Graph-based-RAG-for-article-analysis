# Graph-based RAG for article analysis

План локального веб-приложения для поиска и анализа технических решений по патентам и научным публикациям. На этом этапе в репозитории только архитектура и план работ; production-код ещё не реализован.

Начните с [TASKS.md](TASKS.md): там указаны зависимости, критерии готовности и контекст для каждой задачи. Общий порядок работы и обязательный push после каждой задачи — в [task.md](task.md).

## Документы

- [Архитектура](docs/ARCHITECTURE.md) и [решения](docs/DECISIONS.md)
- [Карта донорских репозиториев](docs/REPO_MAP.md)
- [Модель данных](docs/DATA_MODEL.md), [схема графа](docs/GRAPH_SCHEMA.md)
- [API](docs/API_CONTRACTS.md), [LLM](docs/LLM_CONTRACTS.md), [память и кеш](docs/MEMORY_AND_CACHE.md)
- [Развёртывание](docs/DEPLOYMENT.md), [безопасность](docs/SECURITY.md), [оценка качества](docs/EVALUATION.md)
- [ARCH-002: замечания, исправления и проверка согласованности](docs/ARCH_REVIEW.md)

Planning baseline после ARCH-001/ARCH-002: 2026-09-29. Следующая задача — SKEL-001. Перед реализацией интеграций проверяйте актуальные версии API и условия источников; завершённый planning review не означает готовность production-системы.
