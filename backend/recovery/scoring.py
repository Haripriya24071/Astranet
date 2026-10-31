"""ASTRANET Recovery — Multi-Objective Scoring & Candidate Ranking Engine.

Implements Master Blueprint v2.0 Section 3.5, 3.7 & Section 15.7:
Scores candidate recovery plans using:
- Mission coverage and utility retention
- Propellant / delta-V cost
- Energy cost
- Safety and risk
- Recovery confidence
- Secondary-failure risk
- Future survivability (N-1 / N-2)
- Resilience debt

Adapts dynamically to operator MissionPriority (Balanced, Network First, Fuel Saver, Coverage First).
"""

from typing import List
from backend.autonomy.contracts import MissionPriority
from backend.recovery.contracts import RecoveryCandidate


class MultiObjectiveScorer:
    """Calculates composite utility scores and ranks candidate recovery plans."""

    @classmethod
    def score_candidate(
        cls,
        candidate: RecoveryCandidate,
        priority: MissionPriority = MissionPriority.BALANCED,
    ) -> float:
        """Compute the weighted multi-objective score for a recovery candidate."""
        # 1. Base Utility Component (0 - 100)
        utility = candidate.expected_mission_utility

        # 2. Survivability Bonus: N-1 (up to +20) and N-2 (up to +10)
        survivability_bonus = (candidate.n1_survival * 20.0) + (candidate.n2_survival * 10.0)

        # 3. Penalties
        # Secondary failure risk penalty
        secondary_risk_penalty = candidate.predicted_secondary_risk * 20.0
        # Direct execution risk penalty
        execution_risk_penalty = candidate.risk * 15.0
        # Resilience debt penalty (0 - 100 scaled to 0 - 20)
        resilience_debt_penalty = (candidate.resilience_debt / 100.0) * 18.0

        # Propellant & Energy weights adjusted by operator priority
        if priority == MissionPriority.FUEL_SAVER:
            fuel_penalty = candidate.delta_v_cost_ms * 18.0
            energy_penalty = candidate.energy_cost_pct * 0.8
            resilience_debt_penalty *= 1.4
            utility_weight = 0.90
        elif priority == MissionPriority.NETWORK_FIRST:
            fuel_penalty = candidate.delta_v_cost_ms * 4.0
            energy_penalty = candidate.energy_cost_pct * 0.4
            utility_weight = 1.15
        elif priority == MissionPriority.COVERAGE_FIRST:
            fuel_penalty = candidate.delta_v_cost_ms * 6.0
            energy_penalty = candidate.energy_cost_pct * 0.5
            utility_weight = 1.25
        else:  # BALANCED
            fuel_penalty = candidate.delta_v_cost_ms * 8.0
            energy_penalty = candidate.energy_cost_pct * 0.6
            utility_weight = 1.0

        # Confidence multiplier
        confidence_mult = 0.70 + (candidate.recovery_confidence * 0.30)

        composite = (
            (utility * utility_weight)
            + survivability_bonus
            - fuel_penalty
            - energy_penalty
            - secondary_risk_penalty
            - execution_risk_penalty
            - resilience_debt_penalty
        ) * confidence_mult

        candidate.composite_score = max(0.0, min(100.0, composite))
        return candidate.composite_score

    @classmethod
    def rank_candidates(
        cls,
        candidates: List[RecoveryCandidate],
        priority: MissionPriority = MissionPriority.BALANCED,
    ) -> List[RecoveryCandidate]:
        """Score and sort all candidates in descending order of composite score."""
        for cand in candidates:
            cls.score_candidate(cand, priority)

        # Sort descending by composite score
        return sorted(candidates, key=lambda c: c.composite_score, reverse=True)
