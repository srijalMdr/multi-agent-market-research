"""Analyst: writes a short brief using only the researcher's findings."""
from __future__ import annotations

from core.llm import chat_json
from core.models import Brief, ResearchState

SYSTEM = (
    "You are a market analyst writing a SHORT research brief. Use ONLY the numbered findings "
    "provided. Never invent numbers, names or facts.\n"
    "Sections:\n"
    "- summary: 3-5 sentences on the topic. Cite source ids inline like [1] or [2][4].\n"
    "- competitors: at most 2 relevant competitors/key players found in the findings "
    "(empty list if none or not relevant), each with a 1-2 sentence description and source_ids. "
    "Pick players the findings explicitly describe as operating/offering services in the target market; "
    "do not pick a company just because it appears in an app ranking or is mentioned in passing.\n"
    "- key_observations: 3-5 bullet points, each with inline citations like [3].\n"
    "- source_ids: ids of all sources you actually used.\n"
    "- missing_information: important things the findings do NOT cover "
    "(e.g. market size, growth rate, pricing, market share). Be honest."
)


def _format_findings(state: ResearchState) -> str:
    f = state.findings
    lines = [f"- {x.fact} (sources: {x.source_ids})" for x in f.findings]
    srcs = [f"[{s.id}] {s.title} - {s.url}" for s in f.sources]
    note = "\nNOTE: these findings come from SAMPLE DATA, not live search.\n" if f.is_sample_data else ""
    return f"{note}Findings:\n" + "\n".join(lines) + "\n\nSources:\n" + "\n".join(srcs)


def run(state: ResearchState) -> ResearchState:
    """Write the first draft, or a revision if critic feedback is present."""
    user = f"Research request: {state.query}\n\n{_format_findings(state)}"
    revising = state.feedback is not None and not state.feedback.approved

    if revising:
        user += (
            f"\n\nYour previous draft:\n{state.draft.model_dump_json(indent=2)}"
            f"\n\nCritic issues:\n- " + "\n- ".join(state.feedback.issues)
            + f"\n\nRevision instructions: {state.feedback.revision_instructions}"
            "\n\nRewrite the brief fixing these issues, still using only the findings."
        )

    brief = chat_json(SYSTEM, user, Brief)
    valid = {s.id for s in state.findings.sources}
    brief.source_ids = sorted({i for i in brief.source_ids if i in valid})
    brief.competitors = brief.competitors[:2]

    if revising:
        state.revised_draft = brief
        state.revision_count += 1
        state.add_log("Analyst", "Revised the brief based on critic feedback.")
    else:
        state.draft = brief
        state.add_log("Analyst", "Wrote first draft. Handing off to Critic.")
    return state
