import os

from app.db.models import Base, BannerItem
from app.db.session import SessionLocal, engine
from app.db.migrations import (
    ensure_banner_classification_columns,
    ensure_project_management_columns,
    ensure_editorial_item_columns,
    ensure_identification_review_columns,
    ensure_notification_tables,
    ensure_notification_provider_settings,
    ensure_notification_automation_runs,
    ensure_notification_sla_columns,
    ensure_system_health_tables,
    ensure_maintenance_v40_columns,
    ensure_user_access_tables,
    ensure_generated_reports_table,
    ensure_social_items_unique_index,
)
from app.scripts.seed_banner_items import seed_banner_items
from app.services.auth_service import ensure_default_admin


def bootstrap_system() -> None:
    print("[bootstrap] iniciando bootstrap do sistema...")

    # garante schema base e colunas incrementais
    Base.metadata.create_all(bind=engine)
    ensure_banner_classification_columns(engine)
    ensure_project_management_columns(engine)
    ensure_editorial_item_columns(engine)
    ensure_identification_review_columns(engine)
    ensure_notification_tables(engine)
    ensure_notification_provider_settings(engine)
    ensure_notification_automation_runs(engine)
    ensure_notification_sla_columns(engine)
    ensure_system_health_tables(engine)
    ensure_maintenance_v40_columns(engine)
    ensure_user_access_tables(engine)
    ensure_generated_reports_table(engine)
    ensure_social_items_unique_index(engine)
    print("[bootstrap] tabelas verificadas/criadas")

    db = SessionLocal()
    try:
        ensure_default_admin(db)

        banners_count = db.query(BannerItem).count()
        print(f"[bootstrap] banner_items atuais: {banners_count}")

        seed_demo_enabled = os.getenv("SEED_DEMO_BANNERS", "false").strip().lower() in {"1", "true", "yes", "sim"}

        if banners_count == 0 and seed_demo_enabled:
            print("[bootstrap] base vazia detectada, executando seed demo...")
            seed_banner_items(db=db, replace=False, quantity=250)
            print("[bootstrap] seed demo concluído")
        elif banners_count == 0:
            print("[bootstrap] base vazia sem seed demo. Nenhum banner simulado foi criado.")
        else:
            print("[bootstrap] seed ignorado: base já possui dados")
    finally:
        db.close()

    print("[bootstrap] bootstrap finalizado")