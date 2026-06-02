import csv
import io
import json
import os
import shutil
import subprocess
import tempfile
import zipfile
from dataclasses import dataclass
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any, Dict, List, Optional
from urllib.parse import urlparse

import boto3
from botocore.client import Config
from sqlalchemy import text
from sqlalchemy.orm import Session

from app.core.config import settings


BACKUP_DIR = Path(os.getenv("BACKUP_DIR", "/app/backups"))
BACKUP_RETENTION_DAYS = int(os.getenv("BACKUP_RETENTION_DAYS", "15"))
MAX_BACKUP_LIST = int(os.getenv("MAX_BACKUP_LIST", "50"))
BACKUP_WARNING_HOURS = int(os.getenv("BACKUP_WARNING_HOURS", "24"))
BACKUP_ERROR_HOURS = int(os.getenv("BACKUP_ERROR_HOURS", "168"))


@dataclass
class BackupResult:
    filename: str
    path: str
    size_bytes: int
    created_at: str
    included: List[str]
    warnings: List[str]


def _now_stamp() -> str:
    return datetime.now().strftime("%Y%m%d_%H%M%S")


def _utc_iso() -> str:
    return datetime.utcnow().isoformat(timespec="seconds") + "Z"


def _ensure_backup_dir() -> Path:
    BACKUP_DIR.mkdir(parents=True, exist_ok=True)
    return BACKUP_DIR


def _parse_database_url(database_url: str) -> Dict[str, str]:
    # SQLAlchemy URL used by the project: postgresql+psycopg://user:pass@host:5432/db
    normalized = database_url.replace("postgresql+psycopg://", "postgresql://")
    parsed = urlparse(normalized)
    return {
        "host": parsed.hostname or "postgres",
        "port": str(parsed.port or 5432),
        "user": parsed.username or "webmonitor",
        "password": parsed.password or "",
        "database": (parsed.path or "/webmonitor").lstrip("/"),
    }


def _run_pg_dump(output_file: Path) -> Optional[str]:
    if not shutil.which("pg_dump"):
        return "pg_dump não encontrado no container backend. Rebuild o backend com o Dockerfile V38."

    db = _parse_database_url(settings.DATABASE_URL)
    env = os.environ.copy()
    if db["password"]:
        env["PGPASSWORD"] = db["password"]

    cmd = [
        "pg_dump",
        "-h",
        db["host"],
        "-p",
        db["port"],
        "-U",
        db["user"],
        "-d",
        db["database"],
        "--format=custom",
        "--no-owner",
        "--no-privileges",
        "-f",
        str(output_file),
    ]
    try:
        subprocess.run(cmd, env=env, check=True, capture_output=True, text=True, timeout=240)
        return None
    except subprocess.TimeoutExpired:
        return "pg_dump excedeu o tempo limite de 240s."
    except subprocess.CalledProcessError as exc:
        detail = (exc.stderr or exc.stdout or str(exc)).strip()
        return f"Falha no pg_dump: {detail[:1200]}"


def _minio_client():
    return boto3.client(
        "s3",
        endpoint_url=f"http://{settings.MINIO_ENDPOINT}",
        aws_access_key_id=settings.MINIO_ACCESS_KEY,
        aws_secret_access_key=settings.MINIO_SECRET_KEY,
        config=Config(signature_version="s3v4"),
        region_name="us-east-1",
    )


def _add_minio_objects_to_zip(zipf: zipfile.ZipFile, prefix: str = "minio_evidence", max_objects: int = 5000) -> Dict[str, Any]:
    added = 0
    total_bytes = 0
    warnings: List[str] = []
    try:
        client = _minio_client()
        paginator = client.get_paginator("list_objects_v2")
        for page in paginator.paginate(Bucket=settings.MINIO_BUCKET):
            for obj in page.get("Contents", []):
                if added >= max_objects:
                    warnings.append(f"Backup MinIO limitado a {max_objects} objetos nesta execução.")
                    return {"objects": added, "bytes": total_bytes, "warnings": warnings}
                key = obj.get("Key")
                if not key:
                    continue
                body = client.get_object(Bucket=settings.MINIO_BUCKET, Key=key)["Body"].read()
                zipf.writestr(f"{prefix}/{key}", body)
                added += 1
                total_bytes += len(body)
        return {"objects": added, "bytes": total_bytes, "warnings": warnings}
    except Exception as exc:  # noqa: BLE001
        warnings.append(f"Falha ao incluir evidências MinIO: {exc}")
        return {"objects": added, "bytes": total_bytes, "warnings": warnings}


def _write_manifest(zipf: zipfile.ZipFile, manifest: Dict[str, Any]) -> None:
    zipf.writestr("manifest.json", json.dumps(manifest, ensure_ascii=False, indent=2))


def create_backup(
    *,
    include_database: bool = True,
    include_minio: bool = False,
    include_manifest: bool = True,
    minio_max_objects: int = 5000,
    label: Optional[str] = None,
) -> BackupResult:
    backup_dir = _ensure_backup_dir()
    stamp = _now_stamp()
    safe_label = ""
    if label:
        safe_label = "_" + "".join(ch for ch in label if ch.isalnum() or ch in "-_")[:40]
    filename = f"tvfiscal_backup_{stamp}{safe_label}.zip"
    zip_path = backup_dir / filename
    included: List[str] = []
    warnings: List[str] = []

    with tempfile.TemporaryDirectory() as tmp:
        tmpdir = Path(tmp)
        manifest: Dict[str, Any] = {
            "app": "TV Fiscal WebMonitor",
            "created_at": _utc_iso(),
            "label": label,
            "database_included": include_database,
            "minio_included": include_minio,
            "minio_bucket": settings.MINIO_BUCKET,
            "backup_version": "V40",
        }

        db_dump_path = tmpdir / "postgres_webmonitor.dump"
        if include_database:
            err = _run_pg_dump(db_dump_path)
            if err:
                warnings.append(err)
            elif db_dump_path.exists():
                included.append("postgresql")

        with zipfile.ZipFile(zip_path, "w", compression=zipfile.ZIP_DEFLATED, compresslevel=6) as zipf:
            if include_database and db_dump_path.exists():
                zipf.write(db_dump_path, "postgres/postgres_webmonitor.dump")
            if include_minio:
                minio_stats = _add_minio_objects_to_zip(zipf, max_objects=minio_max_objects)
                manifest["minio_stats"] = minio_stats
                warnings.extend(minio_stats.get("warnings", []))
                if minio_stats.get("objects", 0) > 0:
                    included.append("minio_evidence")
            if include_manifest:
                manifest["included"] = included
                manifest["warnings"] = warnings
                _write_manifest(zipf, manifest)
                included.append("manifest")

    return BackupResult(
        filename=filename,
        path=str(zip_path),
        size_bytes=zip_path.stat().st_size if zip_path.exists() else 0,
        created_at=datetime.now().isoformat(timespec="seconds"),
        included=included,
        warnings=warnings,
    )


def list_backups() -> Dict[str, Any]:
    backup_dir = _ensure_backup_dir()
    items = []
    for path in sorted(backup_dir.glob("*.zip"), key=lambda p: p.stat().st_mtime, reverse=True)[:MAX_BACKUP_LIST]:
        items.append(
            {
                "filename": path.name,
                "size_bytes": path.stat().st_size,
                "created_at": datetime.fromtimestamp(path.stat().st_mtime).isoformat(timespec="seconds"),
                "path": str(path),
            }
        )
    return {"backup_dir": str(backup_dir), "items": items, "retention_days": BACKUP_RETENTION_DAYS}




def get_latest_backup_age_hours() -> Optional[float]:
    backups = list_backups().get("items") or []
    if not backups:
        return None
    latest = backups[0]
    created_at = latest.get("created_at")
    try:
        created = datetime.fromisoformat(str(created_at).replace("Z", "+00:00")).replace(tzinfo=None)
    except Exception:
        path = Path(latest.get("path") or "")
        if path.exists():
            created = datetime.fromtimestamp(path.stat().st_mtime)
        else:
            return None
    return round((datetime.now() - created).total_seconds() / 3600, 2)


def backup_freshness() -> Dict[str, Any]:
    backups = list_backups().get("items") or []
    age_hours = get_latest_backup_age_hours()
    if age_hours is None:
        status = "warning"
        message = "Nenhum backup encontrado. Gere um backup em /admin/maintenance."
    elif age_hours >= BACKUP_ERROR_HOURS:
        status = "error"
        message = f"Último backup tem {age_hours:.1f}h, acima do limite crítico de {BACKUP_ERROR_HOURS}h."
    elif age_hours >= BACKUP_WARNING_HOURS:
        status = "warning"
        message = f"Último backup tem {age_hours:.1f}h, acima do alvo operacional de {BACKUP_WARNING_HOURS}h."
    else:
        status = "ok"
        message = f"Backup recente encontrado há {age_hours:.1f}h."
    return {
        "status": status,
        "message": message,
        "age_hours": age_hours,
        "warning_hours": BACKUP_WARNING_HOURS,
        "error_hours": BACKUP_ERROR_HOURS,
        "latest_backup": backups[0] if backups else None,
        "backup_count": len(backups),
    }

def get_backup_path(filename: str) -> Path:
    backup_dir = _ensure_backup_dir().resolve()
    candidate = (backup_dir / filename).resolve()
    if backup_dir not in candidate.parents and candidate != backup_dir:
        raise ValueError("Nome de arquivo inválido.")
    if not candidate.exists() or candidate.suffix != ".zip":
        raise FileNotFoundError("Backup não encontrado.")
    return candidate


def delete_backup(filename: str) -> bool:
    path = get_backup_path(filename)
    path.unlink()
    return True


def cleanup_old_backups(retention_days: int = BACKUP_RETENTION_DAYS) -> Dict[str, Any]:
    backup_dir = _ensure_backup_dir()
    cutoff = datetime.now() - timedelta(days=retention_days)
    deleted = []
    for path in backup_dir.glob("*.zip"):
        modified = datetime.fromtimestamp(path.stat().st_mtime)
        if modified < cutoff:
            deleted.append({"filename": path.name, "size_bytes": path.stat().st_size})
            path.unlink()
    return {"deleted": deleted, "deleted_count": len(deleted), "retention_days": retention_days}


def _table_exists(db: Session, table_name: str) -> bool:
    result = db.execute(
        text("select exists (select 1 from information_schema.tables where table_schema='public' and table_name=:table)"),
        {"table": table_name},
    ).scalar()
    return bool(result)


def cleanup_database_logs(
    db: Session,
    *,
    days: int = 90,
    dry_run: bool = True,
    cleanup_dry_run_notifications: bool = True,
    cleanup_resolved_notifications: bool = False,
    cleanup_automation_runs: bool = True,
) -> Dict[str, Any]:
    cutoff = datetime.utcnow() - timedelta(days=days)
    results: Dict[str, Any] = {"dry_run": dry_run, "days": days, "cutoff": cutoff.isoformat(timespec="seconds") + "Z", "tables": []}

    cleanup_specs = []
    if cleanup_dry_run_notifications and _table_exists(db, "notification_logs"):
        cleanup_specs.append(
            {
                "table": "notification_logs",
                "where": "created_at < :cutoff and status in ('dry_run','skipped')",
                "label": "notificações simuladas/ignoradas antigas",
            }
        )
    if cleanup_resolved_notifications and _table_exists(db, "notification_logs"):
        cleanup_specs.append(
            {
                "table": "notification_logs",
                "where": "created_at < :cutoff and alert_status in ('resolvido','resolved')",
                "label": "alertas resolvidos antigos",
            }
        )
    if cleanup_automation_runs and _table_exists(db, "notification_automation_runs"):
        cleanup_specs.append(
            {
                "table": "notification_automation_runs",
                "where": "created_at < :cutoff",
                "label": "execuções antigas de automação",
            }
        )

    for spec in cleanup_specs:
        count = db.execute(text(f"select count(*) from {spec['table']} where {spec['where']}"), {"cutoff": cutoff}).scalar() or 0
        deleted = 0
        if not dry_run and count:
            deleted = db.execute(text(f"delete from {spec['table']} where {spec['where']}"), {"cutoff": cutoff}).rowcount or 0
        results["tables"].append({"table": spec["table"], "label": spec["label"], "matched": int(count), "deleted": int(deleted)})

    if not dry_run:
        db.commit()
    return results




def archive_notification_errors(
    db: Session,
    *,
    hours: int = 24,
    dry_run: bool = True,
    archived_by: str = "admin",
    reason: str = "Saneamento operacional V40",
) -> Dict[str, Any]:
    if not _table_exists(db, "notification_logs"):
        return {"dry_run": dry_run, "matched": 0, "archived": 0, "message": "Tabela notification_logs não existe."}
    cutoff = datetime.utcnow() - timedelta(hours=max(1, int(hours or 24)))
    params = {"cutoff": cutoff, "archived_by": archived_by, "reason": reason}
    where_sql = "status IN ('error','erro') AND created_at < :cutoff AND archived_at IS NULL"
    matched = int(db.execute(text(f"SELECT COUNT(*) FROM notification_logs WHERE {where_sql}"), params).scalar() or 0)
    archived = 0
    if not dry_run and matched:
        archived = int(
            db.execute(
                text(f"UPDATE notification_logs SET archived_at = NOW(), archived_by = :archived_by, archive_reason = :reason WHERE {where_sql}"),
                params,
            ).rowcount or 0
        )
        db.commit()
    return {
        "dry_run": dry_run,
        "hours": hours,
        "cutoff": cutoff.isoformat(timespec="seconds") + "Z",
        "matched": matched,
        "archived": archived,
        "reason": reason,
    }



def archive_homologation_notification_errors(
    db: Session,
    *,
    hours: int = 24,
    dry_run: bool = True,
    archived_by: str = "admin",
    reason: str = "Arquivamento de erros de homologação V40.1",
) -> Dict[str, Any]:
    """Arquiva imediatamente erros recentes de teste/homologação.

    Diferente de archive_notification_errors(), que só arquiva erros antigos,
    esta rotina foca em erros recentes e claramente operacionais de teste:
    - título de teste;
    - resposta de teste real SMTP/SMS/WhatsApp;
    - erros de credencial/campo obrigatório durante homologação;
    - timeouts/conexões fechadas gerados em testes manuais.

    Ela não apaga nada; apenas marca archived_at para limpar o healthcheck sem
    perder rastreabilidade.
    """
    if not _table_exists(db, "notification_logs"):
        return {"dry_run": dry_run, "matched": 0, "archived": 0, "message": "Tabela notification_logs não existe."}

    cutoff = datetime.utcnow() - timedelta(hours=max(1, int(hours or 24)))
    params = {
        "cutoff": cutoff,
        "archived_by": archived_by,
        "reason": reason,
    }
    where_sql = """
        status IN ('error','erro')
        AND created_at >= :cutoff
        AND archived_at IS NULL
        AND (
            lower(coalesce(title,'')) LIKE '%teste%'
            OR lower(coalesce(message,'')) LIKE '%teste%'
            OR lower(coalesce(provider_response,'')) LIKE '%teste%'
            OR lower(coalesce(provider_response,'')) LIKE '%smtp%'
            OR lower(coalesce(provider_response,'')) LIKE '%timed out%'
            OR lower(coalesce(provider_response,'')) LIKE '%timeout%'
            OR lower(coalesce(provider_response,'')) LIKE '%connection unexpectedly closed%'
            OR lower(coalesce(provider_response,'')) LIKE '%informe smtp_host%'
            OR lower(coalesce(provider_response,'')) LIKE '%token%'
            OR lower(coalesce(provider_response,'')) LIKE '%credencial%'
            OR lower(coalesce(provider_response,'')) LIKE '%dry_run%'
        )
    """
    matched = int(db.execute(text(f"SELECT COUNT(*) FROM notification_logs WHERE {where_sql}"), params).scalar() or 0)

    sample_rows = db.execute(
        text(f"""
            SELECT id, created_at, channel, title, provider_response
            FROM notification_logs
            WHERE {where_sql}
            ORDER BY created_at DESC
            LIMIT 20
        """),
        params,
    ).fetchall()
    sample = [
        {
            "id": str(row[0]),
            "created_at": row[1].isoformat(timespec="seconds") if hasattr(row[1], "isoformat") else str(row[1]),
            "channel": row[2],
            "title": row[3],
            "provider_response": row[4],
        }
        for row in sample_rows
    ]

    archived = 0
    if not dry_run and matched:
        archived = int(
            db.execute(
                text(f"""
                    UPDATE notification_logs
                    SET archived_at = NOW(), archived_by = :archived_by, archive_reason = :reason
                    WHERE {where_sql}
                """),
                params,
            ).rowcount or 0
        )
        db.commit()

    return {
        "dry_run": dry_run,
        "hours": hours,
        "cutoff": cutoff.isoformat(timespec="seconds") + "Z",
        "matched": matched,
        "archived": archived,
        "reason": reason,
        "criteria": "erros recentes de teste/homologação por título, mensagem ou resposta do provedor",
        "sample": sample,
    }


def notification_error_summary(db: Session) -> Dict[str, Any]:
    if not _table_exists(db, "notification_logs"):
        return {"active_errors_24h": 0, "archived_errors_24h": 0}
    active = int(db.execute(text("""
        SELECT COUNT(*) FROM notification_logs
        WHERE status IN ('error','erro')
          AND created_at >= NOW() - INTERVAL '24 hours'
          AND archived_at IS NULL
    """)).scalar() or 0)
    archived = int(db.execute(text("""
        SELECT COUNT(*) FROM notification_logs
        WHERE status IN ('error','erro')
          AND created_at >= NOW() - INTERVAL '24 hours'
          AND archived_at IS NOT NULL
    """)).scalar() or 0)
    return {"active_errors_24h": active, "archived_errors_24h": archived}

def maintenance_status(db: Session) -> Dict[str, Any]:
    backup_dir = _ensure_backup_dir()
    backups = list_backups()["items"]
    disk = shutil.disk_usage(str(backup_dir))
    table_counts: Dict[str, int] = {}
    for table in ["projects", "items", "banner_items", "notification_logs", "notification_automation_runs"]:
        if _table_exists(db, table):
            try:
                table_counts[table] = int(db.execute(text(f"select count(*) from {table}")).scalar() or 0)
            except Exception:  # noqa: BLE001
                table_counts[table] = -1
    freshness = backup_freshness()
    return {
        "generated_at": datetime.now().isoformat(timespec="seconds"),
        "backup_dir": str(backup_dir),
        "backup_count": len(backups),
        "latest_backup": backups[0] if backups else None,
        "backup_freshness": freshness,
        "retention_days": BACKUP_RETENTION_DAYS,
        "backup_warning_hours": BACKUP_WARNING_HOURS,
        "backup_error_hours": BACKUP_ERROR_HOURS,
        "auto_backup": {
            "enabled": os.getenv("AUTO_BACKUP_ENABLED", "false").strip().lower() in {"1", "true", "yes", "sim", "on"},
            "interval_hours": int(os.getenv("AUTO_BACKUP_INTERVAL_HOURS", "24")),
            "include_minio": os.getenv("AUTO_BACKUP_INCLUDE_MINIO", "false").strip().lower() in {"1", "true", "yes", "sim", "on"},
        },
        "pg_dump_available": bool(shutil.which("pg_dump")),
        "minio_bucket": settings.MINIO_BUCKET,
        "disk": {"total": disk.total, "used": disk.used, "free": disk.free},
        "table_counts": table_counts,
        "notification_errors": notification_error_summary(db),
    }


def generate_security_export(db: Session) -> str:
    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow(["metric", "value"])
    status = maintenance_status(db)
    writer.writerow(["generated_at", status["generated_at"]])
    writer.writerow(["backup_count", status["backup_count"]])
    writer.writerow(["latest_backup", json.dumps(status.get("latest_backup"), ensure_ascii=False)])
    writer.writerow(["backup_freshness", json.dumps(status.get("backup_freshness"), ensure_ascii=False)])
    writer.writerow(["auto_backup", json.dumps(status.get("auto_backup"), ensure_ascii=False)])
    writer.writerow(["notification_errors", json.dumps(status.get("notification_errors"), ensure_ascii=False)])
    writer.writerow(["pg_dump_available", status["pg_dump_available"]])
    writer.writerow(["backup_dir", status["backup_dir"]])
    for table, count in status.get("table_counts", {}).items():
        writer.writerow([f"table_{table}", count])
    return output.getvalue()
