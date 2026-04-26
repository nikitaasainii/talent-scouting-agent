import os
import sys
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from schemas.output_schema import FinalShortlist, ScoredCandidate, InterestSignals, ConversationTurn

class ScorerAgent:
    def __init__(self):
        self.name = "ScorerAgent"
        self.match_weight = 0.6
        self.interest_weight = 0.4

    def run(self, outreach_results, *args, **kwargs):
        trace = []
        trace.append(f"[{self.name}] Finalizing scores for {len(outreach_results)} candidates.")

        jd_title = args[0] if len(args) > 0 else "Specialist Role"
        total_ev = args[1] if len(args) > 1 else len(outreach_results)
        old_trace = args[2] if len(args) > 2 else []

        sorted_results = sorted(
            outreach_results,
            key=lambda x: (
                x.get("match_score", 0) * self.match_weight +
                x.get("interest_score", 0) * self.interest_weight
            ),
            reverse=True
        )

        shortlisted = []
        for i, res in enumerate(sorted_results):
            match_score = float(res.get("match_score", 0))
            interest_score = float(res.get("interest_score", 0))
            combined = round(match_score * self.match_weight + interest_score * self.interest_weight, 1)

            # Profile URL — could be GitHub, LinkedIn search, or Wellfound
            raw_url = (
                res.get("github_url") or
                res.get("url") or
                res.get("profile_url") or
                "https://github.com"
            )

            # Build typed conversation
            raw_convo = res.get("conversation", [])
            conversation = []
            for turn in raw_convo:
                if isinstance(turn, dict):
                    conversation.append(ConversationTurn(
                        speaker=turn.get("speaker", "recruiter"),
                        message=turn.get("message", "")
                    ))
                else:
                    conversation.append(turn)

            # Build interest signals
            enthusiasm = res.get("enthusiasm_level", "medium")
            if isinstance(enthusiasm, str):
                enthusiasm = enthusiasm.lower()
            if enthusiasm not in ["low", "medium", "high"]:
                enthusiasm = "medium"

            signals = InterestSignals(
                open_to_move=res.get("open_to_move", True),
                enthusiasm_level=enthusiasm,
                salary_aligned=res.get("salary_aligned", True),
                key_quotes=res.get("key_quotes", ["Open to new opportunities"])
            )

            candidate = ScoredCandidate(
                rank=i + 1,
                candidate_id=res.get("candidate_id") or res.get("id") or f"cand_{i+1}",
                candidate_name=res.get("name", "Unknown"),
                github_url=raw_url,
                match_score=match_score,
                interest_score=interest_score,
                combined_score=combined,
                match_reasons=res.get("reasons", res.get("match_reasons", ["Strong technical profile"])),
                interest_reasons=res.get("interest_reasons", ["Positive engagement signals"]),
                interest_signals=signals,
                conversation=conversation
            )
            shortlisted.append(candidate)
            trace.append(f"[{self.name}] #{i+1} {candidate.candidate_name} — Match: {match_score} | Interest: {interest_score} | Combined: {combined}")

        if shortlisted:
            trace.append(f"[{self.name}] ✅ #1 candidate: {shortlisted[0].candidate_name} ({shortlisted[0].combined_score}/100)")
        else:
            trace.append(f"[{self.name}] ⚠ No candidates scored.")

        final_output = FinalShortlist(
            job_title=jd_title,
            total_candidates_evaluated=total_ev,
            shortlisted=shortlisted,
            agent_trace=old_trace + trace
        )
        return final_output, trace