"""Classificação multicamadas dos itens visuais detectados.

Versão V3 - calibrada a partir do segundo teste real no ClickPB.

Objetivos:
- Checking publicitário: só aprovar automaticamente o que tem sinal publicitário forte.
- Inteligência de mercado: aproveitar itens comerciais, parciais ou com anunciante detectado.
- Monitoramento de notícias: preservar imagens/chamadas editoriais como candidatas a notícia.
- Não transformar notícia com preço/valor monetário em publicidade apenas por conter "R$".
- Evitar duplicação/contaminação de classification_reason em reclassificações sucessivas.
"""

from __future__ import annotations

import re
import unicodedata
from urllib.parse import unquote, urlparse


COMMON_BANNER_SIZES = {
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
    (728, 250),
    (728, 600),
    (300, 90),
    (160, 90),
    (160, 250),
}

# Sinais técnicos fortes. Evitar tratar apenas o tamanho do card como publicidade.
TECHNICAL_AD_TOKENS = [
    "/ads/",
    "/ad/",
    "/banner/",
    "/banners/",
    "doubleclick",
    "googlesyndication",
    "adservice",
    "criteo",
    "taboola",
    "outbrain",
    "smartadserver",
    "publicidade",
    "sponsor",
    "patrocin",
    "utm_source",
    "utm_campaign",
    "adserver",
    "adsystem",
    "advert",
    "hotmart",
    "monetizze",
    "eduzz",
]

# Domínios/plataformas que indicam anúncio/infoproduto mesmo sem OCR perfeito.
COMMERCIAL_DOMAINS = [
    "hotmart.com",
    "app.oead.com.br",
    "monetizze.com.br",
    "eduzz.com",
    "kiwify.com.br",
    "braip.com",
    "abracadabraonline.com.br",
]

# CTA/termos de venda fortes. Estes podem elevar publicidade mesmo sem preço.
STRONG_COMMERCIAL_TOKENS = [
    "compre",
    "comprar",
    "contrate",
    "assine",
    "matricule-se",
    "inscreva-se",
    "clique aqui",
    "saiba mais",
    "aproveite",
    "garanta sua vaga",
    "frete gratis",
    "frete grátis",
    "boleto",
    "cartao",
    "cartão",
    "parcelamento",
    "curso",
    "treinamento",
    "videoaula",
    "video aula",
    "hamburguer artesanal",
    "maquiagem",
    "treinos",
]

# Termos de preço/oferta são ambíguos em notícia. Só contam como publicidade
# quando combinados com CTA, link externo comercial ou domínio/adserver.
AMBIGUOUS_PRICE_TOKENS = [
    "r$",
    "apenas r$",
    "por apenas",
    "oferta",
    "promocao",
    "promoção",
    "desconto",
    "imperdivel",
    "imperdível",
    "vender",
    "negocio",
    "negócio",
    "produto",
]

# Termos que parecem comerciais, mas em manchete jornalística devem puxar para editorial.
EDITORIAL_PRICE_CONTEXT_TOKENS = [
    "aumento",
    "anuncia aumento",
    "distribuidoras",
    "licitacao",
    "licitação",
    "contratacao",
    "contratação",
    "imposto",
    "impostos",
    "dia livre de impostos",
    "preco do litro",
    "preço do litro",
    "gasolina",
    "petrobras",
    "abre licitacao",
    "abre licitação",
]

# Termos e estruturas típicas de notícia/editorial.
EDITORIAL_TOKENS = [
    "/noticia/",
    "/noticias/",
    "/politica/",
    "/política/",
    "/cidade/",
    "/economia/",
    "/brasil/",
    "/paraiba/",
    "/esporte/",
    "/policial/",
    "/cultura/",
    "/saude/",
    "/saúde/",
    "/blogs/",
    "noticia",
    "notícias",
    "materia",
    "matéria",
    "reportagem",
    "publicado em",
    "redacao",
    "redação",
    "autor",
    "editoria",
    "leia também",
    "leia tambem",
    "mais lidas",
    "veja também",
    "veja tambem",
    "ao vivo",
    "clicknews",
    "morre",
    "morreu",
    "preso",
    "prisao",
    "prisão",
    "condenado",
    "condenada",
    "suspeito",
    "policia",
    "polícia",
    "prf",
    "apreende",
    "apreendida",
    "apreendido",
    "deputado",
    "governador",
    "prefeito",
    "cantor",
    "banda",
    "festival",
    "acidente",
    "liminar",
    "concurso",
    "licitacao",
    "licitação",
    "vacina",
    "sus",
    "petrobras anuncia",
    "seleção",
    "selecao",
]

INSTITUTIONAL_TOKENS = [
    "governo",
    "prefeitura",
    "assembleia legislativa",
    "camara municipal",
    "câmara municipal",
    "secretaria",
    "campanha institucional",
]

VIDEO_TOKENS = [
    "ytimg.com",
    "youtube.com",
    "youtu.be",
    "shorts",
    "embed",
    "video",
]

DERIVED_REASON_TOKENS = [
    "sinal_publicitario_forte",
    "evidencia_preservada",
    "contexto_editorial_ou_video",
    "util_para_inteligencia_de_mercado",
    "candidato_monitoramento_noticias",
    "formato_banner_insuficiente_para_checking",
    "noticia_com_valor_monetario_sem_cta",
]


def normalize_text(value: object) -> str:
    raw = unquote(str(value or "")).lower()
    raw = unicodedata.normalize("NFKD", raw)
    raw = "".join(ch for ch in raw if not unicodedata.combining(ch))
    raw = re.sub(r"\s+", " ", raw).strip()
    return raw


def _text_for_item(item: dict) -> str:
    # Não incluir classification_reason aqui: em reclassificações sucessivas ele
    # contamina o texto com motivos derivados e duplica sinais.
    return normalize_text(
        " ".join(
            str(item.get(key) or "")
            for key in (
                "page_url",
                "image_url",
                "alt_text",
                "ocr_text",
                "link_url",
                "class_name",
                "element_id",
                "source_name",
            )
        )
    )


def _reason_text(item: dict) -> str:
    return normalize_text(item.get("classification_reason"))


def _num(value: object) -> int:
    try:
        return int(float(value or 0))
    except (TypeError, ValueError):
        return 0


def is_common_banner_size(width: object, height: object) -> bool:
    w = _num(width)
    h = _num(height)
    if not w or not h:
        return False

    for bw, bh in COMMON_BANNER_SIZES:
        if abs(w - bw) <= 45 and abs(h - bh) <= 45:
            return True

    ratio = w / max(h, 1)
    return (w >= 250 and h >= 80 and ratio >= 1.5) or (w >= 120 and h >= 300)


def evidence_type(item: dict) -> str:
    if item.get("screenshot_banner_url"):
        return "screenshot_banner"
    if item.get("screenshot_page_url"):
        return "screenshot_page"
    if item.get("evidence_html_url"):
        return "html_preservado"
    if item.get("image_url"):
        return "imagem_dinamica"
    if item.get("page_url"):
        return "pagina_original"
    return "none"


def has_preserved_evidence(item: dict) -> bool:
    return evidence_type(item) in {"screenshot_banner", "screenshot_page", "html_preservado"}


def _advertiser_name(item: dict) -> str:
    advertiser = normalize_text(item.get("advertiser_name"))
    if advertiser in {"", "nao identificado", "não identificado", "none", "null"}:
        return ""
    return advertiser


def _host(value: object) -> str:
    return urlparse(str(value or "")).netloc.lower()


def has_external_click(item: dict) -> bool:
    page_host = _host(item.get("page_url"))
    link_host = _host(item.get("link_url"))
    return bool(page_host and link_host and link_host != page_host)


def has_commercial_domain(item: dict) -> bool:
    text = _text_for_item(item)
    return any(domain in text for domain in COMMERCIAL_DOMAINS)


def has_technical_ad_signal(item: dict) -> bool:
    text = _text_for_item(item)
    reason = _reason_text(item)

    if any(token in text for token in TECHNICAL_AD_TOKENS):
        return True

    if has_commercial_domain(item):
        return True

    # O motivo +banner_url é aceito como forte; +banner_format sozinho nunca é forte.
    if any(token in reason for token in ["+adserver", "+banner_url", "+commercial_text"]):
        return True

    return False


def has_strong_commercial_cta(item: dict) -> bool:
    text = _text_for_item(item)
    return any(token in text for token in STRONG_COMMERCIAL_TOKENS)


def has_ambiguous_price_signal(item: dict) -> bool:
    text = _text_for_item(item)
    return any(token in text for token in AMBIGUOUS_PRICE_TOKENS)


def has_editorial_price_context(item: dict) -> bool:
    text = _text_for_item(item)
    return any(token in text for token in EDITORIAL_PRICE_CONTEXT_TOKENS)


def has_commercial_text_signal(item: dict) -> bool:
    # CTA forte vale por si só. Preço/valor solto não vale se for contexto editorial.
    if has_strong_commercial_cta(item):
        return True

    if not has_ambiguous_price_signal(item):
        return False

    if has_editorial_price_context(item) and not (has_external_click(item) or has_technical_ad_signal(item) or has_commercial_domain(item)):
        return False

    return has_external_click(item) or has_technical_ad_signal(item) or has_commercial_domain(item)


def has_strong_ad_signal(item: dict) -> bool:
    return (
        has_technical_ad_signal(item)
        or has_commercial_text_signal(item)
        or (has_external_click(item) and (has_strong_commercial_cta(item) or has_commercial_domain(item)))
        or bool(_advertiser_name(item))
    )


def has_editorial_or_video_context(item: dict) -> bool:
    text = _text_for_item(item)
    return any(token in text for token in EDITORIAL_TOKENS + VIDEO_TOKENS)


def has_wp_editorial_image(item: dict) -> bool:
    image_url = normalize_text(item.get("image_url"))
    alt_text = normalize_text(item.get("alt_text"))

    # Em portais WordPress/Next, essas URLs geralmente são imagens de matéria.
    # Exceção: quando há domínio/adserver/CTA comercial claro.
    if "/wp-content/uploads/" in image_url and not (has_technical_ad_signal(item) or has_strong_commercial_cta(item) or has_commercial_domain(item)):
        if len(alt_text) >= 18:
            return True
        return True

    return False


def calculate_publicity_score(item: dict) -> int:
    score = 0

    advertiser = _advertiser_name(item)
    if advertiser:
        score += 25

    if has_technical_ad_signal(item):
        score += 30

    if has_commercial_text_signal(item):
        score += 25

    if has_external_click(item) and (has_technical_ad_signal(item) or has_commercial_text_signal(item) or has_commercial_domain(item)):
        score += 20

    if is_common_banner_size(
        item.get("normalized_width") or item.get("width"),
        item.get("normalized_height") or item.get("height"),
    ):
        # Formato é sinal fraco. Não pode aprovar sozinho.
        score += 8

    if has_preserved_evidence(item):
        score += 10

    if any(token in _text_for_item(item) for token in INSTITUTIONAL_TOKENS):
        score += 5

    # Contexto editorial reduz fortemente, salvo quando houver sinais comerciais fortes.
    if has_editorial_or_video_context(item) and not (has_technical_ad_signal(item) or has_commercial_text_signal(item)):
        score -= 35

    if has_wp_editorial_image(item) and not (has_technical_ad_signal(item) or has_commercial_text_signal(item)):
        score -= 25

    # Notícias com valores monetários, licitação, aumento de gasolina etc. não são anúncios.
    if has_editorial_price_context(item) and not (has_external_click(item) or has_technical_ad_signal(item) or has_commercial_domain(item)):
        score -= 35

    return max(0, min(100, score))


def calculate_news_score(item: dict) -> int:
    text = _text_for_item(item)
    score = 0

    if any(token in text for token in EDITORIAL_TOKENS):
        score += 45

    if has_wp_editorial_image(item):
        score += 45

    if any(token in text for token in VIDEO_TOKENS):
        score += 20

    alt_text = normalize_text(item.get("alt_text"))
    # Headline provável: ALT longo, sem domínio/adserver.
    if len(alt_text) >= 25 and not has_technical_ad_signal(item):
        score += 20

    if not has_strong_ad_signal(item):
        score += 10

    if has_technical_ad_signal(item) or has_commercial_text_signal(item):
        score -= 25

    # Se for preço em contexto jornalístico, reforça editorial.
    if has_editorial_price_context(item) and not has_commercial_domain(item):
        score += 15

    return max(0, min(100, score))


def calculate_market_score(item: dict, publicity_score: int | None = None) -> int:
    if publicity_score is None:
        publicity_score = calculate_publicity_score(item)

    score = publicity_score

    if _advertiser_name(item):
        score = max(score, 60)

    if has_technical_ad_signal(item) or has_commercial_text_signal(item) or has_commercial_domain(item):
        score = max(score, 55)

    # Link externo só entra para mercado se houver sinal comercial; link editorial externo não basta.
    if has_external_click(item) and (has_technical_ad_signal(item) or has_commercial_text_signal(item) or has_commercial_domain(item)):
        score = max(score, 55)

    # Formato sozinho não basta para inteligência de mercado; ele apenas mantém o item salvo.
    if is_common_banner_size(
        item.get("normalized_width") or item.get("width"),
        item.get("normalized_height") or item.get("height"),
    ) and has_strong_ad_signal(item):
        score = max(score, 45)

    if has_wp_editorial_image(item) and not has_strong_ad_signal(item):
        score = min(score, 25)

    if has_editorial_price_context(item) and not (has_external_click(item) or has_technical_ad_signal(item) or has_commercial_domain(item)):
        score = min(score, 25)

    return max(0, min(100, score))


def _clean_legacy_reasons(reason: object) -> list[str]:
    raw = [part.strip() for part in str(reason or "").split(",") if part.strip()]
    cleaned: list[str] = []
    for part in raw:
        normalized = normalize_text(part)
        if any(token in normalized for token in DERIVED_REASON_TOKENS):
            continue
        if part not in cleaned:
            cleaned.append(part)
    return cleaned


def _dedupe(parts: list[str]) -> list[str]:
    output: list[str] = []
    seen: set[str] = set()
    for part in parts:
        clean = str(part or "").strip()
        key = normalize_text(clean)
        if clean and key not in seen:
            output.append(clean)
            seen.add(key)
    return output


def classify_detected_item(item: dict) -> dict:
    publicity_score = calculate_publicity_score(item)
    news_score = calculate_news_score(item)
    market_score = calculate_market_score(item, publicity_score)
    evidence = evidence_type(item)
    preserved = evidence in {"screenshot_banner", "screenshot_page", "html_preservado"}
    strong_ad = has_strong_ad_signal(item)
    editorial_context = has_editorial_or_video_context(item) or has_wp_editorial_image(item)

    # Regras rígidas: notícia com valor monetário não pode cair em revisão/checking
    # sem link/domínio comercial ou adserver.
    editorial_price_only = has_editorial_price_context(item) and not (
        has_external_click(item) or has_technical_ad_signal(item) or has_commercial_domain(item)
    )

    if publicity_score >= 75 and strong_ad and preserved and not editorial_price_only and not (news_score >= 70 and not strong_ad):
        checking_status = "auditavel"
    elif publicity_score >= 55 and strong_ad and not editorial_price_only and not (news_score >= 75 and not has_technical_ad_signal(item)):
        checking_status = "parcial"
    elif publicity_score >= 35 and strong_ad and not editorial_price_only:
        checking_status = "revisao"
    else:
        checking_status = "rejeitado"

    news_status = "candidato" if news_score >= 55 and checking_status != "auditavel" else "ignorado"
    market_status = "incluido" if market_score >= 40 else "ignorado"

    if checking_status in {"auditavel", "parcial"}:
        content_type = "advertising"
    elif news_status == "candidato" and market_status == "incluido":
        content_type = "mixed"
    elif news_status == "candidato":
        content_type = "news"
    elif any(token in _text_for_item(item) for token in INSTITUTIONAL_TOKENS):
        content_type = "institutional"
    else:
        content_type = "unknown" if not editorial_context else "news"

    reasons = _clean_legacy_reasons(item.get("classification_reason"))
    if strong_ad:
        reasons.append("sinal_publicitario_forte")
    if preserved:
        reasons.append(f"evidencia_preservada:{evidence}")
    if editorial_context:
        reasons.append("contexto_editorial_ou_video")
    if editorial_price_only:
        reasons.append("noticia_com_valor_monetario_sem_cta")
    if market_status == "incluido":
        reasons.append("util_para_inteligencia_de_mercado")
    if news_status == "candidato":
        reasons.append("candidato_monitoramento_noticias")
    if not strong_ad and is_common_banner_size(item.get("normalized_width") or item.get("width"), item.get("normalized_height") or item.get("height")):
        reasons.append("formato_banner_insuficiente_para_checking")

    legacy_classification = {
        "advertising": "Publicidade",
        "news": "Editorial",
        "mixed": "Misto",
        "institutional": "Institucional",
        "unknown": "Indefinido",
    }.get(content_type, "Indefinido")

    return {
        **item,
        "content_type": content_type,
        "checking_status": checking_status,
        "market_status": market_status,
        "news_status": news_status,
        "publicity_score": publicity_score,
        "news_score": news_score,
        "market_score": market_score,
        "has_preserved_evidence": preserved,
        "evidence_type": evidence,
        "classification": legacy_classification,
        "classification_score": publicity_score,
        "classification_reason": ", ".join(_dedupe(reasons)),
    }
