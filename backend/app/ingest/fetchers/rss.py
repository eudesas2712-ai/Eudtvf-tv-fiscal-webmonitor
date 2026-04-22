import feedparser

def fetch_rss_links(rss_url: str, limit: int = 30) -> list[str]:
    d = feedparser.parse(rss_url)
    links = []
    for e in d.entries[:limit]:
        if getattr(e, "link", None):
            links.append(e.link)
    return links