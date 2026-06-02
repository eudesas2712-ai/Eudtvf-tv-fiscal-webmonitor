from __future__ import annotations

import re
import unicodedata
from functools import lru_cache

from sqlalchemy.orm import Session

from app.db.models import Advertiser, AdvertiserAlias, Segment


def _norm(value: object) -> str:
    text = str(value or "").strip().lower()
    text = unicodedata.normalize("NFKD", text)
    text = "".join(ch for ch in text if not unicodedata.combining(ch))
    text = re.sub(r"[^a-z0-9]+", " ", text)
    return re.sub(r"\s+", " ", text).strip()


def _haystack_from_item(item: object) -> str:
    fields = []
    for attr in (
        "advertiser_name",
        "alt_text",
        "ocr_text",
        "classification_reason",
        "image_url",
        "link_url",
        "page_url",
        "source_name",
    ):
        if isinstance(item, dict):
            fields.append(item.get(attr))
        else:
            fields.append(getattr(item, attr, None))
    return f" {_norm(' '.join(str(f or '') for f in fields))} "


def resolve_advertiser_for_item(db: Session, item: object) -> dict | None:
    """Resolve o anunciante cadastrado por aliases e retorna segmento.

    O casamento é propositalmente lexical/explicável para permitir auditoria:
    o usuário vê exatamente qual alias acionou o vínculo.
    """
    haystack = _haystack_from_item(item)
    if not haystack.strip():
        return None

    rows = (
        db.query(AdvertiserAlias, Advertiser, Segment)
        .join(Advertiser, AdvertiserAlias.advertiser_id == Advertiser.id)
        .outerjoin(Segment, Advertiser.segment_id == Segment.id)
        .filter(Advertiser.active.is_(True), AdvertiserAlias.active.is_(True))
        .all()
    )

    best = None
    for alias, advertiser, segment in rows:
        alias_norm = _norm(alias.alias)
        if len(alias_norm) < 3:
            continue
        pattern = f" {alias_norm} "
        if pattern in haystack:
            candidate = {
                "advertiser_registry_id": str(advertiser.id),
                "advertiser_registry_name": advertiser.name,
                "advertiser_type": advertiser.advertiser_type,
                "advertiser_alias_matched": alias.alias,
                "segment_id": str(segment.id) if segment else None,
                "segment_name": segment.name if segment else None,
                "match_len": len(alias_norm),
            }
            if best is None or candidate["match_len"] > best["match_len"]:
                best = candidate

    if not best:
        return None

    best.pop("match_len", None)
    return best
