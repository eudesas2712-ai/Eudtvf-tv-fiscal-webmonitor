def analyze_timeline(points: list[dict]) -> dict:
    if not points or len(points) < 2:
        return {
            "has_comparison": False,
            "summary": "Histórico insuficiente para comparação temporal.",
            "deltas": {},
            "insights": [],
        }

    previous = points[-2]
    current = points[-1]

    prev_investment = float(previous.get("total_investment", 0) or 0)
    curr_investment = float(current.get("total_investment", 0) or 0)

    prev_share = float(previous.get("top_advertiser_share", 0) or 0)
    curr_share = float(current.get("top_advertiser_share", 0) or 0)

    investment_delta = curr_investment - prev_investment
    share_delta = curr_share - prev_share

    insights = []

    if investment_delta > 0:
        insights.append(f"O investimento estimado cresceu R$ {investment_delta:,.0f}.")
    elif investment_delta < 0:
        insights.append(f"O investimento estimado caiu R$ {abs(investment_delta):,.0f}.")
    else:
        insights.append("O investimento estimado permaneceu estável.")

    if current.get("top_advertiser") != previous.get("top_advertiser"):
        insights.append(
            f"Houve mudança de liderança: {previous.get('top_advertiser')} saiu da liderança e {current.get('top_advertiser')} assumiu."
        )
    else:
        insights.append(
            f"{current.get('top_advertiser')} manteve a liderança no período."
        )

    if share_delta > 0:
        insights.append(f"O share do líder cresceu {share_delta:.2f} pontos percentuais.")
    elif share_delta < 0:
        insights.append(f"O share do líder caiu {abs(share_delta):.2f} pontos percentuais.")
    else:
        insights.append("O share do líder permaneceu estável.")

    return {
        "has_comparison": True,
        "summary": "Comparativo temporal gerado com sucesso.",
        "deltas": {
            "investment_delta": investment_delta,
            "share_delta": share_delta,
            "previous_leader": previous.get("top_advertiser"),
            "current_leader": current.get("top_advertiser"),
        },
        "insights": insights,
    }