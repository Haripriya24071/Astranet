"""ASTRANET Autonomy — Spacecraft Capability Graph & Partial-Failure Reasoning.

Implements Master Blueprint v2.0 Section 3.1 & Section 15.4:
Model each spacecraft as a bundle of capabilities rather than a binary alive/dead node.
A CubeSat with propulsion failure still serves as an Earth-observation sensor,
high-throughput relay, compute node, navigation reference, or storage buffer.
"""

from typing import Dict, List, Set, Any
from backend.app.core.satellite import CubeSat, SubsystemStatus
from backend.autonomy.contracts import (
    CapabilityType,
    CapabilityStatus,
    CapabilityReport,
)


class CapabilityGraph:
    """Evaluates and maintains functional capabilities based on physical subsystem dependencies.

    Dependency Architecture:
    - SENSING: Requires payload (primary), attitudeControl (earth pointing), power (energy).
    - RELAY: Requires communications (primary), compute (routing/framing), power (energy).
    - NAVIGATION: Requires navigation (GNSS/star-tracker), power (energy).
    - COMPUTE: Requires compute (onboard CPU), power (energy).
    - STORAGE: Requires compute (storage controller), power (energy).
    - MANEUVERING: Requires propulsion (thrusters), attitudeControl (vector pointing), power (solenoids).
    """

    # Subsystem status impact weights (0.0 = completely lost, 0.5 = degraded, 1.0 = nominal)
    STATUS_WEIGHTS: Dict[SubsystemStatus, float] = {
        SubsystemStatus.NOMINAL: 1.0,
        SubsystemStatus.WARNING: 0.85,
        SubsystemStatus.DEGRADED: 0.5,
        SubsystemStatus.FAILED: 0.0,
    }

    # Low-power load-shedding thresholds (% state of charge)
    BATTERY_CRITICAL_PAYLOAD_OFF_PCT: float = 20.0
    BATTERY_CRITICAL_COMPUTE_THROTTLE_PCT: float = 15.0
    BATTERY_EMERGENCY_COMMS_SHUTDOWN_PCT: float = 10.0
    PROPELLANT_EMPTY_THRESHOLD_PCT: float = 5.0

    @classmethod
    def evaluate_satellite(cls, satellite: CubeSat) -> CapabilityReport:
        """Evaluate all functional capabilities of a satellite from physical telemetry.

        Args:
            satellite: Target CubeSat instance.

        Returns:
            A detailed CapabilityReport with operational/degraded/lost statuses for each capability.
        """
        subs = satellite.subsystems
        bat = satellite.battery
        prop = satellite.propellant

        capabilities: Dict[CapabilityType, CapabilityStatus] = {}

        # 1. SENSING (Earth Observation payload)
        # Needs payload healthy, attitude control to point sensor at nadir, and sufficient battery
        if subs.payload == SubsystemStatus.FAILED or subs.attitudeControl == SubsystemStatus.FAILED:
            capabilities[CapabilityType.SENSING] = CapabilityStatus.LOST
        elif bat < cls.BATTERY_CRITICAL_PAYLOAD_OFF_PCT:
            # Low power load shedding drops payload to preserve bus
            capabilities[CapabilityType.SENSING] = CapabilityStatus.LOST
        elif subs.payload in (SubsystemStatus.DEGRADED, SubsystemStatus.WARNING) or subs.attitudeControl == SubsystemStatus.DEGRADED:
            capabilities[CapabilityType.SENSING] = CapabilityStatus.DEGRADED
        else:
            capabilities[CapabilityType.SENSING] = CapabilityStatus.OPERATIONAL

        # 2. RELAY (Inter-Satellite Link & Ground Communications)
        # Needs communications subsystem, compute for routing, and battery
        if subs.communications == SubsystemStatus.FAILED:
            capabilities[CapabilityType.RELAY] = CapabilityStatus.LOST
        elif bat < cls.BATTERY_EMERGENCY_COMMS_SHUTDOWN_PCT:
            capabilities[CapabilityType.RELAY] = CapabilityStatus.LOST
        elif subs.communications in (SubsystemStatus.DEGRADED, SubsystemStatus.WARNING) or subs.compute == SubsystemStatus.FAILED:
            capabilities[CapabilityType.RELAY] = CapabilityStatus.DEGRADED
        else:
            capabilities[CapabilityType.RELAY] = CapabilityStatus.OPERATIONAL

        # 3. NAVIGATION (GNSS & relative orbit determination)
        # Needs navigation subsystem and battery
        if subs.navigation == SubsystemStatus.FAILED:
            capabilities[CapabilityType.NAVIGATION] = CapabilityStatus.LOST
        elif subs.navigation in (SubsystemStatus.DEGRADED, SubsystemStatus.WARNING):
            capabilities[CapabilityType.NAVIGATION] = CapabilityStatus.DEGRADED
        else:
            capabilities[CapabilityType.NAVIGATION] = CapabilityStatus.OPERATIONAL

        # 4. COMPUTE (Distributed state processing & autonomy consensus)
        # Needs compute subsystem and battery
        if subs.compute == SubsystemStatus.FAILED:
            capabilities[CapabilityType.COMPUTE] = CapabilityStatus.LOST
        elif bat < cls.BATTERY_CRITICAL_COMPUTE_THROTTLE_PCT or subs.compute in (SubsystemStatus.DEGRADED, SubsystemStatus.WARNING):
            capabilities[CapabilityType.COMPUTE] = CapabilityStatus.DEGRADED
        else:
            capabilities[CapabilityType.COMPUTE] = CapabilityStatus.OPERATIONAL

        # 5. STORAGE (Solid-state telemetry & payload imagery buffer)
        # Needs compute controller and battery
        if subs.compute == SubsystemStatus.FAILED:
            capabilities[CapabilityType.STORAGE] = CapabilityStatus.LOST
        elif subs.compute in (SubsystemStatus.DEGRADED, SubsystemStatus.WARNING):
            capabilities[CapabilityType.STORAGE] = CapabilityStatus.DEGRADED
        else:
            capabilities[CapabilityType.STORAGE] = CapabilityStatus.OPERATIONAL

        # 6. MANEUVERING (Active delta-V & orbital station keeping)
        # Needs propulsion thrusters, propellant > 5%, attitude control pointing, and power
        if subs.propulsion == SubsystemStatus.FAILED or prop <= cls.PROPELLANT_EMPTY_THRESHOLD_PCT or subs.attitudeControl == SubsystemStatus.FAILED:
            capabilities[CapabilityType.MANEUVERING] = CapabilityStatus.LOST
        elif subs.propulsion in (SubsystemStatus.DEGRADED, SubsystemStatus.WARNING) or prop < 15.0 or subs.attitudeControl == SubsystemStatus.DEGRADED:
            capabilities[CapabilityType.MANEUVERING] = CapabilityStatus.DEGRADED
        else:
            capabilities[CapabilityType.MANEUVERING] = CapabilityStatus.OPERATIONAL

        # Determine operational / impaired lists
        impaired = [cap for cap, status in capabilities.items() if status != CapabilityStatus.OPERATIONAL]
        preserved = [cap for cap, status in capabilities.items() if status == CapabilityStatus.OPERATIONAL]
        functional_ratio = len(preserved) / len(capabilities)

        return CapabilityReport(
            satellite_id=satellite.id,
            capabilities=capabilities,
            functional_ratio=functional_ratio,
            impaired_capabilities=impaired,
            preserved_capabilities=preserved,
        )

    @classmethod
    def sync_satellite(cls, satellite: CubeSat) -> CapabilityReport:
        """Evaluate capabilities and synchronize them directly to the CubeSat model.

        Updates satellite.capabilities flags (sensing, relay, navigation, compute,
        storage, maneuvering) so all downstream telemetry frames accurately reflect
        the capability graph.
        """
        report = cls.evaluate_satellite(satellite)

        # Sync boolean flags for schema compatibility (only True if fully OPERATIONAL)
        satellite.capabilities.sensing = (report.capabilities[CapabilityType.SENSING] == CapabilityStatus.OPERATIONAL)
        satellite.capabilities.relay = (report.capabilities[CapabilityType.RELAY] == CapabilityStatus.OPERATIONAL)
        satellite.capabilities.navigation = (report.capabilities[CapabilityType.NAVIGATION] == CapabilityStatus.OPERATIONAL)
        satellite.capabilities.compute = (report.capabilities[CapabilityType.COMPUTE] == CapabilityStatus.OPERATIONAL)
        satellite.capabilities.storage = (report.capabilities[CapabilityType.STORAGE] == CapabilityStatus.OPERATIONAL)
        satellite.capabilities.maneuvering = (report.capabilities[CapabilityType.MANEUVERING] == CapabilityStatus.OPERATIONAL)

        return report
