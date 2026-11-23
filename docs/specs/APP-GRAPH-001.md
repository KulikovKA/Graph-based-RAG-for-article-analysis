# APP-GRAPH-001 — самостоятельный Explorer API

Опоры: [API_CONTRACTS](../API_CONTRACTS.md), [GRAPH_SCHEMA](../GRAPH_SCHEMA.md), [SECURITY](../SECURITY.md), ADR-009/016. Добавляется читающий Explorer поверх ограниченного порта публичного поколения и приватного run. Порт получает только типизированные аргументы. Действующие run graph/evidence и public Source endpoints сохраняются. Первую волну проверяет внедрённый graph adapter, интеграция Neo4j и повторной проверки в агенте остаётся отдельной.

## Аддитивный контракт для UI и fixtures

Все GET начинаются с `/api/v1/explorer`. `scope=published|run`, `run_id` обязателен для run и отсутствует для published. Первый `/search` без cursor может опустить `graph_version`, чтобы сервер закрепил доступную версию published или сохранённого run после проверки владельца. Страница с cursor и другие операции требуют `graph_version`. Версия — opaque строка, node_id — opaque строка, document_id/revision_id/run_id — UUID. Пустой поиск возвращает пустую страницу. Backend получает текущего пользователя из сессии.

| GET | Параметры помимо scope/version | Результат |
| --- | --- | --- |
| `/search` | `q`, `limit`, `cursor?` | `{graph_version,nodes,documents,next_cursor,truncated}`, GraphNodeV1 и Source metadata |
| `/nodes/{node_id}` | — | `{graph_version,node,context_ref}` |
| `/nodes/{node_id}/neighbors` | `limit,cursor?,edge_type?` | `{graph_version,nodes,edges,next_cursor,truncated}` |
| `/paths` | `source,target,max_hops?,edge_type?` | Такой же bounded subgraph для пути |
| `/documents/{document_id}` | `revision_id` | `{graph_version,source,nodes}`, source — Source DTO с `evidence_ids` |
| `/evidence/{evidence_id}` | — | `EvidenceV1` из видимого scope/version |

У ребра Explorer есть `kind=factual|semantic` вдобавок к существующему `type`. Факты содержат допустимые evidence IDs с точными offsets в pinned revision. `RELATED_TO`, `SIMILAR_TO` и `HAS_SHARED_CONCEPT` служат навигации. Синтетическое `HAS_FEATURE` доступно в run scope как переход Idea → IdeaFeature. Такие рёбра не получают IDs доказательств. Поддержка factual metadata pointer без текстового evidence отложена до согласования схемы I-KG. Caps MVP: 20 элементов страницы, 3 hops, 100 visits, 40 edges и 2 s на вызов порта. Cursor подписан и связан с owner, scope, version, операцией, входами, фильтрами и limit. Context ref подписан и ограничен версией, owner и сроком действия; повторная проверка передаёт в агент только разрешённые refs после проверки текущей conversation и членства вершины. Клиент не включает ref в существующий `MessageInput` до подключения APP-AGENT/I-UI.

| ID | Given → When → Then | Проверка |
| --- | --- | --- |
| GRAPH-1 | Опубликована версия, есть документы/узлы → поиск, открытие ревизии, узла, соседей и путей → типизированный результат в этом scope; пустая выдача без ошибки | Fixture adapter и route contracts |
| GRAPH-2 | Фактические и семантические отношения → раскрытие и evidence → только фактические связи имеют проверяемые citations, документы привязаны к revision | Fixture provenance, invalid offsets и membership |
| GRAPH-3 | Страница или path превышает caps → запрос ограничен, `truncated`/cursor отражают ограничения → изменённый cursor/filter/limit отклоняется | Contract pagination и traversal bounds |
| GRAPH-4 | Запрос без сессии, к чужому run, с неверной версией либо при недоступном порте → 401/404/409 GRAPH_VERSION_CONFLICT/503 GRAPH_UNAVAILABLE → приватные данные и служебные детали не раскрываются | Contract/security, двухпользовательские фейки |
| GRAPH-5 | Получен context ref → повторное использование в разрешённом чате проходит ownership/version/membership; подмена, истечение, чужой чат/run или удалённый объект отклоняются | Contract refs, фикстуры отмены и cross-tenant |

Файлы — новый route/DTO/service port и test fixtures, оркестратор подключает router и сверяет OpenAPI. Развёртывание маршрутов с реальным источником требует INT-RET и I-KG. Совместный UI, graph cache и вызов агента проверяются на I-UI/I-MEM/I-SEC. Откат — отключение нового маршрута/порта с сохранением legacy run view.
