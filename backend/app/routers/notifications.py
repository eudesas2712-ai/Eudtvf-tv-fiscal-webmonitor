from __future__ import annotations

import csv
import io

from fastapi import APIRouter, Depends, Query, Request
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session

from app.core.admin_auth import require_admin_access
from app.db.session import get_db
from app.services.notification_service import (
    bootstrap_default_rules,
    cleanup_notification_duplicates,
    deactivate_contact,
    deactivate_rule,
    evaluate_notification_rules,
    evaluate_automatic_notification_rules,
    list_contacts,
    list_logs,
    list_automation_runs,
    list_notification_inbox,
    list_sla_dashboard,
    assign_notification_log,
    evaluate_sla_escalations,
    update_notification_log_status,
    bulk_update_notification_logs,
    list_rules,
    notification_config,
    notification_dashboard,
    provider_status,
    send_test_notification,
    send_real_email_test,
    send_real_sms_test,
    send_real_whatsapp_test,
    send_automatic_email_test,
    send_automatic_sms_test,
    send_automatic_whatsapp_test,
    get_provider_settings,
    upsert_email_smtp_setting,
    deactivate_email_smtp_setting,
    upsert_sms_setting,
    deactivate_sms_setting,
    upsert_whatsapp_setting,
    deactivate_whatsapp_setting,
    upsert_contact,
    upsert_rule,
)

from app.services.notification_report_service import (
    alerts_report_csv,
    build_alerts_management_report,
    generate_alerts_report_pdf,
    generate_alerts_report_pptx,
)

router = APIRouter(prefix="/notifications", tags=["Notifications"])


@router.get("/config")
def config():
    return notification_config()


@router.get("/provider-status")
def providers():
    return provider_status()


@router.get("/dashboard/{project_id}")
def dashboard(project_id: str, db: Session = Depends(get_db)):
    return notification_dashboard(db, project_id)


@router.get("/provider-settings/{project_id}")
def provider_settings(project_id: str, db: Session = Depends(get_db)):
    return get_provider_settings(db, project_id)


@router.post("/provider-settings/{project_id}/email-smtp")
def save_email_smtp(project_id: str, payload: dict, request: Request, db: Session = Depends(get_db)):
    require_admin_access(request)
    return upsert_email_smtp_setting(db, project_id, payload)


@router.delete("/provider-settings/{project_id}/email-smtp")
def disable_email_smtp(project_id: str, request: Request, db: Session = Depends(get_db)):
    require_admin_access(request)
    return deactivate_email_smtp_setting(db, project_id)


@router.post("/provider-settings/{project_id}/sms")
def save_sms_provider(project_id: str, payload: dict, request: Request, db: Session = Depends(get_db)):
    require_admin_access(request)
    return upsert_sms_setting(db, project_id, payload)


@router.delete("/provider-settings/{project_id}/sms")
def disable_sms_provider(project_id: str, request: Request, db: Session = Depends(get_db)):
    require_admin_access(request)
    return deactivate_sms_setting(db, project_id)


@router.post("/provider-settings/{project_id}/whatsapp")
def save_whatsapp_provider(project_id: str, payload: dict, request: Request, db: Session = Depends(get_db)):
    require_admin_access(request)
    return upsert_whatsapp_setting(db, project_id, payload)


@router.delete("/provider-settings/{project_id}/whatsapp")
def disable_whatsapp_provider(project_id: str, request: Request, db: Session = Depends(get_db)):
    require_admin_access(request)
    return deactivate_whatsapp_setting(db, project_id)


@router.get("/contacts/{project_id}")
def contacts(project_id: str, active_only: bool = Query(default=False), db: Session = Depends(get_db)):
    return {"project_id": project_id, "contacts": list_contacts(db, project_id, active_only=active_only)}


@router.post("/contacts/{project_id}")
def create_contact(project_id: str, payload: dict, request: Request, db: Session = Depends(get_db)):
    require_admin_access(request)
    return upsert_contact(db, project_id, payload)


@router.put("/contacts/{project_id}/{contact_id}")
def update_contact(project_id: str, contact_id: str, payload: dict, request: Request, db: Session = Depends(get_db)):
    require_admin_access(request)
    return upsert_contact(db, project_id, payload, contact_id=contact_id)


@router.delete("/contacts/{contact_id}")
def delete_contact(contact_id: str, request: Request, db: Session = Depends(get_db)):
    require_admin_access(request)
    return deactivate_contact(db, contact_id)


@router.get("/rules/{project_id}")
def rules(project_id: str, active_only: bool = Query(default=False), db: Session = Depends(get_db)):
    return {"project_id": project_id, "rules": list_rules(db, project_id, active_only=active_only)}


@router.post("/rules/{project_id}")
def create_rule(project_id: str, payload: dict, request: Request, db: Session = Depends(get_db)):
    require_admin_access(request)
    return upsert_rule(db, project_id, payload)


@router.put("/rules/{project_id}/{rule_id}")
def update_rule(project_id: str, rule_id: str, payload: dict, request: Request, db: Session = Depends(get_db)):
    require_admin_access(request)
    return upsert_rule(db, project_id, payload, rule_id=rule_id)


@router.delete("/rules/{rule_id}")
def delete_rule(rule_id: str, request: Request, db: Session = Depends(get_db)):
    require_admin_access(request)
    return deactivate_rule(db, rule_id)


@router.post("/bootstrap/{project_id}")
def bootstrap(project_id: str, request: Request, db: Session = Depends(get_db)):
    require_admin_access(request)
    return bootstrap_default_rules(db, project_id)


@router.post("/cleanup/{project_id}")
def cleanup(project_id: str, request: Request, db: Session = Depends(get_db)):
    require_admin_access(request)
    return cleanup_notification_duplicates(db, project_id)


@router.post("/evaluate/{project_id}")
def evaluate(project_id: str, request: Request, source: str = Query(default="manual"), event_limit: int = Query(default=80, ge=10, le=300), db: Session = Depends(get_db)):
    require_admin_access(request)
    return evaluate_notification_rules(db, project_id, source=source, event_limit=event_limit)


@router.post("/test/{project_id}")
def test(project_id: str, payload: dict, request: Request, db: Session = Depends(get_db)):
    require_admin_access(request)
    return send_test_notification(db, project_id, payload)


@router.post("/test-real-email/{project_id}")
def test_real_email(project_id: str, payload: dict, request: Request, db: Session = Depends(get_db)):
    require_admin_access(request)
    return send_real_email_test(db, project_id, payload)


@router.post("/test-real-sms/{project_id}")
def test_real_sms(project_id: str, payload: dict, request: Request, db: Session = Depends(get_db)):
    require_admin_access(request)
    return send_real_sms_test(db, project_id, payload)


@router.post("/test-real-whatsapp/{project_id}")
def test_real_whatsapp(project_id: str, payload: dict, request: Request, db: Session = Depends(get_db)):
    require_admin_access(request)
    return send_real_whatsapp_test(db, project_id, payload)


@router.post("/test-automatic-email/{project_id}")
def test_automatic_email(project_id: str, payload: dict, request: Request, db: Session = Depends(get_db)):
    require_admin_access(request)
    return send_automatic_email_test(db, project_id, payload)


@router.post("/test-automatic-sms/{project_id}")
def test_automatic_sms(project_id: str, payload: dict, request: Request, db: Session = Depends(get_db)):
    require_admin_access(request)
    return send_automatic_sms_test(db, project_id, payload)


@router.post("/test-automatic-whatsapp/{project_id}")
def test_automatic_whatsapp(project_id: str, payload: dict, request: Request, db: Session = Depends(get_db)):
    require_admin_access(request)
    return send_automatic_whatsapp_test(db, project_id, payload)




@router.post("/automation-test/{project_id}")
def automation_test(project_id: str, request: Request, source: str = Query(default="manual_automation_test"), event_limit: int = Query(default=120, ge=10, le=500), window_minutes: int = Query(default=180, ge=1, le=10080), db: Session = Depends(get_db)):
    require_admin_access(request)
    return evaluate_automatic_notification_rules(db, project_id, trigger_source=source, event_limit=event_limit, window_minutes=window_minutes)


@router.get("/automation-runs/{project_id}")
def automation_runs(project_id: str, limit: int = Query(default=30, ge=1, le=200), db: Session = Depends(get_db)):
    return {"project_id": project_id, "items": list_automation_runs(db, project_id, limit=limit)}




@router.get("/inbox/{project_id}")
def inbox(project_id: str, status: str | None = Query(default="aberto"), severity: str | None = Query(default=None), channel: str | None = Query(default=None), limit: int = Query(default=150, ge=1, le=1000), db: Session = Depends(get_db)):
    return list_notification_inbox(db, project_id, status=status, severity=severity, channel=channel, limit=limit)


@router.get("/sla/{project_id}")
def sla_dashboard(project_id: str, limit: int = Query(default=200, ge=1, le=1000), db: Session = Depends(get_db)):
    return list_sla_dashboard(db, project_id, limit=limit)


@router.post("/sla/evaluate/{project_id}")
def sla_evaluate(project_id: str, payload: dict, request: Request, db: Session = Depends(get_db)):
    require_admin_access(request)
    return evaluate_sla_escalations(db, project_id, payload)


@router.post("/logs/{log_id}/assign")
def assign_log(log_id: str, payload: dict, request: Request, db: Session = Depends(get_db)):
    require_admin_access(request)
    return assign_notification_log(db, log_id, payload)


@router.post("/logs/{log_id}/ack")
def ack_log(log_id: str, payload: dict, request: Request, db: Session = Depends(get_db)):
    require_admin_access(request)
    return update_notification_log_status(db, log_id, "ack", payload)


@router.post("/logs/{log_id}/resolve")
def resolve_log(log_id: str, payload: dict, request: Request, db: Session = Depends(get_db)):
    require_admin_access(request)
    return update_notification_log_status(db, log_id, "resolve", payload)


@router.post("/logs/{log_id}/snooze")
def snooze_log(log_id: str, payload: dict, request: Request, db: Session = Depends(get_db)):
    require_admin_access(request)
    return update_notification_log_status(db, log_id, "snooze", payload)


@router.post("/logs/{log_id}/reopen")
def reopen_log(log_id: str, payload: dict, request: Request, db: Session = Depends(get_db)):
    require_admin_access(request)
    return update_notification_log_status(db, log_id, "reopen", payload)


@router.post("/logs/{project_id}/bulk-status")
def bulk_log_status(project_id: str, payload: dict, request: Request, db: Session = Depends(get_db)):
    require_admin_access(request)
    return bulk_update_notification_logs(db, project_id, payload.get("action") or "ack", payload)


@router.get("/reports/alerts/{project_id}")
def alerts_management_report(project_id: str, start_date: str | None = Query(default=None), end_date: str | None = Query(default=None), db: Session = Depends(get_db)):
    return build_alerts_management_report(db, project_id, start_date=start_date, end_date=end_date)


@router.get("/reports/alerts/{project_id}/export.csv")
def alerts_management_report_csv(project_id: str, start_date: str | None = Query(default=None), end_date: str | None = Query(default=None), db: Session = Depends(get_db)):
    report = build_alerts_management_report(db, project_id, start_date=start_date, end_date=end_date, limit=10000)
    content = alerts_report_csv(report)
    return StreamingResponse(
        iter([content]),
        media_type="text/csv",
        headers={"Content-Disposition": f"attachment; filename=relatorio_alertas_sla_{project_id}.csv"},
    )


@router.get("/reports/alerts/{project_id}/pdf")
def alerts_management_report_pdf(project_id: str, start_date: str | None = Query(default=None), end_date: str | None = Query(default=None), db: Session = Depends(get_db)):
    report = build_alerts_management_report(db, project_id, start_date=start_date, end_date=end_date, limit=10000)
    content = generate_alerts_report_pdf(report)
    return StreamingResponse(
        io.BytesIO(content),
        media_type="application/pdf",
        headers={"Content-Disposition": f"attachment; filename=relatorio_alertas_sla_{project_id}.pdf"},
    )


@router.get("/reports/alerts/{project_id}/pptx")
def alerts_management_report_pptx(project_id: str, start_date: str | None = Query(default=None), end_date: str | None = Query(default=None), db: Session = Depends(get_db)):
    report = build_alerts_management_report(db, project_id, start_date=start_date, end_date=end_date, limit=10000)
    content = generate_alerts_report_pptx(report)
    return StreamingResponse(
        io.BytesIO(content),
        media_type="application/vnd.openxmlformats-officedocument.presentationml.presentation",
        headers={"Content-Disposition": f"attachment; filename=relatorio_alertas_sla_{project_id}.pptx"},
    )


@router.get("/logs/{project_id}")
def logs(project_id: str, limit: int = Query(default=100, ge=1, le=1000), status: str | None = Query(default=None), channel: str | None = Query(default=None), db: Session = Depends(get_db)):
    return {"project_id": project_id, "logs": list_logs(db, project_id, limit=limit, status=status, channel=channel)}


@router.get("/logs/{project_id}/export.csv")
def export_logs(project_id: str, db: Session = Depends(get_db)):
    rows = list_logs(db, project_id, limit=2000)
    output = io.StringIO()
    writer = csv.writer(output, delimiter=";")
    writer.writerow(["Data", "Canal", "Status", "Severidade", "Categoria", "Título", "Mensagem", "URL", "Provider", "Resposta"])
    for row in rows:
        writer.writerow([
            row.get("created_at_display") or row.get("created_at", ""),
            row.get("channel", ""),
            row.get("status", ""),
            row.get("severity", ""),
            row.get("category", ""),
            row.get("title", ""),
            row.get("message", ""),
            row.get("target_url", ""),
            row.get("provider", ""),
            row.get("provider_response", ""),
        ])
    output.seek(0)
    return StreamingResponse(
        iter([output.getvalue()]),
        media_type="text/csv",
        headers={"Content-Disposition": f"attachment; filename=notificacoes_{project_id}.csv"},
    )
