from __future__ import annotations

import os
import re
import smtplib
import uuid
from dataclasses import dataclass
from datetime import datetime, timedelta
from email.message import EmailMessage
from typing import Any

from sqlalchemy.orm import Session

from app.db.models import BannerItem, Item, NotificationAutomationRun, NotificationContact, NotificationLog, NotificationProviderSetting, NotificationRule
from app.services.alerts_service import build_executive_alerts
from app.utils.timeutils import app_timezone_name, display_local, iso_local, utc_now

SEVERITY_ORDER = {"informativo": 1, "medio": 2, "alto": 3, "critico": 4}

SLA_MINUTES_BY_SEVERITY = {"informativo": 1440, "medio": 480, "alto": 120, "critico": 30}
SLA_SOON_MINUTES = 30


def _sla_minutes_for(severity: str | None) -> int:
    return SLA_MINUTES_BY_SEVERITY.get((severity or "informativo").lower(), 1440)


def _sla_status(row: NotificationLog | None) -> str:
    if not row:
        return "sem_sla"
    alert_status = getattr(row, "alert_status", None) or "aberto"
    if alert_status == "resolvido":
        return "resolvido"
    if alert_status == "adiado":
        return "adiado"
    due_at = getattr(row, "sla_due_at", None)
    if not due_at:
        return "sem_sla"
    now = _now()
    if due_at <= now:
        return "vencido"
    if due_at <= now + timedelta(minutes=SLA_SOON_MINUTES):
        return "vence_em_breve"
    return "no_prazo"


def _sla_remaining_minutes(row: NotificationLog | None) -> int | None:
    due_at = getattr(row, "sla_due_at", None) if row else None
    if not due_at:
        return None
    return int((due_at - _now()).total_seconds() // 60)


def _bool_env(name: str, default: str = "false") -> bool:
    return os.getenv(name, default).lower() in {"1", "true", "yes", "sim", "on"}


def _mask_secret(value: str | None) -> str | None:
    if not value:
        return None
    text = str(value)
    if len(text) <= 6:
        return "***"
    return f"{text[:3]}***{text[-3:]}"


def _compact_message(text: str, limit: int = 155) -> str:
    text = re.sub(r"\s+", " ", str(text or "")).strip()
    return text if len(text) <= limit else text[: limit - 1].rstrip() + "…"


def _uuid(value: str | uuid.UUID | None) -> uuid.UUID | None:
    if not value:
        return None
    if isinstance(value, uuid.UUID):
        return value
    return uuid.UUID(str(value))


def _now() -> datetime:
    return utc_now()


def _as_list(value: Any) -> list:
    if value is None:
        return []
    if isinstance(value, list):
        return value
    if isinstance(value, tuple):
        return list(value)
    if isinstance(value, dict):
        if "items" in value and isinstance(value["items"], list):
            return value["items"]
        if "terms" in value and isinstance(value["terms"], list):
            return value["terms"]
        return list(value.values())
    if isinstance(value, str):
        return [v.strip() for v in re.split(r"[,;\n]", value) if v.strip()]
    return [value]


def _clean_phone(value: str | None) -> str | None:
    if not value:
        return None
    digits = re.sub(r"\D+", "", str(value))
    return digits or None


def _norm(value: Any) -> str:
    import unicodedata

    text = str(value or "").lower().strip()
    text = "".join(ch for ch in unicodedata.normalize("NFKD", text) if not unicodedata.combining(ch))
    text = re.sub(r"\s+", " ", text)
    return text


def _contains_term(haystack: str, term: str) -> bool:
    h = _norm(haystack)
    t = _norm(term)
    if not t:
        return False
    # palavra/frase completa para evitar falsos positivos como Amil dentro de família
    pattern = rf"(?<![a-z0-9]){re.escape(t)}(?![a-z0-9])"
    return bool(re.search(pattern, h))


def _severity_ok(event_severity: str, minimum: str) -> bool:
    return SEVERITY_ORDER.get(event_severity or "informativo", 1) >= SEVERITY_ORDER.get(minimum or "informativo", 1)


def serialize_contact(row: NotificationContact) -> dict:
    return {
        "id": str(row.id),
        "project_id": str(row.project_id),
        "name": row.name,
        "role": row.role,
        "email": row.email,
        "phone": row.phone,
        "whatsapp": row.whatsapp,
        "channels": _as_list(row.channels),
        "priority": row.priority,
        "active": bool(row.active),
        "created_at": iso_local(row.created_at),
        "created_at_display": display_local(row.created_at),
        "updated_at": iso_local(row.updated_at),
        "updated_at_display": display_local(row.updated_at),
    }


def serialize_rule(row: NotificationRule) -> dict:
    return {
        "id": str(row.id),
        "project_id": str(row.project_id),
        "name": row.name,
        "active": bool(row.active),
        "event_type": row.event_type,
        "terms": _as_list(row.terms),
        "categories": _as_list(row.categories),
        "channels": _as_list(row.channels),
        "contact_ids": [str(x) for x in _as_list(row.contact_ids)],
        "severity_min": row.severity_min,
        "sentiment_filter": row.sentiment_filter,
        "cooldown_minutes": row.cooldown_minutes,
        "last_triggered_at": row.last_triggered_at.isoformat() if row.last_triggered_at else None,
        "created_at": iso_local(row.created_at),
        "created_at_display": display_local(row.created_at),
        "updated_at": iso_local(row.updated_at),
        "updated_at_display": display_local(row.updated_at),
    }


def serialize_log(row: NotificationLog) -> dict:
    return {
        "id": str(row.id),
        "project_id": str(row.project_id),
        "rule_id": str(row.rule_id) if row.rule_id else None,
        "contact_id": str(row.contact_id) if row.contact_id else None,
        "event_type": row.event_type,
        "severity": row.severity,
        "category": row.category,
        "channel": row.channel,
        "status": row.status,
        "provider": row.provider,
        "title": row.title,
        "message": row.message,
        "target_url": row.target_url,
        "provider_response": row.provider_response,
        "alert_status": getattr(row, "alert_status", None) or "aberto",
        "acknowledged_at": iso_local(getattr(row, "acknowledged_at", None)) if getattr(row, "acknowledged_at", None) else None,
        "acknowledged_at_display": display_local(getattr(row, "acknowledged_at", None)) if getattr(row, "acknowledged_at", None) else None,
        "acknowledged_by": getattr(row, "acknowledged_by", None),
        "resolved_at": iso_local(getattr(row, "resolved_at", None)) if getattr(row, "resolved_at", None) else None,
        "resolved_at_display": display_local(getattr(row, "resolved_at", None)) if getattr(row, "resolved_at", None) else None,
        "resolved_by": getattr(row, "resolved_by", None),
        "resolution_note": getattr(row, "resolution_note", None),
        "snoozed_until": iso_local(getattr(row, "snoozed_until", None)) if getattr(row, "snoozed_until", None) else None,
        "snoozed_until_display": display_local(getattr(row, "snoozed_until", None)) if getattr(row, "snoozed_until", None) else None,
        "assigned_to": getattr(row, "assigned_to", None),
        "sla_minutes": getattr(row, "sla_minutes", None),
        "sla_due_at": iso_local(getattr(row, "sla_due_at", None)) if getattr(row, "sla_due_at", None) else None,
        "sla_due_at_display": display_local(getattr(row, "sla_due_at", None)) if getattr(row, "sla_due_at", None) else None,
        "sla_status": _sla_status(row),
        "sla_remaining_minutes": _sla_remaining_minutes(row),
        "escalation_level": getattr(row, "escalation_level", 0) or 0,
        "escalation_count": getattr(row, "escalation_count", 0) or 0,
        "escalated_at": iso_local(getattr(row, "escalated_at", None)) if getattr(row, "escalated_at", None) else None,
        "escalated_at_display": display_local(getattr(row, "escalated_at", None)) if getattr(row, "escalated_at", None) else None,
        "last_escalation_note": getattr(row, "last_escalation_note", None),
        "created_at": iso_local(row.created_at),
        "created_at_display": display_local(row.created_at),
    }


def serialize_automation_run(row: NotificationAutomationRun) -> dict:
    return {
        "id": str(row.id),
        "project_id": str(row.project_id),
        "trigger_source": row.trigger_source,
        "status": row.status,
        "rules_count": row.rules_count or 0,
        "events_count": row.events_count or 0,
        "notifications_count": row.notifications_count or 0,
        "sent_count": row.sent_count or 0,
        "registered_count": row.registered_count or 0,
        "dry_run_count": row.dry_run_count or 0,
        "error_count": row.error_count or 0,
        "skipped_duplicates": row.skipped_duplicates or 0,
        "message": row.message,
        "created_at": iso_local(row.created_at),
        "created_at_display": display_local(row.created_at),
    }


def _provider_readiness() -> dict:
    sms_provider = os.getenv("SMS_PROVIDER", "webhook").lower()
    sms_requirements = {
        "twilio": ["TWILIO_ACCOUNT_SID", "TWILIO_AUTH_TOKEN", "TWILIO_FROM_NUMBER"],
        "zenvia": ["ZENVIA_API_TOKEN", "ZENVIA_FROM"],
        "totalvoice": ["TOTALVOICE_ACCESS_TOKEN"],
        "webhook": ["SMS_WEBHOOK_URL"],
    }
    whatsapp_provider = os.getenv("WHATSAPP_PROVIDER", "webhook").lower()
    whatsapp_requirements = {
        "webhook": ["WHATSAPP_WEBHOOK_URL"],
        "zenvia": ["ZENVIA_API_TOKEN", "ZENVIA_WHATSAPP_FROM"],
    }
    email_required = ["SMTP_HOST", "SMTP_FROM"]
    webhook_required = ["NOTIFICATION_WEBHOOK_URL"]

    def check(required: list[str]) -> dict:
        missing = [key for key in required if not os.getenv(key)]
        return {"ready": not missing, "missing": missing}

    return {
        "dry_run": _bool_env("NOTIFICATION_DRY_RUN", "true"),
        "sms": {
            "enabled": _bool_env("SMS_ENABLED"),
            "provider": sms_provider,
            **check(sms_requirements.get(sms_provider, ["SMS_WEBHOOK_URL"])),
        },
        "email": {
            "enabled": _bool_env("EMAIL_ALERTS_ENABLED"),
            "provider": "smtp",
            **check(email_required),
        },
        "whatsapp": {
            "enabled": _bool_env("WHATSAPP_ALERTS_ENABLED"),
            "provider": whatsapp_provider,
            **check(whatsapp_requirements.get(whatsapp_provider, ["WHATSAPP_WEBHOOK_URL"])),
        },
        "webhook": {
            "enabled": bool(os.getenv("NOTIFICATION_WEBHOOK_URL")),
            "provider": "generic",
            **check(webhook_required),
        },
    }


def notification_config() -> dict:
    readiness = _provider_readiness()
    return {
        "sms_enabled": _bool_env("SMS_ENABLED"),
        "sms_provider": os.getenv("SMS_PROVIDER", "webhook"),
        "email_enabled": _bool_env("EMAIL_ALERTS_ENABLED"),
        "whatsapp_enabled": _bool_env("WHATSAPP_ALERTS_ENABLED"),
        "webhook_enabled": bool(os.getenv("NOTIFICATION_WEBHOOK_URL")),
        "dry_run": _bool_env("NOTIFICATION_DRY_RUN", "true"),
        "timezone": app_timezone_name(),
        "server_time": iso_local(_now()),
        "server_time_display": display_local(_now()),
        "auto_after_editorial": _bool_env("NOTIFICATIONS_AUTO_EVALUATE_AFTER_EDITORIAL", "true"),
        "auto_after_scheduler": _bool_env("NOTIFICATIONS_AUTO_EVALUATE_AFTER_SCHEDULER", "true"),
        "auto_event_limit": int(os.getenv("NOTIFICATIONS_AUTO_EVENT_LIMIT", "120") or 120),
        "auto_event_window_minutes": int(os.getenv("NOTIFICATIONS_AUTO_EVENT_WINDOW_MINUTES", "180") or 180),
        "provider_status": readiness,
    }


def provider_status() -> dict:
    cfg = _provider_readiness()
    return {
        "dry_run": cfg["dry_run"],
        "timezone": app_timezone_name(),
        "server_time": iso_local(_now()),
        "server_time_display": display_local(_now()),
        "providers": cfg,
        "masked": {
            "sms_provider": os.getenv("SMS_PROVIDER", "webhook"),
            "twilio_sid": _mask_secret(os.getenv("TWILIO_ACCOUNT_SID")),
            "zenvia_token": _mask_secret(os.getenv("ZENVIA_API_TOKEN")),
            "smtp_host": os.getenv("SMTP_HOST"),
            "smtp_from": os.getenv("SMTP_FROM"),
            "webhook_url": _mask_secret(os.getenv("NOTIFICATION_WEBHOOK_URL")),
        },
    }


def _provider_setting_to_dict(row: NotificationProviderSetting | None, include_secret: bool = False) -> dict | None:
    if not row:
        return None
    cfg = dict(row.config or {})
    safe_cfg = dict(cfg)
    if not include_secret and "smtp_password" in safe_cfg:
        safe_cfg["smtp_password"] = "***" if safe_cfg.get("smtp_password") else ""
    return {
        "id": str(row.id),
        "project_id": str(row.project_id),
        "provider_type": row.provider_type,
        "provider_name": row.provider_name,
        "active": bool(row.active),
        "config": safe_cfg,
        "created_at": iso_local(row.created_at),
        "created_at_display": display_local(row.created_at),
        "updated_at": iso_local(row.updated_at),
        "updated_at_display": display_local(row.updated_at),
    }


def _get_provider_setting(db: Session | None, project_id: str | None, provider_type: str) -> NotificationProviderSetting | None:
    if not db or not project_id:
        return None
    try:
        return (
            db.query(NotificationProviderSetting)
            .filter(
                NotificationProviderSetting.project_id == _uuid(project_id),
                NotificationProviderSetting.provider_type == provider_type,
                NotificationProviderSetting.active.is_(True),
            )
            .order_by(NotificationProviderSetting.updated_at.desc())
            .first()
        )
    except Exception:
        return None


def get_provider_settings(db: Session, project_id: str) -> dict:
    email = _get_provider_setting(db, project_id, "email")
    return {
        "project_id": project_id,
        "email": _provider_setting_to_dict(email),
        "automatic_email_ready": bool(email and (email.config or {}).get("smtp_host") and (email.config or {}).get("smtp_from")),
        "message": "Configuração de e-mail automático por projeto.",
    }


def upsert_email_smtp_setting(db: Session, project_id: str, payload: dict) -> dict:
    host = str(payload.get("smtp_host") or "").strip()
    port = int(payload.get("smtp_port") or 587)
    user = str(payload.get("smtp_user") or "").strip()
    password = str(payload.get("smtp_password") or "")
    sender = str(payload.get("smtp_from") or user or "").strip()
    use_tls = bool(payload.get("smtp_use_tls", True))

    if not host or not sender:
        return {"ok": False, "message": "Informe SMTP Host e remetente para ativar e-mail automático."}

    existing = _get_provider_setting(db, project_id, "email")
    row = existing or NotificationProviderSetting(
        id=uuid.uuid4(),
        project_id=_uuid(project_id),
        provider_type="email",
        provider_name="smtp",
        active=True,
    )
    if not existing:
        db.add(row)
    cfg = dict(row.config or {})
    cfg.update({
        "smtp_host": host,
        "smtp_port": port,
        "smtp_user": user,
        "smtp_from": sender,
        "smtp_use_tls": use_tls,
    })
    # Se a senha vier em branco ou mascarada, preserva a senha anterior.
    if password and password != "***":
        cfg["smtp_password"] = password
    row.config = cfg
    row.provider_name = "smtp"
    row.active = bool(payload.get("active", True))
    row.updated_at = _now()
    db.commit()
    db.refresh(row)
    return {"ok": True, "message": "SMTP automático salvo para este projeto.", "email": _provider_setting_to_dict(row)}


def deactivate_email_smtp_setting(db: Session, project_id: str) -> dict:
    row = _get_provider_setting(db, project_id, "email")
    if not row:
        return {"ok": False, "message": "Nenhum SMTP automático ativo encontrado."}
    row.active = False
    row.updated_at = _now()
    db.commit()
    return {"ok": True, "message": "SMTP automático desativado para este projeto."}


def list_contacts(db: Session, project_id: str, active_only: bool = False) -> list[dict]:
    query = db.query(NotificationContact).filter(NotificationContact.project_id == _uuid(project_id))
    if active_only:
        query = query.filter(NotificationContact.active.is_(True))
    return [serialize_contact(row) for row in query.order_by(NotificationContact.name.asc()).all()]


def upsert_contact(db: Session, project_id: str, payload: dict, contact_id: str | None = None) -> dict:
    row = db.query(NotificationContact).filter(NotificationContact.id == _uuid(contact_id)).first() if contact_id else None
    if not row:
        row = NotificationContact(id=uuid.uuid4(), project_id=_uuid(project_id), name=str(payload.get("name") or "Contato"))
        db.add(row)
    row.name = str(payload.get("name") or row.name or "Contato")
    row.role = payload.get("role")
    row.email = payload.get("email") or None
    row.phone = _clean_phone(payload.get("phone"))
    row.whatsapp = _clean_phone(payload.get("whatsapp"))
    row.channels = _as_list(payload.get("channels") or row.channels or ["painel"])
    row.priority = payload.get("priority") or row.priority or "normal"
    if "active" in payload:
        row.active = bool(payload.get("active"))
    row.updated_at = _now()
    db.commit()
    db.refresh(row)
    return serialize_contact(row)


def deactivate_contact(db: Session, contact_id: str) -> dict:
    row = db.query(NotificationContact).filter(NotificationContact.id == _uuid(contact_id)).first()
    if not row:
        return {"ok": False, "message": "Contato não encontrado."}
    row.active = False
    row.updated_at = _now()
    db.commit()
    return {"ok": True, "id": str(row.id), "message": "Contato desativado."}


def list_rules(db: Session, project_id: str, active_only: bool = False) -> list[dict]:
    query = db.query(NotificationRule).filter(NotificationRule.project_id == _uuid(project_id))
    if active_only:
        query = query.filter(NotificationRule.active.is_(True))
    return [serialize_rule(row) for row in query.order_by(NotificationRule.created_at.desc()).all()]


def upsert_rule(db: Session, project_id: str, payload: dict, rule_id: str | None = None) -> dict:
    row = db.query(NotificationRule).filter(NotificationRule.id == _uuid(rule_id)).first() if rule_id else None
    if not row:
        row = NotificationRule(id=uuid.uuid4(), project_id=_uuid(project_id), name=str(payload.get("name") or "Nova regra"))
        db.add(row)
    row.name = str(payload.get("name") or row.name or "Nova regra")
    row.active = bool(payload.get("active", row.active if row.active is not None else True))
    row.event_type = payload.get("event_type") or row.event_type or "any"
    row.terms = _as_list(payload.get("terms") if "terms" in payload else row.terms)
    row.categories = _as_list(payload.get("categories") if "categories" in payload else row.categories)
    row.channels = _as_list(payload.get("channels") if "channels" in payload else row.channels or ["painel"])
    row.contact_ids = [str(x) for x in _as_list(payload.get("contact_ids") if "contact_ids" in payload else row.contact_ids)]
    row.severity_min = payload.get("severity_min") or row.severity_min or "alto"
    row.sentiment_filter = payload.get("sentiment_filter") or None
    try:
        row.cooldown_minutes = int(payload.get("cooldown_minutes", row.cooldown_minutes or 60))
    except (TypeError, ValueError):
        row.cooldown_minutes = 60
    row.updated_at = _now()
    db.commit()
    db.refresh(row)
    return serialize_rule(row)


def deactivate_rule(db: Session, rule_id: str) -> dict:
    row = db.query(NotificationRule).filter(NotificationRule.id == _uuid(rule_id)).first()
    if not row:
        return {"ok": False, "message": "Regra não encontrada."}
    row.active = False
    row.updated_at = _now()
    db.commit()
    return {"ok": True, "id": str(row.id), "message": "Regra desativada."}


def bootstrap_default_rules(db: Session, project_id: str) -> dict:
    project_uuid = _uuid(project_id)
    existing = db.query(NotificationRule).filter(NotificationRule.project_id == project_uuid).count()
    created = 0
    defaults = [
        {
            "name": "Menção editorial negativa ou crítica",
            "event_type": "editorial_negative",
            "severity_min": "alto",
            "categories": ["editorial"],
            "channels": ["painel", "sms", "email"],
            "cooldown_minutes": 120,
        },
        {
            "name": "Termo/marca monitorada em notícia",
            "event_type": "editorial_mention",
            "severity_min": "medio",
            "categories": ["editorial"],
            "channels": ["painel", "sms", "email"],
            "cooldown_minutes": 60,
        },
        {
            "name": "Alerta executivo crítico/alto",
            "event_type": "executive_alert",
            "severity_min": "alto",
            "channels": ["painel", "email"],
            "cooldown_minutes": 120,
        },
        {
            "name": "Publicidade auditável disponível",
            "event_type": "checking_auditable",
            "severity_min": "medio",
            "categories": ["checking"],
            "channels": ["painel", "email"],
            "cooldown_minutes": 180,
        },
    ]
    if existing == 0:
        for item in defaults:
            upsert_rule(db, project_id, item)
            created += 1
    return {"project_id": project_id, "created": created, "existing_before": existing, "rules": list_rules(db, project_id)}


@dataclass
class NotificationEvent:
    event_type: str
    severity: str
    category: str
    title: str
    message: str
    target_url: str | None = None
    terms: list[str] | None = None
    sentiment: str | None = None


def _build_events_from_alerts(db: Session, project_id: str, since: datetime | None = None) -> list[NotificationEvent]:
    payload = build_executive_alerts(db, project_id)
    events: list[NotificationEvent] = []
    for alert in payload.get("alerts") or []:
        events.append(NotificationEvent(
            event_type="executive_alert",
            severity=alert.get("severity") or "informativo",
            category=alert.get("category") or "geral",
            title=alert.get("title") or "Alerta TV Fiscal",
            message=alert.get("message") or "Alerta gerado pela Central de Alertas.",
            target_url=alert.get("route"),
            terms=[],
        ))
    return events


def _build_events_from_editorial(db: Session, project_id: str, limit: int = 80, since: datetime | None = None) -> list[NotificationEvent]:
    query = db.query(Item).filter(Item.project_id == _uuid(project_id))
    if since is not None:
        query = query.filter(Item.created_at >= since)
    rows = query.order_by(Item.created_at.desc()).limit(limit).all()
    events: list[NotificationEvent] = []
    for row in rows:
        matched_terms = []
        mt = getattr(row, "matched_terms", None)
        if isinstance(mt, dict):
            matched_terms = _as_list(mt.get("terms") or mt.get("matches") or [])
        elif mt:
            matched_terms = _as_list(mt)

        sentiment = (getattr(row, "sentiment", None) or "").lower()
        score = getattr(row, "sentiment_score", 0) or 0
        topic = getattr(row, "topic", None) or "Editorial"
        source = getattr(row, "source_name", None) or "Fonte não informada"
        title = getattr(row, "title", None) or "Matéria sem título"
        summary = getattr(row, "summary", None) or getattr(row, "content_text", "")[:250]
        sev = "critico" if score <= -70 else "alto" if score <= -40 else "medio" if matched_terms else "informativo"

        if sentiment == "negativo" or score <= -40:
            events.append(NotificationEvent(
                event_type="editorial_negative",
                severity=sev,
                category="editorial",
                title=title,
                message=f"Menção editorial negativa em {source}. Tema: {topic}. {summary[:280]}",
                target_url=getattr(row, "url", None),
                terms=matched_terms,
                sentiment=sentiment,
            ))
        if matched_terms:
            events.append(NotificationEvent(
                event_type="editorial_mention",
                severity=max([sev, "medio"], key=lambda x: SEVERITY_ORDER.get(x, 1)),
                category="editorial",
                title=title,
                message=f"Termo/marca monitorada detectada em {source}: {', '.join(matched_terms)}. Tema: {topic}.",
                target_url=getattr(row, "url", None),
                terms=matched_terms,
                sentiment=sentiment,
            ))
    return events


def _build_events_from_checking(db: Session, project_id: str, limit: int = 40, since: datetime | None = None) -> list[NotificationEvent]:
    query = db.query(BannerItem).filter(BannerItem.project_id == _uuid(project_id), BannerItem.checking_status == "auditavel")
    if since is not None:
        query = query.filter(BannerItem.created_at >= since)
    rows = query.order_by(BannerItem.created_at.desc()).limit(limit).all()
    events = []
    for row in rows:
        adv = getattr(row, "advertiser_name", None) or "Pendente de identificação"
        portal = getattr(row, "source_name", None) or "Portal não informado"
        events.append(NotificationEvent(
            event_type="checking_auditable",
            severity="medio",
            category="checking",
            title=f"Publicidade auditável detectada: {adv}",
            message=f"Peça auditável em {portal}, formato {getattr(row, 'normalized_width', None) or getattr(row, 'width', '')} x {getattr(row, 'normalized_height', None) or getattr(row, 'height', '')}. Evidência preservada disponível.",
            target_url=getattr(row, "screenshot_banner_url", None) or getattr(row, "evidence_html_url", None) or getattr(row, "image_url", None),
            terms=[adv],
        ))
    return events


def _rule_matches_event(rule: NotificationRule, event: NotificationEvent) -> bool:
    if not bool(rule.active):
        return False
    if rule.event_type and rule.event_type != "any" and rule.event_type != event.event_type:
        return False
    if not _severity_ok(event.severity, rule.severity_min or "informativo"):
        return False
    categories = [str(x) for x in _as_list(rule.categories)]
    if categories and event.category not in categories:
        return False
    if rule.sentiment_filter and event.sentiment and rule.sentiment_filter.lower() != event.sentiment.lower():
        return False
    terms = [str(x) for x in _as_list(rule.terms)]
    if terms:
        haystack = " ".join([event.title, event.message, " ".join(event.terms or [])])
        if not any(_contains_term(haystack, term) for term in terms):
            return False
    return True


def _resolve_contacts_for_rule(db: Session, project_id: str, rule: NotificationRule) -> list[NotificationContact]:
    ids = [str(x) for x in _as_list(rule.contact_ids) if str(x)]
    query = db.query(NotificationContact).filter(NotificationContact.project_id == _uuid(project_id), NotificationContact.active.is_(True))
    if ids:
        uuid_ids = [_uuid(x) for x in ids]
        query = query.filter(NotificationContact.id.in_(uuid_ids))
    return query.order_by(NotificationContact.name.asc()).all()


def _recent_duplicate_exists(db: Session, project_id: str, rule: NotificationRule, event: NotificationEvent) -> bool:
    cooldown = int(rule.cooldown_minutes or 0)
    if cooldown <= 0:
        return False
    since = _now() - timedelta(minutes=cooldown)
    target = event.target_url or event.title
    found = (
        db.query(NotificationLog)
        .filter(
            NotificationLog.project_id == _uuid(project_id),
            NotificationLog.rule_id == rule.id,
            NotificationLog.event_type == event.event_type,
            NotificationLog.target_url == target,
            NotificationLog.created_at >= since,
        )
        .first()
    )
    return bool(found)


def _build_channel_message(channel: str, event: NotificationEvent) -> str:
    link = f" Link: {event.target_url}" if event.target_url else ""
    severity = (event.severity or "informativo").upper()
    if channel == "sms":
        return _compact_message(f"TV Fiscal Alerta {severity}: {event.title}. {event.message}{link}", 320)
    if channel == "whatsapp":
        return _compact_message(f"*TV Fiscal Alerta*\nSeveridade: {severity}\n{event.title}\n{event.message}{link}", 900)
    return f"TV Fiscal Alerta\nSeveridade: {severity}\nTítulo: {event.title}\n\n{event.message}\n\nLink: {event.target_url or '-'}"


def _post_json(url: str, payload: dict, headers: dict | None = None, auth: tuple[str, str] | None = None) -> tuple[str, str]:
    import requests
    resp = requests.post(url, json=payload, headers=headers or {}, auth=auth, timeout=25)
    return ("sent" if resp.ok else "error", f"HTTP {resp.status_code}: {resp.text[:300]}")


def _send_sms_real(contact: NotificationContact, event: NotificationEvent) -> tuple[str, str, str]:
    if not contact.phone:
        return "skipped", "sms", "Contato sem telefone."
    provider = os.getenv("SMS_PROVIDER", "webhook").lower()
    message = _build_channel_message("sms", event)
    to = contact.phone

    if provider == "twilio":
        sid = os.getenv("TWILIO_ACCOUNT_SID")
        token = os.getenv("TWILIO_AUTH_TOKEN")
        from_number = os.getenv("TWILIO_FROM_NUMBER")
        if not (sid and token and from_number):
            return "error", "twilio", "TWILIO_ACCOUNT_SID, TWILIO_AUTH_TOKEN ou TWILIO_FROM_NUMBER ausente."
        import requests
        url = f"https://api.twilio.com/2010-04-01/Accounts/{sid}/Messages.json"
        resp = requests.post(url, data={"From": from_number, "To": to, "Body": message}, auth=(sid, token), timeout=25)
        return ("sent" if resp.ok else "error", "twilio", f"HTTP {resp.status_code}: {resp.text[:300]}")

    if provider == "zenvia":
        token = os.getenv("ZENVIA_API_TOKEN")
        sender = os.getenv("ZENVIA_FROM", "TVFiscal")
        if not token:
            return "error", "zenvia", "ZENVIA_API_TOKEN ausente."
        payload = {"from": sender, "to": to, "contents": [{"type": "text", "text": message}]}
        status, response = _post_json("https://api.zenvia.com/v2/channels/sms/messages", payload, headers={"X-API-TOKEN": token, "Content-Type": "application/json"})
        return status, "zenvia", response

    if provider == "totalvoice":
        token = os.getenv("TOTALVOICE_ACCESS_TOKEN")
        if not token:
            return "error", "totalvoice", "TOTALVOICE_ACCESS_TOKEN ausente."
        payload = {"numero_destino": to, "mensagem": message}
        status, response = _post_json("https://api.totalvoice.com.br/sms", payload, headers={"Access-Token": token, "Content-Type": "application/json"})
        return status, "totalvoice", response

    webhook = os.getenv("SMS_WEBHOOK_URL") or os.getenv("NOTIFICATION_WEBHOOK_URL")
    if webhook:
        status, response = _post_json(webhook, {"to": to, "message": message, "title": event.title, "channel": "sms", "event": event.__dict__})
        return status, "webhook", response
    return "skipped", provider, "Nenhum provedor SMS configurado."


def _send_whatsapp_real(contact: NotificationContact, event: NotificationEvent) -> tuple[str, str, str]:
    if not contact.whatsapp:
        return "skipped", "whatsapp", "Contato sem WhatsApp."
    provider = os.getenv("WHATSAPP_PROVIDER", "webhook").lower()
    message = _build_channel_message("whatsapp", event)
    to = contact.whatsapp
    if provider == "zenvia":
        token = os.getenv("ZENVIA_API_TOKEN")
        sender = os.getenv("ZENVIA_WHATSAPP_FROM")
        if not (token and sender):
            return "error", "zenvia_whatsapp", "ZENVIA_API_TOKEN ou ZENVIA_WHATSAPP_FROM ausente."
        payload = {"from": sender, "to": to, "contents": [{"type": "text", "text": message}]}
        status, response = _post_json("https://api.zenvia.com/v2/channels/whatsapp/messages", payload, headers={"X-API-TOKEN": token, "Content-Type": "application/json"})
        return status, "zenvia_whatsapp", response
    webhook = os.getenv("WHATSAPP_WEBHOOK_URL") or os.getenv("NOTIFICATION_WEBHOOK_URL")
    if webhook:
        status, response = _post_json(webhook, {"to": to, "message": message, "title": event.title, "channel": "whatsapp", "event": event.__dict__})
        return status, "webhook", response
    return "skipped", provider, "Nenhum provedor WhatsApp configurado."



def _send_email_with_config(contact: NotificationContact, event: NotificationEvent, cfg: dict, provider_name: str = "smtp") -> tuple[str, str, str]:
    if not contact.email:
        return "skipped", provider_name, "Contato sem e-mail."
    host = cfg.get("smtp_host")
    port = int(cfg.get("smtp_port") or 587)
    user = cfg.get("smtp_user")
    password = cfg.get("smtp_password")
    sender = cfg.get("smtp_from") or user or "alertas@tvfiscal.local"
    use_tls = bool(cfg.get("smtp_use_tls", True))
    if not host:
        return "error", provider_name, "SMTP_HOST não configurado."
    msg = EmailMessage()
    msg["Subject"] = f"TV Fiscal Alerta: {event.title[:80]}"
    msg["From"] = sender
    msg["To"] = contact.email
    msg.set_content(_build_channel_message("email", event))
    html = f"""
    <div style='font-family:Arial,sans-serif;color:#111827;line-height:1.55'>
      <div style='border-left:5px solid #b00020;padding-left:14px;margin-bottom:18px'>
        <h2 style='color:#0b1f3a;margin:0 0 6px'>TV Fiscal Alerta</h2>
        <p style='margin:0;color:#667085'>Motor de Notificações · WebMonitor</p>
      </div>
      <p><strong>Severidade:</strong> {(event.severity or 'informativo').upper()}</p>
      <h3>{event.title}</h3>
      <p>{event.message}</p>
      <p><a href='{event.target_url or '#'}'>Abrir evidência/painel</a></p>
    </div>
    """
    msg.add_alternative(html, subtype="html")
    with smtplib.SMTP(host, port, timeout=30) as smtp:
        if use_tls:
            smtp.starttls()
        if user and password:
            smtp.login(user, password)
        smtp.send_message(msg)
    return "sent", provider_name, f"E-mail enviado para {contact.email}."

def _send_channel(channel: str, contact: NotificationContact, event: NotificationEvent, db: Session | None = None, project_id: str | None = None) -> tuple[str, str, str]:
    """Envia ou simula um canal. Retorna status, provider, resposta."""
    cfg = notification_config()
    channel = (channel or "painel").lower()

    if channel in {"painel", "in_app", "interno"}:
        return "registered", "painel", "Alerta registrado no painel interno."

    saved_email = _get_provider_setting(db, project_id, "email") if channel == "email" and db and project_id else None
    if cfg["dry_run"] and not (channel == "email" and saved_email and saved_email.active):
        provider = cfg.get(f"{channel}_provider") or os.getenv(f"{channel.upper()}_PROVIDER", "dry_run")
        return "dry_run", provider, "Envio simulado por NOTIFICATION_DRY_RUN=true."

    try:
        if channel == "email":
            saved = _get_provider_setting(db, project_id, "email") if db and project_id else None
            if saved and saved.active:
                return _send_email_with_config(contact, event, dict(saved.config or {}), "smtp_projeto")
            if not cfg["email_enabled"]:
                return "skipped", "email", "EMAIL_ALERTS_ENABLED=false e nenhum SMTP de projeto ativo."
            return _send_email_with_config(contact, event, {
                "smtp_host": os.getenv("SMTP_HOST"),
                "smtp_port": int(os.getenv("SMTP_PORT", "587")),
                "smtp_user": os.getenv("SMTP_USER"),
                "smtp_password": os.getenv("SMTP_PASSWORD"),
                "smtp_from": os.getenv("SMTP_FROM") or os.getenv("SMTP_USER") or "alertas@tvfiscal.local",
                "smtp_use_tls": _bool_env("SMTP_USE_TLS", "true"),
            }, "smtp")

        if channel == "sms":
            if not cfg["sms_enabled"]:
                return "skipped", "sms", "SMS_ENABLED=false."
            return _send_sms_real(contact, event)

        if channel == "whatsapp":
            if not cfg["whatsapp_enabled"]:
                return "skipped", "whatsapp", "WHATSAPP_ALERTS_ENABLED=false."
            return _send_whatsapp_real(contact, event)

        if channel == "webhook":
            webhook = os.getenv("NOTIFICATION_WEBHOOK_URL")
            if not webhook:
                return "skipped", "webhook", "NOTIFICATION_WEBHOOK_URL não configurado."
            status, response = _post_json(webhook, {"contact": serialize_contact(contact), "event": event.__dict__})
            return status, "webhook", response
    except Exception as exc:
        return "error", channel, str(exc)

    return "skipped", channel, "Canal não suportado."

def _create_log(db: Session, project_id: str, rule: NotificationRule | None, contact: NotificationContact | None, channel: str, event: NotificationEvent, status: str, provider: str, response: str) -> NotificationLog:
    log = NotificationLog(
        id=uuid.uuid4(),
        project_id=_uuid(project_id),
        rule_id=rule.id if rule else None,
        contact_id=contact.id if contact else None,
        event_type=event.event_type,
        severity=event.severity,
        category=event.category,
        channel=channel,
        status=status,
        provider=provider,
        title=event.title[:500],
        message=event.message,
        target_url=event.target_url,
        provider_response=response,
        alert_status="aberto",
        sla_minutes=_sla_minutes_for(event.severity),
        sla_due_at=_now() + timedelta(minutes=_sla_minutes_for(event.severity)),
        escalation_level=0,
        escalation_count=0,
        created_at=_now(),
    )
    db.add(log)
    return log


def evaluate_notification_rules(db: Session, project_id: str, source: str = "manual", event_limit: int = 80, since: datetime | None = None) -> dict:
    rules = db.query(NotificationRule).filter(NotificationRule.project_id == _uuid(project_id), NotificationRule.active.is_(True)).all()
    if not rules:
        return {"project_id": project_id, "source": source, "rules": 0, "events": 0, "notifications": 0, "message": "Nenhuma regra ativa configurada."}

    events = []
    events.extend(_build_events_from_alerts(db, project_id, since=since))
    events.extend(_build_events_from_editorial(db, project_id, limit=event_limit, since=since))
    events.extend(_build_events_from_checking(db, project_id, limit=min(40, event_limit), since=since))

    created_logs = []
    skipped_duplicates = 0
    triggered_rules = set()
    for event in events[: event_limit * 3]:
        for rule in rules:
            if not _rule_matches_event(rule, event):
                continue
            if _recent_duplicate_exists(db, project_id, rule, event):
                skipped_duplicates += 1
                continue
            contacts = _resolve_contacts_for_rule(db, project_id, rule)
            if not contacts:
                # Ainda registra em painel para trilha, mesmo sem contato configurado.
                status, provider, response = "registered", "painel", "Regra acionada sem contatos ativos; alerta registrado no log."
                created_logs.append(_create_log(db, project_id, rule, None, "painel", event, status, provider, response))
            for contact in contacts:
                channels = _as_list(rule.channels or contact.channels or ["painel"])
                if not channels:
                    channels = ["painel"]
                for channel in channels:
                    status, provider, response = _send_channel(str(channel), contact, event, db=db, project_id=project_id)
                    created_logs.append(_create_log(db, project_id, rule, contact, str(channel), event, status, provider, response))
            rule.last_triggered_at = _now()
            rule.updated_at = _now()
            triggered_rules.add(str(rule.id))
    db.commit()
    return {
        "project_id": project_id,
        "source": source,
        "since": iso_local(since) if since else None,
        "rules": len(rules),
        "events": len(events),
        "triggered_rules": len(triggered_rules),
        "notifications": len(created_logs),
        "skipped_duplicates": skipped_duplicates,
        "config": notification_config(),
        "logs": [serialize_log(row) for row in created_logs[-20:]],
    }


def _status_counts(logs: list[dict]) -> dict:
    return {
        "sent": len([l for l in logs if l.get("status") == "sent"]),
        "registered": len([l for l in logs if l.get("status") == "registered"]),
        "dry_run": len([l for l in logs if l.get("status") == "dry_run"]),
        "error": len([l for l in logs if l.get("status") == "error"]),
    }


def list_automation_runs(db: Session, project_id: str, limit: int = 30) -> list[dict]:
    rows = (
        db.query(NotificationAutomationRun)
        .filter(NotificationAutomationRun.project_id == _uuid(project_id))
        .order_by(NotificationAutomationRun.created_at.desc())
        .limit(limit)
        .all()
    )
    return [serialize_automation_run(row) for row in rows]


def evaluate_automatic_notification_rules(
    db: Session,
    project_id: str,
    trigger_source: str,
    event_limit: int | None = None,
    window_minutes: int | None = None,
) -> dict:
    """Avalia regras após coleta automática e registra uma execução de automação.

    Diferente do botão manual, a automação usa uma janela curta de eventos recentes
    para evitar disparos massivos de clipping antigo quando o scheduler roda.
    O cooldown continua impedindo duplicidades por regra + URL/título.
    """
    cfg = notification_config()
    if event_limit is None:
        event_limit = int(cfg.get("auto_event_limit") or 120)
    if window_minutes is None:
        window_minutes = int(cfg.get("auto_event_window_minutes") or 180)

    since = _now() - timedelta(minutes=max(1, int(window_minutes)))
    status = "success"
    message = "Automação de notificações executada."
    try:
        result = evaluate_notification_rules(
            db,
            project_id=project_id,
            source=trigger_source,
            event_limit=event_limit,
            since=since,
        )
        counts = _status_counts(result.get("logs") or [])
        run = NotificationAutomationRun(
            id=uuid.uuid4(),
            project_id=_uuid(project_id),
            trigger_source=trigger_source,
            status=status,
            rules_count=int(result.get("rules") or 0),
            events_count=int(result.get("events") or 0),
            notifications_count=int(result.get("notifications") or 0),
            sent_count=counts["sent"],
            registered_count=counts["registered"],
            dry_run_count=counts["dry_run"],
            error_count=counts["error"],
            skipped_duplicates=int(result.get("skipped_duplicates") or 0),
            message=message,
            created_at=_now(),
        )
        db.add(run)
        db.commit()
        db.refresh(run)
        return {**result, "automation_run": serialize_automation_run(run), "window_minutes": window_minutes}
    except Exception as exc:
        db.rollback()
        status = "error"
        message = f"Falha na automação de notificações: {exc}"
        run = NotificationAutomationRun(
            id=uuid.uuid4(),
            project_id=_uuid(project_id),
            trigger_source=trigger_source,
            status=status,
            rules_count=0,
            events_count=0,
            notifications_count=0,
            sent_count=0,
            registered_count=0,
            dry_run_count=0,
            error_count=1,
            skipped_duplicates=0,
            message=message,
            created_at=_now(),
        )
        db.add(run)
        db.commit()
        return {"project_id": project_id, "source": trigger_source, "status": status, "error": message, "automation_run": serialize_automation_run(run)}




def _alert_priority_score(row: NotificationLog) -> int:
    sev = SEVERITY_ORDER.get((row.severity or "informativo").lower(), 1) * 100
    status = row.status or ""
    channel_boost = {"email": 12, "sms": 18, "whatsapp": 18, "painel": 5}.get((row.channel or "").lower(), 0)
    error_boost = 40 if status == "error" else 0
    sent_boost = 20 if status == "sent" else 0
    sla_boost = {"vencido": 80, "vence_em_breve": 35, "adiado": -10, "resolvido": -60}.get(_sla_status(row), 0)
    escalation_boost = (getattr(row, "escalation_level", 0) or 0) * 25
    return sev + channel_boost + error_boost + sent_boost + sla_boost + escalation_boost


def list_notification_inbox(
    db: Session,
    project_id: str,
    status: str | None = "aberto",
    severity: str | None = None,
    channel: str | None = None,
    limit: int = 150,
) -> dict:
    project_uuid = _uuid(project_id)
    query = db.query(NotificationLog).filter(NotificationLog.project_id == project_uuid)
    now = _now()
    if status and status != "todos":
        query = query.filter(NotificationLog.alert_status == status)
    if severity and severity != "todos":
        query = query.filter(NotificationLog.severity == severity)
    if channel and channel != "todos":
        query = query.filter(NotificationLog.channel == channel)
    rows = query.order_by(NotificationLog.created_at.desc()).limit(limit).all()
    serialized = [serialize_log(r) | {"priority_score": _alert_priority_score(r)} for r in rows]

    base = db.query(NotificationLog).filter(NotificationLog.project_id == project_uuid)
    all_rows = base.limit(5000).all()
    open_rows = [r for r in all_rows if (getattr(r, "alert_status", None) or "aberto") == "aberto"]
    snoozed_rows = [r for r in all_rows if (getattr(r, "alert_status", None) or "aberto") == "adiado"]
    due_snoozed = [r for r in snoozed_rows if getattr(r, "snoozed_until", None) and r.snoozed_until <= now]
    sla_statuses = [_sla_status(r) for r in all_rows]
    summary = {
        "total": len(all_rows),
        "open": len(open_rows),
        "acknowledged": len([r for r in all_rows if (getattr(r, "alert_status", None) or "") == "ciente"]),
        "resolved": len([r for r in all_rows if (getattr(r, "alert_status", None) or "") == "resolvido"]),
        "snoozed": len(snoozed_rows),
        "due_snoozed": len(due_snoozed),
        "critical_open": len([r for r in open_rows if (r.severity or "") == "critico"]),
        "high_open": len([r for r in open_rows if (r.severity or "") == "alto"]),
        "errors_open": len([r for r in open_rows if (r.status or "") == "error"]),
        "sla_overdue": len([s for s in sla_statuses if s == "vencido"]),
        "sla_due_soon": len([s for s in sla_statuses if s == "vence_em_breve"]),
        "escalated": len([r for r in all_rows if (getattr(r, "escalation_count", 0) or 0) > 0]),
        "unassigned_open": len([r for r in open_rows if not getattr(r, "assigned_to", None)]),
    }
    return {"project_id": project_id, "summary": summary, "items": serialized}


def update_notification_log_status(
    db: Session,
    log_id: str,
    action: str,
    payload: dict | None = None,
) -> dict:
    payload = payload or {}
    row = db.query(NotificationLog).filter(NotificationLog.id == _uuid(log_id)).first()
    if not row:
        return {"ok": False, "message": "Alerta não encontrado."}
    actor = str(payload.get("actor") or payload.get("user") or "operador").strip()[:255]
    note = str(payload.get("note") or payload.get("resolution_note") or "").strip()
    now = _now()
    if action == "ack":
        row.alert_status = "ciente"
        row.acknowledged_at = now
        row.acknowledged_by = actor
    elif action == "resolve":
        row.alert_status = "resolvido"
        row.resolved_at = now
        row.resolved_by = actor
        row.resolution_note = note or row.resolution_note
        if not row.acknowledged_at:
            row.acknowledged_at = now
            row.acknowledged_by = actor
    elif action == "snooze":
        minutes = int(payload.get("minutes") or 60)
        row.alert_status = "adiado"
        row.snoozed_until = now + timedelta(minutes=max(1, minutes))
        if note:
            row.resolution_note = note
    elif action == "reopen":
        row.alert_status = "aberto"
        row.snoozed_until = None
        if note:
            row.resolution_note = note
    else:
        return {"ok": False, "message": "Ação inválida."}
    db.commit()
    db.refresh(row)
    return {"ok": True, "message": "Status do alerta atualizado.", "item": serialize_log(row)}


def bulk_update_notification_logs(
    db: Session,
    project_id: str,
    action: str,
    payload: dict | None = None,
) -> dict:
    payload = payload or {}
    ids = [str(x) for x in _as_list(payload.get("ids")) if str(x)]
    if not ids:
        return {"ok": False, "message": "Nenhum alerta selecionado.", "updated": 0}
    updated = 0
    for log_id in ids:
        result = update_notification_log_status(db, log_id, action, payload)
        if result.get("ok"):
            updated += 1
    return {"ok": True, "message": f"{updated} alerta(s) atualizado(s).", "updated": updated}

def send_test_notification(db: Session, project_id: str, payload: dict) -> dict:
    contact_id = payload.get("contact_id")
    channel = payload.get("channel") or "painel"
    contact = None
    if contact_id:
        contact = db.query(NotificationContact).filter(NotificationContact.id == _uuid(contact_id), NotificationContact.project_id == _uuid(project_id)).first()
    if not contact:
        contact = db.query(NotificationContact).filter(NotificationContact.project_id == _uuid(project_id), NotificationContact.active.is_(True)).order_by(NotificationContact.name.asc()).first()
    event = NotificationEvent(
        event_type="test",
        severity="informativo",
        category="teste",
        title="Teste de notificação TV Fiscal",
        message=payload.get("message") or "Mensagem de teste do Motor de Notificações do TV Fiscal WebMonitor.",
        target_url=payload.get("target_url") or "/alerts",
        terms=[],
    )
    status, provider, response = _send_channel(channel, contact, event, db=db, project_id=project_id) if contact else ("registered", "painel", "Sem contato; teste registrado no painel.")
    log = _create_log(db, project_id, None, contact, channel, event, status, provider, response)
    db.commit()
    db.refresh(log)
    return {"ok": True, "log": serialize_log(log), "config": notification_config()}


def send_real_email_test(db: Session, project_id: str, payload: dict) -> dict:
    """Envia um e-mail real avulso usando credenciais informadas no próprio teste.

    Esta rota não persiste senha e ignora NOTIFICATION_DRY_RUN. Serve apenas
    para homologar SMTP real sem editar .env.
    """
    host = str(payload.get("smtp_host") or "").strip()
    port = int(payload.get("smtp_port") or 587)
    user = str(payload.get("smtp_user") or "").strip() or None
    password = str(payload.get("smtp_password") or "") or None
    sender = str(payload.get("smtp_from") or user or "").strip()
    recipient = str(payload.get("to") or "").strip()
    use_tls = bool(payload.get("smtp_use_tls", True))
    subject = str(payload.get("subject") or "TV Fiscal - Teste real de alerta SMTP")
    body = str(payload.get("message") or "Teste real de envio pelo Motor de Notificações do TV Fiscal WebMonitor.")

    event = NotificationEvent(
        event_type="real_email_test",
        severity="informativo",
        category="teste_real",
        title=subject,
        message=body,
        target_url=payload.get("target_url") or "/admin/notifications",
        terms=[],
    )

    if not host or not sender or not recipient:
        response = "Informe SMTP_HOST, remetente e destinatário para teste real."
        log = _create_log(db, project_id, None, None, "email", event, "error", "smtp_real_test", response)
        db.commit()
        db.refresh(log)
        return {"ok": False, "log": serialize_log(log), "message": response}

    try:
        msg = EmailMessage()
        msg["Subject"] = subject
        msg["From"] = sender
        msg["To"] = recipient
        msg.set_content(body)
        msg.add_alternative(
            f"""
            <div style='font-family:Arial,sans-serif;color:#111827;line-height:1.55'>
              <h2 style='color:#0b1f3a;margin-bottom:8px'>TV Fiscal WebMonitor</h2>
              <p><strong>Teste real de notificação SMTP</strong></p>
              <p>{body}</p>
              <p style='color:#667085;font-size:12px'>Este envio ignorou o dry-run apenas para homologação avulsa. A senha informada não foi armazenada.</p>
            </div>
            """,
            subtype="html",
        )
        with smtplib.SMTP(host, port, timeout=30) as smtp:
            if use_tls:
                smtp.starttls()
            if user and password:
                smtp.login(user, password)
            smtp.send_message(msg)
        response = f"E-mail real enviado para {recipient}."
        log = _create_log(db, project_id, None, None, "email", event, "sent", "smtp_real_test", response)
        db.commit()
        db.refresh(log)
        return {"ok": True, "log": serialize_log(log), "message": response}
    except Exception as exc:
        response = f"Falha no teste real SMTP: {exc}"
        log = _create_log(db, project_id, None, None, "email", event, "error", "smtp_real_test", response)
        db.commit()
        db.refresh(log)
        return {"ok": False, "log": serialize_log(log), "message": response}


def send_automatic_email_test(db: Session, project_id: str, payload: dict | None = None) -> dict:
    payload = payload or {}
    contact = db.query(NotificationContact).filter(
        NotificationContact.project_id == _uuid(project_id),
        NotificationContact.active.is_(True),
        NotificationContact.email.isnot(None),
    ).order_by(NotificationContact.name.asc()).first()
    event = NotificationEvent(
        event_type="automatic_email_test",
        severity="informativo",
        category="teste_automatico",
        title=payload.get("subject") or "TV Fiscal - Teste automático de regra por e-mail",
        message=payload.get("message") or "Teste de envio pelo mesmo caminho usado pelas regras automáticas do Motor de Notificações.",
        target_url=payload.get("target_url") or "/admin/notifications",
        terms=[],
    )
    if not contact:
        response = "Nenhum contato ativo com e-mail cadastrado."
        log = _create_log(db, project_id, None, None, "email", event, "error", "smtp_projeto", response)
        db.commit(); db.refresh(log)
        return {"ok": False, "message": response, "log": serialize_log(log)}
    status, provider, response = _send_channel("email", contact, event, db=db, project_id=project_id)
    log = _create_log(db, project_id, None, contact, "email", event, status, provider, response)
    db.commit(); db.refresh(log)
    return {"ok": status == "sent", "message": response, "log": serialize_log(log), "config": notification_config(), "provider_profiles": get_provider_settings(db, project_id)}


def list_logs(db: Session, project_id: str, limit: int = 100, status: str | None = None, channel: str | None = None) -> list[dict]:
    query = db.query(NotificationLog).filter(NotificationLog.project_id == _uuid(project_id))
    if status:
        query = query.filter(NotificationLog.status == status)
    if channel:
        query = query.filter(NotificationLog.channel == channel)
    return [serialize_log(row) for row in query.order_by(NotificationLog.created_at.desc()).limit(limit).all()]


def cleanup_notification_duplicates(db: Session, project_id: str) -> dict:
    project_uuid = _uuid(project_id)
    contacts = db.query(NotificationContact).filter(NotificationContact.project_id == project_uuid, NotificationContact.active.is_(True)).order_by(NotificationContact.created_at.asc()).all()
    seen_contacts: dict[str, NotificationContact] = {}
    deactivated_contacts = 0
    for row in contacts:
        key = "|".join([_norm(row.name), _norm(row.email), _norm(row.phone), _norm(row.whatsapp)])
        if key in seen_contacts:
            row.active = False
            row.updated_at = _now()
            deactivated_contacts += 1
        else:
            seen_contacts[key] = row

    rules = db.query(NotificationRule).filter(NotificationRule.project_id == project_uuid, NotificationRule.active.is_(True)).order_by(NotificationRule.created_at.asc()).all()
    seen_rules: dict[str, NotificationRule] = {}
    deactivated_rules = 0
    for row in rules:
        key = "|".join([
            _norm(row.name),
            _norm(row.event_type),
            ",".join(sorted(_norm(x) for x in _as_list(row.terms))),
            ",".join(sorted(_norm(x) for x in _as_list(row.categories))),
            ",".join(sorted(_norm(x) for x in _as_list(row.channels))),
            _norm(row.severity_min),
            _norm(row.sentiment_filter),
        ])
        if key in seen_rules:
            row.active = False
            row.updated_at = _now()
            deactivated_rules += 1
        else:
            seen_rules[key] = row
    db.commit()
    return {
        "project_id": project_id,
        "contacts_deactivated": deactivated_contacts,
        "rules_deactivated": deactivated_rules,
        "message": "Limpeza concluída. Duplicidades foram desativadas, não excluídas.",
    }


def notification_dashboard(db: Session, project_id: str) -> dict:
    contacts = list_contacts(db, project_id)
    rules = list_rules(db, project_id)
    logs = list_logs(db, project_id, limit=50)
    inbox = list_notification_inbox(db, project_id, status="todos", limit=500)
    sent = len([l for l in logs if l["status"] == "sent"])
    registered = len([l for l in logs if l["status"] == "registered"])
    dry = len([l for l in logs if l["status"] == "dry_run"])
    errors = len([l for l in logs if l["status"] == "error"])
    return {
        "project_id": project_id,
        "config": notification_config(),
        "summary": {
            "contacts": len(contacts),
            "active_contacts": len([c for c in contacts if c["active"]]),
            "rules": len(rules),
            "active_rules": len([r for r in rules if r["active"]]),
            "logs": len(logs),
            "sent": sent,
            "registered": registered,
            "dry_run": dry,
            "errors": errors,
        },
        "contacts": contacts,
        "rules": rules,
        "logs": logs,
        "automation_runs": list_automation_runs(db, project_id, limit=10),
        "inbox_summary": inbox.get("summary", {}),
        "provider_profiles": get_provider_settings(db, project_id),
    }

# -----------------------------------------------------------------------------
# V34 — SMS e WhatsApp real por projeto
# Estas funções complementam o motor existente sem quebrar o fluxo homologado de e-mail.
# O NotificationProviderSetting já é genérico e passa a armazenar perfis sms/whatsapp.
# -----------------------------------------------------------------------------

def _sanitize_phone_for_provider(value: str | None) -> str:
    digits = _clean_phone(value)
    return digits or ""


def _public_provider_config(cfg: dict, provider_type: str) -> dict:
    safe = dict(cfg or {})
    secret_keys = [
        "auth_token", "token", "api_token", "access_token", "webhook_url",
        "twilio_auth_token", "zenvia_api_token", "totalvoice_access_token",
        "meta_access_token", "smtp_password",
    ]
    for key in secret_keys:
        if key in safe and safe.get(key):
            safe[key] = "***"
    return safe


def _provider_setting_to_dict(row: NotificationProviderSetting | None, include_secret: bool = False) -> dict | None:  # type: ignore[no-redef]
    if not row:
        return None
    cfg = dict(row.config or {})
    safe_cfg = cfg if include_secret else _public_provider_config(cfg, row.provider_type)
    return {
        "id": str(row.id),
        "project_id": str(row.project_id),
        "provider_type": row.provider_type,
        "provider_name": row.provider_name,
        "active": bool(row.active),
        "config": safe_cfg,
        "created_at": iso_local(row.created_at),
        "created_at_display": display_local(row.created_at),
        "updated_at": iso_local(row.updated_at),
        "updated_at_display": display_local(row.updated_at),
    }


def get_provider_settings(db: Session, project_id: str) -> dict:  # type: ignore[no-redef]
    email = _get_provider_setting(db, project_id, "email")
    sms = _get_provider_setting(db, project_id, "sms")
    whatsapp = _get_provider_setting(db, project_id, "whatsapp")
    return {
        "project_id": project_id,
        "email": _provider_setting_to_dict(email),
        "sms": _provider_setting_to_dict(sms),
        "whatsapp": _provider_setting_to_dict(whatsapp),
        "automatic_email_ready": bool(email and (email.config or {}).get("smtp_host") and (email.config or {}).get("smtp_from")),
        "automatic_sms_ready": bool(sms and sms.active and (sms.config or {}).get("provider")),
        "automatic_whatsapp_ready": bool(whatsapp and whatsapp.active and (whatsapp.config or {}).get("provider")),
        "message": "Configurações de provedores automáticos por projeto.",
    }


def _validate_sms_cfg(provider: str, cfg: dict) -> tuple[bool, str]:
    provider = (provider or "webhook").lower()
    if provider == "webhook":
        return (bool(cfg.get("webhook_url")), "Informe URL do webhook SMS." if not cfg.get("webhook_url") else "")
    if provider == "twilio":
        ok = bool(cfg.get("account_sid") and cfg.get("auth_token") and cfg.get("from_number"))
        return (ok, "Informe Account SID, Auth Token e número remetente Twilio." if not ok else "")
    if provider == "zenvia":
        ok = bool(cfg.get("api_token") and cfg.get("from_name"))
        return (ok, "Informe API token e remetente Zenvia." if not ok else "")
    if provider == "totalvoice":
        ok = bool(cfg.get("access_token"))
        return (ok, "Informe Access Token TotalVoice." if not ok else "")
    return False, f"Provedor SMS não suportado: {provider}."


def _validate_whatsapp_cfg(provider: str, cfg: dict) -> tuple[bool, str]:
    provider = (provider or "webhook").lower()
    if provider == "webhook":
        return (bool(cfg.get("webhook_url")), "Informe URL do webhook WhatsApp." if not cfg.get("webhook_url") else "")
    if provider == "zenvia":
        ok = bool(cfg.get("api_token") and cfg.get("from_number"))
        return (ok, "Informe API token e remetente Zenvia WhatsApp." if not ok else "")
    if provider in {"meta", "cloudapi", "whatsapp_cloud"}:
        ok = bool(cfg.get("access_token") and cfg.get("phone_number_id"))
        return (ok, "Informe Access Token e Phone Number ID da Meta WhatsApp Cloud API." if not ok else "")
    return False, f"Provedor WhatsApp não suportado: {provider}."


def upsert_sms_setting(db: Session, project_id: str, payload: dict) -> dict:
    provider = str(payload.get("provider") or "webhook").strip().lower()
    cfg = {
        "provider": provider,
        "webhook_url": str(payload.get("webhook_url") or "").strip(),
        "account_sid": str(payload.get("account_sid") or "").strip(),
        "auth_token": str(payload.get("auth_token") or ""),
        "from_number": _sanitize_phone_for_provider(payload.get("from_number")),
        "api_token": str(payload.get("api_token") or ""),
        "from_name": str(payload.get("from_name") or "TVFiscal").strip(),
        "access_token": str(payload.get("access_token") or ""),
        "active": bool(payload.get("active", True)),
    }
    existing = _get_provider_setting(db, project_id, "sms")
    current = dict(existing.config or {}) if existing else {}
    # preserva segredos quando vierem mascarados ou vazios em edição
    for key in ["auth_token", "api_token", "access_token", "webhook_url"]:
        if (not cfg.get(key) or cfg.get(key) == "***") and current.get(key):
            cfg[key] = current.get(key)
    ok, msg = _validate_sms_cfg(provider, cfg)
    if not ok:
        return {"ok": False, "message": msg, "sms": _provider_setting_to_dict(existing) if existing else None}
    row = existing or NotificationProviderSetting(
        id=uuid.uuid4(), project_id=_uuid(project_id), provider_type="sms", provider_name=provider, active=True
    )
    if not existing:
        db.add(row)
    row.provider_name = provider
    row.config = cfg
    row.active = bool(payload.get("active", True))
    row.updated_at = _now()
    db.commit(); db.refresh(row)
    return {"ok": True, "message": "Provedor SMS salvo para alertas automáticos deste projeto.", "sms": _provider_setting_to_dict(row)}


def deactivate_sms_setting(db: Session, project_id: str) -> dict:
    row = _get_provider_setting(db, project_id, "sms")
    if not row:
        return {"ok": False, "message": "Nenhum provedor SMS ativo encontrado."}
    row.active = False; row.updated_at = _now(); db.commit()
    return {"ok": True, "message": "Provedor SMS desativado para este projeto."}


def upsert_whatsapp_setting(db: Session, project_id: str, payload: dict) -> dict:
    provider = str(payload.get("provider") or "webhook").strip().lower()
    cfg = {
        "provider": provider,
        "webhook_url": str(payload.get("webhook_url") or "").strip(),
        "api_token": str(payload.get("api_token") or ""),
        "from_number": _sanitize_phone_for_provider(payload.get("from_number")),
        "access_token": str(payload.get("access_token") or ""),
        "phone_number_id": str(payload.get("phone_number_id") or "").strip(),
        "active": bool(payload.get("active", True)),
    }
    existing = _get_provider_setting(db, project_id, "whatsapp")
    current = dict(existing.config or {}) if existing else {}
    for key in ["api_token", "access_token", "webhook_url"]:
        if (not cfg.get(key) or cfg.get(key) == "***") and current.get(key):
            cfg[key] = current.get(key)
    ok, msg = _validate_whatsapp_cfg(provider, cfg)
    if not ok:
        return {"ok": False, "message": msg, "whatsapp": _provider_setting_to_dict(existing) if existing else None}
    row = existing or NotificationProviderSetting(
        id=uuid.uuid4(), project_id=_uuid(project_id), provider_type="whatsapp", provider_name=provider, active=True
    )
    if not existing:
        db.add(row)
    row.provider_name = provider
    row.config = cfg
    row.active = bool(payload.get("active", True))
    row.updated_at = _now()
    db.commit(); db.refresh(row)
    return {"ok": True, "message": "Provedor WhatsApp salvo para alertas automáticos deste projeto.", "whatsapp": _provider_setting_to_dict(row)}


def deactivate_whatsapp_setting(db: Session, project_id: str) -> dict:
    row = _get_provider_setting(db, project_id, "whatsapp")
    if not row:
        return {"ok": False, "message": "Nenhum provedor WhatsApp ativo encontrado."}
    row.active = False; row.updated_at = _now(); db.commit()
    return {"ok": True, "message": "Provedor WhatsApp desativado para este projeto."}


def _send_sms_with_config(contact: NotificationContact, event: NotificationEvent, cfg: dict, provider_name: str = "sms_projeto") -> tuple[str, str, str]:
    if not contact.phone:
        return "skipped", provider_name, "Contato sem telefone SMS."
    provider = str(cfg.get("provider") or "webhook").lower()
    message = _build_channel_message("sms", event)
    to = contact.phone
    if provider == "twilio":
        sid = cfg.get("account_sid")
        token = cfg.get("auth_token")
        from_number = cfg.get("from_number")
        if not (sid and token and from_number):
            return "error", "twilio_projeto", "Credenciais Twilio incompletas."
        import requests
        url = f"https://api.twilio.com/2010-04-01/Accounts/{sid}/Messages.json"
        resp = requests.post(url, data={"From": from_number, "To": to, "Body": message}, auth=(sid, token), timeout=25)
        return ("sent" if resp.ok else "error", "twilio_projeto", f"HTTP {resp.status_code}: {resp.text[:300]}")
    if provider == "zenvia":
        token = cfg.get("api_token")
        sender = cfg.get("from_name") or "TVFiscal"
        if not token:
            return "error", "zenvia_sms_projeto", "API token Zenvia ausente."
        payload = {"from": sender, "to": to, "contents": [{"type": "text", "text": message}]}
        status, response = _post_json("https://api.zenvia.com/v2/channels/sms/messages", payload, headers={"X-API-TOKEN": token, "Content-Type": "application/json"})
        return status, "zenvia_sms_projeto", response
    if provider == "totalvoice":
        token = cfg.get("access_token")
        if not token:
            return "error", "totalvoice_projeto", "Access token TotalVoice ausente."
        payload = {"numero_destino": to, "mensagem": message}
        status, response = _post_json("https://api.totalvoice.com.br/sms", payload, headers={"Access-Token": token, "Content-Type": "application/json"})
        return status, "totalvoice_projeto", response
    webhook = cfg.get("webhook_url")
    if webhook:
        status, response = _post_json(webhook, {"to": to, "message": message, "title": event.title, "channel": "sms", "event": event.__dict__})
        return status, "sms_webhook_projeto", response
    return "error", provider_name, "Configuração SMS sem endpoint/credenciais."


def _send_whatsapp_with_config(contact: NotificationContact, event: NotificationEvent, cfg: dict, provider_name: str = "whatsapp_projeto") -> tuple[str, str, str]:
    if not contact.whatsapp:
        return "skipped", provider_name, "Contato sem WhatsApp."
    provider = str(cfg.get("provider") or "webhook").lower()
    message = _build_channel_message("whatsapp", event)
    to = contact.whatsapp
    if provider == "zenvia":
        token = cfg.get("api_token")
        sender = cfg.get("from_number")
        if not (token and sender):
            return "error", "zenvia_whatsapp_projeto", "API token ou remetente Zenvia WhatsApp ausente."
        payload = {"from": sender, "to": to, "contents": [{"type": "text", "text": message}]}
        status, response = _post_json("https://api.zenvia.com/v2/channels/whatsapp/messages", payload, headers={"X-API-TOKEN": token, "Content-Type": "application/json"})
        return status, "zenvia_whatsapp_projeto", response
    if provider in {"meta", "cloudapi", "whatsapp_cloud"}:
        token = cfg.get("access_token")
        phone_number_id = cfg.get("phone_number_id")
        if not (token and phone_number_id):
            return "error", "meta_whatsapp_projeto", "Access token ou Phone Number ID ausente."
        payload = {"messaging_product": "whatsapp", "to": to, "type": "text", "text": {"preview_url": False, "body": message}}
        url = f"https://graph.facebook.com/v20.0/{phone_number_id}/messages"
        status, response = _post_json(url, payload, headers={"Authorization": f"Bearer {token}", "Content-Type": "application/json"})
        return status, "meta_whatsapp_projeto", response
    webhook = cfg.get("webhook_url")
    if webhook:
        status, response = _post_json(webhook, {"to": to, "message": message, "title": event.title, "channel": "whatsapp", "event": event.__dict__})
        return status, "whatsapp_webhook_projeto", response
    return "error", provider_name, "Configuração WhatsApp sem endpoint/credenciais."


def _send_channel(channel: str, contact: NotificationContact, event: NotificationEvent, db: Session | None = None, project_id: str | None = None) -> tuple[str, str, str]:  # type: ignore[no-redef]
    """V34: envia por perfil de projeto quando existir, mesmo com dry-run global ativo."""
    cfg = notification_config()
    channel = (channel or "painel").lower()
    if channel in {"painel", "in_app", "interno"}:
        return "registered", "painel", "Alerta registrado no painel interno."

    saved = _get_provider_setting(db, project_id, channel) if channel in {"email", "sms", "whatsapp"} and db and project_id else None
    if cfg["dry_run"] and not (saved and saved.active):
        provider = cfg.get(f"{channel}_provider") or os.getenv(f"{channel.upper()}_PROVIDER", "dry_run")
        return "dry_run", provider, "Envio simulado por NOTIFICATION_DRY_RUN=true."

    try:
        if channel == "email":
            if saved and saved.active:
                return _send_email_with_config(contact, event, dict(saved.config or {}), "smtp_projeto")
            if not cfg["email_enabled"]:
                return "skipped", "email", "EMAIL_ALERTS_ENABLED=false e nenhum SMTP de projeto ativo."
            return _send_email_with_config(contact, event, {
                "smtp_host": os.getenv("SMTP_HOST"),
                "smtp_port": int(os.getenv("SMTP_PORT", "587")),
                "smtp_user": os.getenv("SMTP_USER"),
                "smtp_password": os.getenv("SMTP_PASSWORD"),
                "smtp_from": os.getenv("SMTP_FROM") or os.getenv("SMTP_USER") or "alertas@tvfiscal.local",
                "smtp_use_tls": _bool_env("SMTP_USE_TLS", "true"),
            }, "smtp")
        if channel == "sms":
            if saved and saved.active:
                return _send_sms_with_config(contact, event, dict(saved.config or {}), "sms_projeto")
            if not cfg["sms_enabled"]:
                return "skipped", "sms", "SMS_ENABLED=false e nenhum provedor SMS de projeto ativo."
            return _send_sms_real(contact, event)
        if channel == "whatsapp":
            if saved and saved.active:
                return _send_whatsapp_with_config(contact, event, dict(saved.config or {}), "whatsapp_projeto")
            if not cfg["whatsapp_enabled"]:
                return "skipped", "whatsapp", "WHATSAPP_ALERTS_ENABLED=false e nenhum provedor WhatsApp de projeto ativo."
            return _send_whatsapp_real(contact, event)
        if channel == "webhook":
            webhook = os.getenv("NOTIFICATION_WEBHOOK_URL")
            if not webhook:
                return "skipped", "webhook", "NOTIFICATION_WEBHOOK_URL não configurado."
            status, response = _post_json(webhook, {"contact": serialize_contact(contact), "event": event.__dict__})
            return status, "webhook", response
    except Exception as exc:
        return "error", channel, str(exc)
    return "skipped", channel, "Canal não suportado."


def _first_active_contact_with_channel(db: Session, project_id: str, channel: str) -> NotificationContact | None:
    query = db.query(NotificationContact).filter(NotificationContact.project_id == _uuid(project_id), NotificationContact.active.is_(True))
    if channel == "sms":
        query = query.filter(NotificationContact.phone.isnot(None))
    elif channel == "whatsapp":
        query = query.filter(NotificationContact.whatsapp.isnot(None))
    elif channel == "email":
        query = query.filter(NotificationContact.email.isnot(None))
    return query.order_by(NotificationContact.name.asc()).first()


def send_real_sms_test(db: Session, project_id: str, payload: dict) -> dict:
    contact = _first_active_contact_with_channel(db, project_id, "sms")
    if not contact and payload.get("to"):
        contact = NotificationContact(id=uuid.uuid4(), project_id=_uuid(project_id), name="Teste SMS", phone=_clean_phone(payload.get("to")), channels=["sms"], active=True)
    event = NotificationEvent(
        event_type="real_sms_test", severity="informativo", category="teste_real",
        title=payload.get("title") or "TV Fiscal - Teste real SMS",
        message=payload.get("message") or "Teste real de SMS pelo Motor de Notificações do TV Fiscal WebMonitor.",
        target_url=payload.get("target_url") or "/admin/notifications", terms=[])
    provider = str(payload.get("provider") or "webhook").lower()
    cfg = dict(payload); cfg["provider"] = provider
    if not contact:
        response = "Informe destinatário SMS ou cadastre contato ativo com telefone."
        log = _create_log(db, project_id, None, None, "sms", event, "error", "sms_real_test", response); db.commit(); db.refresh(log)
        return {"ok": False, "message": response, "log": serialize_log(log)}
    status, provider_name, response = _send_sms_with_config(contact, event, cfg, "sms_real_test")
    log = _create_log(db, project_id, None, contact if getattr(contact, "id", None) else None, "sms", event, status, provider_name, response)
    db.commit(); db.refresh(log)
    return {"ok": status == "sent", "message": response, "log": serialize_log(log)}


def send_real_whatsapp_test(db: Session, project_id: str, payload: dict) -> dict:
    contact = _first_active_contact_with_channel(db, project_id, "whatsapp")
    if not contact and payload.get("to"):
        contact = NotificationContact(id=uuid.uuid4(), project_id=_uuid(project_id), name="Teste WhatsApp", whatsapp=_clean_phone(payload.get("to")), channels=["whatsapp"], active=True)
    event = NotificationEvent(
        event_type="real_whatsapp_test", severity="informativo", category="teste_real",
        title=payload.get("title") or "TV Fiscal - Teste real WhatsApp",
        message=payload.get("message") or "Teste real de WhatsApp pelo Motor de Notificações do TV Fiscal WebMonitor.",
        target_url=payload.get("target_url") or "/admin/notifications", terms=[])
    provider = str(payload.get("provider") or "webhook").lower()
    cfg = dict(payload); cfg["provider"] = provider
    if not contact:
        response = "Informe destinatário WhatsApp ou cadastre contato ativo com WhatsApp."
        log = _create_log(db, project_id, None, None, "whatsapp", event, "error", "whatsapp_real_test", response); db.commit(); db.refresh(log)
        return {"ok": False, "message": response, "log": serialize_log(log)}
    status, provider_name, response = _send_whatsapp_with_config(contact, event, cfg, "whatsapp_real_test")
    log = _create_log(db, project_id, None, contact if getattr(contact, "id", None) else None, "whatsapp", event, status, provider_name, response)
    db.commit(); db.refresh(log)
    return {"ok": status == "sent", "message": response, "log": serialize_log(log)}


def send_automatic_sms_test(db: Session, project_id: str, payload: dict | None = None) -> dict:
    payload = payload or {}
    contact = _first_active_contact_with_channel(db, project_id, "sms")
    event = NotificationEvent(
        event_type="automatic_sms_test", severity="informativo", category="teste_automatico",
        title=payload.get("title") or "TV Fiscal - Teste automático SMS",
        message=payload.get("message") or "Teste usando o mesmo provedor SMS salvo para regras automáticas.",
        target_url=payload.get("target_url") or "/admin/notifications", terms=[])
    if not contact:
        response = "Nenhum contato ativo com telefone SMS cadastrado."
        log = _create_log(db, project_id, None, None, "sms", event, "error", "sms_projeto", response); db.commit(); db.refresh(log)
        return {"ok": False, "message": response, "log": serialize_log(log)}
    status, provider, response = _send_channel("sms", contact, event, db=db, project_id=project_id)
    log = _create_log(db, project_id, None, contact, "sms", event, status, provider, response); db.commit(); db.refresh(log)
    return {"ok": status == "sent", "message": response, "log": serialize_log(log), "provider_profiles": get_provider_settings(db, project_id)}


def send_automatic_whatsapp_test(db: Session, project_id: str, payload: dict | None = None) -> dict:
    payload = payload or {}
    contact = _first_active_contact_with_channel(db, project_id, "whatsapp")
    event = NotificationEvent(
        event_type="automatic_whatsapp_test", severity="informativo", category="teste_automatico",
        title=payload.get("title") or "TV Fiscal - Teste automático WhatsApp",
        message=payload.get("message") or "Teste usando o mesmo provedor WhatsApp salvo para regras automáticas.",
        target_url=payload.get("target_url") or "/admin/notifications", terms=[])
    if not contact:
        response = "Nenhum contato ativo com WhatsApp cadastrado."
        log = _create_log(db, project_id, None, None, "whatsapp", event, "error", "whatsapp_projeto", response); db.commit(); db.refresh(log)
        return {"ok": False, "message": response, "log": serialize_log(log)}
    status, provider, response = _send_channel("whatsapp", contact, event, db=db, project_id=project_id)
    log = _create_log(db, project_id, None, contact, "whatsapp", event, status, provider, response); db.commit(); db.refresh(log)
    return {"ok": status == "sent", "message": response, "log": serialize_log(log), "provider_profiles": get_provider_settings(db, project_id)}


def assign_notification_log(db: Session, log_id: str, payload: dict | None = None) -> dict:
    payload = payload or {}
    row = db.query(NotificationLog).filter(NotificationLog.id == _uuid(log_id)).first()
    if not row:
        return {"ok": False, "message": "Alerta não encontrado."}
    assignee = str(payload.get("assigned_to") or payload.get("actor") or "operador").strip()[:255]
    note = str(payload.get("note") or "").strip()
    row.assigned_to = assignee
    if (row.alert_status or "aberto") == "aberto":
        row.alert_status = "ciente"
        row.acknowledged_at = _now()
        row.acknowledged_by = assignee
    if note:
        row.resolution_note = note
    db.commit(); db.refresh(row)
    return {"ok": True, "message": f"Alerta atribuído a {assignee}.", "item": serialize_log(row)}


def list_sla_dashboard(db: Session, project_id: str, limit: int = 200) -> dict:
    project_uuid = _uuid(project_id)
    rows = db.query(NotificationLog).filter(NotificationLog.project_id == project_uuid).order_by(NotificationLog.created_at.desc()).limit(5000).all()
    active = [r for r in rows if (getattr(r, "alert_status", None) or "aberto") not in {"resolvido"}]
    overdue = [r for r in active if _sla_status(r) == "vencido"]
    due_soon = [r for r in active if _sla_status(r) == "vence_em_breve"]
    unassigned = [r for r in active if not getattr(r, "assigned_to", None)]
    escalated = [r for r in active if (getattr(r, "escalation_count", 0) or 0) > 0]
    by_owner: dict[str, int] = {}
    for r in active:
        owner = getattr(r, "assigned_to", None) or "Sem responsável"
        by_owner[owner] = by_owner.get(owner, 0) + 1
    by_severity: dict[str, int] = {}
    for r in active:
        sev = r.severity or "informativo"
        by_severity[sev] = by_severity.get(sev, 0) + 1
    ordered = sorted(active, key=lambda r: (_sla_status(r) != "vencido", getattr(r, "sla_due_at", None) or _now()))[:limit]
    return {
        "project_id": project_id,
        "summary": {
            "active": len(active),
            "overdue": len(overdue),
            "due_soon": len(due_soon),
            "unassigned": len(unassigned),
            "escalated": len(escalated),
            "resolved": len([r for r in rows if (getattr(r, "alert_status", None) or "") == "resolvido"]),
        },
        "by_owner": [{"owner": k, "count": v} for k, v in sorted(by_owner.items(), key=lambda x: x[1], reverse=True)],
        "by_severity": [{"severity": k, "count": v} for k, v in sorted(by_severity.items(), key=lambda x: SEVERITY_ORDER.get(x[0], 0), reverse=True)],
        "items": [serialize_log(r) | {"priority_score": _alert_priority_score(r)} for r in ordered],
    }


def evaluate_sla_escalations(db: Session, project_id: str, payload: dict | None = None) -> dict:
    payload = payload or {}
    project_uuid = _uuid(project_id)
    now = _now()
    dry_run = bool(payload.get("dry_run", False))
    send_email = bool(payload.get("send_email", True))
    escalation_note = str(payload.get("note") or "Escalonamento automático por SLA vencido.")[:500]
    rows = db.query(NotificationLog).filter(
        NotificationLog.project_id == project_uuid,
        NotificationLog.alert_status.in_(["aberto", "ciente"]),
        NotificationLog.sla_due_at.isnot(None),
        NotificationLog.sla_due_at <= now,
    ).order_by(NotificationLog.sla_due_at.asc()).limit(int(payload.get("limit") or 100)).all()

    contacts = db.query(NotificationContact).filter(
        NotificationContact.project_id == project_uuid,
        NotificationContact.active.is_(True),
        NotificationContact.email.isnot(None),
    ).all()
    # Prioriza contatos com prioridade alta/diretoria; se não houver, usa todos com e-mail.
    priority_contacts = [c for c in contacts if (c.priority or "").lower() in {"alta", "alto", "critico", "diretoria", "urgente"}] or contacts

    escalated = 0
    emails = 0
    errors = 0
    escalation_logs = []
    for row in rows:
        row.escalation_level = (getattr(row, "escalation_level", 0) or 0) + 1
        row.escalation_count = (getattr(row, "escalation_count", 0) or 0) + 1
        row.escalated_at = now
        row.last_escalation_note = escalation_note
        row.provider_response = ((row.provider_response or "") + f" | SLA vencido escalonado em {display_local(now)}").strip(" |")
        escalated += 1
        if send_email and priority_contacts:
            event = NotificationEvent(
                event_type="sla_overdue",
                severity="critico" if (row.severity or "") in {"critico", "alto"} else "alto",
                category="sla",
                title=f"SLA vencido: {row.title or 'Alerta TV Fiscal'}",
                message=f"Alerta com SLA vencido. Prazo: {display_local(row.sla_due_at)}. Responsável: {row.assigned_to or 'sem responsável'}. Mensagem original: {(row.message or '')[:300]}",
                target_url=row.target_url or "/alerts/inbox",
                terms=[],
            )
            for contact in priority_contacts[:5]:
                if dry_run:
                    status, provider, response = "dry_run", "sla_dry_run", "Escalonamento de SLA simulado."
                else:
                    status, provider, response = _send_channel("email", contact, event, db=db, project_id=project_id)
                log = _create_log(db, project_id, None, contact, "email", event, status, provider, response)
                log.assigned_to = contact.name
                log.sla_minutes = _sla_minutes_for(event.severity)
                log.sla_due_at = now + timedelta(minutes=log.sla_minutes or 30)
                escalation_logs.append(log)
                if status == "sent":
                    emails += 1
                elif status == "error":
                    errors += 1
    db.commit()
    return {
        "ok": True,
        "project_id": project_id,
        "evaluated": len(rows),
        "escalated": escalated,
        "emails_sent": emails,
        "errors": errors,
        "dry_run": dry_run,
        "logs": [serialize_log(l) for l in escalation_logs[-20:]],
        "message": f"{escalated} alerta(s) vencido(s) escalonado(s).",
    }
