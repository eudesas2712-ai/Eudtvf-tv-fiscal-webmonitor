
## backend/app/routers/alerts.py
GET    /summary/{project_id}
GET    /summary/{project_id}/export.csv

## backend/app/routers/auth.py
POST   /login
GET    /me
POST   /bootstrap-admin
GET    /roles
GET    /permissions-matrix
GET    /my-access
GET    /users
POST   /users
PUT    /users/{user_id}
POST   /users/{user_id}/reset-password
DELETE /users/{user_id}
DELETE /users/{user_id}/purge
GET    /projects-summary
GET    /audit

## backend/app/routers/banners.py
POST   /scan/{project_id}
GET    /{project_id}
GET    /item/{banner_id}
GET    /report/{project_id}
GET    /report-pdf/{project_id}

## backend/app/routers/editorial.py
GET    /summary/{project_id}
GET    /items/{project_id}
POST   /run/{project_id}
POST   /reclassify/{project_id}
GET    /report/{project_id}
GET    /report-pdf/{project_id}
GET    /report-synthetic-pdf/{project_id}
GET    /report-sintetico-pdf/{project_id}
GET    /report-analytical-pdf/{project_id}
GET    /report-analitico-pdf/{project_id}
DELETE /clear/{project_id}

## backend/app/routers/executive_dashboard.py
GET    /dashboard

## backend/app/routers/identification.py
GET    /pending/{project_id}
GET    /pending/{project_id}/export.csv
GET    /quality/{project_id}
GET    /actions/{project_id}/export.csv
GET    /actions/{project_id}
POST   /qualify/{project_id}
POST   /ignore/{project_id}
POST   /reprocess-aliases/{project_id}
POST   /auto-run/{project_id}

## backend/app/routers/ingest.py
POST   /run/{project_id}

## backend/app/routers/intel.py
GET    /{project_id}

## backend/app/routers/intel_compare.py
GET    /{project_id}
GET    /report/pdf/{project_id}
GET    /report/pptx/{project_id}

## backend/app/routers/items.py
GET    /{project_id}
GET    /report/{project_id}
GET    /report-pdf/{project_id}
DELETE /clear/{project_id}

## backend/app/routers/maintenance.py
GET    /status
POST   /backup
GET    /backups
GET    /backups/{filename}
DELETE /backups/{filename}
POST   /cleanup
GET    /backup-freshness
GET    /auto-backup/status
POST   /auto-backup/run
POST   /archive-notification-errors
POST   /archive-homologation-errors
GET    /security-export.csv

## backend/app/routers/market_intelligence.py
GET    /summary/{project_id}
GET    /report/pdf/{project_id}
GET    /report/pptx/{project_id}
GET    /timeline/{project_id}
GET    /trends/{project_id}

## backend/app/routers/notifications.py
GET    /config
GET    /provider-status
GET    /dashboard/{project_id}
GET    /provider-settings/{project_id}
POST   /provider-settings/{project_id}/email-smtp
DELETE /provider-settings/{project_id}/email-smtp
POST   /provider-settings/{project_id}/sms
DELETE /provider-settings/{project_id}/sms
POST   /provider-settings/{project_id}/whatsapp
DELETE /provider-settings/{project_id}/whatsapp
GET    /contacts/{project_id}
POST   /contacts/{project_id}
PUT    /contacts/{project_id}/{contact_id}
DELETE /contacts/{contact_id}
GET    /rules/{project_id}
POST   /rules/{project_id}
PUT    /rules/{project_id}/{rule_id}
DELETE /rules/{rule_id}
POST   /bootstrap/{project_id}
POST   /cleanup/{project_id}
POST   /evaluate/{project_id}
POST   /test/{project_id}
POST   /test-real-email/{project_id}
POST   /test-real-sms/{project_id}
POST   /test-real-whatsapp/{project_id}
POST   /test-automatic-email/{project_id}
POST   /test-automatic-sms/{project_id}
POST   /test-automatic-whatsapp/{project_id}
POST   /automation-test/{project_id}
GET    /automation-runs/{project_id}
GET    /inbox/{project_id}
GET    /sla/{project_id}
POST   /sla/evaluate/{project_id}
POST   /logs/{log_id}/assign
POST   /logs/{log_id}/ack
POST   /logs/{log_id}/resolve
POST   /logs/{log_id}/snooze
POST   /logs/{log_id}/reopen
POST   /logs/{project_id}/bulk-status
GET    /reports/alerts/{project_id}
GET    /reports/alerts/{project_id}/export.csv
GET    /reports/alerts/{project_id}/pdf
GET    /reports/alerts/{project_id}/pptx
GET    /logs/{project_id}
GET    /logs/{project_id}/export.csv

## backend/app/routers/project_reports.py
GET    /summary/{project_id}
GET    /pdf/{project_id}
GET    /pptx/{project_id}

## backend/app/routers/projects.py
GET    /intel-options/

## backend/app/routers/registry.py
GET    /segments
POST   /segments
GET    /advertisers
POST   /advertisers
POST   /advertisers/{advertiser_id}/aliases
GET    /portals
POST   /portals
GET    /projects
POST   /projects
PUT    /projects/{project_id}
POST   /projects/{project_id}/active
POST   /projects/{project_id}/portals
POST   /projects/{project_id}/advertisers
GET    /projects/{project_id}/config
POST   /bootstrap-defaults
POST   /projects/{project_id}/bootstrap-portals

## backend/app/routers/scheduler_admin.py
GET    /status
POST   /run-now
POST   /enable
POST   /run-portal-scan-now
POST   /disable
GET    /history
DELETE /history
GET    /history/export.csv

## backend/app/routers/sources.py
POST   /bootstrap/{project_id}
GET    /{project_id}

## backend/app/routers/system_health.py
GET    /advanced
POST   /check
GET    /history
GET    /history/export.csv
GET    /report.pdf
GET    /uptime
GET    /ready
GET    /live

## backend/app/routers/terms.py
POST   /bootstrap/{project_id}
GET    /{project_id}
