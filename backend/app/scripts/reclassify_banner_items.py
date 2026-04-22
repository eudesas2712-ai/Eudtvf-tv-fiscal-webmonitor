from app.db.models import BannerItem
from app.db.session import SessionLocal
from app.services.banner_classifier import classify_advertiser


def reclassify():
    db = SessionLocal()
    updated = 0

    try:
        items = db.query(BannerItem).all()

        for item in items:
            adv, score, reason = classify_advertiser(
                alt_text=getattr(item, "alt_text", None),
                image_url=getattr(item, "image_url", None),
                ocr_text=getattr(item, "ocr_text", None),
            )

            item.advertiser_name = adv
            item.classification_score = score
            item.classification_reason = reason
            updated += 1

        db.commit()
        print(f"✅ {updated} banners reclassificados")
    finally:
        db.close()


if __name__ == "__main__":
    reclassify()