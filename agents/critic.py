"""Critic: reviews the draft against the findings and may request one revision."""
from __future__ import annotations

from core.llm import chat_json
from core.models import CriticFeedback, ResearchState

SYSTEM = (
    "You are a strict but fair reviewer of market research briefs. Check the draft against "
    "the findings and approve it only if ALL of these hold:\n"
    "1. Every claim, number and name is supported by the findings (no hallucination).\n"
    "2. Claims carry source citations like [1].\n"
    "3. It has a summary, at most 2 competitors (if relevant), key observations, and "
    "a missing_information list.\n"
    "4. Obvious gaps (e.g. no market size data) are listed in missing_information.\n"
    "5. It is concise and answers the research request.\n"
    "Never ask the analyst to add facts, names or competitors that are NOT in the findings; missing items belong in missing_information instead.\n"
    "Approve if issues are only minor style points. Otherwise set approved=false, list concrete "
    "issues, and give clear revision_instructions."
)


def run(state: ResearchState) -> ResearchState:
    findings = "\n".join(
        f"- {f.fact} (sources: {f.source_ids})" for f in state.findings.findings
    )
    user = (
        f"Research request: {state.query}\n\nFindings:\n{findings}\n\n"
        f"Draft brief:\n{state.draft.model_dump_json(indent=2)}"
    )
    state.feedback = chat_json(SYSTEM, user, CriticFeedback)
    if state.feedback.approved:
        state.add_log("Critic", "Approved the draft.")
    else:
        state.add_log("Critic", f"Requested a revision: {len(state.feedback.issues)} issue(s).")
    return state
