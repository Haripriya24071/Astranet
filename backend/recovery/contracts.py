"""ASTRANET Recovery & Decision Engine — Data Contracts.

Defines typed dataclasses and structures for candidate plans, counterfactual
tournaments, stress testing, and machine-readable decision provenance
per Master Blueprint v2.0 (Sections 4, 6, 7, 8, 9, 10, 20).
"""

from typing import List, Dict, Any, Optional
from dataclasses import dataclass, field
from enum import Enum


class ActionType(str, Enum):
    """Types of recovery actions executable by the simulation layer."""
    ROLE_MIGRATION = "ROLE_MIGRATION"
    TOPOLOGY_REROUTE = "TOPOLOGY_REROUTE"
    POWER_THROTTLE = "POWER_THROTTLE"
    ISOLATE_NODE = "ISOLATE_NODE"
    ATTITUDE_SLEW = "ATTITUDE_SLEW"
    FORMATION_TRIM = "FORMATION_TRIM"
    SUBSYSTEM_RESET = "SUBSYSTEM_RESET"


@dataclass
class RecoveryAction:
    """Individual atomic recovery instruction."""
    action_type: ActionType
    target_satellite_id: str
    parameters: Dict[str, Any] = field(default_factory=dict)
    description: str = ""

    def to_dict(self) -> Dict[str, Any]:
        return {
            "actionType": self.action_type.value,
            "targetSatelliteId": self.target_satellite_id,
            "parameters": self.parameters,
            "description": self.description,
        }


@dataclass
class RecoveryCandidate:
    """Candidate recovery future evaluated during the counterfactual tournament."""
    plan_id: str
    name: str
    actions: List[RecoveryAction]
    expected_mission_utility: float  # (0.0 to 100.0)
    delta_v_cost_ms: float  # delta-V in m/s (or % propellant)
    energy_cost_pct: float  # Estimated battery draw increase (%)
    risk: float  # (0.0 to 1.0)
    recovery_confidence: float  # (0.0 to 1.0)
    predicted_secondary_risk: float  # (0.0 to 1.0) downstream failure probability
    resilience_debt: float  # (0.0 to 100.0) redundancy and buffer consumed
    n1_survival: float  # (0.0 to 1.0) survives 1 additional failure
    n2_survival: float  # (0.0 to 1.0) survives 2 additional failures
    composite_score: float = 0.0  # Multi-objective utility score

    def to_dict(self) -> Dict[str, Any]:
        return {
            "planId": self.plan_id,
            "name": self.name,
            "actions": [a.to_dict() for a in self.actions],
            "expectedMissionUtility": round(self.expected_mission_utility, 1),
            "deltaVCostMs": round(self.delta_v_cost_ms, 2),
            "energyCostPct": round(self.energy_cost_pct, 1),
            "risk": round(self.risk, 3),
            "recoveryConfidence": round(self.recovery_confidence, 3),
            "predictedSecondaryRisk": round(self.predicted_secondary_risk, 3),
            "resilienceDebt": round(self.resilience_debt, 1),
            "n1Survival": round(self.n1_survival, 3),
            "n2Survival": round(self.n2_survival, 3),
            "compositeScore": round(self.composite_score, 2),
        }


@dataclass
class RecoveryPlan:
    """Concrete executable plan returned to the simulation layer."""
    plan_id: str
    target_satellite_id: str
    actions: List[RecoveryAction]
    created_sim_time: float
    rationale: str

    def to_dict(self) -> Dict[str, Any]:
        return {
            "planId": self.plan_id,
            "targetSatelliteId": self.target_satellite_id,
            "actions": [a.to_dict() for a in self.actions],
            "createdSimTime": self.created_sim_time,
            "rationale": self.rationale,
        }


@dataclass
class RecoveryDecision:
    """Full decision provenance record from the counterfactual tournament."""
    selected_plan_id: str
    target_satellite_id: str
    timestamp_sec: float
    triggering_anomaly: str
    ranking: List[str]  # Ordered plan IDs (highest to lowest)
    candidates: List[RecoveryCandidate]
    evidence: List[str]
    rejected_plans_with_reasons: Dict[str, str]
    rationale: str
    mission_state_before: str
    mission_state_after: str

    def to_dict(self) -> Dict[str, Any]:
        return {
            "selectedPlanId": self.selected_plan_id,
            "targetSatelliteId": self.target_satellite_id,
            "timestampSec": round(self.timestamp_sec, 2),
            "triggeringAnomaly": self.triggering_anomaly,
            "ranking": self.ranking,
            "candidates": [c.to_dict() for c in self.candidates],
            "evidence": self.evidence,
            "rejectedPlansWithReasons": self.rejected_plans_with_reasons,
            "rationale": self.rationale,
            "missionStateBefore": self.mission_state_before,
            "missionStateAfter": self.mission_state_after,
        }
