"""ASTRANET — Cascading Blast Radius (N-1 Domino Risk Halo Engine).

Evaluates the hypothetical sudden loss (N-1 failure) of an individual satellite agent.
Calculates:
1. Severed optical/RF crosslinks (ISL).
2. Immediate 1-hop domino peers and their predicted traffic rerouting surge.
3. Graph partitioning / islanding risk (connected components delta).
4. Ground footprint observation blindspot (sub-satellite footprint loss).
5. Recommended autonomous rerouting and failover candidate.
"""

from dataclasses import dataclass, field
from typing import Dict, List, Any, Optional
import math
import networkx as nx


def _get_region_label(lat: float, lng: float) -> str:
    """Provide a human-readable geographic label for sub-satellite footprint."""
    if lat > 60:
        return "Arctic Circle Monitoring Corridor"
    if lat < -60:
        return "Antarctic Scientific Sector"
    if -30 <= lat <= 30 and -80 <= lng <= -30:
        return "South America & Amazon Basin"
    if 15 <= lat <= 60 and -130 <= lng <= -60:
        return "North American Transcontinental"
    if 30 <= lat <= 70 and -10 <= lng <= 45:
        return "European & Mediterranean Sector"
    if -35 <= lat <= 35 and 10 <= lng <= 55:
        return "African Continental Corridor"
    if 0 <= lat <= 55 and 60 <= lng <= 145:
        return "Asia-Pacific Geospatial Grid"
    if -45 <= lat <= 0 and 50 <= lng <= 110:
        return "Indian Ocean Maritime Route"
    return "Mid-Ocean High-Bandwidth Transit Area"


def calculate_blast_radius(swarm: Any, target_satellite_id: str) -> Dict[str, Any]:
    """Compute N-1 failure cascading blast radius for a given satellite.

    Args:
        swarm: SwarmConstellationOrchestrator instance.
        target_satellite_id: Identifier of the target satellite (e.g. 'SAT-07').

    Returns:
        Structured blast radius assessment payload for UI rendering and autonomous risk scoring.
    """
    if hasattr(swarm, "_satellites_map") and swarm._satellites_map:
        satellites = swarm._satellites_map
    else:
        sats_list = getattr(swarm, "satellites", [])
        if isinstance(sats_list, dict):
            satellites = sats_list
        else:
            satellites = {s.id: s for s in sats_list}

    if target_satellite_id not in satellites:
        raise KeyError(f"Satellite '{target_satellite_id}' not found in active swarm constellation")

    target_sat = satellites[target_satellite_id]
    network = swarm.network
    graph: nx.Graph = network.graph

    # 1. Severed Links
    severed_links: List[List[str]] = []
    connected_peers: List[str] = []
    if target_satellite_id in graph:
        for u, v in graph.edges(target_satellite_id):
            severed_links.append([u, v])
            peer_id = v if u == target_satellite_id else u
            connected_peers.append(peer_id)

    # 2. Domino Peers (1-Hop Impact & Traffic Surge)
    affected_peers: List[Dict[str, Any]] = []
    for peer_id in connected_peers:
        if peer_id in satellites:
            peer_sat = satellites[peer_id]
            current_degree = graph.degree(peer_id) if peer_id in graph else 0
            new_degree = max(0, current_degree - 1)
            # Projected load surge on remaining links
            if new_degree == 0:
                surge_pct = 100.0  # Node completely isolated
                status = "ISOLATED_RISK"
            else:
                surge_pct = round(min(150.0, (1.0 / max(1, new_degree)) * 55.0), 1)
                status = "ELEVATED_RELAY_LOAD"

            affected_peers.append({
                "satelliteId": peer_id,
                "name": peer_sat.name,
                "role": peer_sat.role.value if hasattr(peer_sat.role, "value") else str(peer_sat.role),
                "state": peer_sat.state.value if hasattr(peer_sat.state, "value") else str(peer_sat.state),
                "battery": round(peer_sat.battery, 1),
                "currentLinks": current_degree,
                "postFailureLinks": new_degree,
                "projectedLoadSurgePct": surge_pct,
                "impactStatus": status,
            })

    # Sort affected peers by highest load surge
    affected_peers.sort(key=lambda x: x["projectedLoadSurgePct"], reverse=True)

    # 3. Constellation Graph Partitioning / Islanding
    components_before = nx.number_connected_components(graph) if graph.number_of_nodes() > 0 else 1
    g_sim = graph.copy()
    if target_satellite_id in g_sim:
        g_sim.remove_node(target_satellite_id)
    components_after = nx.number_connected_components(g_sim) if g_sim.number_of_nodes() > 0 else 1

    partition_risk = components_after > components_before
    new_islands_created = max(0, components_after - components_before)

    # 4. Ground Observation Footprint Loss
    if hasattr(target_sat, "position_eci_m"):
        pos = target_sat.position_eci_m
    elif hasattr(target_sat, "current_state"):
        pos = target_sat.current_state.r_eci
    else:
        pos = [0.0, 0.0, 0.0]

    x, y, z = float(pos[0]), float(pos[1]), float(pos[2])
    r = math.sqrt(x*x + y*y + z*z)
    if r > 1000.0:
        lat = round(math.degrees(math.asin(z / r)), 2)
        lng = round(math.degrees(math.atan2(y, x)), 2)
        # Horizon visibility distance: d = sqrt(r^2 - R_earth^2)
        r_earth = 6378137.0
        horizon_m = math.sqrt(max(0.0, r*r - r_earth*r_earth))
        footprint_radius_km = round(min(2200.0, horizon_m / 1000.0 * 0.5), 1)
    else:
        lat = 0.0
        lng = 0.0
        footprint_radius_km = 1250.0

    region_label = _get_region_label(lat, lng)

    # 5. Severity Rating
    is_coordinator = (
        (hasattr(target_sat.role, "value") and target_sat.role.value == "COORDINATOR")
        or target_sat.role == "COORDINATOR"
    )
    if is_coordinator:
        severity = "CRITICAL"
        risk_score = 94
    elif partition_risk or any(p["impactStatus"] == "ISOLATED_RISK" for p in affected_peers):
        severity = "HIGH"
        risk_score = 78
    elif len(severed_links) >= 2:
        severity = "MEDIUM"
        risk_score = 52
    else:
        severity = "LOW"
        risk_score = 25

    # 6. Autonomous Mitigation Recommendation
    if is_coordinator:
        # Pick healthiest peer as failover
        best_failover = next((p["satelliteId"] for p in affected_peers if p["role"] == "RELAY"), "SAT-08")
        recommendation = f"Initiate Byzantine consensus failover; transfer leadership to {best_failover}."
    elif partition_risk:
        recommendation = "Reconfigure Walker Delta adjacent plane crosslinks to bridge constellation partition."
    elif affected_peers:
        highest_load = affected_peers[0]["satelliteId"]
        recommendation = f"Throttle high-bandwidth observation downlink through {highest_load} to avoid buffer overflow."
    else:
        recommendation = "Rebalance standard ISL routing table across surviving plane neighbors."

    return {
        "targetSatelliteId": target_satellite_id,
        "targetName": target_sat.name,
        "targetRole": target_sat.role.value if hasattr(target_sat.role, "value") else str(target_sat.role),
        "severity": severity,
        "riskScore": risk_score,
        "severedLinksCount": len(severed_links),
        "severedLinks": severed_links,
        "affectedPeersCount": len(affected_peers),
        "affectedPeers": affected_peers,
        "partitionRisk": partition_risk,
        "islandsCreated": new_islands_created,
        "blindspot": {
            "centerLat": lat,
            "centerLng": lng,
            "radiusKm": footprint_radius_km,
            "region": region_label,
            "description": f"Hypothetical ground sensor outage over {region_label} (radius {footprint_radius_km} km).",
        },
        "autonomousMitigation": recommendation,
    }
