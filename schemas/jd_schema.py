from pydantic import BaseModel, Field
from typing import List, Optional
from enum import Enum

class SeniorityLevel(str, Enum):
    JUNIOR = "junior"
    MID = "mid"
    SENIOR = "senior"
    LEAD = "lead"

class RoleType(str, Enum):
    FULLTIME = "full-time"
    CONTRACT = "contract"
    INTERNSHIP = "internship"

class ParsedJD(BaseModel):
    job_title: str
    company_name: Optional[str] = None
    required_skills: List[str] = Field(..., description="Must-have technical skills")
    nice_to_have_skills: List[str] = Field(default_factory=list)
    min_experience_years: float
    max_experience_years: Optional[float] = None
    seniority: SeniorityLevel
    role_type: RoleType
    location: str
    remote_ok: bool
    key_responsibilities: List[str]
    summary: str