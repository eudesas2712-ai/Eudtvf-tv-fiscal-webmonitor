from __future__ import annotations

import uuid
from collections import Counter, defaultdict
from datetime import datetime, timedelta
from typing import Any

from sqlalchemy import func
from sqlalchemy.orm import Session

from app.db.models import (
    Advertiser,
    BannerItem,
    Item,
    NotificationAutomationRun,
    NotificationLog,
    NotificationProviderSetting,
    Project,
    ProjectPortal,
    Source,
)
from app.utils.timeutils import display_local, iso_local, utc_now


def _uuid(value: Any):
    if not value:
        return None
    if isinstance(value, uuid.UUID):
        return value
    return uuid.UUID(str(value))


def _safe_int(value: Any) -> int:
    try:
        return int(value or 0)
    except Exception:
        return 0


def _money(value: Any) -> int:
    return _safe_int(value)


def _is_non_identified(name: str | None) -> bool:
    if not name:
        return True
    n = name.strip().lower()
    return n in {
        "nao identificado",
        "não identificado",
        "pendente de identificação",
        "pendente identificacao",
        "unknown",
        "sem identificação",
        "sem identificacao",
    }


def _severity_value(value: str | None) -> int:
    return {"critico": 4, "crítico": 4, "alto": 3, "medio": 2, "médio": 2, "informativo": 1, "baixo": 1}.get(
        str(value or "informativo").lower(), 1
    )


def _alert_status(row: NotificationLog) -> str:
    return str(getattr(row, "alert_status", None) or "aberto").lower()


def _status(row: NotificationLog) -> str:
    return str(getattr(row, "status", None) or "").lower()


def _sla_status(row: NotificationLog, now: datetime) -> str:
    if _alert_status(row) == "resolvido":
        return "resolvido"
    due = getattr(row, "sla_due_at", None)
    if not due:
        return "sem_sla"
    if due < now:
        return "vencido"
    if due <= now + timedelta(minutes=60):
        return "vence_em_breve"
    return "no_prazo"


def _counter_list(counter: Counter, key: str, limit: int = 8) -> list[dict]:
    return [{key: k, "count": v} for k, v in counter.most_common(limit)]


def _day_key(dt: datetime | None) -> str:
    if not dt:
        return "sem data"
    try:
        local = display_local(dt).split(",")[0]
        return local
    except Exception:
        return str(dt.date())


def _project_name_map(db: Session) -> dict[str, str]:
    rows = db.query(Project.id, Project.name, Project.client_name).all()
    result: dict[str, str] = {}
    for pid, name, client in rows:
        label = name or client or str(pid)
        result[str(pid)] = label
    return result


def build_executive_dashboard(db: Session, project_id: str | None = None, days: int = 30) -> dict:
    """Visão executiva consolidada da plataforma.

    Mantém as consultas simples para funcionar em bases pequenas ou médias e tolerar
    instalações em homologação. A tela usa esses dados para o painel principal.
    """
    now = utc_now()
    days = max(1, min(int(days or 30), 365))
    since = now - timedelta(days=days)
    project_uuid = _uuid(project_id) if project_id else None

    project_query = db.query(Project)
    projects = project_query.order_by(Project.created_at.desc()).all()
    active_projects = [p for p in projects if getattr(p, "active", True)]
    project_map = {str(p.id): p for p in projects}
    name_map = _project_name_map(db)

    item_query = db.query(Item)
    banner_query = db.query(BannerItem)
    log_query = db.query(NotificationLog)
    automation_query = db.query(NotificationAutomationRun)
    source_query = db.query(Source)
    project_portal_query = db.query(ProjectPortal)

    if project_uuid:
        item_query = item_query.filter(Item.project_id == project_uuid)
        banner_query = banner_query.filter(BannerItem.project_id == project_uuid)
        log_query = log_query.filter(NotificationLog.project_id == project_uuid)
        automation_query = automation_query.filter(NotificationAutomationRun.project_id == project_uuid)
        source_query = source_query.filter(Source.project_id == project_uuid)
        project_portal_query = project_portal_query.filter(ProjectPortal.project_id == project_uuid)

    items = item_query.order_by(Item.created_at.desc()).limit(5000).all()
    banners = banner_query.order_by(BannerItem.created_at.desc()).limit(8000).all()
    logs = log_query.order_by(NotificationLog.created_at.desc()).limit(5000).all()
    automations = automation_query.order_by(NotificationAutomationRun.created_at.desc()).limit(30).all()

    recent_items = [i for i in items if getattr(i, "created_at", None) and i.created_at >= since]
    recent_banners = [b for b in banners if getattr(b, "created_at", None) and b.created_at >= since]
    recent_logs = [l for l in logs if getattr(l, "created_at", None) and l.created_at >= since]

    market_items = [b for b in banners if str(getattr(b, "market_status", "") or "").lower() in {"incluido", "incluído"}]
    auditables = [b for b in banners if str(getattr(b, "checking_status", "") or "").lower() == "auditavel"]
    review_items = [b for b in banners if str(getattr(b, "checking_status", "") or "").lower() in {"parcial", "revisao", "revisão"}]
    news_candidates = [b for b in banners if str(getattr(b, "news_status", "") or "").lower() == "candidato"]
    preserved = [b for b in banners if getattr(b, "has_preserved_evidence", False)]

    pending_identification = []
    identified_market = []
    investment_total = 0
    pending_investment = 0
    for b in market_items:
        value = _money(getattr(b, "estimated_value", 0))
        investment_total += value
        status = str(getattr(b, "identification_status", "") or "").lower()
        name = getattr(b, "advertiser_name", None)
        if status in {"pendente", "pending"} or _is_non_identified(name):
            pending_identification.append(b)
            pending_investment += value
        else:
            identified_market.append(b)

    active_alerts = [l for l in logs if _alert_status(l) != "resolvido"]
    resolved_alerts = [l for l in logs if _alert_status(l) == "resolvido"]
    sent_alerts = [l for l in logs if _status(l) == "sent"]
    errors_alerts = [l for l in logs if _status(l) == "error"]
    dry_run_alerts = [l for l in logs if _status(l) == "dry_run"]
    painel_alerts = [l for l in logs if _status(l) == "registered" or str(getattr(l, "channel", "") or "").lower() == "painel"]
    overdue_alerts = [l for l in active_alerts if _sla_status(l, now) == "vencido"]
    due_soon_alerts = [l for l in active_alerts if _sla_status(l, now) == "vence_em_breve"]
    unassigned_alerts = [l for l in active_alerts if not getattr(l, "assigned_to", None)]
    escalated_alerts = [l for l in logs if (getattr(l, "escalation_count", 0) or 0) > 0]

    # Rankings e distribuição.
    advertiser_counter = Counter()
    advertiser_value = defaultdict(int)
    for b in identified_market:
        name = getattr(b, "advertiser_name", None) or "Sem anunciante"
        advertiser_counter[name] += 1
        advertiser_value[name] += _money(getattr(b, "estimated_value", 0))

    portal_counter = Counter()
    portal_value = defaultdict(int)
    for b in market_items:
        portal = getattr(b, "source_name", None) or _host_from_url(getattr(b, "page_url", None)) or "Sem portal"
        portal_counter[portal] += 1
        portal_value[portal] += _money(getattr(b, "estimated_value", 0))

    editorial_source_counter = Counter((getattr(i, "source_name", None) or "Sem fonte") for i in items)
    topic_counter = Counter((getattr(i, "topic", None) or "Sem tema") for i in items)
    sentiment_counter = Counter((getattr(i, "sentiment", None) or "neutro") for i in items)
    alert_severity_counter = Counter((getattr(l, "severity", None) or "informativo") for l in logs)
    alert_channel_counter = Counter((getattr(l, "channel", None) or "painel") for l in logs)
    alert_owner_counter = Counter((getattr(l, "assigned_to", None) or "Sem responsável") for l in active_alerts)

    timeline_days = sorted({(since + timedelta(days=i)).date() for i in range(days + 1)})[-14:]
    timeline = []
    item_day_counter = Counter(_day_key(i.created_at) for i in items if getattr(i, "created_at", None) and i.created_at >= since)
    banner_day_counter = Counter(_day_key(b.created_at) for b in banners if getattr(b, "created_at", None) and b.created_at >= since)
    alert_day_counter = Counter(_day_key(l.created_at) for l in logs if getattr(l, "created_at", None) and l.created_at >= since)
    # Usa display local para chaves consistentes.
    for day in timeline_days:
        fake_dt = datetime(day.year, day.month, day.day)
        key = _day_key(fake_dt)
        timeline.append({
            "date": key,
            "editorial": item_day_counter.get(key, 0),
            "banners": banner_day_counter.get(key, 0),
            "alerts": alert_day_counter.get(key, 0),
        })

    # Projetos por atividade.
    project_activity: dict[str, dict[str, Any]] = defaultdict(lambda: {"project_id": "", "project_name": "", "items": 0, "banners": 0, "alerts": 0, "investment": 0})
    for i in items:
        pid = str(i.project_id)
        project_activity[pid]["project_id"] = pid
        project_activity[pid]["project_name"] = name_map.get(pid, pid)
        project_activity[pid]["items"] += 1
    for b in market_items:
        pid = str(b.project_id)
        project_activity[pid]["project_id"] = pid
        project_activity[pid]["project_name"] = name_map.get(pid, pid)
        project_activity[pid]["banners"] += 1
        project_activity[pid]["investment"] += _money(getattr(b, "estimated_value", 0))
    for l in logs:
        pid = str(l.project_id)
        project_activity[pid]["project_id"] = pid
        project_activity[pid]["project_name"] = name_map.get(pid, pid)
        project_activity[pid]["alerts"] += 1

    project_rows = list(project_activity.values())
    for r in project_rows:
        r["score"] = _safe_int(r.get("items")) + _safe_int(r.get("banners")) + (_safe_int(r.get("alerts")) * 2)
    project_rows.sort(key=lambda r: (r.get("score", 0), r.get("investment", 0)), reverse=True)

    latest_critical = sorted(
        active_alerts,
        key=lambda l: (-_severity_value(getattr(l, "severity", None)), getattr(l, "created_at", None) or datetime.min),
        reverse=False,
    )[:8]

    provider_rows = db.query(NotificationProviderSetting).filter(NotificationProviderSetting.active == True).all()  # noqa: E712
    if project_uuid:
        provider_rows = [p for p in provider_rows if str(p.project_id) == str(project_uuid)]
    provider_counts = Counter(getattr(p, "provider_type", "unknown") for p in provider_rows)

    sources_total = source_query.count()
    linked_portals_total = project_portal_query.filter(ProjectPortal.active == True).count()  # noqa: E712

    selected_project = project_map.get(str(project_uuid)) if project_uuid else None

    return {
        "generated_at": display_local(now),
        "generated_at_iso": iso_local(now),
        "project_filter": str(project_uuid) if project_uuid else None,
        "project_name": getattr(selected_project, "name", None) if selected_project else "Todos os projetos",
        "period_days": days,
        "summary": {
            "projects_total": len(projects),
            "projects_active": len(active_projects),
            "sources_total": sources_total,
            "linked_portals_total": linked_portals_total,
            "editorial_items": len(items),
            "editorial_recent": len(recent_items),
            "banner_items": len(banners),
            "banner_recent": len(recent_banners),
            "market_items": len(market_items),
            "auditables": len(auditables),
            "review_items": len(review_items),
            "news_candidates": len(news_candidates),
            "preserved_evidence": len(preserved),
            "identified_market": len(identified_market),
            "pending_identification": len(pending_identification),
            "pending_identification_investment": pending_investment,
            "investment_total": investment_total,
            "alerts_total": len(logs),
            "alerts_recent": len(recent_logs),
            "alerts_active": len(active_alerts),
            "alerts_resolved": len(resolved_alerts),
            "alerts_overdue": len(overdue_alerts),
            "alerts_due_soon": len(due_soon_alerts),
            "alerts_unassigned": len(unassigned_alerts),
            "alerts_escalated": len(escalated_alerts),
            "alerts_sent": len(sent_alerts),
            "alerts_errors": len(errors_alerts),
            "alerts_dry_run": len(dry_run_alerts),
            "alerts_panel": len(painel_alerts),
            "automation_runs": len(automations),
        },
        "quality": {
            "identification_rate": round((len(identified_market) / len(market_items) * 100), 1) if market_items else 0.0,
            "auditable_rate": round((len(auditables) / len(banners) * 100), 1) if banners else 0.0,
            "preserved_rate": round((len(preserved) / len(banners) * 100), 1) if banners else 0.0,
            "sla_overdue_rate": round((len(overdue_alerts) / len(active_alerts) * 100), 1) if active_alerts else 0.0,
            "alert_resolution_rate": round((len(resolved_alerts) / len(logs) * 100), 1) if logs else 0.0,
            "notification_error_rate": round((len(errors_alerts) / len(logs) * 100), 1) if logs else 0.0,
        },
        "rankings": {
            "advertisers": [
                {"name": name, "count": count, "investment": advertiser_value.get(name, 0)}
                for name, count in advertiser_counter.most_common(8)
            ],
            "portals": [
                {"name": name, "count": count, "investment": portal_value.get(name, 0)}
                for name, count in portal_counter.most_common(8)
            ],
            "editorial_sources": _counter_list(editorial_source_counter, "source", 8),
            "topics": _counter_list(topic_counter, "topic", 8),
            "sentiments": _counter_list(sentiment_counter, "sentiment", 6),
            "alert_severity": _counter_list(alert_severity_counter, "severity", 6),
            "alert_channel": _counter_list(alert_channel_counter, "channel", 8),
            "alert_owner": _counter_list(alert_owner_counter, "owner", 8),
            "projects": project_rows[:10],
        },
        "timeline": timeline,
        "latest": {
            "items": [_serialize_item(i) for i in items[:8]],
            "banners": [_serialize_banner(b) for b in banners[:8]],
            "alerts": [_serialize_alert(l) for l in latest_critical],
            "automation_runs": [_serialize_automation(a) for a in automations[:8]],
        },
        "providers": {
            "email": provider_counts.get("email", 0),
            "sms": provider_counts.get("sms", 0),
            "whatsapp": provider_counts.get("whatsapp", 0),
            "webhook": provider_counts.get("webhook", 0),
        },
        "executive_reading": _executive_reading(
            investment_total=investment_total,
            pending_identification=len(pending_identification),
            auditables=len(auditables),
            items=len(items),
            alerts_active=len(active_alerts),
            overdue=len(overdue_alerts),
            errors=len(errors_alerts),
            projects=len(active_projects),
        ),
    }


def _host_from_url(url: str | None) -> str | None:
    if not url:
        return None
    try:
        from urllib.parse import urlparse
        return urlparse(url).netloc or url
    except Exception:
        return url


def _serialize_item(row: Item) -> dict:
    return {
        "id": str(row.id),
        "project_id": str(row.project_id),
        "title": row.title,
        "source_name": row.source_name,
        "topic": row.topic,
        "sentiment": row.sentiment,
        "url": row.url,
        "created_at": display_local(row.created_at),
    }


def _serialize_banner(row: BannerItem) -> dict:
    return {
        "id": str(row.id),
        "project_id": str(row.project_id),
        "advertiser_name": row.advertiser_name or "Pendente de identificação",
        "source_name": row.source_name or _host_from_url(row.page_url),
        "format": f"{row.width or 0} x {row.height or 0}",
        "estimated_value": _money(row.estimated_value),
        "checking_status": row.checking_status,
        "market_status": row.market_status,
        "created_at": display_local(row.created_at),
        "url": row.page_url,
    }


def _serialize_alert(row: NotificationLog) -> dict:
    return {
        "id": str(row.id),
        "project_id": str(row.project_id),
        "title": row.title,
        "severity": row.severity,
        "channel": row.channel,
        "status": row.status,
        "alert_status": row.alert_status,
        "assigned_to": row.assigned_to,
        "sla_due_at": display_local(row.sla_due_at),
        "created_at": display_local(row.created_at),
        "target_url": row.target_url,
    }


def _serialize_automation(row: NotificationAutomationRun) -> dict:
    return {
        "id": str(row.id),
        "project_id": str(row.project_id),
        "trigger_source": row.trigger_source,
        "status": row.status,
        "events_count": row.events_count,
        "notifications_count": row.notifications_count,
        "sent_count": row.sent_count,
        "error_count": row.error_count,
        "created_at": display_local(row.created_at),
        "message": row.message,
    }


def _executive_reading(
    investment_total: int,
    pending_identification: int,
    auditables: int,
    items: int,
    alerts_active: int,
    overdue: int,
    errors: int,
    projects: int,
) -> list[str]:
    lines: list[str] = []
    lines.append(f"A plataforma monitora {projects} projeto(s) ativo(s), consolidando publicidade, notícias, evidências e alertas operacionais.")
    if investment_total:
        lines.append(f"A inteligência de mercado acumula R$ {investment_total:,.0f} em investimento estimado no recorte atual.".replace(",", "."))
    if auditables:
        lines.append(f"Há {auditables} evidência(s) auditável(is) prontas para checking publicitário.")
    if items:
        lines.append(f"O módulo editorial possui {items} matéria(s)/menção(ões) monitorada(s).")
    if pending_identification:
        lines.append(f"Existem {pending_identification} item(ns) pendente(s) de identificação comercial; recomenda-se priorizar a fila de qualificação de marcas.")
    if alerts_active:
        lines.append(f"A operação possui {alerts_active} alerta(s) ativo(s) em acompanhamento.")
    if overdue:
        lines.append(f"Atenção: {overdue} alerta(s) estão com SLA vencido e exigem tratamento imediato.")
    if errors:
        lines.append(f"Foram detectados {errors} erro(s) de notificação; revisar provedores e canais configurados.")
    if not overdue and not errors:
        lines.append("A saúde operacional está adequada no recorte atual, sem SLA vencido ou erro crítico de notificação.")
    return lines
