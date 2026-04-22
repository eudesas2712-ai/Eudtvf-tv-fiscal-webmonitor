from html import escape
from io import BytesIO

from fastapi import APIRouter, Depends, Query
from fastapi.responses import HTMLResponse, Response
from sqlalchemy.orm import Session

from app.db.models import BannerItem
from app.db.session import get_db

router = APIRouter(prefix="/banners", tags=["Banners"])


def _normalize_confidence(value: str | None) -> str:
    raw = (value or "").strip().lower()

    mapping = {
        "alta": "alta",
        "high": "alta",
        "media": "media",
        "média": "media",
        "medium": "media",
        "baixa": "baixa",
        "low": "baixa",
    }

    return mapping.get(raw, "não informado")


def detect_confidence_and_evidence(item: BannerItem) -> tuple[str, str | None]:
    confidence = None

    for attr in (
        "detection_confidence",
        "confidence",
        "identification_confidence",
        "match_confidence",
        "recognition_confidence",
        "quality",
    ):
        value = getattr(item, attr, None)
        if isinstance(value, str) and value.strip():
            confidence = value
            break

    if not confidence:
        score = getattr(item, "classification_score", None)

        try:
            score_num = float(score) if score is not None else None
        except (TypeError, ValueError):
            score_num = None

        if score_num is not None:
            if score_num >= 12:
                confidence = "alta"
            elif score_num >= 8:
                confidence = "media"
            else:
                confidence = "baixa"
        else:
            advertiser = (getattr(item, "advertiser_name", None) or "").strip().lower()
            if advertiser and advertiser not in {"nao identificado", "não identificado"}:
                confidence = "media"
            else:
                confidence = "baixa"

    evidence = None
    for attr in (
        "screenshot_banner_url",
        "evidence_html_url",
        "screenshot_page_url",
        "image_url",
        "evidence_url",
        "preview_url",
        "url",
        "link",
        "source_url",
        "page_url",
    ):
        value = getattr(item, attr, None)
        if isinstance(value, str) and value.strip():
            evidence = value
            break

    return _normalize_confidence(confidence), evidence


def _format_brl(value: int | float | None) -> str:
    value = value or 0
    return f"R$ {value:,.0f}".replace(",", ".")

def _is_publicity_classification(value: str | None) -> bool:
    raw = (value or "").strip().lower()

    if not raw:
        return True

    editorial_labels = {
        "editorial",
        "noticia",
        "notícia",
        "materia",
        "matéria",
        "conteudo editorial",
        "conteúdo editorial",
        "jornalismo",
        "post editorial",
    }

    return raw not in editorial_labels


def _serialize_banner(row: BannerItem) -> dict:
    confidence, evidence = detect_confidence_and_evidence(row)

    created_at = getattr(row, "created_at", None)
    created_at_iso = created_at.isoformat() if created_at else None

    return {
        "id": str(getattr(row, "id", "") or ""),
        "project_id": str(getattr(row, "project_id", "") or ""),
        "page_url": getattr(row, "page_url", None),
        "image_url": getattr(row, "image_url", None),
        "alt_text": getattr(row, "alt_text", None),
        "width": getattr(row, "width", None),
        "height": getattr(row, "height", None),
        "normalized_width": getattr(row, "normalized_width", None),
        "normalized_height": getattr(row, "normalized_height", None),
        "estimated_value": getattr(row, "estimated_value", None),
        "pos_x": getattr(row, "pos_x", None),
        "pos_y": getattr(row, "pos_y", None),
        "source_name": getattr(row, "source_name", None),
        "evidence_html_key": getattr(row, "evidence_html_key", None),
        "evidence_html_url": getattr(row, "evidence_html_url", None),
        "screenshot_page_key": getattr(row, "screenshot_page_key", None),
        "screenshot_page_url": getattr(row, "screenshot_page_url", None),
        "screenshot_banner_key": getattr(row, "screenshot_banner_key", None),
        "screenshot_banner_url": getattr(row, "screenshot_banner_url", None),
        "ocr_text": getattr(row, "ocr_text", None),
        "advertiser_name": getattr(row, "advertiser_name", None),
        "classification": getattr(row, "classification", None),
        "classification_score": getattr(row, "classification_score", None),
        "classification_reason": getattr(row, "classification_reason", None),
        "detection_confidence": confidence,
        "detection_evidence": evidence,
        "created_at": created_at_iso,
    }


def _get_banner_rows(
    project_id: str,
    db: Session,
    advertiser_name: str | None = None,
    source_name: str | None = None,
    format_size: str | None = None,
    classification: str | None = None,
    limit: int = 300,
):
    query = db.query(BannerItem).filter(BannerItem.project_id == project_id)

    if advertiser_name:
        query = query.filter(BannerItem.advertiser_name == advertiser_name)

    if source_name:
        query = query.filter(BannerItem.source_name == source_name)

    if classification:
        query = query.filter(BannerItem.classification == classification)

    rows = query.order_by(BannerItem.created_at.desc()).all()

    filtered_rows = []
    for row in rows:
        current_classification = getattr(row, "classification", None)
        if not _is_publicity_classification(current_classification):
            continue

        current_format = f"{getattr(row, 'width', 0) or 0}x{getattr(row, 'height', 0) or 0}"
        if format_size and current_format != format_size:
            continue

        filtered_rows.append(_serialize_banner(row))

        if len(filtered_rows) >= limit:
            break

    return filtered_rows

def _get_banner_by_id(db: Session, banner_id: str) -> BannerItem | None:
    return db.query(BannerItem).filter(BannerItem.id == banner_id).first()

@router.get("/{project_id}")
def list_banners(
    project_id: str,
    advertiser_name: str | None = Query(default=None),
    source_name: str | None = Query(default=None),
    format_size: str | None = Query(default=None),
    classification: str | None = Query(default=None),
    limit: int = Query(default=300, ge=1, le=1000),
    db: Session = Depends(get_db),
):
    return _get_banner_rows(
        project_id=project_id,
        db=db,
        advertiser_name=advertiser_name,
        source_name=source_name,
        format_size=format_size,
        classification=classification,
        limit=limit,
    )


@router.get("/item/{banner_id}")
def get_banner_item(
    banner_id: str,
    db: Session = Depends(get_db),
):
    row = _get_banner_by_id(db, banner_id)
    if not row:
        return {"error": "Banner não encontrado"}

    return _serialize_banner(row)

@router.get("/report/{project_id}", response_class=HTMLResponse)
def report_banners_html(
    project_id: str,
    advertiser_name: str | None = Query(default=None),
    source_name: str | None = Query(default=None),
    format_size: str | None = Query(default=None),
    classification: str | None = Query(default=None),
    db: Session = Depends(get_db),
):
    rows = _get_banner_rows(
        project_id=project_id,
        db=db,
        advertiser_name=advertiser_name,
        source_name=source_name,
        format_size=format_size,
        classification=classification,
        limit=500,
    )

    total_items = len(rows)
    total_value = sum((row.get("estimated_value") or 0) for row in rows)

    html_rows = []
    for row in rows:
        advertiser = escape(str(row.get("advertiser_name") or "Nao identificado"))
        portal = escape(str(row.get("source_name") or "Desconhecido"))
        description = escape(str(row.get("classification") or "Sem classificação"))
        created_at = escape(str(row.get("created_at") or "-"))
        confidence = escape(str(row.get("detection_confidence") or "não informado"))
        value = _format_brl(row.get("estimated_value") or 0)
        evidence = row.get("detection_evidence") or row.get("screenshot_banner_url") or row.get("image_url") or row.get("page_url")

        evidence_html = (
            f'<a href="{escape(str(evidence))}" target="_blank" rel="noreferrer">Abrir</a>'
            if evidence
            else "<span>Sem link</span>"
        )

        html_rows.append(
            f"""
            <tr>
              <td>{advertiser}</td>
              <td>{portal}</td>
              <td>{description}</td>
              <td>{created_at}</td>
              <td>{confidence}</td>
              <td>{value}</td>
              <td>{evidence_html}</td>
            </tr>
            """
        )

    html = f"""
    <!doctype html>
    <html lang="pt-BR">
    <head>
      <meta charset="utf-8" />
      <title>Relatório de Evidências de Banners</title>
      <style>
        body {{
          font-family: Arial, Helvetica, sans-serif;
          margin: 0;
          padding: 24px;
          background: #f6f7fb;
          color: #1f2937;
        }}
        .wrap {{
          max-width: 1280px;
          margin: 0 auto;
        }}
        .hero {{
          background: linear-gradient(135deg, #7a1118 0%, #b91c1c 45%, #d93636 100%);
          color: #fff;
          border-radius: 24px;
          padding: 28px;
          margin-bottom: 24px;
        }}
        .eyebrow {{
          font-size: 12px;
          letter-spacing: 0.18em;
          text-transform: uppercase;
          font-weight: 700;
          opacity: 0.9;
        }}
        h1 {{
          margin: 10px 0 8px;
          font-size: 38px;
        }}
        p {{
          margin: 0;
          font-size: 16px;
          opacity: 0.92;
        }}
        .summary {{
          display: grid;
          grid-template-columns: repeat(2, minmax(0, 1fr));
          gap: 16px;
          margin-bottom: 24px;
        }}
        .card {{
          background: #fff;
          border: 1px solid #e5e7eb;
          border-radius: 18px;
          padding: 18px 20px;
        }}
        .label {{
          font-size: 12px;
          text-transform: uppercase;
          letter-spacing: 0.12em;
          color: #6b7280;
        }}
        .value {{
          margin-top: 8px;
          font-size: 28px;
          font-weight: 800;
          color: #111827;
        }}
        table {{
          width: 100%;
          border-collapse: collapse;
          background: #fff;
          border-radius: 18px;
          overflow: hidden;
          border: 1px solid #e5e7eb;
        }}
        thead {{
          background: #c52625;
          color: #fff;
        }}
        th, td {{
          text-align: left;
          padding: 12px 10px;
          border-bottom: 1px solid #eef0f4;
          vertical-align: top;
          font-size: 14px;
        }}
        th {{
          font-size: 13px;
        }}
        a {{
          color: #991b1b;
          font-weight: 700;
          text-decoration: none;
        }}
      </style>
    </head>
    <body>
      <div class="wrap">
        <section class="hero">
          <div class="eyebrow">TV Fiscal WebMonitor</div>
          <h1>Relatório de Evidências de Banners</h1>
          <p>Projeto monitorado: {escape(project_id)}</p>
        </section>

        <section class="summary">
          <div class="card">
            <div class="label">Evidências listadas</div>
            <div class="value">{total_items}</div>
          </div>
          <div class="card">
            <div class="label">Investimento estimado</div>
            <div class="value">{_format_brl(total_value)}</div>
          </div>
        </section>

        <table>
          <thead>
            <tr>
              <th>Anunciante</th>
              <th>Portal</th>
              <th>Descrição</th>
              <th>Data</th>
              <th>Confiança</th>
              <th>Valor</th>
              <th>Evidência</th>
            </tr>
          </thead>
          <tbody>
            {''.join(html_rows) if html_rows else '<tr><td colspan="7">Nenhuma evidência encontrada.</td></tr>'}
          </tbody>
        </table>
      </div>
    </body>
    </html>
    """
    return HTMLResponse(content=html)


@router.get("/report-pdf/{project_id}")
def report_banners_pdf(
    project_id: str,
    advertiser_name: str | None = Query(default=None),
    source_name: str | None = Query(default=None),
    format_size: str | None = Query(default=None),
    classification: str | None = Query(default=None),
    db: Session = Depends(get_db),
):
    from reportlab.lib import colors
    from reportlab.lib.pagesizes import A4, landscape
    from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
    from reportlab.lib.units import mm
    from reportlab.platypus import Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle

    rows = _get_banner_rows(
        project_id=project_id,
        db=db,
        advertiser_name=advertiser_name,
        source_name=source_name,
        format_size=format_size,
        classification=classification,
        limit=500,
    )

    total_items = len(rows)
    total_value = sum((row.get("estimated_value") or 0) for row in rows)

    buffer = BytesIO()
    doc = SimpleDocTemplate(
        buffer,
        pagesize=landscape(A4),
        leftMargin=16 * mm,
        rightMargin=16 * mm,
        topMargin=14 * mm,
        bottomMargin=12 * mm,
    )

    styles = getSampleStyleSheet()

    title_style = ParagraphStyle(
        "title_style",
        parent=styles["Heading1"],
        fontName="Helvetica-Bold",
        fontSize=24,
        leading=28,
        textColor=colors.white,
    )

    brand_style = ParagraphStyle(
        "brand_style",
        parent=styles["Normal"],
        fontName="Helvetica-Bold",
        fontSize=10,
        leading=12,
        textColor=colors.white,
    )

    subtitle_style = ParagraphStyle(
        "subtitle_style",
        parent=styles["Normal"],
        fontName="Helvetica",
        fontSize=11,
        leading=14,
        textColor=colors.HexColor("#4B5563"),
    )

    label_style = ParagraphStyle(
        "label_style",
        parent=styles["Normal"],
        fontName="Helvetica",
        fontSize=9,
        leading=11,
        textColor=colors.HexColor("#6B7280"),
    )

    value_style = ParagraphStyle(
        "value_style",
        parent=styles["Normal"],
        fontName="Helvetica-Bold",
        fontSize=20,
        leading=24,
        textColor=colors.HexColor("#111827"),
    )

    value_red_style = ParagraphStyle(
        "value_red_style",
        parent=value_style,
        textColor=colors.HexColor("#C52625"),
    )

    section_style = ParagraphStyle(
        "section_style",
        parent=styles["Heading2"],
        fontName="Helvetica-Bold",
        fontSize=14,
        leading=18,
        textColor=colors.HexColor("#111827"),
        spaceAfter=8,
    )

    table_header_style = ParagraphStyle(
        "table_header_style",
        parent=styles["Normal"],
        fontName="Helvetica-Bold",
        fontSize=9,
        leading=11,
        textColor=colors.white,
    )

    table_cell_style = ParagraphStyle(
        "table_cell_style",
        parent=styles["Normal"],
        fontName="Helvetica",
        fontSize=8.5,
        leading=10,
        textColor=colors.HexColor("#111827"),
    )

    story = []

    header = Table(
        [[
            Paragraph("TV Fiscal WebMonitor", brand_style),
            Paragraph("Relatório de Evidências de Banners", title_style),
        ]],
        colWidths=[60 * mm, 200 * mm],
    )
    header.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, -1), colors.HexColor("#C52625")),
        ("LEFTPADDING", (0, 0), (-1, -1), 14),
        ("RIGHTPADDING", (0, 0), (-1, -1), 14),
        ("TOPPADDING", (0, 0), (-1, -1), 12),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 14),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
    ]))
    story.append(header)
    story.append(Spacer(1, 8))
    story.append(Paragraph(f"<b>Projeto monitorado:</b> {escape(project_id)}", subtitle_style))
    story.append(Spacer(1, 6))

    summary = Table(
        [[
            Paragraph("Evidências listadas", label_style),
            Paragraph("Investimento estimado", label_style),
        ],
        [
            Paragraph(str(total_items), value_style),
            Paragraph(_format_brl(total_value), value_red_style),
        ]],
        colWidths=[60 * mm, 70 * mm],
    )
    summary.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, -1), colors.white),
        ("BOX", (0, 0), (-1, -1), 0.6, colors.HexColor("#E5E7EB")),
        ("INNERGRID", (0, 0), (-1, -1), 0.4, colors.HexColor("#E5E7EB")),
        ("LEFTPADDING", (0, 0), (-1, -1), 12),
        ("RIGHTPADDING", (0, 0), (-1, -1), 12),
        ("TOPPADDING", (0, 0), (-1, -1), 10),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 10),
    ]))
    story.append(summary)
    story.append(Spacer(1, 12))
    story.append(Paragraph("Evidências monitoradas", section_style))

    data = [[
        Paragraph("Anunciante", table_header_style),
        Paragraph("Portal", table_header_style),
        Paragraph("Descrição", table_header_style),
        Paragraph("Data", table_header_style),
        Paragraph("Confiança", table_header_style),
        Paragraph("Valor", table_header_style),
    ]]

    for row in rows[:80]:
        data.append([
            Paragraph(escape(str(row.get("advertiser_name") or "Nao identificado")), table_cell_style),
            Paragraph(escape(str(row.get("source_name") or "Desconhecido")), table_cell_style),
            Paragraph(escape(str(row.get("classification") or "Sem classificação")), table_cell_style),
            Paragraph(escape(str(row.get("created_at") or "-")), table_cell_style),
            Paragraph(escape(str(row.get("detection_confidence") or "não informado")), table_cell_style),
            Paragraph(_format_brl(row.get("estimated_value") or 0), table_cell_style),
        ])

    table = Table(
        data,
        colWidths=[48 * mm, 48 * mm, 50 * mm, 40 * mm, 26 * mm, 24 * mm],
        repeatRows=1,
    )
    table.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#C52625")),
        ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
        ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, colors.HexColor("#F9FAFB")]),
        ("BOX", (0, 0), (-1, -1), 0.6, colors.HexColor("#E5E7EB")),
        ("INNERGRID", (0, 0), (-1, -1), 0.35, colors.HexColor("#E5E7EB")),
        ("LEFTPADDING", (0, 0), (-1, -1), 6),
        ("RIGHTPADDING", (0, 0), (-1, -1), 6),
        ("TOPPADDING", (0, 0), (-1, -1), 5),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
    ]))
    story.append(table)

    doc.build(story)

    pdf_bytes = buffer.getvalue()
    buffer.close()

    return Response(
        content=pdf_bytes,
        media_type="application/pdf",
        headers={
            "Content-Disposition": f'inline; filename="banners_report_{project_id}.pdf"'
        },
    )