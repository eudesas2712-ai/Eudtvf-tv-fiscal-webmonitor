from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from collections import defaultdict

from app.db.session import get_db
from app.db.models import BannerItem

router = APIRouter(prefix="/intel", tags=["Intel"])


@router.get("/{project_id}")
def intel_dashboard(project_id: str, db: Session = Depends(get_db)):
    rows = db.query(BannerItem).filter(BannerItem.project_id == project_id).all()

    total_investment = 0

    advertiser_investment = defaultdict(int)
    advertiser_portals = defaultdict(set)
    portal_revenue = defaultdict(int)

    for r in rows:
        if r.classification != "ad":
            continue

        value = r.estimated_value or 0
        total_investment += value

        advertiser = r.advertiser_name or "Nao identificado"
        portal = r.source_name or "Desconhecido"

        advertiser_investment[advertiser] += value
        advertiser_portals[advertiser].add(portal)
        portal_revenue[portal] += value

    # ranking anunciantes
    top_advertisers = sorted(
        [
            {
                "advertiser": k,
                "investment": v,
                "share": round((v / total_investment) * 100, 2) if total_investment else 0,
                "portals": len(advertiser_portals[k]),
            }
            for k, v in advertiser_investment.items()
        ],
        key=lambda x: x["investment"],
        reverse=True,
    )

    # ranking portais
    top_portals = sorted(
        [
            {
                "portal": k,
                "revenue": v,
                "share": round((v / total_investment) * 100, 2) if total_investment else 0,
            }
            for k, v in portal_revenue.items()
        ],
        key=lambda x: x["revenue"],
        reverse=True,
    )

    return {
        "total_investment": total_investment,
        "total_ads": len(rows),
        "top_advertisers": top_advertisers[:10],
        "top_portals": top_portals[:10],
    }