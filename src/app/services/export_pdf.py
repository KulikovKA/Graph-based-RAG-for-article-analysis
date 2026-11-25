"""Локальный PDF из уже проверенного отчёта, без внешних ресурсов."""

from html import escape
from html.parser import HTMLParser
from io import BytesIO
from math import atan2, cos, sin
from pathlib import Path
from typing import Any

from reportlab.lib import colors  # type: ignore[import-untyped]
from reportlab.lib.styles import ParagraphStyle  # type: ignore[import-untyped]
from reportlab.lib.units import mm  # type: ignore[import-untyped]
from reportlab.pdfbase import pdfmetrics  # type: ignore[import-untyped]
from reportlab.pdfbase.ttfonts import TTFont  # type: ignore[import-untyped]
from reportlab.platypus import (  # type: ignore[import-untyped]
    Flowable,
    Paragraph,
    SimpleDocTemplate,
    Spacer,
)
from reportlab.platypus.doctemplate import LayoutError  # type: ignore[import-untyped]

from app.services.export_graph import (
    EDGE_STYLES,
    NODE_STYLES,
    ExportGraph,
    edge_curve,
    edge_kind,
    graph_layout,
    short_label,
    visible_edges,
)


class _Text(HTMLParser):
    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.parts: list[str] = []
        self.lines: list[tuple[str, str]] = []
        self.hidden = 0
        self.style = "normal"
        self.link: str | None = None

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        if tag in {"head", "svg"}:
            self.hidden += 1
        if not self.hidden and tag in {"p", "li", "h1", "h2", "h3", "tr", "pre"}:
            self.flush()
            if tag in {"h1", "h2", "h3"}:
                self.style = tag
        elif not self.hidden and tag in {"td", "th"}:
            self.parts.append(" | ")
        elif not self.hidden and tag == "a":
            self.link = dict(attrs).get("href")

    def handle_endtag(self, tag: str) -> None:
        if tag in {"head", "svg"}:
            self.hidden -= 1
        elif not self.hidden and tag == "a" and self.link:
            self.parts.append(" (" + self.link + ")")
            self.link = None
        elif not self.hidden and tag in {"p", "li", "h1", "h2", "h3", "tr", "pre"}:
            self.flush()
            self.style = "normal"

    def handle_data(self, data: str) -> None:
        if not self.hidden:
            self.parts.append(data)

    def flush(self) -> None:
        text = " ".join("".join(self.parts).split()).strip(" |")
        if text:
            self.lines.append((text, self.style))
        self.parts.clear()


class _GraphDiagram(Flowable):  # type: ignore[misc]
    def __init__(self, graph: ExportGraph, font: str) -> None:
        super().__init__()
        self.graph, self.font = graph, font
        self.positions, height = graph_layout(graph)
        self.scale = min(174 * mm / 900, 200 * mm / height)
        self.width, self.height = 900 * self.scale, height * self.scale

    def draw(self) -> None:
        canvas = self.canv
        scale = self.scale
        canvas.saveState()
        canvas.scale(scale, scale)
        canvas.translate(0, self.height / scale)
        canvas.scale(1, -1)
        for edge, lane, count in visible_edges(self.graph):
            x1, y1, c1x, c1y, c2x, c2y, x2, y2 = edge_curve(edge, self.positions, lane, count)
            color, dash = EDGE_STYLES[edge_kind(edge)]
            canvas.setStrokeColor(colors.HexColor(color))
            canvas.setLineWidth(2)
            canvas.setDash([int(x) for x in dash.split()] if dash else [])
            path = canvas.beginPath()
            path.moveTo(x1, y1)
            path.curveTo(c1x, c1y, c2x, c2y, x2, y2)
            canvas.drawPath(path)
            canvas.setDash([])
            angle = atan2(y2 - c2y, x2 - c2x)
            canvas.line(x2, y2, x2 - 10 * cos(angle - 0.45), y2 - 10 * sin(angle - 0.45))
            canvas.line(x2, y2, x2 - 10 * cos(angle + 0.45), y2 - 10 * sin(angle + 0.45))
        for i, node in enumerate(self.graph.nodes):
            x, y = self.positions[node.id]
            code, fill = NODE_STYLES[node.type]
            canvas.setFillColor(colors.HexColor(fill))
            canvas.setStrokeColor(colors.HexColor("#31526b"))
            canvas.circle(x, y, 19, fill=1, stroke=1)
            canvas.saveState()
            canvas.translate(x, y)
            canvas.scale(1, -1)
            canvas.setFillColor(colors.black)
            canvas.setFont(self.font, 12)
            canvas.drawCentredString(0, 1, code)
            canvas.drawCentredString(0, -13, str(i + 1))
            if len(self.graph.nodes) <= 10:
                canvas.setFont(self.font, 15)
                if x < 450:
                    canvas.drawRightString(-25, -5, short_label(node.label))
                else:
                    canvas.drawString(25, -5, short_label(node.label))
            canvas.restoreState()
        canvas.restoreState()


def render_pdf(html: str, graph: ExportGraph | None) -> bytes:
    paths = [
        Path("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf"),
        Path("C:/Windows/Fonts/arial.ttf"),
    ]
    font_path = next((path for path in paths if path.is_file()), None)
    if font_path is None:
        raise ValueError("PDF_FONT_UNAVAILABLE")
    font = "ExportUnicode"
    if font not in pdfmetrics.getRegisteredFontNames():
        pdfmetrics.registerFont(TTFont(font, str(font_path)))
    normal = ParagraphStyle(
        "report", fontName=font, fontSize=9, leading=13, spaceAfter=5, splitLongWords=1
    )
    styles = {
        "normal": normal,
        "h1": ParagraphStyle(
            "title", parent=normal, fontSize=16, leading=20, spaceAfter=12, keepWithNext=True
        ),
        "h2": ParagraphStyle(
            "heading", parent=normal, fontSize=12, leading=16, spaceBefore=8, keepWithNext=True
        ),
        "h3": ParagraphStyle(
            "subheading", parent=normal, fontSize=10, leading=14, spaceBefore=5, keepWithNext=True
        ),
    }
    parser = _Text()
    parser.feed(html)
    parser.flush()
    stream = BytesIO()
    document = SimpleDocTemplate(
        stream,
        pagesize=(210 * mm, 297 * mm),
        leftMargin=18 * mm,
        rightMargin=18 * mm,
        topMargin=18 * mm,
        bottomMargin=18 * mm,
    )
    story = [Paragraph(escape(line), styles[style]) for line, style in parser.lines]
    if graph and graph.nodes:
        story.extend(
            [
                Spacer(1, 8 * mm),
                Paragraph("Схема связей подграфа", styles["h2"]),
                _GraphDiagram(graph, font),
            ]
        )

    def footer(canvas: Any, doc: Any) -> None:
        canvas.saveState()
        canvas.setFont(font, 8)
        canvas.drawRightString(192 * mm, 10 * mm, str(doc.page))
        canvas.restoreState()

    try:
        document.build(story, onFirstPage=footer, onLaterPages=footer)
    except LayoutError:
        raise ValueError("PDF_LAYOUT_ERROR") from None
    return stream.getvalue()
