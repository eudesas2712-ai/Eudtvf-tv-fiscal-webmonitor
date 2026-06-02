from app.db.models import BannerItem
from app.db.session import SessionLocal
from app.services.banner_classifier import classify_advertiser
from app.services.content_classifier import classify_detected_item


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
            item.classification_reason = reason

            classified = classify_detected_item({
                "page_url": getattr(item, "page_url", None),
                "image_url": getattr(item, "image_url", None),
                "alt_text": getattr(item, "alt_text", None),
                "ocr_text": getattr(item, "ocr_text", None),
                "width": getattr(item, "width", None),
                "height": getattr(item, "height", None),
                "normalized_width": getattr(item, "normalized_width", None),
                "normalized_height": getattr(item, "normalized_height", None),
                "source_name": getattr(item, "source_name", None),
                "advertiser_name": adv,
                "classification_reason": reason,
                "screenshot_banner_url": getattr(item, "screenshot_banner_url", None),
                "screenshot_page_url": getattr(item, "screenshot_page_url", None),
                "evidence_html_url": getattr(item, "evidence_html_url", None),
            })

            item.classification = classified["classification"]
            item.classification_score = classified["classification_score"]
            item.classification_reason = classified["classification_reason"]
            item.content_type = classified["content_type"]
            item.checking_status = classified["checking_status"]
            item.market_status = classified["market_status"]
            item.news_status = classified["news_status"]
            item.publicity_score = classified["publicity_score"]
            item.news_score = classified["news_score"]
            item.market_score = classified["market_score"]
            item.has_preserved_evidence = classified["has_preserved_evidence"]
            item.evidence_type = classified["evidence_type"]
            updated += 1

        db.commit()
        print(f"✅ {updated} banners reclassificados")
    finally:
        db.close()


if __name__ == "__main__":
    reclassify()