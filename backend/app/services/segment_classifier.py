from typing import Optional


SEGMENT_RULES = [
    ("Telecom", ["tim", "vivo", "claro", "oi"]),
    ("Financeiro", ["banco do brasil", "caixa", "bradesco", "itau", "santander", "nubank"]),
    ("Saúde", ["unimed", "hapvida", "hospital", "plano de saúde"]),
    ("Varejo", ["magalu", "magazineluiza", "casas bahia", "americanas", "carrefour"]),
    ("Governo", ["prefeitura", "governo", "secretaria", "ministério", "ministerio"]),
    ("Educação", ["faculdade", "universidade", "escola", "curso", "colégio", "colegio"]),
    ("Imobiliário", ["imobiliaria", "imóvel", "imovel", "construtora", "empreendimento"]),
    ("Automotivo", ["fiat", "chevrolet", "volkswagen", "toyota", "hyundai", "carro"]),
]


def classify_segment(advertiser_name: Optional[str]) -> str:
    if not advertiser_name:
        return "Não identificado"

    name = advertiser_name.strip().lower()

    if name == "nao identificado":
        return "Não identificado"

    for segment, keywords in SEGMENT_RULES:
        if any(keyword in name for keyword in keywords):
            return segment

    return "Outros"