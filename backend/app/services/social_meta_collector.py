import os
from sqlalchemy import text


def _meta_token() -> str:
    return (
        os.getenv("META_ACCESS_TOKEN")
        or os.getenv("FACEBOOK_ACCESS_TOKEN")
        or os.getenv("INSTAGRAM_ACCESS_TOKEN")
        or ""
    ).strip()


def _source_row(db, project_id: str, platform: str, source_id: str | None):
    if not source_id:
        return None

    return db.execute(
        text("""
            SELECT id, platform, name, handle, url, source_type, query
            FROM social_sources
            WHERE project_id = CAST(:project_id AS uuid)
              AND id = CAST(:source_id AS uuid)
              AND platform = :platform
              AND active IS TRUE
            LIMIT 1
        """),
        {
            "project_id": project_id,
            "source_id": source_id,
            "platform": platform,
        },
    ).fetchone()


def collect_meta(
    db,
    project_id: str,
    platform: str,
    source_id: str | None = None,
    query: str | None = None,
    max_results: int = 10,
):
    platform = (platform or "").strip().lower()

    if platform not in {"instagram", "facebook"}:
        return {
            "success": False,
            "message": "Plataforma Meta inválida.",
            "collected": 0,
            "saved": 0,
        }

    token = _meta_token()
    if not token:
        return {
            "success": False,
            "message": "Token Meta não configurado. Defina META_ACCESS_TOKEN, FACEBOOK_ACCESS_TOKEN ou INSTAGRAM_ACCESS_TOKEN.",
            "collected": 0,
            "saved": 0,
        }

    source = _source_row(db, project_id, platform, source_id)
    source_map = dict(source._mapping) if source else None

    term = (query or (source_map or {}).get("query") or "").strip()
    handle = ((source_map or {}).get("handle") or "").strip()
    url = ((source_map or {}).get("url") or "").strip()
    source_type = ((source_map or {}).get("source_type") or "keyword").strip().lower()

    if not term and not handle and not url:
        return {
            "success": False,
            "message": f"Fonte {platform} sem query, handle ou URL identificável.",
            "collected": 0,
            "saved": 0,
        }

    return {
        "success": False,
        "message": (
            f"Conector {platform} preparado, mas ainda requer implementação específica da Graph API "
            f"conforme source_type='{source_type}'. Use fonte com handle, URL, page_id ou hashtag válida."
        ),
        "collected": 0,
        "saved": 0,
        "source_type": source_type,
    }
