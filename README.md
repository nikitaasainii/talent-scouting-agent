# 🎯 Talent Scout AI Agent

> *From job description to ranked shortlist — in minutes, not hours.*

Built for the **AI-Powered Talent Scouting & Engagement Hackathon**. An end-to-end agentic recruitment pipeline that discovers real candidates across GitHub, LinkedIn, and the open web, simulates outreach conversations, and delivers a recruiter-ready ranked shortlist with full explainability.

---

## ✦ What It Does

Paste a Job Description. The agent handles everything else.

```
JD Input  ──►  Parse  ──►  Discover  ──►  Match  ──►  Outreach  ──►  Score  ──►  Shortlist
```

| Stage | Agent | What Happens |
|---|---|---|
| 1 | **JD Parser** | Extracts skills, experience, seniority, location, role type |
| 2 | **Web Discovery** | X-Ray searches LinkedIn & GitHub via Tavily |
| 3 | **GitHub Discovery** | Searches real individual developers by language + activity |
| 4 | **HN Discovery** | Scrapes "Who's Hiring" threads for high-intent candidates |
| 5 | **Semantic Matcher** | ChromaDB vector search + LLM match scoring with reasons |
| 6 | **Outreach Agent** | Simulates a 4-turn recruiter conversation per candidate |
| 7 | **Scorer & Ranker** | Weighted combined score → final ranked shortlist |

---

## ✦ Scoring Model

Every candidate is scored on two independent dimensions:

```
Combined Score = (Match Score × 60%) + (Interest Score × 40%)
```

| Dimension | Weight | What It Measures |
|---|---|---|
| 🟢 **Match Score** | 60% | Skill overlap, years of experience, seniority alignment |
| 🔵 **Interest Score** | 40% | Enthusiasm, availability, salary alignment from conversation |
| 🔴 **Combined Score** | — | Weighted final rank — what the recruiter acts on |

Every score comes with **bullet-point reasons** — not just a number.

---

## ✦ Tech Stack

```
LLM Backbone     →  Groq (Llama 3.3 70B / llama-3.1-8b-instant fallback)
Agent Framework  →  LangGraph (state machine orchestration)
Candidate Source →  GitHub REST API + Tavily Web Search (LinkedIn/Wellfound X-Ray)
Vector DB        →  ChromaDB + sentence-transformers (all-MiniLM-L6-v2)
Data Validation  →  Pydantic v2 (strict schemas between every agent)
API Layer        →  FastAPI + Uvicorn
UI               →  Streamlit (editorial white theme)
Environment      →  Python 3.12, venv
```

---

## ✦ Architecture

```
                    ┌─────────────────────────────────────┐
                    │         LANGGRAPH ORCHESTRATOR        │
                    │     (typed state passed per node)     │
                    └──────────────┬──────────────────────┘
                                   │
     ┌─────────────┬───────────────┼──────────────┬──────────────────┐
     ▼             ▼               ▼               ▼                  ▼
[JD Parser]  [Web Discovery]  [GitHub        [HN Discovery]   [ChromaDB
             LinkedIn/         Discovery]    HN Who's          Vector Store]
             Wellfound         Real devs     Hiring                │
             via Tavily        type:user                           │
                    │               │               │              │
                    └───────────────┴───────────────┘              │
                                   │ all_candidates                │
                                   ▼                               │
                            [seed_chromadb] ───────────────────────┘
                                   │
                                   ▼
                         [Candidate Matcher]
                         Semantic search +
                         LLM match scoring
                                   │
                                   ▼
                          [Outreach Agent]
                          4-turn simulated
                          conversation +
                          interest scoring
                                   │
                                   ▼
                         [Scorer & Ranker]
                         Weighted combined
                         score → FinalShortlist
```

---

## ✦ Project Structure

```
talent-scout-agent/
├── agents/
│   ├── jd_parser.py          # Extracts structured requirements from raw JD
│   ├── github_discovery.py   # Finds real individual developers via GitHub API
│   ├── web_discovery.py      # X-Ray searches LinkedIn/Wellfound via Tavily
│   ├── hn_discovery.py       # Scrapes Hacker News "Who's Hiring" threads
│   ├── candidate_matcher.py  # Semantic search + LLM match scoring
│   ├── outreach.py           # Simulates recruiter-candidate conversation
│   ├── scorer.py             # Computes weighted scores + final shortlist
│   └── orchestrator.py       # LangGraph state machine
├── schemas/
│   ├── jd_schema.py          # ParsedJD — structured JD output
│   ├── candidate_schema.py   # Candidate — unified profile schema
│   └── output_schema.py      # ScoredCandidate, FinalShortlist, InterestSignals
├── data/
│   ├── seed_chromadb.py      # Embeds candidates into vector DB
│   ├── candidates.json       # Auto-generated backup of discovered profiles
│   └── chroma_db/            # Local persistent vector store
├── utils/
│   ├── llm.py                # Groq client with multi-model fallback
│   └── prompts.py            # All system prompts centralized
├── api/
│   └── main.py               # FastAPI — exposes /scout endpoint
├── ui/
│   └── app.py                # Streamlit — editorial white UI
├── .env                      # API keys (never commit)
├── requirements.txt
└── README.md
```

---

## ✦ Setup

### 1. Clone & Install

```bash
git clone https://github.com/yourusername/talent-scout-agent
cd talent-scout-agent

python3 -m venv venv
source venv/bin/activate          # Mac/Linux
# venv\Scripts\activate           # Windows

pip install -r requirements.txt
```

### 2. Environment Variables

Create a `.env` file in the project root:

```env
GROQ_API_KEY=your_groq_api_key
GITHUB_TOKEN=your_github_personal_access_token
TAVILY_API_KEY=your_tavily_api_key
```

| Key | Where to Get It | Required |
|---|---|---|
| `GROQ_API_KEY` | [console.groq.com](https://console.groq.com) | ✅ Yes |
| `GITHUB_TOKEN` | GitHub → Settings → Developer Settings → PAT | ✅ Yes |
| `TAVILY_API_KEY` | [tavily.com](https://tavily.com) | Optional (enables LinkedIn/web discovery) |

**GitHub Token Scopes needed:** `read:user`, `read:org` only.

### 3. Run

```bash
# Terminal 1 — API backend
python api/main.py

# Terminal 2 — Streamlit UI
python3 -m streamlit run ui/app.py
```

UI opens at **http://localhost:8501**

---

## ✦ API Reference

### `POST /scout`

Run the full talent scouting pipeline.

**Request:**
```json
{
  "raw_jd": "Senior Backend Engineer — Fintech Startup, Bangalore..."
}
```

**Response:** `FinalShortlist` object containing ranked candidates with match scores, interest scores, simulated conversations, and full agent trace.

### `GET /health`

```json
{ "status": "ok", "message": "All systems operational" }
```

---

## ✦ UI Walkthrough

| View | What You See |
|---|---|
| **Home** | Paste JD → hit "commence search" |
| **Shortlist** | Ranked candidate cards with match score, platform badge, scouting analysis |
| **Chat** | Full simulated recruiter ↔ candidate conversations per candidate |
| **Trace** | Complete agent decision log — every step, every decision |

---

## ✦ Key Design Decisions

**GitHub over LinkedIn (for developer search)**
GitHub's official API gives verifiable, structured data — real repos, real languages, real activity. LinkedIn URLs require authentication to view and always redirect unauthenticated users to the homepage. For LinkedIn candidates found via web search, the UI links to a LinkedIn people search for the candidate's name instead.

**`type:user` filter on all GitHub queries**
Without this, GitHub search returns organizations, open source projects, and community accounts. Every query explicitly filters to individual users only.

**LangGraph over linear scripts**
The orchestrator is a typed state machine. Each node receives and returns a validated `AgentState` dict. This means the pipeline is resumable, debuggable, and each agent is independently testable.

**Pydantic v2 schemas between every agent**
Every agent input and output is validated. Silent failures and key mismatches surface immediately as validation errors rather than downstream crashes.

**Multi-model fallback in LLM layer**
The free Groq tier has a 100k token/day limit per model. `call_llm` automatically falls back through multiple models if one hits its limit — the demo keeps running.

**Explainability first**
Every score is accompanied by bullet-point reasons. The recruiter sees *why* a candidate scored 87, not just the number.

---

## ✦ Troubleshooting

| Problem | Fix |
|---|---|
| `Collection does not exist` | ChromaDB wiped between runs — discovery node re-seeds automatically |
| `Rate limit exceeded` on Groq | `call_llm` falls back to next model automatically; if all hit limits, wait 10 min |
| GitHub returns 0 users | Agent tries 4 fallback queries automatically |
| LinkedIn profile links redirect to homepage | Known LinkedIn limitation — UI now shows people search link instead |
| `node_score is not defined` | Ensure all node functions are defined *before* `build_graph()` in orchestrator.py |
| M1 Mac import errors | Always use `python3 -m streamlit run ui/app.py` not `streamlit run` |

---

## ✦ Roadmap

- [ ] Real async outreach via email/LinkedIn API
- [ ] Candidate deduplication across sources
- [ ] Persistent run history and candidate database
- [ ] Export shortlist to CSV / ATS integration
- [ ] Confidence intervals on match scores
- [ ] Support for non-technical roles (design, product, ops)

---

## ✦ Built With

- [Groq](https://groq.com) — Fastest LLM inference
- [LangGraph](https://langchain-ai.github.io/langgraph/) — Agent orchestration
- [ChromaDB](https://www.trychroma.com) — Local vector database
- [Tavily](https://tavily.com) — AI-optimized web search
- [GitHub REST API](https://docs.github.com/en/rest) — Developer discovery
- [Streamlit](https://streamlit.io) — UI framework
- [FastAPI](https://fastapi.tiangolo.com) — API layer

---

<div align="center">
  <sub>Built in 3 days for a hackathon. Not affiliated with LinkedIn, GitHub, or any mentioned platforms.</sub>
</div>