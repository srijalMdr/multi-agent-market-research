"""Streamlit UI for the multi-agent market research app.

Run:  streamlit run app.py
"""
from __future__ import annotations

import streamlit as st

from agents import orchestrator
from core.llm import LLMError, has_llm_key, llm_config
from core.models import ResearchState
from core.report import brief_to_markdown, cite
from core.search import has_tavily_key

st.set_page_config(page_title="Market Research Agents", page_icon="🔎", layout="centered")

STEP_LABELS = {
    "orchestrator": "🧭 Orchestrator received the query",
    "researcher": "🔍 Researcher gathered sources and findings",
    "analyst": "✍️ Analyst wrote the first draft",
    "critic": "🧐 Critic reviewed the draft",
    "revision": "🔁 Analyst revised the brief using critic feedback",
    "done": "✅ Final brief ready",
}


# ---------------- Sidebar ----------------
with st.sidebar:
    st.header("⚙️ Setup")
    st.write(f"**LLM:** `{llm_config()['model']}`")
    st.write("LLM key: " + ("✅ found" if has_llm_key() else "❌ missing"))
    st.write("Search: " + ("✅ Tavily" if has_tavily_key() else "🦆 DuckDuckGo (no Tavily key)"))
    st.caption("If live search fails, clearly labelled sample data is used.")
    st.divider()
    st.markdown(
        "**Workflow**\n\n1. Orchestrator\n2. Researcher\n3. Analyst\n4. Critic\n"
        "5. Analyst revision (max 1)"
    )

# ---------------- Main ----------------
st.title("🔎 Multi-Agent Market Research")
st.write("Enter a company or industry. Four AI agents will research it and write a short brief.")

query = st.text_input(
    "Company or industry",
    placeholder="Analyze the food delivery market in Nepal.",
)
start = st.button("Start research", type="primary", disabled=not has_llm_key())

if not has_llm_key():
    st.error("LLM_API_KEY is missing. Copy `.env.example` to `.env`, add your key, and restart.")

if start:
    if not query.strip():
        st.warning("Please enter a company or industry.")
    else:
        try:
            with st.status("Running agents...", expanded=True) as status:

                def on_step(name: str, state: ResearchState) -> None:
                    st.write(STEP_LABELS.get(name, name))
                    if name == "critic":
                        st.caption("Approved" if state.feedback.approved else "Revision requested")

                result = orchestrator.run(query, on_step=on_step)
                status.update(label="Research complete", state="complete", expanded=False)
            st.session_state["result"] = result
        except LLMError as e:
            st.error(f"LLM error: {e}")
        except Exception as e:  # noqa: BLE001
            st.error(f"Something went wrong: {e}")

state: ResearchState | None = st.session_state.get("result")
if state and state.final_brief:
    st.divider()
    md = brief_to_markdown(state)
    st.markdown(md)
    st.download_button("⬇️ Download brief (Markdown)", md, file_name="research_brief.md")

    st.subheader("🔗 Agent handoffs")
    with st.expander("Handoff log"):
        for line in state.log:
            st.text(line)
    with st.expander(f"Research findings ({len(state.findings.findings)})"):
        st.write("**Search queries:**", state.findings.search_queries)
        for f in state.findings.findings:
            st.markdown(f"- {f.fact} {cite(f.source_ids)}")
    with st.expander("First draft (before critic)"):
        st.json(state.draft.model_dump())
    with st.expander("Critic feedback"):
        st.json(state.feedback.model_dump())
    with st.expander("Full shared state (JSON)"):
        st.json(state.model_dump())
