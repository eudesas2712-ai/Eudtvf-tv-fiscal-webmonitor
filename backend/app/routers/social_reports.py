
from io import BytesIO
from datetime import datetime

from fastapi import APIRouter, Depends, Query
from fastapi.responses import Response
from sqlalchemy import text
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.services.report_storage_service import save_generated_pdf_report

router = APIRouter(prefix="/social/reports", tags=["Social Reports"])

RED = "#C52625"
DARK = "#111827"
MUTED = "#6B7280"


def safe(value, limit=120):
    if value is None:
        return "-"
    value = str(value).replace("\n", " ").replace("\r", " ").strip()
    return value[: limit - 3] + "..." if len(value) > limit else value


def fmt_int(value):
    try:
        return f"{int(value):,}".replace(",", ".")
    except Exception:
        return "0"


def fmt_dt(value):
    if not value:
        return "-"
    try:
        return value.strftime("%d/%m/%Y %H:%M")
    except Exception:
        return str(value)[:19].replace("T", " ")


def project_name(db: Session, project_id: str):
    row = db.execute(
        text("SELECT name FROM projects WHERE id = CAST(:project_id AS uuid) LIMIT 1"),
        {"project_id": project_id},
    ).fetchone()
    return row[0] if row and row[0] else f"Projeto {project_id[:8]}"



def _social_where(project_id: str, platform=None, q=None, source_id=None, date_from=None, date_to=None):
    where = ["project_id = CAST(:project_id AS uuid)"]
    params = {"project_id": project_id}

    if platform:
        where.append("platform = :platform")
        params["platform"] = platform

    if source_id:
        where.append("source_id = CAST(:source_id AS uuid)")
        params["source_id"] = source_id

    if q:
        where.append("""
            (
              COALESCE(title, '') ILIKE :q_like
              OR COALESCE(text, '') ILIKE :q_like
              OR COALESCE(author_name, '') ILIKE :q_like
              OR COALESCE(author_handle, '') ILIKE :q_like
            )
        """)
        params["q_like"] = "%" + q.strip() + "%"

    if date_from:
        where.append("COALESCE(published_at, created_at) >= CAST(:date_from AS timestamptz)")
        params["date_from"] = date_from

    if date_to:
        where.append("COALESCE(published_at, created_at) < CAST(:date_to AS timestamptz) + INTERVAL '1 day'")
        params["date_to"] = date_to

    return " AND ".join(where), params


def summary(db: Session, project_id: str, platform=None, q=None, source_id=None, date_from=None, date_to=None):
    where_sql, params = _social_where(project_id, platform, q, source_id, date_from, date_to)
    row = db.execute(
        text(f"""
            SELECT
                COUNT(*)::int AS total_items,
                COUNT(DISTINCT COALESCE(author_name, author_handle, 'Não identificado'))::int AS total_channels,
                COUNT(*) FILTER (WHERE platform = 'youtube')::int AS youtube_items,
                COALESCE(SUM(
                    CASE
                        WHEN (metrics_json->'statistics'->>'viewCount') ~ '^[0-9]+$'
                        THEN (metrics_json->'statistics'->>'viewCount')::bigint
                        ELSE 0
                    END
                ), 0)::bigint AS total_views
            FROM social_items
            WHERE {where_sql}
        """),
        params,
    ).fetchone()
    return dict(row._mapping) if row else {
        "total_items": 0,
        "total_channels": 0,
        "youtube_items": 0,
        "total_views": 0,
    }


def top_channels(db: Session, project_id: str, platform=None, q=None, source_id=None, date_from=None, date_to=None):
    where_sql, params = _social_where(project_id, platform, q, source_id, date_from, date_to)
    rows = db.execute(
        text(f"""
            SELECT
                COALESCE(author_name, author_handle, 'Não identificado') AS channel,
                COUNT(*)::int AS total
            FROM social_items
            WHERE {where_sql}
            GROUP BY COALESCE(author_name, author_handle, 'Não identificado')
            ORDER BY total DESC
            LIMIT 10
        """),
        params,
    ).fetchall()
    return [dict(r._mapping) for r in rows]


def latest_items(db: Session, project_id: str, limit: int, platform=None, q=None, source_id=None, date_from=None, date_to=None):
    where_sql, params = _social_where(project_id, platform, q, source_id, date_from, date_to)
    params["limit"] = limit
    rows = db.execute(
        text(f"""
            SELECT
                platform,
                title,
                author_name,
                author_handle,
                url,
                published_at,
                created_at,
                text AS description
            FROM social_items
            WHERE {where_sql}
            ORDER BY COALESCE(published_at, created_at) DESC
            LIMIT :limit
        """),
        params,
    ).fetchall()
    return [dict(r._mapping) for r in rows]

def pdf_start(title, subtitle):
    from reportlab.lib.pagesizes import A4, landscape
    from reportlab.pdfgen import canvas
    from reportlab.lib import colors

    buffer = BytesIO()
    c = canvas.Canvas(buffer, pagesize=landscape(A4))
    width, height = landscape(A4)

    c.setFillColor(colors.HexColor(RED))
    c.rect(0, height - 64, width, 64, fill=1, stroke=0)

    c.setFillColor(colors.white)
    c.setFont("Helvetica-Bold", 16)
    c.drawString(32, height - 35, title)

    c.setFont("Helvetica", 9)
    c.drawRightString(width - 32, height - 28, "TV Fiscal WebMonitor")
    c.drawRightString(width - 32, height - 44, "Social Monitor")

    c.setFillColor(colors.HexColor(DARK))
    c.setFont("Helvetica", 9)
    c.drawString(32, height - 84, subtitle)

    return c, buffer, width, height, colors


def footer(c, width, page, colors):
    c.setStrokeColor(colors.HexColor("#E5E7EB"))
    c.line(32, 28, width - 32, 28)
    c.setFillColor(colors.HexColor(MUTED))
    c.setFont("Helvetica", 8)
    c.drawString(32, 16, "TV Fiscal - Social Monitor")
    c.drawRightString(width - 32, 16, f"Página {page}")


@router.get("/synthetic-v3/{project_id}")
def synthetic_v3(
    project_id: str,
    platform: str | None = Query(default=None),
    q: str | None = Query(default=None),
    source_id: str | None = Query(default=None),
    date_from: str | None = Query(default=None),
    date_to: str | None = Query(default=None),
    db: Session = Depends(get_db),
):
    name = project_name(db, project_id)
    data = summary(db, project_id, platform, q, source_id, date_from, date_to)
    channels = top_channels(db, project_id, platform, q, source_id, date_from, date_to)
    items = latest_items(db, project_id, 12, platform, q, source_id, date_from, date_to)

    c, buffer, width, height, colors = pdf_start(
        "Relatório Social Sintético Executivo Premium V3",
        f"{name} - Gerado em {datetime.now().strftime('%d/%m/%Y %H:%M')}",
    )

    y = height - 135
    x = 32

    for label, value in [
        ("Itens sociais", data["total_items"]),
        ("Canais", data["total_channels"]),
        ("YouTube", data["youtube_items"]),
        ("Visualizações", data["total_views"]),
    ]:
        c.setFillColor(colors.white)
        c.roundRect(x, y, 170, 58, 10, fill=1, stroke=1)
        c.setFillColor(colors.HexColor(RED))
        c.setFont("Helvetica-Bold", 18)
        c.drawString(x + 12, y + 32, fmt_int(value))
        c.setFillColor(colors.HexColor(MUTED))
        c.setFont("Helvetica", 8)
        c.drawString(x + 12, y + 14, label)
        x += 190

    y -= 55
    c.setFillColor(colors.HexColor(DARK))
    c.setFont("Helvetica-Bold", 12)
    c.drawString(32, y, "Top canais/fontes sociais")
    y -= 20

    c.setFont("Helvetica", 8)
    for row in channels:
        c.drawString(36, y, safe(row["channel"], 75))
        c.drawRightString(620, y, fmt_int(row["total"]))
        y -= 15

    y -= 18
    c.setFont("Helvetica-Bold", 12)
    c.drawString(32, y, "Últimos conteúdos coletados")
    y -= 20

    c.setFont("Helvetica", 7.5)
    for item in items:
        c.drawString(36, y, fmt_dt(item.get("published_at") or item.get("created_at")))
        c.drawString(130, y, safe(item.get("author_name") or item.get("author_handle"), 28))
        c.drawString(320, y, safe(item.get("title"), 85))
        y -= 14

    footer(c, width, 1, colors)
    c.showPage()
    c.save()

    pdf = buffer.getvalue()
    buffer.close()

    return Response(
        content=pdf,
        media_type="application/pdf",
        headers={"Content-Disposition": 'attachment; filename="TVFISCAL_SOCIAL_SINTETICO_PREMIUM_V3.pdf"'},
    )



@router.get("/analytic-v3/{project_id}")
def analytic_v3(
    project_id: str,
    platform: str | None = Query(default=None),
    q: str | None = Query(default=None),
    source_id: str | None = Query(default=None),
    date_from: str | None = Query(default=None),
    date_to: str | None = Query(default=None),
    limit: int = Query(default=80, ge=1, le=300),
    db: Session = Depends(get_db),
):
    name = project_name(db, project_id)
    items = latest_items(db, project_id, limit, platform, q, source_id, date_from, date_to)

    c, buffer, width, height, colors = pdf_start(
        "Relatório Social Analítico Executivo Premium V3",
        f"{name} - Gerado em {datetime.now().strftime('%d/%m/%Y %H:%M')}",
    )

    page = 1
    y = height - 120

    c.setFillColor(colors.HexColor(DARK))
    c.setFont("Helvetica-Bold", 12)
    c.drawString(32, y, "Detalhamento dos conteúdos sociais coletados")
    y -= 25

    def new_page():
        nonlocal page, y
        footer(c, width, page, colors)
        c.showPage()
        page += 1

        c.setFillColor(colors.HexColor(RED))
        c.rect(0, height - 64, width, 64, fill=1, stroke=0)

        c.setFillColor(colors.white)
        c.setFont("Helvetica-Bold", 16)
        c.drawString(32, height - 35, "Relatório Social Analítico Executivo Premium V3")

        c.setFont("Helvetica", 9)
        c.drawRightString(width - 32, height - 28, "TV Fiscal WebMonitor")
        c.drawRightString(width - 32, height - 44, "Social Monitor")

        c.setFillColor(colors.HexColor(DARK))
        c.setFont("Helvetica", 9)
        c.drawString(32, height - 84, f"{name} - Continuação")

        y = height - 120

    for item in items:
        if y < 95:
            new_page()

        c.setFillColor(colors.HexColor(RED))
        c.setFont("Helvetica-Bold", 9)
        c.drawString(36, y, safe(item.get("title"), 115))
        y -= 14

        c.setFillColor(colors.HexColor(MUTED))
        c.setFont("Helvetica", 7.5)
        c.drawString(
            36,
            y,
            f"{safe(item.get('platform'), 12)} - {safe(item.get('author_name') or item.get('author_handle'), 45)} - {fmt_dt(item.get('published_at') or item.get('created_at'))}",
        )
        y -= 13

        c.setFillColor(colors.HexColor(DARK))
        c.setFont("Helvetica", 7.5)
        c.drawString(36, y, safe(item.get("description"), 150))
        y -= 13

        c.setFillColor(colors.HexColor(MUTED))
        c.setFont("Helvetica", 7)
        c.drawString(36, y, safe(item.get("url"), 150))
        y -= 22

    if not items:
        c.setFont("Helvetica", 9)
        c.drawString(32, y, "Nenhum conteúdo social encontrado.")

    footer(c, width, page, colors)
    c.showPage()
    c.save()

    pdf = buffer.getvalue()
    buffer.close()

    return Response(
        content=pdf,
        media_type="application/pdf",
        headers={"Content-Disposition": 'attachment; filename="TVFISCAL_SOCIAL_ANALITICO_PREMIUM_V3.pdf"'},
    )



def performance_rows(db: Session, project_id: str, platform=None, q=None, source_id=None, date_from=None, date_to=None, limit=10):
    where = ['s.project_id = CAST(:project_id AS uuid)']
    join_filters = ['i.project_id = CAST(:project_id AS uuid)', 'i.source_id = s.id']
    params = {'project_id': project_id, 'limit': limit}
    if platform:
        where.append('s.platform = :platform')
        params['platform'] = platform
    if source_id:
        where.append('s.id = CAST(:source_id AS uuid)')
        params['source_id'] = source_id
    if q:
        join_filters.append('(COALESCE(i.title, \'\') ILIKE :q_like OR COALESCE(i.text, \'\') ILIKE :q_like OR COALESCE(i.author_name, \'\') ILIKE :q_like)')
        params['q_like'] = '%' + q.strip() + '%'
    if date_from:
        join_filters.append('COALESCE(i.published_at, i.created_at) >= CAST(:date_from AS timestamptz)')
        params['date_from'] = date_from
    if date_to:
        join_filters.append("COALESCE(i.published_at, i.created_at) < CAST(:date_to AS timestamptz) + INTERVAL '1 day'")
        params['date_to'] = date_to
    result = db.execute(text(f'''
        SELECT s.platform, s.name AS source_name, s.active, s.query,
               COUNT(i.id)::int AS total_items,
               COUNT(i.id) FILTER (WHERE i.is_sponsored IS TRUE)::int AS sponsored_items,
               MAX(COALESCE(i.published_at, i.created_at)) AS last_item_at
        FROM social_sources s
        LEFT JOIN social_items i ON {' AND '.join(join_filters)}
        WHERE {' AND '.join(where)}
        GROUP BY s.platform, s.id, s.name, s.active, s.query
        ORDER BY total_items DESC, last_item_at DESC NULLS LAST, s.name
        LIMIT :limit
    '''), params)
    return [dict(r._mapping) for r in result.fetchall()]


def evolution_rows(db: Session, project_id: str, platform=None, q=None, source_id=None, date_from=None, date_to=None, limit=15):
    where_sql, params = _social_where(project_id, platform, q, source_id, date_from, date_to)
    params['limit'] = limit
    result = db.execute(text(f'''
        SELECT DATE_TRUNC('day', COALESCE(published_at, created_at))::date AS date,
               platform, COUNT(*)::int AS total_items,
               COUNT(*) FILTER (WHERE is_sponsored IS TRUE)::int AS sponsored_items
        FROM social_items
        WHERE {where_sql}
        GROUP BY 1, 2
        ORDER BY 1 DESC, 2
        LIMIT :limit
    '''), params)
    return [dict(r._mapping) for r in result.fetchall()]



@router.get("/executive-consolidated-v3/{project_id}")
def executive_consolidated_v3(
    project_id: str,
    platform: str | None = Query(default=None),
    q: str | None = Query(default=None),
    source_id: str | None = Query(default=None),
    date_from: str | None = Query(default=None),
    date_to: str | None = Query(default=None),
    db: Session = Depends(get_db),
):
    name = project_name(db, project_id)
    data = summary(db, project_id, platform, q, source_id, date_from, date_to)
    channels = top_channels(db, project_id, platform, q, source_id, date_from, date_to)
    perf = performance_rows(db, project_id, platform, q, source_id, date_from, date_to, 10)
    evol = evolution_rows(db, project_id, platform, q, source_id, date_from, date_to, 12)

    platform_totals = {}
    for row in perf:
        key = row.get("platform") or "social"
        platform_totals[key] = platform_totals.get(key, 0) + int(row.get("total_items") or 0)

    platform_leader = "-"
    if platform_totals:
        platform_leader = sorted(platform_totals.items(), key=lambda item: item[1], reverse=True)[0][0]

    source_leader = perf[0].get("source_name") if perf else "-"
    sponsored_total = sum(int(row.get("sponsored_items") or 0) for row in perf)

    c, buffer, width, height, colors = pdf_start(
        "Relatório Social Executivo Consolidado Premium V3",
        f"{name} - Gerado em {datetime.now().strftime('%d/%m/%Y %H:%M')}",
    )

    y = height - 130
    x = 32

    cards = [
        ("Total no recorte", data.get("total_items", 0)),
        ("Canais/fontes", data.get("total_channels", 0)),
        ("Plataforma líder", platform_leader),
        ("Fonte líder", source_leader),
        ("Patrocinados", sponsored_total),
        ("Dias com coleta", len(evol)),
    ]

    for idx, item in enumerate(cards):
        label, value = item
        c.setFillColor(colors.white)
        c.roundRect(x, y, 118, 54, 10, fill=1, stroke=1)
        c.setFillColor(colors.HexColor(RED))
        c.setFont("Helvetica-Bold", 12)
        c.drawString(x + 10, y + 31, safe(value, 18))
        c.setFillColor(colors.HexColor(MUTED))
        c.setFont("Helvetica", 7)
        c.drawString(x + 10, y + 14, label)
        x += 130
        if idx == 2:
            x = 32
            y -= 66

    y -= 28
    c.setFillColor(colors.HexColor(DARK))
    c.setFont("Helvetica-Bold", 12)
    c.drawString(32, y, "Ranking executivo de fontes sociais")
    y -= 18

    c.setFont("Helvetica-Bold", 7.5)
    c.drawString(36, y, "Fonte")
    c.drawString(260, y, "Plataforma")
    c.drawRightString(390, y, "Itens")
    c.drawRightString(480, y, "Patrocinados")
    c.drawString(520, y, "Última coleta")
    y -= 12

    c.setFont("Helvetica", 7.2)
    for row in perf:
        c.drawString(36, y, safe(row.get("source_name"), 40))
        c.drawString(260, y, safe(row.get("platform"), 16))
        c.drawRightString(390, y, fmt_int(row.get("total_items")))
        c.drawRightString(480, y, fmt_int(row.get("sponsored_items")))
        c.drawString(520, y, fmt_dt(row.get("last_item_at")))
        y -= 13

    footer(c, width, 1, colors)
    c.showPage()

    c.setFillColor(colors.HexColor(RED))
    c.rect(0, height - 64, width, 64, fill=1, stroke=0)
    c.setFillColor(colors.white)
    c.setFont("Helvetica-Bold", 16)
    c.drawString(32, height - 35, "Relatório Social Executivo Consolidado Premium V3")
    c.setFont("Helvetica", 9)
    c.drawRightString(width - 32, height - 28, "TV Fiscal WebMonitor")
    c.drawRightString(width - 32, height - 44, "Social Monitor · Página 2")

    y = height - 105
    c.setFillColor(colors.HexColor(DARK))
    c.setFont("Helvetica-Bold", 13)
    c.drawString(32, y, "Evolução temporal social")
    y -= 20

    c.setFont("Helvetica-Bold", 7.5)
    c.drawString(36, y, "Data")
    c.drawString(155, y, "Plataforma")
    c.drawRightString(290, y, "Itens")
    c.drawRightString(390, y, "Patrocinados")
    y -= 13

    c.setFont("Helvetica", 7.2)
    for row in evol:
        c.drawString(36, y, str(row.get("date") or "-"))
        c.drawString(155, y, safe(row.get("platform"), 18))
        c.drawRightString(290, y, fmt_int(row.get("total_items")))
        c.drawRightString(390, y, fmt_int(row.get("sponsored_items")))
        y -= 13

    y -= 24
    c.setFont("Helvetica-Bold", 13)
    c.drawString(32, y, "Top canais/fontes sociais")
    y -= 20

    c.setFont("Helvetica", 7.5)
    for row in channels[:12]:
        c.drawString(36, y, safe(row.get("channel"), 70))
        c.drawRightString(620, y, fmt_int(row.get("total")))
        y -= 13

    y -= 24
    c.setFont("Helvetica-Bold", 13)
    c.drawString(32, y, "Leitura executiva")
    y -= 18
    c.setFillColor(colors.HexColor(MUTED))
    c.setFont("Helvetica", 8)
    c.drawString(36, y, "• O relatório consolida o comportamento social por volume, fonte, plataforma e evolução diária.")
    y -= 14
    c.drawString(36, y, "• Os indicadores servem para priorização editorial, análise de presença digital e acompanhamento de temas monitorados.")
    y -= 14
    c.drawString(36, y, "• As métricas representam coleta e evidências do Social Monitor, não medição deduplicada de audiência cross-media.")

    footer(c, width, 2, colors)
    c.showPage()
    c.save()

    pdf = buffer.getvalue()
    buffer.close()

    filename = "TVFISCAL_SOCIAL_EXECUTIVO_CONSOLIDADO_PREMIUM_V3.pdf"
    try:
        save_generated_pdf_report(
            db,
            project_id=project_id,
            report_family="social",
            report_type="executive_consolidated_v3",
            title="Relatório Social Executivo Consolidado Premium V3",
            filename=filename,
            pdf_bytes=pdf,
            filters={
                "platform": platform,
                "q": q,
                "source_id": source_id,
                "date_from": date_from,
                "date_to": date_to,
            },
            generated_by="webmonitor",
        )
    except Exception as exc:
        try:
            db.rollback()
        except Exception:
            pass
        print(f"[report-history] falha ao salvar histórico social executive_consolidated_v3: {exc}")

    return Response(
        content=pdf,
        media_type="application/pdf",
        headers={"Content-Disposition": 'attachment; filename="TVFISCAL_SOCIAL_EXECUTIVO_CONSOLIDADO_PREMIUM_V3.pdf"'},
    )
