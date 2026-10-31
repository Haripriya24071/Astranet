"""ASTRANET Autonomy — Peer Verification, Trust-Weighted Consensus & Failover Election.

Implements Master Blueprint v2.0 Section 3.2, 3.11, 3.12, 3.14 & Section 15.3:
- Peer verification of anomalies across line-of-sight RF neighbors.
- Trust-weighted consensus voting to reduce the influence of noisy or stale nodes.
- Byzantine / quarantined node exclusion from quorums.
- Quorum-enforced coordinator failover election (requiring >= 7 reachable nodes).
"""

from typing import List, Dict, Tuple, Optional, Set, Any
from dataclasses import dataclass, field
import numpy as np

from backend.app.core.satellite import CubeSat, SatelliteState, SatelliteRole, SubsystemStatus
from backend.app.core.network import (
    NetworkTopology,
    compute_euclidean_distance,
    check_earth_line_of_sight,
    DEFAULT_MAX_ISL_RANGE_M,
)
from backend.autonomy.trust import TrustManager


@dataclass
class PeerVote:
    """Individual peer vote on anomaly confirmation or coordinator election."""
    voter_id: str
    vote_confirm: bool
    trust_weight: float
    evidence: str


@dataclass
class PeerConsensusResult:
    """Outcome of a trust-weighted peer verification quorum."""
    target_id: str
    confirmed: bool
    quorum_reached: bool
    total_peers_observed: int
    weighted_agreement_ratio: float
    voter_details: List[PeerVote] = field(default_factory=list)
    reason: str = ""

    def to_dict(self) -> Dict[str, Any]:
        return {
            "targetId": self.target_id,
            "confirmed": self.confirmed,
            "quorumReached": self.quorum_reached,
            "totalPeersObserved": self.total_peers_observed,
            "weightedAgreementRatio": round(self.weighted_agreement_ratio, 3),
            "reason": self.reason,
            "votes": [
                {
                    "voterId": v.voter_id,
                    "confirm": v.vote_confirm,
                    "trustWeight": round(v.trust_weight, 3),
                    "evidence": v.evidence,
                }
                for v in self.voter_details
            ],
        }


@dataclass
class ElectionResult:
    """Outcome of a swarm coordinator election."""
    elected_coordinator_id: Optional[str]
    is_unresolved: bool
    participating_nodes_count: int
    quorum_met: bool
    winning_score: float
    reason: str

    def to_dict(self) -> Dict[str, Any]:
        return {
            "electedCoordinatorId": self.elected_coordinator_id,
            "isUnresolved": self.is_unresolved,
            "participatingNodesCount": self.participating_nodes_count,
            "quorumMet": self.quorum_met,
            "winningScore": round(self.winning_score, 3),
            "reason": self.reason,
        }


class ConsensusEngine:
    """Orchestrates trust-weighted peer confirmation and split-brain-safe coordinator elections."""

    # Explicit Quorum Thresholds:
    MIN_PEER_QUORUM_COUNT: int = 1
    PEER_QUORUM_RATIO: float = 0.6667
    GLOBAL_ELECTION_QUORUM: int = 7  # Majority of 12-satellite constellation

    def __init__(self, trust_manager: Optional[TrustManager] = None) -> None:
        self.trust_manager: TrustManager = trust_manager if trust_manager is not None else TrustManager()

    def verify_anomaly_with_peers(
        self,
        target: CubeSat,
        satellites: List[CubeSat],
        network: NetworkTopology,
    ) -> PeerConsensusResult:
        """Collect trust-weighted votes from reachable line-of-sight peers to confirm an anomaly.

        Args:
            target: The anomalous CubeSat under suspicion.
            satellites: Full constellation satellite list.
            network: Swarm communication graph.

        Returns:
            PeerConsensusResult indicating whether quorum agreed the anomaly is genuine.
        """
        sat_map = {s.id: s for s in satellites}
        votes: List[PeerVote] = []

        # Find line-of-sight peers within geometric range
        target_pos = target.position_eci_m

        for peer in satellites:
            if peer.id == target.id:
                continue

            # Exclude failed or quarantined peers from consensus quorum
            if peer.state in (SatelliteState.FAILED, SatelliteState.ISOLATED):
                continue
            if self.trust_manager.is_quarantined(peer.id):
                continue

            peer_pos = peer.position_eci_m
            dist_m = compute_euclidean_distance(target_pos, peer_pos)

            if dist_m > network.max_range_m:
                continue

            has_los, _ = check_earth_line_of_sight(
                target_pos, peer_pos, network.earth_radius_m, network.atmosphere_buffer_m
            )
            if not has_los:
                continue

            # Peer is in line-of-sight RF range. Evaluate peer observation.
            trust_weight = self.trust_manager.get_trust(peer.id)

            # Check if peer confirms anomaly:
            # 1. Direct RF link check: is carrier absent or degraded?
            # 2. Or telemetry indicates subsystem failure
            rf_active = (target.id in network.get_active_links()) or (target.subsystems.communications != SubsystemStatus.FAILED)
            target_degraded = (target.state != SatelliteState.NOMINAL) or any(
                s != SubsystemStatus.NOMINAL.value for s in target.subsystems.to_dict().values()
            )

            confirm = target_degraded or not rf_active
            evidence_desc = (
                f"Peer {peer.id} detected telemetry/carrier anomaly on {target.id}"
                if confirm
                else f"Peer {peer.id} observed normal telemetry"
            )

            votes.append(
                PeerVote(
                    voter_id=peer.id,
                    vote_confirm=confirm,
                    trust_weight=trust_weight,
                    evidence=evidence_desc,
                )
            )

        if len(votes) < self.MIN_PEER_QUORUM_COUNT:
            return PeerConsensusResult(
                target_id=target.id,
                confirmed=False,
                quorum_reached=False,
                total_peers_observed=len(votes),
                weighted_agreement_ratio=0.0,
                voter_details=votes,
                reason="Insufficient line-of-sight peers within RF range to achieve consensus quorum.",
            )

        # Calculate trust-weighted agreement
        total_weight = sum(v.trust_weight for v in votes)
        confirm_weight = sum(v.trust_weight for v in votes if v.vote_confirm)
        weighted_ratio = confirm_weight / total_weight if total_weight > 0 else 0.0

        if len(votes) == 1:
            confirmed = votes[0].vote_confirm
        else:
            confirmed = weighted_ratio >= self.PEER_QUORUM_RATIO

        reason = (
            f"Consensus quorum verified: {len(votes)} peers, weighted agreement {weighted_ratio * 100:.1f}%"
            if confirmed
            else f"Consensus rejected: weighted agreement {weighted_ratio * 100:.1f}% below quorum threshold"
        )

        return PeerConsensusResult(
            target_id=target.id,
            confirmed=confirmed,
            quorum_reached=True,
            total_peers_observed=len(votes),
            weighted_agreement_ratio=weighted_ratio,
            voter_details=votes,
            reason=reason,
        )

    def elect_coordinator(
        self,
        satellites: List[CubeSat],
        network: NetworkTopology,
    ) -> ElectionResult:
        """Elect a new swarm coordinator enforcing connected-component quorum.

        Returns:
            ElectionResult with elected satellite ID or UNRESOLVED status if quorum is unachievable.
        """
        # Find largest connected component of operational, non-quarantined satellites
        sat_map = {s.id: s for s in satellites}
        components = network.get_connected_components()

        best_component: Set[str] = set()
        for comp in components:
            operational_nodes = {
                nid for nid in comp
                if sat_map[nid].state not in (SatelliteState.FAILED, SatelliteState.ISOLATED)
                and not self.trust_manager.is_quarantined(nid)
            }
            if len(operational_nodes) > len(best_component):
                best_component = operational_nodes

        # Enforce global majority quorum (>= 7) to prevent split-brain elections
        if len(best_component) < self.GLOBAL_ELECTION_QUORUM:
            return ElectionResult(
                elected_coordinator_id=None,
                is_unresolved=True,
                participating_nodes_count=len(best_component),
                quorum_met=False,
                winning_score=0.0,
                reason=(
                    f"Quorum failure: Largest connected operational component has {len(best_component)} "
                    f"nodes (minimum {self.GLOBAL_ELECTION_QUORUM} required). Election unresolved to prevent split-brain."
                ),
            )

        # Score eligible candidates in the quorum component
        candidate_scores: List[Tuple[CubeSat, float]] = []
        for nid in best_component:
            sat = sat_map[nid]
            trust = self.trust_manager.get_trust(sat.id)

            # Relay capability bonus
            relay_bonus = 0.25 if sat.capabilities.relay else 0.0
            # Score formula: trust (35%) + battery (25%) + compute (15%) + relay capability (25%)
            score = (
                trust * 0.35
                + (sat.battery / 100.0) * 0.25
                + (max(0.0, 100.0 - sat.compute) / 100.0) * 0.15
                + relay_bonus
            )
            candidate_scores.append((sat, score))

        # Sort descending by score, tiebreak on satellite ID
        candidate_scores.sort(key=lambda item: (item[1], item[0].id), reverse=True)
        winner, winning_score = candidate_scores[0]

        return ElectionResult(
            elected_coordinator_id=winner.id,
            is_unresolved=False,
            participating_nodes_count=len(best_component),
            quorum_met=True,
            winning_score=winning_score,
            reason=f"Candidate {winner.id} elected with quorum of {len(best_component)} peers (score: {winning_score:.3f}).",
        )
