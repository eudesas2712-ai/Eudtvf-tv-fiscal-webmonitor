import json
import os
import urllib.parse
import urllib.request
from datetime import datetime, timezone
from typing import Any

from sqlalchemy import text


X_RECENT_SEARCH_URL = "https://api.x.com/2/tweets/search/recent"


def _now():
    return datetime.now(timezone.utc)


def _bearer_token() -> str:
    return (
        os.getenv("X_BEARER_TOKEN", "").strip()
        or os.getenv("TWITTER_BEARER_TOKEN", "").strip()
        or os.getenv("X_API_BEARER_TOKEN", "").strip()
    )


def _http_json(url: str, params: dict[str, Any], bearer_token: str, timeout: int = 25) -> dict:
    query = urllib.parse.urlencode(params)
    request_url = f"{url}?{query}"

    req = urllib.request.Request(
        request_url,
        headers={
            "User-Agent": "TVFiscalWebMonitor/1.0",
            "Accept": "application/json",
            "Authorization": f"Bearer {bearer_token}",
        },
    )

    with urllib.request.urlopen(req, timeout=timeout) as response:
        raw = response.read().decode("utf-8", errors="replace")
        return json.loads(raw)


def _insert_run(db, project_id: str, source_id: str | None) -> str:
    row = db.execute(
        text("""
            INSERT INTO social_collection_runs(project_id, platform, source_id, status, message)
            VALUES (CAST(:project_id AS uuid), 'x', CAST(:source_id AS uuid), 'running', 'Coleta X / Twitter iniciada.')
            RETURNING id
        """),
        {"project_id": project_id, "source_id": source_id},
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


def _parse_x_datetime(value: str | None):
    if not value:
        return None
    try:
        return datetime.fromisoformat(value.replace("Z", "+00:00"))
    except Exception:
        return None


def collect_x(db, project_id: str, source_id: str | None = None, query: str | None = None, max_results: int = 10) -> dict:
    bearer_token = _bearer_token()
    run_id = None

    try:
        source = None

        if source_id:
            source = _get_source(db, source_id)

            if not source:
                return {"success": False, "message": "Fonte social não encontrada.", "collected": 0, "saved": 0}

            if str(source.get("project_id")) != str(project_id):
                return {"success": False, "message": "Fonte social não pertence ao projeto informado.", "collected": 0, "saved": 0}

            if source.get("platform") not in ("x", "twitter", "twitter_x"):
                return {"success": False, "message": "Fonte selecionada não é X / Twitter.", "collected": 0, "saved": 0}

            if not source.get("active"):
                return {"success": False, "message": "Fonte social inativa.", "collected": 0, "saved": 0}

        search_query = (query or (source or {}).get("query") or (source or {}).get("handle") or (source or {}).get("name") or "").strip()

        if not search_query:
            return {"success": False, "message": "Informe uma query ou selecione uma fonte X / Twitter com termo de busca.", "collected": 0, "saved": 0}

        run_id = _insert_run(db, project_id, source_id)

        if not bearer_token:
            message = "Token do X / Twitter não configurado. Defina X_BEARER_TOKEN no .env.production."
            _finish_run(db, run_id, "error", message, 0, 0)
            return {"success": False, "message": message, "collected": 0, "saved": 0}

        api_max_results = max(10, min(int(max_results or 10), 100))

        payload = _http_json(
            X_RECENT_SEARCH_URL,
            {
                "query": search_query,
                "max_results": api_max_results,
                "tweet.fields": "created_at,public_metrics,lang,possibly_sensitive,conversation_id",
                "expansions": "author_id",
                "user.fields": "username,name,verified,profile_image_url",
            },
            bearer_token=bearer_token,
        )

        tweets = payload.get("data") or []
        users = {
            user.get("id"): user
            for user in ((payload.get("includes") or {}).get("users") or [])
            if user.get("id")
        }

        saved = 0

        for tweet in tweets:
            tweet_id = tweet.get("id")
            if not tweet_id:
                continue

            author = users.get(tweet.get("author_id")) or {}
            username = author.get("username")
            author_name = author.get("name") or username or "Não identificado"

            url = f"https://x.com/{username}/status/{tweet_id}" if username else f"https://x.com/i/web/status/{tweet_id}"
            text_value = tweet.get("text") or ""
            title = text_value[:120] if text_value else f"Post X / Twitter {tweet_id}"

            metrics_json = {
                "public_metrics": tweet.get("public_metrics") or {},
                "lang": tweet.get("lang"),
                "possibly_sensitive": tweet.get("possibly_sensitive"),
                "conversation_id": tweet.get("conversation_id"),
            }

            matched_terms = {
                "query": search_query,
                "source_name": (source or {}).get("name"),
            }

            db.execute(
                text("""
                    INSERT INTO social_items (
                        project_id, source_id, platform, external_id, content_type,
                        title, author_name, author_handle, url, published_at, text,
                        thumbnail_url, metrics_json, matched_terms, sentiment, topic,
                        editorial_score, ad_score, is_sponsored
                    )
                    VALUES (
                        CAST(:project_id AS uuid), CAST(:source_id AS uuid), 'x', :external_id, 'post',
                        :title, :author_name, :author_handle, :url, :published_at, :text,
                        :thumbnail_url, CAST(:metrics_json AS jsonb), CAST(:matched_terms AS jsonb), 'neutro', 'Social/X',
                        70, 0, false
                    )
                    ON CONFLICT (platform, external_id)
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
                    "external_id": tweet_id,
                    "title": title,
                    "author_name": author_name,
                    "author_handle": f"@{username}" if username else None,
                    "url": url,
                    "published_at": _parse_x_datetime(tweet.get("created_at")),
                    "text": text_value,
                    "thumbnail_url": author.get("profile_image_url"),
                    "metrics_json": json.dumps(metrics_json, ensure_ascii=False),
                    "matched_terms": json.dumps(matched_terms, ensure_ascii=False),
                },
            )
            saved += 1

        db.commit()

        message = f"Coleta X / Twitter finalizada. {len(tweets)} coletados, {saved} salvos."
        _finish_run(db, run_id, "success", message, len(tweets), saved)

        return {"success": True, "message": message, "collected": len(tweets), "saved": saved}

    except Exception as exc:
        try:
            db.rollback()
        except Exception:
            pass

        message = f"Erro na coleta X / Twitter: {exc}"

        if run_id:
            try:
                _finish_run(db, run_id, "error", message, 0, 0)
            except Exception:
                pass

        return {"success": False, "message": message, "collected": 0, "saved": 0}
