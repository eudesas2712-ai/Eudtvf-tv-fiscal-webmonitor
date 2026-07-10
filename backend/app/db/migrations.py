from sqlalchemy import text


def ensure_banner_classification_columns(engine) -> None:
    """Adiciona colunas novas sem depender de Alembic.

    O projeto atual usa Base.metadata.create_all(), que cria tabelas novas,
    mas não altera tabelas existentes. Estas instruções são idempotentes.
    """

    statements = [
        "ALTER TABLE banner_items ADD COLUMN IF NOT EXISTS content_type VARCHAR(50)",
        "ALTER TABLE banner_items ADD COLUMN IF NOT EXISTS checking_status VARCHAR(50)",
        "ALTER TABLE banner_items ADD COLUMN IF NOT EXISTS market_status VARCHAR(50)",
        "ALTER TABLE banner_items ADD COLUMN IF NOT EXISTS news_status VARCHAR(50)",
        "ALTER TABLE banner_items ADD COLUMN IF NOT EXISTS publicity_score INTEGER",
        "ALTER TABLE banner_items ADD COLUMN IF NOT EXISTS news_score INTEGER",
        "ALTER TABLE banner_items ADD COLUMN IF NOT EXISTS market_score INTEGER",
        "ALTER TABLE banner_items ADD COLUMN IF NOT EXISTS has_preserved_evidence BOOLEAN DEFAULT FALSE",
        "ALTER TABLE banner_items ADD COLUMN IF NOT EXISTS evidence_type VARCHAR(50)",
    ]

    with engine.begin() as conn:
        for statement in statements:
            conn.execute(text(statement))


def ensure_project_management_columns(engine) -> None:
    """Adiciona campos de gestão operacional de projetos sem Alembic."""

    statements = [
        "ALTER TABLE projects ADD COLUMN IF NOT EXISTS client_name VARCHAR(255)",
        "ALTER TABLE projects ADD COLUMN IF NOT EXISTS segment_id UUID",
        "ALTER TABLE projects ADD COLUMN IF NOT EXISTS active BOOLEAN DEFAULT TRUE",
        "ALTER TABLE projects ADD COLUMN IF NOT EXISTS monitor_publicity BOOLEAN DEFAULT TRUE",
        "ALTER TABLE projects ADD COLUMN IF NOT EXISTS monitor_editorial BOOLEAN DEFAULT TRUE",
        "ALTER TABLE projects ADD COLUMN IF NOT EXISTS monitor_market BOOLEAN DEFAULT TRUE",
        "ALTER TABLE projects ADD COLUMN IF NOT EXISTS monitor_checking BOOLEAN DEFAULT TRUE",
        "ALTER TABLE projects ADD COLUMN IF NOT EXISTS updated_at TIMESTAMP DEFAULT NOW()",
    ]

    with engine.begin() as conn:
        for statement in statements:
            conn.execute(text(statement))


def ensure_editorial_item_columns(engine) -> None:
    """Adiciona campos do módulo editorial/notícias sem depender de Alembic."""

    statements = [
        "ALTER TABLE items ADD COLUMN IF NOT EXISTS source_name VARCHAR(255)",
        "ALTER TABLE items ADD COLUMN IF NOT EXISTS summary TEXT",
        "ALTER TABLE items ADD COLUMN IF NOT EXISTS sentiment VARCHAR(50)",
        "ALTER TABLE items ADD COLUMN IF NOT EXISTS sentiment_score INTEGER",
        "ALTER TABLE items ADD COLUMN IF NOT EXISTS topic VARCHAR(120)",
        "ALTER TABLE items ADD COLUMN IF NOT EXISTS editorial_score INTEGER",
        "ALTER TABLE items ADD COLUMN IF NOT EXISTS published_at TIMESTAMP",
    ]

    with engine.begin() as conn:
        for statement in statements:
            conn.execute(text(statement))


def ensure_identification_review_columns(engine) -> None:
    """Adiciona campos da fila de qualificação de anunciantes sem Alembic."""

    statements = [
        "ALTER TABLE banner_items ADD COLUMN IF NOT EXISTS identification_status VARCHAR(50)",
        "ALTER TABLE banner_items ADD COLUMN IF NOT EXISTS identification_note TEXT",
        "ALTER TABLE banner_items ADD COLUMN IF NOT EXISTS qualified_advertiser_id UUID",
        "ALTER TABLE banner_items ADD COLUMN IF NOT EXISTS qualified_at TIMESTAMP",
    ]

    with engine.begin() as conn:
        for statement in statements:
            conn.execute(text(statement))


def ensure_notification_tables(engine) -> None:
    """Cria tabelas do motor de notificações sem depender de Alembic."""

    statements = [
        """
        CREATE TABLE IF NOT EXISTS notification_contacts (
            id UUID PRIMARY KEY,
            project_id UUID NOT NULL,
            name VARCHAR(255) NOT NULL,
            role VARCHAR(120),
            email VARCHAR(255),
            phone VARCHAR(80),
            whatsapp VARCHAR(80),
            channels JSONB DEFAULT '[]'::jsonb,
            priority VARCHAR(50) DEFAULT 'normal',
            active BOOLEAN DEFAULT TRUE,
            created_at TIMESTAMP DEFAULT NOW(),
            updated_at TIMESTAMP DEFAULT NOW()
        )
        """,
        """
        CREATE TABLE IF NOT EXISTS notification_rules (
            id UUID PRIMARY KEY,
            project_id UUID NOT NULL,
            name VARCHAR(255) NOT NULL,
            active BOOLEAN DEFAULT TRUE,
            event_type VARCHAR(80) DEFAULT 'any',
            terms JSONB DEFAULT '[]'::jsonb,
            categories JSONB DEFAULT '[]'::jsonb,
            channels JSONB DEFAULT '[]'::jsonb,
            contact_ids JSONB DEFAULT '[]'::jsonb,
            severity_min VARCHAR(50) DEFAULT 'alto',
            sentiment_filter VARCHAR(50),
            cooldown_minutes INTEGER DEFAULT 60,
            last_triggered_at TIMESTAMP,
            created_at TIMESTAMP DEFAULT NOW(),
            updated_at TIMESTAMP DEFAULT NOW()
        )
        """,
        """
        CREATE TABLE IF NOT EXISTS notification_logs (
            id UUID PRIMARY KEY,
            project_id UUID NOT NULL,
            rule_id UUID,
            contact_id UUID,
            event_type VARCHAR(80),
            severity VARCHAR(50),
            category VARCHAR(80),
            channel VARCHAR(50) NOT NULL,
            status VARCHAR(50) DEFAULT 'queued',
            provider VARCHAR(80),
            title VARCHAR(500),
            message TEXT,
            target_url VARCHAR(2048),
            provider_response TEXT,
            alert_status VARCHAR(50) DEFAULT 'aberto',
            acknowledged_at TIMESTAMP,
            acknowledged_by VARCHAR(255),
            resolved_at TIMESTAMP,
            resolved_by VARCHAR(255),
            resolution_note TEXT,
            snoozed_until TIMESTAMP,
            created_at TIMESTAMP DEFAULT NOW()
        )
        """,
        "CREATE INDEX IF NOT EXISTS ix_notification_contacts_project ON notification_contacts(project_id)",
        "CREATE INDEX IF NOT EXISTS ix_notification_rules_project ON notification_rules(project_id)",
        "CREATE INDEX IF NOT EXISTS ix_notification_logs_project_created ON notification_logs(project_id, created_at DESC)",
        "ALTER TABLE notification_logs ADD COLUMN IF NOT EXISTS alert_status VARCHAR(50) DEFAULT 'aberto'",
        "ALTER TABLE notification_logs ADD COLUMN IF NOT EXISTS acknowledged_at TIMESTAMP",
        "ALTER TABLE notification_logs ADD COLUMN IF NOT EXISTS acknowledged_by VARCHAR(255)",
        "ALTER TABLE notification_logs ADD COLUMN IF NOT EXISTS resolved_at TIMESTAMP",
        "ALTER TABLE notification_logs ADD COLUMN IF NOT EXISTS resolved_by VARCHAR(255)",
        "ALTER TABLE notification_logs ADD COLUMN IF NOT EXISTS resolution_note TEXT",
        "ALTER TABLE notification_logs ADD COLUMN IF NOT EXISTS snoozed_until TIMESTAMP",
        "CREATE INDEX IF NOT EXISTS ix_notification_logs_project_status ON notification_logs(project_id, alert_status, created_at DESC)",
    ]

    with engine.begin() as conn:
        for statement in statements:
            conn.execute(text(statement))


def ensure_notification_provider_settings(engine) -> None:
    """Cria a tabela de perfis de provedores do motor de notificações."""

    statements = [
        """
        CREATE TABLE IF NOT EXISTS notification_provider_settings (
            id UUID PRIMARY KEY,
            project_id UUID NOT NULL,
            provider_type VARCHAR(50) NOT NULL,
            provider_name VARCHAR(80) NOT NULL,
            active BOOLEAN DEFAULT TRUE,
            config JSONB DEFAULT '{}'::jsonb,
            created_at TIMESTAMP DEFAULT NOW(),
            updated_at TIMESTAMP DEFAULT NOW()
        )
        """,
        "CREATE INDEX IF NOT EXISTS ix_notification_provider_settings_project ON notification_provider_settings(project_id, provider_type, active)",
    ]
    with engine.begin() as conn:
        for statement in statements:
            conn.execute(text(statement))

def ensure_notification_automation_runs(engine) -> None:
    """Registra execuções automáticas do motor de notificações."""

    statements = [
        """
        CREATE TABLE IF NOT EXISTS notification_automation_runs (
            id UUID PRIMARY KEY,
            project_id UUID NOT NULL,
            trigger_source VARCHAR(80) NOT NULL,
            status VARCHAR(50) DEFAULT 'success',
            rules_count INTEGER DEFAULT 0,
            events_count INTEGER DEFAULT 0,
            notifications_count INTEGER DEFAULT 0,
            sent_count INTEGER DEFAULT 0,
            registered_count INTEGER DEFAULT 0,
            dry_run_count INTEGER DEFAULT 0,
            error_count INTEGER DEFAULT 0,
            skipped_duplicates INTEGER DEFAULT 0,
            message TEXT,
            created_at TIMESTAMP DEFAULT NOW()
        )
        """,
        "CREATE INDEX IF NOT EXISTS ix_notification_automation_runs_project_created ON notification_automation_runs(project_id, created_at DESC)",
    ]
    with engine.begin() as conn:
        for statement in statements:
            conn.execute(text(statement))



def ensure_notification_sla_columns(engine) -> None:
    """Adiciona campos de SLA/escalonamento para alertas operacionais."""

    statements = [
        "ALTER TABLE notification_logs ADD COLUMN IF NOT EXISTS assigned_to VARCHAR(255)",
        "ALTER TABLE notification_logs ADD COLUMN IF NOT EXISTS sla_minutes INTEGER",
        "ALTER TABLE notification_logs ADD COLUMN IF NOT EXISTS sla_due_at TIMESTAMP",
        "ALTER TABLE notification_logs ADD COLUMN IF NOT EXISTS escalation_level INTEGER DEFAULT 0",
        "ALTER TABLE notification_logs ADD COLUMN IF NOT EXISTS escalation_count INTEGER DEFAULT 0",
        "ALTER TABLE notification_logs ADD COLUMN IF NOT EXISTS escalated_at TIMESTAMP",
        "ALTER TABLE notification_logs ADD COLUMN IF NOT EXISTS last_escalation_note TEXT",
        "CREATE INDEX IF NOT EXISTS ix_notification_logs_sla ON notification_logs(project_id, alert_status, sla_due_at)",
        "CREATE INDEX IF NOT EXISTS ix_notification_logs_assigned ON notification_logs(project_id, assigned_to, alert_status)",
    ]
    with engine.begin() as conn:
        for statement in statements:
            conn.execute(text(statement))

def ensure_system_health_tables(engine) -> None:
    """Cria histórico operacional de saúde/uptime sem depender de Alembic."""

    statements = [
        "CREATE EXTENSION IF NOT EXISTS pgcrypto",
        """
        CREATE TABLE IF NOT EXISTS system_health_checks (
            id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
            service VARCHAR(80) NOT NULL,
            status VARCHAR(50) NOT NULL,
            latency_ms INTEGER,
            message TEXT,
            details JSONB DEFAULT '{}'::jsonb,
            trigger_source VARCHAR(80) DEFAULT 'manual',
            created_at TIMESTAMP DEFAULT NOW()
        )
        """,
        "CREATE INDEX IF NOT EXISTS ix_system_health_checks_created ON system_health_checks(created_at DESC)",
        "CREATE INDEX IF NOT EXISTS ix_system_health_checks_service_status ON system_health_checks(service, status, created_at DESC)",
    ]
    with engine.begin() as conn:
        for statement in statements:
            conn.execute(text(statement))



def ensure_maintenance_v40_columns(engine) -> None:
    """Campos de saneamento operacional V40 para logs de notificação."""

    statements = [
        "ALTER TABLE notification_logs ADD COLUMN IF NOT EXISTS archived_at TIMESTAMP",
        "ALTER TABLE notification_logs ADD COLUMN IF NOT EXISTS archived_by VARCHAR(255)",
        "ALTER TABLE notification_logs ADD COLUMN IF NOT EXISTS archive_reason TEXT",
        "CREATE INDEX IF NOT EXISTS ix_notification_logs_archive ON notification_logs(project_id, status, archived_at, created_at DESC)",
    ]
    with engine.begin() as conn:
        for statement in statements:
            conn.execute(text(statement))


def ensure_user_access_tables(engine) -> None:
    """Cria tabelas de usuários, perfis e auditoria de acesso sem depender de Alembic."""

    statements = [
        "CREATE EXTENSION IF NOT EXISTS pgcrypto",
        """
        CREATE TABLE IF NOT EXISTS app_users (
            id UUID PRIMARY KEY,
            name VARCHAR(255) NOT NULL,
            email VARCHAR(255) NOT NULL UNIQUE,
            password_hash TEXT NOT NULL,
            role VARCHAR(80) NOT NULL DEFAULT 'cliente',
            active BOOLEAN DEFAULT TRUE,
            project_ids JSONB DEFAULT '[]'::jsonb,
            allowed_modules JSONB DEFAULT '[]'::jsonb,
            last_login_at TIMESTAMP,
            created_at TIMESTAMP DEFAULT NOW(),
            updated_at TIMESTAMP DEFAULT NOW()
        )
        """,
        """
        CREATE TABLE IF NOT EXISTS auth_audit_logs (
            id UUID PRIMARY KEY,
            user_id UUID,
            action VARCHAR(120) NOT NULL,
            status VARCHAR(50) NOT NULL,
            ip_address VARCHAR(120),
            user_agent TEXT,
            detail TEXT,
            created_at TIMESTAMP DEFAULT NOW()
        )
        """,
        "CREATE INDEX IF NOT EXISTS ix_app_users_email ON app_users(email)",
        "CREATE INDEX IF NOT EXISTS ix_app_users_role_active ON app_users(role, active)",
        "CREATE INDEX IF NOT EXISTS ix_auth_audit_logs_created ON auth_audit_logs(created_at DESC)",
        "CREATE INDEX IF NOT EXISTS ix_auth_audit_logs_user ON auth_audit_logs(user_id, created_at DESC)",
    ]

    with engine.begin() as conn:
        for statement in statements:
            conn.execute(text(statement))

def ensure_generated_reports_table(engine) -> None:
    """Cria histórico de relatórios gerados e armazenados no MinIO."""
    statements = [
        "CREATE EXTENSION IF NOT EXISTS pgcrypto",
        """
        CREATE TABLE IF NOT EXISTS generated_reports (
            id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
            project_id UUID NOT NULL,
            report_family VARCHAR(80) NOT NULL,
            report_type VARCHAR(120) NOT NULL,
            title VARCHAR(255),
            filename VARCHAR(500) NOT NULL,
            object_key VARCHAR(1024) NOT NULL,
            public_url VARCHAR(2048),
            content_type VARCHAR(120) DEFAULT 'application/pdf',
            filters JSONB DEFAULT '{}'::jsonb,
            file_size INTEGER,
            generated_by VARCHAR(255),
            created_at TIMESTAMP DEFAULT NOW()
        )
        """,
        "CREATE INDEX IF NOT EXISTS ix_generated_reports_project_created ON generated_reports(project_id, created_at DESC)",
        "CREATE INDEX IF NOT EXISTS ix_generated_reports_family_type ON generated_reports(project_id, report_family, report_type, created_at DESC)",
    ]

    with engine.begin() as conn:
        for statement in statements:
            conn.execute(text(statement))
