"""Защищённый API самостоятельного просмотра графа."""

from typing import Annotated, Any
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Path, Query, Request

from app.api.auth import require_owner
from app.domain.contracts import EvidenceV1
from app.domain.explorer import (
    EdgeType,
    ExplorerDocumentResponse,
    ExplorerGraphResponse,
    ExplorerNodeResponse,
    ExplorerSearchResponse,
    Scope,
)
from app.services.auth import Principal
from app.services.explorer import ExplorerService, _call

router = APIRouter(prefix="/api/v1/explorer", tags=["explorer"])
Owner = Annotated[Principal, Depends(require_owner)]


def service(request: Request) -> ExplorerService:
    port = getattr(request.app.state, "explorer_port", None)
    if port is None:
        raise HTTPException(503, "GRAPH_UNAVAILABLE")
    return ExplorerService(port)


Service = Annotated[ExplorerService, Depends(service)]
Version = Annotated[str | None, Query(max_length=256)]
Cursor = Annotated[str | None, Query(max_length=4096)]
Limit = Annotated[int, Query(ge=1, le=20)]
NodeId = Annotated[str, Query(min_length=1, max_length=512)]


@router.get("/search", response_model=ExplorerSearchResponse)
async def search(
    owner: Owner,
    svc: Service,
    scope: Scope,
    q: Annotated[str, Query(max_length=512)] = "",
    graph_version: Version = None,
    run_id: UUID | None = None,
    limit: Limit = 20,
    cursor: Cursor = None,
) -> dict[str, Any]:
    view = await svc.scope(owner.user_id, scope, run_id, graph_version, first=cursor is None)
    args = {"q": q, "limit": limit}
    offset = svc.cursor(cursor, view, "search", args)
    if not q.strip():
        return {
            "graph_version": view.version,
            "nodes": [],
            "documents": [],
            "next_cursor": None,
            "truncated": False,
        }
    page = await _call(svc.port.search(view, q, offset, limit))
    if len(page.nodes) + len(page.documents) > limit:
        raise HTTPException(503, "GRAPH_UNAVAILABLE")
    await svc.check_nodes_and_sources(view, page.nodes, page.documents)
    size = len(page.nodes) + len(page.documents)
    if page.more and not size:
        raise HTTPException(503, "GRAPH_UNAVAILABLE")
    return {
        "graph_version": view.version,
        "nodes": page.nodes,
        "documents": page.documents,
        "next_cursor": svc.next_cursor(view, "search", args, offset + size, page.more),
        "truncated": page.more,
    }


@router.get("/nodes/{node_id}", response_model=ExplorerNodeResponse)
async def node(
    node_id: Annotated[str, Path(min_length=1, max_length=512)],
    owner: Owner,
    svc: Service,
    scope: Scope,
    graph_version: Version = None,
    run_id: UUID | None = None,
) -> dict[str, Any]:
    view = await svc.scope(owner.user_id, scope, run_id, graph_version)
    item = await _call(svc.port.node(view, node_id))
    if item is None:
        raise HTTPException(404, "NOT_FOUND")
    if item.id != node_id:
        raise HTTPException(503, "GRAPH_UNAVAILABLE")
    await svc.check_nodes_and_sources(view, [item], [])
    return {
        "graph_version": view.version,
        "node": item,
        "context_ref": svc.context_ref(view, node_id),
    }


@router.get("/nodes/{node_id}/neighbors", response_model=ExplorerGraphResponse)
async def neighbors(
    node_id: Annotated[str, Path(min_length=1, max_length=512)],
    owner: Owner,
    svc: Service,
    scope: Scope,
    graph_version: Version = None,
    run_id: UUID | None = None,
    limit: Limit = 20,
    cursor: Cursor = None,
    edge_type: EdgeType | None = None,
) -> dict[str, Any]:
    view = await svc.scope(owner.user_id, scope, run_id, graph_version)
    args = {"node": node_id, "limit": limit, "edge_type": edge_type}
    offset = svc.cursor(cursor, view, "neighbors", args)
    page = await _call(svc.port.neighbors(view, node_id, edge_type, offset, limit))
    if page is None:
        raise HTTPException(404, "NOT_FOUND")
    await svc.check_graph(view, page)
    expected_nodes = (
        {node_id} | {edge.source for edge in page.edges} | {edge.target for edge in page.edges}
    )
    if (
        len(page.edges) > limit
        or (page.more and not page.edges)
        or {node.id for node in page.nodes} != expected_nodes
        or any(
            node_id not in (edge.source, edge.target) or (edge_type and edge.type != edge_type)
            for edge in page.edges
        )
    ):
        raise HTTPException(503, "GRAPH_UNAVAILABLE")
    return {
        "graph_version": view.version,
        "nodes": page.nodes,
        "edges": page.edges,
        "next_cursor": svc.next_cursor(
            view, "neighbors", args, offset + len(page.edges), page.more
        ),
        "truncated": page.more,
    }


@router.get("/paths", response_model=ExplorerGraphResponse)
async def paths(
    owner: Owner,
    svc: Service,
    scope: Scope,
    source: NodeId,
    target: NodeId,
    graph_version: Version = None,
    run_id: UUID | None = None,
    max_hops: Annotated[int, Query(ge=1, le=3)] = 3,
    edge_type: EdgeType | None = None,
) -> dict[str, Any]:
    view = await svc.scope(owner.user_id, scope, run_id, graph_version)
    page = await _call(svc.port.paths(view, source, target, edge_type, max_hops, 100, 40))
    if page is None:
        raise HTTPException(404, "NOT_FOUND")
    await svc.check_graph(view, page)
    current = source
    seen = {source}
    for edge in page.edges:
        if edge_type and edge.type != edge_type:
            raise HTTPException(503, "GRAPH_UNAVAILABLE")
        if current not in (edge.source, edge.target):
            raise HTTPException(503, "GRAPH_UNAVAILABLE")
        current = edge.target if current == edge.source else edge.source
        if current in seen:
            raise HTTPException(503, "GRAPH_UNAVAILABLE")
        seen.add(current)
    if len(page.edges) > max_hops or (page.edges and current != target):
        raise HTTPException(503, "GRAPH_UNAVAILABLE")
    if page.edges and {node.id for node in page.nodes} != seen:
        raise HTTPException(503, "GRAPH_UNAVAILABLE")
    if (
        not page.edges
        and page.nodes
        and not (source == target and {node.id for node in page.nodes} == {source})
    ):
        raise HTTPException(503, "GRAPH_UNAVAILABLE")
    return {
        "graph_version": view.version,
        "nodes": page.nodes,
        "edges": page.edges,
        "next_cursor": None,
        "truncated": page.more,
    }


@router.get("/documents/{document_id}", response_model=ExplorerDocumentResponse)
async def document(
    document_id: UUID,
    owner: Owner,
    svc: Service,
    scope: Scope,
    revision_id: UUID,
    graph_version: Version = None,
    run_id: UUID | None = None,
) -> dict[str, Any]:
    view = await svc.scope(owner.user_id, scope, run_id, graph_version)
    item = await _call(svc.port.document(view, document_id, revision_id))
    if item is None:
        raise HTTPException(404, "NOT_FOUND")
    if (
        item.source.document_id != document_id
        or item.source.revision_id != revision_id
        or len(item.nodes) > 20
    ):
        raise HTTPException(503, "GRAPH_UNAVAILABLE")
    await svc.check_nodes_and_sources(view, item.nodes, [item.source])
    return {"graph_version": view.version, "source": item.source, "nodes": item.nodes}


@router.get("/evidence/{evidence_id}", response_model=EvidenceV1)
async def evidence(
    evidence_id: UUID,
    owner: Owner,
    svc: Service,
    scope: Scope,
    graph_version: Version = None,
    run_id: UUID | None = None,
) -> EvidenceV1:
    view = await svc.scope(owner.user_id, scope, run_id, graph_version)
    item = await _call(svc.port.evidence(view, evidence_id))
    if item is None:
        raise HTTPException(404, "NOT_FOUND")
    if (
        item.evidence_id != evidence_id
        or item.span_end <= item.span_start
        or len(item.quoted_span) != item.span_end - item.span_start
    ):
        raise HTTPException(503, "GRAPH_UNAVAILABLE")
    svc.check_url(item.source_url)
    return item
