"""Контракты самостоятельного Explorer и ограниченного порта графа."""

from enum import StrEnum
from typing import Literal, Protocol
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

from app.domain.contracts import EvidenceV1, SourceV1


class Scope(StrEnum):
    PUBLISHED = "published"
    RUN = "run"


EdgeType = Literal[
    "HAS_FEATURE",
    "MATCHES",
    "DISCLOSES_FEATURE",
    "USES_TECHNOLOGY",
    "CLASSIFIED_AS",
    "CITES",
    "APPLIED_BY",
    "INVENTED_BY",
    "AUTHORED_BY",
    "RELATED_TO",
    "SIMILAR_TO",
    "HAS_SHARED_CONCEPT",
]


class ExplorerNode(BaseModel):
    model_config = ConfigDict(extra="forbid")
    id: str = Field(min_length=1, max_length=512)
    type: Literal[
        "Idea",
        "IdeaFeature",
        "Patent",
        "ScientificWork",
        "TechnicalFeature",
        "Technology",
        "Classification",
        "Applicant",
        "Inventor",
        "Author",
    ]
    label: str = Field(max_length=512)
    document_id: UUID | None = None
    revision_id: UUID | None = None
    feature_id: str | None = None
    evidence_ids: list[UUID] = Field(default_factory=list)


class ExplorerEdge(BaseModel):
    model_config = ConfigDict(extra="forbid")
    id: str = Field(min_length=1, max_length=512)
    source: str
    target: str
    type: EdgeType
    kind: Literal["factual", "semantic"]
    evidence_ids: list[UUID] = Field(default_factory=list)


class GraphScope(BaseModel):
    owner: UUID
    scope: Scope
    run_id: UUID | None
    version: str


class SearchPage(BaseModel):
    nodes: list[ExplorerNode]
    documents: list[SourceV1]
    more: bool


class SubgraphPage(BaseModel):
    nodes: list[ExplorerNode]
    edges: list[ExplorerEdge]
    more: bool


class DocumentView(BaseModel):
    source: SourceV1
    nodes: list[ExplorerNode]


class ExplorerSearchResponse(BaseModel):
    graph_version: str
    nodes: list[ExplorerNode]
    documents: list[SourceV1]
    next_cursor: str | None
    truncated: bool


class ExplorerNodeResponse(BaseModel):
    graph_version: str
    node: ExplorerNode
    context_ref: str


class ExplorerGraphResponse(BaseModel):
    graph_version: str
    nodes: list[ExplorerNode]
    edges: list[ExplorerEdge]
    next_cursor: str | None
    truncated: bool


class ExplorerDocumentResponse(BaseModel):
    graph_version: str
    source: SourceV1
    nodes: list[ExplorerNode]


class ExplorerPort(Protocol):
    """Адаптер обязан проверять membership, offsets и доступ до возврата DTO.

    Страницы ограничены limit; traversal — 100 посещений и 40 рёбер.
    Адаптер не принимает произвольные запросы к хранилищу.
    """

    async def resolve(self, owner: UUID, scope: Scope, run_id: UUID | None) -> str | None: ...
    async def search(self, scope: GraphScope, q: str, offset: int, limit: int) -> SearchPage: ...
    async def node(self, scope: GraphScope, node_id: str) -> ExplorerNode | None: ...
    async def neighbors(
        self, scope: GraphScope, node_id: str, edge_type: str | None, offset: int, limit: int
    ) -> SubgraphPage | None: ...
    async def paths(
        self,
        scope: GraphScope,
        source: str,
        target: str,
        edge_type: str | None,
        max_hops: int,
        max_visits: int,
        max_edges: int,
    ) -> SubgraphPage | None: ...
    async def document(
        self, scope: GraphScope, document_id: UUID, revision_id: UUID
    ) -> DocumentView | None: ...
    async def evidence(self, scope: GraphScope, evidence_id: UUID) -> EvidenceV1 | None: ...
    async def conversation_allowed(
        self, owner: UUID, conversation_id: UUID, run_id: UUID | None
    ) -> bool: ...
