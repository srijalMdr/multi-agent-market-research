"""Orchestrator: receives the query, runs the agents in sequence, allows one revision."""
from __future__ import annotations

from typing import Callable

from agents import analyst, critic, researcher
from core.models import ResearchState

MAX_REVISIONS = 1

StepCallback = Callable[[str, ResearchState], None]


def run(query: str, on_step: StepCallback | None = None) -> ResearchState:
    query = query.strip()
    if not query:
        raise ValueError("Please enter a company or industry to research.")

    def step(name: str, state: ResearchState) -> None:
        if on_step:
            on_step(name, state)

    state = ResearchState(query=query)
    state.add_log("Orchestrator", f"Received query: '{query}'. Starting workflow.")
    step("orchestrator", state)

    state = researcher.run(state)
    step("researcher", state)

    state = analyst.run(state)
    step("analyst", state)

    state = critic.run(state)
    step("critic", state)

    if not state.feedback.approved and state.revision_count < MAX_REVISIONS:
        state = analyst.run(state)
        step("revision", state)
        state.final_brief = state.revised_draft
    else:
        state.final_brief = state.draft

    state.add_log("Orchestrator", "Workflow complete. Final brief ready.")
    step("done", state)
    return state
