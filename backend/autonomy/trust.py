"""ASTRANET Autonomy — Spacecraft Trust Scoring & Byzantine Quarantine Engine.

Implements Master Blueprint v2.0 Section 3.12, 3.14 & Section 15.3:
- Trust-weighted consensus: Nodes with stale timing, noisy sensors, or prior
  anomalies contribute less confidence to swarm decisions.
- Byzantine spacecraft quarantine: If a spacecraft provides inconsistent evidence,
  spoofer behavior, or corrupted telemetry, ASTRANET lowers its trust score,
  excludes its messages from consensus, and isolates it from critical coordination.
"""

from typing import Dict, List, Set, Any, Optional
from dataclasses import dataclass, field


@dataclass
class TrustRecord:
    """Historical trust record for an individual spacecraft."""
    satellite_id: str
    current_trust: float = 0.98
    is_quarantined: bool = False
    consecutive_inconsistencies: int = 0
    anomaly_history: List[str] = field(default_factory=list)
    last_updated_epoch: int = 0

    def to_dict(self) -> Dict[str, Any]:
        return {
            "satelliteId": self.satellite_id,
            "trustScore": round(self.current_trust, 3),
            "isQuarantined": self.is_quarantined,
            "consecutiveInconsistencies": self.consecutive_inconsistencies,
            "anomalyHistory": list(self.anomaly_history[-5:]),
        }


class TrustManager:
    """Manages dynamic trust ratings, reputation decay, and Byzantine quarantine."""

    INITIAL_TRUST: float = 0.98
    MIN_TRUST: float = 0.05
    MAX_TRUST: float = 1.00

    # Quarantine thresholds
    QUARANTINE_THRESHOLD: float = 0.40
    REHABILITATION_THRESHOLD: float = 0.70

    # Penalties
    PENALTY_TELEMETRY_INCONSISTENCY: float = 0.15
    PENALTY_SPOOFED_TELEMETRY: float = 0.35
    PENALTY_BYZANTINE_VOTE: float = 0.25
    PENALTY_LINK_DEGRADATION: float = 0.08

    # Gradual recovery
    RESTORE_INCREMENT_PER_EPOCH: float = 0.015

    def __init__(self) -> None:
        self._records: Dict[str, TrustRecord] = {}

    def get_record(self, satellite_id: str) -> TrustRecord:
        if satellite_id not in self._records:
            self._records[satellite_id] = TrustRecord(
                satellite_id=satellite_id,
                current_trust=self.INITIAL_TRUST,
            )
        return self._records[satellite_id]

    def get_trust(self, satellite_id: str) -> float:
        return self.get_record(satellite_id).current_trust

    def is_quarantined(self, satellite_id: str) -> bool:
        return self.get_record(satellite_id).is_quarantined

    def record_inconsistency(
        self,
        satellite_id: str,
        reason: str,
        penalty: Optional[float] = None,
        epoch: int = 0,
    ) -> TrustRecord:
        """Penalize node trust upon observing contradictory or corrupted evidence."""
        record = self.get_record(satellite_id)
        deduction = penalty if penalty is not None else self.PENALTY_TELEMETRY_INCONSISTENCY
        record.current_trust = max(self.MIN_TRUST, record.current_trust - deduction)
        record.consecutive_inconsistencies += 1
        record.anomaly_history.append(reason)
        record.last_updated_epoch = epoch

        # Quarantine check
        if record.current_trust <= self.QUARANTINE_THRESHOLD:
            record.is_quarantined = True

        return record

    def record_spoofed_or_byzantine_behavior(
        self,
        satellite_id: str,
        description: str,
        epoch: int = 0,
    ) -> TrustRecord:
        """Impose severe penalty and quarantine for adversarial or Byzantine behavior."""
        return self.record_inconsistency(
            satellite_id=satellite_id,
            reason=f"Byzantine/Adversarial: {description}",
            penalty=self.PENALTY_SPOOFED_TELEMETRY,
            epoch=epoch,
        )

    def record_verified_nominal(self, satellite_id: str, epoch: int = 0) -> TrustRecord:
        """Gradually restore trust for consistently well-behaved nodes."""
        record = self.get_record(satellite_id)
        if record.current_trust < self.MAX_TRUST:
            record.current_trust = min(
                self.MAX_TRUST,
                record.current_trust + self.RESTORE_INCREMENT_PER_EPOCH,
            )
        record.consecutive_inconsistencies = max(0, record.consecutive_inconsistencies - 1)
        record.last_updated_epoch = epoch

        if record.is_quarantined and record.current_trust >= self.REHABILITATION_THRESHOLD:
            record.is_quarantined = False

        return record

    def get_all_records(self) -> Dict[str, Dict[str, Any]]:
        return {sat_id: r.to_dict() for sat_id, r in self._records.items()}
