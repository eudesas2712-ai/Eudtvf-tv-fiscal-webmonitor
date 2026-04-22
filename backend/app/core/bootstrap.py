from app.db.models import Base, BannerItem
from app.db.session import SessionLocal, engine
from app.scripts.seed_banner_items import seed_banner_items


def bootstrap_system() -> None:
    print("[bootstrap] iniciando bootstrap do sistema...")

    # garante schema
    Base.metadata.create_all(bind=engine)
    print("[bootstrap] tabelas verificadas/criadas")

    db = SessionLocal()
    try:
        banners_count = db.query(BannerItem).count()
        print(f"[bootstrap] banner_items atuais: {banners_count}")

        if banners_count == 0:
            print("[bootstrap] base vazia detectada, executando seed demo...")
            seed_banner_items(db=db, replace=False, quantity=250)
            print("[bootstrap] seed demo concluído")
        else:
            print("[bootstrap] seed ignorado: base já possui dados")
    finally:
        db.close()

    print("[bootstrap] bootstrap finalizado")