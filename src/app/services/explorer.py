"""Авторизация и ограниченные операции Explorer поверх внедрённого порта."""

import asyncio
import base64
import binascii
import hashlib
import hmac
import json
import os
import secrets
import time
from collections.abc import Awaitable
from typing import Any, TypeVar
from uuid import UUID

from fastapi import HTTPException

from app.api.projections import source_url
from app.domain.contracts import SourceV1
from app.domain.explorer import ExplorerNode, ExplorerPort, GraphScope, Scope, SubgraphPage

T = TypeVar("T")
_PROCESS_KEY = secrets.token_bytes(32)
_SEMANTIC_EDGE_TYPES = frozenset({"SIMILAR_TO", "HAS_SHARED_CONCEPT", "RELATED_TO"})


def _key() -> bytes:
    value = os.getenv("AUTH_SESSION_SECRET")
    return value.encode() if value else _PROCESS_KEY


def _encode(data: dict[str, Any]) -> str:
    raw = json.dumps(data, sort_keys=True, separators=(",", ":")).encode()
    signature = hmac.new(_key(), raw, hashlib.sha256).digest()
    return (
        base64.urlsafe_b64encode(raw).decode().rstrip("=")
        + "."
        + base64.urlsafe_b64encode(signature).decode().rstrip("=")
    )


def _decode(token: str, error: str) -> dict[str, Any]:
    try:
        if len(token) > 4096:
            raise ValueError
        body, sig = token.split(".")
        raw = base64.urlsafe_b64decode(body + "=" * (-len(body) % 4))
        signature = base64.urlsafe_b64decode(sig + "=" * (-len(sig) % 4))
        if (
            base64.urlsafe_b64encode(raw).decode().rstrip("=") != body
            or base64.urlsafe_b64encode(signature).decode().rstrip("=") != sig
        ):
            raise ValueError
        if not hmac.compare_digest(signature, hmac.new(_key(), raw, hashlib.sha256).digest()):
            raise ValueError
        value = json.loads(raw)
        if not isinstance(value, dict):
            raise ValueError
        return value
    except (ValueError, TypeError, binascii.Error, UnicodeDecodeError):
        raise HTTPException(400, error) from None


async def _call(call: Awaitable[T]) -> T:
    try:
        return await asyncio.wait_for(call, timeout=2)
    except Exception:
        raise HTTPException(503, "GRAPH_UNAVAILABLE") from None


class ExplorerService:
    def __init__(self, port: ExplorerPort) -> None:
        self.port = port

    async def scope(
        self,
        owner: UUID,
        scope: Scope,
        run_id: UUID | None,
        version: str | None,
        *,
        first: bool = False,
    ) -> GraphScope:
        if (scope == Scope.RUN) != (run_id is not None):
            raise HTTPException(422, "INVALID_SCOPE")
        if version is None and not first:
            raise HTTPException(422, "GRAPH_VERSION_REQUIRED")
        current = await _call(self.port.resolve(owner, scope, run_id))
        if current is None:
            raise HTTPException(404, "NOT_FOUND")
        if version is not None and version != current:
            raise HTTPException(409, "GRAPH_VERSION_CONFLICT")
        return GraphScope(owner=owner, scope=scope, run_id=run_id, version=current)

    def cursor(
        self, token: str | None, scope: GraphScope, operation: str, args: dict[str, Any]
    ) -> int:
        if token is None:
            return 0
        data = _decode(token, "INVALID_CURSOR")
        offset = data.pop("offset", None)
        if (
            data != {"scope": scope.model_dump(mode="json"), "operation": operation, "args": args}
            or type(offset) is not int
            or offset < 0
        ):
            raise HTTPException(400, "INVALID_CURSOR")
        return offset

    def next_cursor(
        self, scope: GraphScope, operation: str, args: dict[str, Any], offset: int, more: bool
    ) -> str | None:
        if not more:
            return None
        return _encode(
            {
                "scope": scope.model_dump(mode="json"),
                "operation": operation,
                "args": args,
                "offset": offset,
            }
        )

    def context_ref(self, scope: GraphScope, node_id: str) -> str:
        return _encode(
            {
                "kind": "node",
                "scope": scope.model_dump(mode="json"),
                "node": node_id,
                "exp": int(time.time()) + 900,
            }
        )

    async def validate_context_ref(self, token: str, owner: UUID, conversation_id: UUID) -> str:
        data = _decode(token, "INVALID_CONTEXT_REF")
        try:
            if (
                set(data) != {"kind", "scope", "node", "exp"}
                or data["kind"] != "node"
                or type(data["exp"]) is not int
                or data["exp"] <= int(time.time())
                or not isinstance(data["node"], str)
            ):
                raise ValueError
            saved = GraphScope.model_validate(data["scope"])
            if saved.owner != owner:
                raise ValueError
        except Exception:
            raise HTTPException(400, "INVALID_CONTEXT_REF") from None
        scope = await self.scope(owner, saved.scope, saved.run_id, saved.version)
        if not await _call(self.port.conversation_allowed(owner, conversation_id, scope.run_id)):
            raise HTTPException(404, "NOT_FOUND")
        node = await _call(self.port.node(scope, data["node"]))
        if node is None or node.id != data["node"]:
            raise HTTPException(404, "NOT_FOUND")
        await self.check_nodes_and_sources(scope, [node], [])
        return data["node"]

    async def check_evidence(
        self,
        scope: GraphScope,
        ids: list[UUID],
        document_id: UUID | None = None,
        revision_id: UUID | None = None,
        bindings: dict[UUID, tuple[UUID, UUID]] | None = None,
    ) -> None:
        if len(ids) > 40:
            raise HTTPException(503, "GRAPH_UNAVAILABLE")

        async def fetch() -> list[Any]:
            return list(await asyncio.gather(*(self.port.evidence(scope, eid) for eid in ids)))

        records = await _call(fetch())
        for eid, item in zip(ids, records, strict=True):
            if (
                item is None
                or item.evidence_id != eid
                or item.span_end <= item.span_start
                or len(item.quoted_span) != item.span_end - item.span_start
                or (document_id is not None and item.document_id != document_id)
                or (revision_id is not None and item.revision_id != revision_id)
                or (
                    bindings is not None
                    and eid in bindings
                    and (item.document_id, item.revision_id) != bindings[eid]
                )
            ):
                raise HTTPException(503, "GRAPH_UNAVAILABLE")
            self.check_url(item.source_url)

    async def check_nodes_and_sources(
        self,
        scope: GraphScope,
        nodes: list[ExplorerNode],
        sources: list[SourceV1],
        extra_evidence: set[UUID] | None = None,
    ) -> None:
        ids = set(extra_evidence or ())
        if len(ids) > 40:
            raise HTTPException(503, "GRAPH_UNAVAILABLE")
        bindings: dict[UUID, tuple[UUID, UUID]] = {}
        for node in nodes:
            if scope.scope == Scope.PUBLISHED and node.type in {"Idea", "IdeaFeature"}:
                raise HTTPException(503, "GRAPH_UNAVAILABLE")
            ids.update(node.evidence_ids)
            if len(ids) > 40:
                raise HTTPException(503, "GRAPH_UNAVAILABLE")
            if (node.document_id is None) != (node.revision_id is None):
                raise HTTPException(503, "GRAPH_UNAVAILABLE")
            if node.document_id is not None and node.revision_id is not None:
                for eid in node.evidence_ids:
                    pair = (node.document_id, node.revision_id)
                    if eid in bindings and bindings[eid] != pair:
                        raise HTTPException(503, "GRAPH_UNAVAILABLE")
                    bindings[eid] = pair
        for source in sources:
            self.check_url(source.url)
            for eid in source.evidence_ids:
                pair = (source.document_id, source.revision_id)
                if eid in bindings and bindings[eid] != pair:
                    raise HTTPException(503, "GRAPH_UNAVAILABLE")
                bindings[eid] = pair
                ids.add(eid)
                if len(ids) > 40:
                    raise HTTPException(503, "GRAPH_UNAVAILABLE")
        await self.check_evidence(scope, list(ids), bindings=bindings)

    async def check_graph(self, scope: GraphScope, page: SubgraphPage) -> None:
        if len(page.edges) > 40 or len(page.nodes) > 100:
            raise HTTPException(503, "GRAPH_UNAVAILABLE")
        node_ids = {node.id for node in page.nodes}
        if len(node_ids) != len(page.nodes) or len({edge.id for edge in page.edges}) != len(
            page.edges
        ):
            raise HTTPException(503, "GRAPH_UNAVAILABLE")
        nodes = {node.id: node for node in page.nodes}
        evidence_ids: set[UUID] = set()
        for edge in page.edges:
            # HAS_FEATURE — синтетическая связь ввода пользователя только в run,
            # отображается как навигация и не утверждает факт об источнике.
            synthetic = edge.type == "HAS_FEATURE"
            if (
                edge.source not in node_ids
                or edge.target not in node_ids
                or (edge.kind == "semantic" and edge.evidence_ids)
                or (edge.kind == "factual" and not edge.evidence_ids)
                or (edge.type in _SEMANTIC_EDGE_TYPES and edge.kind != "semantic")
                or (
                    edge.type not in _SEMANTIC_EDGE_TYPES
                    and not synthetic
                    and edge.kind != "factual"
                )
                or (
                    synthetic
                    and (
                        scope.scope != Scope.RUN
                        or edge.kind != "semantic"
                        or nodes[edge.source].type != "Idea"
                        or nodes[edge.target].type != "IdeaFeature"
                    )
                )
            ):
                raise HTTPException(503, "GRAPH_UNAVAILABLE")
            evidence_ids.update(edge.evidence_ids)
        await self.check_nodes_and_sources(scope, page.nodes, [], evidence_ids)

    @staticmethod
    def check_url(url: str) -> None:
        try:
            source_url(url)
        except Exception:
            raise HTTPException(503, "GRAPH_UNAVAILABLE") from None
