from __future__ import annotations

import hashlib
import re
import unicodedata
from collections import defaultdict
from datetime import datetime
from typing import Any

from sqlalchemy.orm import Session

from app.db.models import Advertiser, AdvertiserAlias, BannerItem
from app.services.identification_quality import is_unknown_advertiser


def _norm(value: Any) -> str:
    text = str(value or "").strip().lower()
    text = unicodedata.normalize("NFKD", text)
    text = "".join(ch for ch in text if not unicodedata.combining(ch))
    text = re.sub(r"https?://", "", text)
    text = re.sub(r"[^a-z0-9]+", " ", text)
    return re.sub(r"\s+", " ", text).strip()


def _short(value: Any, limit: int = 180) -> str:
    text = re.sub(r"\s+", " ", str(value or "").strip())
    if len(text) <= limit:
        return text
    return text[: limit - 1].rstrip() + "…"


def _safe_alias(value: Any) -> str:
    alias = re.sub(r"\s+", " ", str(value or "").strip())
    alias = alias.strip("|,.;:·—- ")
    return alias[:255]


def is_pending_identification(item: BannerItem) -> bool:
    status = (getattr(item, "identification_status", None) or "").strip().lower()
    if status in {"qualificado", "qualificado_auto", "ignorado"}:
        return False
    if getattr(item, "market_status", None) != "incluido":
        return False
    return is_unknown_advertiser(getattr(item, "advertiser_name", None))


def make_identification_group_key(item: BannerItem) -> str:
    """Agrupa peças semelhantes para qualificação em lote.

    A chave privilegia a URL da imagem porque muitas inserções repetidas
    do mesmo banner aparecem em horários e portais diferentes. Quando a
    imagem não é suficiente, usa OCR/ALT, formato e portal.
    """
    image = _norm(getattr(item, "image_url", None))
    if image:
        source = f"image:{image}"
    else:
        parts = [
            _norm(getattr(item, "ocr_text", None))[:180],
            _norm(getattr(item, "alt_text", None))[:180],
            _norm(getattr(item, "source_name", None))[:80],
            str(getattr(item, "normalized_width", None) or getattr(item, "width", None) or ""),
            str(getattr(item, "normalized_height", None) or getattr(item, "height", None) or ""),
        ]
        source = "fallback:" + "|".join(parts)
    return hashlib.sha1(source.encode("utf-8")).hexdigest()[:16]


def _best_preview(item: BannerItem) -> str | None:
    for attr in ("screenshot_banner_url", "screenshot_page_url", "evidence_html_url", "image_url", "page_url"):
        value = getattr(item, attr, None)
        if value:
            return value
    return None


def _group_suggestion(item: BannerItem) -> str:
    for attr in ("ocr_text", "alt_text", "image_url", "page_url"):
        value = getattr(item, attr, None)
        if value:
            return _short(value, 120)
    return "Sem texto sugestivo"


def _item_search_text(item: BannerItem) -> str:
    return _norm(" ".join(
        str(getattr(item, attr, None) or "")
        for attr in (
            "ocr_text",
            "alt_text",
            "image_url",
            "page_url",
            "classification_reason",
            "source_name",
        )
    ))


def _alias_matches(alias: str, haystack_norm: str) -> bool:
    alias_norm = _norm(alias)
    if len(alias_norm) < 3:
        return False
    # Normalização já separa pontuação por espaços; usar bordas evita falsos positivos
    # como "amil" dentro de "família".
    return f" {alias_norm} " in f" {haystack_norm} "


def _active_aliases(db: Session) -> list[tuple[Advertiser, str, str]]:
    advertisers = db.query(Advertiser).filter(Advertiser.active.is_(True)).all()
    aliases = db.query(AdvertiserAlias).filter(AdvertiserAlias.active.is_(True)).all()

    by_adv: dict[str, Advertiser] = {str(adv.id): adv for adv in advertisers}
    pairs: list[tuple[Advertiser, str, str]] = []
    for adv in advertisers:
        pairs.append((adv, adv.name, "nome"))
        if getattr(adv, "legal_name", None):
            pairs.append((adv, adv.legal_name, "razao_social"))
    for alias in aliases:
        adv = by_adv.get(str(alias.advertiser_id))
        if adv:
            pairs.append((adv, alias.alias, "alias"))

    # Alias maior primeiro reduz colisões de termos curtos.
    pairs = [p for p in pairs if len(_norm(p[1])) >= 3]
    pairs.sort(key=lambda p: len(_norm(p[1])), reverse=True)
    return pairs


def _find_alias_match(item: BannerItem, aliases: list[tuple[Advertiser, str, str]]) -> tuple[Advertiser, str, str] | None:
    haystack = _item_search_text(item)
    if not haystack:
        return None
    for adv, alias, origin in aliases:
        if _alias_matches(alias, haystack):
            return adv, alias, origin
    return None


def list_identification_groups(db: Session, project_id: str, limit: int = 120) -> dict:
    rows = (
        db.query(BannerItem)
        .filter(BannerItem.project_id == project_id)
        .filter(BannerItem.market_status == "incluido")
        .order_by(BannerItem.created_at.desc())
        .all()
    )

    aliases = _active_aliases(db)
    groups: dict[str, dict] = {}
    total_pending_items = 0
    total_pending_investment = 0
    auto_suggested_groups = 0

    for item in rows:
        if not is_pending_identification(item):
            continue
        total_pending_items += 1
        total_pending_investment += int(getattr(item, "estimated_value", None) or 0)
        key = make_identification_group_key(item)
        group = groups.get(key)
        if not group:
            match = _find_alias_match(item, aliases)
            group = {
                "group_key": key,
                "count": 0,
                "estimated_investment": 0,
                "sample_id": str(item.id),
                "sample_image_url": getattr(item, "image_url", None),
                "sample_page_url": getattr(item, "page_url", None),
                "sample_preview_url": _best_preview(item),
                "sample_ocr": _short(getattr(item, "ocr_text", None), 240),
                "sample_alt": _short(getattr(item, "alt_text", None), 180),
                "source_name": getattr(item, "source_name", None),
                "format": f"{getattr(item, 'normalized_width', None) or getattr(item, 'width', None) or 0} x {getattr(item, 'normalized_height', None) or getattr(item, 'height', None) or 0}",
                "publicity_score": int(getattr(item, "publicity_score", None) or getattr(item, "classification_score", None) or 0),
                "market_score": int(getattr(item, "market_score", None) or 0),
                "confidence_hint": getattr(item, "classification", None) or "pendente",
                "suggestion": _group_suggestion(item),
                "suggested_advertiser_id": str(match[0].id) if match else None,
                "suggested_advertiser_name": match[0].name if match else None,
                "suggested_alias": match[1] if match else None,
                "suggested_origin": match[2] if match else None,
                "first_seen": item.created_at.isoformat() if getattr(item, "created_at", None) else None,
                "last_seen": item.created_at.isoformat() if getattr(item, "created_at", None) else None,
                "portals": set(),
                "items": [],
            }
            if match:
                auto_suggested_groups += 1
            groups[key] = group

        group["count"] += 1
        group["estimated_investment"] += int(getattr(item, "estimated_value", None) or 0)
        group["publicity_score"] = max(group["publicity_score"], int(getattr(item, "publicity_score", None) or 0))
        group["market_score"] = max(group["market_score"], int(getattr(item, "market_score", None) or 0))
        if getattr(item, "source_name", None):
            group["portals"].add(getattr(item, "source_name"))
        if getattr(item, "created_at", None):
            iso = item.created_at.isoformat()
            group["first_seen"] = min(group["first_seen"] or iso, iso)
            group["last_seen"] = max(group["last_seen"] or iso, iso)
        if len(group["items"]) < 8:
            group["items"].append({
                "id": str(item.id),
                "portal": getattr(item, "source_name", None),
                "page_url": getattr(item, "page_url", None),
                "image_url": getattr(item, "image_url", None),
                "value": int(getattr(item, "estimated_value", None) or 0),
                "created_at": item.created_at.isoformat() if getattr(item, "created_at", None) else None,
            })

    ordered = sorted(groups.values(), key=lambda g: (g["estimated_investment"], g["count"]), reverse=True)
    payload_groups = []
    for group in ordered[: max(1, min(limit, 500))]:
        group["portals"] = sorted(group["portals"])
        group["portals_count"] = len(group["portals"])
        payload_groups.append(group)

    return {
        "project_id": str(project_id),
        "groups": payload_groups,
        "summary": {
            "pending_groups": len(groups),
            "pending_items": total_pending_items,
            "pending_investment": total_pending_investment,
            "auto_suggested_groups": auto_suggested_groups,
        },
    }


def identification_quality_summary(db: Session, project_id: str) -> dict:
    rows = (
        db.query(BannerItem)
        .filter(BannerItem.project_id == project_id)
        .filter(BannerItem.market_status == "incluido")
        .all()
    )
    total = len(rows)
    total_investment = sum(int(getattr(item, "estimated_value", None) or 0) for item in rows)
    pending_items = 0
    pending_investment = 0
    identified_items = 0
    identified_investment = 0
    qualified_manual = 0
    qualified_auto = 0
    ignored = 0
    auditables_pending = 0

    for item in rows:
        status = (getattr(item, "identification_status", None) or "").strip().lower()
        if status == "qualificado":
            qualified_manual += 1
        elif status == "qualificado_auto":
            qualified_auto += 1
        elif status == "ignorado":
            ignored += 1

        if is_pending_identification(item):
            pending_items += 1
            pending_investment += int(getattr(item, "estimated_value", None) or 0)
            if getattr(item, "checking_status", None) == "auditavel":
                auditables_pending += 1
        elif not is_unknown_advertiser(getattr(item, "advertiser_name", None)):
            identified_items += 1
            identified_investment += int(getattr(item, "estimated_value", None) or 0)

    identified_rate = round((identified_items / total) * 100, 2) if total else 0.0
    pending_rate = round((pending_items / total) * 100, 2) if total else 0.0
    return {
        "project_id": str(project_id),
        "total_market_items": total,
        "total_market_investment": total_investment,
        "identified_items": identified_items,
        "identified_investment": identified_investment,
        "pending_items": pending_items,
        "pending_investment": pending_investment,
        "auditables_pending": auditables_pending,
        "qualified_manual": qualified_manual,
        "qualified_auto": qualified_auto,
        "ignored": ignored,
        "identified_rate": identified_rate,
        "pending_rate": pending_rate,
        "quality_label": "boa" if pending_rate < 15 else "atenção" if pending_rate < 35 else "crítica",
    }


def _matching_group_items(db: Session, project_id: str, group_key: str) -> list[BannerItem]:
    rows = (
        db.query(BannerItem)
        .filter(BannerItem.project_id == project_id)
        .filter(BannerItem.market_status == "incluido")
        .all()
    )
    return [item for item in rows if is_pending_identification(item) and make_identification_group_key(item) == group_key]


def qualify_group(
    db: Session,
    project_id: str,
    group_key: str,
    advertiser_id: str,
    create_alias: bool = True,
    alias: str | None = None,
    note: str | None = None,
    apply_alias_to_pending: bool = False,
) -> dict:
    advertiser = db.query(Advertiser).filter(Advertiser.id == advertiser_id).first()
    if not advertiser:
        raise ValueError("Anunciante não encontrado.")

    rows = _matching_group_items(db, project_id, group_key)
    if not rows:
        return {"updated": 0, "message": "Nenhum item pendente encontrado para este grupo."}

    now = datetime.utcnow()
    updated = 0
    for item in rows:
        item.advertiser_name = advertiser.name
        item.qualified_advertiser_id = advertiser.id
        item.identification_status = "qualificado"
        item.qualified_at = now
        parts = [p for p in [getattr(item, "classification_reason", None), "qualificacao_manual", note] if p]
        item.classification_reason = ", ".join(dict.fromkeys(parts))
        item.identification_note = note or f"Qualificado manualmente como {advertiser.name}."
        updated += 1

    alias_created = False
    alias_value = ""
    if create_alias:
        alias_value = _safe_alias(alias or _group_suggestion(rows[0]) or advertiser.name)
        if alias_value and len(alias_value) <= 255:
            existing = (
                db.query(AdvertiserAlias)
                .filter(AdvertiserAlias.advertiser_id == advertiser.id, AdvertiserAlias.alias.ilike(alias_value))
                .first()
            )
            if not existing:
                db.add(AdvertiserAlias(advertiser_id=advertiser.id, alias=alias_value, active=True))
                alias_created = True

    db.commit()
    alias_updated = 0
    if create_alias and alias_value and apply_alias_to_pending:
        alias_updated = apply_aliases_to_pending_items(db, project_id=project_id, only_advertiser_id=str(advertiser.id))["updated"]

    return {
        "updated": updated,
        "alias_updated": alias_updated,
        "alias_created": alias_created,
        "advertiser": advertiser.name,
        "group_key": group_key,
        "message": f"{updated} item(ns) qualificado(s) como {advertiser.name}." + (f" {alias_updated} item(ns) adicionais por alias." if alias_updated else ""),
    }


def ignore_group(db: Session, project_id: str, group_key: str, note: str | None = None, remove_from_market: bool = True) -> dict:
    rows = _matching_group_items(db, project_id, group_key)
    if not rows:
        return {"updated": 0, "message": "Nenhum item pendente encontrado para este grupo."}
    now = datetime.utcnow()
    for item in rows:
        item.identification_status = "ignorado"
        item.identification_note = note or "Ignorado na qualificação comercial."
        item.qualified_at = now
        if remove_from_market:
            item.market_status = "ignorado"
        parts = [p for p in [getattr(item, "classification_reason", None), "ignorado_qualificacao_manual", note] if p]
        item.classification_reason = ", ".join(dict.fromkeys(parts))
    db.commit()
    return {
        "updated": len(rows),
        "group_key": group_key,
        "message": f"{len(rows)} item(ns) removido(s) da fila de identificação.",
    }


def apply_aliases_to_pending_items(db: Session, project_id: str, only_advertiser_id: str | None = None, limit: int = 5000) -> dict:
    aliases = _active_aliases(db)
    if only_advertiser_id:
        aliases = [(adv, alias, origin) for adv, alias, origin in aliases if str(adv.id) == str(only_advertiser_id)]
    if not aliases:
        return {"updated": 0, "matches": [], "message": "Nenhum alias ativo encontrado."}

    rows = (
        db.query(BannerItem)
        .filter(BannerItem.project_id == project_id)
        .filter(BannerItem.market_status == "incluido")
        .order_by(BannerItem.created_at.desc())
        .limit(max(1, min(limit, 20000)))
        .all()
    )
    now = datetime.utcnow()
    updated = 0
    by_advertiser: dict[str, dict] = {}

    for item in rows:
        if not is_pending_identification(item):
            continue
        match = _find_alias_match(item, aliases)
        if not match:
            continue
        advertiser, alias, origin = match
        item.advertiser_name = advertiser.name
        item.qualified_advertiser_id = advertiser.id
        item.identification_status = "qualificado_auto"
        item.qualified_at = now
        item.identification_note = f"Qualificado automaticamente por {origin}: {alias}."
        parts = [p for p in [getattr(item, "classification_reason", None), f"qualificacao_automatica_alias:{alias}"] if p]
        item.classification_reason = ", ".join(dict.fromkeys(parts))
        updated += 1
        row = by_advertiser.setdefault(str(advertiser.id), {"advertiser_id": str(advertiser.id), "advertiser": advertiser.name, "updated": 0, "aliases": set()})
        row["updated"] += 1
        row["aliases"].add(alias)

    db.commit()
    matches = []
    for row in by_advertiser.values():
        row["aliases"] = sorted(row["aliases"])
        matches.append(row)
    matches.sort(key=lambda r: r["updated"], reverse=True)
    return {
        "updated": updated,
        "matches": matches,
        "message": f"{updated} item(ns) qualificado(s) automaticamente por aliases.",
    }


def recent_identification_actions(db: Session, project_id: str, limit: int = 80) -> dict:
    rows = (
        db.query(BannerItem)
        .filter(BannerItem.project_id == project_id)
        .filter(BannerItem.identification_status.in_(["qualificado", "qualificado_auto", "ignorado"]))
        .order_by(BannerItem.qualified_at.desc().nullslast(), BannerItem.created_at.desc())
        .limit(max(1, min(limit, 300)))
        .all()
    )
    actions = []
    for item in rows:
        actions.append({
            "id": str(item.id),
            "status": getattr(item, "identification_status", None),
            "advertiser_name": getattr(item, "advertiser_name", None),
            "note": _short(getattr(item, "identification_note", None), 220),
            "portal": getattr(item, "source_name", None),
            "value": int(getattr(item, "estimated_value", None) or 0),
            "qualified_at": item.qualified_at.isoformat() if getattr(item, "qualified_at", None) else None,
            "created_at": item.created_at.isoformat() if getattr(item, "created_at", None) else None,
            "preview_url": _best_preview(item),
            "page_url": getattr(item, "page_url", None),
        })
    return {"project_id": str(project_id), "actions": actions}
