"""Компонентные проверки Explorer с искусственным графом, без Neo4j."""

from collections import deque
from uuid import uuid4

import pytest
from fastapi import HTTPException
from fastapi.testclient import TestClient

from app.api.auth import require_owner
from app.domain.contracts import EvidenceV1, SourceV1
from app.domain.explorer import (
    DocumentView,
    ExplorerEdge,
    ExplorerNode,
    GraphScope,
    Scope,
    SearchPage,
    SubgraphPage,
)
from app.main import create_app
from app.services.auth import Principal
from app.services.explorer import ExplorerService, _encode

OWNER, OTHER, RUN, CHAT, DOC, REV, EID, CHUNK = (uuid4() for _ in range(8))


class FixtureGraph:
    def __init__(self):
        self.nodes = {
            x: ExplorerNode(id=x, type="TechnicalFeature", label=x) for x in ("a", "b", "c")
        }
        self.text = "Абвгд"
        self.ev = EvidenceV1(
            evidence_id=EID,
            document_id=DOC,
            revision_id=REV,
            chunk_id=CHUNK,
            section="abstract",
            span_start=1,
            span_end=3,
            quoted_span="бв",
            source_url="https://openalex.org/W123",
        )
        self.src = SourceV1(
            document_id=DOC,
            revision_id=REV,
            title="a",
            kind="work",
            url="https://openalex.org/W123",
            evidence_ids=[EID],
        )
        self.edges = [
            ExplorerEdge(
                id="1",
                source="a",
                target="b",
                type="DISCLOSES_FEATURE",
                kind="factual",
                evidence_ids=[EID],
            ),
            ExplorerEdge(id="2", source="a", target="c", type="SIMILAR_TO", kind="semantic"),
        ]
        self.chat_allowed = True
        self.active_version = "g1"
        self.published_versions = {"g1"}
        self.searched_versions = []

    async def resolve(self, owner, scope, run_id, *, requested_version):
        if scope == Scope.RUN:
            return "g1" if owner == OWNER and run_id == RUN else None
        if requested_version in self.published_versions:
            return requested_version
        return self.active_version

    async def search(self, scope, q, offset, limit):
        self.searched_versions.append(scope.version)
        values = sorted(
            (n for n in self.nodes.values() if q.casefold() in n.label.casefold()),
            key=lambda n: n.id,
        )
        values += [self.src] if q.casefold() in self.src.title.casefold() else []
        page = values[offset : offset + limit]
        return SearchPage(
            nodes=[v for v in page if isinstance(v, ExplorerNode)],
            documents=[v for v in page if isinstance(v, SourceV1)],
            more=offset + len(page) < len(values),
        )

    async def node(self, scope, node_id):
        return self.nodes.get(node_id)

    async def neighbors(self, scope, node_id, edge_type, offset, limit):
        if node_id not in self.nodes:
            return None
        edges = [
            e
            for e in self.edges
            if node_id in (e.source, e.target)
            and (edge_type is None or e.type == edge_type)
            and (
                e.kind == "semantic"
                or all([await self.evidence(scope, eid) for eid in e.evidence_ids])
            )
        ]
        page = edges[offset : offset + limit]
        ids = {node_id} | {e.source for e in page} | {e.target for e in page}
        return SubgraphPage(
            nodes=[self.nodes[i] for i in sorted(ids)],
            edges=page,
            more=offset + len(page) < len(edges),
        )

    async def paths(self, scope, source, target, edge_type, max_hops, max_visits, max_edges):
        if source not in self.nodes or target not in self.nodes:
            return None
        queue = deque([(source, [])])
        visited = {source}
        examined = 0
        while queue:
            node, path = queue.popleft()
            if node == target:
                ids = {source, target} | {e.source for e in path} | {e.target for e in path}
                return SubgraphPage(
                    nodes=[self.nodes[i] for i in sorted(ids)], edges=path, more=False
                )
            if len(path) == max_hops:
                continue
            for edge in self.edges:
                if node not in (edge.source, edge.target) or (edge_type and edge.type != edge_type):
                    continue
                examined += 1
                if examined > max_edges or len(visited) >= max_visits:
                    return SubgraphPage(nodes=[], edges=[], more=True)
                if edge.kind == "factual" and not all(
                    [await self.evidence(scope, eid) for eid in edge.evidence_ids]
                ):
                    continue
                nxt = edge.target if node == edge.source else edge.source
                if nxt not in visited:
                    visited.add(nxt)
                    queue.append((nxt, path + [edge]))
        return SubgraphPage(nodes=[], edges=[], more=False)

    async def document(self, scope, document_id, revision_id):
        if (document_id, revision_id) != (DOC, REV):
            return None
        ids = [EID] if await self.evidence(scope, EID) else []
        return DocumentView(source=self.src.model_copy(update={"evidence_ids": ids}), nodes=[])

    async def evidence(self, scope, evidence_id):
        if evidence_id != EID or self.ev.document_id != DOC or self.ev.revision_id != REV:
            return None
        if (
            self.ev.span_end <= self.ev.span_start
            or self.text[self.ev.span_start : self.ev.span_end] != self.ev.quoted_span
        ):
            return None
        return self.ev

    async def conversation_allowed(self, owner, conversation_id, run_id):
        return (
            self.chat_allowed
            and owner == OWNER
            and conversation_id == CHAT
            and run_id in (None, RUN)
        )


@pytest.fixture
def setup():
    graph = FixtureGraph()
    app = create_app(explorer=graph)
    app.dependency_overrides[require_owner] = lambda: Principal(OWNER, uuid4(), "csrf")
    return TestClient(app), graph, app


def test_search_pagination_cursor_and_revision(setup):
    client, graph, _ = setup
    base = {"scope": "published", "q": "a", "limit": 1}
    first = client.get("/api/v1/explorer/search", params=base)
    assert first.status_code == 200
    assert first.json()["graph_version"] == "g1"
    cursor = first.json()["next_cursor"]
    assert cursor and first.json()["truncated"]
    second = client.get(
        "/api/v1/explorer/search", params={**base, "graph_version": "g1", "cursor": cursor}
    )
    assert second.status_code == 200 and second.json()["documents"][0]["revision_id"] == str(REV)
    for changed in (
        {"limit": 2},
        {"q": "b"},
        {"cursor": cursor[:-1] + ("A" if cursor[-1] != "A" else "B")},
    ):
        assert (
            client.get(
                "/api/v1/explorer/search",
                params={**base, "graph_version": "g1", "cursor": cursor, **changed},
            ).status_code
            == 400
        )
    assert (
        client.get("/api/v1/explorer/search", params={"scope": "published", "q": "  "}).json()[
            "nodes"
        ]
        == []
    )
    assert (
        client.get(
            f"/api/v1/explorer/documents/{DOC}",
            params={"scope": "published", "graph_version": "g1", "revision_id": uuid4()},
        ).status_code
        == 404
    )
    assert client.get(
        f"/api/v1/explorer/documents/{DOC}",
        params={"scope": "published", "graph_version": "g1", "revision_id": REV},
    ).json()["source"]["evidence_ids"] == [str(EID)]


def test_cursor_keeps_a_retained_published_generation(setup):
    client, graph, _ = setup
    endpoint = "/api/v1/explorer/search"
    params = {"scope": "published", "q": "a", "limit": 1}
    initial = client.get(endpoint, params=params)
    assert initial.status_code == 200 and initial.json()["graph_version"] == "g1"
    cursor = initial.json()["next_cursor"]
    assert cursor

    graph.published_versions.add("g2")
    graph.active_version = "g2"
    assert client.get(endpoint, params=params).json()["graph_version"] == "g2"
    historical = {**params, "graph_version": "g1", "cursor": cursor}
    second = client.get(endpoint, params=historical)
    assert second.status_code == 200 and second.json()["graph_version"] == "g1"
    assert graph.searched_versions == ["g1", "g2", "g1"]

    graph.published_versions.remove("g1")
    conflict = client.get(endpoint, params=historical)
    assert conflict.status_code == 409 and conflict.json()["error"]["code"] == (
        "GRAPH_VERSION_CONFLICT"
    )
    assert graph.searched_versions == ["g1", "g2", "g1"]
    run = {**params, "scope": "run", "run_id": str(RUN), "graph_version": "g2"}
    assert client.get(endpoint, params=run).status_code == 409
    assert client.get(endpoint, params={**run, "run_id": str(uuid4())}).status_code == 404


def test_edges_evidence_and_traversal(setup):
    client, graph, _ = setup
    params = {"scope": "published", "graph_version": "g1"}
    page = client.get("/api/v1/explorer/nodes/a/neighbors", params={**params, "limit": 1}).json()
    assert page["edges"][0]["kind"] == "factual" and page["edges"][0]["evidence_ids"] == [str(EID)]
    cursor = page["next_cursor"]
    assert (
        client.get(
            "/api/v1/explorer/nodes/a/neighbors", params={**params, "limit": 2, "cursor": cursor}
        ).status_code
        == 400
    )
    page2 = client.get(
        "/api/v1/explorer/nodes/a/neighbors", params={**params, "limit": 1, "cursor": cursor}
    ).json()
    assert page2["edges"][0]["kind"] == "semantic" and page2["edges"][0]["evidence_ids"] == []
    assert (
        client.get(f"/api/v1/explorer/evidence/{EID}", params=params).json()["quoted_span"] == "бв"
    )
    path = client.get(
        "/api/v1/explorer/paths", params={**params, "source": "b", "target": "c", "max_hops": 2}
    ).json()
    assert len(path["edges"]) == 2
    assert (
        client.get(
            "/api/v1/explorer/paths", params={**params, "source": "b", "target": "c", "max_hops": 4}
        ).status_code
        == 422
    )
    graph.text = "wrong"
    assert client.get(f"/api/v1/explorer/evidence/{EID}", params=params).status_code == 404
    assert (
        client.get("/api/v1/explorer/nodes/a/neighbors", params=params).json()["edges"][0]["kind"]
        == "semantic"
    )


def test_scope_auth_version_unavailable_and_refs(setup):
    client, graph, app = setup
    params = {"scope": "run", "run_id": str(RUN), "graph_version": "g1"}
    assert (
        client.get(
            "/api/v1/explorer/nodes/a", params={**params, "graph_version": "old"}
        ).status_code
        == 409
    )
    assert (
        client.get(
            "/api/v1/explorer/nodes/a", params={**params, "run_id": str(uuid4())}
        ).status_code
        == 404
    )
    ref = client.get("/api/v1/explorer/nodes/a", params=params).json()["context_ref"]
    import asyncio

    svc = ExplorerService(graph)
    assert asyncio.run(svc.validate_context_ref(ref, OWNER, CHAT)) == "a"
    for bad, owner, chat in [(ref + "x", OWNER, CHAT), (ref, OTHER, CHAT), (ref, OWNER, uuid4())]:
        with pytest.raises(HTTPException):
            asyncio.run(svc.validate_context_ref(bad, owner, chat))
    expired = _encode(
        {
            "kind": "node",
            "scope": GraphScope(owner=OWNER, scope=Scope.RUN, run_id=RUN, version="g1").model_dump(
                mode="json"
            ),
            "node": "a",
            "exp": 1,
        }
    )
    with pytest.raises(HTTPException):
        asyncio.run(svc.validate_context_ref(expired, OWNER, CHAT))
    del graph.nodes["a"]
    with pytest.raises(HTTPException):
        asyncio.run(svc.validate_context_ref(ref, OWNER, CHAT))
    app.state.explorer_port = None
    assert client.get("/api/v1/explorer/nodes/a", params=params).status_code == 503
    app.dependency_overrides[require_owner] = lambda: (_ for _ in ()).throw(
        HTTPException(401, "UNAUTHENTICATED")
    )
    assert client.get("/api/v1/explorer/nodes/a", params=params).status_code == 401


def test_rejects_private_nodes_and_bad_adapter_subgraphs(setup):
    client, graph, _ = setup
    params = {"scope": "published", "graph_version": "g1"}
    graph.nodes["private"] = ExplorerNode(id="private", type="Idea", label="private")
    assert client.get("/api/v1/explorer/nodes/private", params=params).status_code == 503
    assert (
        client.get("/api/v1/explorer/search", params={**params, "q": "private"}).status_code == 503
    )

    async def wrong_neighbors(scope, node_id, edge_type, offset, limit):
        return SubgraphPage(
            nodes=[graph.nodes["a"], graph.nodes["b"], graph.nodes["c"]],
            edges=[graph.edges[1]],
            more=False,
        )

    graph.neighbors = wrong_neighbors
    assert client.get("/api/v1/explorer/nodes/b/neighbors", params=params).status_code == 503
    assert (
        client.get(
            "/api/v1/explorer/nodes/a/neighbors",
            params={**params, "edge_type": "DISCLOSES_FEATURE"},
        ).status_code
        == 503
    )

    async def wrong_paths(scope, source, target, edge_type, max_hops, max_visits, max_edges):
        assert (max_hops, max_visits, max_edges) == (1, 100, 40)
        return SubgraphPage(
            nodes=[graph.nodes["a"], graph.nodes["b"], graph.nodes["c"]],
            edges=graph.edges,
            more=False,
        )

    graph.paths = wrong_paths
    assert (
        client.get(
            "/api/v1/explorer/paths", params={**params, "source": "b", "target": "c", "max_hops": 1}
        ).status_code
        == 503
    )


def test_adapter_failure_does_not_leak_details(setup):
    client, graph, _ = setup

    async def fail(*args, **kwargs):
        raise RuntimeError("secret database address")

    graph.resolve = fail
    response = client.get("/api/v1/explorer/search", params={"scope": "published", "q": "x"})
    assert response.status_code == 503
    assert "secret database address" not in response.text


def test_cursor_owner_filter_and_invalid_provenance(setup):
    client, graph, app = setup
    params = {"scope": "published", "graph_version": "g1", "limit": 1}
    cursor = client.get("/api/v1/explorer/nodes/a/neighbors", params=params).json()["next_cursor"]
    assert (
        client.get(
            "/api/v1/explorer/nodes/a/neighbors",
            params={**params, "cursor": cursor, "edge_type": "SIMILAR_TO"},
        ).status_code
        == 400
    )
    app.dependency_overrides[require_owner] = lambda: Principal(OTHER, uuid4(), "csrf")
    assert (
        client.get(
            "/api/v1/explorer/nodes/a/neighbors", params={**params, "cursor": cursor}
        ).status_code
        == 400
    )
    assert (
        client.get(
            "/api/v1/explorer/nodes/a", params={**params, "scope": "run", "run_id": str(RUN)}
        ).status_code
        == 404
    )
    app.dependency_overrides[require_owner] = lambda: Principal(OWNER, uuid4(), "csrf")
    graph.src = graph.src.model_copy(update={"revision_id": uuid4()})
    assert (
        client.get("/api/v1/explorer/search", params={"scope": "published", "q": "a"}).status_code
        == 503
    )


def test_no_port_is_controlled_degradation(setup):
    client, _, app = setup
    app.state.explorer_port = None
    response = client.get("/api/v1/explorer/search", params={"scope": "published", "q": "x"})
    assert response.status_code == 503 and "GRAPH_UNAVAILABLE" in response.text


def test_port_timeout_is_controlled(setup):
    import asyncio

    client, graph, _ = setup

    async def slow(*args, **kwargs):
        await asyncio.sleep(10)
        return "g1"

    graph.resolve = slow
    response = client.get("/api/v1/explorer/search", params={"scope": "published", "q": "x"})
    assert response.status_code == 503 and "GRAPH_UNAVAILABLE" in response.text


@pytest.mark.parametrize(
    ("edge_type", "kind", "evidence_ids"),
    [
        ("DISCLOSES_FEATURE", "semantic", []),
        ("USES_TECHNOLOGY", "semantic", []),
        ("MATCHES", "semantic", []),
        ("CITES", "factual", []),
        ("RELATED_TO", "factual", [EID]),
        ("SIMILAR_TO", "factual", [EID]),
        ("HAS_SHARED_CONCEPT", "factual", [EID]),
        ("SIMILAR_TO", "semantic", [EID]),
    ],
)
def test_rejects_incorrect_edge_type_kind_and_provenance(setup, edge_type, kind, evidence_ids):
    client, graph, _ = setup
    edge = ExplorerEdge(
        id="bad", source="a", target="b", type=edge_type, kind=kind, evidence_ids=evidence_ids
    )

    async def invalid_neighbors(scope, node_id, edge_type, offset, limit):
        return SubgraphPage(nodes=[graph.nodes["a"], graph.nodes["b"]], edges=[edge], more=False)

    graph.neighbors = invalid_neighbors
    response = client.get(
        "/api/v1/explorer/nodes/a/neighbors",
        params={"scope": "published", "graph_version": "g1", "limit": 1},
    )
    assert response.status_code == 503


@pytest.mark.parametrize("case", ["extra_node", "duplicate_node", "duplicate_edge"])
def test_rejects_unrelated_or_duplicate_neighbors(setup, case):
    client, graph, _ = setup

    async def invalid_neighbors(scope, node_id, edge_type, offset, limit):
        nodes = [graph.nodes["a"], graph.nodes["b"]]
        edges = [graph.edges[0]]
        if case == "extra_node":
            nodes.append(graph.nodes["c"])
        elif case == "duplicate_node":
            nodes.append(graph.nodes["b"])
        else:
            edges.append(graph.edges[0])
        return SubgraphPage(nodes=nodes, edges=edges, more=False)

    graph.neighbors = invalid_neighbors
    assert (
        client.get(
            "/api/v1/explorer/nodes/a/neighbors",
            params={"scope": "published", "graph_version": "g1", "limit": 2},
        ).status_code
        == 503
    )


def test_synthetic_has_feature_only_as_run_navigation(setup):
    client, graph, _ = setup
    idea = ExplorerNode(id="idea", type="Idea", label="idea")
    feature = ExplorerNode(id="feature", type="IdeaFeature", label="feature")
    synthetic = ExplorerEdge(
        id="h", source="idea", target="feature", type="HAS_FEATURE", kind="semantic"
    )

    async def page(scope, node_id, edge_type, offset, limit):
        return SubgraphPage(nodes=[idea, feature], edges=[synthetic], more=False)

    graph.neighbors = page
    run = {"scope": "run", "run_id": str(RUN), "graph_version": "g1"}
    assert client.get("/api/v1/explorer/nodes/idea/neighbors", params=run).status_code == 200
    assert (
        client.get(
            "/api/v1/explorer/nodes/idea/neighbors",
            params={"scope": "published", "graph_version": "g1"},
        ).status_code
        == 503
    )
    synthetic.kind = "factual"
    assert client.get("/api/v1/explorer/nodes/idea/neighbors", params=run).status_code == 503
    synthetic.kind = "semantic"
    synthetic.source, synthetic.target = "feature", "idea"
    assert client.get("/api/v1/explorer/nodes/idea/neighbors", params=run).status_code == 503


def test_first_search_pins_run_but_cursor_requires_version(setup):
    client, _, _ = setup
    params = {"scope": "run", "run_id": str(RUN), "q": "a", "limit": 1}
    first = client.get("/api/v1/explorer/search", params=params)
    assert first.status_code == 200 and first.json()["graph_version"] == "g1"
    cursor = first.json()["next_cursor"]
    assert cursor
    assert (
        client.get("/api/v1/explorer/search", params={**params, "cursor": cursor}).status_code
        == 422
    )
    assert (
        client.get(
            "/api/v1/explorer/search", params={**params, "cursor": cursor, "graph_version": "g1"}
        ).status_code
        == 200
    )
    assert (
        client.get("/api/v1/explorer/search", params={**params, "run_id": str(uuid4())}).status_code
        == 404
    )
    published = client.get(
        "/api/v1/explorer/search", params={"scope": "published", "q": "a", "limit": 1}
    ).json()
    assert (
        client.get(
            "/api/v1/explorer/search",
            params={"scope": "published", "q": "a", "limit": 1, "cursor": published["next_cursor"]},
        ).status_code
        == 422
    )
