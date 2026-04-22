import requests
from tenacity import retry, stop_after_attempt, wait_exponential
from app.utils.rate_limit import polite_sleep
from urllib.parse import urlparse

UA = "TvFiscalWebMonitor/0.1 (+https://tvfiscal-pb.com.br)"

@retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=1, max=6))
def fetch_html(url: str, timeout: int = 20) -> str:
    domain = urlparse(url).netloc
    polite_sleep(domain, min_interval_sec=1.0)
    r = requests.get(url, headers={"User-Agent": UA}, timeout=timeout)
    r.raise_for_status()
    r.encoding = r.apparent_encoding or "utf-8"
    return r.text