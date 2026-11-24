"""Локальный PDF из уже проверенного отчёта, без внешних ресурсов."""

from html import escape
from html.parser import HTMLParser
from io import BytesIO
from pathlib import Path
from typing import Any

from reportlab.lib import colors  # type: ignore[import-untyped]
from reportlab.lib.enums import TA_CENTER  # type: ignore[import-untyped]
from reportlab.lib.styles import ParagraphStyle  # type: ignore[import-untyped]
from reportlab.lib.units import mm  # type: ignore[import-untyped]
from reportlab.pdfbase import pdfmetrics  # type: ignore[import-untyped]
from reportlab.pdfbase.ttfonts import TTFont  # type: ignore[import-untyped]
from reportlab.platypus import (  # type: ignore[import-untyped]
    Paragraph,
    SimpleDocTemplate,
    Spacer,
    Table,
    TableStyle,
)
from reportlab.platypus.doctemplate import LayoutError  # type: ignore[import-untyped]

from app.services.export_graph import ExportGraph


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
    center = ParagraphStyle("diagram", parent=normal, alignment=TA_CENTER, fontSize=8)
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
    if graph and graph.edges:
        story.extend([Spacer(1, 8 * mm), Paragraph("Схема связей подграфа", normal)])
        nodes = {node.id: node for node in graph.nodes}
        for edge in graph.edges:
            cells = [nodes[edge.source].label, "→ " + edge.type + " →", nodes[edge.target].label]
            table = Table(
                [[Paragraph(escape(cell), center) for cell in cells]],
                colWidths=[64 * mm, 46 * mm, 64 * mm],
            )
            table.setStyle(
                TableStyle(
                    [
                        ("BACKGROUND", (0, 0), (0, 0), colors.HexColor("#e8f2fa")),
                        ("BACKGROUND", (2, 0), (2, 0), colors.HexColor("#e8f2fa")),
                        ("BOX", (0, 0), (0, 0), 0.5, colors.HexColor("#31526b")),
                        ("BOX", (2, 0), (2, 0), 0.5, colors.HexColor("#31526b")),
                        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
                    ]
                )
            )
            story.extend([table, Spacer(1, 2 * mm)])

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
