"""Проверка и автономное отображение сохранённой проекции графа run."""

from html import escape
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, model_validator

from app.domain.contracts import SourceV1
from app.domain.explorer import EdgeType
from app.storage.models import RunEvidence


class GraphNode(BaseModel):
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
    label: str = Field(max_length=240)
    document_id: UUID | None = None
    revision_id: UUID | None = None
    feature_id: str | None = Field(default=None, max_length=512)
    evidence_ids: list[UUID] = Field(default_factory=list, max_length=36)


class GraphEdge(BaseModel):
    model_config = ConfigDict(extra="forbid")
    id: str = Field(min_length=1, max_length=512)
    source: str = Field(min_length=1, max_length=512)
    target: str = Field(min_length=1, max_length=512)
    type: EdgeType
    evidence_ids: list[UUID] = Field(default_factory=list, max_length=36)


class ExportGraph(BaseModel):
    model_config = ConfigDict(extra="forbid")
    schema_version: Literal[1]
    run_id: UUID
    graph_version: str = Field(min_length=1, max_length=256)
    nodes: list[GraphNode] = Field(max_length=30)
    edges: list[GraphEdge] = Field(max_length=50)
    next_cursor: None = None
    truncated: bool

    @model_validator(mode="after")
    def validate_links(self) -> "ExportGraph":
        nodes = {node.id for node in self.nodes}
        if len(nodes) != len(self.nodes) or len({edge.id for edge in self.edges}) != len(
            self.edges
        ):
            raise ValueError("INVALID_GRAPH_SNAPSHOT")
        if any(edge.source not in nodes or edge.target not in nodes for edge in self.edges):
            raise ValueError("INVALID_GRAPH_SNAPSHOT")
        return self


def read_graph(
    raw: object, run_id: UUID, evidence: dict[UUID, RunEvidence], sources: list[SourceV1]
) -> ExportGraph | None:
    if raw is None:
        return None
    graph = ExportGraph.model_validate(raw)
    if graph.run_id != run_id:
        raise ValueError("INVALID_GRAPH_SNAPSHOT")
    if (graph.nodes or graph.edges) and not evidence:
        raise ValueError("INVALID_GRAPH_SNAPSHOT")
    source_revisions = {s.document_id: s.revision_id for s in sources}
    nodes = {node.id: node for node in graph.nodes}
    for node in graph.nodes:
        if (node.document_id is None) != (node.revision_id is None):
            raise ValueError("INVALID_GRAPH_SNAPSHOT")
        if node.type in {"Patent", "ScientificWork"} and node.document_id is None:
            raise ValueError("INVALID_GRAPH_SNAPSHOT")
        if (
            node.document_id is not None
            and source_revisions.get(node.document_id) != node.revision_id
        ):
            raise ValueError("INVALID_GRAPH_SNAPSHOT")
        for eid in node.evidence_ids:
            item = evidence.get(eid)
            if item is None or (
                node.document_id is not None and item.document_id != node.document_id
            ):
                raise ValueError("INVALID_GRAPH_SNAPSHOT")
    for edge in graph.edges:
        semantic = edge.type in {"RELATED_TO", "SIMILAR_TO", "HAS_SHARED_CONCEPT"}
        structural = edge.type == "HAS_FEATURE"
        if semantic and edge.evidence_ids:
            raise ValueError("INVALID_GRAPH_SNAPSHOT")
        if structural and (
            edge.evidence_ids
            or nodes[edge.source].type != "Idea"
            or nodes[edge.target].type != "IdeaFeature"
        ):
            raise ValueError("INVALID_GRAPH_SNAPSHOT")
        if not semantic and not structural and not edge.evidence_ids:
            raise ValueError("INVALID_GRAPH_SNAPSHOT")
        for eid in edge.evidence_ids:
            item = evidence.get(eid)
            docs = {
                n.document_id for n in (nodes[edge.source], nodes[edge.target]) if n.document_id
            }
            if item is None or (docs and item.document_id not in docs):
                raise ValueError("INVALID_GRAPH_SNAPSHOT")
    return graph


def render_graph_html(graph: ExportGraph | None) -> str:
    if graph is None:
        return "<h2>Подграф исследования</h2><p>Сохранённая проекция подграфа отсутствует.</p>"

    def esc(value: object) -> str:
        return escape(str(value), quote=True)

    nodes = {node.id: node for node in graph.nodes}
    output = [
        "<h2>Подграф исследования</h2><p>Версия: ",
        esc(graph.graph_version),
        "; усечён: ",
        "да" if graph.truncated else "нет",
        ". MATCHES — аналитическое сопоставление.</p>",
    ]
    if graph.edges:
        height = 48 * len(graph.edges)
        output.append(
            '<svg xmlns="http://www.w3.org/2000/svg" role="img" '
            f'aria-label="Связи подграфа" width="900" height="{height}" '
            f'viewBox="0 0 900 {height}">'
        )
        for index, edge in enumerate(graph.edges):
            y = 48 * index + 4
            left, right = nodes[edge.source].label[:35], nodes[edge.target].label[:35]
            output.extend(
                [
                    f'<rect x="2" y="{y}" width="300" height="38" '
                    'fill="#e8f2fa" stroke="#31526b"/>',
                    f'<text x="8" y="{y + 24}" font-size="14">{esc(left)}</text>',
                    f'<text x="310" y="{y + 24}" font-size="13">→ {esc(edge.type)} →</text>',
                    f'<rect x="590" y="{y}" width="300" height="38" '
                    'fill="#e8f2fa" stroke="#31526b"/>',
                    f'<text x="596" y="{y + 24}" font-size="14">{esc(right)}</text>',
                ]
            )
        output.append("</svg>")
    # Полные подписи и provenance доступны также в текстовой форме.
    output.append('<ol aria-label="Связи подграфа">')
    for edge in graph.edges:
        output.extend(
            [
                "<li><strong>",
                esc(nodes[edge.source].label),
                "</strong> → <code>",
                esc(edge.type),
                "</code> → <strong>",
                esc(nodes[edge.target].label),
                "</strong> (evidence: ",
                esc(", ".join(map(str, edge.evidence_ids)) or "нет"),
                ")</li>",
            ]
        )
    output.append("</ol><h3>Узлы</h3><ul>")
    for node in graph.nodes:
        output.extend(["<li>", esc(node.label), " (", esc(node.type), ", ", esc(node.id), ")</li>"])
    output.append("</ul>")
    return "".join(output)
