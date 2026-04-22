from urllib.parse import urlsplit, urlunsplit, parse_qsl, urlencode

TRACKING_KEYS = {"utm_source","utm_medium","utm_campaign","utm_term","utm_content","gclid","fbclid"}

def canonicalize_url(url: str) -> str:
    parts = urlsplit(url)
    q = [(k,v) for (k,v) in parse_qsl(parts.query, keep_blank_values=True) if k.lower() not in TRACKING_KEYS]
    query = urlencode(q)
    clean = urlunsplit((parts.scheme, parts.netloc, parts.path, query, ""))  # drop fragment
    return clean