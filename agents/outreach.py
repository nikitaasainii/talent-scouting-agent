import os
import sys
import json
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from utils.llm import call_llm, parse_llm_json  # <-- Imported parse_llm_json
from utils.prompts import OUTREACH_PROMPT, INTEREST_SCORER_PROMPT
from schemas.jd_schema import ParsedJD

class OutreachAgent:
    def __init__(self):
        self.name = "OutreachAgent"

    # ------------------------------------------------------------------ #
    #  1. Simulate a 4-turn conversation                                  #
    # ------------------------------------------------------------------ #
    def _simulate_conversation(self, candidate: dict, parsed_jd: ParsedJD) -> list:
        context = f"""
        Job Role: {parsed_jd.job_title}
        Company Location: {parsed_jd.location}
        Remote OK: {parsed_jd.remote_ok}
        Required Skills: {', '.join(parsed_jd.required_skills)}

        Candidate Name: {candidate.get('name', 'Unknown')}
        Candidate Skills: {candidate.get('skills', 'Not specified')}
        Candidate Location: {candidate.get('location', 'Not specified')}
        Candidate Experience: {candidate.get('experience_years', candidate.get('total_experience_years', 'Unknown'))} years
        Candidate Profile: {candidate.get('document', candidate.get('enriched_summary', ''))[:300]}
        """

        raw_response = call_llm(
            OUTREACH_PROMPT,
            f"Simulate a recruiter-candidate conversation:\n\n{context}",
            temperature=0.7     # higher temp = more natural conversation
        )

        try:
            data = parse_llm_json(raw_response)
            return data.get("conversation", [])
        except Exception as e:
            print(f"  ⚠ Failed to parse conversation JSON for {candidate.get('name')}: {e}")
            # Safe fallback conversation
            return [
                {"speaker": "recruiter", "message": f"Hi {candidate.get('name', 'there')}, are you open to new opportunities?"},
                {"speaker": "candidate", "message": "Hi! Yes, I might be open depending on the role."},
                {"speaker": "recruiter", "message": f"Great, we are looking for a {parsed_jd.job_title}. Would you like to chat?"},
                {"speaker": "candidate", "message": "Sure, I'd be happy to learn more."}
            ]

    # ------------------------------------------------------------------ #
    #  2. Score interest from conversation                                #
    # ------------------------------------------------------------------ #
    def _score_interest(self, conversation: list, candidate: dict, job_title: str = "the role") -> dict:
        transcript = "\n".join([
            f"{turn.get('speaker', 'UNKNOWN').upper()}: {turn.get('message', '')}"
            for turn in conversation
        ])

        context = f"""
        Candidate: {candidate.get('name', 'Unknown')}
        Role Applied For: {job_title}

        Conversation Transcript:
        {transcript}
        """

        raw_response = call_llm(INTEREST_SCORER_PROMPT, context)
        
        try:
            return parse_llm_json(raw_response)
        except Exception as e:
            print(f"  ⚠ Failed to parse interest score JSON for {candidate.get('name')}: {e}")
            # Neutral fallback score
            return {
                "interest_score": 50,
                "enthusiasm_level": "medium",
                "open_to_move": True,
                "salary_aligned": True,
                "key_quotes": ["Sure, I'd be happy to learn more."],
                "reasons": ["Error extracting score from LLM. Assigned default neutral interest."]
            }

    # ------------------------------------------------------------------ #
    #  Main run                                                            #
    # ------------------------------------------------------------------ #
    def run(self, matched_candidates: list, parsed_jd: ParsedJD) -> tuple[list, list[str]]:
        trace = []
        trace.append(f"[{self.name}] Starting outreach simulation for {len(matched_candidates)} candidates...")

        results = []
        for i, candidate in enumerate(matched_candidates):
            trace.append(f"[{self.name}] Outreach {i+1}/{len(matched_candidates)}: {candidate['name']}")

            try:
                # Simulate conversation
                conversation = self._simulate_conversation(candidate, parsed_jd)
                trace.append(f"[{self.name}]   ✓ Conversation simulated ({len(conversation)} turns)")

                # Score interest
                interest = self._score_interest(conversation, candidate, parsed_jd.job_title)
                trace.append(f"[{self.name}]   ✓ Interest Score: {interest.get('interest_score', 0)}/100 | Enthusiasm: {interest.get('enthusiasm_level', 'unknown')}")

                results.append({
                    **candidate,
                    "conversation": conversation,
                    "interest_score": interest.get("interest_score", 50),
                    "enthusiasm_level": interest.get("enthusiasm_level", "medium"),
                    "open_to_move": interest.get("open_to_move", True),
                    "salary_aligned": interest.get("salary_aligned", True),
                    "key_quotes": interest.get("key_quotes", []),
                    "interest_reasons": interest.get("reasons", [])
                })

            except Exception as e:
                import traceback
                trace.append(f"[{self.name}]   ⚠ Skipped {candidate['name']}: {e}")
                print(f"OUTREACH ERROR for {candidate['name']}: {traceback.format_exc()}")

        trace.append(f"[{self.name}] ✅ Outreach complete — {len(results)} candidates processed")
        return results, trace