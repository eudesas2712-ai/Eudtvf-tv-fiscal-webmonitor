from app.db.models import BannerItem
from app.db.session import SessionLocal
from app.services.banner_visibility import calculate_visibility_score


def fill_visibility():
    db = SessionLocal()
    updated = 0

    try:
        items = db.query(BannerItem).all()

        for item in items:
            visibility = calculate_visibility_score(
                getattr(item, "width", None),
                getattr(item, "height", None),
                getattr(item, "pos_y", None),
                getattr(item, "estimated_value", None),
            )
            item.visibility_score = visibility
            updated += 1

        db.commit()
        print(f"✅ {updated} banners atualizados com visibility_score")
    finally:
        db.close()


if __name__ == "__main__":
    fill_visibility()