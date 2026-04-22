def get_base_value(width: int | None, height: int | None) -> int:
    if not width or not height:
        return 100

    if width == 300 and height == 250:
        return 120
    if width == 728 and height == 90:
        return 180
    if width == 160 and height == 600:
        return 150

    return 100


def get_portal_multiplier(source_name: str | None) -> float:
    if not source_name:
        return 1.0

    source_name = source_name.lower()

    if "polemicaparaiba" in source_name:
        return 1.3
    if "portalcorreio" in source_name:
        return 1.4
    if "clickpb" in source_name:
        return 1.2
    if "wscom" in source_name:
        return 1.2
    if "jornaldaparaiba" in source_name:
        return 1.3

    return 1.0


def get_position_multiplier(pos_y: int | None) -> float:
    if pos_y is None:
        return 1.0

    if pos_y < 500:
        return 1.2
    elif pos_y > 1500:
        return 0.8

    return 1.0


def estimate_banner_value(width, height, source_name, pos_y) -> int:
    base = get_base_value(width, height)
    portal = get_portal_multiplier(source_name)
    position = get_position_multiplier(pos_y)

    value = base * portal * position
    return int(value)