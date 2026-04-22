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

        paragraphs = soup.find_all("p")
        text_parts = []

        for p in paragraphs:
            txt = p.get_text(" ", strip=True)
            if txt and len(txt) > 30:
                text_parts.append(txt)

        text = " ".join(text_parts)

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
        ]

        if title_lower.strip() in generic_titles:
            return None

        return {
            "title": title,
            "text": text
        }

    except Exception:
        return None