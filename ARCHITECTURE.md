# Architecture & Scoring Logic

## Pipeline Diagram

```
JD Input (raw text)
        │
        ▼
┌─────────────────┐
│  JD Parser      │  Extracts: skills, seniority, experience, location, role type
└────────┬────────┘
         │
    ┌────┴─────────────────────┐
    ▼           ▼              ▼
┌──────────┐ ┌──────────┐ ┌──────────┐
│  Web     │ │  GitHub  │ │    HN    │
│Discovery │ │Discovery │ │Discovery │
│LinkedIn  │ │type:user │ │Who's     │
│Wellfound │ │filter    │ │Hiring    │
└────┬─────┘ └────┬─────┘ └────┬─────┘
     └────────────┴────────────┘
                  │
                  ▼
        ┌──────────────────┐
        │  ChromaDB        │  all-MiniLM-L6-v2 embeddings
        │  Vector Store    │
        └────────┬─────────┘
                 │
                 ▼
        ┌──────────────────┐
        │ Candidate Matcher│  Semantic search + LLM match scoring
        └────────┬─────────┘
                 │
                 ▼
        ┌──────────────────┐
        │ Outreach Agent   │  Simulated 4-turn conversation + interest scoring
        └────────┬─────────┘
                 │
                 ▼
        ┌──────────────────┐
        │ Scorer & Ranker  │  Weighted combined score → FinalShortlist
        └──────────────────┘
```

Orchestrated by **LangGraph** as a typed state machine.
LLM: **Groq Llama 3.3 70B** with multi-model fallback.

---

## Scoring Logic

### Match Score (0–100)
Computed by the LLM given the parsed JD and candidate profile:

| Range | Meaning |
|---|---|
| 90–100 | All required skills present, experience aligned, seniority match |
| 70–89 | Most requirements met, minor gaps |
| 50–69 | Partial fit, notable missing skills |
| Below 50 | Poor fit |

### Interest Score (0–100)
Extracted from simulated conversation signals:

| Signal | What it measures |
|---|---|
| Enthusiasm level | low / medium / high from conversation tone |
| Open to move | Willing to change jobs / relocate |
| Salary aligned | Expected compensation fits role range |
| Notice period | Availability matches recruiter's need |

### Combined Score
```
Combined = (Match Score × 0.60) + (Interest Score × 0.40)
```

Match weighted higher because technical fit is harder to train than interest.

---

## Sample Input

```
Senior Backend Engineer — Fintech Startup, Bangalore (Hybrid)

Requirements:
- 4+ years with Python and FastAPI
- PostgreSQL, Redis, AWS (EC2, S3, Lambda)
- Docker and Kubernetes
- Nice to have: Kafka, GraphQL

Full-time hybrid. Salary: ₹30–45 LPA. Immediate joiners preferred.
```

## Sample Output

| Rank | Candidate | GitHub | Match | Interest | Combined |
|---|---|---|---|---|---|
| #1 | Sebastián Ramírez | github.com/tiangolo | 85 | 80 | 83 |
| #2 | Krish C Naik | github.com/krishnaik06 | 72 | 85 | 77 |
| #3 | Siraj Raval | github.com/llSourcell | 60 | 75 | 66 |

### Sample Conversation (Candidate #1)
**Recruiter:** Hi Sebastián, I came across your GitHub profile and was impressed by your work on FastAPI. We have a senior backend role at a fintech startup in Bangalore — would you be open to learning more?

**Candidate:** Thanks for reaching out! I'm always open to interesting opportunities. FastAPI is close to my heart, so I'd love to hear more about the role.

**Recruiter:** Great. The role involves building payments infrastructure handling 10M+ transactions. Are you available for a hybrid setup in Bangalore, and what's your current notice period?

**Candidate:** The technical challenge sounds exciting. I'm based in Berlin currently but open to relocation for the right opportunity. My notice period would be around 30 days.

### Interest Signals Extracted
- Enthusiasm: High
- Open to move: Yes
- Salary aligned: Yes
- Key quote: "FastAPI is close to my heart"