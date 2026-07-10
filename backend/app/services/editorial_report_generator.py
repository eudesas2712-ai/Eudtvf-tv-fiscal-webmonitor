from __future__ import annotations

import html
import os
from collections import Counter
from datetime import datetime
from io import BytesIO
from typing import Any

from reportlab.graphics.charts.barcharts import HorizontalBarChart, VerticalBarChart
from reportlab.graphics.charts.piecharts import Pie
from reportlab.graphics.shapes import Circle, Drawing, Line, Rect, String
from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER, TA_LEFT, TA_RIGHT
from reportlab.lib.pagesizes import A4, landscape
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import mm
from reportlab.platypus import (
    Image,
    KeepTogether,
    PageBreak,
    Paragraph,
    SimpleDocTemplate,
    Spacer,
    Table,
    TableStyle,
)

TVF_RED = colors.HexColor("#c1121f")
TVF_RED_DARK = colors.HexColor("#8f0d16")
TVF_DARK = colors.HexColor("#071a2f")
TVF_NAVY = colors.HexColor("#0b213a")
TVF_BLUE = colors.HexColor("#193a5a")
TVF_SLATE = colors.HexColor("#334155")
TVF_GRAY = colors.HexColor("#64748b")
TVF_LIGHT = colors.HexColor("#f7f9fc")
TVF_CARD = colors.HexColor("#ffffff")
TVF_BORDER = colors.HexColor("#d8e1ec")
TVF_GREEN = colors.HexColor("#18b26b")
TVF_YELLOW = colors.HexColor("#f3c623")
TVF_NEG = colors.HexColor("#e53935")
TVF_ORANGE = colors.HexColor("#f97316")
TVF_PURPLE = colors.HexColor("#635bff")

LOGO_PATH = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "assets", "logo_tvfiscal.png"))
LOGO_HEADER_PATH = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "assets", "logo_tvfiscal_header.png"))


def _escape(value: Any) -> str:
    return html.escape(str(value or ""))


def _short(value: Any, size: int = 120) -> str:
    text = " ".join(str(value or "").split())
    if not text:
        return "-"
    return text if len(text) <= size else text[: size - 1].rsplit(" ", 1)[0] + "..."


def _date(value: Any) -> str:
    if not value:
        return "-"
    if isinstance(value, datetime):
        return value.strftime("%d/%m/%Y")
    text = str(value)
    try:
        return datetime.fromisoformat(text.replace("Z", "+00:00")).strftime("%d/%m/%Y")
    except Exception:
        return text[:10]


def _risk_from_row(row: dict) -> str:
    score = int(row.get("sentiment_score") or 0)
    sentiment = str(row.get("sentiment") or "neutro").lower()
    title = str(row.get("title") or "").lower()
    body = str(row.get("summary") or row.get("content_text") or "").lower()
    sensitive = any(t in f"{title} {body}" for t in [
        "denúncia", "denuncia", "investiga", "prisão", "preso", "operação", "operacao",
        "condena", "inelegibilidade", "assédio", "assedio", "irregular", "crime", "morte",
    ])
    if sentiment == "negativo" and (score <= -60 or sensitive):
        return "Alto"
    if sentiment == "negativo" or abs(score) >= 40 or sensitive:
        return "Médio"
    return "Baixo"


def _overall_risk(rows: list[dict]) -> str:
    if not rows:
        return "Baixo"
    neg = sum(1 for r in rows if str(r.get("sentiment") or "").lower() == "negativo")
    high = sum(1 for r in rows if _risk_from_row(r) == "Alto")
    ratio = neg / max(1, len(rows))
    if high >= 3 or ratio >= 0.35:
        return "Alto"
    if high >= 1 or ratio >= 0.18:
        return "Médio/Alto"
    if neg:
        return "Médio"
    return "Baixo"


def _item_type(row: dict) -> str:
    text = f"{row.get('title','')} {row.get('url','')} {row.get('summary','')}".lower()
    if any(token in text for token in ["instagram", "reels", "youtube", "youtu.be", "facebook", "podcast", "vídeo", "video"]):
        return "Rede social / vídeo"
    return "Portal"


def _possible_transcript(row: dict, max_chars: int = 260) -> str:
    text = row.get("content_text") or row.get("summary") or ""
    text = " ".join(str(text).split())
    if not text:
        return "Transcrição possível: conteúdo textual não disponível no item coletado."
    return "Transcrição possível / síntese textual: " + _short(text, max_chars)


def _terms_text(row: dict) -> str:
    terms = (row.get("matched_terms") or {}).get("terms") if isinstance(row.get("matched_terms"), dict) else []
    return ", ".join(terms or []) or "-"


def _counters(rows: list[dict]) -> dict:
    sentiment = Counter(str(r.get("sentiment") or "neutro").lower() for r in rows)
    sources = Counter(str(r.get("source_name") or "Fonte não identificada") for r in rows)
    topics = Counter(str(r.get("topic") or "Geral") for r in rows)
    terms = Counter()
    by_month = Counter()
    for row in rows:
        for term in (row.get("matched_terms") or {}).get("terms", []) if isinstance(row.get("matched_terms"), dict) else []:
            terms[str(term)] += 1
        dt = row.get("published_at") or row.get("created_at")
        if isinstance(dt, datetime):
            by_month[dt.strftime("%Y-%m")] += 1
        else:
            text = str(dt or "")
            by_month[text[:7] or "Sem data"] += 1
    return {"sentiment": sentiment, "sources": sources, "topics": topics, "terms": terms, "timeline": by_month}


def _styles():
    styles = getSampleStyleSheet()
    return {
        "cover_title": ParagraphStyle("TVFCoverTitle", parent=styles["Title"], textColor=colors.white, fontSize=23, leading=26, alignment=TA_LEFT, spaceAfter=3),
        "cover_subtitle": ParagraphStyle("TVFCoverSub", parent=styles["Normal"], textColor=colors.HexColor("#dbeafe"), fontSize=8.5, leading=10.5),
        "title": ParagraphStyle("TVFTitle", parent=styles["Title"], textColor=TVF_DARK, fontSize=19, leading=22, alignment=TA_LEFT, spaceAfter=2),
        "subtitle": ParagraphStyle("TVFSub", parent=styles["Normal"], textColor=TVF_GRAY, fontSize=8.2, leading=10),
        "h": ParagraphStyle("TVFH", parent=styles["Heading2"], textColor=TVF_DARK, fontSize=12, leading=14, spaceBefore=5, spaceAfter=4),
        "h_white": ParagraphStyle("TVFHWhite", parent=styles["Heading2"], textColor=colors.white, fontSize=12, leading=14, spaceBefore=0, spaceAfter=2),
        "body": ParagraphStyle("TVFBody", parent=styles["Normal"], textColor=colors.HexColor("#1f2937"), fontSize=7.7, leading=9.8),
        "small": ParagraphStyle("TVFSmall", parent=styles["Normal"], textColor=TVF_GRAY, fontSize=6.7, leading=8.2),
        "tiny": ParagraphStyle("TVFTiny", parent=styles["Normal"], textColor=TVF_GRAY, fontSize=5.9, leading=7.1),
        "center": ParagraphStyle("TVFCenter", parent=styles["Normal"], textColor=TVF_DARK, fontSize=7, alignment=TA_CENTER, leading=8.2),
        "metric_value": ParagraphStyle("TVFMetricValue", parent=styles["Normal"], textColor=TVF_DARK, fontSize=17, leading=18, alignment=TA_CENTER, fontName="Helvetica-Bold"),
        "metric_label": ParagraphStyle("TVFMetricLabel", parent=styles["Normal"], textColor=TVF_GRAY, fontSize=6.3, leading=7.2, alignment=TA_CENTER),
        "badge": ParagraphStyle("TVFBadge", parent=styles["Normal"], textColor=colors.white, fontSize=6.2, leading=7.4, alignment=TA_CENTER, fontName="Helvetica-Bold"),
    }


def _header_footer(canvas, doc):
    canvas.saveState()
    w, h = landscape(A4)
    canvas.setFillColor(TVF_DARK)
    canvas.rect(0, 0, w, 9 * mm, fill=1, stroke=0)
    canvas.setFillColor(TVF_RED)
    canvas.rect(0, 9 * mm, w, 1.1 * mm, fill=1, stroke=0)
    canvas.setFillColor(colors.white)
    canvas.setFont("Helvetica", 7)
    canvas.drawCentredString(w / 2, 3.4 * mm, "© TV Fiscal - Inteligência e Monitoramento de Mídia | Evolução e precisão no monitoramento de mídia. Desde 1987.")
    canvas.setFillColor(TVF_LIGHT)
    canvas.setFont("Helvetica", 6)
    canvas.drawRightString(w - 11 * mm, 3.4 * mm, f"p. {doc.page}")
    canvas.restoreState()


def _logo(width: float = 20 * mm, header: bool = False) -> Image | Paragraph:
    path = LOGO_HEADER_PATH if header and os.path.exists(LOGO_HEADER_PATH) else LOGO_PATH
    if os.path.exists(path):
        img = Image(path, mask="auto")
        img.drawWidth = width
        img.drawHeight = width * 193 / 250
        return img
    style = ParagraphStyle("LogoFallback", parent=_styles()["small"], textColor=colors.white if header else TVF_DARK, fontName="Helvetica-Bold")
    return Paragraph("TV Fiscal", style)


def _hero(title: str, subtitle: str, risk: str, project_label: str) -> Table:
    """Modern editorial header.

    V20 removes the white badge behind the logo and uses a transparent/header-safe
    logo file. The risk indicator remains only in KPI cards, keeping the hero clean.
    """
    s = _styles()
    kicker = Paragraph("EDITORIAL INTELLIGENCE · TV FISCAL WEBMONITOR", ParagraphStyle(
        "HeroKicker", parent=s["cover_subtitle"], textColor=colors.HexColor("#93c5fd"),
        fontSize=6.8, leading=8, fontName="Helvetica-Bold", spaceAfter=1.2
    ))
    left = [
        kicker,
        Paragraph(title, s["cover_title"]),
        Paragraph(_escape(subtitle), s["cover_subtitle"]),
        Spacer(1, 1.8 * mm),
        Paragraph(f"Projeto/Cliente: <b>{_escape(project_label)}</b>", s["cover_subtitle"]),
    ]

    logo_cell = [
        _logo(28 * mm, header=True),
        Paragraph("O monitor ideal da sua mídia", ParagraphStyle(
            "LogoTag", parent=s["tiny"], textColor=colors.HexColor("#cbd5e1"),
            alignment=TA_CENTER, fontSize=5.5, leading=6.2
        )),
    ]

    box = Table([[left, logo_cell]], colWidths=[215 * mm, 39 * mm], rowHeights=[29 * mm])
    box.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, -1), TVF_DARK),
        ("BOX", (0, 0), (-1, -1), 0, TVF_DARK),
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
    return box


def _kpi_cards(metrics: list[tuple[str, str, str | None]]) -> Table:
    s = _styles()
    cells = []
    for idx, (label, value, note) in enumerate(metrics):
        value_color = TVF_RED if label.lower() == "risco" and "alto" in str(value).lower() else TVF_DARK
        value_style = ParagraphStyle(
            f"TVFMetricValue{idx}", parent=s["metric_value"],
            textColor=value_color, fontSize=16, leading=16, fontName="Helvetica-Bold"
        )
        cell = [
            Paragraph(_escape(value), value_style),
            Paragraph(_escape(label), ParagraphStyle(
                f"TVFMetricLabel{idx}", parent=s["metric_label"],
                textColor=TVF_SLATE, fontSize=6.4, leading=7.2, fontName="Helvetica-Bold"
            )),
        ]
        if note:
            cell.append(Paragraph(_escape(note), s["tiny"]))
        cells.append(cell)
    t = Table([cells], colWidths=[50.8 * mm] * len(cells), rowHeights=[17 * mm])
    style = TableStyle([
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("BACKGROUND", (0, 0), (-1, -1), colors.white),
        ("BOX", (0, 0), (-1, -1), 0.35, colors.HexColor("#e2e8f0")),
        ("GRID", (0, 0), (-1, -1), 0.25, colors.HexColor("#edf2f7")),
        ("TOPPADDING", (0, 0), (-1, -1), 3.7),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 3.7),
        ("LEFTPADDING", (0, 0), (-1, -1), 4),
        ("RIGHTPADDING", (0, 0), (-1, -1), 4),
    ])
    accents = [TVF_RED, TVF_BLUE, TVF_PURPLE, TVF_ORANGE, TVF_DARK]
    for i in range(len(cells)):
        style.add("LINEABOVE", (i, 0), (i, 0), 2.6, accents[i % len(accents)])
    t.setStyle(style)
    return t


def _card(title: str, content: Any, width_mm: float = 84, height_mm: float | None = None, accent: colors.Color = TVF_RED) -> Table:
    s = _styles()
    parts = [Paragraph(_escape(title), ParagraphStyle(
        "CardTitle", parent=s["small"], textColor=TVF_DARK,
        fontName="Helvetica-Bold", fontSize=7.5, leading=8.8
    ))]
    if isinstance(content, list):
        parts.extend(content)
    else:
        parts.append(content)
    t = Table([[parts]], colWidths=[width_mm * mm], rowHeights=[height_mm * mm] if height_mm else None)
    t.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, -1), colors.white),
        ("BOX", (0, 0), (-1, -1), 0.35, colors.HexColor("#d7e0ea")),
        ("LINEABOVE", (0, 0), (-1, 0), 2.5, accent),
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("LEFTPADDING", (0, 0), (-1, -1), 5.5),
        ("RIGHTPADDING", (0, 0), (-1, -1), 5.5),
        ("TOPPADDING", (0, 0), (-1, -1), 5.5),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 5.5),
    ]))
    return t


def _sentiment_pie(counter: Counter, width: int = 190, height: int = 122) -> Drawing:
    values = [counter.get("positivo", 0), counter.get("neutro", 0), counter.get("negativo", 0)]
    if sum(values) == 0:
        values = [1, 0, 0]
    d = Drawing(width, height)
    pie = Pie()
    pie.x = 12
    pie.y = 18
    pie.width = 82
    pie.height = 82
    pie.data = values
    pie.labels = None
    pie.simpleLabels = 0
    pie.slices[0].fillColor = TVF_GREEN
    pie.slices[1].fillColor = TVF_YELLOW
    pie.slices[2].fillColor = TVF_NEG
    for i in range(3):
        pie.slices[i].strokeColor = colors.white
        pie.slices[i].strokeWidth = 1.2
    d.add(pie)
    # Donut center for a more modern BI look.
    d.add(Circle(53, 59, 22, fillColor=colors.white, strokeColor=colors.white))
    total = max(1, sum(values))
    d.add(String(45, 63, f"{total}", fontSize=13, fillColor=TVF_DARK, fontName="Helvetica-Bold"))
    d.add(String(38, 51, "ocorrências", fontSize=5.5, fillColor=TVF_GRAY))

    legend = [("Positivo", TVF_GREEN, values[0]), ("Neutro", TVF_YELLOW, values[1]), ("Negativo", TVF_NEG, values[2])]
    for idx, (lab, col, val) in enumerate(legend):
        y = 83 - idx * 22
        d.add(Rect(112, y, 9, 9, fillColor=col, strokeColor=col))
        pct = round((val / total) * 100)
        d.add(String(126, y + 1.6, f"{lab}: {val} ({pct}%)", fontSize=7, fillColor=TVF_SLATE))
    d.add(String(14, 5, "Leitura de tom editorial", fontSize=6.2, fillColor=TVF_GRAY))
    return d


def _bar_chart(title: str, pairs: list[tuple[str, int]], width: int = 210, height: int = 122, bar_color=TVF_DARK) -> Drawing:
    pairs = pairs[:6]
    if not pairs:
        pairs = [("Sem dados", 0)]
    d = Drawing(width, height)
    max_val = max(1, max(int(v) for _, v in pairs))
    left = 70
    top = height - 22
    row_h = 14
    bar_w_max = width - left - 26
    for idx, (label, val) in enumerate(pairs):
        y = top - idx * row_h
        v = max(0, int(val))
        d.add(String(3, y + 1, _short(label, 18), fontSize=6.1, fillColor=TVF_SLATE))
        d.add(Rect(left, y, bar_w_max, 7, fillColor=colors.HexColor("#eef2f7"), strokeColor=colors.HexColor("#eef2f7")))
        fill_w = 1 if v == 0 else max(4, bar_w_max * v / max_val)
        d.add(Rect(left, y, fill_w, 7, fillColor=bar_color, strokeColor=bar_color))
        d.add(String(left + fill_w + 4, y + 0.7, str(v), fontSize=5.8, fillColor=TVF_GRAY))
    return d


def _timeline_chart(counter: Counter, width: int = 260, height: int = 95) -> Drawing:
    pairs = sorted(counter.items())[-8:]
    if not pairs:
        pairs = [("Sem data", 0)]
    d = Drawing(width, height)
    max_val = max(1, max(int(v) for _, v in pairs))
    base = 22
    chart_h = height - 40
    left = 28
    gap = 8
    bar_w = max(10, (width - left - 18 - gap * (len(pairs)-1)) / max(1, len(pairs)))
    d.add(Line(left, base, width - 10, base, strokeColor=colors.HexColor("#cbd5e1"), strokeWidth=0.8))
    d.add(Line(left, base, left, base + chart_h, strokeColor=colors.HexColor("#cbd5e1"), strokeWidth=0.8))
    for idx, (label, val) in enumerate(pairs):
        v = max(0, int(val))
        h = 2 if v == 0 else max(4, chart_h * v / max_val)
        x = left + idx * (bar_w + gap)
        d.add(Rect(x, base, bar_w, h, fillColor=TVF_RED, strokeColor=TVF_RED))
        d.add(String(x, base - 9, _short(label, 8), fontSize=5.3, fillColor=TVF_GRAY))
        d.add(String(x + bar_w/2 - 3, base + h + 3, str(v), fontSize=5.3, fillColor=TVF_SLATE))
    return d


def _executive_text(rows: list[dict], project_label: str) -> str:
    counters = _counters(rows)
    total = len(rows)
    pos = counters["sentiment"].get("positivo", 0)
    neg = counters["sentiment"].get("negativo", 0)
    top_topics = [t for t, _ in counters["topics"].most_common(3)]
    top_sources = [s for s, _ in counters["sources"].most_common(3)]
    risk = _overall_risk(rows)
    if total == 0:
        return "Nenhuma ocorrência editorial foi encontrada no recorte selecionado. Recomenda-se ampliar período, fontes ou termos monitorados."
    polarity = "predominância positiva" if pos > neg else "atenção a ocorrências negativas" if neg > pos else "distribuição equilibrada entre tons"
    return (
        f"A cobertura monitorada apresenta {polarity}, com {total} item(ns) em {len(counters['sources'])} fonte(s). "
        f"Os temas de maior recorrência são {', '.join(top_topics) or 'sem tema dominante'}. "
        f"As fontes de maior volume no recorte são {', '.join(top_sources) or 'sem fonte dominante'}. "
        f"O risco reputacional estimado é {risk}, considerando sentimento, temas sensíveis e volume de exposição. "
        f"Para uso executivo, recomenda-se priorizar matérias negativas, itens com termos/marcas monitorados, fontes de maior volume e evolução por tema."
    )


def _risk_palette(risk: str) -> colors.Color:
    return TVF_NEG if "Alto" in risk else TVF_ORANGE if "Médio" in risk else TVF_GREEN


def _report_table_style(header_color: colors.Color = TVF_RED) -> TableStyle:
    return TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), header_color),
        ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
        ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
        ("FONTSIZE", (0, 0), (-1, -1), 6.6),
        ("LEADING", (0, 0), (-1, -1), 7.5),
        ("GRID", (0, 0), (-1, -1), 0.25, TVF_BORDER),
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, colors.HexColor("#f8fafc")]),
        ("LEFTPADDING", (0, 0), (-1, -1), 3.2),
        ("RIGHTPADDING", (0, 0), (-1, -1), 3.2),
        ("TOPPADDING", (0, 0), (-1, -1), 3.2),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 3.2),
    ])


def _badge(text: str, fill: colors.Color) -> Table:
    p = Paragraph(_escape(text), _styles()["badge"])
    t = Table([[p]], colWidths=[22 * mm], rowHeights=[6 * mm])
    t.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, -1), fill),
        ("BOX", (0, 0), (-1, -1), 0, fill),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("LEFTPADDING", (0, 0), (-1, -1), 2),
        ("RIGHTPADDING", (0, 0), (-1, -1), 2),
        ("TOPPADDING", (0, 0), (-1, -1), 1),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 1),
    ]))
    return t


def _sentiment_color(sentiment: str) -> colors.Color:
    st = (sentiment or "neutro").lower()
    if st == "positivo":
        return TVF_GREEN
    if st == "negativo":
        return TVF_NEG
    return TVF_YELLOW



def _topic_risk_level(topic_rows: list[dict]) -> str:
    if not topic_rows:
        return "Baixo"

    high = sum(1 for r in topic_rows if _risk_from_row(r) == "Alto")
    neg = sum(1 for r in topic_rows if str(r.get("sentiment") or "").lower() == "negativo")
    ratio = neg / max(1, len(topic_rows))

    if high >= 2 or ratio >= 0.35:
        return "Alto"
    if high >= 1 or ratio >= 0.20:
        return "Médio/Alto"
    if neg:
        return "Médio"

    return "Baixo"


def _risk_reading_for_topic(topic: str, level: str, count: int) -> str:
    t = (topic or "").lower()

    if any(x in t for x in ["mobilidade", "trânsito", "transito", "zona azul", "viário", "viario"]):
        return "Tema operacional sensível; exige comunicação técnica, cronograma, sinalização e orientação preventiva."

    if any(x in t for x in ["saúde", "saude", "saae", "serviço", "servico", "esgoto", "iluminação", "iluminacao"]):
        return "Cobrança de serviço público com risco de amplificação por bairro; recomenda resposta nominalizada e prazo."

    if any(x in t for x in ["segurança", "seguranca", "gcm", "operação", "operacao"]):
        return "Pode reforçar agenda positiva quando associado a prevenção, ordem pública e presença institucional."

    if any(x in t for x in ["cultura", "são joão", "sao joao", "forró", "forro", "turismo", "literária", "literaria"]):
        return "Ativo reputacional positivo; deve ser vinculado a organização, segurança, fluxo e prestação de serviço."

    if any(x in t for x in ["política", "politica", "pgp", "governo", "prefeito", "agenda"]):
        return "Alta exposição institucional; amplia visibilidade, mas também aumenta cobrança por entregas concretas."

    if level in ["Alto", "Médio/Alto"]:
        return "Tema com potencial de desgaste e repercussão; requer resposta objetiva, fonte oficial e acompanhamento."

    return "Tema de acompanhamento regular, com baixo risco imediato no recorte analisado."


def _append_premium_v3_final_analysis(
    story: list,
    rows: list[dict],
    summary: dict | None = None,
    project_label: str | None = None,
    analytical: bool = False,
):
    """Acrescenta Radar de Riscos, SWOT, Recomendações, Metodologia e Conclusão no padrão Premium V3."""
    s = _styles()
    summary = summary or {}
    counters = _counters(rows)
    overall_risk = _overall_risk(rows)

    topic_groups: dict[str, list[dict]] = {}
    source_names = set()
    positive_topics = []
    negative_topics = []

    for row in rows:
        topic = str(row.get("topic") or "Geral")
        topic_groups.setdefault(topic, []).append(row)

        if row.get("source_name"):
            source_names.add(str(row.get("source_name")))

        sentiment = str(row.get("sentiment") or "").lower()
        if sentiment == "positivo":
            positive_topics.append(topic)
        elif sentiment == "negativo":
            negative_topics.append(topic)

    top_topics = sorted(topic_groups.items(), key=lambda kv: len(kv[1]), reverse=True)[:8]

    story.append(PageBreak())
    story.append(Paragraph("Análise estratégica - V3", s["title"]))
    story.append(Paragraph(
        f"{_escape(project_label or 'Projeto editorial')} | Radar de riscos, SWOT, recomendações e conclusão executiva",
        s["subtitle"],
    ))
    story.append(Spacer(1, 4 * mm))

    story.append(Paragraph("Radar de riscos", s["h"]))

    radar_data = [[
        Paragraph("Risco / Tema", s["badge"]),
        Paragraph("Nível", s["badge"]),
        Paragraph("Leitura executiva", s["badge"]),
    ]]

    if top_topics:
        for topic, topic_rows in top_topics:
            level = _topic_risk_level(topic_rows)
            radar_data.append([
                Paragraph(_escape(topic), s["body"]),
                Paragraph(_escape(level), s["body"]),
                Paragraph(_escape(_risk_reading_for_topic(topic, level, len(topic_rows))), s["body"]),
            ])
    else:
        radar_data.append([
            Paragraph("Sem temas classificados", s["body"]),
            Paragraph("Baixo", s["body"]),
            Paragraph("Não há volume suficiente de ocorrências no recorte para leitura de risco.", s["body"]),
        ])

    radar = Table(radar_data, colWidths=[60 * mm, 28 * mm, 166 * mm], repeatRows=1)
    radar.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), TVF_RED),
        ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
        ("GRID", (0, 0), (-1, -1), 0.25, TVF_BORDER),
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("BACKGROUND", (0, 1), (-1, -1), colors.white),
        ("LEFTPADDING", (0, 0), (-1, -1), 5),
        ("RIGHTPADDING", (0, 0), (-1, -1), 5),
        ("TOPPADDING", (0, 0), (-1, -1), 4),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
    ]))
    story.append(radar)
    story.append(Spacer(1, 5 * mm))

    positive_rank = [x for x, _ in Counter(positive_topics).most_common(4)]
    negative_rank = [x for x, _ in Counter(negative_topics).most_common(4)]
    topic_rank = [x for x, _ in counters["topics"].most_common(5)]

    strengths = "; ".join(positive_rank) if positive_rank else "Pautas institucionais, culturais ou informativas com potencial de reforço reputacional."
    weaknesses = "; ".join(negative_rank) if negative_rank else "Baixo volume de críticas explícitas no recorte, mas exige manutenção da vigilância editorial."
    opportunities = "Comunicar respostas por tema, fonte oficial, cronograma e prestação de serviço; transformar exposição positiva em entregas percebidas."
    threats = "Viralização de temas negativos, associação entre cobrança operacional e ausência de resposta, politização de serviços e amplificação por rádio/redes."

    story.append(Paragraph("SWOT Síntese", s["h"]))

    swot_data = [
        [Paragraph("Eixo", s["badge"]), Paragraph("Leitura executiva", s["badge"])],
        [Paragraph("Forças", s["body"]), Paragraph(_escape(strengths), s["body"])],
        [Paragraph("Fraquezas", s["body"]), Paragraph(_escape(weaknesses), s["body"])],
        [Paragraph("Oportunidades", s["body"]), Paragraph(_escape(opportunities), s["body"])],
        [Paragraph("Ameaças", s["body"]), Paragraph(_escape(threats), s["body"])],
    ]

    swot = Table(swot_data, colWidths=[38 * mm, 216 * mm], repeatRows=1)
    swot.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), TVF_RED),
        ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
        ("GRID", (0, 0), (-1, -1), 0.25, TVF_BORDER),
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("BACKGROUND", (0, 1), (-1, -1), colors.white),
        ("LEFTPADDING", (0, 0), (-1, -1), 5),
        ("RIGHTPADDING", (0, 0), (-1, -1), 5),
        ("TOPPADDING", (0, 0), (-1, -1), 4),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
    ]))
    story.append(swot)
    story.append(Spacer(1, 5 * mm))

    main_topics_text = ", ".join(topic_rank[:4]) if topic_rank else "temas editoriais monitorados"

    story.append(Paragraph("Recomendações executivas", s["h"]))

    rec_data = [
        [Paragraph("Frente", s["badge"]), Paragraph("Recomendação", s["badge"])],
        [Paragraph("Gestão / Cliente", s["body"]), Paragraph(f"Publicar boletim consolidado com respostas para {_escape(main_topics_text)}, priorizando prazos, responsáveis e próximos passos.", s["body"])],
        [Paragraph("Comunicação", s["body"]), Paragraph("Separar a narrativa em três linhas: agenda positiva, resposta técnica aos pontos críticos e prestação de serviço por tema/bairro/fonte.", s["body"])],
        [Paragraph("Operação", s["body"]), Paragraph("Criar respostas nominalizadas para temas de maior risco, com linguagem objetiva e evidência operacional.", s["body"])],
        [Paragraph("Monitoramento", s["body"]), Paragraph("Acompanhar reincidência de fontes, termos negativos, temas sensíveis e evolução do sentimento nas próximas coletas.", s["body"])],
    ]

    rec = Table(rec_data, colWidths=[48 * mm, 206 * mm], repeatRows=1)
    rec.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), TVF_RED),
        ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
        ("GRID", (0, 0), (-1, -1), 0.25, TVF_BORDER),
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("BACKGROUND", (0, 1), (-1, -1), colors.white),
        ("LEFTPADDING", (0, 0), (-1, -1), 5),
        ("RIGHTPADDING", (0, 0), (-1, -1), 5),
        ("TOPPADDING", (0, 0), (-1, -1), 4),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
    ]))
    story.append(rec)
    story.append(Spacer(1, 5 * mm))

    named_sources = sorted(source_names)
    sources_text = "; ".join(named_sources[:18]) if named_sources else "Fontes digitais, rádio/áudio, TV/redes públicas e itens editoriais cadastrados no projeto, conforme base disponível."

    story.append(Paragraph("Fontes, metodologia e observações", s["h"]))

    methodology = (
        f"Relatório gerado a partir do recorte editorial filtrado no WebMonitor. "
        f"Base analisada: {len(rows)} ocorrências. Fontes nomeadas monitoradas: {sources_text}. "
        f"Classificação por tema, sentimento, termos monitorados, fonte, evidência textual e risco editorial. "
        f"Quando houver áudio, a transcrição literal depende de processamento ASR/Whisper; na ausência dela, o sistema utiliza resumo, metadados e síntese textual disponível."
    )

    story.append(Paragraph(_escape(methodology), s["body"]))
    story.append(Spacer(1, 4 * mm))

    conclusion = (
        f"O recorte fecha com risco geral {overall_risk}. "
        f"A recomendação central é transformar o monitoramento editorial em resposta executiva: consolidar temas críticos, comunicar providências, valorizar pautas positivas e acompanhar reincidências."
    )

    story.append(Paragraph("Conclusão executiva", s["h"]))
    story.append(Paragraph(_escape(conclusion), s["body"]))

def _synthetic_occurrence_table(rows: list[dict]) -> Table:
    s = _styles()
    table_rows = [["Data", "Fonte", "Tema", "Tom", "Observação executiva"]]
    for row in rows[:5]:
        sent = str(row.get("sentiment") or "neutro").title()
        table_rows.append([
            _date(row.get("published_at") or row.get("created_at")),
            _short(row.get("source_name"), 22),
            _short(row.get("topic"), 25),
            sent,
            Paragraph(_escape(_short(row.get("summary") or row.get("title"), 106)), s["small"]),
        ])
    if len(table_rows) == 1:
        table_rows.append(["-", "-", "-", "-", "Nenhuma ocorrência encontrada"])
    t = Table(table_rows, colWidths=[21 * mm, 39 * mm, 33 * mm, 25 * mm, 138 * mm], repeatRows=1)
    t.setStyle(_report_table_style(TVF_RED))
    # Visual strip in the sentiment column.
    for idx, row in enumerate(rows[:5], start=1):
        t.setStyle(TableStyle([("TEXTCOLOR", (3, idx), (3, idx), _sentiment_color(str(row.get("sentiment") or "neutro")))]))
    return t


def build_editorial_synthetic_pdf(project_id: str, rows: list[dict], summary: dict | None = None, project_label: str | None = None) -> bytes:
    """Gera relatório editorial sintético executivo em página única, com dashboard premium e gráficos."""
    buffer = BytesIO()
    doc = SimpleDocTemplate(
        buffer,
        pagesize=landscape(A4),
        leftMargin=9 * mm,
        rightMargin=9 * mm,
        topMargin=8 * mm,
        bottomMargin=13 * mm,
    )
    s = _styles()
    counters = _counters(rows)
    risk = _overall_risk(rows)
    video_count = sum(1 for row in rows if _item_type(row) != "Portal")
    terms_total = sum(len((row.get("matched_terms") or {}).get("terms", [])) for row in rows if isinstance(row.get("matched_terms"), dict))
    label = project_label or f"Projeto: {project_id}"
    pos = counters["sentiment"].get("positivo", 0)
    neg = counters["sentiment"].get("negativo", 0)
    neu = counters["sentiment"].get("neutro", 0)

    story = []
    story.append(_hero(
        "TV Fiscal SmartReport",
        "Sintético Executivo - monitoramento editorial, clipping eletrônico e análise de reputação",
        risk,
        label,
    ))
    story.append(Spacer(1, 2 * mm))
    story.append(_kpi_cards([
        ("Itens monitorados", str(len(rows)), "clipping editorial"),
        ("Fontes", str(len(counters["sources"])), "veículos ativos"),
        ("Vídeos/Reels", str(video_count), "itens audiovisuais"),
        ("Termos", str(terms_total), "menções detectadas"),
        ("Risco", risk, "leitura reputacional"),
    ]))
    story.append(Spacer(1, 2 * mm))

    sentiment_card = _card("Distribuição por sentimento", _sentiment_pie(counters["sentiment"], width=185, height=96), width_mm=82, height_mm=38, accent=TVF_GREEN)
    topic_card = _card("Temas dominantes", _bar_chart("", counters["topics"].most_common(6), width=210, height=96, bar_color=TVF_BLUE), width_mm=88, height_mm=38, accent=TVF_BLUE)
    source_card = _card("Ranking de veículos/fontes", _bar_chart("", counters["sources"].most_common(6), width=210, height=96, bar_color=TVF_DARK), width_mm=88, height_mm=38, accent=TVF_DARK)
    row_cards = Table([[sentiment_card, topic_card, source_card]], colWidths=[84 * mm, 90 * mm, 90 * mm])
    row_cards.setStyle(TableStyle([("VALIGN", (0, 0), (-1, -1), "TOP"), ("LEFTPADDING", (0, 0), (-1, -1), 0), ("RIGHTPADDING", (0, 0), (-1, -1), 3)]))
    story.append(row_cards)
    story.append(Spacer(1, 2 * mm))

    analysis_text = Paragraph(f"<b>Análise executiva:</b> {_escape(_executive_text(rows, label))}", s["body"])
    sentiment_line = Paragraph(
        f"<b>Leitura rápida:</b> Positivo {pos} · Neutro {neu} · Negativo {neg}. Risco estimado: <font color='{_risk_palette(risk).hexval()}'><b>{_escape(risk)}</b></font>.",
        s["body"],
    )
    timeline_card = _card("Linha do tempo de exposição", _timeline_chart(counters["timeline"], width=280, height=72), width_mm=104, height_mm=29, accent=TVF_RED)
    analysis_card = _card("Leitura executiva IA", [analysis_text, Spacer(1, 0.6 * mm), sentiment_line], width_mm=158, height_mm=29, accent=TVF_BLUE)
    bottom = Table([[timeline_card, analysis_card]], colWidths=[106 * mm, 160 * mm])
    bottom.setStyle(TableStyle([("VALIGN", (0, 0), (-1, -1), "TOP"), ("LEFTPADDING", (0, 0), (-1, -1), 0), ("RIGHTPADDING", (0, 0), (-1, -1), 3)]))
    story.append(bottom)
    story.append(Spacer(1, 1.5 * mm))
    story.append(Paragraph("Ocorrências resumidas - fontes monitoradas", s["h"]))
    story.append(_synthetic_occurrence_table(rows))

    _append_premium_v3_final_analysis(story, rows, summary or {}, project_label, analytical=False)
    doc.build(story, onFirstPage=_header_footer, onLaterPages=_header_footer)
    return buffer.getvalue()


def _cover_page(story: list, title: str, subtitle: str, risk: str, project_label: str, metrics: list[tuple[str, str, str | None]]):
    story.append(_hero(title, subtitle, risk, project_label))
    story.append(Spacer(1, 5 * mm))
    story.append(_kpi_cards(metrics))


def _dashboard_block(rows: list[dict]) -> Table:
    counters = _counters(rows)
    sentiment_card = _card("Distribuição por sentimento", _sentiment_pie(counters["sentiment"], width=210, height=125), width_mm=84, height_mm=55)
    topic_card = _card("Temas dominantes", _bar_chart("", counters["topics"].most_common(6), width=226, height=125, bar_color=TVF_BLUE), width_mm=90, height_mm=55)
    source_card = _card("Ranking de veículos/fontes", _bar_chart("", counters["sources"].most_common(6), width=226, height=125, bar_color=TVF_DARK), width_mm=90, height_mm=55)
    block = Table([[sentiment_card, topic_card, source_card]], colWidths=[86 * mm, 92 * mm, 92 * mm])
    block.setStyle(TableStyle([("VALIGN", (0, 0), (-1, -1), "TOP"), ("LEFTPADDING", (0, 0), (-1, -1), 0), ("RIGHTPADDING", (0, 0), (-1, -1), 3)]))
    return block


def _clip_card(row: dict, index: int) -> Table:
    s = _styles()
    sentiment = str(row.get("sentiment") or "neutro").title()
    risk = _risk_from_row(row)
    risk_color = _risk_palette(risk)
    sent_color = _sentiment_color(sentiment)
    evidence = row.get("evidence_html_url") or row.get("url") or "-"
    title = _short(row.get("title"), 120)
    summary = _short(row.get("summary") or row.get("content_text"), 270)
    transcript = _short(_possible_transcript(row, 330), 360)
    meta = f"{_date(row.get('published_at') or row.get('created_at'))} · {_short(row.get('source_name'), 24)} · {_short(_item_type(row), 18)} · Tema: {_short(row.get('topic'), 20)}"

    left = [
        Paragraph(f"<b>{index:02d}. {_escape(title)}</b>", ParagraphStyle("ClipTitle", parent=s["body"], textColor=TVF_DARK, fontName="Helvetica-Bold", fontSize=8.2, leading=9.5)),
        Paragraph(_escape(meta), s["tiny"]),
        Spacer(1, 1.1 * mm),
        Paragraph(_escape(summary), s["small"]),
        Paragraph(_escape(transcript), s["tiny"]),
        Paragraph(f"<font color='#64748b'>Termos: {_escape(_terms_text(row))} | Evidência: {_escape(_short(evidence, 120))}</font>", s["tiny"]),
    ]
    right = [
        _badge(sentiment, sent_color),
        Spacer(1, 1.2 * mm),
        _badge(risk, risk_color),
        Spacer(1, 1.2 * mm),
        Paragraph(f"Score editorial<br/><b>{int(row.get('editorial_score') or 0)}</b>", s["center"]),
    ]
    t = Table([[left, right]], colWidths=[220 * mm, 30 * mm])
    t.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, -1), colors.white),
        ("BOX", (0, 0), (-1, -1), 0.35, TVF_BORDER),
        ("LINEBEFORE", (0, 0), (0, 0), 2.0, risk_color),
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("LEFTPADDING", (0, 0), (-1, -1), 5),
        ("RIGHTPADDING", (0, 0), (-1, -1), 5),
        ("TOPPADDING", (0, 0), (-1, -1), 5),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
    ]))
    return t


def build_editorial_analytical_pdf(project_id: str, rows: list[dict], summary: dict | None = None, project_label: str | None = None) -> bytes:
    """Gera relatório editorial analítico expandido premium com dashboard, clipping detalhado, transcrições possíveis e evidências."""
    buffer = BytesIO()
    doc = SimpleDocTemplate(
        buffer,
        pagesize=landscape(A4),
        leftMargin=9 * mm,
        rightMargin=9 * mm,
        topMargin=8 * mm,
        bottomMargin=13 * mm,
    )
    s = _styles()
    counters = _counters(rows)
    risk = _overall_risk(rows)
    video_count = sum(1 for row in rows if _item_type(row) != "Portal")
    portal_count = len(rows) - video_count
    label = project_label or f"Projeto: {project_id}"
    matched_count = sum(1 for row in rows if _terms_text(row) != "-")

    story = []
    _cover_page(story, "TV Fiscal Intelligence Report", "Analítico Expandido - clipping detalhado, dashboard, transcrições possíveis e evidências", risk, label, [
        ("Itens", str(len(rows)), "ocorrências editoriais"),
        ("Textos/Portais", str(portal_count), "conteúdo textual"),
        ("Vídeos/Reels", str(video_count), "itens audiovisuais"),
        ("Termos", str(matched_count), "com menção"),
        ("Risco", risk, "leitura reputacional"),
    ])
    story.append(Spacer(1, 5 * mm))
    story.append(_dashboard_block(rows))
    story.append(Spacer(1, 4 * mm))
    story.append(_card("Leitura analítica IA", Paragraph(_escape(_executive_text(rows, label)), s["body"]), width_mm=264, height_mm=24))
    story.append(PageBreak())

    story.append(Paragraph("Clipping analítico detalhado", s["title"]))
    story.append(Paragraph("Notícias, vídeos/reels, resumo executivo, risco, termos monitorados e transcrição possível/síntese textual.", s["subtitle"]))
    story.append(Spacer(1, 2 * mm))

    for idx, row in enumerate(rows[:32], start=1):
        story.append(KeepTogether([_clip_card(row, idx), Spacer(1, 2 * mm)]))

    story.append(PageBreak())
    story.append(Paragraph("TV Fiscal Intelligence Report - Amostras de Evidência", s["title"]))
    story.append(Paragraph("Amostras reais disponíveis usam link/evidência HTML quando capturada. Para vídeos, áudios e redes sociais, o sistema pode anexar MP3/MP4, thumbnail, QR Code, print e transcrição sincronizada quando esses ativos existirem na coleta.", s["subtitle"]))
    story.append(Spacer(1, 5 * mm))
    story.append(_evidence_samples_drawing(rows))
    story.append(Spacer(1, 5 * mm))
    methodology = (
        "<b>Nota metodológica:</b> as transcrições literais dependem do acesso aos vídeos, áudios, links completos e arquivos capturados. "
        "Neste relatório, 'transcrição possível' significa síntese textual derivada do conteúdo capturado, título, resumo, descrição pública e contexto da fonte monitorada. "
        "Quando houver captura audiovisual real, o relatório poderá incluir transcrição sincronizada, QR Code, print preservado e arquivo anexado."
    )
    story.append(_card("Metodologia e evidência", Paragraph(methodology, s["body"]), width_mm=264, height_mm=28))
    _append_premium_v3_final_analysis(story, rows, summary or {}, project_label, analytical=True)
    doc.build(story, onFirstPage=_header_footer, onLaterPages=_header_footer)
    return buffer.getvalue()


def _evidence_samples_drawing(rows: list[dict]) -> Drawing:
    d = Drawing(760, 255)
    labels = ["Print preservado / portal", "Frame MP4 / Reels", "Recorte MP3 / entrevista"]
    subtitles = ["Notícia, blog ou portal", "Vídeo, Reels, Shorts ou podcast", "Áudio, rádio ou entrevista"]
    x_positions = [15, 270, 525]
    for i, x in enumerate(x_positions):
        d.add(Rect(x, 202, 220, 30, fillColor=TVF_DARK, strokeColor=TVF_DARK))
        d.add(Rect(x, 202, 220, 3, fillColor=TVF_RED, strokeColor=TVF_RED))
        d.add(String(x + 8, 218, f"TV Fiscal WebMonitor", fontSize=7, fillColor=colors.white, fontName="Helvetica-Bold"))
        d.add(String(x + 8, 208, labels[i], fontSize=6.2, fillColor=colors.HexColor("#dbeafe")))
        d.add(Rect(x, 42, 220, 145, fillColor=colors.white, strokeColor=TVF_BORDER))
        if i == 0:
            d.add(Rect(x + 18, 158, 170, 10, fillColor=colors.HexColor("#e2e8f0"), strokeColor=colors.HexColor("#e2e8f0")))
            for line_y in [139, 119, 99, 79, 61]:
                d.add(Line(x + 18, line_y, x + 192, line_y, strokeColor=colors.HexColor("#cbd5e1"), strokeWidth=0.8))
            d.add(String(x + 18, 48, "PRINT/PNG + link original", fontSize=6.2, fillColor=TVF_GRAY))
        elif i == 1:
            d.add(Rect(x + 22, 64, 176, 104, fillColor=TVF_DARK, strokeColor=TVF_DARK))
            d.add(String(x + 91, 105, "▶", fontSize=34, fillColor=colors.white))
            d.add(String(x + 30, 70, "Frame MP4/Reels + thumbnail", fontSize=6.2, fillColor=colors.HexColor("#dbeafe")))
        else:
            for n in range(64):
                xx = x + 18 + n * 3
                h = 12 + ((n * 5) % 19)
                d.add(Line(xx, 112 - h, xx, 112 + h, strokeColor=colors.HexColor("#94a3b8"), strokeWidth=1))
            d.add(String(x + 18, 64, "Waveform MP3 + transcrição", fontSize=6.2, fillColor=TVF_GRAY))
        d.add(String(x + 10, 25, subtitles[i], fontSize=7, fillColor=TVF_DARK, fontName="Helvetica-Bold"))
        d.add(String(x + 10, 13, "Pode incluir QR Code, arquivo e transcrição sincronizada", fontSize=6.2, fillColor=TVF_GRAY))
    return d
