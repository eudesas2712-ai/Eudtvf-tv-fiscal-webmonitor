from collections import defaultdict
from itertools import combinations


def _safe_float(value) -> float:
    try:
        return float(value or 0)
    except (TypeError, ValueError):
        return 0.0


def build_competitive_map(portal_ranking_data, banner_items_data):
    portal_to_advertisers = defaultdict(set)
    advertiser_portal_investment = defaultdict(float)
    advertiser_total_investment = defaultdict(float)

    # 1. Base por portal e anunciante
    for item in banner_items_data:
        advertiser = item.get("advertiser") or "Nao identificado"
        portal = item.get("portal") or "Desconhecido"
        investment = _safe_float(item.get("investment", 0))

        if advertiser == "Nao identificado":
            continue

        portal_to_advertisers[portal].add(advertiser)
        advertiser_portal_investment[(advertiser, portal)] += investment
        advertiser_total_investment[advertiser] += investment

    pair_stats = defaultdict(
        lambda: {
            "shared_portals": set(),
            "combined_investment": 0.0,
            "pair_hits": 0,
            "investment_a": 0.0,
            "investment_b": 0.0,
            "balance_score": 0.0,
            "rivalry_score": 0.0,
        }
    )

    # 2. Pares reais por portal
    for portal, advertisers in portal_to_advertisers.items():
        advertisers = sorted(advertisers)
        if len(advertisers) < 2:
            continue

        for a1, a2 in combinations(advertisers, 2):
            key = (a1, a2)
            pair_stats[key]["shared_portals"].add(portal)

    # 3. Investimento combinado por par/portal
    for (a1, a2), stats in pair_stats.items():
        inv_a_total = 0.0
        inv_b_total = 0.0

        for portal in stats["shared_portals"]:
            inv_a = advertiser_portal_investment.get((a1, portal), 0.0)
            inv_b = advertiser_portal_investment.get((a2, portal), 0.0)

            inv_a_total += inv_a
            inv_b_total += inv_b
            stats["combined_investment"] += inv_a + inv_b
            stats["pair_hits"] += 1

        stats["investment_a"] = round(inv_a_total, 2)
        stats["investment_b"] = round(inv_b_total, 2)

        max_inv = max(inv_a_total, inv_b_total, 1.0)
        gap = abs(inv_a_total - inv_b_total)

        # quanto menor a diferença, maior o equilíbrio competitivo
        balance_score = round(100 - min((gap / max_inv) * 100, 100), 2)
        stats["balance_score"] = balance_score

        shared_portals_count = len(stats["shared_portals"])
        combined_investment = stats["combined_investment"]

        # score principal: presença conjunta + investimento + equilíbrio
        rivalry_score = round(
            (shared_portals_count * 8)
            + (combined_investment / 3500)
            + (stats["pair_hits"] * 3)
            + (balance_score * 0.25),
            2,
        )
        stats["rivalry_score"] = rivalry_score

    competitive_map = []

    for (a1, a2), stats in pair_stats.items():
        competitive_map.append(
            {
                "advertiser_a": a1,
                "advertiser_b": a2,
                "shared_portals": sorted(list(stats["shared_portals"])),
                "shared_portals_count": len(stats["shared_portals"]),
                "combined_investment": round(stats["combined_investment"], 2),
                "pair_hits": stats["pair_hits"],
                "investment_a": stats["investment_a"],
                "investment_b": stats["investment_b"],
                "balance_score": stats["balance_score"],
                "competition_score": stats["rivalry_score"],
            }
        )

    competitive_map.sort(
        key=lambda x: (
            x["shared_portals_count"],
            x["competition_score"],
            x["combined_investment"],
            x["balance_score"],
        ),
        reverse=True,
    )

    return competitive_map


def build_portal_pressure_map(banner_items_data):
    portal_advertisers = defaultdict(set)
    portal_investment = defaultdict(float)
    portal_banner_count = defaultdict(int)

    for item in banner_items_data:
        advertiser = item.get("advertiser") or "Nao identificado"
        portal = item.get("portal") or "Desconhecido"
        investment = _safe_float(item.get("investment", 0))

        if advertiser != "Nao identificado":
            portal_advertisers[portal].add(advertiser)

        portal_investment[portal] += investment
        portal_banner_count[portal] += 1

    results = []
    for portal in portal_banner_count.keys():
        advertisers_count = len(portal_advertisers[portal])
        banners = portal_banner_count[portal]
        investment = portal_investment[portal]

        pressure_score = round(
            (advertisers_count * 10)
            + (banners * 0.3)
            + (investment / 4000),
            2,
        )

        if pressure_score >= 45:
            pressure_label = "Alta"
        elif pressure_score >= 25:
            pressure_label = "Média"
        else:
            pressure_label = "Baixa"

        results.append(
            {
                "portal": portal,
                "advertisers_count": advertisers_count,
                "banners": banners,
                "investment": round(investment, 2),
                "pressure_score": pressure_score,
                "pressure_label": pressure_label,
            }
        )

    results.sort(key=lambda x: x["pressure_score"], reverse=True)
    return results


def build_rival_summary(competitive_map):
    if not competitive_map:
        return {
            "top_rival_pair": None,
            "top_pressure_pair": None,
        }

    top_pair = competitive_map[0]

    top_balance_pair = sorted(
        competitive_map,
        key=lambda x: (x["balance_score"], x["competition_score"]),
        reverse=True,
    )[0]

    return {
        "top_rival_pair": top_pair,
        "top_pressure_pair": top_balance_pair,
    }