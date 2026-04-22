FORMAT_PRICE_TABLE = {
    "728x90": 120,
    "300x250": 150,
    "970x250": 200,
    "320x100": 90,
    "160x600": 110,
    "300x600": 160,
    "336x280": 150,
    "468x60": 80,
    "970x90": 130,
    "970x150": 150,
}

DEFAULT_PRICE = 100


def estimate_banner_value(width: int, height: int):

    if not width or not height:
        return DEFAULT_PRICE

    key = f"{width}x{height}"

    if key in FORMAT_PRICE_TABLE:
        return FORMAT_PRICE_TABLE[key]

    return DEFAULT_PRICE