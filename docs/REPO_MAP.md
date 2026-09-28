# Карта донорских репозиториев

Срез проверки: 2026-09-28. Использовать ссылки и закреплять commit SHA в lockfile реализации. Это исследование кода и публичных интерфейсов, а не обещание стабильного API будущих версий.

## LightRAG — основной Graph-RAG кандидат

Источник: [HKUDS/LightRAG](https://github.com/HKUDS/LightRAG), ветка main, просмотренное дерево `453dce83d6d0354a06e46c8d4029a0895c4e054b`. [Лицензия MIT](https://github.com/HKUDS/LightRAG/blob/main/LICENSE). В текущем коде есть Neo4j/Qdrant storage, query modes и получение контекста без генерации ответа.

| Путь | Что подтверждено | Решение |
|---|---|---|
| [lightrag/lightrag.py](https://github.com/HKUDS/LightRAG/blob/main/lightrag/lightrag.py) | Оркестратор ingestion/query и storage configuration | Обернуть в `integrations/lightrag_adapter.py`, не копировать |
| [lightrag/base.py](https://github.com/HKUDS/LightRAG/blob/main/lightrag/base.py) | `QueryParam`, `only_need_context`, `mode=mix`, лимиты токенов, `enable_rerank` | Использовать context-only, валидировать результат и source IDs |
| [lightrag/operate.py](https://github.com/HKUDS/LightRAG/blob/main/lightrag/operate.py) | KG query, extraction, provenance/context assembly | Изучить при integration spike; не вызывать внутренние функции напрямую |
| [lightrag/kg/neo4j_impl.py](https://github.com/HKUDS/LightRAG/blob/main/lightrag/kg/neo4j_impl.py) | Реальная реализация Neo4j storage/workspace | Отдельный namespace, не смешивать с доменным графом |
| [lightrag/kg/qdrant_impl.py](https://github.com/HKUDS/LightRAG/blob/main/lightrag/kg/qdrant_impl.py) | Реальная реализация Qdrant storage/workspace | Проверить совместимость коллекций и embedding dimensions |
| [examples/insert_custom_kg.py](https://github.com/HKUDS/LightRAG/blob/main/examples/insert_custom_kg.py) | Custom entities, relationships, chunks с `source_id` | Spike для импорта валидированных данных |
| [lightrag/rerank.py](https://github.com/HKUDS/LightRAG/blob/main/lightrag/rerank.py) | Rerank чанков с budget/window | Сравнить с нашим лёгким reranker, не дублировать без измерения |
| [lightrag_webui/src/features/GraphViewer.tsx](https://github.com/HKUDS/LightRAG/blob/main/lightrag_webui/src/features/GraphViewer.tsx) | React/Sigma graph viewer | Идеи взаимодействия; собственный scoped API/UI |

Ограничения: автоматическое извлечение свободных entity types не гарантирует фиксированную патентную онтологию; встроенный WebUI и auth не являются auth продукта; workspace не заменяет row-level ownership; версия LightRAG может меняться. В фазе 0 проверить API `ainsert_custom_kg`/`aquery` на выбранном релизе, idempotency и очистку provenance. Если custom KG не сохраняет нужные invariant, использовать LightRAG только для публичного контекста, а доменный graph retrieval оставить в собственном адаптере. Не импортировать весь сервер.

## PQAI — патентные эвристики

Источник: [pqaidevteam/pqai](https://github.com/pqaidevteam/pqai), ветка master, просмотренное дерево `56342aaac5d9bf626f9413e5e49819e70709ce2f`. [Лицензия MIT](https://github.com/pqaidevteam/pqai/blob/master/LICENSE), copyright AT&T. Код полезен как reference; полноценный сервис зависит от заранее построенных индексов, model assets и AWS/S3.

| Путь | Проверенный механизм | Решение |
|---|---|---|
| [core/api.py](https://github.com/pqaidevteam/pqai/blob/master/core/api.py) | Patent/NPL search, фильтры, snippets, mapping; импорт требует AWS env/S3 | Не переносить сервис; взять UX/контрактные идеи |
| [core/search.py](https://github.com/pqaidevteam/pqai/blob/master/core/search.py) | Поиск по индексам и ranking кандидатов | Reference для candidate fusion |
| [core/reranking.py](https://github.com/pqaidevteam/pqai/blob/master/core/reranking.py) | `Ranker`, `CustomRanker`, `ConceptMatchRanker` с model assets | Проверить методику, выбрать компактный локальный reranker измерением |
| [core/snippet.py](https://github.com/pqaidevteam/pqai/blob/master/core/snippet.py) | Sentence/span extraction и feature mapping | Переосмыслить с детерминированным span + offsets; код использует случайный контекст и тяжёлые импорты |
| [core/highlighter.py](https://github.com/pqaidevteam/pqai/blob/master/core/highlighter.py) | Подсветка терминов | Не копировать HTML replacement; безопасная подсветка на клиенте |
| [core/documents.py](https://github.com/pqaidevteam/pqai/blob/master/core/documents.py) | Модель Patent/Document | Reference для нормализации, не схема хранения |

## Prior-Art-Engine — недоступен на дату проверки

Указанный URL [nimajz/Prior-Art-Engine](https://github.com/nimajz/Prior-Art-Engine) и GitHub API вернули 404 2026-09-28. [Индексированный README](https://github.com/nimajz/Prior-Art-Engine) описывал OpenAlex arm, dense retrieval, cross-encoder и MIT, но исходники и LICENSE сейчас нельзя проверить. **Не копировать код, не указывать точные пути или поведение как факт.** В `ARCH-001` повторить проверку URL/commit/fork и снять блокировку лишь после просмотра дерева и LICENSE. OpenAlex adapter и двухступенчатый rerank проектировать по официальным API и измерениям независимо от этого донора.

## Внешние API

- [EPO OPS](https://www.epo.org/en/searching-for-patents/data/web-services/ops): XML/REST, регистрация, OAuth и отдельные условия. [Fair use](https://www.epo.org/en/service-support/ordering/fair-use): недельная квота и throttling; соблюдать текущие заголовки и ограничения. Не публиковать скачанный корпус как есть.
- [OpenAlex API](https://developers.openalex.org/): брать метаданные и доступные abstract, сохранять source ID, дату обновления и URL. Проверить актуальные auth/usage limits при реализации; не планировать полный snapshot на 32 ГБ машине.

При включении стороннего кода сохранить оригинальные copyright/license notices и записать точную версию и изменённые файлы в dependency inventory.
