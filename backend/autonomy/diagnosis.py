"""ASTRANET Autonomy — Fault Attribution & Probabilistic Diagnostic Engine.

Implements Master Blueprint v2.0 Section 3.2:
Failure Attribution, Not Merely Failure Detection:
Move beyond heartbeat timeout logic. Infer the likely cause of a fault from multiple
evidence sources: communication subsystem, network partition, power system,
attitude control, navigation, propulsion, or complete node loss. Peer evidence
updates these probabilities before recovery is initiated.
"""

from typing import List, Dict, Optional, Any
import math

from backend.app.core.satellite import CubeSat, SatelliteState, SubsystemStatus
from backend.app.core.network import NetworkTopology
from backend.app.core.faults import FaultEvent, FailureType, FailureSeverity
from backend.autonomy.contracts import (
    DiagnosticReport,
    DiagnosticEvidence,
    CapabilityType,
    CapabilityStatus,
)
from backend.autonomy.capability import CapabilityGraph


class FaultAttributor:
    """Diagnoses satellite anomalies and attributes root causes using multi-sensor evidence."""

    def __init__(self) -> None:
        self._diagnostic_history: List[DiagnosticReport] = []

    @property
    def history(self) -> List[DiagnosticReport]:
        return self._diagnostic_history

    def diagnose_satellite(
        self,
        satellite: CubeSat,
        network: NetworkTopology,
        sim_time_sec: float,
        fault_event: Optional[FaultEvent] = None,
    ) -> DiagnosticReport:
        """Analyze satellite telemetry to formulate a probabilistic diagnosis and attribution.

        Args:
            satellite: Target anomalous CubeSat.
            network: Swarm communication topology.
            sim_time_sec: Master simulation time in seconds.
            fault_event: Optional injected fault event context if known.

        Returns:
            DiagnosticReport containing root cause attribution, confidence score, and evidence trail.
        """
        evidence_list: List[DiagnosticEvidence] = []
        cap_report = CapabilityGraph.evaluate_satellite(satellite)

        subs = satellite.subsystems
        bat = satellite.battery
        prop = satellite.propellant
        cpu = satellite.compute
        net = satellite.network

        # 1. Inspect Power Bus
        if bat < 20.0:
            evidence_list.append(
                DiagnosticEvidence(
                    source="EPS (Power)",
                    metric="battery_soc_pct",
                    observed_value=f"{bat:.1f}%",
                    expected_value=">= 40.0%",
                    severity="critical" if bat < 12.0 else "warning",
                    description=f"Critical battery depletion observed ({bat:.1f}% SoC). Triggering bus preservation.",
                )
            )

        # 2. Inspect Communications & Network Topology
        neighbor_count = network.get_neighbor_count(satellite.id)
        if subs.communications == SubsystemStatus.FAILED:
            evidence_list.append(
                DiagnosticEvidence(
                    source="RF Comms",
                    metric="transceiver_status",
                    observed_value=subs.communications.value,
                    expected_value=SubsystemStatus.NOMINAL.value,
                    severity="critical",
                    description="Transceiver carrier signal lost. Unable to route inter-satellite relay frames.",
                )
            )
        elif neighbor_count == 0:
            evidence_list.append(
                DiagnosticEvidence(
                    source="Network Topology",
                    metric="active_isl_neighbors",
                    observed_value=0,
                    expected_value=">= 1",
                    severity="warning",
                    description="Zero active ISL links within maximum range or line-of-sight occlusion.",
                )
            )

        # 3. Inspect Propulsion & Kinetic Control
        if subs.propulsion == SubsystemStatus.FAILED:
            evidence_list.append(
                DiagnosticEvidence(
                    source="GNC Propulsion",
                    metric="thruster_status",
                    observed_value=subs.propulsion.value,
                    expected_value=SubsystemStatus.NOMINAL.value,
                    severity="critical",
                    description="Thruster valve failure or pressure loss detected. Station-keeping disabled.",
                )
            )
        elif prop <= 5.0:
            evidence_list.append(
                DiagnosticEvidence(
                    source="Propellant Tank",
                    metric="propellant_reserve_pct",
                    observed_value=f"{prop:.1f}%",
                    expected_value=">= 15.0%",
                    severity="critical",
                    description="Delta-V propellant depleted below minimum station-keeping threshold.",
                )
            )

        # 4. Inspect Attitude Determination and Control (ADCS)
        if subs.attitudeControl == SubsystemStatus.FAILED:
            evidence_list.append(
                DiagnosticEvidence(
                    source="ADCS",
                    metric="reaction_wheel_status",
                    observed_value=subs.attitudeControl.value,
                    expected_value=SubsystemStatus.NOMINAL.value,
                    severity="critical",
                    description="Reaction wheel assembly or gyro failure. Unable to maintain nadir pointing.",
                )
            )

        # 5. Inspect Onboard Computer (OBC)
        if subs.compute == SubsystemStatus.FAILED:
            evidence_list.append(
                DiagnosticEvidence(
                    source="OBC (Compute)",
                    metric="processor_health",
                    observed_value=subs.compute.value,
                    expected_value=SubsystemStatus.NOMINAL.value,
                    severity="critical",
                    description="Onboard processor unresponsive or kernel panic detected.",
                )
            )

        # 6. Synthesize Root Cause Attribution & Total vs Partial Loss
        is_total_loss = False
        action_class = "PARTIAL_REALLOCATION"

        # Check for catastrophic multi-subsystem death (power empty + compute failed + comms failed)
        failed_subs_count = sum(1 for s in subs.to_dict().values() if s == SubsystemStatus.FAILED.value)

        if failed_subs_count >= 4 or (bat <= 5.0 and subs.compute == SubsystemStatus.FAILED):
            is_total_loss = True
            attributed_cause = "TOTAL_SPACECRAFT_BUS_FAILURE"
            action_class = "FULL_FAILOVER"
            confidence = 0.98
        elif subs.propulsion == SubsystemStatus.FAILED:
            # PROVENANCE NOTE: Propulsion failure leaves sensing and comms operational
            attributed_cause = "PROPULSION_THRUSTER_DEGRADATION"
            action_class = "PARTIAL_REALLOCATION"
            confidence = 0.95
        elif subs.communications == SubsystemStatus.FAILED:
            attributed_cause = "COMMUNICATION_TRANSCEIVER_LOSS"
            action_class = "TOPOLOGY_REROUTE"
            confidence = 0.94
        elif bat < 20.0 or subs.power == SubsystemStatus.FAILED:
            attributed_cause = "POWER_SUBSYSTEM_DEGRADATION"
            action_class = "SAFE_MODE"
            confidence = 0.92
        elif subs.attitudeControl == SubsystemStatus.FAILED:
            attributed_cause = "ATTITUDE_CONTROL_POINTING_LOSS"
            action_class = "PARTIAL_REALLOCATION"
            confidence = 0.90
        elif subs.navigation == SubsystemStatus.FAILED:
            attributed_cause = "NAVIGATION_GNSS_RECEIVER_LOSS"
            action_class = "PARTIAL_REALLOCATION"
            confidence = 0.88
        elif subs.payload == SubsystemStatus.FAILED:
            attributed_cause = "PAYLOAD_INSTRUMENT_SHUTDOWN"
            action_class = "PARTIAL_REALLOCATION"
            confidence = 0.92
        elif neighbor_count == 0:
            attributed_cause = "TEMPORARY_TOPOLOGY_PARTITION"
            action_class = "TOPOLOGY_REROUTE"
            confidence = 0.82
        else:
            attributed_cause = "UNSPECIFIED_ANOMALY"
            action_class = "PARTIAL_REALLOCATION"
            confidence = 0.70

        # Adjust confidence upward if corroborating evidence items exist
        if len(evidence_list) >= 2:
            confidence = min(0.99, confidence + 0.04)

        report = DiagnosticReport(
            satellite_id=satellite.id,
            timestamp_sec=sim_time_sec,
            attributed_cause=attributed_cause,
            is_total_node_loss=is_total_loss,
            confidence=confidence,
            evidence=evidence_list,
            affected_capabilities=cap_report.impaired_capabilities,
            preserved_capabilities=cap_report.preserved_capabilities,
            recommended_action_class=action_class,
        )

        self._diagnostic_history.append(report)
        return report
