import os
import sys
import json
import time
import requests
from datetime import datetime
from dotenv import load_dotenv

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from utils.llm import call_llm, parse_llm_json
from utils.prompts import GITHUB_SEARCH_QUERY_PROMPT, CANDIDATE_ENRICHMENT_PROMPT
from schemas.candidate_schema import Candidate
from schemas.jd_schema import ParsedJD

load_dotenv()

GITHUB_TOKEN = os.getenv("GITHUB_TOKEN")
HEADERS = {
    "Authorization": f"Bearer {GITHUB_TOKEN}",
    "Accept": "application/vnd.github+json",
    "X-GitHub-Api-Version": "2022-11-28"
}

class GitHubDiscoveryAgent:
    def __init__(self):
        self.name = "GitHubDiscoveryAgent"
        self.base_url = "https://api.github.com"

    def _build_search_query(self, parsed_jd: ParsedJD) -> dict:
        jd_summary = f"""
        Role: {parsed_jd.job_title}
        Required skills: {', '.join(parsed_jd.required_skills)}
        Location: {parsed_jd.location}
        Seniority: {parsed_jd.seniority.value}
        """
        raw = call_llm(GITHUB_SEARCH_QUERY_PROMPT, jd_summary)
        try:
            return parse_llm_json(raw)
        except Exception:
            primary_skill = parsed_jd.required_skills[0] if parsed_jd.required_skills else "Python"
            return {"query": f"language:{primary_skill}", "language_filter": primary_skill, "location_hint": None}

    def _search_users(self, query_data: dict, max_results: int = 30) -> list:
        lang = query_data.get("language_filter", "Python") or "Python"
        loc = query_data.get("location_hint", "")

        # type:user is critical — filters out orgs, projects, communities
        queries_to_try = [
            f"language:{lang} location:\"{loc}\" type:user followers:>10" if loc else None,
            f"language:{lang} type:user is:hireable followers:>10",
            f"language:{lang} type:user followers:5..500",
            f"language:{lang} type:user repos:>5",
        ]
        queries_to_try = [q for q in queries_to_try if q]

        all_items = []
        seen_logins = set()

        for q in queries_to_try:
            if len(all_items) >= max_results:
                break

            print(f"  [{self.name}] Casting net: {q}")
            url = f"{self.base_url}/search/users"
            params = {"q": q, "per_page": 30, "sort": "followers", "order": "desc"}

            try:
                resp = requests.get(url, headers=HEADERS, params=params, timeout=10)
                if resp.status_code == 403:
                    print("  ⚠ Rate limit hit, moving to next query.")
                    time.sleep(5)
                    continue
                if resp.status_code != 200:
                    continue

                items = resp.json().get("items", [])

                for item in items:
                    login = item["login"]
                    # Only accept type:User — reject orgs that slip through
                    if item.get("type", "User") == "User" and login not in seen_logins:
                        all_items.append(item)
                        seen_logins.add(login)

                if all_items:
                    print(f"  ✓ {len(all_items)} real individual developers found so far.")
                    break  # Stop at first query that returns results

            except Exception as e:
                print(f"  ⚠ Search error: {e}")
                continue

        return all_items[:max_results]

    def _fetch_user_profile(self, username: str) -> dict:
        url = f"{self.base_url}/users/{username}"
        try:
            resp = requests.get(url, headers=HEADERS, timeout=10)
            if resp.status_code != 200:
                return {}
            profile = resp.json()
            # Final guard — reject org accounts
            if profile.get("type", "User") != "User":
                return {}
            return profile
        except:
            return {}

    def _fetch_top_repos(self, username: str, limit: int = 5) -> list:
        url = f"{self.base_url}/users/{username}/repos"
        params = {"per_page": limit, "sort": "stars", "direction": "desc"}
        try:
            resp = requests.get(url, headers=HEADERS, params=params, timeout=10)
            if resp.status_code != 200:
                return []
            return [
                {
                    "name": r["name"],
                    "language": r.get("language", ""),
                    "stars": r.get("stargazers_count", 0),
                    "description": r.get("description", "")
                }
                for r in resp.json() if not r.get("fork")
            ]
        except:
            return []

    def _extract_skills(self, profile: dict, repos: list) -> list:
        skills = {r["language"] for r in repos if r.get("language")}
        bio = (profile.get("bio") or "").lower()
        tech_keywords = [
            "python", "javascript", "typescript", "react", "node", "fastapi",
            "django", "docker", "kubernetes", "aws", "gcp", "azure", "rust",
            "go", "java", "kafka", "postgres", "redis"
        ]
        for kw in tech_keywords:
            if kw in bio:
                skills.add(kw.capitalize())
        return list(skills) if skills else ["Not specified"]

    def _enrich_candidate(self, profile: dict, repos: list) -> str:
        repo_summary = "\n".join([
            f"- {r['name']} ({r['language']}): {r['description']}"
            for r in repos
        ])
        raw_data = f"""
        Name: {profile.get('name', 'Unknown')}
        Bio: {profile.get('bio', 'None')}
        Location: {profile.get('location', 'Not specified')}
        Public Repos: {profile.get('public_repos', 0)}
        Followers: {profile.get('followers', 0)}
        Top Repos:
        {repo_summary if repo_summary else 'No public repos'}
        """
        return call_llm(CANDIDATE_ENRICHMENT_PROMPT, raw_data, temperature=0.4)

    def _build_candidate(self, profile: dict, repos: list, idx: int) -> Candidate:
        # Hard reject orgs
        if profile.get("type", "User") != "User":
            raise ValueError(f"Skipping org account: {profile.get('login')}")

        skills = self._extract_skills(profile, repos)
        enriched = self._enrich_candidate(profile, repos)
        created = profile.get("created_at", "2020-01-01T00:00:00Z")
        est_experience = float(max(1.0, datetime.now().year - int(created[:4])))

        return Candidate(
            id=f"gh_{profile.get('login', f'user_{idx}')}",
            name=profile.get("name") or profile.get("login", "Unknown"),
            github_url=profile.get("html_url", ""),
            current_role=profile.get("company") or "Software Engineer",
            total_experience_years=est_experience,
            skills=skills,
            location=profile.get("location") or "Not specified",
            open_to_remote=True,
            bio=profile.get("bio") or "",
            public_repos=profile.get("public_repos", 0),
            followers=profile.get("followers", 0),
            top_repositories=[r["name"] for r in repos],
            hireable=profile.get("hireable"),
            enriched_summary=enriched.strip()
        )

    def run(self, parsed_jd: ParsedJD, max_candidates: int = 20) -> tuple[list[Candidate], list[str]]:
        trace = [f"[{self.name}] Starting GitHub candidate discovery..."]
        query_data = self._build_search_query(parsed_jd)
        raw_users = self._search_users(query_data, max_results=max_candidates)
        trace.append(f"[{self.name}] Search returned {len(raw_users)} individual users")

        candidates = []
        for i, user in enumerate(raw_users):
            username = user["login"]
            profile = self._fetch_user_profile(username)
            if not profile:
                trace.append(f"[{self.name}]   ⚠ Skipped {username} — org or fetch failed")
                continue
            repos = self._fetch_top_repos(username)
            try:
                candidate = self._build_candidate(profile, repos, i)
                candidates.append(candidate)
                trace.append(f"[{self.name}]   ✓ {candidate.name} | {candidate.github_url}")
            except Exception as e:
                trace.append(f"[{self.name}]   ⚠ Skipped {username}: {str(e)}")
            time.sleep(1)

        trace.append(f"[{self.name}] ✅ GitHub discovery complete — {len(candidates)} real developers.")
        return candidates, trace