from PIL import Image
import pytesseract
import io
import unicodedata
import re

ALIASES = {
    "magalu": "Magazine Luiza",
    "magazine luiza": "Magazine Luiza",
    "maga lu": "Magazine Luiza",
    "magazineluiza": "Magazine Luiza",
    "casas bahia": "Casas Bahia",
    "casasbahia": "Casas Bahia",
    "americanas": "Americanas",
    "mercado livre": "Mercado Livre",
    "mercadolivre": "Mercado Livre",
    "amazon": "Amazon",
    "shopee": "Shopee",
    "netshoes": "Netshoes",
    "tim": "TIM",
    "t1m": "TIM",
    "t im": "TIM",
    "oi": "OI",
    "0i": "OI",
    "claro": "Claro",
    "vivo": "Vivo",
    "unimed": "Unimed",
    "uni med": "Unimed",
    "natura": "Natura",
    "boticario": "O Boticário",
    "o boticario": "O Boticário",
    "o boticário": "O Boticário",
    "renner": "Renner",
    "riachuelo": "Riachuelo",
    "cea": "C&A",
    "c&a": "C&A",
    "itau": "Itaú",
    "itaú": "Itaú",
    "bradesco": "Bradesco",
    "santander": "Santander",
    "caixa": "Caixa",
    "gov pb": "Governo da Paraíba",
    "governo da paraiba": "Governo da Paraíba",
    "governo da paraíba": "Governo da Paraíba",
    "paraiba governo": "Governo da Paraíba",

    "prefeitura municipal de joao pessoa": "Prefeitura Municipal de João Pessoa",
    "prefeitura municipal de joão pessoa": "Prefeitura Municipal de João Pessoa",
    "prefeitura de joao pessoa": "Prefeitura Municipal de João Pessoa",
    "prefeitura de joão pessoa": "Prefeitura Municipal de João Pessoa",
    "pmjp": "Prefeitura Municipal de João Pessoa",

    "camara municipal de joao pessoa": "Câmara Municipal de João Pessoa",
    "camara municipal de joão pessoa": "Câmara Municipal de João Pessoa",
    "câmara municipal de joão pessoa": "Câmara Municipal de João Pessoa",
    "cmjp": "Câmara Municipal de João Pessoa",

    "assembleia legislativa da paraiba": "Assembleia Legislativa da Paraíba",
    "assembleia legislativa da paraíba": "Assembleia Legislativa da Paraíba",
    "alpb": "Assembleia Legislativa da Paraíba",

    # Governo / instituições
    "governo da paraiba": "Governo da Paraíba",
    "governo da paraíba": "Governo da Paraíba",
    "gov pb": "Governo da Paraíba",
    "gov paraiba": "Governo da Paraíba",
    "gov paraíba": "Governo da Paraíba",

    "prefeitura municipal de joao pessoa": "Prefeitura Municipal de João Pessoa",
    "prefeitura municipal de joão pessoa": "Prefeitura Municipal de João Pessoa",
    "prefeitura de joao pessoa": "Prefeitura Municipal de João Pessoa",
    "prefeitura de joão pessoa": "Prefeitura Municipal de João Pessoa",
    "pmjp": "Prefeitura Municipal de João Pessoa",

    "prefeitura municipal de cabedelo": "Prefeitura Municipal de Cabedelo",
    "prefeitura de cabedelo": "Prefeitura Municipal de Cabedelo",
    "pmc cabedelo": "Prefeitura Municipal de Cabedelo",
    "cabedelo prefeitura": "Prefeitura Municipal de Cabedelo",

    "prefeitura municipal de santa rita": "Prefeitura Municipal de Santa Rita",
    "prefeitura de santa rita": "Prefeitura Municipal de Santa Rita",
    "pmsr": "Prefeitura Municipal de Santa Rita",
    "santa rita prefeitura": "Prefeitura Municipal de Santa Rita",

    "assembleia legislativa da paraiba": "Assembleia Legislativa da Paraíba",
    "assembleia legislativa da paraíba": "Assembleia Legislativa da Paraíba",
    "alpb": "Assembleia Legislativa da Paraíba",

    "camara municipal de joao pessoa": "Câmara Municipal de João Pessoa",
    "camara municipal de joão pessoa": "Câmara Municipal de João Pessoa",
    "câmara municipal de joão pessoa": "Câmara Municipal de João Pessoa",
    "cmjp": "Câmara Municipal de João Pessoa",

    # Políticos / nomes públicos
    "joao azevedo": "João Azevêdo",
    "joão azevedo": "João Azevêdo",
    "joão azevêdo": "João Azevêdo",

    "lucas ribeiro": "Lucas Ribeiro",

    "cicero lucena": "Cícero Lucena",
    "cícero lucena": "Cícero Lucena",

    "efraim filho": "Efraim Filho",

    "adriano galdino": "Adriano Galdino",

    "walber virgulino": "Walber Virgulino",

    # Eventos / campanhas
    "world beach games": "World Beach Games",
    "beach games": "World Beach Games",

    "antes que aconteca": "Antes Que Aconteça",
    "antes que aconteça": "Antes Que Aconteça",

    "eleicoes suplementares": "Eleições Suplementares",
    "eleições suplementares": "Eleições Suplementares",

    "eleicoes 2026": "Eleições 2026",
    "eleições 2026": "Eleições 2026",

    # Varejo / comércio
    "armazem paraiba": "Armazém Paraíba",
    "armazém paraiba": "Armazém Paraíba",
    "armazém paraíba": "Armazém Paraíba",

    "magazine luiza": "Magazine Luiza",
    "magazineluiza": "Magazine Luiza",
    "magalu": "Magazine Luiza",

    "casas bahia": "Casas Bahia",
    "casasbahia": "Casas Bahia",

    "laser eletro": "Laser Eletro",

    "lojao rio do peixe": "Lojão Rio do Peixe",
    "lojão rio do peixe": "Lojão Rio do Peixe",

    # Saúde / imobiliário / construção
    "unimed jp": "Unimed JP",
    "unimed joao pessoa": "Unimed JP",
    "unimed joão pessoa": "Unimed JP",

    "alliance": "Alliance",

    "setai": "Setai",

    "gp": "GP",

    "delta engenharia": "Delta Engenharia",

    "ghc": "GHC",

    "construtora tropical": "Construtora Tropical",
}

COMMERCIAL_TERMS = [
    "promocao",
    "promoção",
    "oferta",
    "desconto",
    "compre",
    "saiba mais",
    "clique aqui",
    "aproveite",
    "frete gratis",
    "frete grátis",
    "parcelamento",
    "imperdivel",
    "imperdível",
    "assine",
]

EDITORIAL_TERMS = [
    "noticia",
    "notícias",
    "publicado em",
    "redacao",
    "redação",
    "autor",
    "politica",
    "política",
    "esporte",
    "leia também",
    "mais lidas",
    "veja também",
]

def normalize_text(text: str) -> str:
    if not text:
        return ""

    text = text.lower()
    text = unicodedata.normalize("NFKD", text)
    text = "".join(ch for ch in text if not unicodedata.combining(ch))
    text = re.sub(r"[^a-z0-9&\s]", " ", text)
    text = re.sub(r"\s+", " ", text).strip()
    return text

def extract_text_from_image_bytes(image_bytes: bytes) -> str:
    try:
        image = Image.open(io.BytesIO(image_bytes)).convert("L")
        text = pytesseract.image_to_string(image, lang="eng")
        return text.strip()
    except Exception:
        return ""

def detect_advertiser_from_text(text: str) -> str | None:
    normalized = normalize_text(text)
    if not normalized:
        return None

    short_aliases = {"oi", "tim"}

    for alias, canonical in ALIASES.items():
        alias_norm = normalize_text(alias)
        if not alias_norm:
            continue

        # Para marcas curtas, exigir palavra isolada
        if alias_norm in short_aliases:
            pattern = rf"\b{re.escape(alias_norm)}\b"
            if re.search(pattern, normalized):
                return canonical
        else:
            if alias_norm in normalized:
                return canonical

    return None

def has_commercial_signal(text: str) -> bool:
    normalized = normalize_text(text)
    return any(normalize_text(term) in normalized for term in COMMERCIAL_TERMS)

def has_editorial_signal(text: str) -> bool:
    normalized = normalize_text(text)
    return any(normalize_text(term) in normalized for term in EDITORIAL_TERMS)