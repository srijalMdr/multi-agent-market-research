"""Render a ResearchState's final brief as Markdown (used by the UI and sample output)."""
from __future__ import annotations

from core.llm import llm_config
from core.models import Brief, ResearchState


def cite(ids: list[int]) -> str:
    return "".join(f"[{i}]" for i in ids)


def brief_to_markdown(state: ResearchState) -> str:
    b: Brief = state.final_brief
    src = {s.id: s for s in state.findings.sources}
    used = b.source_ids or sorted(src)
    out = [f"# Research Brief: {state.query}\n"]
    if state.findings.is_sample_data:
        out.append("> Built from labelled SAMPLE DATA (live search unavailable).\n")
    out.append(f"## Summary\n{b.summary}\n")
    out.append("## Competitors")
    if b.competitors:
        out += [f"- **{c.name}**: {c.description}" + ("" if "[" in c.description else f" {cite(c.source_ids)}") for c in b.competitors]
    else:
        out.append("- No relevant competitors identified in the sources.")
    out.append("\n## Key Observations")
    out += [f"- {o}" for o in b.key_observations]
    out.append("\n## Sources")
    out += [f"{i}. [{src[i].title}]({src[i].url})" for i in used if i in src]
    out.append("\n## Missing Information")
    out += [f"- {m}" for m in b.missing_information] or ["- None noted."]
    out.append(
        f"\n---\n*Search: {state.findings.search_provider} · Model: {llm_config()['model']} · "
        f"Critic approved first draft: {'yes' if state.feedback.approved else 'no (1 revision)'}*"
    )
    return "\n".join(out)
