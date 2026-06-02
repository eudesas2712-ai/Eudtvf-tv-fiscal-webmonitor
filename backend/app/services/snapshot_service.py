import json

from sqlalchemy import text
from datetime import timezone
from zoneinfo import ZoneInfo

brasilia_tz = ZoneInfo("America/Sao_Paulo")


def to_brasilia(dt):
    if not dt:
        return None

    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)

    return dt.astimezone(brasilia_tz).strftime("%d/%m/%Y %H:%M:%S")

def save_market_snapshot(db, project_id: str, data: dict):
   
    current_leader = ((data.get("share_of_voice") or [{}])[0]).get("advertiser")
    current_investment = str(data.get("total_investment", 0))
    current_banners = str(data.get("total_banners", 0))

    existing = db.execute(
        text("""
            SELECT id
            FROM market_snapshots
            WHERE project_id = :project_id
              AND snapshot_data->>'total_investment' = :investment
              AND snapshot_data->>'total_banners' = :banners
              AND snapshot_data->'share_of_voice'->0->>'advertiser' = :leader
            LIMIT 1
        """),
        {
            "project_id": project_id,
            "investment": current_investment,
            "banners": current_banners,
            "leader": current_leader,
        },
    ).fetchone()

    if existing:
        return

    db.execute(
        text("""
            INSERT INTO market_snapshots
            (project_id, snapshot_data)
            VALUES (:project_id, CAST(:snapshot_data AS JSONB))
        """),
        {
            "project_id": project_id,
            "snapshot_data": json.dumps(data),
        },
    )

    db.commit()

def get_market_timeline(db, project_id: str, limit=20):
    rows = db.execute(
        text("""
            SELECT snapshot_data, created_at
            FROM market_snapshots
            WHERE project_id = :project_id
            ORDER BY created_at ASC
            LIMIT :limit
        """),
        {
            "project_id": project_id,
            "limit": limit,
        },
    ).fetchall()

    points = []

    for row in rows:
        data = row[0] or {}

        share = data.get("share_of_voice", []) or []
        portals = data.get("portal_ranking", []) or []

        leader = share[0] if share else {}
        portal = portals[0] if portals else {}

        points.append({
            "created_at": to_brasilia(row[1]) if row[1] else None,
            "total_banners": data.get("total_banners", 0),
            "total_investment": data.get("total_investment", 0),
            "top_advertiser": leader.get("advertiser", "N/D"),
            "top_advertiser_share": leader.get("share_percent", 0),
            "top_portal": portal.get("portal", "N/D"),
            "top_portal_share": portal.get("share_percent", 0),
            "market_type": (data.get("market_analysis") or {}).get("market_type", "N/D"),
        })


    return {
        "project_id": project_id,
        "points": points,
    }

def get_previous_market_snapshot(db, project_id: str):
    rows = db.execute(
        text("""
            SELECT snapshot_data, created_at
            FROM market_snapshots
            WHERE project_id = :project_id
            ORDER BY created_at DESC
            LIMIT 1
        """),
        {"project_id": project_id},
    ).fetchall()

    if not rows:
        return None

    data = rows[0][0] or {}

    share = data.get("share_of_voice", []) or []
    leader = share[0] if share else {}

    return {
        "created_at": to_brasilia(rows[0][1]),
        "total_banners": data.get("total_banners", 0),
        "total_investment": data.get("total_investment", 0),
        "top_advertiser": leader.get("advertiser", "N/D"),
        "top_advertiser_share": leader.get("share_percent", 0),
    }
