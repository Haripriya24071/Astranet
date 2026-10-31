"""ASTRANET Recovery — Candidate Recovery Plan Generator.

Implements Master Blueprint v2.0 Section 3.1, Section 3.6, and Section 15.5:
Generates multiple distinct, plausible candidate recovery plans instead of
immediately executing the first available action.
"""

from typing import List, Dict, Optional, Any
from backend.app.core.satellite import CubeSat, SatelliteState, SatelliteRole, SubsystemStatus
from backend.app.core.network import NetworkTopology
from backend.autonomy.contracts import (
    DiagnosticReport,
    CapabilityType,
    CapabilityStatus,
)
from backend.recovery.contracts import (
    RecoveryCandidate,
    RecoveryAction,
    ActionType,
)


class CandidatePlanGenerator:
    """Generates a competitive portfolio of recovery strategies for an anomalous spacecraft."""

    @classmethod
    def generate_candidates(
        cls,
        target: CubeSat,
        diagnosis: DiagnosticReport,
        satellites: List[CubeSat],
        network: NetworkTopology,
    ) -> List[RecoveryCandidate]:
        """Generate competing recovery candidates based on the diagnosed capability loss."""
        candidates: List[RecoveryCandidate] = []

        # Find best candidate peer in same plane to absorb workload
        same_plane_peers = [
            s for s in satellites
            if s.plane == target.plane
            and s.id != target.id
            and s.state not in (SatelliteState.FAILED, SatelliteState.ISOLATED)
            and s.battery > 40.0
        ]
        # Sort by battery descending
        same_plane_peers.sort(key=lambda s: s.battery, reverse=True)
        best_peer = same_plane_peers[0] if same_plane_peers else None

        # ---------------------------------------------------------------------
        # CANDIDATE A: Agile Role Migration (High yield, moderate resource cost)
        # ---------------------------------------------------------------------
        actions_a: List[RecoveryAction] = []
        if target.role in (SatelliteRole.COORDINATOR, SatelliteRole.RELAY) and best_peer:
            actions_a.append(
                RecoveryAction(
                    action_type=ActionType.ROLE_MIGRATION,
                    target_satellite_id=best_peer.id,
                    parameters={"newRole": target.role.value, "previousHolder": target.id},
                    description=f"Migrate {target.role.value} responsibility from {target.id} to {best_peer.id}."
                )
            )
        actions_a.append(
            RecoveryAction(
                action_type=ActionType.ROLE_MIGRATION,
                target_satellite_id=target.id,
                parameters={"newRole": SatelliteRole.OBSERVER.value},
                description=f"Demote impaired {target.id} to degraded observer role."
            )
        )

        candidates.append(
            RecoveryCandidate(
                plan_id="PLAN-A-ROLE-MIGRATION",
                name="Agile Role Migration",
                actions=actions_a,
                expected_mission_utility=94.5,
                delta_v_cost_ms=0.0,
                energy_cost_pct=6.5,  # Slightly higher power draw on receiving peer
                risk=0.12,
                recovery_confidence=0.92,
                predicted_secondary_risk=0.15,
                resilience_debt=18.0,  # Consumes one healthy observer as relay
                n1_survival=0.88,
                n2_survival=0.74,
            )
        )

        # ---------------------------------------------------------------------
        # CANDIDATE B: Communication Topology Rerouting (Zero fuel, fast fix)
        # ---------------------------------------------------------------------
        actions_b = [
            RecoveryAction(
                action_type=ActionType.TOPOLOGY_REROUTE,
                target_satellite_id=target.id,
                parameters={"bypassNode": target.id, "increaseTransmitPower": True},
                description=f"Reroute multi-hop ISL packets around {target.id} to preserve ring connectivity."
            )
        ]

        candidates.append(
            RecoveryCandidate(
                plan_id="PLAN-B-TOPOLOGY-REROUTE",
                name="Dynamic Topology Reroute",
                actions=actions_b,
                expected_mission_utility=82.0,
                delta_v_cost_ms=0.0,
                energy_cost_pct=11.0,  # Neighbor transceivers boost RF power to bridge gap
                risk=0.22,
                recovery_confidence=0.86,
                predicted_secondary_risk=0.28,  # RF amplifiers run hotter
                resilience_debt=24.0,  # Increases ISL hops and average latency
                n1_survival=0.79,
                n2_survival=0.62,
            )
        )

        # ---------------------------------------------------------------------
        # CANDIDATE C: Safe-Mode Load-Sharing & Duty-Cycle Throttling
        # ---------------------------------------------------------------------
        actions_c = [
            RecoveryAction(
                action_type=ActionType.POWER_THROTTLE,
                target_satellite_id=target.id,
                parameters={"payloadDutyCyclePct": 40.0, "conserveBattery": True},
                description=f"Throttle payload duty cycle on {target.id} to 40% to halt battery degradation."
            )
        ]
        if best_peer:
            actions_c.append(
                RecoveryAction(
                    action_type=ActionType.POWER_THROTTLE,
                    target_satellite_id=best_peer.id,
                    parameters={"payloadDutyCyclePct": 120.0, "boostCoverage": True},
                    description=f"Overclock {best_peer.id} optical collection window to offset coverage deficit."
                )
            )

        candidates.append(
            RecoveryCandidate(
                plan_id="PLAN-C-SAFE-THROTTLE",
                name="Safe Mode Load-Sharing",
                actions=actions_c,
                expected_mission_utility=78.0,
                delta_v_cost_ms=0.0,
                energy_cost_pct=3.0,
                risk=0.08,
                recovery_confidence=0.96,
                predicted_secondary_risk=0.10,
                resilience_debt=12.0,  # Very low resilience debt
                n1_survival=0.91,
                n2_survival=0.82,
            )
        )

        # ---------------------------------------------------------------------
        # CANDIDATE D: Orbital Formation Trim (Active Propulsion Maneuver)
        # Only feasible if propulsion and propellant > 15% are available
        # ---------------------------------------------------------------------
        if target.capabilities.maneuvering and target.propellant > 15.0:
            actions_d = [
                RecoveryAction(
                    action_type=ActionType.FORMATION_TRIM,
                    target_satellite_id=target.id,
                    parameters={"deltaVTargetMs": 1.85, "phaseAdvanceDeg": 5.0},
                    description=f"Execute +1.85 m/s delta-V burn on {target.id} to close inter-satellite gap."
                )
            ]
            candidates.append(
                RecoveryCandidate(
                    plan_id="PLAN-D-FORMATION-MANEUVER",
                    name="Orbital Phase Trim Maneuver",
                    actions=actions_d,
                    expected_mission_utility=98.0,
                    delta_v_cost_ms=1.85,
                    energy_cost_pct=14.0,
                    risk=0.25,
                    recovery_confidence=0.84,
                    predicted_secondary_risk=0.32,  # Propellant loss creates future vulnerability
                    resilience_debt=45.0,  # High resilience debt (burns delta-V reserves)
                    n1_survival=0.68,
                    n2_survival=0.51,
                )
            )

        # ---------------------------------------------------------------------
        # CANDIDATE E: Byzantine Quarantine & Isolation (for Adversarial/Corrupted)
        # ---------------------------------------------------------------------
        if "TOTAL" in diagnosis.attributed_cause or "BYZANTINE" in diagnosis.attributed_cause or diagnosis.is_total_node_loss:
            actions_e = [
                RecoveryAction(
                    action_type=ActionType.ISOLATE_NODE,
                    target_satellite_id=target.id,
                    parameters={"severISL": True, "quarantineConsensus": True},
                    description=f"Sever all communication links with {target.id} and exclude from consensus."
                )
            ]
            candidates.append(
                RecoveryCandidate(
                    plan_id="PLAN-E-QUARANTINE-ISOLATE",
                    name="Byzantine Swarm Quarantine",
                    actions=actions_e,
                    expected_mission_utility=75.0,
                    delta_v_cost_ms=0.0,
                    energy_cost_pct=0.0,
                    risk=0.05,
                    recovery_confidence=0.98,
                    predicted_secondary_risk=0.05,
                    resilience_debt=30.0,
                    n1_survival=0.82,
                    n2_survival=0.70,
                )
            )

        return candidates
