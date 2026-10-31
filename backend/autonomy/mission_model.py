"""ASTRANET Autonomy — Swarm Mission Model & Mission Degradation Modes.

Implements Master Blueprint v2.0 Section 3.4 & Section 15.4:
Mission Degradation Modes:
Explicitly model NOMINAL, DEGRADED-A, DEGRADED-B, SURVIVAL, and MISSION-LOST states.
ASTRANET preserves the highest-value objectives under failure rather than
pretending full capability can always be restored.
"""

from typing import List, Dict, Any, Optional
from backend.app.core.satellite import CubeSat, SatelliteState, SatelliteRole
from backend.app.core.network import NetworkTopology
from backend.autonomy.contracts import (
    MissionMode,
    MissionObjective,
    MissionPriority,
    SwarmMissionReport,
    CapabilityType,
    CapabilityStatus,
)
from backend.autonomy.capability import CapabilityGraph


class SwarmMissionModel:
    """Evaluates constellation-wide mission performance and determines degradation modes."""

    # Threshold constants for mission mode transitions
    COVERAGE_NOMINAL_MIN: float = 0.90      # 90%+ coverage needed for NOMINAL
    COVERAGE_DEGRADED_A_MIN: float = 0.75   # 75%-90% coverage for DEGRADED-A
    COVERAGE_DEGRADED_B_MIN: float = 0.50   # 50%-75% coverage for DEGRADED-B

    RELAY_NOMINAL_MIN: float = 0.90
    RELAY_DEGRADED_A_MIN: float = 0.70

    @classmethod
    def evaluate_swarm(
        cls,
        satellites: List[CubeSat],
        network: NetworkTopology,
        sim_time_sec: float = 0.0,
        priority: MissionPriority = MissionPriority.BALANCED,
    ) -> SwarmMissionReport:
        """Evaluate constellation-wide capabilities and compute the authoritative MissionMode.

        Args:
            satellites: All 12 CubeSats in the constellation.
            network: Inter-satellite communication graph.
            sim_time_sec: Current simulation elapsed time in seconds.
            priority: Active mission priority weighting.

        Returns:
            SwarmMissionReport containing coverage, relay ratios, mission mode, and overall health score.
        """
        total_sats = len(satellites)
        if total_sats == 0:
            return SwarmMissionReport(
                timestamp_sec=sim_time_sec,
                mission_mode=MissionMode.MISSION_LOST,
                coverage_ratio=0.0,
                relay_ratio=0.0,
                compute_ratio=0.0,
                maneuvering_ratio=0.0,
                coordinator_status="NONE",
                primary_objectives_met=False,
                mission_score=0.0,
            )

        # 1. Evaluate Capability Graphs for every node
        reports = [CapabilityGraph.evaluate_satellite(s) for s in satellites]

        # 2. Count Operational Capabilities
        sensing_nodes = sum(1 for r in reports if r.capabilities[CapabilityType.SENSING] == CapabilityStatus.OPERATIONAL)
        relay_nodes = sum(1 for r in reports if r.capabilities[CapabilityType.RELAY] == CapabilityStatus.OPERATIONAL)
        compute_nodes = sum(1 for r in reports if r.capabilities[CapabilityType.COMPUTE] == CapabilityStatus.OPERATIONAL)
        maneuver_nodes = sum(1 for r in reports if r.capabilities[CapabilityType.MANEUVERING] == CapabilityStatus.OPERATIONAL)

        coverage_ratio = sensing_nodes / total_sats
        relay_ratio = relay_nodes / total_sats
        compute_ratio = compute_nodes / total_sats
        maneuver_ratio = maneuver_nodes / total_sats

        # 3. Check Network Partitioning & Coordinator Status
        partition_count = network.partition_count() if hasattr(network, "partition_count") else 1
        coordinator = next(
            (s for s in satellites if s.role == SatelliteRole.COORDINATOR and s.state not in (SatelliteState.FAILED, SatelliteState.ISOLATED)),
            None
        )

        coordinator_status = "NOMINAL"
        if not coordinator:
            coordinator_status = "FAILOVER_REQUIRED"

        failed_nodes = sum(1 for s in satellites if s.state == SatelliteState.FAILED)

        # 4. Determine Mission Mode
        # - NOMINAL: >= 90% sensing & relay, connected network, coordinator healthy
        # - DEGRADED-A: All primary objectives preserved (e.g. lost 1-2 thrusters or 1 sensor, coverage >= 75%)
        # - DEGRADED-B: Secondary objectives sacrificed (coverage 50-75% or minor partition)
        # - SURVIVAL: Severe loss (coverage < 50% or multiple dead nodes), basic bus survival prioritized
        # - MISSION-LOST: Swarm collapsed (> 50% nodes dead or partitioned without recovery)

        if failed_nodes >= 6 or (coverage_ratio < 0.25 and relay_ratio < 0.25):
            mode = MissionMode.MISSION_LOST
            primary_met = False
        elif failed_nodes >= 3 or coverage_ratio < cls.COVERAGE_DEGRADED_B_MIN or coordinator_status == "FAILOVER_REQUIRED":
            mode = MissionMode.SURVIVAL
            primary_met = False
        elif coverage_ratio < cls.COVERAGE_DEGRADED_A_MIN or relay_ratio < cls.RELAY_DEGRADED_A_MIN or partition_count > 1:
            mode = MissionMode.DEGRADED_B
            primary_met = True  # Degraded but primary payload still delivered
        elif coverage_ratio < cls.COVERAGE_NOMINAL_MIN or relay_ratio < cls.RELAY_NOMINAL_MIN or maneuver_ratio < 1.0 or failed_nodes > 0:
            mode = MissionMode.DEGRADED_A
            primary_met = True
        else:
            mode = MissionMode.NOMINAL
            primary_met = True

        # 5. Calculate Weighted Mission Health Score (0 - 100)
        if priority == MissionPriority.NETWORK_FIRST:
            mission_score = (relay_ratio * 45.0) + (coverage_ratio * 25.0) + (compute_ratio * 15.0) + (maneuver_ratio * 15.0)
        elif priority == MissionPriority.FUEL_SAVER:
            mission_score = (coverage_ratio * 35.0) + (relay_ratio * 30.0) + (maneuver_ratio * 25.0) + (compute_ratio * 10.0)
        elif priority == MissionPriority.COVERAGE_FIRST:
            mission_score = (coverage_ratio * 50.0) + (relay_ratio * 25.0) + (compute_ratio * 15.0) + (maneuver_ratio * 10.0)
        else:  # BALANCED
            mission_score = (coverage_ratio * 35.0) + (relay_ratio * 30.0) + (compute_ratio * 20.0) + (maneuver_ratio * 15.0)

        # Scale by network penalty if partitioned
        if partition_count > 1:
            mission_score *= max(0.6, 1.0 - (partition_count - 1) * 0.15)

        return SwarmMissionReport(
            timestamp_sec=sim_time_sec,
            mission_mode=mode,
            coverage_ratio=coverage_ratio,
            relay_ratio=relay_ratio,
            compute_ratio=compute_ratio,
            maneuvering_ratio=maneuver_ratio,
            coordinator_status=coordinator_status,
            primary_objectives_met=primary_met,
            mission_score=max(0.0, min(100.0, mission_score)),
        )

    @classmethod
    def sync_mission_state(
        cls,
        satellites: List[CubeSat],
        network: NetworkTopology,
        sim_time_sec: float = 0.0,
    ) -> SwarmMissionReport:
        """Evaluate swarm mission health and synchronize satellite mission_state strings."""
        # 1. Sync individual capabilities first
        for sat in satellites:
            CapabilityGraph.sync_satellite(sat)

        # 2. Evaluate overall swarm
        report = cls.evaluate_swarm(satellites, network, sim_time_sec)

        # 3. Synchronize mission_state string on all satellites
        for sat in satellites:
            sat.mission_state = report.mission_mode.value

        return report
