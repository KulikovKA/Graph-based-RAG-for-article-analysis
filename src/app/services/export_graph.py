"""Проверка и автономное отображение сохранённой проекции графа run."""

from html import escape
from math import atan2, cos, pi, sin
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


def edge_kind(edge: GraphEdge) -> str:
    if edge.type in {"RELATED_TO", "SIMILAR_TO", "HAS_SHARED_CONCEPT"}:
        return "semantic"
    if edge.type == "HAS_FEATURE":
        return "structural"
    if edge.type == "MATCHES":
        return "analytical"
    return "factual"


EDGE_STYLES = {
    "factual": ("#235b8e", ""),
    "semantic": ("#a26400", "7 4"),
    "structural": ("#68747d", "2 4"),
    "analytical": ("#814d8c", "9 3 2 3"),
}
NODE_STYLES = {
    "Idea": ("И", "#f5d88d"),
    "IdeaFeature": ("ИП", "#f8ebbd"),
    "Patent": ("П", "#a7d4f2"),
    "ScientificWork": ("С", "#c7def4"),
    "TechnicalFeature": ("ТП", "#bfe4cc"),
    "Technology": ("Т", "#95d1b4"),
    "Classification": ("К", "#d9c9ee"),
    "Applicant": ("З", "#f0c3b5"),
    "Inventor": ("ИЗ", "#eeb8cd"),
    "Author": ("А", "#d0d5dc"),
}
GRAPH_LEGEND = (
    "Сплошная синяя — факт с evidence; оранжевая пунктирная — семантическая связь "
    "без evidence; серая точечная — структура идеи; фиолетовая штрихпунктирная — "
    "аналитическое сопоставление MATCHES с evidence. Стрелка указывает направление. "
    "Совпадающие по направлению и категории связи объединены на схеме; "
    "все отдельные связи, типы и evidence приведены в списке. "
    "Номера вершин раскрыты ниже. Обозначения типов вершин: "
    "И — Idea; ИП — IdeaFeature; П — Patent; С — ScientificWork; ТП — TechnicalFeature; "
    "Т — Technology; К — Classification; З — Applicant; ИЗ — Inventor; А — Author."
)


def visible_edges(graph: ExportGraph) -> list[tuple[GraphEdge, int, int]]:
    # Для плотных повторов сохраняем направления и категории, а все факты — в списке.
    groups: dict[tuple[str, str, str], GraphEdge] = {}
    for edge in graph.edges:
        groups.setdefault((edge.source, edge.target, edge_kind(edge)), edge)
    pairs: dict[tuple[str, str], list[tuple[str, str, str]]] = {}
    for key in groups:
        pair = (min(key[0], key[1]), max(key[0], key[1]))
        pairs.setdefault(pair, []).append(key)
    result = []
    for keys in pairs.values():
        keys.sort()
        for lane, key in enumerate(keys):
            result.append((groups[key], lane, len(keys)))
    return result


def short_label(label: str) -> str:
    text = " ".join(label.split())
    return text if len(text) <= 17 else text[:16] + "…"


def graph_layout(graph: ExportGraph) -> tuple[dict[str, tuple[float, float]], int]:
    # Порядок snapshot фиксирует номера и геометрию при повторном экспорте.
    count = len(graph.nodes)
    if count == 1:
        return {graph.nodes[0].id: (450.0, 350.0)}, 700
    return (
        {
            node.id: (
                450 + 230 * cos(-pi / 2 + 2 * pi * i / count),
                350 + 230 * sin(-pi / 2 + 2 * pi * i / count),
            )
            for i, node in enumerate(graph.nodes)
        },
        700,
    )


def edge_curve(
    edge: GraphEdge, positions: dict[str, tuple[float, float]], lane: int, count: int
) -> tuple[float, float, float, float, float, float, float, float]:
    x1, y1 = positions[edge.source]
    x2, y2 = positions[edge.target]
    if edge.source == edge.target:
        angle = atan2(350 - y1, 450 - x1) if (x1, y1) != (450, 350) else -pi / 2
        ux, uy = cos(angle), sin(angle)
        nx, ny = -uy, ux
        reach = 55 + lane * 22
        return (
            x1 + 22 * nx,
            y1 + 22 * ny,
            x1 + reach * ux + 40 * nx,
            y1 + reach * uy + 40 * ny,
            x1 + reach * ux - 40 * nx,
            y1 + reach * uy - 40 * ny,
            x1 - 22 * nx,
            y1 - 22 * ny,
        )
    angle = atan2(y2 - y1, x2 - x1)
    ux, uy = cos(angle), sin(angle)
    sx, sy, tx, ty = x1 + 19 * ux, y1 + 19 * uy, x2 - 22 * ux, y2 - 22 * uy
    # Обратные рёбра используют общую систему отсчёта стороны пары.
    offset = (lane - (count - 1) / 2) * 32
    if edge.source > edge.target:
        offset = -offset
    return (
        sx,
        sy,
        sx + (tx - sx) / 3 - uy * offset,
        sy + (ty - sy) / 3 + ux * offset,
        sx + 2 * (tx - sx) / 3 - uy * offset,
        sy + 2 * (ty - sy) / 3 + ux * offset,
        tx,
        ty,
    )


def render_graph_html(graph: ExportGraph | None) -> str:
    if graph is None:
        return "<h2>Подграф исследования</h2><p>Сохранённая проекция подграфа отсутствует.</p>"

    def esc(value: object) -> str:
        return escape(str(value), quote=True)

    numbers = {node.id: i + 1 for i, node in enumerate(graph.nodes)}
    positions, height = graph_layout(graph)
    output = [
        "<h2>Подграф исследования</h2><p>Версия: ",
        esc(graph.graph_version),
        "; усечён: ",
        "да" if graph.truncated else "нет",
        ".</p><p>",
        GRAPH_LEGEND,
        "</p>",
    ]
    if graph.nodes:
        output.append(
            '<svg xmlns="http://www.w3.org/2000/svg" role="img" '
            f'aria-label="Схема подграфа" width="900" height="{height}" '
            f'viewBox="0 0 900 {height}" style="max-width:100%;height:auto">'
        )
        for i, (edge, lane, count) in enumerate(visible_edges(graph)):
            x1, y1, c1x, c1y, c2x, c2y, x2, y2 = edge_curve(edge, positions, lane, count)
            color, dash = EDGE_STYLES[edge_kind(edge)]
            angle = atan2(y2 - c2y, x2 - c2x)
            ax1, ay1 = x2 - 10 * cos(angle - 0.45), y2 - 10 * sin(angle - 0.45)
            ax2, ay2 = x2 - 10 * cos(angle + 0.45), y2 - 10 * sin(angle + 0.45)
            output.append(
                f'<path data-edge="{i + 1}" d="M{x1:.1f},{y1:.1f} C{c1x:.1f},{c1y:.1f} '
                f'{c2x:.1f},{c2y:.1f} {x2:.1f},{y2:.1f}" fill="none" '
                f'stroke="{color}" stroke-width="2" stroke-dasharray="{dash}"/>'
            )
            output.append(
                f'<path d="M{ax1:.1f},{ay1:.1f} L{x2:.1f},{y2:.1f} '
                f'L{ax2:.1f},{ay2:.1f}" fill="none" stroke="{color}" stroke-width="2"/>'
            )
        for i, node in enumerate(graph.nodes):
            x, y = positions[node.id]
            code, fill = NODE_STYLES[node.type]
            output.append(
                f'<g data-node="{i + 1}"><circle cx="{x}" cy="{y}" r="19" '
                f'fill="{fill}" stroke="#31526b" stroke-width="2"/>'
                f'<text x="{x}" y="{y - 1}" text-anchor="middle" font-size="12">'
                f'{esc(code)}</text><text x="{x}" y="{y + 13}" text-anchor="middle" '
                f'font-size="12">{i + 1}</text></g>'
            )
            if len(graph.nodes) <= 10:
                anchor = "end" if x < 450 else "start"
                label_x = x - 25 if x < 450 else x + 25
                output.append(
                    f'<text x="{label_x}" y="{y + 5}" text-anchor="{anchor}" '
                    f'font-size="15">{esc(short_label(node.label))}</text>'
                )
        output.append("</svg>")
    else:
        output.append("<p>Сохранённый подграф пуст.</p>")
    output.append('<h3>Связи подграфа</h3><ul aria-label="Связи подграфа">')
    for i, edge in enumerate(graph.edges):
        kind = {
            "factual": "факт",
            "semantic": "семантическая",
            "structural": "структурная",
            "analytical": "аналитическая",
        }[edge_kind(edge)]
        output.extend(
            [
                "<li>Связь ",
                str(i + 1),
                ": ",
                esc(numbers[edge.source]),
                " → ",
                esc(numbers[edge.target]),
                ": <code>",
                esc(edge.type),
                "</code> (",
                kind,
                "; evidence: ",
                esc(", ".join(map(str, edge.evidence_ids)) or "нет"),
                ")</li>",
            ]
        )
    output.append('</ul><h3>Узлы</h3><ul aria-label="Узлы подграфа">')
    for i, node in enumerate(graph.nodes):
        output.extend(
            [
                "<li>Узел ",
                str(i + 1),
                ": ",
                esc(node.label),
                " (тип: ",
                esc(node.type),
                "; id: ",
                esc(node.id),
                "; документ: ",
                esc(node.document_id or "нет"),
                "; ревизия: ",
                esc(node.revision_id or "нет"),
                "; feature: ",
                esc(node.feature_id or "нет"),
                "; evidence: ",
                esc(", ".join(map(str, node.evidence_ids)) or "нет"),
                ")</li>",
            ]
        )
    output.append("</ul>")
    return "".join(output)
