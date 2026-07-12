from fastapi import APIRouter, Body, Depends, Query
from sqlalchemy import text
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.services.social_youtube_collector import collect_youtube
from app.services.social_x_collector import collect_x
from app.services.social_meta_collector import collect_meta


router = APIRouter(prefix="/social", tags=["Social Monitor"])


def _rows(result):
    return [dict(row._mapping) for row in result.fetchall()]


@router.get("/summary/{project_id}")
def social_summary(
    project_id: str,
    platform: str | None = Query(None),
    db: Session = Depends(get_db),
):
    platform = (platform or "").strip().lower() or None
    item_filter = "AND platform = :platform" if platform else ""
    source_filter = "AND platform = :platform" if platform else ""
    params = {"project_id": project_id}
    if platform:
        params["platform"] = platform

    totals = db.execute(
        text(f"""
            SELECT
                COUNT(*)::int AS total_items,
                COUNT(DISTINCT source_id)::int AS sources_with_items,
                COUNT(*) FILTER (WHERE platform = 'youtube')::int AS youtube_items,
                COUNT(*) FILTER (WHERE platform = 'x')::int AS x_items,
                COUNT(*) FILTER (WHERE platform = 'instagram')::int AS instagram_items,
                COUNT(*) FILTER (WHERE platform = 'facebook')::int AS facebook_items,
                COUNT(*) FILTER (WHERE platform = 'linkedin')::int AS linkedin_items,
                COUNT(*) FILTER (WHERE platform = 'tiktok')::int AS tiktok_items,
                COUNT(*) FILTER (WHERE is_sponsored IS TRUE)::int AS sponsored_items
            FROM social_items
            WHERE project_id = CAST(:project_id AS uuid)
              {item_filter}
        """),
        params,
    ).fetchone()

    sources = db.execute(
        text(f"""
            SELECT platform, COUNT(*)::int AS total
            FROM social_sources
            WHERE project_id = CAST(:project_id AS uuid)
              AND active IS TRUE
              {source_filter}
            GROUP BY platform
            ORDER BY total DESC
        """),
        params,
    )

    channels = db.execute(
        text(f"""
            SELECT COALESCE(author_name, 'Não identificado') AS name, COUNT(*)::int AS count
            FROM social_items
            WHERE project_id = CAST(:project_id AS uuid)
              {item_filter}
            GROUP BY COALESCE(author_name, 'Não identificado')
            ORDER BY count DESC
            LIMIT 10
        """),
        params,
    )

    latest = db.execute(
        text(f"""
            SELECT id, platform, title, author_name, url, published_at, created_at, thumbnail_url
            FROM social_items
            WHERE project_id = CAST(:project_id AS uuid)
              {item_filter}
            ORDER BY COALESCE(published_at, created_at) DESC
            LIMIT 10
        """),
        params,
    )

    return {
        "project_id": project_id,
        "platform": platform,
        "summary": dict(totals._mapping) if totals else {},
        "sources_by_platform": _rows(sources),
        "top_channels": _rows(channels),
        "latest": _rows(latest),
    }


@router.get("/sources/{project_id}")
def list_social_sources(project_id: str, db: Session = Depends(get_db)):
    result = db.execute(
        text("""
            SELECT id, project_id, platform, name, handle, url, source_type, query,
                   active, monitor_news, monitor_ads, monitor_mentions, created_at
            FROM social_sources
            WHERE project_id = CAST(:project_id AS uuid)
            ORDER BY created_at DESC
        """),
        {"project_id": project_id},
    )
    return {"items": _rows(result)}


@router.post("/sources")
def create_social_source(payload: dict = Body(...), db: Session = Depends(get_db)):
    project_id = payload.get("project_id")
    name = (payload.get("name") or "").strip()
    platform = (payload.get("platform") or "youtube").strip().lower()
    source_type = (payload.get("source_type") or "keyword").strip().lower()
    query = (payload.get("query") or name).strip()

    if not project_id:
        return {"success": False, "message": "project_id obrigatório."}
    if not name:
        return {"success": False, "message": "name obrigatório."}

    row = db.execute(
        text("""
            INSERT INTO social_sources (
                project_id, platform, name, handle, url, source_type, query,
                active, monitor_news, monitor_ads, monitor_mentions
            )
            VALUES (
                CAST(:project_id AS uuid), :platform, :name, :handle, :url, :source_type, :query,
                :active, :monitor_news, :monitor_ads, :monitor_mentions
            )
            RETURNING id, project_id, platform, name, handle, url, source_type, query,
                      active, monitor_news, monitor_ads, monitor_mentions, created_at
        """),
        {
            "project_id": project_id,
            "platform": platform,
            "name": name,
            "handle": payload.get("handle"),
            "url": payload.get("url"),
            "source_type": source_type,
            "query": query,
            "active": bool(payload.get("active", True)),
            "monitor_news": bool(payload.get("monitor_news", True)),
            "monitor_ads": bool(payload.get("monitor_ads", False)),
            "monitor_mentions": bool(payload.get("monitor_mentions", True)),
        },
    ).fetchone()
    db.commit()

    return {"success": True, "item": dict(row._mapping)}


@router.post("/sources/{source_id}/toggle")
def toggle_social_source(source_id: str, payload: dict = Body(default={}), db: Session = Depends(get_db)):
    active = bool(payload.get("active", True))

    row = db.execute(
        text("""
            UPDATE social_sources
            SET active = :active
            WHERE id = CAST(:source_id AS uuid)
            RETURNING id, project_id, platform, name, handle, url, source_type, query,
                      active, monitor_news, monitor_ads, monitor_mentions, created_at
        """),
        {"source_id": source_id, "active": active},
    ).fetchone()

    db.commit()

    if not row:
        return {"success": False, "message": "Fonte social não encontrada."}

    return {
        "success": True,
        "message": "Fonte social ativada." if active else "Fonte social desativada.",
        "item": dict(row._mapping),
    }


@router.get("/items/{project_id}")
def list_social_items(
    project_id: str,
    platform: str | None = Query(default=None),
    source_id: str | None = Query(default=None),
    q: str | None = Query(default=None),
    date_from: str | None = Query(default=None),
    date_to: str | None = Query(default=None),
    limit: int = Query(default=50, ge=1, le=300),
    db: Session = Depends(get_db),
):
    where = ["project_id = CAST(:project_id AS uuid)"]
    params = {"project_id": project_id, "limit": limit}

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

    where_sql = " AND ".join(where)

    result = db.execute(
        text(f"""
            SELECT id, project_id, source_id, platform, external_id, content_type,
                   title, author_name, author_handle, url, published_at, text,
                   thumbnail_url, metrics_json, matched_terms, sentiment, topic,
                   editorial_score, ad_score, is_sponsored, created_at
            FROM social_items
            WHERE {where_sql}
            ORDER BY COALESCE(published_at, created_at) DESC
            LIMIT :limit
        """),
        params,
    )
    return {"items": _rows(result)}


@router.get("/performance/{project_id}")
def social_performance(
    project_id: str,
    platform: str | None = Query(default=None),
    source_id: str | None = Query(default=None),
    date_from: str | None = Query(default=None),
    date_to: str | None = Query(default=None),
    limit: int = Query(default=100, ge=1, le=500),
    db: Session = Depends(get_db),
):
    where = ["s.project_id = CAST(:project_id AS uuid)"]
    join_filters = ["i.project_id = CAST(:project_id AS uuid)", "i.source_id = s.id"]
    params = {"project_id": project_id, "limit": limit}

    if platform:
        where.append("s.platform = :platform")
        params["platform"] = platform

    if source_id:
        where.append("s.id = CAST(:source_id AS uuid)")
        params["source_id"] = source_id

    if date_from:
        join_filters.append("COALESCE(i.published_at, i.created_at) >= CAST(:date_from AS timestamptz)")
        params["date_from"] = date_from

    if date_to:
        join_filters.append("COALESCE(i.published_at, i.created_at) < CAST(:date_to AS timestamptz) + INTERVAL '1 day'")
        params["date_to"] = date_to

    where_sql = " AND ".join(where)
    join_sql = " AND ".join(join_filters)

    result = db.execute(
        text(f"""
            SELECT
                s.platform,
                s.id AS source_id,
                s.name AS source_name,
                s.active,
                s.query,
                COUNT(i.id)::int AS total_items,
                COUNT(i.id) FILTER (WHERE i.is_sponsored IS TRUE)::int AS sponsored_items,
                MIN(COALESCE(i.published_at, i.created_at)) AS first_item_at,
                MAX(COALESCE(i.published_at, i.created_at)) AS last_item_at,
                ROUND(AVG(i.editorial_score)::numeric, 2) AS avg_editorial_score,
                ROUND(AVG(i.ad_score)::numeric, 2) AS avg_ad_score
            FROM social_sources s
            LEFT JOIN social_items i ON {join_sql}
            WHERE {where_sql}
            GROUP BY s.platform, s.id, s.name, s.active, s.query
            ORDER BY total_items DESC, last_item_at DESC NULLS LAST, s.name
            LIMIT :limit
        """),
        params,
    )

    return {"project_id": project_id, "items": _rows(result)}


@router.get("/evolution/{project_id}")
def social_evolution(
    project_id: str,
    platform: str | None = Query(default=None),
    source_id: str | None = Query(default=None),
    date_from: str | None = Query(default=None),
    date_to: str | None = Query(default=None),
    db: Session = Depends(get_db),
):
    where = ["project_id = CAST(:project_id AS uuid)"]
    params = {"project_id": project_id}

    if platform:
        where.append("platform = :platform")
        params["platform"] = platform

    if source_id:
        where.append("source_id = CAST(:source_id AS uuid)")
        params["source_id"] = source_id

    if date_from:
        where.append("COALESCE(published_at, created_at) >= CAST(:date_from AS timestamptz)")
        params["date_from"] = date_from

    if date_to:
        where.append("COALESCE(published_at, created_at) < CAST(:date_to AS timestamptz) + INTERVAL '1 day'")
        params["date_to"] = date_to

    where_sql = " AND ".join(where)

    result = db.execute(
        text(f"""
            SELECT
                DATE_TRUNC('day', COALESCE(published_at, created_at))::date AS date,
                platform,
                COUNT(*)::int AS total_items,
                COUNT(*) FILTER (WHERE is_sponsored IS TRUE)::int AS sponsored_items,
                COUNT(DISTINCT source_id)::int AS sources_count,
                ROUND(AVG(editorial_score)::numeric, 2)::float AS avg_editorial_score,
                ROUND(AVG(ad_score)::numeric, 2)::float AS avg_ad_score
            FROM social_items
            WHERE {where_sql}
            GROUP BY 1, 2
            ORDER BY 1, 2
            LIMIT 3660
        """),
        params,
    )

    return {"project_id": project_id, "items": _rows(result)}


@router.get("/platform-status/{project_id}")
def social_platform_status(project_id: str, db: Session = Depends(get_db)):
    result = db.execute(
        text("""
            WITH platforms(platform, label, connector_state, connector_status, sort_order) AS (
                VALUES
                    ('youtube', 'YouTube', 'active', 'Ativo', 1),
                    ('x', 'X / Twitter', 'active', 'Ativo', 2),
                    ('instagram', 'Instagram', 'pending', 'Pendente', 3),
                    ('facebook', 'Facebook', 'pending', 'Pendente', 4),
                    ('tiktok', 'TikTok', 'pending', 'Pendente', 5),
                    ('linkedin', 'LinkedIn', 'pending', 'Pendente', 6)
            ),
            source_stats AS (
                SELECT
                    platform,
                    COUNT(*)::int AS total_sources,
                    COUNT(*) FILTER (WHERE active IS TRUE)::int AS active_sources
                FROM social_sources
                WHERE project_id = CAST(:project_id AS uuid)
                GROUP BY platform
            ),
            item_stats AS (
                SELECT
                    platform,
                    COUNT(*)::int AS total_items,
                    COUNT(*) FILTER (WHERE is_sponsored IS TRUE)::int AS sponsored_items
                FROM social_items
                WHERE project_id = CAST(:project_id AS uuid)
                GROUP BY platform
            ),
            latest_runs AS (
                SELECT *
                FROM (
                    SELECT
                        platform,
                        status AS last_run_status,
                        message AS last_run_message,
                        collected AS last_run_collected,
                        saved AS last_run_saved,
                        started_at AS last_run_started_at,
                        finished_at AS last_run_finished_at,
                        ROW_NUMBER() OVER (PARTITION BY platform ORDER BY started_at DESC) AS rn
                    FROM social_collection_runs
                    WHERE project_id = CAST(:project_id AS uuid)
                ) ranked
                WHERE rn = 1
            )
            SELECT
                p.platform,
                p.label,
                p.connector_state,
                p.connector_status,
                COALESCE(ss.total_sources, 0)::int AS total_sources,
                COALESCE(ss.active_sources, 0)::int AS active_sources,
                COALESCE(ist.total_items, 0)::int AS total_items,
                COALESCE(ist.sponsored_items, 0)::int AS sponsored_items,
                lr.last_run_status,
                lr.last_run_message,
                COALESCE(lr.last_run_collected, 0)::int AS last_run_collected,
                COALESCE(lr.last_run_saved, 0)::int AS last_run_saved,
                lr.last_run_started_at,
                lr.last_run_finished_at
            FROM platforms p
            LEFT JOIN source_stats ss ON ss.platform = p.platform
            LEFT JOIN item_stats ist ON ist.platform = p.platform
            LEFT JOIN latest_runs lr ON lr.platform = p.platform
            ORDER BY p.sort_order
        """),
        {"project_id": project_id},
    )

    return {"project_id": project_id, "items": _rows(result)}


@router.get("/runs/{project_id}")
def list_social_runs(project_id: str, limit: int = Query(default=30, ge=1, le=200), db: Session = Depends(get_db)):
    result = db.execute(
        text("""
            SELECT id, project_id, platform, source_id, status, message, collected, saved, started_at, finished_at
            FROM social_collection_runs
            WHERE project_id = CAST(:project_id AS uuid)
            ORDER BY started_at DESC
            LIMIT :limit
        """),
        {"project_id": project_id, "limit": limit},
    )
    return {"items": _rows(result)}


@router.post("/youtube/collect/{project_id}")
def collect_youtube_route(
    project_id: str,
    query: str | None = Query(default=None),
    source_id: str | None = Query(default=None),
    max_results: int = Query(default=15, ge=1, le=50),
    db: Session = Depends(get_db),
):
    return collect_youtube(db, project_id=project_id, source_id=source_id, query=query, max_results=max_results)

@router.post("/x/collect/{project_id}")
def collect_x_route(
    project_id: str,
    query: str | None = Query(default=None),
    source_id: str | None = Query(default=None),
    max_results: int = Query(default=10, ge=10, le=100),
    db: Session = Depends(get_db),
):
    return collect_x(db, project_id=project_id, source_id=source_id, query=query, max_results=max_results)


@router.post("/instagram/collect/{project_id}")
def collect_instagram_route(
    project_id: str,
    query: str | None = Query(default=None),
    source_id: str | None = Query(default=None),
    max_results: int = Query(default=10, ge=1, le=100),
    db: Session = Depends(get_db),
):
    return collect_meta(
        db,
        project_id=project_id,
        platform="instagram",
        source_id=source_id,
        query=query,
        max_results=max_results,
    )


@router.post("/facebook/collect/{project_id}")
def collect_facebook_route(
    project_id: str,
    query: str | None = Query(default=None),
    source_id: str | None = Query(default=None),
    max_results: int = Query(default=10, ge=1, le=100),
    db: Session = Depends(get_db),
):
    return collect_meta(
        db,
        project_id=project_id,
        platform="facebook",
        source_id=source_id,
        query=query,
        max_results=max_results,
    )
