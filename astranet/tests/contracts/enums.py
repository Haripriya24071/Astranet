MISSION_STATES = ["NOMINAL", "DEGRADED-A", "DEGRADED-B", "SURVIVAL", "MISSION-LOST"]

FAILURE_TYPES = [
    "node_loss", "comms_failure", "propulsion_failure", "navigation_degradation",
    "power_degradation", "network_partition", "stale_state",
    "spoofed_telemetry", "byzantine_behavior",
   ]

ROLES = [
    "sensing_node", "relay", "navigation_aid", "coordinator",
    "compute_storage_support", "degraded_contributor",
]