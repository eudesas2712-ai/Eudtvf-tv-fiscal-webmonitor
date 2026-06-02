def _by_advertiser(summary):
    return {
        item.get("advertiser"): item
        for item in summary.get("share_of_voice", [])
        if item.get("advertiser")
    }


def generate_comparative_alerts(current: dict, previous: dict | None = None):
    alerts = []

    if not previous:
        alerts.append("Primeiro snapshot registrado. Alertas comparativos serão gerados a partir da próxima coleta.")
        return alerts

    curr_adv = _by_advertiser(current)
    prev_adv = _by_advertiser(previous)

    new_advertisers = set(curr_adv) - set(prev_adv)
    for adv in sorted(new_advertisers):
        alerts.append(f"Novo anunciante detectado: {adv}.")

    removed_advertisers = set(prev_adv) - set(curr_adv)
    for adv in sorted(removed_advertisers):
        alerts.append(f"Anunciante deixou de aparecer no período: {adv}.")

    for adv in sorted(set(curr_adv) & set(prev_adv)):
        curr_share = float(curr_adv[adv].get("share_percent", 0) or 0)
        prev_share = float(prev_adv[adv].get("share_percent", 0) or 0)

        curr_inv = float(curr_adv[adv].get("investment", 0) or 0)
        prev_inv = float(prev_adv[adv].get("investment", 0) or 0)

        share_delta = curr_share - prev_share
        if abs(share_delta) >= 3:
            direction = "aumentou" if share_delta > 0 else "reduziu"
            alerts.append(f"{adv} {direction} {abs(round(share_delta, 2))} pontos percentuais de share.")

        if prev_inv > 0:
            inv_delta_pct = ((curr_inv - prev_inv) / prev_inv) * 100
            if abs(inv_delta_pct) >= 20:
                direction = "aumentou" if inv_delta_pct > 0 else "reduziu"
                alerts.append(f"{adv} {direction} investimento estimado em {abs(round(inv_delta_pct, 1))}%.")

    curr_portal = (current.get("portal_ranking") or [{}])[0].get("portal")
    prev_portal = (previous.get("portal_ranking") or [{}])[0].get("portal")

    if curr_portal and prev_portal and curr_portal != prev_portal:
        alerts.append(f"Mudança de portal líder: saiu {prev_portal}, entrou {curr_portal}.")

    pressure = current.get("portal_pressure_map", [])
    high_pressure = [p for p in pressure if p.get("pressure_label") == "Alta"]

    for p in high_pressure[:3]:
        alerts.append(f"Alta pressão competitiva em {p.get('portal')}.")

    return alerts