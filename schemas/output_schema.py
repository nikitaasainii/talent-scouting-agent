from pydantic import BaseModel
from typing import List

class ConversationTurn(BaseModel):
    speaker: str
    message: str

class InterestSignals(BaseModel):
    open_to_move: bool
    enthusiasm_level: str       # "low" | "medium" | "high"
    salary_aligned: bool
    key_quotes: List[str]

class ScoredCandidate(BaseModel):
    candidate_id: str
    candidate_name: str
    github_url: str
    match_score: float
    interest_score: float
    combined_score: float
    match_reasons: List[str]
    interest_reasons: List[str]
    conversation: List[ConversationTurn]
    interest_signals: InterestSignals
    rank: int

class FinalShortlist(BaseModel):
    job_title: str
    total_candidates_evaluated: int
    shortlisted: List[ScoredCandidate]
    agent_trace: List[str]