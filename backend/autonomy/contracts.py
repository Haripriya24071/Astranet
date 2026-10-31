"""ASTRANET Autonomy & Resilience Engine — Shared Data Contracts.

Defines typed dataclasses and enums in strict accordance with the
ASTRANET Master Blueprint v2.0 (Sections 3, 7, 15, and 20).
"""

from enum import Enum
from typing import Dict, List, Any, Optional
from dataclasses import dataclass, field


class CapabilityType(str, Enum):
    """Core spacecraft functional capabilities."""
    SENSING = "sensing"
    RELAY = "relay"
    NAVIGATION = "navigation"
    COMPUTE = "compute"
    STORAGE = "storage"
    MANEUVERING = "maneuvering"


class CapabilityStatus(str, Enum):
    """Operational status of an individual capability."""
    OPERATIONAL = "OPERATIONAL"
    DEGRADED = "DEGRADED"
    LOST = "LOST"


class MissionMode(str, Enum):
    """Swarm-wide mission degradation modes per Master Blueprint Section 3.4."""
    NOMINAL = "NOMINAL"
    DEGRADED_A = "DEGRADED-A"
    DEGRADED_B = "DEGRADED-B"
    SURVIVAL = "SURVIVAL"
    MISSION_LOST = "MISSION-LOST"


class MissionObjective(str, Enum):
    """Core swarm mission objectives."""
    EARTH_OBSERVATION = "Earth Observation Coverage"
    ISL_RELAY = "Inter-Satellite Link Relay Throughput"
    DISTRIBUTED_COMPUTE = "Distributed Swarm Consensus & Compute"
    FORMATION_SAFETY = "Orbital Separation & Collision Avoidance"


class MissionPriority(str, Enum):
    """Operator mission prioritization strategies."""
    BALANCED = "Balanced"
    NETWORK_FIRST = "Network First"
    FUEL_SAVER = "Fuel Saver"
    COVERAGE_FIRST = "Coverage First"


@dataclass
class CapabilityReport:
    """Detailed capability evaluation for a single CubeSat."""
    satellite_id: str
    capabilities: Dict[CapabilityType, CapabilityStatus]
    functional_ratio: float  # Fraction of operational capabilities (0.0 - 1.0)
    impaired_capabilities: List[CapabilityType] = field(default_factory=list)
    preserved_capabilities: List[CapabilityType] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "satelliteId": self.satellite_id,
            "capabilities": {k.value: v.value for k, v in self.capabilities.items()},
            "functionalRatio": round(self.functional_ratio, 2),
            "impaired": [c.value for c in self.impaired_capabilities],
            "preserved": [c.value for c in self.preserved_capabilities],
        }


@dataclass
class DiagnosticEvidence:
    """Individual piece of observable telemetry evidence."""
    source: str
    metric: str
    observed_value: Any
    expected_value: Any
    severity: str  # "info", "warning", "critical"
    description: str


@dataclass
class DiagnosticReport:
    """Probabilistic failure attribution report for an anomalous spacecraft."""
    satellite_id: str
    timestamp_sec: float
    attributed_cause: str
    is_total_node_loss: bool
    confidence: float  # Confidence score (0.0 to 1.0)
    evidence: List[DiagnosticEvidence] = field(default_factory=list)
    affected_capabilities: List[CapabilityType] = field(default_factory=list)
    preserved_capabilities: List[CapabilityType] = field(default_factory=list)
    recommended_action_class: str = "PARTIAL_REALLOCATION"  # "PARTIAL_REALLOCATION", "TOPOLOGY_REROUTE", "FULL_FAILOVER", "SAFE_MODE"

    def to_dict(self) -> Dict[str, Any]:
        return {
            "satelliteId": self.satellite_id,
            "timestampSec": round(self.timestamp_sec, 2),
            "attributedCause": self.attributed_cause,
            "isTotalNodeLoss": self.is_total_node_loss,
            "confidence": round(self.confidence, 3),
            "evidence": [
                {
                    "source": e.source,
                    "metric": e.metric,
                    "observed": str(e.observed_value),
                    "expected": str(e.expected_value),
                    "severity": e.severity,
                    "description": e.description,
                }
                for e in self.evidence
            ],
            "affectedCapabilities": [c.value for c in self.affected_capabilities],
            "preservedCapabilities": [c.value for c in self.preserved_capabilities],
            "recommendedActionClass": self.recommended_action_class,
        }


@dataclass
class SwarmMissionReport:
    """Constellation-wide capability and mission retention report."""
    timestamp_sec: float
    mission_mode: MissionMode
    coverage_ratio: float  # Active Earth observation capacity (0.0 - 1.0)
    relay_ratio: float  # Active ISL relay capacity (0.0 - 1.0)
    compute_ratio: float  # Active compute capacity (0.0 - 1.0)
    maneuvering_ratio: float  # Active orbital maneuver capacity (0.0 - 1.0)
    coordinator_status: str  # "NOMINAL", "FAILOVER_REQUIRED", "UNRESOLVED"
    primary_objectives_met: bool
    mission_score: float  # Overall mission health (0.0 - 100.0)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "timestampSec": round(self.timestamp_sec, 2),
            "missionMode": self.mission_mode.value,
            "coverageRatio": round(self.coverage_ratio, 3),
            "relayRatio": round(self.relay_ratio, 3),
            "computeRatio": round(self.compute_ratio, 3),
            "maneuveringRatio": round(self.maneuvering_ratio, 3),
            "coordinatorStatus": self.coordinator_status,
            "primaryObjectivesMet": self.primary_objectives_met,
            "missionScore": round(self.mission_score, 1),
        }
