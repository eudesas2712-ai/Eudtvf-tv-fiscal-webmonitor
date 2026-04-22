from bs4 import BeautifulSoup
from urllib.parse import urljoin
from app.utils.timeutils import parse_dt

def extract_links_from_list(base_url: str, html: str, limit: int = 30) -> list[str]:
    soup = BeautifulSoup(html, "lxml")
    links = []
    for a in soup.select("a[href]"):
        href = a.get("href", "").strip()
        if not href:
            continue
        u = urljoin(base_url, href)
        # heurística simples: evita âncoras e arquivos
        if any(u.lower().endswith(ext) for ext in [".jpg",".png",".pdf",".mp4",".mp3",".zip"]):
            continue
        # tenta pegar notícias: muitos sites têm /noticia/ ou datas; deixamos amplo no MVP
        if u.startswith("http"):
            links.append(u)
        if len(links) >= limit:
            break
    return links

def parse_news_article(url: str, html: str) -> dict:
    soup = BeautifulSoup(html, "lxml")

    # Título
    title = None
    if soup.find("meta", property="og:title"):
        title = soup.find("meta", property="og:title").get("content")
    if not title and soup.title:
        title = soup.title.get_text(strip=True)

    # Autor
    author = None
    if soup.find("meta", attrs={"name":"author"}):
        author = soup.find("meta", attrs={"name":"author"}).get("content")

    # Data
    published_at = None
    for sel in [
        ("meta", {"property":"article:published_time"}),
        ("meta", {"property":"og:updated_time"}),
        ("time", {}),
    ]:
        el = soup.find(sel[0], attrs=sel[1])
        if el:
            cand = el.get("content") or el.get("datetime") or el.get_text(strip=True)
            published_at = parse_dt(cand)
            if published_at:
                break

    # Corpo: tenta article; senão, junta <p>
    body_text = ""
    article = soup.find("article")
    if article:
        ps = article.find_all("p")
    else:
        ps = soup.find_all("p")

    chunks = []
    for p in ps:
        txt = p.get_text(" ", strip=True)
        if txt and len(txt) > 20:
            chunks.append(txt)
    body_text = "\n".join(chunks)[:50000]

    return {
        "url": url,
        "title": title,
        "author": author,
        "published_at": published_at,
        "content_text": body_text,
    }