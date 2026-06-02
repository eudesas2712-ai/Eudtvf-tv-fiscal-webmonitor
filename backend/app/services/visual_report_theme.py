from __future__ import annotations

import os
from typing import Any, Iterable

from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER, TA_LEFT
from reportlab.lib.pagesizes import A4, landscape
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import mm
from reportlab.platypus import Image, Paragraph, Spacer, Table, TableStyle
from reportlab.graphics.shapes import Drawing, Circle, Rect, String

TVF_RED = colors.HexColor("#c1121f")
TVF_RED_DARK = colors.HexColor("#8f0d16")
TVF_DARK = colors.HexColor("#071a2f")
TVF_NAVY = colors.HexColor("#0b213a")
TVF_BLUE = colors.HexColor("#193a5a")
TVF_SLATE = colors.HexColor("#334155")
TVF_GRAY = colors.HexColor("#64748b")
TVF_LIGHT = colors.HexColor("#f7f9fc")
TVF_BORDER = colors.HexColor("#d8e1ec")
TVF_GREEN = colors.HexColor("#18b26b")
TVF_YELLOW = colors.HexColor("#f3c623")
TVF_NEG = colors.HexColor("#e53935")
TVF_ORANGE = colors.HexColor("#f97316")
TVF_PURPLE = colors.HexColor("#635bff")
WHITE = colors.white

LOGO_PATH = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "assets", "logo_tvfiscal.png"))
LOGO_HEADER_PATH = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "assets", "logo_tvfiscal_header.png"))


def safe(value: Any, fallback: str = "—") -> str:
    text = " ".join(str(value or "").split())
    return text or fallback


def short(value: Any, size: int = 80) -> str:
    text = safe(value, "")
    if not text:
        return "—"
    return text if len(text) <= size else text[: size - 1].rsplit(" ", 1)[0] + "…"


def brl(value: Any) -> str:
    try:
        return f"R$ {float(value or 0):,.0f}".replace(",", ".")
    except Exception:
        return "R$ 0"


def pct(value: Any) -> str:
    try:
        return f"{float(value or 0):.1f}%"
    except Exception:
        return "0,0%"


def styles():
    base = getSampleStyleSheet()
    return {
        "hero_title": ParagraphStyle("TVFHeroTitle", parent=base["Title"], textColor=WHITE, fontSize=22, leading=25, alignment=TA_LEFT, spaceAfter=2),
        "hero_sub": ParagraphStyle("TVFHeroSub", parent=base["Normal"], textColor=colors.HexColor("#dbeafe"), fontSize=8.4, leading=10.2),
        "kicker": ParagraphStyle("TVFKicker", parent=base["Normal"], textColor=colors.HexColor("#93c5fd"), fontSize=6.8, leading=8, fontName="Helvetica-Bold"),
        "h": ParagraphStyle("TVFSection", parent=base["Heading2"], textColor=TVF_DARK, fontSize=12.4, leading=14.5, spaceBefore=7, spaceAfter=5, fontName="Helvetica-Bold"),
        "body": ParagraphStyle("TVFBody", parent=base["Normal"], textColor=colors.HexColor("#1f2937"), fontSize=7.4, leading=9.4),
        "small": ParagraphStyle("TVFSmall", parent=base["Normal"], textColor=TVF_GRAY, fontSize=6.5, leading=7.8),
        "tiny": ParagraphStyle("TVFTiny", parent=base["Normal"], textColor=TVF_GRAY, fontSize=5.8, leading=7),
        "metric_value": ParagraphStyle("TVFMetricValue", parent=base["Normal"], textColor=TVF_DARK, fontSize=16, leading=16.5, alignment=TA_CENTER, fontName="Helvetica-Bold"),
        "metric_label": ParagraphStyle("TVFMetricLabel", parent=base["Normal"], textColor=TVF_SLATE, fontSize=6.2, leading=7.2, alignment=TA_CENTER, fontName="Helvetica-Bold"),
        "badge": ParagraphStyle("TVFBadge", parent=base["Normal"], textColor=WHITE, fontSize=6.2, leading=7.2, alignment=TA_CENTER, fontName="Helvetica-Bold"),
    }


def header_footer(canvas, doc):
    canvas.saveState()
    w, _h = landscape(A4)
    canvas.setFillColor(TVF_DARK)
    canvas.rect(0, 0, w, 9 * mm, fill=1, stroke=0)
    canvas.setFillColor(TVF_RED)
    canvas.rect(0, 9 * mm, w, 1.1 * mm, fill=1, stroke=0)
    canvas.setFillColor(WHITE)
    canvas.setFont("Helvetica", 7)
    canvas.drawCentredString(w / 2, 3.4 * mm, "© TV Fiscal - Inteligência e Monitoramento de Mídia | Evolução e precisão no monitoramento de mídia. Desde 1987.")
    canvas.setFillColor(TVF_LIGHT)
    canvas.setFont("Helvetica", 6)
    canvas.drawRightString(w - 11 * mm, 3.4 * mm, f"p. {doc.page}")
    canvas.restoreState()


def logo(width: float = 26 * mm):
    path = LOGO_HEADER_PATH if os.path.exists(LOGO_HEADER_PATH) else LOGO_PATH
    if os.path.exists(path):
        img = Image(path, mask="auto")
        img.drawWidth = width
        img.drawHeight = width * 193 / 250
        return img
    return Paragraph("TV Fiscal", ParagraphStyle("LogoFallback", textColor=WHITE, fontName="Helvetica-Bold", fontSize=12))


def hero(title: str, subtitle: str, project_label: str, kicker: str = "TV FISCAL WEBMONITOR") -> Table:
    s = styles()
    left = [
        Paragraph(kicker.upper(), s["kicker"]),
        Paragraph(short(title, 80), s["hero_title"]),
        Paragraph(short(subtitle, 150), s["hero_sub"]),
        Spacer(1, 1.8 * mm),
        Paragraph(f"Projeto/Cliente: <b>{safe(project_label)}</b>", s["hero_sub"]),
    ]
    mark = [logo(27 * mm), Paragraph("O monitor ideal da sua mídia", ParagraphStyle("LogoTag", parent=s["tiny"], textColor=colors.HexColor("#cbd5e1"), alignment=TA_CENTER, fontSize=5.4, leading=6.2))]
    t = Table([[left, mark]], colWidths=[215 * mm, 39 * mm], rowHeights=[29 * mm])
    t.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, -1), TVF_DARK),
        ("LEFTPADDING", (0, 0), (0, 0), 8 * mm),
        ("RIGHTPADDING", (0, 0), (0, 0), 5 * mm),
        ("LEFTPADDING", (1, 0), (1, 0), 1 * mm),
        ("RIGHTPADDING", (1, 0), (1, 0), 2 * mm),
        ("TOPPADDING", (0, 0), (-1, -1), 4 * mm),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 4 * mm),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("ALIGN", (1, 0), (1, 0), "CENTER"),
        ("LINEBELOW", (0, 0), (-1, -1), 2.6, TVF_RED),
        ("LINEBEFORE", (1, 0), (1, 0), 0.7, colors.HexColor("#1e3a5f")),
    ]))
    return t


def kpi_cards(metrics: list[tuple[str, Any, str | None]], width: float = 254 * mm) -> Table:
    s = styles()
    cells = []
    count = max(1, len(metrics))
    for i, (label, value, note) in enumerate(metrics):
        value_color = TVF_RED if str(label).lower() in {"risco", "auditáveis", "checking"} and str(value).lower() not in {"0", "baixo"} else TVF_DARK
        value_style = ParagraphStyle(f"MetricValue{i}", parent=s["metric_value"], textColor=value_color)
        cell = [Paragraph(safe(value), value_style), Paragraph(safe(label), s["metric_label"])]
        if note:
            cell.append(Paragraph(short(note, 28), s["tiny"]))
        cells.append(cell)
    t = Table([cells], colWidths=[width / count] * count, rowHeights=[17 * mm])
    style = TableStyle([
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("BACKGROUND", (0, 0), (-1, -1), WHITE),
        ("BOX", (0, 0), (-1, -1), 0.35, colors.HexColor("#e2e8f0")),
        ("GRID", (0, 0), (-1, -1), 0.25, colors.HexColor("#edf2f7")),
        ("TOPPADDING", (0, 0), (-1, -1), 3.7),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 3.7),
        ("LEFTPADDING", (0, 0), (-1, -1), 4),
        ("RIGHTPADDING", (0, 0), (-1, -1), 4),
    ])
    accent = [TVF_RED, TVF_BLUE, TVF_GREEN, TVF_ORANGE, TVF_PURPLE, TVF_YELLOW]
    for i in range(count):
        style.add("LINEABOVE", (i, 0), (i, 0), 1.7, accent[i % len(accent)])
    t.setStyle(style)
    return t


def section_title(text: str) -> Paragraph:
    return Paragraph(text, styles()["h"])


def notice_box(text: str, tone: str = "warning") -> Table:
    bg = colors.HexColor("#fff7ed") if tone == "warning" else colors.HexColor("#eff6ff")
    fg = colors.HexColor("#9a3412") if tone == "warning" else TVF_BLUE
    p = Paragraph(f"<b>Atenção:</b> {safe(text)}", ParagraphStyle("Notice", parent=styles()["body"], textColor=fg, fontSize=7.2, leading=9))
    t = Table([[p]], colWidths=[254 * mm])
    t.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, -1), bg),
        ("BOX", (0, 0), (-1, -1), 0.35, fg),
        ("LEFTPADDING", (0, 0), (-1, -1), 6),
        ("RIGHTPADDING", (0, 0), (-1, -1), 6),
        ("TOPPADDING", (0, 0), (-1, -1), 5),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
    ]))
    return t


def table_style(header_color=TVF_RED) -> TableStyle:
    return TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), header_color),
        ("TEXTCOLOR", (0, 0), (-1, 0), WHITE),
        ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
        ("FONTSIZE", (0, 0), (-1, -1), 7.2),
        ("GRID", (0, 0), (-1, -1), 0.25, colors.HexColor("#d1d5db")),
        ("BACKGROUND", (0, 1), (-1, -1), WHITE),
        ("ROWBACKGROUNDS", (0, 1), (-1, -1), [WHITE, colors.HexColor("#f9fafb")]),
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("TOPPADDING", (0, 0), (-1, -1), 5),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
        ("LEFTPADDING", (0, 0), (-1, -1), 4),
        ("RIGHTPADDING", (0, 0), (-1, -1), 4),
    ])


def bar_list(title: str, items: Iterable[dict], label_key: str, value_key: str, max_value: float | None = None, sub_key: str | None = None, limit: int = 5) -> Table:
    s = styles()
    rows = [[Paragraph(title, ParagraphStyle("BarTitle", parent=s["body"], fontName="Helvetica-Bold", textColor=TVF_DARK, fontSize=8.5, leading=10))]]
    values = []
    real_items = list(items or [])[:limit]
    for item in real_items:
        try:
            values.append(float(item.get(value_key) or 0))
        except Exception:
            values.append(0)
    maxv = max_value or max(values or [1]) or 1
    for item in real_items:
        value = float(item.get(value_key) or 0)
        label = short(item.get(label_key), 42)
        pct_width = min(100, max(2, value / maxv * 100))
        bar = Drawing(80 * mm, 5 * mm)
        bar.add(Rect(0, 1.5 * mm, 80 * mm, 2.2 * mm, fillColor=colors.HexColor("#e2e8f0"), strokeColor=None))
        bar.add(Rect(0, 1.5 * mm, 80 * mm * pct_width / 100, 2.2 * mm, fillColor=TVF_DARK, strokeColor=None))
        sub = f"{value:g}"
        if sub_key:
            sub = safe(item.get(sub_key), sub)
        inner = Table([[Paragraph(label, s["small"]), Paragraph(sub, s["small"])], [bar, ""]], colWidths=[70 * mm, 22 * mm])
        inner.setStyle(TableStyle([("SPAN", (0, 1), (1, 1)), ("VALIGN", (0, 0), (-1, -1), "MIDDLE"), ("LEFTPADDING", (0, 0), (-1, -1), 0), ("RIGHTPADDING", (0, 0), (-1, -1), 0), ("TOPPADDING", (0, 0), (-1, -1), 1), ("BOTTOMPADDING", (0, 0), (-1, -1), 1)]))
        rows.append([inner])
    if not real_items:
        rows.append([Paragraph("Sem dados para exibir.", s["small"])])
    t = Table(rows, colWidths=[92 * mm])
    t.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, -1), WHITE),
        ("BOX", (0, 0), (-1, -1), 0.3, TVF_BORDER),
        ("LINEABOVE", (0, 0), (-1, 0), 1.7, TVF_RED),
        ("LEFTPADDING", (0, 0), (-1, -1), 5),
        ("RIGHTPADDING", (0, 0), (-1, -1), 5),
        ("TOPPADDING", (0, 0), (-1, -1), 5),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
    ]))
    return t


def text_panel(title: str, body_lines: list[str] | str, width: float = 254 * mm) -> Table:
    s = styles()
    if isinstance(body_lines, str):
        body_lines = [body_lines]
    flow = [Paragraph(title, ParagraphStyle("PanelTitle", parent=s["body"], textColor=TVF_DARK, fontName="Helvetica-Bold", fontSize=8.4, leading=10))]
    for line in body_lines[:10]:
        flow.append(Paragraph(f"• {safe(line)}", s["body"]))
    t = Table([[flow]], colWidths=[width])
    t.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, -1), WHITE),
        ("BOX", (0, 0), (-1, -1), 0.35, TVF_BORDER),
        ("LINEABOVE", (0, 0), (-1, -1), 1.7, TVF_RED),
        ("LEFTPADDING", (0, 0), (-1, -1), 6),
        ("RIGHTPADDING", (0, 0), (-1, -1), 6),
        ("TOPPADDING", (0, 0), (-1, -1), 5),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
    ]))
    return t


def gauge_donut(value: float, label: str, color=TVF_RED) -> Drawing:
    d = Drawing(32 * mm, 25 * mm)
    cx, cy, r = 16 * mm, 14 * mm, 9 * mm
    d.add(Circle(cx, cy, r, fillColor=colors.HexColor("#e2e8f0"), strokeColor=None))
    # approximate donut by filled circle + inner white; percentage shown in center (keeps dependency-free)
    d.add(Circle(cx, cy, r, fillColor=color, strokeColor=None))
    d.add(Circle(cx, cy, r * 0.62, fillColor=WHITE, strokeColor=None))
    d.add(String(cx, cy + 1, f"{value:.0f}%", textAnchor="middle", fontName="Helvetica-Bold", fontSize=9, fillColor=TVF_DARK))
    d.add(String(cx, cy - 9, label, textAnchor="middle", fontName="Helvetica", fontSize=5.6, fillColor=TVF_GRAY))
    return d
