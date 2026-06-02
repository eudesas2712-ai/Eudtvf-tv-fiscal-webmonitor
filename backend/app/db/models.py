import uuid
from datetime import datetime

from sqlalchemy import String, Text, DateTime, Boolean, Integer, UniqueConstraint
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.orm import Mapped, mapped_column, declarative_base

Base = declarative_base()


class Project(Base):
    __tablename__ = "projects"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    client_name: Mapped[str] = mapped_column(String(255), nullable=True)
    segment_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=True)
    description: Mapped[str] = mapped_column(Text, nullable=True)
    active: Mapped[bool] = mapped_column(Boolean, default=True)
    monitor_publicity: Mapped[bool] = mapped_column(Boolean, default=True)
    monitor_editorial: Mapped[bool] = mapped_column(Boolean, default=True)
    monitor_market: Mapped[bool] = mapped_column(Boolean, default=True)
    monitor_checking: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)


class Source(Base):
    __tablename__ = "sources"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    project_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False)

    name: Mapped[str] = mapped_column(String(255), nullable=False)
    base_url: Mapped[str] = mapped_column(String(1024), nullable=False)
    rss_url: Mapped[str] = mapped_column(String(1024), nullable=True)

    enabled: Mapped[bool] = mapped_column(Boolean, default=True)
    interval_minutes: Mapped[int] = mapped_column(Integer, default=60)


class WatchTerm(Base):
    __tablename__ = "watch_terms"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    project_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False)

    term: Mapped[str] = mapped_column(String(255), nullable=False)
    active: Mapped[bool] = mapped_column(Boolean, default=True)

    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)


class Item(Base):
    __tablename__ = "items"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    project_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False)
    source_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False)

    title: Mapped[str] = mapped_column(String(500), nullable=False)
    url: Mapped[str] = mapped_column(String(1024), nullable=False)
    content_text: Mapped[str] = mapped_column(Text, nullable=False)
    matched_terms: Mapped[dict] = mapped_column(JSONB, default=dict)

    evidence_html_key: Mapped[str] = mapped_column(String(1024), nullable=True)
    evidence_html_url: Mapped[str] = mapped_column(String(2048), nullable=True)

    # Campos editoriais incrementais para o módulo de monitoramento de notícias.
    source_name: Mapped[str] = mapped_column(String(255), nullable=True)
    summary: Mapped[str] = mapped_column(Text, nullable=True)
    sentiment: Mapped[str] = mapped_column(String(50), nullable=True)
    sentiment_score: Mapped[int] = mapped_column(nullable=True)
    topic: Mapped[str] = mapped_column(String(120), nullable=True)
    editorial_score: Mapped[int] = mapped_column(nullable=True)
    published_at: Mapped[datetime] = mapped_column(DateTime, nullable=True)

    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)


class BannerItem(Base):
    __tablename__ = "banner_items"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    project_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False)

    page_url: Mapped[str] = mapped_column(String(1024), nullable=False)
    image_url: Mapped[str] = mapped_column(String(2048), nullable=False)
    alt_text: Mapped[str] = mapped_column(String(500), nullable=True)

    width: Mapped[int] = mapped_column(nullable=True)
    height: Mapped[int] = mapped_column(nullable=True)
    normalized_width: Mapped[int] = mapped_column(nullable=True)
    normalized_height: Mapped[int] = mapped_column(nullable=True)
    estimated_value: Mapped[int] = mapped_column(nullable=True)

    pos_x: Mapped[int] = mapped_column(nullable=True)
    pos_y: Mapped[int] = mapped_column(nullable=True)

    source_name: Mapped[str] = mapped_column(String(255), nullable=True)

    evidence_html_key: Mapped[str] = mapped_column(String(1024), nullable=True)
    evidence_html_url: Mapped[str] = mapped_column(String(2048), nullable=True)

    screenshot_page_key: Mapped[str] = mapped_column(String(1024), nullable=True)
    screenshot_page_url: Mapped[str] = mapped_column(String(2048), nullable=True)
    screenshot_banner_key: Mapped[str] = mapped_column(String(1024), nullable=True)
    screenshot_banner_url: Mapped[str] = mapped_column(String(2048), nullable=True)

    ocr_text: Mapped[str] = mapped_column(Text, nullable=True)
    advertiser_name: Mapped[str] = mapped_column(String(255), nullable=True)

    classification: Mapped[str] = mapped_column(String(50), nullable=True)
    classification_score: Mapped[int] = mapped_column(nullable=True)
    classification_reason: Mapped[str] = mapped_column(Text, nullable=True)

    # Classificação multicamadas: separa checking, mercado e notícias.
    content_type: Mapped[str] = mapped_column(String(50), nullable=True)
    checking_status: Mapped[str] = mapped_column(String(50), nullable=True)
    market_status: Mapped[str] = mapped_column(String(50), nullable=True)
    news_status: Mapped[str] = mapped_column(String(50), nullable=True)
    publicity_score: Mapped[int] = mapped_column(nullable=True)
    news_score: Mapped[int] = mapped_column(nullable=True)
    market_score: Mapped[int] = mapped_column(nullable=True)
    has_preserved_evidence: Mapped[bool] = mapped_column(Boolean, default=False)
    evidence_type: Mapped[str] = mapped_column(String(50), nullable=True)

    visibility_score: Mapped[int] = mapped_column(nullable=True)

    # Qualificação manual de identificação comercial.
    # Permite transformar "Não identificado" em anunciante cadastrado
    # sem perder a trilha de auditoria operacional.
    identification_status: Mapped[str] = mapped_column(String(50), nullable=True)
    identification_note: Mapped[str] = mapped_column(Text, nullable=True)
    qualified_advertiser_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=True)
    qualified_at: Mapped[datetime] = mapped_column(DateTime, nullable=True)

    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)


class Segment(Base):
    __tablename__ = "segments"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name: Mapped[str] = mapped_column(String(255), nullable=False, unique=True)
    description: Mapped[str] = mapped_column(Text, nullable=True)
    active: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)


class Advertiser(Base):
    __tablename__ = "advertisers"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    legal_name: Mapped[str] = mapped_column(String(255), nullable=True)
    segment_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=True)
    advertiser_type: Mapped[str] = mapped_column(String(50), default="anunciante")
    active: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)


class AdvertiserAlias(Base):
    __tablename__ = "advertiser_aliases"
    __table_args__ = (UniqueConstraint("advertiser_id", "alias", name="uq_advertiser_alias"),)

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    advertiser_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False)
    alias: Mapped[str] = mapped_column(String(255), nullable=False)
    active: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)


class Portal(Base):
    __tablename__ = "portals"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    base_url: Mapped[str] = mapped_column(String(1024), nullable=False, unique=True)
    category: Mapped[str] = mapped_column(String(100), nullable=True)
    active: Mapped[bool] = mapped_column(Boolean, default=True)
    monitor_publicity: Mapped[bool] = mapped_column(Boolean, default=True)
    monitor_editorial: Mapped[bool] = mapped_column(Boolean, default=True)
    interval_minutes: Mapped[int] = mapped_column(Integer, default=60)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)


class ProjectPortal(Base):
    __tablename__ = "project_portals"
    __table_args__ = (UniqueConstraint("project_id", "portal_id", name="uq_project_portal"),)

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    project_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False)
    portal_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False)
    active: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)


class ProjectAdvertiser(Base):
    __tablename__ = "project_advertisers"
    __table_args__ = (UniqueConstraint("project_id", "advertiser_id", name="uq_project_advertiser"),)

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    project_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False)
    advertiser_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False)
    role: Mapped[str] = mapped_column(String(50), default="monitorado")
    active: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)


class NotificationContact(Base):
    __tablename__ = "notification_contacts"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    project_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    role: Mapped[str] = mapped_column(String(120), nullable=True)
    email: Mapped[str] = mapped_column(String(255), nullable=True)
    phone: Mapped[str] = mapped_column(String(80), nullable=True)
    whatsapp: Mapped[str] = mapped_column(String(80), nullable=True)
    channels: Mapped[dict] = mapped_column(JSONB, default=list)
    priority: Mapped[str] = mapped_column(String(50), default="normal")
    active: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)


class NotificationRule(Base):
    __tablename__ = "notification_rules"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    project_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    active: Mapped[bool] = mapped_column(Boolean, default=True)
    event_type: Mapped[str] = mapped_column(String(80), default="any")
    terms: Mapped[dict] = mapped_column(JSONB, default=list)
    categories: Mapped[dict] = mapped_column(JSONB, default=list)
    channels: Mapped[dict] = mapped_column(JSONB, default=list)
    contact_ids: Mapped[dict] = mapped_column(JSONB, default=list)
    severity_min: Mapped[str] = mapped_column(String(50), default="alto")
    sentiment_filter: Mapped[str] = mapped_column(String(50), nullable=True)
    cooldown_minutes: Mapped[int] = mapped_column(Integer, default=60)
    last_triggered_at: Mapped[datetime] = mapped_column(DateTime, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)


class NotificationLog(Base):
    __tablename__ = "notification_logs"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    project_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False)
    rule_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=True)
    contact_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=True)
    event_type: Mapped[str] = mapped_column(String(80), nullable=True)
    severity: Mapped[str] = mapped_column(String(50), nullable=True)
    category: Mapped[str] = mapped_column(String(80), nullable=True)
    channel: Mapped[str] = mapped_column(String(50), nullable=False)
    status: Mapped[str] = mapped_column(String(50), default="queued")
    provider: Mapped[str] = mapped_column(String(80), nullable=True)
    title: Mapped[str] = mapped_column(String(500), nullable=True)
    message: Mapped[str] = mapped_column(Text, nullable=True)
    target_url: Mapped[str] = mapped_column(String(2048), nullable=True)
    provider_response: Mapped[str] = mapped_column(Text, nullable=True)
    alert_status: Mapped[str] = mapped_column(String(50), default="aberto")
    acknowledged_at: Mapped[datetime] = mapped_column(DateTime, nullable=True)
    acknowledged_by: Mapped[str] = mapped_column(String(255), nullable=True)
    resolved_at: Mapped[datetime] = mapped_column(DateTime, nullable=True)
    resolved_by: Mapped[str] = mapped_column(String(255), nullable=True)
    resolution_note: Mapped[str] = mapped_column(Text, nullable=True)
    snoozed_until: Mapped[datetime] = mapped_column(DateTime, nullable=True)

    # SLA operacional e escalonamento de alertas.
    assigned_to: Mapped[str] = mapped_column(String(255), nullable=True)
    sla_minutes: Mapped[int] = mapped_column(Integer, nullable=True)
    sla_due_at: Mapped[datetime] = mapped_column(DateTime, nullable=True)
    escalation_level: Mapped[int] = mapped_column(Integer, default=0)
    escalation_count: Mapped[int] = mapped_column(Integer, default=0)
    escalated_at: Mapped[datetime] = mapped_column(DateTime, nullable=True)
    last_escalation_note: Mapped[str] = mapped_column(Text, nullable=True)

    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)


class NotificationProviderSetting(Base):
    __tablename__ = "notification_provider_settings"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    project_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False)
    provider_type: Mapped[str] = mapped_column(String(50), nullable=False)
    provider_name: Mapped[str] = mapped_column(String(80), nullable=False)
    active: Mapped[bool] = mapped_column(Boolean, default=True)
    config: Mapped[dict] = mapped_column(JSONB, default=dict)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

class NotificationAutomationRun(Base):
    __tablename__ = "notification_automation_runs"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    project_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False)
    trigger_source: Mapped[str] = mapped_column(String(80), nullable=False)
    status: Mapped[str] = mapped_column(String(50), default="success")
    rules_count: Mapped[int] = mapped_column(Integer, default=0)
    events_count: Mapped[int] = mapped_column(Integer, default=0)
    notifications_count: Mapped[int] = mapped_column(Integer, default=0)
    sent_count: Mapped[int] = mapped_column(Integer, default=0)
    registered_count: Mapped[int] = mapped_column(Integer, default=0)
    dry_run_count: Mapped[int] = mapped_column(Integer, default=0)
    error_count: Mapped[int] = mapped_column(Integer, default=0)
    skipped_duplicates: Mapped[int] = mapped_column(Integer, default=0)
    message: Mapped[str] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

