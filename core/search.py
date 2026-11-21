"""Web search with a three-level fallback: Tavily -> DuckDuckGo -> labelled sample data."""
from __future__ import annotations

import json
import os
from pathlib import Path

from dotenv import load_dotenv

load_dotenv()

SAMPLE_DIR = Path(__file__).resolve().parent.parent / "sample_data"
MAX_SNIPPET = 600


def has_tavily_key() -> bool:
    key = os.getenv("TAVILY_API_KEY", "").strip()
    return bool(key) and not key.startswith("your_")


def _tavily(query: str, max_results: int) -> list[dict]:
    from tavily import TavilyClient

    client = TavilyClient(api_key=os.getenv("TAVILY_API_KEY"))
    res = client.search(query=query, max_results=max_results, search_depth="basic")
    return [
        {"title": r.get("title", ""), "url": r.get("url", ""), "snippet": r.get("content", "")}
        for r in res.get("results", [])
    ]


def _ddg(query: str, max_results: int) -> list[dict]:
    from ddgs import DDGS

    rows = DDGS().text(query, max_results=max_results) or []
    return [
        {"title": r.get("title", ""), "url": r.get("href", ""), "snippet": r.get("body", "")}
        for r in rows
    ]


def web_search(query: str, max_results: int = 5) -> tuple[list[dict], str]:
    """Return (results, provider_name). Results may be empty if every provider fails."""
    providers = []
    if has_tavily_key():
        providers.append(("Tavily", _tavily))
    providers.append(("DuckDuckGo", _ddg))

    for name, fn in providers:
        try:
            results = [r for r in fn(query, max_results) if r["url"]]
            if results:
                for r in results:
                    r["snippet"] = r["snippet"][:MAX_SNIPPET]
                return results, name
        except Exception:
            continue
    return [], "none"


def load_sample_data(query: str) -> list[dict]:
    """Load clearly labelled SAMPLE data (used only when live search fails)."""
    files = sorted(SAMPLE_DIR.glob("*.json"))
    if not files:
        return []
    q = query.lower()
    chosen = files[0]
    for f in files:
        data = json.loads(f.read_text(encoding="utf-8"))
        if any(k in q for k in data.get("keywords", [])):
            chosen = f
            break
    data = json.loads(chosen.read_text(encoding="utf-8"))
    return [
        {**r, "title": f"[SAMPLE DATA] {r['title']}"} for r in data.get("results", [])
    ]
