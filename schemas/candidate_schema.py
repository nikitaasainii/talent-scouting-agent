from pydantic import BaseModel, Field
from typing import List, Optional

class WorkExperience(BaseModel):
    company: str
    role: str
    years: float
    skills_used: List[str]

class Candidate(BaseModel):
    id: str
    name: str
    github_url: str
    current_role: str
    total_experience_years: float
    skills: List[str]                   # Derived from GitHub languages + bio
    location: str
    open_to_remote: bool
    bio: str
    public_repos: int
    followers: int
    top_repositories: List[str]         # Repo names, used for context
    hireable: Optional[bool] = None     # GitHub's own hireable flag
    enriched_summary: str               # LLM-generated summary from GitHub data