import os
import time
import threading
import urllib.request
import urllib.error
from datetime import datetime, timezone
from uuid import UUID

from sqlalchemy import text

from app.db.models import BannerItem, Portal, Project, ProjectPortal
from app.db.session import SessionLocal
from app.services.banner_service import scan_page_for_banners
from app.services.content_classifier import classify_detected_item
from app.services.identification_review import apply_aliases_to_pending_items, identification_quality_summary
from app.services.notification_service import evaluate_automatic_notification_rules, notification_config


_scheduler_thread = None
_stop_event = None

_scheduler_state = {
    "enabled": False,
    "running": False,
    "started_at": None,
    "last_cycle_started_at": None,
    "last_success_at": None,
    "last_error_at": None,
    "last_error": None,
    "last_project_id": None,
    "last_portal_url": None,
    "last_scan_at": None,
    "last_scan_summary": None,
    "run_count": 0,
    "scan_count": 0,
    "next_interval_seconds": None,
    "last_identification_at": None,
    "last_identification_summary": None,
}


def _now_iso():
    return datetime.now(timezone.utc).isoformat()


def _get_env_project_ids() -> list[str]:
    raw = os.getenv(
        "SNAPSHOT_PROJECT_IDS",
        "9b972aa2-f8a4-483b-a7d1-e979d86482fb",
    )
    return [project_id.strip() for project_id in raw.split(",") if project_id.strip()]


def _get_interval_seconds() -> int:
    try:
        return int(os.getenv("SNAPSHOT_INTERVAL_SECONDS", "3600"))
    except ValueError:
        return 3600


def _get_base_url() -> str:
    return os.getenv("SNAPSHOT_API_BASE_URL", "http://127.0.0.1:8000").rstrip("/")


def _scan_registered_portals_enabled() -> bool:
    return os.getenv("SNAPSHOT_SCAN_REGISTERED_PORTALS", "true").lower() in {"1", "true", "yes", "sim"}


def _auto_identification_enabled() -> bool:
    return os.getenv("IDENTIFICATION_AUTO_REPROCESS_AFTER_SCAN", "true").lower() in {"1", "true", "yes", "sim"}


def _auto_identify_project(project_id: str, limit: int = 20000) -> dict:
    """Aplica aliases ativos após coletas para reduzir pendências antes do Intel/relatórios.

    A função não cria novos aliases; ela apenas aplica o aprendizado já validado pelo
    operador em /admin/identificacao. Assim, a automação melhora a base sem inventar
    marcas ou contaminar o ranking.
    """
    if not _auto_identification_enabled():
        return {"enabled": False, "updated": 0, "message": "Autoidentificação por alias desativada."}

    db = SessionLocal()
    try:
        result = apply_aliases_to_pending_items(db, project_id=project_id, limit=limit)
        quality = identification_quality_summary(db, project_id)
        payload = {
            "enabled": True,
            "project_id": project_id,
            "updated": int(result.get("updated") or 0),
            "matches": result.get("matches") or [],
            "identified_rate": quality.get("identified_rate"),
            "pending_rate": quality.get("pending_rate"),
            "pending_items": quality.get("pending_items"),
            "quality_label": quality.get("quality_label"),
            "message": result.get("message"),
        }
        _scheduler_state["last_identification_at"] = _now_iso()
        _scheduler_state["last_identification_summary"] = payload
        if payload["updated"]:
            _save_scheduler_run(
                project_id,
                "success",
                f"Autoidentificação pós-coleta: {payload['updated']} item(ns) qualificado(s) por alias.",
            )
        return payload
    except Exception as exc:
        message = f"Erro na autoidentificação pós-coleta: {exc}"
        _scheduler_state["last_error_at"] = _now_iso()
        _scheduler_state["last_error"] = message
        _save_scheduler_run(project_id, "error", message)
        return {"enabled": True, "updated": 0, "error": message}
    finally:
        db.close()


def _uuid(value: str) -> UUID:
    return UUID(str(value))


def _save_scheduler_run(project_id: str | None, status: str, message: str):
    db = SessionLocal()
    try:
        db.execute(
            text("""
                INSERT INTO scheduler_runs
                (project_id, status, message)
                VALUES (:project_id, :status, :message)
            """),
            {
                "project_id": project_id,
                "status": status,
                "message": message,
            },
        )
        db.commit()
    except Exception as exc:
        db.rollback()
        print(f"[snapshot_scheduler] erro ao registrar histórico: {exc}", flush=True)
    finally:
        db.close()


def get_scheduler_recent_runs(limit: int = 10):
    db = SessionLocal()
    try:
        rows = db.execute(
            text("""
                SELECT project_id, status, message, created_at
                FROM scheduler_runs
                ORDER BY created_at DESC
                LIMIT :limit
            """),
            {"limit": limit},
        ).fetchall()

        return [
            {
                "project_id": str(row[0]) if row[0] else None,
                "status": row[1],
                "message": row[2],
                "created_at": row[3].isoformat() if row[3] else None,
            }
            for row in rows
        ]
    except Exception as exc:
        print(f"[snapshot_scheduler] erro ao carregar histórico: {exc}", flush=True)
        return []
    finally:
        db.close()


def _get_registered_project_ids() -> list[str]:
    """Retorna projetos com ao menos um portal ativo vinculado.

    Se ainda não houver vínculos, mantém compatibilidade com SNAPSHOT_PROJECT_IDS.
    """
    db = SessionLocal()
    try:
        rows = (
            db.query(ProjectPortal.project_id)
            .join(Portal, Portal.id == ProjectPortal.portal_id)
            .join(Project, Project.id == ProjectPortal.project_id)
            .filter(ProjectPortal.active.is_(True), Portal.active.is_(True), Project.active.isnot(False))
            .distinct()
            .all()
        )
        project_ids = [str(row[0]) for row in rows if row[0]]
        return project_ids or _get_env_project_ids()
    except Exception as exc:
        print(f"[snapshot_scheduler] erro ao carregar projetos cadastrados: {exc}", flush=True)
        return _get_env_project_ids()
    finally:
        db.close()


def _get_project_ids() -> list[str]:
    if os.getenv("SNAPSHOT_USE_REGISTERED_PROJECTS", "true").lower() in {"1", "true", "yes", "sim"}:
        return _get_registered_project_ids()
    return _get_env_project_ids()


def _get_project_portals(project_id: str) -> list[dict]:
    db = SessionLocal()
    try:
        project_uuid = _uuid(project_id)
        rows = (
            db.query(Portal)
            .join(ProjectPortal, ProjectPortal.portal_id == Portal.id)
            .filter(
                ProjectPortal.project_id == project_uuid,
                ProjectPortal.active.is_(True),
                Portal.active.is_(True),
                Portal.monitor_publicity.is_(True),
            )
            .order_by(Portal.name.asc())
            .all()
        )
        return [
            {
                "id": str(row.id),
                "name": row.name,
                "base_url": row.base_url,
                "category": row.category,
                "interval_minutes": row.interval_minutes,
                "monitor_publicity": row.monitor_publicity,
                "monitor_editorial": row.monitor_editorial,
            }
            for row in rows
        ]
    except Exception as exc:
        print(f"[snapshot_scheduler] erro ao carregar portais do projeto {project_id}: {exc}", flush=True)
        return []
    finally:
        db.close()


def get_configured_project_portals() -> list[dict]:
    project_ids = _get_project_ids()
    db = SessionLocal()
    try:
        projects = {str(row.id): row for row in db.query(Project).filter(Project.id.in_([_uuid(pid) for pid in project_ids if pid])).all()}
    except Exception:
        projects = {}
    finally:
        db.close()

    return [
        {
            "project_id": project_id,
            "project_name": projects.get(project_id).name if projects.get(project_id) else f"Projeto {project_id[:8]}",
            "portals": _get_project_portals(project_id),
        }
        for project_id in project_ids
    ]


def _collect_snapshot(project_id: str, base_url: str):
    url = f"{base_url}/intel/summary/{project_id}"
    try:
        with urllib.request.urlopen(url, timeout=60) as response:
            response.read()

        message = "Snapshot automático coletado com sucesso."
        _scheduler_state["last_success_at"] = _now_iso()
        _scheduler_state["last_project_id"] = project_id
        _scheduler_state["last_error"] = None
        _scheduler_state["run_count"] = int(_scheduler_state.get("run_count") or 0) + 1
        _save_scheduler_run(project_id, "success", message)
        print(f"[snapshot_scheduler] snapshot automático coletado para {project_id}", flush=True)
        return {"success": True, "project_id": project_id, "message": message}

    except urllib.error.URLError as exc:
        message = str(exc)
        _scheduler_state["last_error_at"] = _now_iso()
        _scheduler_state["last_error"] = message
        _scheduler_state["last_project_id"] = project_id
        _save_scheduler_run(project_id, "error", message)
        print(f"[snapshot_scheduler] falha ao coletar snapshot para {project_id}: {exc}", flush=True)
        return {"success": False, "project_id": project_id, "message": message}

    except Exception as exc:
        message = str(exc)
        _scheduler_state["last_error_at"] = _now_iso()
        _scheduler_state["last_error"] = message
        _scheduler_state["last_project_id"] = project_id
        _save_scheduler_run(project_id, "error", message)
        print(f"[snapshot_scheduler] erro inesperado ao coletar snapshot para {project_id}: {exc}", flush=True)
        return {"success": False, "project_id": project_id, "message": message}


def _insert_banner_rows(project_id: str, rows: list[dict]) -> int:
    if not rows:
        return 0

    db = SessionLocal()
    inserted = 0
    try:
        project_uuid = _uuid(project_id)
        for row in rows:
            item = BannerItem(
                project_id=project_uuid,
                page_url=row.get("page_url") or "",
                image_url=row.get("image_url") or "",
                alt_text=row.get("alt_text"),
                width=row.get("width") or 0,
                height=row.get("height") or 0,
                normalized_width=row.get("normalized_width") or 0,
                normalized_height=row.get("normalized_height") or 0,
                estimated_value=row.get("estimated_value") or 0,
                pos_x=row.get("pos_x") or 0,
                pos_y=row.get("pos_y") or 0,
                source_name=row.get("source_name"),
                evidence_html_key=row.get("evidence_html_key"),
                evidence_html_url=row.get("evidence_html_url"),
                screenshot_page_key=row.get("screenshot_page_key"),
                screenshot_page_url=row.get("screenshot_page_url"),
                screenshot_banner_key=row.get("screenshot_banner_key"),
                screenshot_banner_url=row.get("screenshot_banner_url"),
                ocr_text=row.get("ocr_text"),
                advertiser_name=row.get("advertiser_name"),
                classification=row.get("classification"),
                classification_score=row.get("classification_score") or 0,
                classification_reason=row.get("classification_reason"),
                content_type=row.get("content_type"),
                checking_status=row.get("checking_status"),
                market_status=row.get("market_status"),
                news_status=row.get("news_status"),
                publicity_score=row.get("publicity_score") or row.get("classification_score") or 0,
                news_score=row.get("news_score") or 0,
                market_score=row.get("market_score") or 0,
                has_preserved_evidence=bool(row.get("has_preserved_evidence")),
                evidence_type=row.get("evidence_type"),
            )
            db.add(item)
            inserted += 1
        db.commit()
        return inserted
    except Exception:
        db.rollback()
        raise
    finally:
        db.close()


def _scan_portal(project_id: str, portal: dict, save_rejected: bool = True) -> dict:
    url = portal.get("base_url")
    if not url:
        return {"project_id": project_id, "portal": portal, "success": False, "message": "Portal sem URL."}

    try:
        raw_rows = [
            classify_detected_item(row)
            for row in scan_page_for_banners(project_id=project_id, url=url)
        ]
        accepted_rows = [row for row in raw_rows if row.get("checking_status") == "auditavel"]
        rejected_rows = [row for row in raw_rows if row.get("checking_status") == "rejeitado"]
        market_rows = [row for row in raw_rows if row.get("market_status") == "incluido"]
        news_rows = [row for row in raw_rows if row.get("news_status") == "candidato"]
        rows_to_insert = raw_rows if save_rejected else accepted_rows
        inserted = _insert_banner_rows(project_id, rows_to_insert)

        summary = {
            "project_id": project_id,
            "portal_id": portal.get("id"),
            "portal_name": portal.get("name"),
            "url": url,
            "success": True,
            "detected": len(raw_rows),
            "accepted": len(accepted_rows),
            "auditables": len(accepted_rows),
            "rejected": len(rejected_rows),
            "inserted": inserted,
            "market_included": len(market_rows),
            "news_candidates": len(news_rows),
            "saved_all": save_rejected,
        }
        _scheduler_state["last_scan_at"] = _now_iso()
        _scheduler_state["last_project_id"] = project_id
        _scheduler_state["last_portal_url"] = url
        _scheduler_state["scan_count"] = int(_scheduler_state.get("scan_count") or 0) + 1
        _save_scheduler_run(
            project_id,
            "success",
            f"Varredura do portal {portal.get('name') or url}: {len(raw_rows)} detectados, {len(accepted_rows)} auditáveis, {inserted} salvos.",
        )
        print(f"[snapshot_scheduler] portal escaneado: {project_id} {url}", flush=True)
        return summary
    except Exception as exc:
        message = str(exc)
        _scheduler_state["last_error_at"] = _now_iso()
        _scheduler_state["last_error"] = message
        _scheduler_state["last_project_id"] = project_id
        _scheduler_state["last_portal_url"] = url
        _save_scheduler_run(project_id, "error", f"Erro ao escanear portal {portal.get('name') or url}: {message}")
        print(f"[snapshot_scheduler] erro ao escanear portal {url}: {message}", flush=True)
        return {
            "project_id": project_id,
            "portal_id": portal.get("id"),
            "portal_name": portal.get("name"),
            "url": url,
            "success": False,
            "message": message,
        }


def run_registered_portal_scans_now(project_id: str | None = None, save_rejected: bool = True) -> dict:
    project_ids = [project_id] if project_id else _get_project_ids()
    results = []

    for current_project_id in project_ids:
        portals = _get_project_portals(current_project_id)
        if not portals:
            results.append({
                "project_id": current_project_id,
                "success": False,
                "message": "Nenhum portal ativo vinculado ao projeto.",
                "portals": [],
            })
            _save_scheduler_run(current_project_id, "error", "Nenhum portal ativo vinculado ao projeto.")
            continue

        for portal in portals:
            results.append(_scan_portal(current_project_id, portal, save_rejected=save_rejected))

        identification_summary = _auto_identify_project(current_project_id)
        results.append({
            "project_id": current_project_id,
            "success": True,
            "type": "identification_auto",
            "identification": identification_summary,
            "updated": int(identification_summary.get("updated") or 0),
        })

        notification_summary = _evaluate_notifications_after_collection(current_project_id, source="manual_portal_scan")
        results.append({
            "project_id": current_project_id,
            "success": True,
            "type": "notifications",
            "notifications": notification_summary,
            "sent_or_registered": int(notification_summary.get("notifications") or 0),
        })

        _collect_snapshot(current_project_id, _get_base_url())

    portal_results = [item for item in results if item.get("type") != "identification_auto"]
    totals = {
        "projects": len(project_ids),
        "portals": len(portal_results),
        "detected": sum(int(item.get("detected") or 0) for item in portal_results),
        "auditables": sum(int(item.get("auditables") or 0) for item in portal_results),
        "inserted": sum(int(item.get("inserted") or 0) for item in portal_results),
        "market_included": sum(int(item.get("market_included") or 0) for item in portal_results),
        "news_candidates": sum(int(item.get("news_candidates") or 0) for item in portal_results),
        "auto_identified": sum(int(item.get("updated") or 0) for item in results if item.get("type") == "identification_auto"),
        "notifications": sum(int(item.get("sent_or_registered") or 0) for item in results if item.get("type") == "notifications"),
        "errors": len([item for item in portal_results if not item.get("success")]),
    }
    _scheduler_state["last_scan_summary"] = totals
    return {"executed": True, "totals": totals, "results": results, "status": get_snapshot_scheduler_status()}



def _evaluate_notifications_after_collection(project_id: str, source: str = "scheduler") -> dict:
    try:
        if not notification_config().get("auto_after_scheduler"):
            return {"enabled": False, "notifications": 0, "message": "Avaliação automática de notificações desativada."}
        db = SessionLocal()
        try:
            result = evaluate_automatic_notification_rules(db, project_id=project_id, trigger_source=source)
            if int(result.get("notifications") or 0):
                _save_scheduler_run(project_id, "success", f"Notificações avaliadas: {result.get('notifications')} registro(s) gerado(s).")
            return result
        finally:
            db.close()
    except Exception as exc:
        message = f"Erro ao avaliar notificações pós-coleta: {exc}"
        _save_scheduler_run(project_id, "error", message)
        return {"enabled": True, "notifications": 0, "error": message}


def _run_scheduler(stop_event: threading.Event):
    interval = _get_interval_seconds()
    _scheduler_state["next_interval_seconds"] = interval

    try:
        startup_delay = int(os.getenv("SNAPSHOT_STARTUP_DELAY_SECONDS", "15"))
    except ValueError:
        startup_delay = 15

    print(f"[snapshot_scheduler] aguardando {startup_delay}s para iniciar a primeira coleta...", flush=True)
    time.sleep(startup_delay)

    while not stop_event.is_set():
        _scheduler_state["last_cycle_started_at"] = _now_iso()
        project_ids = _get_project_ids()

        if not project_ids:
            print("[snapshot_scheduler] nenhum project_id configurado.", flush=True)

        for project_id in project_ids:
            if stop_event.is_set():
                break

            if _scan_registered_portals_enabled():
                portals = _get_project_portals(project_id)
                for portal in portals:
                    if stop_event.is_set():
                        break
                    _scan_portal(project_id, portal, save_rejected=True)

                _auto_identify_project(project_id)
                _evaluate_notifications_after_collection(project_id, source="scheduler_cycle")

            _collect_snapshot(project_id, _get_base_url())

        stop_event.wait(interval)

    _scheduler_state["running"] = False
    print("[snapshot_scheduler] parado.", flush=True)


def start_snapshot_scheduler():
    global _scheduler_thread, _stop_event

    enabled = os.getenv("SNAPSHOT_SCHEDULER_ENABLED", "true").lower() == "true"
    _scheduler_state["enabled"] = enabled
    _scheduler_state["next_interval_seconds"] = _get_interval_seconds()

    if not enabled:
        _scheduler_state["running"] = False
        print("[snapshot_scheduler] desativado por configuração.", flush=True)
        return None

    if _scheduler_thread and _scheduler_thread.is_alive():
        _scheduler_state["running"] = True
        print("[snapshot_scheduler] já estava em execução.", flush=True)
        return _stop_event

    _stop_event = threading.Event()
    _scheduler_thread = threading.Thread(
        target=_run_scheduler,
        args=(_stop_event,),
        daemon=True,
        name="tvfiscal_snapshot_scheduler",
    )
    _scheduler_thread.start()
    _scheduler_state["running"] = True
    _scheduler_state["started_at"] = _now_iso()
    print("[snapshot_scheduler] iniciado.", flush=True)
    return _stop_event


def stop_snapshot_scheduler():
    global _stop_event
    if _stop_event:
        _stop_event.set()
        _scheduler_state["running"] = False
        print("[snapshot_scheduler] parada solicitada.", flush=True)


def get_snapshot_scheduler_status():
    recent_runs = get_scheduler_recent_runs()
    configured = get_configured_project_portals()
    return {
        "enabled": _scheduler_state.get("enabled"),
        "running": bool(_scheduler_thread and _scheduler_thread.is_alive()),
        "started_at": _scheduler_state.get("started_at"),
        "last_cycle_started_at": _scheduler_state.get("last_cycle_started_at"),
        "last_success_at": _scheduler_state.get("last_success_at"),
        "last_error_at": _scheduler_state.get("last_error_at"),
        "last_error": _scheduler_state.get("last_error"),
        "last_project_id": _scheduler_state.get("last_project_id"),
        "last_portal_url": _scheduler_state.get("last_portal_url"),
        "last_scan_at": _scheduler_state.get("last_scan_at"),
        "last_scan_summary": _scheduler_state.get("last_scan_summary"),
        "run_count": _scheduler_state.get("run_count"),
        "scan_count": _scheduler_state.get("scan_count"),
        "interval_seconds": _get_interval_seconds(),
        "project_ids": _get_project_ids(),
        "env_project_ids": _get_env_project_ids(),
        "use_registered_projects": os.getenv("SNAPSHOT_USE_REGISTERED_PROJECTS", "true").lower() in {"1", "true", "yes", "sim"},
        "scan_registered_portals": _scan_registered_portals_enabled(),
        "base_url": _get_base_url(),
        "configured_projects": configured,
        "configured_portal_count": sum(len(item.get("portals") or []) for item in configured),
        "recent_runs": recent_runs,
        "history": recent_runs,
    }


def run_snapshot_now():
    results = []
    for project_id in _get_project_ids():
        results.append(_collect_snapshot(project_id, _get_base_url()))
    return {"executed": True, "results": results, "status": get_snapshot_scheduler_status()}


def disable_snapshot_scheduler():
    global _stop_event
    if _stop_event:
        _stop_event.set()
    _scheduler_state["enabled"] = False
    _scheduler_state["running"] = False
    print("[snapshot_scheduler] desativado manualmente pela interface.", flush=True)
    return get_snapshot_scheduler_status()


def enable_snapshot_scheduler():
    _scheduler_state["enabled"] = True
    print("[snapshot_scheduler] ativação manual solicitada pela interface.", flush=True)
    start_snapshot_scheduler()
    return get_snapshot_scheduler_status()


def start_scheduler():
    return start_snapshot_scheduler()


def list_scheduler_runs(limit: int = 50, status: str | None = None, project_id: str | None = None):
    db = SessionLocal()
    try:
        limit = max(1, min(int(limit or 50), 200))
        filters = []
        params = {"limit": limit}

        if status and status != "all":
            filters.append("status = :status")
            params["status"] = status
        if project_id:
            filters.append("project_id = :project_id")
            params["project_id"] = project_id

        where_sql = ""
        if filters:
            where_sql = "WHERE " + " AND ".join(filters)

        rows = db.execute(
            text(f"""
                SELECT id, project_id, status, message, created_at
                FROM scheduler_runs
                {where_sql}
                ORDER BY created_at DESC
                LIMIT :limit
            """),
            params,
        ).fetchall()

        return [
            {
                "id": str(row[0]),
                "project_id": str(row[1]) if row[1] else None,
                "status": row[2],
                "message": row[3],
                "created_at": row[4].isoformat() if row[4] else None,
            }
            for row in rows
        ]
    finally:
        db.close()


def clear_scheduler_runs(status: str | None = None, project_id: str | None = None):
    db = SessionLocal()
    try:
        filters = []
        params = {}
        if status and status != "all":
            filters.append("status = :status")
            params["status"] = status
        if project_id:
            filters.append("project_id = :project_id")
            params["project_id"] = project_id

        where_sql = ""
        if filters:
            where_sql = "WHERE " + " AND ".join(filters)

        rows = db.execute(
            text(f"""
                DELETE FROM scheduler_runs
                {where_sql}
                RETURNING id
            """),
            params,
        ).fetchall()
        db.commit()
        return {"cleared": True, "deleted_count": len(rows), "status_filter": status or "all", "project_id_filter": project_id or "all"}
    except Exception:
        db.rollback()
        raise
    finally:
        db.close()
