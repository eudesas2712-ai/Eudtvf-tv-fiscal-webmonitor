import uuid
from datetime import datetime
from urllib.parse import urljoin, urlparse

import requests
from bs4 import BeautifulSoup

from app.db.models import BannerItem
from app.db.session import SessionLocal
from app.services.banner_classifier import classify_advertiser
from app.services.banner_valuator import estimate_banner_value
from app.services.banner_visibility import calculate_visibility_score

PROJECT_ID = "9b972aa2-f8a4-483b-a7d1-e979d86482fb"

PORTALS = [
    "https://www.polemicaparaiba.com.br",
    "https://www.portalcorreio.com.br",
    "https://www.clickpb.com.br",
]


def _normalize_image_url(page_url: str, src: str | None) -> str | None:
    if not src:
        return None
    src = src.strip()
    if not src:
        return None
    if src.startswith("data:"):
        return None
    return urljoin(page_url, src)


def _looks_like_banner(img) -> bool:
    src = (img.get("src") or "").lower()
    alt = (img.get("alt") or "").lower()
    classes = " ".join(img.get("class", [])).lower()

    blocked_terms = [
        "logo",
        "avatar",
        "icon",
        "favicon",
        "profile",
    ]
    if any(term in src or term in alt or term in classes for term in blocked_terms):
        return False

    return True


def collect_banners(project_id: str = PROJECT_ID, limit_per_portal: int = 20) -> None:
    db = SessionLocal()
    inserted = 0

    try:
        project_uuid = uuid.UUID(project_id)

        for portal in PORTALS:
            try:
                response = requests.get(
                    portal,
                    timeout=15,
                    headers={
                        "User-Agent": (
                            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                            "AppleWebKit/537.36 (KHTML, like Gecko) "
                            "Chrome/124.0.0.0 Safari/537.36"
                        )
                    },
                )
                response.raise_for_status()

                soup = BeautifulSoup(response.text, "html.parser")
                images = soup.find_all("img")

                collected_here = 0
                seen_urls = set()

                for img in images:
                    if collected_here >= limit_per_portal:
                        break

                    if not _looks_like_banner(img):
                        continue

                    src = _normalize_image_url(portal, img.get("src"))
                    if not src:
                        continue

                    if src in seen_urls:
                        continue
                    seen_urls.add(src)

                    exists = (
                        db.query(BannerItem)
                        .filter(
                            BannerItem.project_id == project_uuid,
                            BannerItem.page_url == portal,
                            BannerItem.image_url == src,
                        )
                        .first()
                    )
                    if exists:
                        continue

                    width = None
                    height = None

                    try:
                        width = int(img.get("width")) if img.get("width") else None
                    except Exception:
                        width = None

                    try:
                        height = int(img.get("height")) if img.get("height") else None
                    except Exception:
                        height = None

                    adv, score, reason = classify_advertiser(
                        alt_text=img.get("alt"),
                        image_url=src,
                        ocr_text=img.get("alt") or "",
                    )

                    value = estimate_banner_value(
                        width,
                        height,
                        urlparse(portal).netloc,
                        0,
                    )

                    visibility = calculate_visibility_score(
                        width,
                        height,
                        0,
                        value,
                    )

                    item = BannerItem(
                        project_id=project_uuid,
                        page_url=portal,
                        image_url=src,
                        alt_text=img.get("alt"),
                        width=width,
                        height=height,
                        normalized_width=width or 300,
                        normalized_height=height or 250,
                        estimated_value=value,
                        pos_x=0,
                        pos_y=0,
                        source_name=urlparse(portal).netloc,
                        advertiser_name=adv,
                        classification="Publicidade",
                        classification_score=score,
                        classification_reason=reason,
                        ocr_text=img.get("alt") or "",
                        visibility_score=visibility,
                        created_at=datetime.utcnow(),                        
                  )
                    
                    db.add(item)
                    inserted += 1
                    collected_here += 1

                db.commit()
                print(f"[collector] {portal}: {collected_here} banners inseridos")

            except Exception as e:
                db.rollback()
                print(f"[collector] erro em {portal}: {e}")

        print(f"✅ coleta concluída: {inserted} banners inseridos")

    finally:
        db.close()


if __name__ == "__main__":
    collect_banners()