import uuid
from datetime import datetime

from sqlalchemy import String, Text, DateTime, Boolean, Integer
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.orm import Mapped, mapped_column, declarative_base
from sqlalchemy import String, Text, DateTime, Boolean, Integer, Float

Base = declarative_base()


class Project(Base):
    __tablename__ = "projects"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[str] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)


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

    visibility_score: Mapped[int] = mapped_column(nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
