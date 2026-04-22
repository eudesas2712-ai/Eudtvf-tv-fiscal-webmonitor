def get_position_weight(pos_y: int | None) -> float:
    if pos_y is None:
        return 1.0

    if pos_y < 500:
        return 1.3
    elif pos_y > 1500:
        return 0.7

    return 1.0


def calculate_visibility_score(width, height, pos_y, estimated_value) -> float:
    if not width or not height:
        return 0

    area = width * height
    position_weight = get_position_weight(pos_y)
    value_weight = estimated_value / 100

    score = area * position_weight * value_weight

    return round(score / 1000, 2)  # normalização