"""ASTRANET Recovery — Secondary-Failure Forecasting, Resilience Debt & N-1/N-2 Stress Testing.

Implements Master Blueprint v2.0 Section 3.7, 3.8, 3.9 & Section 15.6:
- Secondary Failure Forecasting: Predicts whether recovery overloads surviving spacecraft.
- Resilience Debt: Quantifies future fault-tolerance consumed by recovery.
- N-1 / N-2 Survivability Testing: Evaluates swarm survival under 1 or 2 subsequent failures.
"""

from typing import List, Dict, Set
from backend.app.core.satellite import CubeSat, SatelliteState, SatelliteRole
from backend.app.core.network import NetworkTopology
from backend.recovery.contracts import RecoveryCandidate, ActionType


class SurvivabilityStressTester:
    """Stress-tests recovery candidates against secondary risks, resilience debt, and N-1/N-2 failures."""

    @classmethod
    def evaluate_candidate(
        cls,
        candidate: RecoveryCandidate,
        satellites: List[CubeSat],
        network: NetworkTopology,
    ) -> RecoveryCandidate:
        """Run stress tests on a candidate recovery plan and update survivability metrics."""
        operational_count = sum(1 for s in satellites if s.state not in (SatelliteState.FAILED, SatelliteState.ISOLATED))
        sat_map = {s.id: s for s in satellites}

        # 1. Forecast Secondary Overload Risks
        recipient_id: str = ""
        for action in candidate.actions:
            if action.action_type == ActionType.ROLE_MIGRATION and action.parameters.get("previousHolder"):
                recipient_id = action.target_satellite_id
                break

        secondary_risk = 0.08
        resilience_debt = 10.0

        if recipient_id and recipient_id in sat_map:
            recipient = sat_map[recipient_id]
            # Check if recipient satellite has high compute or low battery
            if recipient.compute > 45.0:
                secondary_risk += 0.12  # CPU congestion risk
            if recipient.battery < 55.0:
                secondary_risk += 0.15  # Battery strain risk
            if recipient.propellant < 30.0:
                secondary_risk += 0.10  # Delta-V scarcity risk

            # Resilience debt increases as we consume a healthy observer
            resilience_debt += 15.0

        if candidate.delta_v_cost_ms > 0.0:
            # Propellant burn directly adds to resilience debt
            resilience_debt += candidate.delta_v_cost_ms * 12.0
            secondary_risk += 0.10

        # 2. N-1 Survivability Simulation
        # Probability of swarm retaining mission viability if 1 more node fails
        redundancy_margin = max(0, operational_count - 1)
        if redundancy_margin >= 8:
            n1_base = 0.92
        elif redundancy_margin >= 6:
            n1_base = 0.80
        else:
            n1_base = 0.55

        # Degrade N-1 by secondary risk and resilience debt
        n1_survival = max(0.20, min(0.99, n1_base - (secondary_risk * 0.4) - (resilience_debt / 250.0)))

        # 3. N-2 Survivability Simulation
        # Probability of swarm retaining mission viability if 2 additional nodes fail
        if redundancy_margin >= 9:
            n2_base = 0.82
        elif redundancy_margin >= 7:
            n2_base = 0.65
        else:
            n2_base = 0.35

        n2_survival = max(0.10, min(0.95, n2_base - (secondary_risk * 0.6) - (resilience_debt / 180.0)))

        # Update candidate metrics
        candidate.predicted_secondary_risk = max(0.02, min(0.95, secondary_risk))
        candidate.resilience_debt = max(5.0, min(100.0, resilience_debt))
        candidate.n1_survival = round(n1_survival, 3)
        candidate.n2_survival = round(n2_survival, 3)

        return candidate
