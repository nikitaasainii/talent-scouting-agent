import os
import sys
import json
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import chromadb
from chromadb.utils import embedding_functions

from utils.llm import call_llm, parse_llm_json
from utils.prompts import MATCH_SCORER_PROMPT
from schemas.jd_schema import ParsedJD
from schemas.candidate_schema import Candidate

class CandidateMatcherAgent:
    def __init__(self):
        self.name = "CandidateMatcherAgent"
        db_path = os.path.join(os.path.dirname(__file__), "..", "data", "chroma_db")
        self.db_path = db_path
        self.embedding_fn = embedding_functions.SentenceTransformerEmbeddingFunction(
            model_name="all-MiniLM-L6-v2"
        )
        self._load_collection()

    def _load_collection(self):
        client = chromadb.PersistentClient(path=self.db_path)
        try:
            self.collection = client.get_collection(
                name="candidates",
                embedding_function=self.embedding_fn
            )
        
        except Exception:
            # Collection doesn't exist yet — create empty one
            self.collection = client.create_collection(
                name="candidates",
                embedding_function=self.embedding_fn,
                metadata={"hnsw:space": "cosine"}
            )

    # ------------------------------------------------------------------ #
    #  1. Semantic search — find top N candidates from ChromaDB           #
    # ------------------------------------------------------------------ #
    def _semantic_search(self, parsed_jd: ParsedJD, top_n: int = 10) -> list:
        # INDUSTRY GRADE: Check if database is empty before querying
        count = self.collection.count()
        if count == 0:
            return []

        # Build a rich query from the JD
        query = f"""
        {parsed_jd.job_title}
        Skills: {', '.join(parsed_jd.required_skills)}
        Experience: {parsed_jd.min_experience_years}+ years
        {parsed_jd.summary}
        """.strip()

        # FIXED: Ensure n_results is never 0 or greater than total count
        results = self.collection.query(
            query_texts=[query],
            n_results=min(top_n, count)
        )

        candidates = []
        for i, metadata in enumerate(results["metadatas"][0]):
            candidates.append({
                "candidate_id": metadata["candidate_id"],
                "name": metadata["name"],
                "github_url": metadata.get("github_url", ""),
                "skills": metadata.get("skills", ""),
                "experience_years": metadata.get("experience_years", 0),
                "location": metadata.get("location", ""),
                "document": results["documents"][0][i],
                "similarity_score": 1 - results["distances"][0][i]  # cosine → similarity
            })

        return candidates

    # ------------------------------------------------------------------ #
    #  2. LLM scoring — detailed match analysis per candidate             #
    # ------------------------------------------------------------------ #
    def _score_candidate(self, candidate: dict, parsed_jd: ParsedJD) -> dict:
        jd_context = f"""
        Job: {parsed_jd.job_title}
        Required Skills: {', '.join(parsed_jd.required_skills)}
        Nice to Have: {', '.join(parsed_jd.nice_to_have_skills)}
        Min Experience: {parsed_jd.min_experience_years} years
        Seniority: {parsed_jd.seniority.value}
        Location: {parsed_jd.location}
        Remote OK: {parsed_jd.remote_ok}
        Responsibilities: {', '.join(parsed_jd.key_responsibilities)}
        """

        candidate_context = f"""
        Name: {candidate['name']}
        Skills: {candidate['skills']}
        Experience: {candidate['experience_years']} years
        Location: {candidate['location']}
        Profile: {candidate['document']}
        """

        raw_response = call_llm(
            MATCH_SCORER_PROMPT,
            f"JD:\n{jd_context}\n\nCandidate:\n{candidate_context}"
        )

        try:
            result = parse_llm_json(raw_response)
        except Exception as e:
            print(f"  ⚠ Failed to parse match score for {candidate['name']}: {e}")
            result = {
                "match_score": 50,
                "reasons": ["Error extracting score from LLM. Assuming average fit."],
                "missing_skills": [],
                "strengths": []
            }

        result["candidate_id"] = candidate["candidate_id"]
        result["name"] = candidate["name"]
        result["github_url"] = candidate["github_url"]
        result["similarity_score"] = candidate["similarity_score"]
        return result

    # ------------------------------------------------------------------ #
    #  Main run                                                            #
    # ------------------------------------------------------------------ #
    def run(self, parsed_jd: ParsedJD, top_n: int = 10) -> tuple[list, list[str]]:
        trace = []
        trace.append(f"[{self.name}] Starting semantic candidate matching...")
        
        db_count = self.collection.count()
        trace.append(f"[{self.name}] Vector DB has {db_count} candidates")

        # INDUSTRY GRADE: Graceful exit if no candidates were discovered
        if db_count == 0:
            trace.append(f"[{self.name}] ⚠ No candidates found in database. Skipping scoring.")
            return [], trace

        # Step 1: Semantic search
        candidates = self._semantic_search(parsed_jd, top_n=top_n)
        trace.append(f"[{self.name}] Top {len(candidates)} candidates retrieved from ChromaDB")

        # Step 2: LLM match scoring
        scored = []
        for i, candidate in enumerate(candidates):
            trace.append(f"[{self.name}] Scoring {i+1}/{len(candidates)}: {candidate['name']}")
            try:
                score = self._score_candidate(candidate, parsed_jd)
                scored.append(score)
                trace.append(f"[{self.name}]   ✓ Match Score: {score.get('match_score', 0)}/100")
            except Exception as e:
                trace.append(f"[{self.name}]   ⚠ Skipped {candidate['name']}: {e}")

        # Sort by match score
        scored.sort(key=lambda x: x.get("match_score", 0), reverse=True)
        
        if scored:
            trace.append(f"[{self.name}] ✅ Matching complete — top score: {scored[0]['match_score']}")
        else:
            trace.append(f"[{self.name}] ⚠ Matching complete — no candidates scored successfully.")

        return scored, trace