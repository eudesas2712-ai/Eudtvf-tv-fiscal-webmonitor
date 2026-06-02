from __future__ import annotations

import csv
import io
import os
import shutil
import time
from datetime import datetime, timedelta
from io import BytesIO
from typing import Any, Callable, Dict, List

import boto3
import redis
from botocore.client import Config
from botocore.config import Config as BotoConfig
from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.platypus import Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle
from sqlalchemy import text
from sqlalchemy.orm import Session

from app.core.config import settings
from app.services.maintenance_service import backup_freshness
from app.services.snapshot_scheduler import get_snapshot_scheduler_status, list_scheduler_runs
from app.utils.timeutils import display_local, utc_now


STATUS_ORDER = {"ok": 0, "warning": 1, "error": 2}
STATUS_LABEL = {"ok": "OK", "warning": "Atenção", "error": "Erro"}


def _ms(start: float) -> int:
    return int((time.perf_counter() - start) * 1000)


def _safe_int(value: Any, default: int = 0) -> int:
    try:
        return int(value or default)
    except Exception:
        return default


def _run_check(service: str, label: str, fn: Callable[[], Dict[str, Any]]) -> Dict[str, Any]:
    started = time.perf_counter()
    try:
        data = fn() or {}
        latency = data.pop("latency_ms", _ms(started))
        status = data.pop("status", "ok")
        message = data.pop("message", "Serviço operacional.")
        return {
            "service": service,
            "label": label,
            "status": status if status in STATUS_ORDER else "warning",
            "message": message,
            "latency_ms": latency,
            "details": data,
            "checked_at": utc_now().isoformat(timespec="seconds"),
            "checked_at_display": display_local(utc_now()),
        }
    except Exception as exc:  # noqa: BLE001
        return {
            "service": service,
            "label": label,
            "status": "error",
            "message": str(exc)[:1000],
            "latency_ms": _ms(started),
            "details": {},
            "checked_at": utc_now().isoformat(timespec="seconds"),
            "checked_at_display": display_local(utc_now()),
        }


def _database_check(db: Session) -> Dict[str, Any]:
    started = time.perf_counter()
    value = db.execute(text("SELECT 1")).scalar()
    counts = {}
    for table in [
        "projects",
        "items",
        "banner_items",
        "notification_logs",
        "scheduler_runs",
        "notification_automation_runs",
    ]:
        try:
            counts[table] = int(db.execute(text(f"SELECT COUNT(*) FROM {table}")).scalar() or 0)
        except Exception:
            counts[table] = None
    return {
        "status": "ok" if value == 1 else "warning",
        "message": "PostgreSQL respondendo normalmente." if value == 1 else "PostgreSQL respondeu fora do esperado.",
        "latency_ms": _ms(started),
        "counts": counts,
    }


def _redis_check() -> Dict[str, Any]:
    started = time.perf_counter()
    client = redis.Redis.from_url(settings.REDIS_URL, socket_connect_timeout=3, socket_timeout=3)
    ok = client.ping()
    info = {}
    try:
        raw_info = client.info(section="server")
        info = {
            "redis_version": raw_info.get("redis_version"),
            "uptime_in_seconds": raw_info.get("uptime_in_seconds"),
        }
    except Exception:
        info = {}
    return {
        "status": "ok" if ok else "warning",
        "message": "Redis respondendo." if ok else "Redis não respondeu ao ping.",
        "latency_ms": _ms(started),
        **info,
    }


def _minio_check() -> Dict[str, Any]:
    started = time.perf_counter()
    client = boto3.client(
        "s3",
        endpoint_url=f"http://{settings.MINIO_ENDPOINT}",
        aws_access_key_id=settings.MINIO_ACCESS_KEY,
        aws_secret_access_key=settings.MINIO_SECRET_KEY,
        config=BotoConfig(signature_version="s3v4", connect_timeout=3, read_timeout=4, retries={"max_attempts": 1}),
        region_name="us-east-1",
    )
    bucket = settings.MINIO_BUCKET
    try:
        client.head_bucket(Bucket=bucket)
        bucket_ok = True
    except Exception:
        bucket_ok = False
    object_count = None
    try:
        page = client.list_objects_v2(Bucket=bucket, MaxKeys=1)
        object_count = page.get("KeyCount", 0)
    except Exception:
        object_count = None
    return {
        "status": "ok" if bucket_ok else "error",
        "message": f"Bucket MinIO '{bucket}' acessível." if bucket_ok else f"Bucket MinIO '{bucket}' não acessível.",
        "latency_ms": _ms(started),
        "endpoint": settings.MINIO_ENDPOINT,
        "bucket": bucket,
        "sample_key_count": object_count,
    }


def _scheduler_check() -> Dict[str, Any]:
    status = get_snapshot_scheduler_status()
    running = bool(status.get("running"))
    enabled = bool(status.get("enabled"))
    recent_runs = list_scheduler_runs(limit=10)
    recent_errors = [r for r in recent_runs if r.get("status") == "error"]
    last_error = status.get("last_error")
    if not enabled:
        check_status = "warning"
        message = "Scheduler desativado por configuração."
    elif not running:
        check_status = "error"
        message = "Scheduler deveria estar ativo, mas não está rodando."
    elif recent_errors and not status.get("last_success_at"):
        check_status = "warning"
        message = "Scheduler rodando, mas com erros recentes."
    else:
        check_status = "ok"
        message = "Scheduler em execução."
    return {
        "status": check_status,
        "message": message,
        "enabled": enabled,
        "running": running,
        "last_success_at": status.get("last_success_at"),
        "last_error_at": status.get("last_error_at"),
        "last_error": last_error,
        "run_count": status.get("run_count"),
        "scan_count": status.get("scan_count"),
        "recent_errors": len(recent_errors),
    }


def _disk_check() -> Dict[str, Any]:
    path = os.getenv("HEALTH_DISK_PATH", "/app")
    usage = shutil.disk_usage(path if os.path.exists(path) else "/")
    pct = round((usage.used / usage.total) * 100, 2) if usage.total else 0
    if pct >= 90:
        status = "error"
        message = "Uso de disco crítico."
    elif pct >= 80:
        status = "warning"
        message = "Uso de disco elevado."
    else:
        status = "ok"
        message = "Uso de disco dentro do esperado."
    return {
        "status": status,
        "message": message,
        "path": path,
        "used_percent": pct,
        "total_bytes": usage.total,
        "used_bytes": usage.used,
        "free_bytes": usage.free,
    }


def _backup_check() -> Dict[str, Any]:
    freshness = backup_freshness()
    return {
        "status": freshness.get("status", "warning"),
        "message": freshness.get("message", "Status de backup indisponível."),
        "backup_count": freshness.get("backup_count", 0),
        "latest_backup": freshness.get("latest_backup"),
        "age_hours": freshness.get("age_hours"),
        "warning_hours": freshness.get("warning_hours"),
        "error_hours": freshness.get("error_hours"),
    }


def _notification_check(db: Session) -> Dict[str, Any]:
    rows = db.execute(
        text("""
            SELECT provider_type, COUNT(*)
            FROM notification_provider_settings
            WHERE active IS TRUE
            GROUP BY provider_type
        """)
    ).fetchall()
    providers = {str(row[0]): int(row[1]) for row in rows}
    last_errors = db.execute(
        text("""
            SELECT COUNT(*)
            FROM notification_logs
            WHERE status IN ('error', 'erro')
              AND created_at >= NOW() - INTERVAL '24 hours'
              AND archived_at IS NULL
        """)
    ).scalar() or 0
    archived_errors = db.execute(
        text("""
            SELECT COUNT(*)
            FROM notification_logs
            WHERE status IN ('error', 'erro')
              AND created_at >= NOW() - INTERVAL '24 hours'
              AND archived_at IS NOT NULL
        """)
    ).scalar() or 0
    if last_errors:
        status = "warning"
        message = f"Há {last_errors} erro(s) ativo(s) de notificação nas últimas 24h."
    else:
        status = "ok"
        message = "Motor de notificações sem erros ativos recentes."
    return {
        "status": status,
        "message": message,
        "providers": providers,
        "last_24h_errors": int(last_errors),
        "archived_24h_errors": int(archived_errors or 0),
    }


def _recent_activity(db: Session) -> Dict[str, Any]:
    since = datetime.utcnow() - timedelta(hours=24)
    activity = {}
    for key, table in [
        ("items_24h", "items"),
        ("banners_24h", "banner_items"),
        ("notifications_24h", "notification_logs"),
        ("scheduler_runs_24h", "scheduler_runs"),
    ]:
        try:
            activity[key] = int(db.execute(text(f"SELECT COUNT(*) FROM {table} WHERE created_at >= :since"), {"since": since}).scalar() or 0)
        except Exception:
            activity[key] = 0
    return activity


def _persist_check_results(db: Session, checks: List[Dict[str, Any]], trigger_source: str = "manual") -> None:
    for item in checks:
        db.execute(
            text("""
                INSERT INTO system_health_checks
                (service, status, latency_ms, message, details, trigger_source)
                VALUES (:service, :status, :latency_ms, :message, CAST(:details AS JSONB), :trigger_source)
            """),
            {
                "service": item.get("service"),
                "status": item.get("status"),
                "latency_ms": item.get("latency_ms"),
                "message": item.get("message"),
                "details": __import__("json").dumps(item.get("details") or {}, ensure_ascii=False),
                "trigger_source": trigger_source,
            },
        )
    db.commit()


def advanced_health(db: Session, *, persist: bool = False, trigger_source: str = "manual") -> Dict[str, Any]:
    checks = [
        _run_check("database", "PostgreSQL", lambda: _database_check(db)),
        _run_check("redis", "Redis", _redis_check),
        _run_check("minio", "MinIO / Evidências", _minio_check),
        _run_check("scheduler", "Scheduler", _scheduler_check),
        _run_check("disk", "Disco", _disk_check),
        _run_check("backup", "Backup", _backup_check),
        _run_check("notifications", "Notificações", lambda: _notification_check(db)),
    ]
    worst = max(checks, key=lambda item: STATUS_ORDER.get(item.get("status", "warning"), 1))
    overall = worst.get("status", "warning")
    activity = _recent_activity(db)
    summary = {
        "overall_status": overall,
        "overall_label": STATUS_LABEL.get(overall, overall),
        "ok": sum(1 for c in checks if c.get("status") == "ok"),
        "warning": sum(1 for c in checks if c.get("status") == "warning"),
        "error": sum(1 for c in checks if c.get("status") == "error"),
        "services": len(checks),
        "activity_24h": activity,
    }
    if persist:
        _persist_check_results(db, checks, trigger_source=trigger_source)
    return {
        "app": "TV Fiscal WebMonitor",
        "generated_at": utc_now().isoformat(timespec="seconds"),
        "generated_at_display": display_local(utc_now()),
        "summary": summary,
        "checks": checks,
        "uptime_robot": {
            "live_url": "/health/live",
            "ready_url": "/health/ready",
            "advanced_url": "/system/health/uptime",
            "expected_http_status": 200 if overall != "error" else 503,
        },
        "recommendations": health_recommendations(checks, summary),
    }


def health_recommendations(checks: List[Dict[str, Any]], summary: Dict[str, Any]) -> List[str]:
    recs: List[str] = []
    by_service = {c.get("service"): c for c in checks}
    if by_service.get("backup", {}).get("status") != "ok":
        recs.append("Gerar backup em /admin/maintenance ou ativar AUTO_BACKUP_ENABLED=true para manter rotina de produção protegida.")
    if by_service.get("scheduler", {}).get("status") != "ok":
        recs.append("Verificar o Scheduler em /admin/scheduler e revisar histórico de erros.")
    if by_service.get("minio", {}).get("status") == "error":
        recs.append("Verificar MinIO/evidências, pois a preservação de prova pode estar indisponível.")
    if by_service.get("notifications", {}).get("status") != "ok":
        recs.append("Revisar logs ativos do Motor de Notificações ou arquivar erros históricos em /admin/maintenance.")
    if not recs and summary.get("overall_status") == "ok":
        recs.append("Ambiente operacional saudável. Manter rotina de backup, scheduler e alertas monitorados.")
    return recs


def history(db: Session, *, limit: int = 100, service: str | None = None, status: str | None = None) -> List[Dict[str, Any]]:
    limit = max(1, min(int(limit or 100), 1000))
    filters = []
    params: Dict[str, Any] = {"limit": limit}
    if service:
        filters.append("service = :service")
        params["service"] = service
    if status:
        filters.append("status = :status")
        params["status"] = status
    where_sql = "WHERE " + " AND ".join(filters) if filters else ""
    rows = db.execute(
        text(f"""
            SELECT id, service, status, latency_ms, message, details, trigger_source, created_at
            FROM system_health_checks
            {where_sql}
            ORDER BY created_at DESC
            LIMIT :limit
        """),
        params,
    ).fetchall()
    return [
        {
            "id": str(row[0]),
            "service": row[1],
            "status": row[2],
            "latency_ms": row[3],
            "message": row[4],
            "details": row[5] or {},
            "trigger_source": row[6],
            "created_at": row[7].isoformat(timespec="seconds") if row[7] else None,
            "created_at_display": display_local(row[7]) if row[7] else "—",
        }
        for row in rows
    ]


def history_csv(db: Session, *, limit: int = 1000) -> str:
    rows = history(db, limit=limit)
    output = io.StringIO()
    writer = csv.writer(output, delimiter=";")
    writer.writerow(["Data", "Serviço", "Status", "Latência ms", "Origem", "Mensagem"])
    for row in rows:
        writer.writerow([
            row.get("created_at_display"),
            row.get("service"),
            row.get("status"),
            row.get("latency_ms"),
            row.get("trigger_source"),
            row.get("message"),
        ])
    output.seek(0)
    return output.getvalue()


def technical_report_pdf(db: Session) -> bytes:
    data = advanced_health(db, persist=True, trigger_source="pdf_report")
    buffer = BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=A4, rightMargin=36, leftMargin=36, topMargin=36, bottomMargin=36)
    styles = getSampleStyleSheet()
    story = []
    story.append(Paragraph("TV Fiscal WebMonitor — Relatório Técnico de Saúde", styles["Title"]))
    story.append(Paragraph(f"Gerado em: {data.get('generated_at_display')}", styles["Normal"]))
    story.append(Spacer(1, 12))
    summary = data.get("summary") or {}
    story.append(Paragraph(f"Status geral: <b>{summary.get('overall_label')}</b>", styles["Heading2"]))
    story.append(Paragraph("Recomendações", styles["Heading3"]))
    for rec in data.get("recommendations") or []:
        story.append(Paragraph(f"• {rec}", styles["Normal"]))
    story.append(Spacer(1, 12))
    table_data = [["Serviço", "Status", "Latência", "Mensagem"]]
    for check in data.get("checks") or []:
        table_data.append([
            check.get("label"),
            STATUS_LABEL.get(check.get("status"), check.get("status")),
            f"{check.get('latency_ms')} ms",
            check.get("message"),
        ])
    table = Table(table_data, colWidths=[95, 65, 60, 300])
    table.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#0B1F3A")),
        ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
        ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
        ("FONTSIZE", (0, 0), (-1, -1), 8),
        ("GRID", (0, 0), (-1, -1), 0.25, colors.HexColor("#D0D5DD")),
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
    ]))
    story.append(table)
    doc.build(story)
    return buffer.getvalue()


def quick_ready(db: Session) -> Dict[str, Any]:
    db_ok = False
    try:
        db_ok = db.execute(text("SELECT 1")).scalar() == 1
    except Exception:
        db_ok = False
    scheduler = get_snapshot_scheduler_status()
    status = "ok" if db_ok else "error"
    return {
        "status": status,
        "database": "ok" if db_ok else "error",
        "scheduler_running": bool(scheduler.get("running")),
        "checked_at": display_local(utc_now()),
    }
