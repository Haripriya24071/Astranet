"""ASTRANET Autonomy & Resilience Engine — Phases 3 to 5 Test Suite.

Validates Zahid's deliverables per Master Blueprint v2.0:
1. Candidate Recovery Generator (portfolio of >= 3 distinct strategies).
2. Counterfactual Recovery Tournament across cloned futures.
3. Secondary-Failure Forecasting, Resilience Debt, and N-1/N-2 Survivability Testing.
4. Multi-Objective Utility Scoring under dynamic operator MissionPriorities.
5. Explainable Autonomy & Machine-Readable Provenance.
6. Closed-Loop Execution and Verification on Constellation State.
"""

import unittest
from backend.app.core.satellite import (
    CubeSat,
    SatelliteState,
    SatelliteRole,
    SubsystemStatus,
)
from backend.app.core.orbit import KeplerianOrbit
from backend.app.core.network import NetworkTopology
from backend.app.core.faults import FailureType, FailureSeverity
from backend.app.core.swarm import SwarmOrchestrator
from backend.autonomy.contracts import (
    MissionPriority,
    CapabilityType,
    CapabilityStatus,
)
from backend.autonomy.diagnosis import FaultAttributor
from backend.recovery.contracts import (
    RecoveryCandidate,
    RecoveryDecision,
    RecoveryPlan,
    ActionType,
)
from backend.recovery.generator import CandidatePlanGenerator
from backend.recovery.stress_test import SurvivabilityStressTester
from backend.recovery.scoring import MultiObjectiveScorer
from backend.recovery.explainer import DecisionExplainer
from backend.recovery.tournament import RecoveryTournamentEngine
from backend.recovery.orchestration import RecoveryPlanExecutor


class TestRecoveryCandidateGenerator(unittest.TestCase):
    """Unit tests for candidate recovery generation."""

    def setUp(self) -> None:
        self.orchestrator = SwarmOrchestrator()
        self.sat_04 = self.orchestrator.get_satellite("SAT-04")
        self.attributor = FaultAttributor()

    def test_generates_minimum_three_distinct_candidates(self) -> None:
        self.sat_04.subsystems.propulsion = SubsystemStatus.FAILED
        diagnosis = self.attributor.diagnose_satellite(
            self.sat_04, self.orchestrator.network, sim_time_sec=10.0
        )

        candidates = CandidatePlanGenerator.generate_candidates(
            target=self.sat_04,
            diagnosis=diagnosis,
            satellites=self.orchestrator.satellites,
            network=self.orchestrator.network,
        )

        self.assertGreaterEqual(len(candidates), 3)
        plan_ids = {c.plan_id for c in candidates}
        self.assertIn("PLAN-A-ROLE-MIGRATION", plan_ids)
        self.assertIn("PLAN-B-TOPOLOGY-REROUTE", plan_ids)
        self.assertIn("PLAN-C-SAFE-THROTTLE", plan_ids)


class TestStressTestingAndScoring(unittest.TestCase):
    """Unit tests for stress testing, resilience debt, and priority-aware scoring."""

    def setUp(self) -> None:
        self.orchestrator = SwarmOrchestrator()
        self.sat_02 = self.orchestrator.get_satellite("SAT-02")
        self.attributor = FaultAttributor()

    def test_stress_test_computes_survivability_and_debt(self) -> None:
        diagnosis = self.attributor.diagnose_satellite(
            self.sat_02, self.orchestrator.network, sim_time_sec=10.0
        )
        candidates = CandidatePlanGenerator.generate_candidates(
            target=self.sat_02,
            diagnosis=diagnosis,
            satellites=self.orchestrator.satellites,
            network=self.orchestrator.network,
        )

        for cand in candidates:
            tested = SurvivabilityStressTester.evaluate_candidate(
                cand, self.orchestrator.satellites, self.orchestrator.network
            )
            self.assertGreaterEqual(tested.n1_survival, 0.0)
            self.assertLessEqual(tested.n1_survival, 1.0)
            self.assertGreaterEqual(tested.n2_survival, 0.0)
            self.assertLessEqual(tested.n2_survival, 1.0)
            self.assertGreater(tested.resilience_debt, 0.0)

    def test_fuel_saver_priority_penalizes_delta_v(self) -> None:
        # Create two candidates: one with zero delta-V, one with maneuver
        plan_zero_fuel = RecoveryCandidate(
            plan_id="PLAN-ZERO-FUEL",
            name="Zero Fuel Plan",
            actions=[],
            expected_mission_utility=85.0,
            delta_v_cost_ms=0.0,
            energy_cost_pct=5.0,
            risk=0.1,
            recovery_confidence=0.9,
            predicted_secondary_risk=0.1,
            resilience_debt=10.0,
            n1_survival=0.85,
            n2_survival=0.70,
        )
        plan_high_fuel = RecoveryCandidate(
            plan_id="PLAN-HIGH-FUEL",
            name="High Fuel Plan",
            actions=[],
            expected_mission_utility=90.0,
            delta_v_cost_ms=2.5,  # 2.5 m/s burn
            energy_cost_pct=10.0,
            risk=0.2,
            recovery_confidence=0.9,
            predicted_secondary_risk=0.2,
            resilience_debt=40.0,
            n1_survival=0.85,
            n2_survival=0.70,
        )

        ranked = MultiObjectiveScorer.rank_candidates(
            [plan_high_fuel, plan_zero_fuel], priority=MissionPriority.FUEL_SAVER
        )

        # Under Fuel Saver, the zero fuel plan must beat the high fuel plan
        self.assertEqual(ranked[0].plan_id, "PLAN-ZERO-FUEL")


class TestCounterfactualTournamentAndExecution(unittest.TestCase):
    """Unit tests for the end-to-end tournament, explainability, and simulation execution."""

    def setUp(self) -> None:
        self.orchestrator = SwarmOrchestrator()
        self.tournament = RecoveryTournamentEngine()
        self.attributor = FaultAttributor()

    def test_tournament_produces_decision_and_executable_plan(self) -> None:
        # Inject propulsion failure on SAT-04
        sat_04 = self.orchestrator.get_satellite("SAT-04")
        self.orchestrator.inject_fault(
            target_satellite_id="SAT-04",
            failure_type=FailureType.PROPULSION_FAILURE,
            severity=FailureSeverity.CRITICAL,
        )

        diagnosis = self.attributor.diagnose_satellite(
            sat_04, self.orchestrator.network, sim_time_sec=15.0
        )

        decision, plan = self.tournament.run_tournament(
            target=sat_04,
            diagnosis=diagnosis,
            satellites=self.orchestrator.satellites,
            network=self.orchestrator.network,
            sim_time_sec=15.0,
            priority=MissionPriority.BALANCED,
        )

        # Validate Decision
        self.assertIsNotNone(decision.selected_plan_id)
        self.assertEqual(len(decision.ranking), len(decision.candidates))
        self.assertEqual(decision.ranking[0], decision.selected_plan_id)
        self.assertIn("Selected", decision.rationale)
        self.assertGreater(len(decision.rejected_plans_with_reasons), 0)

        # Validate Plan
        self.assertEqual(plan.plan_id, decision.selected_plan_id)
        self.assertEqual(plan.target_satellite_id, "SAT-04")
        self.assertGreater(len(plan.actions), 0)

    def test_closed_loop_plan_execution_updates_swarm(self) -> None:
        # Simulate coordinator failure on SAT-07
        sat_07 = self.orchestrator.get_satellite("SAT-07")
        self.orchestrator.inject_fault(
            target_satellite_id="SAT-07",
            failure_type=FailureType.NODE_LOSS,
            severity=FailureSeverity.CRITICAL,
        )
        diagnosis = self.attributor.diagnose_satellite(
            sat_07, self.orchestrator.network, sim_time_sec=20.0
        )

        decision, plan = self.tournament.run_tournament(
            target=sat_07,
            diagnosis=diagnosis,
            satellites=self.orchestrator.satellites,
            network=self.orchestrator.network,
            sim_time_sec=20.0,
        )

        success, msg, metrics = RecoveryPlanExecutor.execute_plan(
            plan=plan,
            satellites=self.orchestrator.satellites,
            network=self.orchestrator.network,
        )

        self.assertTrue(success)
        self.assertIn(plan.plan_id, msg)
        self.assertGreater(metrics["actionsCount"], 0)


if __name__ == "__main__":
    unittest.main()
