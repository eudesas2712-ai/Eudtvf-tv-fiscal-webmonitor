import json
import os
import urllib.parse
import urllib.request
from datetime import datetime, timezone
from typing import Any

from sqlalchemy import text


YOUTUBE_SEARCH_URL = "https://www.googleapis.com/youtube/v3/search"
YOUTUBE_VIDEOS_URL = "https://www.googleapis.com/youtube/v3/videos"


def _now():
    return datetime.now(timezone.utc)


def _api_key() -> str:
    return os.getenv("YOUTUBE_API_KEY", "").strip()


def _http_json(url: str, params: dict[str, Any], timeout: int = 25) -> dict:
    query = urllib.parse.urlencode(params)
    request_url = f"{url}?{query}"
    req = urllib.request.Request(
        request_url,
        headers={
            "User-Agent": "TVFiscalWebMonitor/1.0",
            "Accept": "application/json",
        },
    )
    with urllib.request.urlopen(req, timeout=timeout) as response:
        raw = response.read().decode("utf-8", errors="replace")
        return json.loads(raw)


def _thumb(snippet: dict) -> str | None:
    thumbnails = snippet.get("thumbnails") or {}
    for key in ("high", "medium", "default"):
        item = thumbnails.get(key) or {}
        if item.get("url"):
            return item["url"]
    return None


def _insert_run(db, project_id: str, platform: str, source_id: str | None) -> str:
    row = db.execute(
        text("""
            INSERT INTO social_collection_runs(project_id, platform, source_id, status, message)
            VALUES (CAST(:project_id AS uuid), :platform, CAST(:source_id AS uuid), 'running', 'Coleta iniciada.')
            RETURNING id
        """),
        {"project_id": project_id, "platform": platform, "source_id": source_id},
    ).fetchone()
    db.commit()
    return str(row[0])


def _finish_run(db, run_id: str, status: str, message: str, collected: int = 0, saved: int = 0):
    db.execute(
        text("""
            UPDATE social_collection_runs
            SET status = :status,
                message = :message,
                collected = :collected,
                saved = :saved,
                finished_at = NOW()
            WHERE id = CAST(:run_id AS uuid)
        """),
        {
            "run_id": run_id,
            "status": status,
            "message": message,
            "collected": collected,
            "saved": saved,
        },
    )
    db.commit()


def _get_source(db, source_id: str) -> dict | None:
    row = db.execute(
        text("""
            SELECT id, project_id, platform, name, handle, url, source_type, query, active
            FROM social_sources
            WHERE id = CAST(:source_id AS uuid)
            LIMIT 1
        """),
        {"source_id": source_id},
    ).fetchone()
    return dict(row._mapping) if row else None


def _video_stats(api_key: str, video_ids: list[str]) -> dict[str, dict]:
    if not video_ids:
        return {}

    payload = _http_json(
        YOUTUBE_VIDEOS_URL,
        {
            "key": api_key,
            "part": "statistics,contentDetails",
            "id": ",".join(video_ids[:50]),
            "maxResults": 50,
        },
    )

    stats = {}
    for item in payload.get("items", []):
        vid = item.get("id")
        if vid:
            stats[vid] = {
                "statistics": item.get("statistics") or {},
                "contentDetails": item.get("contentDetails") or {},
            }
    return stats


def collect_youtube(db, project_id: str, source_id: str | None = None, query: str | None = None, max_results: int = 15) -> dict:
    api_key = _api_key()
    run_id = None

    try:
        source = None
        if source_id:
            source = _get_source(db, source_id)
            if not source:
                return {"success": False, "message": "Fonte social não encontrada.", "collected": 0, "saved": 0}
            if not source.get("active"):
                return {"success": False, "message": "Fonte social inativa.", "collected": 0, "saved": 0}
            project_id = str(source["project_id"])
            query = query or source.get("query") or source.get("name")

        query = (query or "").strip()

        run_id = _insert_run(db, project_id, "youtube", source_id)

        if not api_key:
            message = "YOUTUBE_API_KEY não configurada. Informe a chave no .env.production para ativar a coleta."
            _finish_run(db, run_id, "error", message, 0, 0)
            return {"success": False, "message": message, "collected": 0, "saved": 0}

        if not query:
            message = "Informe uma palavra-chave, termo monitorado ou fonte com query configurada."
            _finish_run(db, run_id, "error", message, 0, 0)
            return {"success": False, "message": message, "collected": 0, "saved": 0}

        max_results = max(1, min(int(max_results or 15), 50))

        payload = _http_json(
            YOUTUBE_SEARCH_URL,
            {
                "key": api_key,
                "part": "snippet",
                "type": "video",
                "order": "date",
                "q": query,
                "maxResults": max_results,
                "safeSearch": "none",
            },
        )

        items = payload.get("items") or []
        video_ids = [
            item.get("id", {}).get("videoId")
            for item in items
            if item.get("id", {}).get("videoId")
        ]
        stats_map = _video_stats(api_key, video_ids)

        saved = 0

        for item in items:
            video_id = item.get("id", {}).get("videoId")
            snippet = item.get("snippet") or {}
            if not video_id:
                continue

            title = snippet.get("title") or "Sem título"
            description = snippet.get("description") or ""
            channel_title = snippet.get("channelTitle")
            channel_id = snippet.get("channelId")
            published_at = snippet.get("publishedAt")
            url = f"https://www.youtube.com/watch?v={video_id}"

            text_blob = f"{title}\n{description}"
            matched_terms = {"terms": [query]} if query.lower() in text_blob.lower() else {"terms": []}

            metrics = stats_map.get(video_id, {})
            metrics["query"] = query

            db.execute(
                text("""
                    INSERT INTO social_items (
                        project_id, source_id, platform, external_id, content_type,
                        title, author_name, author_handle, url, published_at,
                        text, thumbnail_url, metrics_json, matched_terms,
                        sentiment, topic, editorial_score, ad_score, is_sponsored,
                        updated_at
                    )
                    VALUES (
                        CAST(:project_id AS uuid), CAST(:source_id AS uuid), 'youtube', :external_id, 'video',
                        :title, :author_name, :author_handle, :url, :published_at,
                        :text, :thumbnail_url, CAST(:metrics_json AS jsonb), CAST(:matched_terms AS jsonb),
                        'neutro', 'Social/YouTube', 70, 0, false,
                        NOW()
                    )
                    ON CONFLICT (platform, external_id)
                    WHERE external_id IS NOT NULL
                    DO UPDATE SET
                        title = EXCLUDED.title,
                        author_name = EXCLUDED.author_name,
                        author_handle = EXCLUDED.author_handle,
                        url = EXCLUDED.url,
                        published_at = EXCLUDED.published_at,
                        text = EXCLUDED.text,
                        thumbnail_url = EXCLUDED.thumbnail_url,
                        metrics_json = EXCLUDED.metrics_json,
                        matched_terms = EXCLUDED.matched_terms,
                        updated_at = NOW()
                """),
                {
                    "project_id": project_id,
                    "source_id": source_id,
                    "external_id": video_id,
                    "title": title,
                    "author_name": channel_title,
                    "author_handle": channel_id,
                    "url": url,
                    "published_at": published_at,
                    "text": description,
                    "thumbnail_url": _thumb(snippet),
                    "metrics_json": json.dumps(metrics, ensure_ascii=False),
                    "matched_terms": json.dumps(matched_terms, ensure_ascii=False),
                },
            )
            saved += 1

        db.commit()

        message = f"YouTube: {len(items)} coletados, {saved} salvos/atualizados para a busca '{query}'."
        _finish_run(db, run_id, "success", message, len(items), saved)

        return {
            "success": True,
            "message": message,
            "project_id": project_id,
            "platform": "youtube",
            "query": query,
            "collected": len(items),
            "saved": saved,
        }

    except Exception as exc:
        db.rollback()
        message = f"Erro na coleta YouTube: {exc}"
        if run_id:
            try:
                _finish_run(db, run_id, "error", message, 0, 0)
            except Exception:
                pass
        return {"success": False, "message": message, "collected": 0, "saved": 0}
