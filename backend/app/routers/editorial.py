from fastapi import APIRouter, Depends, Query, Request
from fastapi.responses import HTMLResponse, Response
from sqlalchemy.orm import Session

from app.core.admin_auth import require_admin_access
from app.db.session import get_db
from app.services.editorial_service import editorial_rows, editorial_summary, reclassify_editorial_items, run_editorial_collection
from app.services.editorial_report_generator import build_editorial_analytical_pdf, build_editorial_synthetic_pdf
from app.services.notification_service import evaluate_automatic_notification_rules, notification_config

router = APIRouter(prefix="/editorial", tags=["editorial"])


def _html_escape(value: object) -> str:
    import html

    return html.escape(str(value or ""))


def _report_html(project_id: str, rows: list[dict], summary: dict) -> str:
    cards = ""
    for row in rows[:80]:
        terms = ", ".join((row.get("matched_terms") or {}).get("terms", [])) or "Nenhum termo monitorado"
        cards += f"""
        <div class="card">
            <h3>{_html_escape(row.get('title'))}</h3>
            <p><strong>Fonte:</strong> {_html_escape(row.get('source_name'))}</p>
            <p><strong>Tema:</strong> {_html_escape(row.get('topic'))} · <strong>Sentimento:</strong> {_html_escape(row.get('sentiment'))} ({row.get('sentiment_score', 0)}) · <strong>Score editorial:</strong> {row.get('editorial_score', 0)}</p>
            <p><strong>Termos:</strong> {_html_escape(terms)}</p>
            <p>{_html_escape(row.get('summary'))}</p>
            <p><a href="{_html_escape(row.get('url'))}">Abrir matéria original</a></p>
        </div>
        """

    return f"""
    <!doctype html>
    <html lang="pt-br">
    <head>
      <meta charset="utf-8" />
      <title>Relatório Editorial — TV Fiscal WebMonitor</title>
      <style>
        body {{ font-family: Arial, sans-serif; color: #1f2937; margin: 0; padding: 28px; background: #f4f6fa; }}
        h1 {{ color: #b00020; margin-bottom: 6px; }}
        .subtitle {{ color: #64748b; margin-top: 0; }}
        .summary {{ display: grid; grid-template-columns: repeat(4,1fr); gap: 10px; margin: 20px 0; }}
        .metric {{ background: #fff; border-radius: 12px; padding: 16px; border-left: 5px solid #b00020; }}
        .metric small {{ color: #64748b; font-weight: 700; }}
        .metric div {{ font-size: 24px; color: #b00020; font-weight: 800; margin-top: 6px; }}
        .card {{ background: #fff; border-radius: 12px; padding: 16px; margin-bottom: 14px; page-break-inside: avoid; border-left: 5px solid #1f4e79; }}
        .card h3 {{ margin: 0 0 8px; color: #111827; }}
        .card p {{ font-size: 13px; line-height: 1.5; margin: 5px 0; }}
        a {{ color: #1f4e79; text-decoration: none; font-weight: 700; }}
        @page {{ size: A4; margin: 1.1cm; }}
      </style>
    </head>
    <body>
      <h1>TV Fiscal WebMonitor — Relatório Editorial</h1>
      <p class="subtitle">Projeto: {_html_escape(project_id)} · Monitoramento de notícias, menções e clipping eletrônico.</p>
      <div class="summary">
        <div class="metric"><small>Matérias</small><div>{summary.get('total_items', 0)}</div></div>
        <div class="metric"><small>Termos encontrados</small><div>{summary.get('total_terms', 0)}</div></div>
        <div class="metric"><small>Fontes</small><div>{summary.get('sources_count', 0)}</div></div>
        <div class="metric"><small>Temas</small><div>{summary.get('topics_count', 0)}</div></div>
      </div>
      {cards if cards else '<p>Nenhuma matéria encontrada no recorte.</p>'}
      <p class="subtitle">Relatório gerado automaticamente pela plataforma TV Fiscal WebMonitor.</p>
    </body>
    </html>
    """


@router.get("/summary/{project_id}")
def summary(project_id: str, db: Session = Depends(get_db)):
    return editorial_summary(db, project_id)


@router.get("/items/{project_id}")
def list_editorial_items(
    project_id: str,
    q: str | None = Query(default=None),
    source_name: str | None = Query(default=None),
    term: str | None = Query(default=None),
    sentiment: str | None = Query(default=None),
    topic: str | None = Query(default=None),
    date_from: str | None = Query(default=None),
    date_to: str | None = Query(default=None),
    limit: int = Query(default=300, ge=1, le=1000),
    db: Session = Depends(get_db),
):
    return editorial_rows(
        db=db,
        project_id=project_id,
        q=q,
        source_name=source_name,
        term=term,
        sentiment=sentiment,
        topic=topic,
        date_from=date_from,
        date_to=date_to,
        limit=limit,
    )


@router.post("/run/{project_id}")
def run_editorial_scan(
    project_id: str,
    request: Request,
    collect_all: bool = Query(default=True),
    limit_per_source: int = Query(default=25, ge=1, le=80),
    db: Session = Depends(get_db),
):
    require_admin_access(request)
    result = run_editorial_collection(
        db=db,
        project_id=project_id,
        collect_all=collect_all,
        limit_per_source=limit_per_source,
    )
    try:
        if notification_config().get("auto_after_editorial"):
            result["notifications"] = evaluate_automatic_notification_rules(db, project_id, trigger_source="editorial_run")
    except Exception as exc:
        result["notifications"] = {"error": str(exc), "message": "Coleta editorial concluída, mas a avaliação de notificações falhou."}
    return result


@router.post("/reclassify/{project_id}")
def reclassify_editorial_quality(
    project_id: str,
    request: Request,
    delete_listing_pages: bool = Query(default=True),
    db: Session = Depends(get_db),
):
    require_admin_access(request)
    return reclassify_editorial_items(db, project_id, delete_listing_pages=delete_listing_pages)


@router.get("/report/{project_id}", response_class=HTMLResponse)
def editorial_report_html(
    project_id: str,
    q: str | None = Query(default=None),
    source_name: str | None = Query(default=None),
    term: str | None = Query(default=None),
    sentiment: str | None = Query(default=None),
    topic: str | None = Query(default=None),
    db: Session = Depends(get_db),
):
    rows = editorial_rows(db, project_id, q=q, source_name=source_name, term=term, sentiment=sentiment, topic=topic, limit=500)
    summary = editorial_summary(db, project_id)
    return _report_html(project_id, rows, summary)


def _build_editorial_pdf(project_id: str, rows: list[dict], summary: dict) -> bytes:
    """Gera PDF editorial com ReportLab.

    Evita importar WeasyPrint no startup do FastAPI, pois em alguns ambientes Docker
    a ausência de bibliotecas nativas do Cairo/Pango derruba o backend antes da API subir.
    """
    from io import BytesIO

    from reportlab.lib import colors
    from reportlab.lib.pagesizes import A4
    from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
    from reportlab.lib.units import mm
    from reportlab.platypus import Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle

    buffer = BytesIO()
    doc = SimpleDocTemplate(
        buffer,
        pagesize=A4,
        rightMargin=12 * mm,
        leftMargin=12 * mm,
        topMargin=12 * mm,
        bottomMargin=12 * mm,
    )
    styles = getSampleStyleSheet()
    title_style = ParagraphStyle("TVFTitle", parent=styles["Title"], textColor=colors.HexColor("#b00020"), fontSize=18, leading=22)
    subtitle_style = ParagraphStyle("TVFSubtitle", parent=styles["Normal"], textColor=colors.HexColor("#64748b"), fontSize=9, leading=12)
    h_style = ParagraphStyle("TVFH", parent=styles["Heading2"], textColor=colors.HexColor("#1f4e79"), fontSize=12, leading=15, spaceBefore=8)
    body_style = ParagraphStyle("TVFBody", parent=styles["Normal"], textColor=colors.HexColor("#1f2937"), fontSize=8, leading=10)
    small_style = ParagraphStyle("TVFSmall", parent=styles["Normal"], textColor=colors.HexColor("#475569"), fontSize=7, leading=9)

    story = []
    story.append(Paragraph("TV Fiscal WebMonitor — Relatório Editorial", title_style))
    story.append(Paragraph(f"Projeto: {_html_escape(project_id)} · Monitoramento de notícias, menções e clipping eletrônico.", subtitle_style))
    story.append(Spacer(1, 7 * mm))

    metrics = [
        ["Matérias", str(summary.get("total_items", 0))],
        ["Termos", str(summary.get("total_terms", 0))],
        ["Fontes", str(summary.get("sources_count", 0))],
        ["Temas", str(summary.get("topics_count", 0))],
    ]
    metric_table = Table(metrics, colWidths=[32 * mm, 25 * mm] * 0 or [35 * mm, 25 * mm])
    metric_table.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, -1), colors.HexColor("#fff7f7")),
        ("TEXTCOLOR", (0, 0), (-1, -1), colors.HexColor("#111827")),
        ("GRID", (0, 0), (-1, -1), 0.25, colors.HexColor("#e5e7eb")),
        ("FONTNAME", (0, 0), (-1, -1), "Helvetica-Bold"),
        ("FONTSIZE", (0, 0), (-1, -1), 8),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("LEFTPADDING", (0, 0), (-1, -1), 7),
        ("RIGHTPADDING", (0, 0), (-1, -1), 7),
    ]))
    story.append(metric_table)
    story.append(Spacer(1, 6 * mm))

    if not rows:
        story.append(Paragraph("Nenhuma matéria encontrada no recorte.", body_style))
    else:
        story.append(Paragraph("Matérias monitoradas", h_style))
        for row in rows[:80]:
            terms = ", ".join((row.get("matched_terms") or {}).get("terms", [])) or "Nenhum termo monitorado"
            story.append(Paragraph(_html_escape(row.get("title") or "Sem título"), h_style))
            story.append(Paragraph(
                f"Fonte: {_html_escape(row.get('source_name'))} · Tema: {_html_escape(row.get('topic'))} · "
                f"Sentimento: {_html_escape(row.get('sentiment'))} ({row.get('sentiment_score', 0)}) · "
                f"Score editorial: {row.get('editorial_score', 0)}",
                small_style,
            ))
            story.append(Paragraph(f"Termos: {_html_escape(terms)}", small_style))
            story.append(Paragraph(_html_escape(row.get("summary") or "Sem resumo."), body_style))
            story.append(Paragraph(f"URL: {_html_escape(row.get('url'))}", small_style))
            story.append(Spacer(1, 3 * mm))

    story.append(Spacer(1, 5 * mm))
    story.append(Paragraph("Relatório gerado automaticamente pela plataforma TV Fiscal WebMonitor.", subtitle_style))
    doc.build(story)
    return buffer.getvalue()


@router.get("/report-pdf/{project_id}")
def editorial_report_pdf(
    project_id: str,
    q: str | None = Query(default=None),
    source_name: str | None = Query(default=None),
    term: str | None = Query(default=None),
    sentiment: str | None = Query(default=None),
    topic: str | None = Query(default=None),
    db: Session = Depends(get_db),
):
    rows = editorial_rows(db, project_id, q=q, source_name=source_name, term=term, sentiment=sentiment, topic=topic, limit=500)
    summary = editorial_summary(db, project_id)
    pdf_bytes = _build_editorial_pdf(project_id, rows, summary)
    return Response(
        content=pdf_bytes,
        media_type="application/pdf",
        headers={"Content-Disposition": f'inline; filename="relatorio_editorial_{project_id}.pdf"'},
    )


def _editorial_filtered_rows(
    db: Session,
    project_id: str,
    q: str | None,
    source_name: str | None,
    term: str | None,
    sentiment: str | None,
    topic: str | None,
    date_from: str | None,
    date_to: str | None,
    limit: int = 800,
) -> list[dict]:
    return editorial_rows(
        db=db,
        project_id=project_id,
        q=q,
        source_name=source_name,
        term=term,
        sentiment=sentiment,
        topic=topic,
        date_from=date_from,
        date_to=date_to,
        limit=limit,
    )


@router.get("/report-synthetic-pdf/{project_id}")
@router.get("/report-sintetico-pdf/{project_id}")
def editorial_report_synthetic_pdf(
    project_id: str,
    q: str | None = Query(default=None),
    source_name: str | None = Query(default=None),
    term: str | None = Query(default=None),
    sentiment: str | None = Query(default=None),
    topic: str | None = Query(default=None),
    date_from: str | None = Query(default=None),
    date_to: str | None = Query(default=None),
    db: Session = Depends(get_db),
):
    rows = _editorial_filtered_rows(db, project_id, q, source_name, term, sentiment, topic, date_from, date_to)
    summary = editorial_summary(db, project_id)
    pdf_bytes = build_editorial_synthetic_pdf(project_id, rows, summary)
    return Response(
        content=pdf_bytes,
        media_type="application/pdf",
        headers={"Content-Disposition": f'inline; filename="editorial_sintetico_{project_id}.pdf"'},
    )


@router.get("/report-analytical-pdf/{project_id}")
@router.get("/report-analitico-pdf/{project_id}")
def editorial_report_analytical_pdf(
    project_id: str,
    q: str | None = Query(default=None),
    source_name: str | None = Query(default=None),
    term: str | None = Query(default=None),
    sentiment: str | None = Query(default=None),
    topic: str | None = Query(default=None),
    date_from: str | None = Query(default=None),
    date_to: str | None = Query(default=None),
    db: Session = Depends(get_db),
):
    rows = _editorial_filtered_rows(db, project_id, q, source_name, term, sentiment, topic, date_from, date_to)
    summary = editorial_summary(db, project_id)
    pdf_bytes = build_editorial_analytical_pdf(project_id, rows, summary)
    return Response(
        content=pdf_bytes,
        media_type="application/pdf",
        headers={"Content-Disposition": f'inline; filename="editorial_analitico_{project_id}.pdf"'},
    )


@router.delete("/clear/{project_id}")
def clear_editorial_items(project_id: str, request: Request, db: Session = Depends(get_db)):
    require_admin_access(request)
    from app.db.models import Item
    import uuid

    project_uuid = uuid.UUID(project_id)
    deleted = db.query(Item).filter(Item.project_id == project_uuid).delete()
    db.commit()
    return {"deleted": deleted, "message": "Matérias removidas com sucesso."}
