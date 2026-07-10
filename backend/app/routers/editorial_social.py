
from fastapi import APIRouter, Depends, Query
from fastapi.responses import Response
from sqlalchemy import text
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.services.editorial_service import editorial_rows, editorial_summary
from app.services.editorial_report_generator import build_editorial_analytical_pdf, build_editorial_synthetic_pdf
from app.services.report_storage_service import save_generated_pdf_report
from collections import Counter

router = APIRouter(prefix="/editorial-social", tags=["editorial-social"])


def _social_rows(db, project_id, q, source_name, term, sentiment, topic, date_from, date_to, limit=120):
    rows = db.execute(
        text("""
            SELECT
                id::text AS id,
                platform,
                title,
                author_name,
                author_handle,
                url,
                published_at,
                created_at,
                text AS description,
                sentiment,
                topic,
                matched_terms,
                editorial_score
            FROM social_items
            WHERE project_id = CAST(:project_id AS uuid)
                AND (
                  COALESCE(CAST(:date_from AS text), '') = ''
                  OR COALESCE(published_at, created_at) >= CAST(CAST(:date_from AS text) AS timestamptz)
                )
                AND (
                  COALESCE(CAST(:date_to AS text), '') = ''
                  OR COALESCE(published_at, created_at) < CAST(CAST(:date_to AS text) AS timestamptz) + INTERVAL '1 day'
                )
                AND (
                  COALESCE(CAST(:q_like AS text), '') = ''
                  OR COALESCE(title, '') ILIKE CAST(:q_like AS text)
                  OR COALESCE(text, '') ILIKE CAST(:q_like AS text)
                  OR COALESCE(author_name, '') ILIKE CAST(:q_like AS text)
                  OR COALESCE(author_handle, '') ILIKE CAST(:q_like AS text)
                  OR COALESCE(url, '') ILIKE CAST(:q_like AS text)
                )
                AND (
                  COALESCE(CAST(:term_like AS text), '') = ''
                  OR COALESCE(title, '') ILIKE CAST(:term_like AS text)
                  OR COALESCE(text, '') ILIKE CAST(:term_like AS text)
                  OR COALESCE(author_name, '') ILIKE CAST(:term_like AS text)
                  OR COALESCE(author_handle, '') ILIKE CAST(:term_like AS text)
                )
                AND (
                  COALESCE(CAST(:source_like AS text), '') = ''
                  OR COALESCE(author_name, '') ILIKE CAST(:source_like AS text)
                  OR COALESCE(author_handle, '') ILIKE CAST(:source_like AS text)
                  OR COALESCE(platform, '') ILIKE CAST(:source_like AS text)
                )
                AND (
                  COALESCE(CAST(:sentiment_filter AS text), '') = ''
                  OR LOWER(COALESCE(sentiment, 'neutro')) = LOWER(CAST(:sentiment_filter AS text))
                )
                AND (
                  COALESCE(CAST(:topic_like AS text), '') = ''
                  OR COALESCE(topic, '') ILIKE CAST(:topic_like AS text)
                )
            ORDER BY COALESCE(published_at, created_at) DESC
            LIMIT :limit
        """),
        {
            "project_id": project_id,
            "date_from": date_from or "",
            "date_to": date_to or "",
            "q_like": "%" + q.strip() + "%" if q else "",
            "term_like": "%" + term.strip() + "%" if term else "",
            "source_like": "%" + source_name.replace("YouTube ·", "").strip() + "%" if source_name else "",
            "sentiment_filter": sentiment or "",
            "topic_like": "%" + topic.strip() + "%" if topic else "",
            "limit": limit,
        },
    ).fetchall()

    items = []

    for row in rows:
        r = dict(row._mapping)
        channel = r.get("author_name") or r.get("author_handle") or "Canal não identificado"
        platform = r.get("platform") or "youtube"
        source = f"YouTube · {channel}" if platform == "youtube" else f"{platform} · {channel}"
        desc = r.get("description") or ""
        mt = r.get("matched_terms") if isinstance(r.get("matched_terms"), dict) else {"terms": []}

        item = {
            "id": "social-" + str(r.get("id")),
            "title": r.get("title") or "Conteúdo social sem título",
            "summary": desc,
            "content_text": desc,
            "source_name": source,
            "url": r.get("url"),
            "evidence_html_url": r.get("url"),
            "published_at": r.get("published_at"),
            "created_at": r.get("created_at"),
            "sentiment": r.get("sentiment") or "neutro",
            "topic": r.get("topic") or "Social / YouTube",
            "matched_terms": mt,
            "editorial_score": r.get("editorial_score") or 70,
        }

        blob = " ".join([
            str(item.get("title") or ""),
            str(item.get("summary") or ""),
            str(item.get("source_name") or ""),
            str(item.get("url") or ""),
        ]).lower()

        if q and q.lower() not in blob:
            continue
        if source_name and source_name.lower() not in str(item.get("source_name") or "").lower():
            continue
        if term and term.lower() not in blob:
            continue
        if sentiment and str(item.get("sentiment") or "").lower() != sentiment.lower():
            continue
        if topic and topic.lower() not in str(item.get("topic") or "").lower():
            continue

        items.append(item)

    return items


def _base_rows(db, project_id, q, source_name, term, sentiment, topic, date_from, date_to, limit=800):
    base = editorial_rows(
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

    social = _social_rows(
        db=db,
        project_id=project_id,
        q=q,
        source_name=source_name,
        term=term,
        sentiment=sentiment,
        topic=topic,
        date_from=date_from,
        date_to=date_to,
        limit=120,
    )

    combined = list(base or []) + list(social or [])
    combined.sort(
        key=lambda item: str(item.get("published_at") or item.get("created_at") or ""),
        reverse=True,
    )
    return combined[:limit]


def _report_filters_payload(q, source_name, term, sentiment, topic, date_from, date_to):
    return {
        "q": q,
        "source_name": source_name,
        "term": term,
        "sentiment": sentiment,
        "topic": topic,
        "date_from": date_from,
        "date_to": date_to,
    }


def _try_save_editorial_social_report_history(
    db,
    *,
    project_id,
    report_type,
    title,
    filename,
    pdf_bytes,
    q,
    source_name,
    term,
    sentiment,
    topic,
    date_from,
    date_to,
):
    try:
        save_generated_pdf_report(
            db,
            project_id=project_id,
            report_family="editorial_social",
            report_type=report_type,
            title=title,
            filename=filename,
            pdf_bytes=pdf_bytes,
            filters=_report_filters_payload(q, source_name, term, sentiment, topic, date_from, date_to),
            generated_by="webmonitor",
        )
    except Exception as exc:
        try:
            db.rollback()
        except Exception:
            pass
        print(f"[report-history] falha ao salvar histórico editorial_social {report_type}: {exc}")


def _summary_from_rows(project_id: str, rows: list[dict]) -> dict:
    sources = Counter(row.get("source_name") or "Desconhecido" for row in rows)
    terms = Counter()
    sentiments = Counter(row.get("sentiment") or "neutro" for row in rows)
    topics = Counter(row.get("topic") or "Geral" for row in rows)

    for row in rows:
        matched_terms = row.get("matched_terms") or {}
        if isinstance(matched_terms, dict):
            for term in matched_terms.get("terms", []):
                terms[str(term)] += 1

    return {
        "project_id": project_id,
        "total_items": len(rows),
        "total_terms": sum(terms.values()),
        "sources_count": len(sources),
        "topics_count": len(topics),
        "sentiment": dict(sentiments),
        "top_sources": [{"name": k, "count": v} for k, v in sources.most_common(10)],
        "top_terms": [{"term": k, "count": v} for k, v in terms.most_common(10)],
        "top_topics": [{"topic": k, "count": v} for k, v in topics.most_common(10)],
        "latest": rows[:8],
    }


@router.get("/reports/synthetic-v3/{project_id}")
def synthetic_v3(
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
    rows = _base_rows(db, project_id, q, source_name, term, sentiment, topic, date_from, date_to)
    summary = _summary_from_rows(project_id, rows)
    pdf = build_editorial_synthetic_pdf(project_id, rows, summary, project_label="Editorial + Social Monitor")
    _try_save_editorial_social_report_history(
        db,
        project_id=project_id,
        report_type="synthetic_v3",
        title="Sintético Editorial + Social V3",
        filename=f"EDITORIAL_SOCIAL_SINTETICO_PREMIUM_V3_{project_id}.pdf",
        pdf_bytes=pdf,
        q=q,
        source_name=source_name,
        term=term,
        sentiment=sentiment,
        topic=topic,
        date_from=date_from,
        date_to=date_to,
    )
    return Response(
        content=pdf,
        media_type="application/pdf",
        headers={"Content-Disposition": f'inline; filename="EDITORIAL_SOCIAL_SINTETICO_PREMIUM_V3_{project_id}.pdf"'},
    )


@router.get("/reports/analytic-expanded-v3/{project_id}")
def analytic_v3(
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
    rows = _base_rows(db, project_id, q, source_name, term, sentiment, topic, date_from, date_to)
    summary = _summary_from_rows(project_id, rows)
    pdf = build_editorial_analytical_pdf(project_id, rows, summary, project_label="Editorial + Social Monitor")
    _try_save_editorial_social_report_history(
        db,
        project_id=project_id,
        report_type="analytic_expanded_v3",
        title="Analítico Editorial + Social V3",
        filename=f"EDITORIAL_SOCIAL_ANALITICO_PREMIUM_V3_{project_id}.pdf",
        pdf_bytes=pdf,
        q=q,
        source_name=source_name,
        term=term,
        sentiment=sentiment,
        topic=topic,
        date_from=date_from,
        date_to=date_to,
    )
    return Response(
        content=pdf,
        media_type="application/pdf",
        headers={"Content-Disposition": f'inline; filename="EDITORIAL_SOCIAL_ANALITICO_PREMIUM_V3_{project_id}.pdf"'},
    )
