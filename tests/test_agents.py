import pytest

from agents import orchestrator
from core.report import brief_to_markdown


def test_approved_draft_skips_revision(fake_llm, fake_web):
    llm = fake_llm(critic_approves=True)
    state = orchestrator.run("Food delivery in Nepal")

    assert llm.calls == ["_QueryPlan", "_Extracted", "Brief", "CriticFeedback"]
    assert state.revision_count == 0
    assert state.final_brief == state.draft
    assert state.revised_draft is None


def test_rejected_draft_gets_exactly_one_revision(fake_llm, fake_web):
    llm = fake_llm(critic_approves=False)
    state = orchestrator.run("Food delivery in Nepal")

    assert llm.calls.count("Brief") == 2
    assert llm.calls.count("CriticFeedback") == 1
    assert state.revision_count == 1
    assert state.final_brief == state.revised_draft
    assert state.final_brief.summary.startswith("Revised")


def test_handoffs_are_logged_in_order(fake_llm, fake_web):
    fake_llm(critic_approves=False)
    state = orchestrator.run("Food delivery in Nepal")
    agents = [line.split("]")[0].strip("[") for line in state.log]
    order = ["Orchestrator", "Researcher", "Analyst", "Critic", "Analyst", "Orchestrator"]
    it = iter(agents)
    assert all(a in it for a in order)


def test_researcher_drops_unsourced_findings_and_bad_ids(fake_llm, fake_web):
    fake_llm()
    state = orchestrator.run("Food delivery in Nepal")
    facts = {f.fact: f.source_ids for f in state.findings.findings}

    assert "Unsourced claim." not in facts
    assert facts["Pathao offers food delivery."] == [2]


def test_researcher_ranks_scrapeable_sources_and_scrapes_them(fake_llm, fake_web):
    fake_llm()
    f = orchestrator.run("Food delivery in Nepal").findings

    assert "facebook.com" in f.sources[-1].url
    assert not f.sources[-1].scraped
    assert f.scraped_count == 2
    assert f.search_provider == "FakeSearch"


def test_analyst_drops_unknown_source_ids(fake_llm, fake_web):
    fake_llm()
    state = orchestrator.run("Food delivery in Nepal")
    assert 42 not in state.final_brief.source_ids


def test_falls_back_to_sample_data_when_search_fails(fake_llm, monkeypatch):
    fake_llm()
    monkeypatch.setattr("agents.researcher.web_search", lambda q, max_results=8: ([], "none"))
    f = orchestrator.run("food delivery nepal").findings

    assert f.is_sample_data
    assert f.scraped_count == 0
    assert all(s.title.startswith("[SAMPLE DATA]") for s in f.sources)


def test_empty_query_is_rejected():
    with pytest.raises(ValueError):
        orchestrator.run("   ")


def test_on_step_callback_reports_each_stage(fake_llm, fake_web):
    fake_llm(critic_approves=False)
    steps = []
    orchestrator.run("q", on_step=lambda name, s: steps.append(name))
    assert steps == ["orchestrator", "researcher", "analyst", "critic", "revision", "done"]


def test_markdown_report_has_required_sections(fake_llm, fake_web):
    fake_llm()
    md = brief_to_markdown(orchestrator.run("Food delivery in Nepal"))
    for section in ("## Summary", "## Competitors", "## Key Observations", "## Sources", "## Missing Information"):
        assert section in md
