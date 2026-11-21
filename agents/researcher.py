"""Researcher: plans search queries, runs web search, extracts sourced findings."""
from __future__ import annotations

from pydantic import BaseModel, Field

from core.llm import chat_json
from core.models import Finding, ResearchFindings, ResearchState, Source
from core.search import load_sample_data, web_search

MAX_SOURCES = 10


class _QueryPlan(BaseModel):
    queries: list[str] = Field(min_length=1, max_length=3)


class _Extracted(BaseModel):
    findings: list[Finding]


PLAN_PROMPT = (
    "You are a market researcher. Given a research request about a company or industry, "
    "write 3 short web search queries: (1) overview/market size, (2) main competitors or players, "
    "(3) recent trends or challenges. Keep the country/region if one is mentioned."
)

EXTRACT_PROMPT = (
    "You are a careful market researcher. From the numbered sources below, extract 6-12 short, "
    "atomic factual findings relevant to the request. Rules:\n"
    "- Use ONLY information stated in the sources. Do not add outside knowledge.\n"
    "- Every finding must list the source id(s) it came from in source_ids.\n"
    "- Prefer concrete facts: names, numbers, dates, market share, services, challenges.\n"
    "- Skip sources that are irrelevant."
)


def _format_sources(sources: list[Source]) -> str:
    return "\n\n".join(f"[{s.id}] {s.title}\nURL: {s.url}\n{s.snippet}" for s in sources)


def run(state: ResearchState) -> ResearchState:
    plan = chat_json(PLAN_PROMPT, f"Research request: {state.query}", _QueryPlan)
    state.add_log("Researcher", f"Planned searches: {plan.queries}")

    raw, seen, providers = [], set(), set()
    for q in plan.queries:
        results, provider = web_search(q, max_results=6)
        if provider != "none":
            providers.add(provider)
        for r in results:
            if r["url"] not in seen:
                seen.add(r["url"])
                raw.append(r)

    is_sample = False
    if not raw:
        raw = load_sample_data(state.query)
        is_sample = True
        providers = {"Sample data"}
        state.add_log("Researcher", "Live search returned nothing. Using labelled SAMPLE DATA.")

    sources = [
        Source(id=i, title=r["title"], url=r["url"], snippet=r["snippet"])
        for i, r in enumerate(raw[:MAX_SOURCES], start=1)
    ]
    state.add_log("Researcher", f"Collected {len(sources)} sources via {', '.join(sorted(providers))}.")

    extracted = chat_json(
        EXTRACT_PROMPT,
        f"Research request: {state.query}\n\nSources:\n{_format_sources(sources)}",
        _Extracted,
    )
    valid_ids = {s.id for s in sources}
    findings = [
        Finding(fact=f.fact, source_ids=[i for i in f.source_ids if i in valid_ids])
        for f in extracted.findings
    ]
    findings = [f for f in findings if f.source_ids]

    state.findings = ResearchFindings(
        search_queries=plan.queries,
        sources=sources,
        findings=findings,
        search_provider=", ".join(sorted(providers)),
        is_sample_data=is_sample,
    )
    state.add_log("Researcher", f"Extracted {len(findings)} sourced findings. Handing off to Analyst.")
    return state
