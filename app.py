"""Streamlit UI for the multi-agent market research app.

Run:  streamlit run app.py
"""
from __future__ import annotations

import html
from urllib.parse import urlparse

import streamlit as st

from agents import orchestrator
from core.llm import LLMError, has_llm_key, llm_config
from core.models import ResearchState
from core.report import brief_to_markdown, cite

st.set_page_config(page_title="Market Research Agents", layout="wide", initial_sidebar_state="collapsed")

EXAMPLES = [
    "Analyze the food delivery market in Nepal.",
    "Pathao Nepal",
    "Electric vehicle market in India",
    "Digital wallets in Nepal",
]

AGENTS = [
    ("orchestrator", "01", "Orchestrator", "Receives the query"),
    ("researcher", "02", "Researcher", "Searches the web"),
    ("analyst", "03", "Analyst", "Writes the draft"),
    ("critic", "04", "Critic", "Reviews the draft"),
    ("revision", "05", "Revision", "Fixes issues (max 1)"),
]

st.markdown(
    """
<style>
.block-container {padding-top: 1.5rem; max-width: 1100px;}
.hero {text-align: center; padding: 36px 0 22px 0;}
.hero h1 {font-size: 3rem; font-weight: 500; letter-spacing: -0.03em; line-height: 1.1;
  color: #111111; margin: 0 0 14px 0; font-family: Georgia, "Times New Roman", serif !important;}
.hero p {color: #3F3F41; font-size: 1.05rem; max-width: 560px; margin: 0 auto; line-height: 1.6;
  font-family: Georgia, "Times New Roman", serif;}
.st-key-search_card {background: #FFFFFF; border: 1px solid #E7E5E4; border-radius: 16px;
  padding: 14px 16px 12px 16px; box-shadow: 0 1px 3px rgba(0,0,0,.04);}
.st-key-search_card [data-baseweb="textarea"], .st-key-search_card [data-baseweb="base-input"],
.st-key-search_card textarea {background: #FFFFFF !important; border: none !important;
  box-shadow: none !important; padding-left: 0; font-size: 1rem; resize: none;}
.st-key-search_card [data-baseweb="textarea"]:focus-within {box-shadow: none !important; border: none !important;}
.st-key-search_card [data-testid="stTextAreaRootElement"] {background: #FFFFFF !important;
  border: 0 !important;}
.st-key-search_card [data-testid="stTextArea"] *, .st-key-search_card [data-testid="stTextArea"] *:focus,
.st-key-search_card [data-testid="stTextArea"] *:focus-within {border-color: transparent !important;
  box-shadow: none !important; outline: none !important;}
.examples {text-align: center; color: #71717A; font-size: .85rem; margin: 14px 0 6px 0;}
.pipeline {display: flex; gap: 10px; margin: 6px 0 4px 0; flex-wrap: wrap;}
.agent {
  flex: 1 1 150px; border-radius: 14px; padding: 12px 14px; border: 1.5px solid #E2E8F0;
  background: white; transition: all .2s;
}
.agent .icon {font-size: .78rem; font-weight: 700; color: #94A3B8; letter-spacing: .05em;}
.agent .name {font-weight: 700; color: #0F172A; margin-top: 2px;}
.agent .desc {font-size: .8rem; color: #64748B;}
.agent .badge {font-size: .72rem; font-weight: 600; margin-top: 6px; display: inline-block;
  padding: 2px 8px; border-radius: 999px; background: #F1F5F9; color: #64748B;}
.agent.running {border-color: #7C3AED; box-shadow: 0 0 0 4px rgba(124,58,237,.12);}
.agent.running .badge {background: #F5F3FF; color: #7C3AED;}
.agent.done {border-color: #10B981; background: #F0FDF4;}
.agent.done .badge {background: #D1FAE5; color: #047857;}
.agent.skipped {opacity: .5;}
.card {
  background: white; border: 1px solid #E2E8F0; border-radius: 14px; padding: 18px 20px;
  margin-bottom: 14px;
}
.card h4 {margin: 0 0 8px 0; color: #0F172A;}
.card p, .card li {color: #334155; line-height: 1.6;}
.card.missing {background: #FFFBEB; border-color: #FDE68A;}
.comp {background: #F8FAFC; border: 1px solid #E2E8F0; border-radius: 12px; padding: 14px 16px; height: 100%;}
.comp .cname {font-weight: 700; font-size: 1.05rem; color: #7C3AED;}
.cite {color: #7C3AED; font-weight: 600; font-size: .85em;}
.src {display: flex; gap: 12px; align-items: flex-start; padding: 10px 0; border-bottom: 1px solid #F1F5F9;}
.src .num {background: #F5F3FF; color: #7C3AED; font-weight: 700; border-radius: 8px;
  min-width: 30px; text-align: center; padding: 3px 0;}
.src a {font-weight: 600; text-decoration: none;}
.src .dom {font-size: .8rem; color: #64748B;}
.used {font-size: .7rem; background: #D1FAE5; color: #047857; padding: 1px 7px; border-radius: 999px; margin-left: 6px;}
.pipeline {margin-bottom: 18px;}
[data-testid="stMetric"] {background: white; border: 1px solid #E2E8F0; border-radius: 14px; padding: 12px 16px;}
[data-testid="stMetricValue"] {font-size: 1.7rem; color: #7C3AED; font-weight: 700;}
.scraped {font-size: .7rem; background: #F5F3FF; color: #7C3AED; padding: 1px 7px; border-radius: 999px; margin-left: 6px;}
.meta {color: #71717A; font-size: .8rem; margin: 8px 0 4px 0;}
[data-testid="stSidebarCollapsedControl"], [data-testid="stSidebar"] {display: none;}
.sample-banner {background: #FEF3C7; border: 1px solid #F59E0B; color: #92400E; border-radius: 12px;
  padding: 10px 14px; margin-bottom: 12px; font-weight: 600;}
</style>
""",
    unsafe_allow_html=True,
)


def esc(text: str) -> str:
    return html.escape(text or "")


def cite_html(ids: list[int]) -> str:
    return f' <span class="cite">{esc(cite(ids))}</span>' if ids else ""


def domain(url: str) -> str:
    return urlparse(url).netloc.replace("www.", "")


def pipeline_html(status: dict[str, str]) -> str:
    labels = {"waiting": "Waiting", "running": "Running…", "done": "Done", "skipped": "Not needed"}
    cards = []
    for key, icon, name, desc in AGENTS:
        s = status.get(key, "waiting")
        cards.append(
            f'<div class="agent {s}"><div class="icon">{icon}</div><div class="name">{name}</div>'
            f'<div class="desc">{desc}</div><div class="badge">{labels[s]}</div></div>'
        )
    return f'<div class="pipeline">{"".join(cards)}</div>'


def set_query(q: str) -> None:
    st.session_state["query"] = q


st.markdown(
    '<div class="hero"><h1>Multi-Agent Market Research</h1>'
    "<p>Enter a company or industry. Four AI agents search the web, write a short brief, "
    "and check it against the sources.</p></div>",
    unsafe_allow_html=True,
)

_, mid, _ = st.columns([1, 6, 1])
with mid:
    with st.container(key="search_card"):
        query = st.text_area(
            "Company or industry",
            key="query",
            placeholder="Describe a company or industry to research...",
            label_visibility="collapsed",
            height=90,
        )
        _, c2 = st.columns([4, 1.2], vertical_alignment="center")
        with c2:
            start = st.button(
                "Start research", type="primary", use_container_width=True, disabled=not has_llm_key()
            )
    st.markdown('<div class="examples">Try an example</div>', unsafe_allow_html=True)
    ex_cols = st.columns(len(EXAMPLES))
    for col, ex in zip(ex_cols, EXAMPLES):
        col.button(ex, on_click=set_query, args=(ex,), use_container_width=True, key=f"ex_{ex}")
    st.write("")

if not has_llm_key():
    st.error("LLM_API_KEY is missing. Copy `.env.example` to `.env`, add your key, and restart.")

pipeline_slot = st.empty()

if start:
    if not query.strip():
        st.warning("Please enter a company or industry.")
    else:
        status = {"orchestrator": "running"}
        pipeline_slot.markdown(pipeline_html(status), unsafe_allow_html=True)
        next_step = {"orchestrator": "researcher", "researcher": "analyst", "analyst": "critic"}

        def on_step(name: str, state: ResearchState) -> None:
            if name in next_step:
                status[name] = "done"
                status[next_step[name]] = "running"
            elif name == "critic":
                status["critic"] = "done"
                status["revision"] = "skipped" if state.feedback.approved else "running"
            elif name == "revision":
                status["revision"] = "done"
            pipeline_slot.markdown(pipeline_html(status), unsafe_allow_html=True)

        try:
            with st.spinner("Agents are working… this usually takes 20–60 seconds."):
                st.session_state["result"] = orchestrator.run(query, on_step=on_step)
        except LLMError as e:
            st.error(str(e))
        except Exception as e:
            st.error(f"Something went wrong: {e}")

state: ResearchState | None = st.session_state.get("result")

if state and state.final_brief:
    if not start:
        done = {k: "done" for k, *_ in AGENTS}
        if state.revision_count == 0:
            done["revision"] = "skipped"
        pipeline_slot.markdown(pipeline_html(done), unsafe_allow_html=True)

    b = state.final_brief
    f = state.findings
    src = {s.id: s for s in f.sources}

    st.markdown(f"## {esc(state.query)}")
    m1, m2, m3, m4 = st.columns(4)
    m1.metric("Sources", len(f.sources), help=f"via {f.search_provider}")
    m2.metric("Sourced findings", len(f.findings))
    m3.metric("Competitors", len(b.competitors))
    m4.metric("Critic", "Approved" if state.feedback.approved else "1 revision")
    st.markdown(
        f'<div class="meta">Search: {esc(f.search_provider)} &middot; Pages scraped: {f.scraped_count} &middot; Model: {esc(llm_config()["model"])}</div>',
        unsafe_allow_html=True,
    )

    if f.is_sample_data:
        st.markdown(
            '<div class="sample-banner">Live search was unavailable. This brief uses labelled '
            "SAMPLE DATA, not verified facts.</div>",
            unsafe_allow_html=True,
        )

    tab_brief, tab_trail, tab_src = st.tabs(["Brief", "Agent trail", "Sources"])

    with tab_brief:
        st.markdown(
            f'<div class="card"><h4>Summary</h4><p>{esc(b.summary)}</p></div>',
            unsafe_allow_html=True,
        )

        st.markdown("#### Competitors")
        if b.competitors:
            cols = st.columns(len(b.competitors))
            for col, c in zip(cols, b.competitors):
                col.markdown(
                    f'<div class="comp"><div class="cname">{esc(c.name)}</div>'
                    f"<p>{esc(c.description)}{'' if '[' in c.description else cite_html(c.source_ids)}</p></div>",
                    unsafe_allow_html=True,
                )
        else:
            st.info("No relevant competitors were identified in the sources.")

        st.write("")
        left, right = st.columns([3, 2])
        with left:
            obs = "".join(f"<li>{esc(o)}</li>" for o in b.key_observations)
            st.markdown(
                f'<div class="card"><h4>Key observations</h4><ul>{obs}</ul></div>',
                unsafe_allow_html=True,
            )
        with right:
            miss = "".join(f"<li>{esc(m)}</li>" for m in b.missing_information) or "<li>None noted.</li>"
            st.markdown(
                f'<div class="card missing"><h4>Missing information</h4><ul>{miss}</ul></div>',
                unsafe_allow_html=True,
            )

        st.download_button(
            "Download brief (Markdown)",
            brief_to_markdown(state),
            file_name="research_brief.md",
            type="primary",
        )

    with tab_trail:
        st.markdown("##### Handoff log")
        st.code("\n".join(state.log), language=None)

        with st.expander(f"Researcher output: {len(f.findings)} findings", expanded=True):
            st.markdown("**Search queries:** " + " · ".join(f"`{q}`" for q in f.search_queries))
            for x in f.findings:
                st.markdown(f"- {x.fact} **{cite(x.source_ids)}**")
        with st.expander("Analyst first draft (before critic)"):
            st.json(state.draft.model_dump())
        with st.expander("Critic feedback"):
            fb = state.feedback
            if fb.approved:
                st.success("Approved the first draft.")
            else:
                st.warning("Requested one revision.")
                for i in fb.issues:
                    st.markdown(f"- {i}")
                if fb.revision_instructions:
                    st.markdown(f"**Instructions:** {fb.revision_instructions}")
        with st.expander("Full shared state (JSON)"):
            st.json(state.model_dump())

    with tab_src:
        st.caption(
            f"Collected via **{f.search_provider}**. *full text* means the page was scraped; "
            "others use the search snippet. *cited* means the brief uses it."
        )
        rows = []
        for s in f.sources:
            tag = '<span class="scraped">full text</span>' if s.scraped else ""
            tag += '<span class="used">cited</span>' if s.id in b.source_ids else ""
            rows.append(
                f'<div class="src"><div class="num">{s.id}</div><div>'
                f'<a href="{esc(s.url)}" target="_blank">{esc(s.title)}</a>{tag}'
                f'<div class="dom">{esc(domain(s.url))}</div></div></div>'
            )
        st.markdown(f'<div class="card">{"".join(rows)}</div>', unsafe_allow_html=True)
else:
    pipeline_slot.markdown(pipeline_html({}), unsafe_allow_html=True)
