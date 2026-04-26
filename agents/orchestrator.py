import os
import sys
import json
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from typing import TypedDict
from langgraph.graph import StateGraph, END

from agents.jd_parser import JDParserAgent
from agents.github_discovery import GitHubDiscoveryAgent
from agents.candidate_matcher import CandidateMatcherAgent
from agents.outreach import OutreachAgent
from agents.scorer import ScorerAgent
from agents.hn_discovery import HNDiscoveryAgent
from agents.web_discovery import WebDiscoveryAgent # New Agent
from schemas.jd_schema import ParsedJD
from schemas.output_schema import FinalShortlist
from data.seed_chromadb import seed_from_candidates

# ------------------------------------------------------------------ #
#  LangGraph State                                                    #
# ------------------------------------------------------------------ #
class AgentState(TypedDict):
    raw_jd: str
    parsed_jd: ParsedJD | None
    candidates_found: int
    matched_candidates: list
    outreach_results: list
    shortlist: FinalShortlist | None
    trace: list[str]
    error: str | None

# ------------------------------------------------------------------ #
#  Node functions                                                     #
# ------------------------------------------------------------------ #
def node_parse_jd(state: AgentState) -> AgentState:
    agent = JDParserAgent()
    parsed_jd, trace = agent.run(state["raw_jd"])
    return {**state, "parsed_jd": parsed_jd, "trace": state["trace"] + trace}

def node_discover_candidates(state: AgentState) -> AgentState:
    parsed_jd = state["parsed_jd"]
    current_trace = state.get("trace", [])
    
    all_candidates = []
    
    # 1. Web Discovery (LinkedIn / Wellfound via Tavily)
    try:
        web_agent = WebDiscoveryAgent()
        web_candidates, web_trace = web_agent.run(parsed_jd, max_candidates=10)
        all_candidates.extend(web_candidates)
        current_trace.extend(web_trace)
    except Exception as e:
        current_trace.append(f"[Orchestrator] ⚠ Web Discovery failed: {e}")

    # 2. Hacker News (High Intent)
    try:
        hn_agent = HNDiscoveryAgent()
        hn_candidates, hn_trace = hn_agent.run(parsed_jd, max_candidates=10)
        all_candidates.extend(hn_candidates)
        current_trace.extend(hn_trace)
    except Exception as e:
        current_trace.append(f"[Orchestrator] ⚠ HN Discovery failed: {e}")

    # 3. GitHub (Technical Validation)
    try:
        gh_agent = GitHubDiscoveryAgent()
        gh_candidates, gh_trace = gh_agent.run(parsed_jd, max_candidates=10)
        all_candidates.extend(gh_candidates)
        current_trace.extend(gh_trace)
    except Exception as e:
        current_trace.append(f"[Orchestrator] ⚠ GitHub Discovery failed: {e}")

    current_trace.append(
        f"[Orchestrator] Discovery Complete: {len(all_candidates)} total candidates across Web, HN, and GitHub."
    )
    
    # INDUSTRY GRADE: Seed discovered candidates into Vector DB for the Matcher
    if all_candidates:
        seed_from_candidates(all_candidates)
        current_trace.append(f"[Orchestrator] Successfully indexed {len(all_candidates)} candidates into ChromaDB.")
    
    return {**state, "candidates_found": len(all_candidates), "trace": current_trace}

def node_match_candidates(state: AgentState) -> AgentState:
    agent = CandidateMatcherAgent()
    # No need to load_collection manually, __init__ does it
    matched, trace = agent.run(state["parsed_jd"], top_n=8)
    return {**state, "matched_candidates": matched, "trace": state["trace"] + trace}

def node_outreach(state: AgentState) -> AgentState:
    agent = OutreachAgent()
    results, trace = agent.run(state["matched_candidates"], state["parsed_jd"])
    return {**state, "outreach_results": results, "trace": state["trace"] + trace}

def node_score(state):
    agent = ScorerAgent()
    
    # We pass the four specific arguments the Scorer expects
    shortlist, trace = agent.run(
        state["outreach_results"],
        state["parsed_jd"].job_title if state["parsed_jd"] else "Software Engineer",
        state["candidates_found"],
        state["trace"]
    )
    
    return {**state, "shortlist": shortlist, "trace": state["trace"] + trace}
# ------------------------------------------------------------------ #
#  Build the graph                                                    #
# ------------------------------------------------------------------ #
def build_graph():
    graph = StateGraph(AgentState)

    graph.add_node("parse_jd", node_parse_jd)
    graph.add_node("discover_candidates", node_discover_candidates)
    graph.add_node("match_candidates", node_match_candidates)
    graph.add_node("outreach", node_outreach)
    graph.add_node("score", node_score)

    graph.set_entry_point("parse_jd")
    graph.add_edge("parse_jd", "discover_candidates")
    graph.add_edge("discover_candidates", "match_candidates")
    graph.add_edge("match_candidates", "outreach")
    graph.add_edge("outreach", "score")
    graph.add_edge("score", END)

    return graph.compile()

def run_pipeline(raw_jd: str) -> FinalShortlist:
    graph = build_graph()
    initial_state: AgentState = {
        "raw_jd": raw_jd,
        "parsed_jd": None,
        "candidates_found": 0,
        "matched_candidates": [],
        "outreach_results": [],
        "shortlist": None,
        "trace": [],
        "error": None
    }
    final_state = graph.invoke(initial_state)
    return final_state["shortlist"]