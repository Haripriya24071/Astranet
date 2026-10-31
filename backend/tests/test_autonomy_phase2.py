"""ASTRANET Autonomy & Resilience Engine — Phase 2 Test Suite.

Validates Zahid's Phase 2 deliverables per Master Blueprint v2.0:
1. Spacecraft Trust Scoring & Dynamic Reputation Updates.
2. Byzantine / Spoofed Node Detection & Quarantine.
3. Peer Verification Quorum & Trust-Weighted Voting.
4. Split-Brain-Safe Coordinator Failover Election with Quorum Enforcement.
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
from backend.autonomy.trust import TrustManager
from backend.autonomy.consensus import ConsensusEngine, PeerConsensusResult, ElectionResult
from backend.app.core.swarm import SwarmOrchestrator


class TestTrustManager(unittest.TestCase):
    """Unit tests for dynamic node trust and Byzantine quarantine."""

    def setUp(self) -> None:
        self.trust_mgr = TrustManager()

    def test_initial_trust_score(self) -> None:
        trust = self.trust_mgr.get_trust("SAT-01")
        self.assertAlmostEqual(trust, 0.98, delta=0.01)
        self.assertFalse(self.trust_mgr.is_quarantined("SAT-01"))

    def test_inconsistency_penalties_decay_trust(self) -> None:
        self.trust_mgr.record_inconsistency("SAT-02", "Missed telemetry sync")
        trust_1 = self.trust_mgr.get_trust("SAT-02")
        self.assertLess(trust_1, 0.98)

        self.trust_mgr.record_inconsistency("SAT-02", "Contradictory telemetry")
        trust_2 = self.trust_mgr.get_trust("SAT-02")
        self.assertLess(trust_2, trust_1)

    def test_byzantine_spoofing_triggers_quarantine(self) -> None:
        # A single severe spoofing event + inconsistency drops trust below 0.40 threshold
        self.trust_mgr.record_spoofed_or_byzantine_behavior(
            "SAT-05", "Spoofed position telemetry"
        )
        self.trust_mgr.record_spoofed_or_byzantine_behavior(
            "SAT-05", "Contradictory consensus vote"
        )

        trust = self.trust_mgr.get_trust("SAT-05")
        self.assertLessEqual(trust, 0.40)
        self.assertTrue(self.trust_mgr.is_quarantined("SAT-05"))

    def test_rehabilitation_restores_trust_above_threshold(self) -> None:
        self.trust_mgr.record_spoofed_or_byzantine_behavior("SAT-06", "Test anomaly")
        self.trust_mgr.record_spoofed_or_byzantine_behavior("SAT-06", "Test anomaly 2")
        self.assertTrue(self.trust_mgr.is_quarantined("SAT-06"))

        # Re-verify nominal over multiple epochs
        for epoch in range(1, 40):
            self.trust_mgr.record_verified_nominal("SAT-06", epoch=epoch)

        self.assertGreater(self.trust_mgr.get_trust("SAT-06"), 0.70)
        self.assertFalse(self.trust_mgr.is_quarantined("SAT-06"))


class TestConsensusEngine(unittest.TestCase):
    """Unit tests for peer-verification and coordinator failover elections."""

    def setUp(self) -> None:
        self.orchestrator = SwarmOrchestrator()
        self.trust_mgr = TrustManager()
        self.consensus = ConsensusEngine(trust_manager=self.trust_mgr)

    def test_peer_verification_confirms_anomalous_node(self) -> None:
        # Inject propulsion failure on SAT-04
        sat_04 = self.orchestrator.get_satellite("SAT-04")
        self.assertIsNotNone(sat_04)
        sat_04.subsystems.propulsion = SubsystemStatus.FAILED
        sat_04.state = SatelliteState.DEGRADED

        result = self.consensus.verify_anomaly_with_peers(
            target=sat_04,
            satellites=self.orchestrator.satellites,
            network=self.orchestrator.network,
        )

        self.assertTrue(result.quorum_reached)
        self.assertTrue(result.confirmed)
        self.assertGreater(result.total_peers_observed, 0)
        self.assertGreaterEqual(result.weighted_agreement_ratio, 0.66)

    def test_quarantined_peer_is_excluded_from_voting(self) -> None:
        # Put neighbor SAT-03 in quarantine
        self.trust_mgr.record_spoofed_or_byzantine_behavior("SAT-03", "Malicious node")
        self.trust_mgr.record_spoofed_or_byzantine_behavior("SAT-03", "Malicious node 2")
        self.assertTrue(self.trust_mgr.is_quarantined("SAT-03"))

        sat_04 = self.orchestrator.get_satellite("SAT-04")
        sat_04.subsystems.propulsion = SubsystemStatus.FAILED

        result = self.consensus.verify_anomaly_with_peers(
            target=sat_04,
            satellites=self.orchestrator.satellites,
            network=self.orchestrator.network,
        )

        voter_ids = [v.voter_id for v in result.voter_details]
        self.assertNotIn("SAT-03", voter_ids)

    def test_coordinator_election_with_quorum(self) -> None:
        # Build connected network component with 7 operational nodes (excluding SAT-07)
        connected_net = NetworkTopology()
        connected_ids = ["SAT-01", "SAT-02", "SAT-03", "SAT-04", "SAT-05", "SAT-06", "SAT-08"]
        for i in range(len(connected_ids) - 1):
            connected_net._graph.add_edge(connected_ids[i], connected_ids[i + 1])

        # SAT-07 fails
        sat_07 = self.orchestrator.get_satellite("SAT-07")
        sat_07.state = SatelliteState.FAILED

        result = self.consensus.elect_coordinator(
            satellites=self.orchestrator.satellites,
            network=connected_net,
        )

        self.assertFalse(result.is_unresolved)
        self.assertTrue(result.quorum_met)
        self.assertIsNotNone(result.elected_coordinator_id)
        self.assertIn(result.elected_coordinator_id, connected_ids)
        self.assertNotEqual(result.elected_coordinator_id, "SAT-07")
        self.assertGreater(result.winning_score, 0.5)

    def test_election_unresolved_when_quorum_fails(self) -> None:
        # Fail 6 satellites so only 6 remain (below quorum threshold of 7)
        for sat_id in ["SAT-01", "SAT-02", "SAT-03", "SAT-04", "SAT-05", "SAT-06"]:
            sat = self.orchestrator.get_satellite(sat_id)
            sat.state = SatelliteState.FAILED

        result = self.consensus.elect_coordinator(
            satellites=self.orchestrator.satellites,
            network=self.orchestrator.network,
        )

        # Must report unresolved to prevent split-brain leadership
        self.assertTrue(result.is_unresolved)
        self.assertFalse(result.quorum_met)
        self.assertIsNone(result.elected_coordinator_id)


if __name__ == "__main__":
    unittest.main()
