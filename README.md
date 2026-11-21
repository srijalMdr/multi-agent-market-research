# 🔎 Multi-Agent Market Research App

A simple Streamlit web app: enter a company or industry (e.g. *"Analyze the food delivery market in Nepal."*), and four AI agents research it on the web and write a short, sourced research brief.

- **Sample output:** [sample_output.md](sample_output.md)
- **Screenshot:** [docs/screenshot.png](docs/screenshot.png)
- **Demo video:** _add link here_

---

## How it works

```
User query
   │
   ▼
Orchestrator ─► Researcher ─► Analyst ─► Critic ─┬─ approved ──────────────► Final brief
                                                 └─ revision needed (max 1) ─► Analyst revises ─► Final brief
```

| Agent | File | Job |
|-------|------|-----|
| **Orchestrator** | `agents/orchestrator.py` | Receives the query, creates the shared state, runs the agents in order, allows **at most one** revision |
| **Researcher** | `agents/researcher.py` | Plans 3 search queries, runs web search, keeps up to 10 sources, extracts short facts **each tagged with source ids** |
| **Analyst** | `agents/analyst.py` | Writes the brief using **only** the findings, with citations like `[3]`, and lists missing information |
| **Critic** | `agents/critic.py` | Checks the draft against the findings (unsupported claims, wrong citations, missing sections) and approves or requests one revision |

All agents use the same LLM.

### Shared data

Agents pass a single **Pydantic** object, `ResearchState` (`core/models.py`), from one to the next:

```python
class ResearchState(BaseModel):
    query: str
    findings: ResearchFindings | None   # sources + sourced facts (Researcher)
    draft: Brief | None                 # first draft (Analyst)
    feedback: CriticFeedback | None     # approved / issues / instructions (Critic)
    revised_draft: Brief | None         # revision, if requested (Analyst)
    revision_count: int
    final_brief: Brief | None
    log: list[str]                      # handoff trail shown in the UI
```

The app shows this whole trail under **"Agent handoffs"**: log, findings, first draft, critic feedback and the full JSON state.

### The brief contains

- Summary of the topic
- Up to two competitors (if relevant)
- Key observations
- Sources (clickable) and missing information

### Search fallback

1. **Tavily** (if `TAVILY_API_KEY` is set) → 2. **DuckDuckGo** (no key needed) → 3. **Sample data** from `sample_data/`, clearly labelled `[SAMPLE DATA]` with a warning banner in the app.

---

## Requirements

- Python **3.10+**
- A free **Groq** API key: https://console.groq.com/keys
- *(Optional, recommended)* A free **Tavily** API key: https://app.tavily.com. Search results are better with it.

---

## Setup

### 1. Clone

```bash
git clone https://github.com/<your-username>/multi-agent-market-research.git
cd multi-agent-market-research
```

### 2. Create a virtual environment and install dependencies

**macOS / Linux**
```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

**Windows (PowerShell)**
```powershell
python -m venv .venv
.venv\Scripts\Activate.ps1
pip install -r requirements.txt
```

### 3. Add your API keys

```bash
cp .env.example .env        # Windows: copy .env.example .env
```

Open `.env` and fill in:

```
LLM_API_KEY=gsk_...            # your Groq key (required)
TAVILY_API_KEY=tvly-...        # optional; leave as-is to use DuckDuckGo
```

---

## Run

```bash
streamlit run app.py
```

Open **http://localhost:8501**, type a company or industry, and click **Start research**. A run takes about 20–60 seconds.

Example queries:
- `Analyze the food delivery market in Nepal.`
- `Pathao Nepal`
- `Electric vehicle market in India`

---

## Using a different LLM provider

The app works with any OpenAI-compatible API. Change these three lines in `.env`:

| Provider | `LLM_BASE_URL` | `LLM_MODEL` (example) |
|----------|----------------|------------------------|
| Groq (default) | `https://api.groq.com/openai/v1` | `openai/gpt-oss-120b` |
| OpenAI | `https://api.openai.com/v1` | `gpt-4o-mini` |
| Google Gemini | `https://generativelanguage.googleapis.com/v1beta/openai/` | `gemini-2.0-flash` |

---

## Project structure

```
├── app.py                  # Streamlit UI
├── agents/
│   ├── orchestrator.py     # workflow + max 1 revision
│   ├── researcher.py       # search + sourced findings
│   ├── analyst.py          # writes / revises the brief
│   └── critic.py           # reviews the brief
├── core/
│   ├── models.py           # Pydantic shared data (ResearchState, Brief, ...)
│   ├── llm.py              # LLM client + validated JSON output with retry
│   ├── search.py           # Tavily → DuckDuckGo → sample data
│   └── report.py           # brief → Markdown
├── sample_data/            # labelled offline sample data
├── sample_output.md        # one real run
├── .env.example            # placeholder config
└── requirements.txt
```

---

## Troubleshooting

| Problem | Fix |
|---------|-----|
| "LLM_API_KEY is missing" | Create `.env` from `.env.example` and add your key, then restart Streamlit |
| `404 model does not exist` | The provider retired the model. Pick a current one from your provider's model list and set `LLM_MODEL` |
| `429` / rate limit | Free tiers have limits; wait a minute and try again |
| Brief says it used SAMPLE DATA | Live search failed (no internet, or blocked). Check your connection or add a Tavily key |
| Port 8501 already in use | `streamlit run app.py --server.port 8502` |

---

## Limitations and possible improvements

- Search results are short snippets, not full pages, so details like market size are often missing. The brief lists these under **Missing information** instead of guessing.
- The LLM can still occasionally misread a source. The Critic reduces this but doesn't eliminate it.
- Possible next steps: fetch full page text, cache results, run searches in parallel, add automated tests, deploy to Streamlit Community Cloud.

---

*No API keys are included in this repository. `.env` is git-ignored.*
