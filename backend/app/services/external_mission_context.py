from __future__ import annotations

import json
import math
import ssl
from datetime import datetime, timezone
from typing import Any, Dict, List
from urllib.request import Request, urlopen

import certifi
import networkx as nx


EONET_URL = (
    "https://eonet.gsfc.nasa.gov/api/v3/events/geojson"
    "?status=open&days=14&limit=30"
)

USGS_URL = (
    "https://earthquake.usgs.gov/earthquakes/feed/v1.0/"
    "summary/2.5_day.geojson"
)

_observation_tasks: Dict[str, Dict[str, Any]] = {}
_task_counter = 0


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _fetch_json(url: str, timeout: float = 8.0) -> Dict[str, Any]:
    request = Request(
        url,
        headers={
            "User-Agent": "ASTRANET/0.1 research-digital-twin",
            "Accept": "application/json",
        },
    )

    context = ssl.create_default_context(
        cafile=certifi.where()
    )

    with urlopen(
        request,
        timeout=timeout,
        context=context,
    ) as response:
        return json.loads(
            response.read().decode("utf-8")
        )


def _safe_fetch(url: str) -> Dict[str, Any]:
    try:
        return {
            "ok": True,
            "data": _fetch_json(url),
            "error": None,
        }
    except Exception as exc:
        return {
            "ok": False,
            "data": None,
            "error": str(exc),
        }


def _eonet_severity(category: str) -> str:
    value = category.lower()

    if "wildfire" in value:
        return "HIGH"

    if "volcano" in value:
        return "HIGH"

    if "storm" in value or "cyclone" in value:
        return "HIGH"

    return "MEDIUM"


def _earthquake_severity(
    magnitude: Any,
) -> str:
    try:
        mag = float(magnitude)
    except (TypeError, ValueError):
        return "LOW"

    if mag >= 6.0:
        return "CRITICAL"

    if mag >= 5.0:
        return "HIGH"

    if mag >= 4.0:
        return "MEDIUM"

    return "LOW"


def _normalize_eonet(
    data: Dict[str, Any],
) -> List[Dict[str, Any]]:
    output: List[Dict[str, Any]] = []

    for feature in data.get("features", []):
        geometry = feature.get("geometry") or {}

        if geometry.get("type") != "Point":
            continue

        coordinates = (
            geometry.get("coordinates") or []
        )

        if len(coordinates) < 2:
            continue

        properties = (
            feature.get("properties") or {}
        )

        categories = (
            properties.get("categories") or []
        )

        category = (
            categories[0].get("title")
            if categories
            else "Natural Event"
        )

        magnitude_value = properties.get(
            "magnitudeValue"
        )

        magnitude_unit = properties.get(
            "magnitudeUnit"
        )

        magnitude_label = None

        if magnitude_value is not None:
            magnitude_label = str(
                magnitude_value
            )

            if magnitude_unit:
                magnitude_label += (
                    f" {magnitude_unit}"
                )

        output.append(
            {
                "id": str(
                    properties.get("id")
                    or feature.get("id")
                    or f"EONET-{len(output) + 1}"
                ),
                "source": "NASA_EONET",
                "title": (
                    properties.get("title")
                    or "NASA EONET Event"
                ),
                "category": category,
                "latitude": float(
                    coordinates[1]
                ),
                "longitude": float(
                    coordinates[0]
                ),
                "timestamp": properties.get(
                    "date"
                ),
                "magnitudeLabel": (
                    magnitude_label
                ),
                "severity": (
                    _eonet_severity(category)
                ),
            }
        )

    return output


def _normalize_usgs(
    data: Dict[str, Any],
) -> List[Dict[str, Any]]:
    output: List[Dict[str, Any]] = []

    for feature in data.get("features", []):
        geometry = feature.get("geometry") or {}

        coordinates = (
            geometry.get("coordinates") or []
        )

        if (
            geometry.get("type") != "Point"
            or len(coordinates) < 2
        ):
            continue

        properties = (
            feature.get("properties") or {}
        )

        magnitude = properties.get("mag")
        timestamp_ms = properties.get("time")

        timestamp = None

        if isinstance(
            timestamp_ms,
            (int, float),
        ):
            timestamp = datetime.fromtimestamp(
                timestamp_ms / 1000,
                tz=timezone.utc,
            ).isoformat()

        output.append(
            {
                "id": str(
                    feature.get("id")
                    or properties.get("code")
                    or f"USGS-{len(output) + 1}"
                ),
                "source": "USGS",
                "title": (
                    properties.get("place")
                    or "USGS Earthquake"
                ),
                "category": "Earthquake",
                "latitude": float(
                    coordinates[1]
                ),
                "longitude": float(
                    coordinates[0]
                ),
                "timestamp": timestamp,
                "magnitudeLabel": (
                    f"M {float(magnitude):.1f}"
                    if isinstance(
                        magnitude,
                        (int, float),
                    )
                    else None
                ),
                "severity": (
                    _earthquake_severity(
                        magnitude
                    )
                ),
            }
        )

    return output


def get_live_context() -> Dict[str, Any]:
    nasa = _safe_fetch(EONET_URL)
    usgs = _safe_fetch(USGS_URL)

    events: List[Dict[str, Any]] = []

    if nasa["ok"]:
        events.extend(
            _normalize_eonet(
                nasa["data"]
            )[:15]
        )

    if usgs["ok"]:
        events.extend(
            _normalize_usgs(
                usgs["data"]
            )[:15]
        )

    return {
        "generatedAt": _utc_now(),
        "classification":
            "REAL_WORLD_MISSION_CONTEXT",
        "disclaimer": (
            "NASA EONET and USGS provide "
            "real-world external mission context. "
            "ASTRANET spacecraft telemetry, "
            "assignment and task execution remain "
            "simulated digital-twin outputs."
        ),
        "sourceStatus": {
            "nasaEonet": {
                "ok": nasa["ok"],
                "error": nasa["error"],
            },
            "usgs": {
                "ok": usgs["ok"],
                "error": usgs["error"],
            },
        },
        "eventCount": len(events),
        "events": events,
    }


def _haversine_km(
    lat1: float,
    lon1: float,
    lat2: float,
    lon2: float,
) -> float:
    radius_km = 6371.0

    p1 = math.radians(lat1)
    p2 = math.radians(lat2)

    dp = math.radians(lat2 - lat1)
    dl = math.radians(lon2 - lon1)

    a = (
        math.sin(dp / 2) ** 2
        + math.cos(p1)
        * math.cos(p2)
        * math.sin(dl / 2) ** 2
    )

    return radius_km * (
        2
        * math.atan2(
            math.sqrt(a),
            math.sqrt(1 - a),
        )
    )


def _shortest_relay_path(
    orchestrator: Any,
    source_id: str,
    coordinator_id: str | None,
) -> List[str]:
    if not coordinator_id:
        return [source_id]

    if source_id == coordinator_id:
        return [source_id]

    graph = orchestrator.network.graph

    if (
        source_id not in graph
        or coordinator_id not in graph
    ):
        return [source_id]

    try:
        return list(
            nx.shortest_path(
                graph,
                source=source_id,
                target=coordinator_id,
            )
        )
    except (
        nx.NetworkXNoPath,
        nx.NodeNotFound,
    ):
        return [source_id]


def create_observation_task(
    orchestrator: Any,
    event: Dict[str, Any],
) -> Dict[str, Any]:
    global _task_counter

    coordinator = orchestrator.coordinator

    coordinator_id = (
        coordinator.id
        if coordinator is not None
        else None
    )

    candidates: List[Dict[str, Any]] = []

    for satellite in orchestrator.satellites:
        telemetry = satellite.to_dict()

        if telemetry["state"] in {
            "FAILED",
            "ISOLATED",
        }:
            continue

        capabilities = (
            telemetry.get("capabilities") or {}
        )

        if not capabilities.get(
            "sensing",
            False,
        ):
            continue

        position = (
            telemetry.get("position") or {}
        )

        lat = position.get("lat")
        lon = position.get("lon")

        if not isinstance(
            lat,
            (int, float),
        ):
            continue

        if not isinstance(
            lon,
            (int, float),
        ):
            continue

        distance = _haversine_km(
            float(lat),
            float(lon),
            float(event["latitude"]),
            float(event["longitude"]),
        )

        relay_path = _shortest_relay_path(
            orchestrator,
            telemetry["id"],
            coordinator_id,
        )

        network_reachable = (
            coordinator_id is None
            or telemetry["id"]
            == coordinator_id
            or (
                len(relay_path) > 1
                and relay_path[-1]
                == coordinator_id
            )
        )

        candidates.append(
            {
                "satelliteId":
                    telemetry["id"],
                "distanceKm": distance,
                "battery":
                    telemetry.get(
                        "battery",
                        0,
                    ),
                "trust":
                    telemetry.get(
                        "trust",
                        0,
                    ),
                "relayPath":
                    relay_path,
                "networkReachable":
                    network_reachable,
            }
        )

    if not candidates:
        raise ValueError(
            "No operational sensing spacecraft "
            "are currently available"
        )

    candidates.sort(
        key=lambda item: (
            0
            if item["networkReachable"]
            else 1,
            item["distanceKm"],
            -item["battery"],
            -item["trust"],
        )
    )

    selected = candidates[0]

    _task_counter += 1

    task_id = (
        f"OBS-{_task_counter:04d}"
    )

    sim_time = (
        orchestrator.clock.elapsed_seconds
    )

    task = {
        "taskId": task_id,
        "createdAt": _utc_now(),
        "createdSimSec": sim_time,
        "startedSimSec": None,
        "targetCompletionSimSec": None,
        "completedSimSec": None,
        "plannedDurationSec": 12.0,
        "progressPct": 0.0,
        "status": "PLANNED",
        "classification":
            "SIMULATED_MISSION_TASK",
        "missionType":
            "EARTH_OBSERVATION",
        "priority": event.get(
            "priority",
            "HIGH",
        ),
        "assignedSatelliteId":
            selected["satelliteId"],
        "candidateDistanceKm": round(
            selected["distanceKm"],
            1,
        ),
        "relayPath":
            selected["relayPath"],
        "networkReachable":
            selected["networkReachable"],
        "reason": (
            "Selected from operational sensing "
            "CubeSats using network reachability, "
            "ground-track distance, battery and "
            "trust within the ASTRANET digital twin."
        ),
        "event": {
            "id": event["eventId"],
            "source": event["source"],
            "title": event["title"],
            "category":
                event["category"],
            "latitude":
                event["latitude"],
            "longitude":
                event["longitude"],
            "timestamp":
                event.get("timestamp"),
            "magnitudeLabel":
                event.get(
                    "magnitudeLabel"
                ),
        },
    }

    _observation_tasks[task_id] = task

    return dict(task)


def execute_observation_task(
    orchestrator: Any,
    task_id: str,
) -> Dict[str, Any]:
    refresh_observation_tasks(
        orchestrator
    )

    task = _observation_tasks.get(
        task_id
    )

    if task is None:
        raise KeyError(
            f"Observation task "
            f"'{task_id}' not found"
        )

    if task["status"] in {
        "EXECUTING",
        "COMPLETED",
    }:
        return dict(task)

    satellite = orchestrator.get_satellite(
        task["assignedSatelliteId"]
    )

    if satellite is None:
        raise ValueError(
            "Assigned spacecraft "
            "no longer exists"
        )

    if satellite.state.value in {
        "FAILED",
        "ISOLATED",
    }:
        raise ValueError(
            "Assigned spacecraft is "
            "not operational"
        )

    if not satellite.capabilities.sensing:
        raise ValueError(
            "Assigned spacecraft sensing "
            "capability is unavailable"
        )

    start = (
        orchestrator.clock.elapsed_seconds
    )

    task["status"] = "EXECUTING"
    task["startedSimSec"] = start

    task["targetCompletionSimSec"] = (
        start
        + task["plannedDurationSec"]
    )

    task["progressPct"] = 0.0

    satellite.mission_state = (
        "OBSERVATION_ACTIVE"
    )

    satellite.autonomy_status = (
        f"Executing autonomous observation "
        f"task {task_id}"
    )

    return dict(task)


def refresh_observation_tasks(
    orchestrator: Any,
) -> None:
    sim_time = (
        orchestrator.clock.elapsed_seconds
    )

    for task in _observation_tasks.values():
        if task["status"] != "EXECUTING":
            continue

        satellite = (
            orchestrator.get_satellite(
                task["assignedSatelliteId"]
            )
        )

        if (
            satellite is None
            or satellite.state.value
            in {"FAILED", "ISOLATED"}
            or not satellite.capabilities.sensing
        ):
            task["status"] = "ABORTED"
            task["progressPct"] = 0.0

            continue

        start = task["startedSimSec"]
        target = task[
            "targetCompletionSimSec"
        ]

        duration = max(
            task["plannedDurationSec"],
            0.001,
        )

        progress = (
            (sim_time - start)
            / duration
            * 100
        )

        task["progressPct"] = round(
            min(
                100.0,
                max(0.0, progress),
            ),
            1,
        )

        if sim_time >= target:
            task["status"] = "COMPLETED"
            task["progressPct"] = 100.0

            task["completedSimSec"] = (
                sim_time
            )

            if satellite.state.value == "NOMINAL":
                satellite.mission_state = (
                    "NOMINAL"
                )

                satellite.autonomy_status = (
                    f"Observation task "
                    f"{task['taskId']} completed"
                )


def get_observation_tasks(
    orchestrator: Any,
) -> List[Dict[str, Any]]:
    refresh_observation_tasks(
        orchestrator
    )

    return [
        dict(task)
        for task in sorted(
            _observation_tasks.values(),
            key=lambda value:
                value["createdSimSec"],
            reverse=True,
        )
    ]
