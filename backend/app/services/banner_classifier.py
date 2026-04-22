import re
from typing import Optional


BRAND_RULES = [
    ("TIM", [r"\btim\b", r"tim\.com", r"/tim", r"logo[_-]?tim"]),
    ("Vivo", [r"\bvivo\b", r"vivo\.com", r"/vivo", r"logo[_-]?vivo"]),
    ("Claro", [r"\bclaro\b", r"claro\.com", r"/claro", r"logo[_-]?claro"]),
    ("Banco do Brasil", [r"banco\s*do\s*brasil", r"\bbb\b", r"bb\.com\.br"]),
    ("Caixa", [r"\bcaixa\b", r"caixa\.gov\.br", r"caixa\.com\.br"]),
    ("Unimed", [r"\bunimed\b", r"unimed\."]),
    ("Magalu", [r"\bmagalu\b", r"magazineluiza", r"magalu\.com"]),
    ("Casas Bahia", [r"casas?\s*bahia", r"casasbahia"]),
    ("Prefeitura de João Pessoa", [
        r"prefeitura\s*de\s*jo[aã]o\s*pessoa",
        r"jo[aã]o\s*pessoa",
        r"\bprefeitura\b",
    ]),
    ("Governo da Paraíba", [
        r"governo\s*da\s*para[ií]ba",
        r"para[ií]ba\s*gov",
        r"\bgoverno\b",
    ]),
]


def _normalize_text(*parts: Optional[str]) -> str:
    joined = " ".join([(p or "") for p in parts]).strip().lower()
    joined = re.sub(r"\s+", " ", joined)
    return joined


def classify_advertiser(
    alt_text: Optional[str] = None,
    image_url: Optional[str] = None,
    ocr_text: Optional[str] = None,
) -> tuple[str, int, str]:
    haystack = _normalize_text(alt_text, image_url, ocr_text)

    if not haystack:
        return "Nao identificado", 25, "sem texto disponível"

    best_brand = None
    best_score = 0
    best_reason = "sem correspondência"

    for brand, patterns in BRAND_RULES:
        matches = 0
        matched_terms = []

        for pattern in patterns:
            if re.search(pattern, haystack, flags=re.IGNORECASE):
                matches += 1
                matched_terms.append(pattern)

        if matches == 0:
            continue

        if matches >= 3:
            score = 96
        elif matches == 2:
            score = 88
        else:
            score = 78

        if brand in {"Prefeitura de João Pessoa", "Governo da Paraíba"} and matches >= 1:
            score = max(score, 82)

        if score > best_score:
            best_brand = brand
            best_score = score
            best_reason = f"match por regras: {', '.join(matched_terms[:3])}"

    if best_brand:
        return best_brand, best_score, best_reason

    public_hints = [
        r"\bpromo\b",
        r"\boferta\b",
        r"\bcompre\b",
        r"\bassine\b",
        r"\bclique\b",
        r"\bsaiba mais\b",
        r"\banuncie\b",
    ]
    if any(re.search(p, haystack, flags=re.IGNORECASE) for p in public_hints):
        return "Nao identificado", 45, "criativo publicitário sem marca reconhecida"

    return "Nao identificado", 35, "nenhuma regra de marca acionada"