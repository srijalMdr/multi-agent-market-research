import pytest

from core.models import Brief, CriticFeedback, Finding

SEARCH_RESULTS = [
    {"title": "Foodmandu overview", "url": "https://news.example.com/foodmandu", "snippet": "Foodmandu was founded in 2010."},
    {"title": "Pathao Food", "url": "https://blog.example.com/pathao", "snippet": "Pathao offers food delivery."},
    {"title": "Foodmandu on Facebook", "url": "https://www.facebook.com/foodmandu", "snippet": "Social page."},
]


class FakeLLM:
    """Stands in for core.llm.chat_json and returns canned objects per agent."""

    def __init__(self, critic_approves: bool = True):
        self.critic_approves = critic_approves
        self.calls: list[str] = []

    def __call__(self, system, user, model_cls, retries=1):
        name = model_cls.__name__
        self.calls.append(name)
        if name == "_QueryPlan":
            return model_cls(queries=["q1", "q2"])
        if name == "_Extracted":
            return model_cls(findings=[
                Finding(fact="Foodmandu was founded in 2010.", source_ids=[1]),
                Finding(fact="Pathao offers food delivery.", source_ids=[2, 99]),
                Finding(fact="Unsourced claim.", source_ids=[]),
            ])
        if name == "Brief":
            revised = "Critic issues" in user
            return Brief(
                summary="Revised summary [1]." if revised else "Draft summary [1].",
                competitors=[{"name": "Foodmandu", "description": "Founded 2010 [1].", "source_ids": [1]}],
                key_observations=["Foodmandu is the oldest platform [1]."],
                source_ids=[1, 2, 42],
                missing_information=["Market size"],
            )
        if name == "CriticFeedback":
            if self.critic_approves:
                return CriticFeedback(approved=True)
            return CriticFeedback(approved=False, issues=["Weak citation"], revision_instructions="Fix it")
        raise AssertionError(f"Unexpected model {name}")


@pytest.fixture
def fake_llm(monkeypatch):
    def install(critic_approves=True):
        llm = FakeLLM(critic_approves)
        for mod in ("agents.researcher", "agents.analyst", "agents.critic"):
            monkeypatch.setattr(f"{mod}.chat_json", llm)
        return llm
    return install


@pytest.fixture
def fake_web(monkeypatch):
    monkeypatch.setattr(
        "agents.researcher.web_search", lambda q, max_results=8: ([dict(r) for r in SEARCH_RESULTS], "FakeSearch")
    )
    monkeypatch.setattr(
        "agents.researcher.scrape_many",
        lambda urls, workers=8: {u: "Full article text. " * 30 for u in urls},
    )
