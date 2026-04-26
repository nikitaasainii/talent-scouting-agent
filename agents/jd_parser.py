import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from utils.llm import call_llm, parse_llm_json
from utils.prompts import JD_PARSER_PROMPT
from schemas.jd_schema import ParsedJD

class JDParserAgent:
    def __init__(self):
        self.name = "JDParserAgent"

    def run(self, raw_jd: str) -> tuple[ParsedJD, list[str]]:
        trace = []
        trace.append(f"[{self.name}] Starting JD parsing...")

        raw_response = call_llm(JD_PARSER_PROMPT, f"Parse this JD:\n\n{raw_jd}")
        
        try:
            # Replaced the manual .strip() and .lstrip() with the safe JSON extractor
            parsed_dict = parse_llm_json(raw_response)
            parsed_jd = ParsedJD(**parsed_dict)
            
        except Exception as e:
            trace.append(f"[{self.name}] ❌ ERROR parsing JSON: {e}")
            raise ValueError(f"Failed to parse JD JSON: {e}")

        trace.append(f"[{self.name}] ✓ Role: {parsed_jd.job_title}")
        trace.append(f"[{self.name}] ✓ Skills: {parsed_jd.required_skills}")
        trace.append(f"[{self.name}] ✓ Experience: {parsed_jd.min_experience_years}+ yrs")
        trace.append(f"[{self.name}] ✓ Seniority: {parsed_jd.seniority.value}")

        return parsed_jd, trace