import os
import sys
import json
import requests
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from utils.llm import call_llm, parse_llm_json
from schemas.candidate_schema import Candidate
from schemas.jd_schema import ParsedJD

TAVILY_API_KEY = os.getenv("TAVILY_API_KEY")

class WebDiscoveryAgent:
    def __init__(self):
        self.name = "WebDiscoveryAgent"
        self.base_url = "https://api.tavily.com/search"

    def _generate_search_queries(self, parsed_jd: ParsedJD) -> list[str]:
        prompt = f"""
        Generate 3 high-precision X-Ray search strings for finding individual candidate profiles.
        Role: {parsed_jd.job_title}
        Skills: {', '.join(parsed_jd.required_skills[:3])}
        Location: {parsed_jd.location}

        Rules:
        - ONLY target individual profile URLs: site:linkedin.com/in/ or site:github.com/
        - Never target job listings, company pages, or directories
        - Include the job title and at least one skill in each query
        - Return ONLY a JSON list of 3 strings, no markdown
        Example: ["site:linkedin.com/in/ \\"Python Developer\\" \\"FastAPI\\" \\"Bangalore\\""]
        """
        raw = call_llm(
            system_prompt="You are an expert technical headhunter. Return only valid JSON arrays.",
            user_message=prompt
        )
        try:
            return parse_llm_json(raw)
        except:
            skill = parsed_jd.required_skills[0] if parsed_jd.required_skills else "Python"
            return [
                f'site:linkedin.com/in/ "{parsed_jd.job_title}" "{skill}"',
                f'site:github.com "{skill}" "{parsed_jd.job_title}"',
            ]

    def _search_web(self, query: str) -> list:
        if not TAVILY_API_KEY:
            print("⚠ TAVILY_API_KEY not found.")
            return []
        payload = {
            "api_key": TAVILY_API_KEY,
            "query": query,
            "search_depth": "advanced",
            "include_domains": ["linkedin.com", "github.com"],
            "max_results": 8
        }
        try:
            resp = requests.post(self.base_url, json=payload, timeout=15)
            return resp.json().get("results", [])
        except Exception as e:
            print(f"  ⚠ Tavily search failed: {e}")
            return []

    def _is_valid_profile(self, url: str) -> bool:
        invalid_patterns = [
            "/pub/dir/", "/jobs/", "/title/", "/company/",
            "/search", "login", "signup", "directory",
            "?trk=", "/feed", "/messaging", "/notifications"
        ]
        url_lower = url.lower()

        # Must be a specific individual profile path
        is_linkedin_profile = "linkedin.com/in/" in url_lower
        is_github_profile = (
            "github.com/" in url_lower
            and url_lower.count("/") <= 4  # github.com/username only, not deep paths
            and "github.com/topics/" not in url_lower
            and "github.com/orgs/" not in url_lower
            and "github.com/collections/" not in url_lower
        )

        has_garbage = any(p in url_lower for p in invalid_patterns)
        return (is_linkedin_profile or is_github_profile) and not has_garbage

    def _build_linkedin_search_url(self, name: str) -> str:
        """Build a LinkedIn people search URL since direct profile links redirect."""
        search_name = name.replace(" ", "%20")
        return f"https://www.linkedin.com/search/results/people/?keywords={search_name}"

    def _parse_web_result_to_candidate(self, result: dict) -> Candidate:
        prompt = f"""
        Extract candidate data from this search result.
        Title: {result['title']}
        Snippet: {result['content']}
        URL: {result['url']}

        Return ONLY valid JSON, no markdown:
        {{
            "name": "Full Name or Unknown Professional",
            "current_role": "Job Title",
            "skills": ["Skill1", "Skill2"],
            "location": "City, Country",
            "bio": "One sentence professional summary"
        }}
        """
        raw = call_llm(
            system_prompt="Extract candidate details accurately. Return only valid JSON.",
            user_message=prompt
        )
        data = parse_llm_json(raw)

        raw_url = result['url']
        is_linkedin = "linkedin.com/in/" in raw_url.lower()

        # For LinkedIn: store a working search URL instead of direct profile
        # (direct LinkedIn profile URLs always redirect to homepage for unauthenticated users)
        candidate_name = data.get("name", "Unknown Professional")
        if is_linkedin:
            profile_url = self._build_linkedin_search_url(candidate_name)
        else:
            profile_url = raw_url

        return Candidate(
            id=f"web_{abs(hash(raw_url))}",
            name=candidate_name,
            github_url=profile_url,  # holds LinkedIn search URL or GitHub URL
            current_role=data.get("current_role", "Specialist"),
            total_experience_years=5.0,
            skills=data.get("skills", []),
            location=data.get("location", "Global"),
            open_to_remote=True,
            bio=data.get("bio", result['content'][:200]),
            public_repos=0,
            followers=0,
            top_repositories=[],
            hireable=True,
            enriched_summary=f"Source: {'LinkedIn' if is_linkedin else 'GitHub'} | {raw_url}"
        )

    def run(self, parsed_jd: ParsedJD, max_candidates: int = 10) -> tuple[list[Candidate], list[str]]:
        trace = [f"[{self.name}] Initiating high-precision profile discovery..."]

        if not TAVILY_API_KEY:
            trace.append(f"[{self.name}] ⚠ No TAVILY_API_KEY — skipping web discovery.")
            return [], trace

        queries = self._generate_search_queries(parsed_jd)
        candidates = []
        seen_urls = set()

        for q in queries:
            if len(candidates) >= max_candidates:
                break
            trace.append(f"[{self.name}] Scouting: {q}")
            results = self._search_web(q)

            for res in results:
                url = res['url']
                if url not in seen_urls and self._is_valid_profile(url):
                    try:
                        candidate = self._parse_web_result_to_candidate(res)
                        candidates.append(candidate)
                        seen_urls.add(url)
                        trace.append(f"[{self.name}]   ✓ {candidate.name} — {candidate.github_url}")
                    except Exception as e:
                        trace.append(f"[{self.name}]   ⚠ Parse failed for {url}: {e}")
                if len(candidates) >= max_candidates:
                    break

        trace.append(f"[{self.name}] ✅ Verified {len(candidates)} individual profiles.")
        return candidates, trace