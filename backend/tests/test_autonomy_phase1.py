"""ASTRANET Autonomy & Resilience Engine — Phase 1 Test Suite.

Validates Zahid's Phase 1 deliverables per Master Blueprint v2.0:
1. Capability Graph & Partial-Failure Reasoning: Spacecraft is modeled as a bundle
   of capabilities, not a binary alive/dead node.
2. Fault Attribution & Diagnosis: Probabilistic attribution distinguishing partial
   degradation from total node loss with evidence tracking.
3. Swarm Mission Model: Explicitly maps capability state to NOMINAL, DEGRADED-A,
   DEGRADED-B, SURVIVAL, and MISSION-LOST.
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
from backend.app.core.faults import FaultEngine, FailureType, FailureSeverity
from backend.app.core.swarm import SwarmOrchestrator
from backend.autonomy.contracts import (
    CapabilityType,
    CapabilityStatus,
    MissionMode,
    MissionPriority,
)
from backend.autonomy.capability import CapabilityGraph
from backend.autonomy.diagnosis import FaultAttributor
from backend.autonomy.mission_model import SwarmMissionModel


class TestCapabilityGraph(unittest.TestCase):
    """Unit tests for spacecraft capability graph and partial-role degradation."""

    def setUp(self) -> None:
        orbit = KeplerianOrbit(semi_major_axis_m=6928137.0, inclination_deg=53.0)
        self.sat = CubeSat(
            satellite_id="SAT-04",
            name="SAT-04",
            plane_name="PLANE A",
            plane_index=0,
            slot_name="SLOT 04",
            slot_index=3,
            orbit=orbit,
            role=SatelliteRole.RELAY,
            initial_battery=90.0,
            initial_propellant=85.0,
            initial_compute=40.0,
            initial_storage=50.0,
            trust_score=0.98,
        )

    def test_nominal_satellite_has_all_capabilities_operational(self) -> None:
        report = CapabilityGraph.evaluate_satellite(self.sat)
        self.assertEqual(report.functional_ratio, 1.0)
        self.assertEqual(len(report.impaired_capabilities), 0)
        self.assertEqual(len(report.preserved_capabilities), 6)
        for cap in CapabilityType:
            self.assertEqual(report.capabilities[cap], CapabilityStatus.OPERATIONAL)

    def test_propulsion_failure_preserves_sensing_and_relay(self) -> None:
        """Core blueprint requirement: A CubeSat with propulsion failure still serves as sensor/relay."""
        self.sat.subsystems.propulsion = SubsystemStatus.FAILED

        report = CapabilityGraph.evaluate_satellite(self.sat)

        # Maneuvering is lost
        self.assertEqual(report.capabilities[CapabilityType.MANEUVERING], CapabilityStatus.LOST)
        self.assertIn(CapabilityType.MANEUVERING, report.impaired_capabilities)

        # Sensing, relay, navigation, compute, storage are PRESERVED
        self.assertEqual(report.capabilities[CapabilityType.SENSING], CapabilityStatus.OPERATIONAL)
        self.assertEqual(report.capabilities[CapabilityType.RELAY], CapabilityStatus.OPERATIONAL)
        self.assertEqual(report.capabilities[CapabilityType.NAVIGATION], CapabilityStatus.OPERATIONAL)
        self.assertEqual(report.capabilities[CapabilityType.COMPUTE], CapabilityStatus.OPERATIONAL)
        self.assertEqual(report.capabilities[CapabilityType.STORAGE], CapabilityStatus.OPERATIONAL)
        self.assertIn(CapabilityType.SENSING, report.preserved_capabilities)
        self.assertIn(CapabilityType.RELAY, report.preserved_capabilities)

    def test_communications_failure_preserves_sensing_and_maneuvering(self) -> None:
        self.sat.subsystems.communications = SubsystemStatus.FAILED

        report = CapabilityGraph.evaluate_satellite(self.sat)
        self.assertEqual(report.capabilities[CapabilityType.RELAY], CapabilityStatus.LOST)
        self.assertEqual(report.capabilities[CapabilityType.SENSING], CapabilityStatus.OPERATIONAL)
        self.assertEqual(report.capabilities[CapabilityType.MANEUVERING], CapabilityStatus.OPERATIONAL)
        self.assertEqual(report.capabilities[CapabilityType.COMPUTE], CapabilityStatus.OPERATIONAL)

    def test_low_power_load_shedding_disables_sensing(self) -> None:
        """Low power load shedding drops payload instrument to protect satellite bus."""
        self.sat.battery = 18.0  # Under 20% threshold

        report = CapabilityGraph.evaluate_satellite(self.sat)
        self.assertEqual(report.capabilities[CapabilityType.SENSING], CapabilityStatus.LOST)
        # Relay still operates above 10%
        self.assertEqual(report.capabilities[CapabilityType.RELAY], CapabilityStatus.OPERATIONAL)

    def test_sync_satellite_updates_boolean_flags(self) -> None:
        self.sat.subsystems.propulsion = SubsystemStatus.FAILED
        CapabilityGraph.sync_satellite(self.sat)

        self.assertFalse(self.sat.capabilities.maneuvering)
        self.assertTrue(self.sat.capabilities.sensing)
        self.assertTrue(self.sat.capabilities.relay)


class TestFaultAttributionAndDiagnosis(unittest.TestCase):
    """Unit tests for probabilistic fault attribution and evidence synthesis."""

    def setUp(self) -> None:
        orbit = KeplerianOrbit(semi_major_axis_m=6928137.0, inclination_deg=53.0)
        self.sat = CubeSat(
            satellite_id="SAT-02",
            name="SAT-02",
            plane_name="PLANE A",
            plane_index=0,
            slot_name="SLOT 02",
            slot_index=1,
            orbit=orbit,
            role=SatelliteRole.RELAY,
        )
        self.network = NetworkTopology()
        self.attributor = FaultAttributor()

    def test_diagnose_propulsion_thruster_degradation(self) -> None:
        self.sat.subsystems.propulsion = SubsystemStatus.FAILED
        report = self.attributor.diagnose_satellite(self.sat, self.network, sim_time_sec=10.0)

        self.assertEqual(report.satellite_id, "SAT-02")
        self.assertEqual(report.attributed_cause, "PROPULSION_THRUSTER_DEGRADATION")
        self.assertFalse(report.is_total_node_loss)
        self.assertGreaterEqual(report.confidence, 0.90)
        self.assertIn(CapabilityType.MANEUVERING, report.affected_capabilities)
        self.assertIn(CapabilityType.RELAY, report.preserved_capabilities)
        self.assertGreater(len(report.evidence), 0)

    def test_diagnose_total_bus_power_collapse(self) -> None:
        # Multi-subsystem failure mimicking catastrophic bus collapse
        self.sat.subsystems.communications = SubsystemStatus.FAILED
        self.sat.subsystems.navigation = SubsystemStatus.FAILED
        self.sat.subsystems.compute = SubsystemStatus.FAILED
        self.sat.subsystems.power = SubsystemStatus.FAILED
        self.sat.battery = 0.0

        report = self.attributor.diagnose_satellite(self.sat, self.network, sim_time_sec=25.0)
        self.assertTrue(report.is_total_node_loss)
        self.assertEqual(report.attributed_cause, "TOTAL_SPACECRAFT_BUS_FAILURE")
        self.assertEqual(report.recommended_action_class, "FULL_FAILOVER")
        self.assertGreaterEqual(report.confidence, 0.95)


class TestSwarmMissionModel(unittest.TestCase):
    """Unit tests for constellation mission modes and degradation transitions."""

    def setUp(self) -> None:
        self.orchestrator = SwarmOrchestrator()

    def test_nominal_constellation_mission_mode(self) -> None:
        frame = self.orchestrator.get_telemetry_frame()
        summary = frame["swarmSummary"]

        self.assertEqual(summary["missionState"], MissionMode.NOMINAL.value)
        self.assertGreaterEqual(summary["missionScore"], 95.0)
        self.assertEqual(summary["coverageRatio"], 1.0)

    def test_propulsion_failure_transitions_to_degraded_a(self) -> None:
        """A single propulsion fault preserves primary mission coverage and results in DEGRADED-A."""
        self.orchestrator.inject_fault(
            target_satellite_id="SAT-04",
            failure_type=FailureType.PROPULSION_FAILURE,
            severity=FailureSeverity.CRITICAL,
        )

        frame = self.orchestrator.get_telemetry_frame()
        summary = frame["swarmSummary"]

        # Constellation mode is DEGRADED-A (minor capability loss, primary Earth observation preserved)
        self.assertEqual(summary["missionState"], MissionMode.DEGRADED_A.value)
        # All 12 satellites still have operational sensing instruments
        self.assertEqual(summary["coverageRatio"], 1.0)

        # Check SAT-04 in frame: maneuvering lost, but sensing and relay are active!
        sat_04 = next(s for s in frame["satellites"] if s["id"] == "SAT-04")
        self.assertFalse(sat_04["capabilities"]["maneuvering"])
        self.assertTrue(sat_04["capabilities"]["sensing"])
        self.assertTrue(sat_04["capabilities"]["relay"])
        self.assertEqual(sat_04["missionState"], MissionMode.DEGRADED_A.value)

    def test_coordinator_loss_triggers_survival_mode(self) -> None:
        """Coordinator node loss puts swarm into SURVIVAL until failover election completes."""
        self.orchestrator.inject_fault(
            target_satellite_id="SAT-07",
            failure_type=FailureType.NODE_LOSS,
            severity=FailureSeverity.CRITICAL,
        )

        frame = self.orchestrator.get_telemetry_frame()
        summary = frame["swarmSummary"]

        # SURVIVAL mode triggered because coordinator is lost
        self.assertEqual(summary["missionState"], MissionMode.SURVIVAL.value)


if __name__ == "__main__":
    unittest.main()
