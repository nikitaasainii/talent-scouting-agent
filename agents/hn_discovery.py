import os
import sys
import json
import re
import time
import requests
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from utils.llm import call_llm, parse_llm_json
from schemas.candidate_schema import Candidate
from schemas.jd_schema import ParsedJD

class HNDiscoveryAgent:
    def __init__(self):
        self.name = "HNDiscoveryAgent"
        self.search_url = "https://hn.algolia.com/api/v1/search_by_date"
        self.item_url = "https://hn.algolia.com/api/v1/items/"

    # ------------------------------------------------------------------ #
    #  1. Find the latest "Who wants to be hired?" thread                #
    # ------------------------------------------------------------------ #
    def _get_latest_hiring_thread_id(self) -> str:
        params = {
            "query": '"who wants to be hired"',
            "tags": "story"
        }
        resp = requests.get(self.search_url, params=params, timeout=10)
        resp.raise_for_status()
        hits = resp.json().get("hits", [])
        if not hits:
            raise Exception("Could not find any 'Who wants to be hired?' threads.")
        
        # Return the objectID (thread ID) of the most recent post
        return str(hits[0]["objectID"])

    # ------------------------------------------------------------------ #
    #  2. Fetch comments from the thread                                 #
    # ------------------------------------------------------------------ #
    def _fetch_comments(self, thread_id: str, limit: int = 50) -> list:
        resp = requests.get(f"{self.item_url}{thread_id}", timeout=10)
        resp.raise_for_status()
        children = resp.json().get("children", [])
        
        valid_comments = []
        for child in children:
            text = child.get("text", "")
            if text and len(text) > 150: # Skip empty or extremely short joke comments
                # Clean HTML tags that Algolia returns
                clean_text = re.sub(r'<[^>]+>', ' ', text)
                valid_comments.append({
                    "username": child.get("author", "Unknown"),
                    "text": clean_text.strip(),
                    "id": child.get("id")
                })
                if len(valid_comments) >= limit:
                    break
                    
        return valid_comments

    # ------------------------------------------------------------------ #
    #  3. Use LLM to structure the raw text into our Candidate schema    #
    # ------------------------------------------------------------------ #
    def _parse_comment_to_candidate(self, comment: dict, parsed_jd: ParsedJD) -> Candidate:
        prompt = f"""
        You are an expert technical recruiter. Read this developer's "Who Wants To Be Hired" post and extract their profile into a structured JSON format.
        
        Raw Post by '{comment['username']}':
        "{comment['text']}"
        
        Return ONLY valid JSON matching this exact structure:
        {{
            "name": "Guess from text or use username",
            "current_role": "What they do or 'Seeking Opportunities'",
            "total_experience_years": 5.0, 
            "skills": ["Skill1", "Skill2", "Skill3"],
            "location": "City, Country or 'Not specified'",
            "open_to_remote": true,
            "bio": "A short 1-sentence bio",
            "github_url": "Extract github link if present, else empty string",
            "enriched_summary": "Write a professional 2-sentence recruiter summary of this candidate based on their post."
        }}
        If experience years aren't explicitly stated, estimate based on the text or default to 2.0.
        """
        
        raw_response = call_llm(
            system_prompt="You are a data extraction bot. Return ONLY JSON.",
            user_message=prompt,
            temperature=0.1
        )
        
        data = parse_llm_json(raw_response)
        
        return Candidate(
            id=f"hn_{comment['id']}",
            name=data.get("name", comment['username']),
            github_url=data.get("github_url", ""),
            current_role=data.get("current_role", "Seeking Opportunities"),
            total_experience_years=float(data.get("total_experience_years", 2.0)),
            skills=data.get("skills", ["Not specified"]),
            location=data.get("location", "Not specified"),
            open_to_remote=bool(data.get("open_to_remote", True)),
            bio=data.get("bio", ""),
            public_repos=0, # HN doesn't provide this directly
            followers=0,    # HN doesn't provide this directly
            top_repositories=[],
            hireable=True,  # 100% true because they posted in this thread!
            enriched_summary=data.get("enriched_summary", comment['text'][:200])
        )

    # ------------------------------------------------------------------ #
    #  Main run method                                                   #
    # ------------------------------------------------------------------ #
    def run(self, parsed_jd: ParsedJD, max_candidates: int = 15) -> tuple[list[Candidate], list[str]]:
        trace = []
        trace.append(f"[{self.name}] Starting Hacker News candidate discovery...")

        try:
            # Step 1: Find Thread
            thread_id = self._get_latest_hiring_thread_id()
            trace.append(f"[{self.name}] Found latest 'Who Wants To Be Hired' thread: {thread_id}")

            # Step 2: Fetch raw comments
            comments = self._fetch_comments(thread_id, limit=max_candidates * 2) # Fetch extra in case some fail parsing
            trace.append(f"[{self.name}] Pulled {len(comments)} raw comments from thread")

            # Step 3: LLM Parsing
            candidates = []
            for i, comment in enumerate(comments):
                if len(candidates) >= max_candidates:
                    break
                    
                trace.append(f"[{self.name}] Parsing candidate {len(candidates)+1}/{max_candidates}: {comment['username']}")
                try:
                    candidate = self._parse_comment_to_candidate(comment, parsed_jd)
                    candidates.append(candidate)
                    trace.append(f"[{self.name}]   ✓ {candidate.name} | {len(candidate.skills)} skills | {candidate.location}")
                except Exception as e:
                    trace.append(f"[{self.name}]   ⚠ Skipped {comment['username']} — LLM parsing failed: {e}")
                
                # Small sleep to respect rate limits on Groq
                time.sleep(1)

            trace.append(f"[{self.name}] ✅ Discovery complete — {len(candidates)} high-intent candidates built")
            return candidates, trace

        except Exception as e:
            trace.append(f"[{self.name}] ❌ Fatal Error: {str(e)}")
            return [], trace

# Quick test
if __name__ == "__main__":
    from agents.jd_parser import JDParserAgent
    
    # Mock JD for testing
    class MockJD(ParsedJD):
        pass
        
    sample_jd = MockJD(
        job_title="Backend Developer",
        required_skills=["Python"],
        min_experience_years=2.0,
        seniority="mid",
        role_type="full-time",
        location="Remote",
        remote_ok=True,
        key_responsibilities=["Coding"],
        summary="Test"
    )

    discovery = HNDiscoveryAgent()
    candidates, trace = discovery.run(sample_jd, max_candidates=5)
    for log in trace:
        print(log)