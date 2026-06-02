import requests
from bs4 import BeautifulSoup
import urllib3

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/145.0 Safari/537.36"
}

BAD_PATTERNS = [
    "/tag/",
    "/author/",
    "/categoria/",
    "/category/",
    "/wp-content/",
    "/feed/",
    "/page/",
    "/videos/",
    "/video/",
    "/tv-",
    "/colunistas/",
    "/opiniao/",
    "/entretenimento/",
    "/economia/",
    "/internacional/",
    "/esportes/",
    "/policial/",
    "/podcast/",
]

BAD_EXACT_ENDS = [
    "/",
    "/paraiba/",
    "/politica/",
    "/economia/",
    "/internacional/",
    "/entretenimento/",
]

SECTION_TITLE_PATTERNS = [
    "tudo sobre ",
    "últimas notícias",
    "ultimas noticias",
    "mídias e entretenimento",
    "midias e entretenimento",
    "opinião - artigos",
    "opiniao - artigos",
    "política - análises",
    "politica - analises",
    "esporte - notícias",
    "esporte - noticias",
]

BOILERPLATE_SNIPPETS = [
    "@2022 - All Right Reserved. Designed and Developed by WSCOM",
    "Siga o canal do WSCOM no Whatsapp.",
    "Siga o canal do WSCOM no WhatsApp.",
]

def clean_text(text: str) -> str:
    clean = text or ""
    for snippet in BOILERPLATE_SNIPPETS:
        clean = clean.replace(snippet, " ")
    return " ".join(clean.split())

def is_probable_section_title(title: str) -> bool:
    lower = (title or "").strip().lower()
    if any(pattern in lower for pattern in SECTION_TITLE_PATTERNS):
        return True
    exact = {"política", "politica", "economia", "esporte", "cultura", "saúde", "saude", "opinião", "opiniao"}
    return lower in exact

def is_probable_news_url(url: str, base_url: str) -> bool:
    if not url.startswith("http"):
        return False

    if url == base_url:
        return False

    url_lower = url.lower()

    for pattern in BAD_PATTERNS:
        if pattern in url_lower:
            return False

    for ending in BAD_EXACT_ENDS:
        if url_lower.endswith(ending) and len(url_lower.rstrip("/").split("/")) <= 4:
            return False

    # Tenta manter URLs mais profundas, mais típicas de notícia
    path_parts = [p for p in url_lower.replace("https://", "").replace("http://", "").split("/") if p]
    if len(path_parts) < 3:
        return False

    return True

def collect_links(base_url):
    response = requests.get(
        base_url,
        headers=HEADERS,
        timeout=20,
        verify=False
    )
    response.raise_for_status()

    soup = BeautifulSoup(response.text, "lxml")
    links = []

    for a in soup.find_all("a", href=True):
        href = a["href"].strip()

        if is_probable_news_url(href, base_url):
            links.append(href)

    return list(dict.fromkeys(links))[:40]

def collect_article(url):
    try:
        response = requests.get(
            url,
            headers=HEADERS,
            timeout=20,
            verify=False
        )
        response.raise_for_status()

        soup = BeautifulSoup(response.text, "lxml")
        title = soup.title.text.strip() if soup.title else "Sem título"
        if is_probable_section_title(title):
            return None

        paragraphs = soup.find_all("p")
        text_parts = []

        for p in paragraphs:
            txt = p.get_text(" ", strip=True)
            if txt and len(txt) > 30:
                text_parts.append(txt)

        text = clean_text(" ".join(text_parts))

        # Rejeita textos curtos demais
        if len(text) < 400:
            return None

        # Rejeita títulos genéricos de seção
        title_lower = title.lower()
        generic_titles = [
            "polêmica paraíba",
            "portal correio",
            "pb agora",
            "economia",
            "internacional",
            "entretenimento",
            "política",
            "notícias da paraíba",
            "últimas notícias",
            "ultimas noticias",
            "tudo sobre",
        ]

        if title_lower.strip() in generic_titles or is_probable_section_title(title):
            return None

        return {
            "title": title,
            "text": text
        }

    except Exception:
        return None