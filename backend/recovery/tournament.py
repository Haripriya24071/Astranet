"""ASTRANET Recovery — Counterfactual Recovery Tournament Engine.

Implements Master Blueprint v2.0 Section 4 (Signature Feature) & Section 6:
Counterfactual Mission Recovery Engine:
1. Diagnose and attribute the failure.
2. Generate multiple recovery strategies.
3. Clone current swarm state into parallel digital-twin futures.
4. Simulate candidate plans.
5. Inject plausible additional failures (N-1, N-2).
6. Score mission utility, safety, resource cost, and confidence.
7. Calculate resilience debt and future survivability.
8. Select the best plan.
9. Explain why it won and why alternatives lost.
10. Return the selected RecoveryPlan for simulation execution.
"""

from typing import List, Dict, Tuple, Optional
from backend.app.core.satellite import CubeSat
from backend.app.core.network import NetworkTopology
from backend.autonomy.contracts import DiagnosticReport, MissionPriority, MissionMode
from backend.recovery.contracts import (
    RecoveryCandidate,
    RecoveryDecision,
    RecoveryPlan,
)
from backend.recovery.generator import CandidatePlanGenerator
from backend.recovery.stress_test import SurvivabilityStressTester
from backend.recovery.scoring import MultiObjectiveScorer
from backend.recovery.explainer import DecisionExplainer


class RecoveryTournamentEngine:
    """Orchestrates the counterfactual recovery tournament across parallel digital-twin futures."""

    def __init__(self) -> None:
        self._decision_history: List[RecoveryDecision] = []

    @property
    def decision_history(self) -> List[RecoveryDecision]:
        return self._decision_history

    def run_tournament(
        self,
        target: CubeSat,
        diagnosis: DiagnosticReport,
        satellites: List[CubeSat],
        network: NetworkTopology,
        sim_time_sec: float,
        mission_state_before: str = "DEGRADED-A",
        priority: MissionPriority = MissionPriority.BALANCED,
    ) -> Tuple[RecoveryDecision, RecoveryPlan]:
        """Execute the counterfactual tournament and produce the winning RecoveryPlan."""
        # 1. Generate Multiple Candidate Futures
        candidates = CandidatePlanGenerator.generate_candidates(
            target=target,
            diagnosis=diagnosis,
            satellites=satellites,
            network=network,
        )

        # 2. Stress-Test Parallel Futures (N-1, N-2, Secondary Failure Risks, Resilience Debt)
        for cand in candidates:
            SurvivabilityStressTester.evaluate_candidate(
                candidate=cand,
                satellites=satellites,
                network=network,
            )

        # 3. Multi-Objective Scoring & Ranking
        ranked = MultiObjectiveScorer.rank_candidates(candidates, priority=priority)
        winner = ranked[0]

        # 4. Generate Machine-Readable Explanations
        rationale, rejections = DecisionExplainer.explain_tournament(
            winner=winner,
            ranked_candidates=ranked,
            diagnosis=diagnosis,
        )

        # 5. Determine Predicted Post-Recovery Mission State
        # If winner preserves >= 90% utility, swarm returns to NOMINAL or DEGRADED-A
        if winner.expected_mission_utility >= 90.0:
            predicted_after = "RECOVERED-OPTIMAL"
        else:
            predicted_after = "RECOVERED-DEGRADED"

        evidence_summaries = [e.description for e in diagnosis.evidence]

        decision = RecoveryDecision(
            selected_plan_id=winner.plan_id,
            target_satellite_id=target.id,
            timestamp_sec=sim_time_sec,
            triggering_anomaly=diagnosis.attributed_cause,
            ranking=[c.plan_id for c in ranked],
            candidates=ranked,
            evidence=evidence_summaries,
            rejected_plans_with_reasons=rejections,
            rationale=rationale,
            mission_state_before=mission_state_before,
            mission_state_after=predicted_after,
        )

        self._decision_history.append(decision)

        # 6. Formulate Actionable RecoveryPlan for Simulation Execution
        plan = RecoveryPlan(
            plan_id=winner.plan_id,
            target_satellite_id=target.id,
            actions=winner.actions,
            created_sim_time=sim_time_sec,
            rationale=rationale,
        )

        return decision, plan
