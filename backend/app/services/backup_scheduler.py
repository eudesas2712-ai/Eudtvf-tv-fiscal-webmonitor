from __future__ import annotations

import os
import threading
import time
from datetime import datetime, timedelta
from typing import Any, Dict, Optional

from app.services.maintenance_service import create_backup, get_latest_backup_age_hours, list_backups


def _bool_env(name: str, default: str = "false") -> bool:
    return os.getenv(name, default).strip().lower() in {"1", "true", "yes", "sim", "on"}


def _int_env(name: str, default: int) -> int:
    try:
        return int(os.getenv(name, str(default)))
    except Exception:
        return default


def auto_backup_status() -> Dict[str, Any]:
    age = get_latest_backup_age_hours()
    return {
        "enabled": _bool_env("AUTO_BACKUP_ENABLED", "false"),
        "interval_hours": _int_env("AUTO_BACKUP_INTERVAL_HOURS", 24),
        "check_every_minutes": _int_env("AUTO_BACKUP_CHECK_EVERY_MINUTES", 60),
        "include_minio": _bool_env("AUTO_BACKUP_INCLUDE_MINIO", "false"),
        "minio_max_objects": _int_env("AUTO_BACKUP_MINIO_MAX_OBJECTS", 5000),
        "backup_dir": os.getenv("BACKUP_DIR", "/app/backups"),
        "latest_backup_age_hours": age,
        "latest_backup": (list_backups().get("items") or [None])[0],
    }


def run_auto_backup_once(label: str = "auto") -> Dict[str, Any]:
    include_minio = _bool_env("AUTO_BACKUP_INCLUDE_MINIO", "false")
    max_objects = _int_env("AUTO_BACKUP_MINIO_MAX_OBJECTS", 5000)
    result = create_backup(
        include_database=True,
        include_minio=include_minio,
        include_manifest=True,
        minio_max_objects=max_objects,
        label=label,
    )
    return {
        "created": True,
        "filename": result.filename,
        "size_bytes": result.size_bytes,
        "included": result.included,
        "warnings": result.warnings,
    }


def _worker(stop_event: threading.Event) -> None:
    # Aguarda alguns segundos para não competir com o bootstrap inicial.
    time.sleep(8)
    while not stop_event.is_set():
        try:
            status = auto_backup_status()
            if status.get("enabled"):
                interval_hours = int(status.get("interval_hours") or 24)
                age = status.get("latest_backup_age_hours")
                if age is None or float(age) >= interval_hours:
                    run_auto_backup_once(label="auto")
        except Exception as exc:  # noqa: BLE001
            print(f"[auto-backup] falha na rotina automática: {exc}")
        wait_seconds = max(60, _int_env("AUTO_BACKUP_CHECK_EVERY_MINUTES", 60) * 60)
        stop_event.wait(wait_seconds)


def start_auto_backup_scheduler() -> Optional[threading.Event]:
    if not _bool_env("AUTO_BACKUP_ENABLED", "false"):
        print("[auto-backup] desativado. Configure AUTO_BACKUP_ENABLED=true para ativar backup automático.")
        return None
    stop_event = threading.Event()
    thread = threading.Thread(target=_worker, args=(stop_event,), name="tvfiscal-auto-backup", daemon=True)
    thread.start()
    print("[auto-backup] rotina automática iniciada")
    return stop_event
