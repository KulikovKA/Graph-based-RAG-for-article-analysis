# GRAPHUI-001 — Interactive explanation graph

Completed 2026-10-02.

## Implementation

- Added authenticated `GET /api/v1/runs/{id}/graph` and `/graph/neighbors` routes. Both check run ownership before reading graph data; non-completed runs return `409`, and unknown/foreign nodes and runs return `404`.
- The initial view is assembled from the completed run's immutable source/evidence snapshot and validated `AnswerV1` matches. It contains only allowlisted node and edge types, caps output at 30 nodes and 50 edges, and does not expose Neo4j IDs or properties.
- One-hop expansion uses graph facts only when their revision, chunk, and span overlap evidence in that same run. Results are limited to 20 edges per page and 100 nodes / 200 edges overall. HMAC cursors bind owner, run, node, and graph version.
- Added a responsive graph view with drag pan, zoom controls, selected-node details, shortest-path highlighting from the idea, one-hop expand/collapse, and evidence-card links. Narrow screens use a keyboard-accessible node list.

The interaction pattern follows [LightRAG's reference viewer](https://github.com/HKUDS/LightRAG/blob/main/lightrag_webui/src/features/GraphViewer.tsx) for node focus, zoom controls, and a properties panel; its global graph access and heavy rendering stack were not adopted for this run-scoped view.

## Verification

- `npm run build` — passed.
- `npm run lint` — passed.
- `npm run test:e2e -- --grep "interactive graph"` — passed on desktop (1280 px) and mobile (375 px); selection, expansion, citation navigation, and collapse verified.
- `python -m pytest tests/contract/test_graph_api.py -q` in Compose with PostgreSQL — passed. Covers auth/owner isolation, bounded output/page size, invalid cursors, and unknown internal node IDs.
- `ruff check` on changed Python files — passed.
- Local Compose smoke — Caddy page and API health returned 200, account login/session returned successfully, and an unknown graph run returned 404.

## Limits

Only one-hop graph facts whose provenance overlaps the selected run's saved evidence are shown. Additional corpus data remains outside the view until another retrieval run includes it.
