import pytest
from pydantic import BaseModel, ValidationError

import core.llm as llm
import core.scraper as scraper
import core.search as search
from core.models import Brief, ResearchState


def test_brief_rejects_more_than_two_competitors():
    comp = {"name": "X", "description": "d"}
    with pytest.raises(ValidationError):
        Brief(summary="s", competitors=[comp, comp, comp])


def test_state_log_records_agent_name():
    s = ResearchState(query="q")
    s.add_log("Researcher", "done")
    assert s.log == ["[Researcher] done"]


@pytest.mark.parametrize("raw", [
    '{"a": 1}',
    '```json\n{"a": 1}\n```',
    'Here you go: {"a": 1} thanks',
])
def test_extract_json_handles_wrapped_output(raw):
    assert llm._extract_json(raw) == {"a": 1}


class _Out(BaseModel):
    a: int


def test_chat_json_retries_once_on_invalid_json(monkeypatch):
    replies = iter(["not json", '{"a": 5}'])
    monkeypatch.setattr(llm, "chat", lambda *a, **k: next(replies))
    assert llm.chat_json("sys", "user", _Out).a == 5


def test_chat_json_raises_after_retries(monkeypatch):
    monkeypatch.setattr(llm, "chat", lambda *a, **k: "still not json")
    with pytest.raises(llm.LLMError):
        llm.chat_json("sys", "user", _Out)


def test_placeholder_key_is_treated_as_missing(monkeypatch):
    monkeypatch.setenv("LLM_API_KEY", "your_groq_api_key_here")
    assert not llm.has_llm_key()


def test_web_search_falls_back_to_next_provider(monkeypatch):
    monkeypatch.setattr(search, "has_tavily_key", lambda: True)
    monkeypatch.setattr(search, "_tavily", lambda q, n: (_ for _ in ()).throw(RuntimeError("down")))
    monkeypatch.setattr(search, "_ddg", lambda q, n: [{"title": "t", "url": "https://a.com", "snippet": "x" * 900}])
    results, provider = search.web_search("q")
    assert provider == "DuckDuckGo"
    assert len(results[0]["snippet"]) == search.MAX_SNIPPET


def test_web_search_returns_none_when_all_fail(monkeypatch):
    monkeypatch.setattr(search, "has_tavily_key", lambda: False)
    monkeypatch.setattr(search, "_ddg", lambda q, n: [])
    assert search.web_search("q") == ([], "none")


def test_sample_data_is_clearly_labelled():
    rows = search.load_sample_data("food delivery nepal")
    assert rows and all(r["title"].startswith("[SAMPLE DATA]") for r in rows)


@pytest.mark.parametrize("url,ok", [
    ("https://news.example.com/article", True),
    ("https://www.facebook.com/page", False),
    ("https://play.google.com/store/apps/x", False),
    ("https://example.com/report.pdf", False),
])
def test_can_scrape(url, ok):
    assert scraper.can_scrape(url) is ok


class _Resp:
    def __init__(self, status=200, ctype="text/html", text="<html></html>"):
        self.status_code, self.headers, self.text = status, {"content-type": ctype}, text


def test_scrape_extracts_and_truncates(monkeypatch):
    monkeypatch.setattr(scraper.requests, "get", lambda *a, **k: _Resp())
    monkeypatch.setattr(scraper.trafilatura, "extract", lambda *a, **k: "word  " * 2000)
    text = scraper.scrape("https://news.example.com/a")
    assert len(text) == scraper.MAX_CHARS and "  " not in text


def test_scrape_returns_empty_on_error(monkeypatch):
    def boom(*a, **k):
        raise TimeoutError
    monkeypatch.setattr(scraper.requests, "get", boom)
    assert scraper.scrape("https://news.example.com/a") == ""


def test_scrape_ignores_non_html(monkeypatch):
    monkeypatch.setattr(scraper.requests, "get", lambda *a, **k: _Resp(ctype="application/pdf"))
    assert scraper.scrape("https://news.example.com/a") == ""


def _api_error(cls, status):
    import httpx

    req = httpx.Request("POST", "https://api.example.com")
    return cls("err", response=httpx.Response(status, request=req), body=None)


@pytest.mark.parametrize("cls,status,expected", [
    ("RateLimitError", 429, "Rate limit reached"),
    ("AuthenticationError", 401, "API key was rejected"),
    ("NotFoundError", 404, "is not available"),
])
def test_api_errors_become_friendly_messages(monkeypatch, cls, status, expected):
    import openai

    err = _api_error(getattr(openai, cls), status)

    class _Client:
        class chat:
            class completions:
                @staticmethod
                def create(**kwargs):
                    raise err

    monkeypatch.setattr(llm, "_client", lambda: _Client)
    with pytest.raises(llm.LLMError, match=expected):
        llm.chat("sys", "user")
