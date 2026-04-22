from fastapi import APIRouter, Depends, Query
from fastapi.responses import HTMLResponse, Response
from sqlalchemy.orm import Session
from app.db.session import get_db
from app.db.models import Item, Source
from weasyprint import HTML

router = APIRouter()

def build_items_report_html(project_id: str, rows, source_name=None, term=None):
    filtro_origem = source_name or "Todas"
    filtro_termo = term or "Todos"

    cards_html = ""

    for row in rows:
        matched_terms = row["matched_terms"].get("terms", []) if row.get("matched_terms") else []

        cards_html += f"""
        <div class="card">
            <div class="content">
                <h3>{row["title"]}</h3>
                <p><strong>Origem:</strong> {row["source_name"]}</p>
                <p><strong>Coletado em:</strong> {row["created_at"] or "Sem data"}</p>
                <p><strong>Termos encontrados:</strong> {", ".join(matched_terms) if matched_terms else "Nenhum"}</p>
                <p><a href="{row["url"]}" target="_blank">Abrir materia</a></p>
                <p><a href="{row.get("evidence_html_url") or "#"}" target="_blank">Evidencia HTML</a></p>
            </div>
        </div>
        """

    html = f"""
    <!DOCTYPE html>
    <html lang="pt-br">
    <head>
        <meta charset="UTF-8" />
        <title>Relatorio de Materias - TV Fiscal WebMonitor</title>
        <style>
            body {{
                font-family: Arial, sans-serif;
                background: #f4f6fa;
                margin: 0;
                padding: 30px;
                color: #222;
            }}
            h1 {{
                color: #b00020;
                margin-bottom: 8px;
            }}
            p.subtitle {{
                margin-top: 0;
                color: #555;
            }}
            .summary {{
                background: #fff;
                padding: 18px;
                border-radius: 12px;
                margin-bottom: 24px;
                box-shadow: 0 2px 10px rgba(0,0,0,0.08);
            }}
            .card {{
                background: #fff;
                border-radius: 12px;
                padding: 18px;
                margin-bottom: 18px;
                box-shadow: 0 2px 10px rgba(0,0,0,0.08);
                border-left: 6px solid #b00020;
                page-break-inside: avoid;
            }}
            .content h3 {{
                margin-top: 0;
                color: #b00020;
            }}
            .content p {{
                margin: 6px 0;
                font-size: 14px;
            }}
            a {{
                color: #0056b3;
                text-decoration: none;
            }}
            @page {{
                size: A4;
                margin: 1.2cm;
            }}
        </style>
    </head>
    <body>
        <h1>Relatorio de Materias</h1>
        <p class="subtitle">TV Fiscal WebMonitor - Monitoramento editorial digital</p>

        <div class="summary">
            <p><strong>Projeto:</strong> {project_id}</p>
            <p><strong>Total de materias listadas:</strong> {len(rows)}</p>
            <p><strong>Filtro origem:</strong> {filtro_origem}</p>
            <p><strong>Filtro termo:</strong> {filtro_termo}</p>
        </div>

        {cards_html if cards_html else "<p>Nenhuma materia encontrada para os filtros informados.</p>"}
    </body>
    </html>
    """

    return html

@router.get("/{project_id}")
def list_items(
    project_id: str,
    source_name: str | None = Query(default=None),
    term: str | None = Query(default=None),
    db: Session = Depends(get_db)
):
    query = (
        db.query(Item, Source)
        .join(Source, Item.source_id == Source.id)
        .filter(Item.project_id == project_id)
    )

    if source_name:
        query = query.filter(Source.name == source_name)

    rows = query.order_by(Item.created_at.desc()).limit(300).all()

    results = []
    for item, source in rows:
        matched_terms = item.matched_terms or {}
        terms = matched_terms.get("terms", [])

        if term:
            if term.lower() not in [t.lower() for t in terms]:
                continue

        results.append(
            {
                "title": item.title,
                "url": item.url,
                "matched_terms": item.matched_terms,
                "source_name": source.name,
                "created_at": item.created_at.isoformat() if item.created_at else None,
                "evidence_html_url": item.evidence_html_url,
            }
        )

    return results

@router.get("/report/{project_id}", response_class=HTMLResponse)
def report_items(
    project_id: str,
    source_name: str | None = Query(default=None),
    term: str | None = Query(default=None),
    db: Session = Depends(get_db)
):
    rows = list_items(project_id=project_id, source_name=source_name, term=term, db=db)
    html = build_items_report_html(project_id, rows, source_name, term)
    return html

@router.get("/report-pdf/{project_id}")
def report_items_pdf(
    project_id: str,
    source_name: str | None = Query(default=None),
    term: str | None = Query(default=None),
    db: Session = Depends(get_db)
):
    rows = list_items(project_id=project_id, source_name=source_name, term=term, db=db)
    html = build_items_report_html(project_id, rows, source_name, term)
    pdf_bytes = HTML(string=html).write_pdf()

    return Response(
        content=pdf_bytes,
        media_type="application/pdf",
        headers={
            "Content-Disposition": f'inline; filename="relatorio_materias_{project_id}.pdf"'
        },
    )

@router.delete("/clear/{project_id}")
def clear_items(project_id: str, db: Session = Depends(get_db)):
    deleted = db.query(Item).filter(Item.project_id == project_id).delete()
    db.commit()
    return {"message": "Itens removidos com sucesso", "deleted": deleted}