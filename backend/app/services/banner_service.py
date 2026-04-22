from app.services.ocr_service import (
    extract_text_from_image_bytes,
    detect_advertiser_from_text,
    has_commercial_signal,
    has_editorial_signal,
)
from app.services.evidence_service import save_html_evidence, save_binary_evidence
from app.services.pricing_service import estimate_banner_value
from playwright.sync_api import sync_playwright
from urllib.parse import urljoin, urlparse
import uuid
import re


COMMON_BANNER_SIZES = [
    (728, 90),
    (300, 250),
    (970, 250),
    (320, 100),
    (160, 600),
    (300, 600),
    (336, 280),
    (468, 60),
    (970, 90),
    (970, 150),
]


def detect_advertiser_from_url(url: str):
    if not url:
        return None

    url = url.lower()

    if "magazineluiza" in url:
        return "Magazine Luiza"
    if "casasbahia" in url:
        return "Casas Bahia"
    if "americanas" in url:
        return "Americanas"
    if "mercadolivre" in url:
        return "Mercado Livre"
    if "claro" in url:
        return "Claro"
    if "vivo" in url:
        return "Vivo"
    if "tim" in url:
        return "TIM"
    if "oi" in url:
        return "OI"
    if "netshoes" in url:
        return "Netshoes"
    if "natura" in url:
        return "Natura"
    if "boticario" in url:
        return "O Boticário"
    if "shopee" in url:
        return "Shopee"
    if "amazon" in url:
        return "Amazon"
    if "renner" in url:
        return "Renner"
    if "riachuelo" in url:
        return "Riachuelo"
    if "unimed" in url:
        return "Unimed"

    return None


def normalize_banner_size(width: int, height: int) -> tuple[int, int]:
    if not width or not height:
        return (0, 0)

    closest = None
    closest_distance = None

    for bw, bh in COMMON_BANNER_SIZES:
        distance = abs(width - bw) + abs(height - bh)

        if closest_distance is None or distance < closest_distance:
            closest_distance = distance
            closest = (bw, bh)

    if closest and closest_distance is not None and closest_distance <= 140:
        return closest

    return (width, height)


def looks_like_banner(width: int, height: int) -> bool:
    if width < 120 or height < 60:
        return False

    for bw, bh in COMMON_BANNER_SIZES:
        if abs(width - bw) <= 40 and abs(height - bh) <= 40:
            return True

    ratio = width / max(height, 1)

    if width >= 250 and height >= 80 and ratio >= 1.5:
        return True

    if width >= 120 and height >= 300:
        return True

    return False


def get_background_image(style_value: str):
    if not style_value:
        return None

    match = re.search(r'url\(["\']?(.*?)["\']?\)', style_value)
    return match.group(1) if match else None

    
def classify_banner_candidate(
    full_src: str,
    alt_text: str,
    ocr_text: str,
    page_url: str,
    width: int,
    height: int,
):
    score = 0
    reasons = []
    
    advertiser_from_url = detect_advertiser_from_url(full_src)
    advertiser_from_text = detect_advertiser_from_text(ocr_text)
    commercial_signal = has_commercial_signal(ocr_text)
    editorial_signal = has_editorial_signal(ocr_text)

    src_lower = (full_src or "").lower()
    combined = f"{full_src} {alt_text} {ocr_text} {page_url}".lower()

    if advertiser_from_url:
        score += 25
        reasons.append("+brand_url")

    if advertiser_from_text:
        score += 20
        reasons.append("+brand_ocr")

    if commercial_signal:
        score += 15
        reasons.append("+commercial_text")

    if any(
        x in src_lower
        for x in [
            "doubleclick",
            "googlesyndication",
            "adservice",
            "criteo",
            "taboola",
            "outbrain",
            "smartadserver",
        ]
    ):
        score += 25
        reasons.append("+adserver")

    if any(
        x in src_lower
        for x in [
            "/ads/",
            "/banners/",
            "banner",
            "advert",
            "adsystem",
        ]
    ):
        score += 10
        reasons.append("+banner_url")

    if looks_like_banner(width, height):
        score += 8
        reasons.append("+banner_format")

    if editorial_signal:
        score -= 18
        reasons.append("-editorial_text")

    if any(
        x in combined
        for x in [
            "noticia",
            "notícias",
            "editoria",
            "publicado em",
            "leia também",
            "mais lidas",
            "veja também",
            "redacao",
            "redação",
            "autor",
            "politica",
            "política",
            "esporte",
        ]
    ):
        score -= 12
        reasons.append("-editorial_context")

    strong_positive_count = sum(
        [
            1 if advertiser_from_url else 0,
            1 if advertiser_from_text else 0,
            1 if commercial_signal else 0,
            1
            if any(
                x in src_lower
                for x in [
                    "doubleclick",
                    "googlesyndication",
                    "adservice",
                    "criteo",
                    "taboola",
                    "outbrain",
                    "smartadserver",
                ]
            )
            else 0,
        ]
    )

    if strong_positive_count >= 2 or score >= 28:
        classification = "Publicidade"
    elif editorial_signal and score <= -10:
        classification = "Editorial"
    else:
        classification = "Indefinido"

    detected_advertiser = advertiser_from_url or advertiser_from_text

    return classification, score, ", ".join(reasons), detected_advertiser


def scan_page_for_banners(project_id: str, url: str):
    results = []

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page(viewport={"width": 1440, "height": 3000})

        page.goto(url, wait_until="domcontentloaded", timeout=60000)
        page.wait_for_timeout(5000)

        page.mouse.wheel(0, 1200)
        page.wait_for_timeout(3000)

        html = page.content()
        evidence_key = f"{project_id}/banners/{uuid.uuid4()}.html"
        saved_key, saved_url = save_html_evidence(evidence_key, html)

        page_screenshot_bytes = page.screenshot(full_page=True)
        page_shot_key = f"{project_id}/banners/{uuid.uuid4()}-page.png"
        saved_page_key, saved_page_url = save_binary_evidence(
            page_shot_key,
            page_screenshot_bytes,
            "image/png"
        )

        page_domain = urlparse(url).netloc
        seen = set()

        images = page.query_selector_all("img")
        for img in images:
            try:
                src = img.get_attribute("src")
                alt = img.get_attribute("alt")
                box = img.bounding_box()
                href = img.evaluate("""
                (el) => {
                    let p = el.closest('a');
                    return p ? p.href : '';
                }
                """)
                class_name = img.get_attribute("class") or ""
                element_id = img.get_attribute("id") or ""

                if not src or not box:
                    continue

                width = int(box.get("width", 0))
                height = int(box.get("height", 0))
                pos_x = int(box.get("x", 0))
                pos_y = int(box.get("y", 0))

                if not looks_like_banner(width, height):
                    continue

                full_src = urljoin(url, src)
                unique_key = f"{full_src}-{width}-{height}"

                if unique_key in seen:
                    continue
                seen.add(unique_key)

                normalized_width, normalized_height = normalize_banner_size(width, height)

                banner_png = img.screenshot()
                ocr_text = extract_text_from_image_bytes(banner_png)
              
                combined_text = f"{alt or ''} {full_src or ''} {href or ''} {class_name or ''} {element_id or ''}"
                ocr_or_meta_advertiser = detect_advertiser_from_text(f"{ocr_text} {combined_text}")
                
                classification, classification_score, classification_reason, advertiser_name = classify_banner_candidate(
                    full_src=full_src,
                    alt_text=alt or "",
                    ocr_text=ocr_text,
                    page_url=url,
                    width=width,
                    height=height,
                )

                if not advertiser_name:
                    advertiser_name = ocr_or_meta_advertiser

                estimated_value = estimate_banner_value(normalized_width, normalized_height)

                banner_shot_key = f"{project_id}/banners/{uuid.uuid4()}-banner.png"
                saved_banner_key, saved_banner_url = save_binary_evidence(
                    banner_shot_key,
                    banner_png,
                    "image/png"
                )

                results.append(
                    {
                        "page_url": url,
                        "image_url": full_src,
                        "alt_text": alt or "",
                        "width": width,
                        "height": height,
                        "normalized_width": normalized_width,
                        "normalized_height": normalized_height,
                        "estimated_value": estimated_value,
                        "pos_x": pos_x,
                        "pos_y": pos_y,
                        "source_name": page_domain,
                        "evidence_html_key": saved_key,
                        "evidence_html_url": saved_url,
                        "screenshot_page_key": saved_page_key,
                        "screenshot_page_url": saved_page_url,
                        "screenshot_banner_key": saved_banner_key,
                        "screenshot_banner_url": saved_banner_url,
                        "ocr_text": ocr_text,
                        "advertiser_name": advertiser_name,
                        "classification": classification,
                        "classification_score": classification_score,
                        "classification_reason": classification_reason,
                    }
                )

            except Exception:
                continue

        blocks = page.query_selector_all("[style*='background-image']")
        for block in blocks:
            try:
                style = block.get_attribute("style")
                src = get_background_image(style or "")
                box = block.bounding_box()
                href = block.evaluate("""
                (el) => {
                    let p = el.closest('a');
                    return p ? p.href : '';
                }
                """)
                class_name = block.get_attribute("class") or ""
                element_id = block.get_attribute("id") or ""

                if not src or not box:
                    continue

                width = int(box.get("width", 0))
                height = int(box.get("height", 0))
                pos_x = int(box.get("x", 0))
                pos_y = int(box.get("y", 0))

                if not looks_like_banner(width, height):
                    continue

                full_src = urljoin(url, src)
                unique_key = f"{full_src}-{width}-{height}"

                if unique_key in seen:
                    continue
                seen.add(unique_key)

                normalized_width, normalized_height = normalize_banner_size(width, height)

                banner_png = block.screenshot()
                ocr_text = extract_text_from_image_bytes(banner_png)
                
                combined_text = f"{full_src or ''} {href or ''} {class_name or ''} {element_id or ''}"
                ocr_or_meta_advertiser = detect_advertiser_from_text(f"{ocr_text} {combined_text}")

                classification, classification_score, classification_reason, advertiser_name = classify_banner_candidate(
                    full_src=full_src,
                    alt_text="",
                    ocr_text=ocr_text,
                    page_url=url,
                    width=width,
                    height=height,
                )

                if not advertiser_name:
                    advertiser_name = ocr_or_meta_advertiser
               
                estimated_value = estimate_banner_value(normalized_width, normalized_height)

                banner_shot_key = f"{project_id}/banners/{uuid.uuid4()}-banner.png"
                saved_banner_key, saved_banner_url = save_binary_evidence(
                    banner_shot_key,
                    banner_png,
                    "image/png"
                )

                results.append(
                    {
                        "page_url": url,
                        "image_url": full_src,
                        "alt_text": "",
                        "width": width,
                        "height": height,
                        "normalized_width": normalized_width,
                        "normalized_height": normalized_height,
                        "estimated_value": estimated_value,
                        "pos_x": pos_x,
                        "pos_y": pos_y,
                        "source_name": page_domain,
                        "evidence_html_key": saved_key,
                        "evidence_html_url": saved_url,
                        "screenshot_page_key": saved_page_key,
                        "screenshot_page_url": saved_page_url,
                        "screenshot_banner_key": saved_banner_key,
                        "screenshot_banner_url": saved_banner_url,
                        "ocr_text": ocr_text,
                        "advertiser_name": advertiser_name,
                        "classification": classification,
                        "classification_score": classification_score,
                        "classification_reason": classification_reason,
                    }
                )

            except Exception:
                continue

        browser.close()

    return results