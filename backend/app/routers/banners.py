from html import escape
from io import BytesIO
from uuid import UUID
from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import HTMLResponse, Response
from sqlalchemy import or_
from sqlalchemy.orm import Session

from app.db.models import BannerItem
from app.db.session import SessionLocal, get_db
from app.services.banner_service import scan_page_for_banners
from app.services.content_classifier import classify_detected_item
from app.services.registry_matcher import resolve_advertiser_for_item
from app.services.identification_review import apply_aliases_to_pending_items


router = APIRouter(prefix="/banners", tags=["Banners"])


MIN_PUBLICITY_SCORE = 28


def _as_uuid(value: str):
    try:
        return UUID(str(value))
    except Exception:
        raise HTTPException(status_code=400, detail="project_id inválido.")


def _row_text(row: dict) -> str:
    return " ".join(
        str(row.get(key) or "")
        for key in [
            "image_url",
            "alt_text",
            "ocr_text",
            "classification_reason",
            "source_name",
            "page_url",
        ]
    ).lower()


def _has_editorial_or_video_context(row: dict) -> bool:
    text = _row_text(row)

    blocked_terms = [
        "ytimg.com",
        "youtube.com",
        "youtu.be",
        "shorts",
        "ao vivo",
        "clicknews",
        "reflexão",
        "reflexao",
        "motivação",
        "motivacao",
        "notícia",
        "noticia",
        "morre",
        "preso",
        "suspeito",
        "polícia",
        "policia",
        "deputado",
        "governador",
        "cantor",
        "festival",
        "acidente",
    ]

    return any(term in text for term in blocked_terms)


def _has_strong_ad_context(row: dict) -> bool:
    """
    Sinais fortes de publicidade para checking real.

    Não basta OCR encontrar uma marca em uma imagem. Para aceitar
    automaticamente, precisa haver contexto técnico/publicitário:
    adserver, URL de banner, URL publicitária, link de anúncio ou
    texto comercial explícito.
    """
    reason = str(row.get("classification_reason") or "").lower()
    text = _row_text(row)

    if "+adserver" in reason:
        return True

    if "+banner_url" in reason:
        return True

    if "+commercial_text" in reason:
        return True

    if "+brand_url" in reason and not _has_editorial_or_video_context(row):
        return True

    technical_ad_tokens = [
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
    ]

    if any(token in text for token in technical_ad_tokens):
        return True

    commercial_tokens = [
        "compre",
        "oferta",
        "promoção",
        "promocao",
        "desconto",
        "apenas r$",
        "r$",
        "boleto",
        "assine",
        "contrate",
        "matricule-se",
        "inscreva-se",
    ]

    return any(token in text for token in commercial_tokens) and not _has_editorial_or_video_context(row)


def _is_accepted_publicity(row: dict) -> bool:
    """Aprovado automático apenas quando serve para checking real."""
    classified = row if row.get("checking_status") else classify_detected_item(row)
    return classified.get("checking_status") == "auditavel"


def _insert_banner_items(project_id: str, rows: list[dict]):
    db = SessionLocal()
    inserted = 0

    try:
        for row in rows:
            item = BannerItem(
                project_id=_as_uuid(project_id),
                page_url=row.get("page_url") or "",
                image_url=row.get("image_url"),
                alt_text=row.get("alt_text"),
                width=row.get("width") or 0,
                height=row.get("height") or 0,
                normalized_width=row.get("normalized_width") or 0,
                normalized_height=row.get("normalized_height") or 0,
                estimated_value=row.get("estimated_value") or 0,
                pos_x=row.get("pos_x") or 0,
                pos_y=row.get("pos_y") or 0,
                source_name=row.get("source_name"),
                evidence_html_key=row.get("evidence_html_key"),
                evidence_html_url=row.get("evidence_html_url"),
                screenshot_page_key=row.get("screenshot_page_key"),
                screenshot_page_url=row.get("screenshot_page_url"),
                screenshot_banner_key=row.get("screenshot_banner_key"),
                screenshot_banner_url=row.get("screenshot_banner_url"),
                ocr_text=row.get("ocr_text"),
                advertiser_name=row.get("advertiser_name"),
                classification=row.get("classification"),
                classification_score=row.get("classification_score") or 0,
                classification_reason=row.get("classification_reason"),
                content_type=row.get("content_type"),
                checking_status=row.get("checking_status"),
                market_status=row.get("market_status"),
                news_status=row.get("news_status"),
                publicity_score=row.get("publicity_score") or row.get("classification_score") or 0,
                news_score=row.get("news_score") or 0,
                market_score=row.get("market_score") or 0,
                has_preserved_evidence=bool(row.get("has_preserved_evidence")),
                evidence_type=row.get("evidence_type"),
            )

            db.add(item)
            inserted += 1

        db.commit()
        return inserted

    except Exception as exc:
        db.rollback()
        raise HTTPException(
            status_code=500,
            detail=f"Erro ao salvar banners coletados: {exc}",
        )

    finally:
        db.close()


@router.post("/scan/{project_id}")
def scan_banners_for_project(
    project_id: str,
    url: str = Query(..., description="URL da página que será escaneada"),
    save_rejected: bool = Query(
        default=True,
        description="Se true, salva todos os detectados para mercado/notícias; se false, salva só auditáveis.",
    ),
):
    raw_rows = [classify_detected_item(row) for row in scan_page_for_banners(project_id=project_id, url=url)]

    accepted_rows = [row for row in raw_rows if _is_accepted_publicity(row)]
    partial_rows = [row for row in raw_rows if row.get("checking_status") == "parcial"]
    review_rows = [row for row in raw_rows if row.get("checking_status") == "revisao"]
    rejected_rows = [row for row in raw_rows if row.get("checking_status") == "rejeitado"]
    market_rows = [row for row in raw_rows if row.get("market_status") == "incluido"]
    news_rows = [row for row in raw_rows if row.get("news_status") == "candidato"]

    rows_to_insert = raw_rows if save_rejected else accepted_rows

    inserted = _insert_banner_items(project_id, rows_to_insert)
    identification_auto = {"updated": 0, "message": "Autoidentificação não executada."}
    try:
        db = SessionLocal()
        try:
            identification_auto = apply_aliases_to_pending_items(db, project_id=project_id, limit=5000)
        finally:
            db.close()
    except Exception as exc:
        identification_auto = {"updated": 0, "error": str(exc)}

    return {
        "project_id": project_id,
        "url": url,
        "detected": len(raw_rows),
        "accepted": len(accepted_rows),
        "rejected": len(rejected_rows),
        "inserted": inserted,
        "auditables": len(accepted_rows),
        "checking": {
            "auditavel": len(accepted_rows),
            "parcial": len(partial_rows),
            "revisao": len(review_rows),
            "rejeitado": len(rejected_rows),
        },
        "market_intelligence": {
            "included": len(market_rows),
        },
        "news_monitoring": {
            "candidates": len(news_rows),
        },
        "min_publicity_score": MIN_PUBLICITY_SCORE,
        "saved_rejected": save_rejected,
        "saved_all": save_rejected,
        "identification_auto": identification_auto,
        "items": rows_to_insert,
        "rejected_items": rejected_rows[:20],
        "news_candidates": news_rows[:20],
    }


def _normalize_confidence(value: str | None) -> str:
    raw = (value or "").strip().lower()

    mapping = {
        "alta": "alta",
        "high": "alta",
        "media": "media",
        "média": "media",
        "medium": "media",
        "baixa": "baixa",
        "low": "baixa",
    }

    return mapping.get(raw, "não informado")


def detect_confidence_and_evidence(item: BannerItem) -> tuple[str, str | None]:
    confidence = None

    for attr in (
        "detection_confidence",
        "confidence",
        "identification_confidence",
        "match_confidence",
        "recognition_confidence",
        "quality",
    ):
        value = getattr(item, attr, None)
        if isinstance(value, str) and value.strip():
            confidence = value
            break

    if not confidence:
        score = getattr(item, "classification_score", None)

        try:
            score_num = float(score) if score is not None else None
        except (TypeError, ValueError):
            score_num = None

        if score_num is not None:
            if score_num >= 75:
                confidence = "alta"
            elif score_num >= 55:
                confidence = "media"
            else:
                confidence = "baixa"
        else:
            advertiser = (getattr(item, "advertiser_name", None) or "").strip().lower()
            if advertiser and advertiser not in {"nao identificado", "não identificado"}:
                confidence = "media"
            else:
                confidence = "baixa"

    evidence = None
    for attr in (
        "screenshot_banner_url",
        "evidence_html_url",
        "screenshot_page_url",
        "image_url",
        "evidence_url",
        "preview_url",
        "url",
        "link",
        "source_url",
        "page_url",
    ):
        value = getattr(item, attr, None)
        if isinstance(value, str) and value.strip():
            evidence = value
            break

    return _normalize_confidence(confidence), evidence


def _format_brl(value: int | float | None) -> str:
    value = value or 0
    return f"R$ {value:,.0f}".replace(",", ".")

def _is_publicity_classification(value: str | None) -> bool:
    raw = (value or "").strip().lower()

    if not raw:
        return True

    editorial_labels = {
        "editorial",
        "noticia",
        "notícia",
        "materia",
        "matéria",
        "conteudo editorial",
        "conteúdo editorial",
        "jornalismo",
        "post editorial",
    }

    return raw not in editorial_labels


def _serialize_banner(row: BannerItem, db: Session | None = None) -> dict:
    confidence, evidence = detect_confidence_and_evidence(row)

    created_at = getattr(row, "created_at", None)
    created_at_iso = created_at.isoformat() if created_at else None

    fallback = classify_detected_item({
        "page_url": getattr(row, "page_url", None),
        "image_url": getattr(row, "image_url", None),
        "alt_text": getattr(row, "alt_text", None),
        "ocr_text": getattr(row, "ocr_text", None),
        "width": getattr(row, "width", None),
        "height": getattr(row, "height", None),
        "normalized_width": getattr(row, "normalized_width", None),
        "normalized_height": getattr(row, "normalized_height", None),
        "source_name": getattr(row, "source_name", None),
        "advertiser_name": getattr(row, "advertiser_name", None),
        "classification_reason": getattr(row, "classification_reason", None),
        "screenshot_banner_url": getattr(row, "screenshot_banner_url", None),
        "screenshot_page_url": getattr(row, "screenshot_page_url", None),
        "evidence_html_url": getattr(row, "evidence_html_url", None),
    })

    registry_match = resolve_advertiser_for_item(db, row) if db is not None else None

    return {
        "id": str(getattr(row, "id", "") or ""),
        "project_id": str(getattr(row, "project_id", "") or ""),
        "page_url": getattr(row, "page_url", None),
        "image_url": getattr(row, "image_url", None),
        "alt_text": getattr(row, "alt_text", None),
        "width": getattr(row, "width", None),
        "height": getattr(row, "height", None),
        "normalized_width": getattr(row, "normalized_width", None),
        "normalized_height": getattr(row, "normalized_height", None),
        "estimated_value": getattr(row, "estimated_value", None),
        "pos_x": getattr(row, "pos_x", None),
        "pos_y": getattr(row, "pos_y", None),
        "source_name": getattr(row, "source_name", None),
        "evidence_html_key": getattr(row, "evidence_html_key", None),
        "evidence_html_url": getattr(row, "evidence_html_url", None),
        "screenshot_page_key": getattr(row, "screenshot_page_key", None),
        "screenshot_page_url": getattr(row, "screenshot_page_url", None),
        "screenshot_banner_key": getattr(row, "screenshot_banner_key", None),
        "screenshot_banner_url": getattr(row, "screenshot_banner_url", None),
        "ocr_text": getattr(row, "ocr_text", None),
        "advertiser_name": getattr(row, "advertiser_name", None),
        "classification": getattr(row, "classification", None),
        "classification_score": getattr(row, "classification_score", None),
        "classification_reason": getattr(row, "classification_reason", None),
        "content_type": getattr(row, "content_type", None) or fallback.get("content_type"),
        "checking_status": getattr(row, "checking_status", None) or fallback.get("checking_status"),
        "market_status": getattr(row, "market_status", None) or fallback.get("market_status"),
        "news_status": getattr(row, "news_status", None) or fallback.get("news_status"),
        "publicity_score": getattr(row, "publicity_score", None) if getattr(row, "publicity_score", None) is not None else fallback.get("publicity_score"),
        "news_score": getattr(row, "news_score", None) if getattr(row, "news_score", None) is not None else fallback.get("news_score"),
        "market_score": getattr(row, "market_score", None) if getattr(row, "market_score", None) is not None else fallback.get("market_score"),
        "has_preserved_evidence": getattr(row, "has_preserved_evidence", None) if getattr(row, "has_preserved_evidence", None) is not None else fallback.get("has_preserved_evidence"),
        "evidence_type": getattr(row, "evidence_type", None) or fallback.get("evidence_type"),
        "detection_confidence": confidence,
        "detection_evidence": evidence,
        "advertiser_registry_id": (registry_match or {}).get("advertiser_registry_id"),
        "advertiser_registry_name": (registry_match or {}).get("advertiser_registry_name"),
        "advertiser_type": (registry_match or {}).get("advertiser_type"),
        "advertiser_alias_matched": (registry_match or {}).get("advertiser_alias_matched"),
        "segment_id": (registry_match or {}).get("segment_id"),
        "segment_name": (registry_match or {}).get("segment_name"),
        "effective_advertiser_name": (registry_match or {}).get("advertiser_registry_name") or getattr(row, "advertiser_name", None),
        "created_at": created_at_iso,
    }


def _parse_dt(value: str | None):
    if not value:
        return None

    try:
        normalized = str(value).replace("Z", "+00:00")
        return datetime.fromisoformat(normalized).replace(tzinfo=None)
    except Exception:
        return None


def _get_banner_rows(
    project_id: str,
    db: Session,
    advertiser_name: str | None = None,
    source_name: str | None = None,
    format_size: str | None = None,
    classification: str | None = None,
    usage_scope: str | None = None,
    content_type: str | None = None,
    checking_status: str | None = None,
    market_status: str | None = None,
    news_status: str | None = None,
    min_publicity_score: int | None = None,
    min_news_score: int | None = None,
    preserved_only: bool | None = None,
    date_from: str | None = None,
    date_to: str | None = None,
    q: str | None = None,
    registry_advertiser_id: str | None = None,
    segment_id: str | None = None,
    limit: int = 300,
):
    query = db.query(BannerItem).filter(BannerItem.project_id == project_id)

    if advertiser_name:
        query = query.filter(BannerItem.advertiser_name == advertiser_name)

    if source_name:
        query = query.filter(BannerItem.source_name == source_name)

    if classification:
        query = query.filter(BannerItem.classification == classification)

    if content_type:
        query = query.filter(BannerItem.content_type == content_type)

    if checking_status:
        query = query.filter(BannerItem.checking_status == checking_status)

    if market_status:
        query = query.filter(BannerItem.market_status == market_status)

    if news_status:
        query = query.filter(BannerItem.news_status == news_status)

    if min_publicity_score is not None:
        query = query.filter(BannerItem.publicity_score >= min_publicity_score)

    if min_news_score is not None:
        query = query.filter(BannerItem.news_score >= min_news_score)

    if preserved_only is True:
        query = query.filter(BannerItem.has_preserved_evidence.is_(True))

    parsed_from = _parse_dt(date_from)
    if parsed_from:
        query = query.filter(BannerItem.created_at >= parsed_from)

    parsed_to = _parse_dt(date_to)
    if parsed_to:
        query = query.filter(BannerItem.created_at <= parsed_to)

    if q:
        like = f"%{q.strip()}%"
        query = query.filter(
            or_(
                BannerItem.advertiser_name.ilike(like),
                BannerItem.source_name.ilike(like),
                BannerItem.alt_text.ilike(like),
                BannerItem.ocr_text.ilike(like),
                BannerItem.page_url.ilike(like),
                BannerItem.image_url.ilike(like),
            )
        )

    rows = query.order_by(BannerItem.created_at.desc()).all()

    filtered_rows = []
    for row in rows:
        if usage_scope == "checking" and getattr(row, "checking_status", None) not in {"auditavel", "parcial", "revisao"}:
            continue

        if usage_scope == "market" and getattr(row, "market_status", None) != "incluido":
            continue

        if usage_scope == "news" and getattr(row, "news_status", None) != "candidato":
            continue

        current_format = f"{getattr(row, 'width', 0) or 0}x{getattr(row, 'height', 0) or 0}"
        normalized_format = f"{getattr(row, 'normalized_width', 0) or 0}x{getattr(row, 'normalized_height', 0) or 0}"
        if format_size and format_size not in {current_format, normalized_format}:
            continue

        serialized = _serialize_banner(row, db)

        if registry_advertiser_id and serialized.get("advertiser_registry_id") != registry_advertiser_id:
            continue

        if segment_id and serialized.get("segment_id") != segment_id:
            continue

        filtered_rows.append(serialized)

        if len(filtered_rows) >= limit:
            break

    return filtered_rows

def _get_banner_by_id(db: Session, banner_id: str) -> BannerItem | None:
    return db.query(BannerItem).filter(BannerItem.id == banner_id).first()

@router.get("/{project_id}")
def list_banners(
    project_id: str,
    advertiser_name: str | None = Query(default=None),
    source_name: str | None = Query(default=None),
    format_size: str | None = Query(default=None),
    classification: str | None = Query(default=None),
    usage_scope: str | None = Query(default=None, description="all, checking, market ou news"),
    content_type: str | None = Query(default=None, description="advertising, news, mixed, institutional, unknown"),
    checking_status: str | None = Query(default=None, description="auditavel, parcial, revisao ou rejeitado"),
    market_status: str | None = Query(default=None, description="incluido ou ignorado"),
    news_status: str | None = Query(default=None, description="candidato ou ignorado"),
    min_publicity_score: int | None = Query(default=None, ge=0, le=100),
    min_news_score: int | None = Query(default=None, ge=0, le=100),
    preserved_only: bool | None = Query(default=None),
    date_from: str | None = Query(default=None),
    date_to: str | None = Query(default=None),
    q: str | None = Query(default=None, description="Busca em anunciante, portal, texto, URL e OCR"),
    registry_advertiser_id: str | None = Query(default=None, description="ID do anunciante cadastrado"),
    segment_id: str | None = Query(default=None, description="ID do segmento cadastrado"),
    limit: int = Query(default=300, ge=1, le=1000),
    db: Session = Depends(get_db),
):
    return _get_banner_rows(
        project_id=project_id,
        db=db,
        advertiser_name=advertiser_name,
        source_name=source_name,
        format_size=format_size,
        classification=classification,
        usage_scope=usage_scope,
        content_type=content_type,
        checking_status=checking_status,
        market_status=market_status,
        news_status=news_status,
        min_publicity_score=min_publicity_score,
        min_news_score=min_news_score,
        preserved_only=preserved_only,
        date_from=date_from,
        date_to=date_to,
        q=q,
        registry_advertiser_id=registry_advertiser_id,
        segment_id=segment_id,
        limit=limit,
    )


@router.get("/item/{banner_id}")
def get_banner_item(
    banner_id: str,
    db: Session = Depends(get_db),
):
    row = _get_banner_by_id(db, banner_id)
    if not row:
        return {"error": "Banner não encontrado"}

    return _serialize_banner(row, db)

@router.get("/report/{project_id}", response_class=HTMLResponse)
def report_banners_html(
    project_id: str,
    advertiser_name: str | None = Query(default=None),
    source_name: str | None = Query(default=None),
    format_size: str | None = Query(default=None),
    classification: str | None = Query(default=None),
    db: Session = Depends(get_db),
):
    rows = _get_banner_rows(
        project_id=project_id,
        db=db,
        advertiser_name=advertiser_name,
        source_name=source_name,
        format_size=format_size,
        classification=classification,
        limit=500,
    )

    total_items = len(rows)
    total_value = sum((row.get("estimated_value") or 0) for row in rows)

    html_rows = []
    for row in rows:
        advertiser = escape(str(row.get("advertiser_name") or "Nao identificado"))
        portal = escape(str(row.get("source_name") or "Desconhecido"))
        description = escape(str(row.get("classification") or "Sem classificação"))
        created_at = escape(str(row.get("created_at") or "-"))
        confidence = escape(str(row.get("detection_confidence") or "não informado"))
        value = _format_brl(row.get("estimated_value") or 0)
        evidence = row.get("screenshot_banner_url") or row.get("screenshot_page_url") or row.get("evidence_html_url") or row.get("image_url") or row.get("page_url")

        evidence_html = (
            f'<a href="{escape(str(evidence))}" target="_blank" rel="noreferrer">Abrir</a>'
            if evidence
            else "<span>Sem link</span>"
        )

        html_rows.append(
            f"""
            <tr>
              <td>{advertiser}</td>
              <td>{portal}</td>
              <td>{description}</td>
              <td>{created_at}</td>
              <td>{confidence}</td>
              <td>{value}</td>
              <td>{evidence_html}</td>
            </tr>
            """
        )

    html = f"""
    <!doctype html>
    <html lang="pt-BR">
    <head>
      <meta charset="utf-8" />
      <title>Relatório de Evidências de Banners</title>
      <style>
        body {{
          font-family: Arial, Helvetica, sans-serif;
          margin: 0;
          padding: 24px;
          background: #f6f7fb;
          color: #1f2937;
        }}
        .wrap {{
          max-width: 1280px;
          margin: 0 auto;
        }}
        .hero {{
          background: linear-gradient(135deg, #7a1118 0%, #b91c1c 45%, #d93636 100%);
          color: #fff;
          border-radius: 24px;
          padding: 28px;
          margin-bottom: 24px;
        }}
        .eyebrow {{
          font-size: 12px;
          letter-spacing: 0.18em;
          text-transform: uppercase;
          font-weight: 700;
          opacity: 0.9;
        }}
        h1 {{
          margin: 10px 0 8px;
          font-size: 38px;
        }}
        p {{
          margin: 0;
          font-size: 16px;
          opacity: 0.92;
        }}
        .summary {{
          display: grid;
          grid-template-columns: repeat(2, minmax(0, 1fr));
          gap: 16px;
          margin-bottom: 24px;
        }}
        .card {{
          background: #fff;
          border: 1px solid #e5e7eb;
          border-radius: 18px;
          padding: 18px 20px;
        }}
        .label {{
          font-size: 12px;
          text-transform: uppercase;
          letter-spacing: 0.12em;
          color: #6b7280;
        }}
        .value {{
          margin-top: 8px;
          font-size: 28px;
          font-weight: 800;
          color: #111827;
        }}
        table {{
          width: 100%;
          border-collapse: collapse;
          background: #fff;
          border-radius: 18px;
          overflow: hidden;
          border: 1px solid #e5e7eb;
        }}
        thead {{
          background: #c52625;
          color: #fff;
        }}
        th, td {{
          text-align: left;
          padding: 12px 10px;
          border-bottom: 1px solid #eef0f4;
          vertical-align: top;
          font-size: 14px;
        }}
        th {{
          font-size: 13px;
        }}
        a {{
          color: #991b1b;
          font-weight: 700;
          text-decoration: none;
        }}
      </style>
    </head>
    <body>
      <div class="wrap">
        <section class="hero">
          <div class="eyebrow">TV Fiscal WebMonitor</div>
          <h1>Relatório de Evidências de Banners</h1>
          <p>Projeto monitorado: {escape(project_id)}</p>
        </section>

        <section class="summary">
          <div class="card">
            <div class="label">Evidências listadas</div>
            <div class="value">{total_items}</div>
          </div>
          <div class="card">
            <div class="label">Investimento estimado</div>
            <div class="value">{_format_brl(total_value)}</div>
          </div>
        </section>

        <table>
          <thead>
            <tr>
              <th>Anunciante</th>
              <th>Portal</th>
              <th>Descrição</th>
              <th>Data</th>
              <th>Confiança</th>
              <th>Valor</th>
              <th>Evidência</th>
            </tr>
          </thead>
          <tbody>
            {''.join(html_rows) if html_rows else '<tr><td colspan="7">Nenhuma evidência encontrada.</td></tr>'}
          </tbody>
        </table>
      </div>
    </body>
    </html>
    """
    return HTMLResponse(content=html)


@router.get("/report-pdf/{project_id}")
def report_banners_pdf(
    project_id: str,
    advertiser_name: str | None = Query(default=None),
    source_name: str | None = Query(default=None),
    format_size: str | None = Query(default=None),
    classification: str | None = Query(default=None),
    db: Session = Depends(get_db),
):
    from reportlab.lib import colors
    from reportlab.lib.pagesizes import A4, landscape
    from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
    from reportlab.lib.units import mm
    from reportlab.platypus import Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle

    rows = _get_banner_rows(
        project_id=project_id,
        db=db,
        advertiser_name=advertiser_name,
        source_name=source_name,
        format_size=format_size,
        classification=classification,
        limit=500,
    )

    total_items = len(rows)
    total_value = sum((row.get("estimated_value") or 0) for row in rows)

    buffer = BytesIO()
    doc = SimpleDocTemplate(
        buffer,
        pagesize=landscape(A4),
        leftMargin=16 * mm,
        rightMargin=16 * mm,
        topMargin=14 * mm,
        bottomMargin=12 * mm,
    )

    styles = getSampleStyleSheet()

    title_style = ParagraphStyle(
        "title_style",
        parent=styles["Heading1"],
        fontName="Helvetica-Bold",
        fontSize=24,
        leading=28,
        textColor=colors.white,
    )

    brand_style = ParagraphStyle(
        "brand_style",
        parent=styles["Normal"],
        fontName="Helvetica-Bold",
        fontSize=10,
        leading=12,
        textColor=colors.white,
    )

    subtitle_style = ParagraphStyle(
        "subtitle_style",
        parent=styles["Normal"],
        fontName="Helvetica",
        fontSize=11,
        leading=14,
        textColor=colors.HexColor("#4B5563"),
    )

    label_style = ParagraphStyle(
        "label_style",
        parent=styles["Normal"],
        fontName="Helvetica",
        fontSize=9,
        leading=11,
        textColor=colors.HexColor("#6B7280"),
    )

    value_style = ParagraphStyle(
        "value_style",
        parent=styles["Normal"],
        fontName="Helvetica-Bold",
        fontSize=20,
        leading=24,
        textColor=colors.HexColor("#111827"),
    )

    value_red_style = ParagraphStyle(
        "value_red_style",
        parent=value_style,
        textColor=colors.HexColor("#C52625"),
    )

    section_style = ParagraphStyle(
        "section_style",
        parent=styles["Heading2"],
        fontName="Helvetica-Bold",
        fontSize=14,
        leading=18,
        textColor=colors.HexColor("#111827"),
        spaceAfter=8,
    )

    table_header_style = ParagraphStyle(
        "table_header_style",
        parent=styles["Normal"],
        fontName="Helvetica-Bold",
        fontSize=9,
        leading=11,
        textColor=colors.white,
    )

    table_cell_style = ParagraphStyle(
        "table_cell_style",
        parent=styles["Normal"],
        fontName="Helvetica",
        fontSize=8.5,
        leading=10,
        textColor=colors.HexColor("#111827"),
    )

    story = []

    header = Table(
        [[
            Paragraph("TV Fiscal WebMonitor", brand_style),
            Paragraph("Relatório de Evidências de Banners", title_style),
        ]],
        colWidths=[60 * mm, 200 * mm],
    )
    header.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, -1), colors.HexColor("#C52625")),
        ("LEFTPADDING", (0, 0), (-1, -1), 14),
        ("RIGHTPADDING", (0, 0), (-1, -1), 14),
        ("TOPPADDING", (0, 0), (-1, -1), 12),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 14),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
    ]))
    story.append(header)
    story.append(Spacer(1, 8))
    story.append(Paragraph(f"<b>Projeto monitorado:</b> {escape(project_id)}", subtitle_style))
    story.append(Spacer(1, 6))

    summary = Table(
        [[
            Paragraph("Evidências listadas", label_style),
            Paragraph("Investimento estimado", label_style),
        ],
        [
            Paragraph(str(total_items), value_style),
            Paragraph(_format_brl(total_value), value_red_style),
        ]],
        colWidths=[60 * mm, 70 * mm],
    )
    summary.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, -1), colors.white),
        ("BOX", (0, 0), (-1, -1), 0.6, colors.HexColor("#E5E7EB")),
        ("INNERGRID", (0, 0), (-1, -1), 0.4, colors.HexColor("#E5E7EB")),
        ("LEFTPADDING", (0, 0), (-1, -1), 12),
        ("RIGHTPADDING", (0, 0), (-1, -1), 12),
        ("TOPPADDING", (0, 0), (-1, -1), 10),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 10),
    ]))
    story.append(summary)
    story.append(Spacer(1, 12))
    story.append(Paragraph("Evidências monitoradas", section_style))

    data = [[
        Paragraph("Anunciante", table_header_style),
        Paragraph("Portal", table_header_style),
        Paragraph("Descrição", table_header_style),
        Paragraph("Data", table_header_style),
        Paragraph("Confiança", table_header_style),
        Paragraph("Valor", table_header_style),
    ]]

    for row in rows[:80]:
        data.append([
            Paragraph(escape(str(row.get("advertiser_name") or "Nao identificado")), table_cell_style),
            Paragraph(escape(str(row.get("source_name") or "Desconhecido")), table_cell_style),
            Paragraph(escape(str(row.get("classification") or "Sem classificação")), table_cell_style),
            Paragraph(escape(str(row.get("created_at") or "-")), table_cell_style),
            Paragraph(escape(str(row.get("detection_confidence") or "não informado")), table_cell_style),
            Paragraph(_format_brl(row.get("estimated_value") or 0), table_cell_style),
        ])

    table = Table(
        data,
        colWidths=[48 * mm, 48 * mm, 50 * mm, 40 * mm, 26 * mm, 24 * mm],
        repeatRows=1,
    )
    table.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#C52625")),
        ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
        ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, colors.HexColor("#F9FAFB")]),
        ("BOX", (0, 0), (-1, -1), 0.6, colors.HexColor("#E5E7EB")),
        ("INNERGRID", (0, 0), (-1, -1), 0.35, colors.HexColor("#E5E7EB")),
        ("LEFTPADDING", (0, 0), (-1, -1), 6),
        ("RIGHTPADDING", (0, 0), (-1, -1), 6),
        ("TOPPADDING", (0, 0), (-1, -1), 5),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
    ]))
    story.append(table)

    doc.build(story)

    pdf_bytes = buffer.getvalue()
    buffer.close()

    return Response(
        content=pdf_bytes,
        media_type="application/pdf",
        headers={
            "Content-Disposition": f'inline; filename="banners_report_{project_id}.pdf"'
        },
    )