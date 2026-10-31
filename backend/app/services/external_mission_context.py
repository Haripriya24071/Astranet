from __future__ import annotations

import json
import math
import ssl
from datetime import datetime, timezone
from typing import Any, Dict, List
from urllib.request import Request, urlopen

import certifi


EONET_URL = (
    "https://eonet.gsfc.nasa.gov/api/v3/events/geojson"
    "?status=open&days=14&limit=30"
)

USGS_URL = (
    "https://earthquake.usgs.gov/earthquakes/feed/v1.0/"
    "summary/2.5_day.geojson"
)

_observation_tasks: List[Dict[str, Any]] = []


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

    context = ssl.create_default_context(cafile=certifi.where())

    with urlopen(
        request,
        timeout=timeout,
        context=context,
    ) as response:
        return json.loads(response.read().decode("utf-8"))


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


def _severity_for_eonet(category: str) -> str:
    value = category.lower()

    if "wildfire" in value or "volcano" in value:
        return "HIGH"

    if "storm" in value:
        return "HIGH"

    return "MEDIUM"


def _severity_for_earthquake(magnitude: Any) -> str:
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


def _normalize_eonet(data: Dict[str, Any]) -> List[Dict[str, Any]]:
    events: List[Dict[str, Any]] = []

    for feature in data.get("features", []):
        geometry = feature.get("geometry") or {}

        if geometry.get("type") != "Point":
            continue

        coordinates = geometry.get("coordinates") or []

        if len(coordinates) < 2:
            continue

        properties = feature.get("properties") or {}
        categories = properties.get("categories") or []

        category = (
            categories[0].get("title")
            if categories
            else "Natural Event"
        )

        magnitude_value = properties.get("magnitudeValue")
        magnitude_unit = properties.get("magnitudeUnit")

        magnitude_label = None

        if magnitude_value is not None:
            magnitude_label = str(magnitude_value)

            if magnitude_unit:
                magnitude_label += f" {magnitude_unit}"

        events.append(
            {
                "id": str(
                    properties.get("id")
                    or feature.get("id")
                    or f"EONET-{len(events) + 1}"
                ),
                "source": "NASA_EONET",
                "title": properties.get("title")
                or "NASA EONET Event",
                "category": category,
                "latitude": float(coordinates[1]),
                "longitude": float(coordinates[0]),
                "timestamp": properties.get("date"),
                "magnitudeLabel": magnitude_label,
                "severity": _severity_for_eonet(category),
            }
        )

    return events


def _normalize_usgs(data: Dict[str, Any]) -> List[Dict[str, Any]]:
    events: List[Dict[str, Any]] = []

    for feature in data.get("features", []):
        geometry = feature.get("geometry") or {}
        coordinates = geometry.get("coordinates") or []

        if (
            geometry.get("type") != "Point"
            or len(coordinates) < 2
        ):
            continue

        properties = feature.get("properties") or {}
        magnitude = properties.get("mag")
        timestamp_ms = properties.get("time")

        timestamp = None

        if isinstance(timestamp_ms, (int, float)):
            timestamp = datetime.fromtimestamp(
                timestamp_ms / 1000,
                tz=timezone.utc,
            ).isoformat()

        events.append(
            {
                "id": str(
                    feature.get("id")
                    or properties.get("code")
                    or f"USGS-{len(events) + 1}"
                ),
                "source": "USGS",
                "title": properties.get("place")
                or "USGS Earthquake",
                "category": "Earthquake",
                "latitude": float(coordinates[1]),
                "longitude": float(coordinates[0]),
                "timestamp": timestamp,
                "magnitudeLabel": (
                    f"M {float(magnitude):.1f}"
                    if isinstance(magnitude, (int, float))
                    else None
                ),
                "severity": _severity_for_earthquake(magnitude),
            }
        )

    return events


def get_live_context() -> Dict[str, Any]:
    eonet = _safe_fetch(EONET_URL)
    usgs = _safe_fetch(USGS_URL)

    events: List[Dict[str, Any]] = []

    if eonet["ok"]:
        events.extend(
            _normalize_eonet(eonet["data"])[:20]
        )

    if usgs["ok"]:
        events.extend(
            _normalize_usgs(usgs["data"])[:20]
        )

    return {
        "generatedAt": _utc_now(),
        "classification": "REAL_WORLD_MISSION_CONTEXT",
        "disclaimer": (
            "External NASA EONET and USGS feeds provide "
            "real-world mission context. ASTRANET spacecraft "
            "telemetry and observation tasking remain simulated."
        ),
        "sourceStatus": {
            "nasaEonet": {
                "ok": eonet["ok"],
                "error": eonet["error"],
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

    phi1 = math.radians(lat1)
    phi2 = math.radians(lat2)

    d_phi = math.radians(lat2 - lat1)
    d_lambda = math.radians(lon2 - lon1)

    a = (
        math.sin(d_phi / 2) ** 2
        + math.cos(phi1)
        * math.cos(phi2)
        * math.sin(d_lambda / 2) ** 2
    )

    return radius_km * (
        2
        * math.atan2(
            math.sqrt(a),
            math.sqrt(1 - a),
        )
    )


def create_observation_task(
    orchestrator: Any,
    event: Dict[str, Any],
) -> Dict[str, Any]:
    candidates: List[Dict[str, Any]] = []

    for satellite in orchestrator.satellites:
        telemetry = satellite.to_dict()

        if telemetry.get("state") in {
            "FAILED",
            "ISOLATED",
        }:
            continue

        capabilities = telemetry.get("capabilities") or {}

        if not capabilities.get("sensing", False):
            continue

        position = telemetry.get("position") or {}

        lat = position.get("lat")
        lon = position.get("lon")

        if not isinstance(lat, (int, float)):
            continue

        if not isinstance(lon, (int, float)):
            continue

        distance_km = _haversine_km(
            float(lat),
            float(lon),
            float(event["latitude"]),
            float(event["longitude"]),
        )

        candidates.append(
            {
                "satelliteId": telemetry["id"],
                "distanceKm": distance_km,
                "battery": telemetry.get("battery", 0),
                "trust": telemetry.get("trust", 0),
            }
        )

    if not candidates:
        raise ValueError(
            "No operational sensing spacecraft are available"
        )

    candidates.sort(
        key=lambda item: (
            item["distanceKm"],
            -item["battery"],
            -item["trust"],
        )
    )

    selected = candidates[0]

    coordinator = orchestrator.coordinator
    coordinator_id = (
        coordinator.id
        if coordinator is not None
        else None
    )

    relay_path = [selected["satelliteId"]]

    if (
        coordinator_id
        and coordinator_id != selected["satelliteId"]
    ):
        relay_path.append(coordinator_id)

    task = {
        "taskId": f"OBS-{len(_observation_tasks) + 1:04d}",
        "createdAt": _utc_now(),
        "status": "PLANNED",
        "classification": "SIMULATED_MISSION_TASK",
        "missionType": "EARTH_OBSERVATION",
        "priority": event.get("priority", "HIGH"),
        "assignedSatelliteId": selected["satelliteId"],
        "candidateDistanceKm": round(
            selected["distanceKm"],
            1,
        ),
        "relayPath": relay_path,
        "reason": (
            "Nearest currently operational CubeSat with "
            "sensing capability in the ASTRANET digital twin"
        ),
        "event": {
            "id": event["eventId"],
            "source": event["source"],
            "title": event["title"],
            "category": event["category"],
            "latitude": event["latitude"],
            "longitude": event["longitude"],
            "timestamp": event.get("timestamp"),
            "magnitudeLabel": event.get(
                "magnitudeLabel"
            ),
        },
    }

    _observation_tasks.insert(0, task)

    return task


def get_observation_tasks() -> List[Dict[str, Any]]:
    return list(_observation_tasks)
