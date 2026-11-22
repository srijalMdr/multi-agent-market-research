"""Fetch source pages and extract their main text (used to enrich search snippets)."""
from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor
from urllib.parse import urlparse

import requests
import trafilatura

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 "
        "(KHTML, like Gecko) Chrome/124.0 Safari/537.36"
    ),
    "Accept-Language": "en-US,en;q=0.9",
}
TIMEOUT = 8
MAX_CHARS = 1500
SKIP_DOMAINS = (
    "facebook.com", "instagram.com", "linkedin.com", "x.com", "twitter.com",
    "youtube.com", "tiktok.com", "play.google.com", "apps.apple.com",
)


def can_scrape(url: str) -> bool:
    host = urlparse(url).netloc.lower()
    return not (url.lower().endswith(".pdf") or any(host.endswith(d) for d in SKIP_DOMAINS))


def scrape(url: str) -> str:
    """Return the main text of a page, or "" if it can't be fetched or parsed."""
    if not can_scrape(url):
        return ""
    try:
        resp = requests.get(url, headers=HEADERS, timeout=TIMEOUT)
        if resp.status_code != 200 or "html" not in resp.headers.get("content-type", ""):
            return ""
        text = trafilatura.extract(resp.text, include_comments=False, include_tables=True) or ""
    except Exception:
        return ""
    text = " ".join(text.split())
    return text[:MAX_CHARS]


def scrape_many(urls: list[str], workers: int = 5) -> dict[str, str]:
    with ThreadPoolExecutor(max_workers=workers) as pool:
        return dict(zip(urls, pool.map(scrape, urls)))
