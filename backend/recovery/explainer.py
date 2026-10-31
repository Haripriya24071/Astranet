"""ASTRANET Recovery — Explainable Autonomy & Decision Provenance Engine.

Implements Master Blueprint v2.0 Section 3.15, 3.16, 3.17 & Section 15.8:
- Explainability / Provenance: Records why a plan won, why alternatives lost,
  what evidence was used, and exposes machine-readable explanation payloads.
"""

from typing import List, Dict, Tuple
from backend.recovery.contracts import RecoveryCandidate, RecoveryDecision
from backend.autonomy.contracts import DiagnosticReport


class DecisionExplainer:
    """Generates structured, machine-readable explanations for autonomous recovery selections."""

    @classmethod
    def explain_tournament(
        cls,
        winner: RecoveryCandidate,
        ranked_candidates: List[RecoveryCandidate],
        diagnosis: DiagnosticReport,
    ) -> Tuple[str, Dict[str, str]]:
        """Formulate rationale for winner and specific rejection explanations for all competitors.

        Returns:
            Tuple of (winner_rationale: str, rejected_plans_with_reasons: Dict[str, str]).
        """
        winner_rationale = (
            f"Selected '{winner.name}' ({winner.plan_id}): Achieved highest composite utility "
            f"({winner.composite_score:.1f}/100) by preserving {winner.expected_mission_utility:.1f}% mission yield "
            f"while maintaining strong future fault tolerance (N-1 survival {winner.n1_survival * 100:.1f}%, "
            f"resilience debt {winner.resilience_debt:.1f})."
        )

        rejections: Dict[str, str] = {}
        for cand in ranked_candidates:
            if cand.plan_id == winner.plan_id:
                continue

            reasons: List[str] = []
            if cand.composite_score < winner.composite_score:
                reasons.append(f"lower composite utility ({cand.composite_score:.1f} vs {winner.composite_score:.1f})")
            if cand.resilience_debt > winner.resilience_debt:
                reasons.append(f"excessive resilience debt ({cand.resilience_debt:.1f} vs {winner.resilience_debt:.1f})")
            if cand.n1_survival < winner.n1_survival:
                reasons.append(f"reduced N-1 survivability ({cand.n1_survival * 100:.1f}%)")
            if cand.delta_v_cost_ms > winner.delta_v_cost_ms:
                reasons.append(f"consumes {cand.delta_v_cost_ms:.2f} m/s delta-V reserve")
            if cand.predicted_secondary_risk > winner.predicted_secondary_risk:
                reasons.append(f"higher secondary failure risk ({cand.predicted_secondary_risk * 100:.1f}%)")

            rejection_text = f"Rejected due to {'; '.join(reasons)}." if reasons else "Rejected due to lower multi-objective rank."
            rejections[cand.plan_id] = rejection_text

        return winner_rationale, rejections
