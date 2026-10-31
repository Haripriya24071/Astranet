import json
import math
from datetime import datetime, timezone
from pathlib import Path

from sgp4.api import Satrec, jday


EARTH_A_KM = 6378.137
EARTH_E2 = 6.69437999014e-3

DEFAULT_MAX_AGE_HOURS = 48.0

CACHE_FILE = (
    Path(__file__).resolve().parents[2]
    / "starlink_latest_page.json"
)


def gmst_radians(jd: float) -> float:
    t = (jd - 2451545.0) / 36525.0

    gmst_deg = (
        280.46061837
        + 360.98564736629 * (jd - 2451545.0)
        + 0.000387933 * t * t
        - (t * t * t) / 38710000.0
    )

    return math.radians(gmst_deg % 360.0)


def teme_to_ecef(position, jd):
    x, y, z = position

    theta = gmst_radians(jd)

    cos_t = math.cos(theta)
    sin_t = math.sin(theta)

    return (
        cos_t * x + sin_t * y,
        -sin_t * x + cos_t * y,
        z,
    )


def ecef_to_geodetic(x, y, z):
    lon = math.atan2(y, x)

    p = math.sqrt(
        x * x + y * y
    )

    lat = math.atan2(
        z,
        p * (1.0 - EARTH_E2),
    )

    for _ in range(8):
        sin_lat = math.sin(lat)

        n = EARTH_A_KM / math.sqrt(
            1.0
            - EARTH_E2
            * sin_lat
            * sin_lat
        )

        alt = (
            p / math.cos(lat)
            - n
        )

        lat = math.atan2(
            z,
            p
            * (
                1.0
                - EARTH_E2
                * n
                / (n + alt)
            ),
        )

    sin_lat = math.sin(lat)

    n = EARTH_A_KM / math.sqrt(
        1.0
        - EARTH_E2
        * sin_lat
        * sin_lat
    )

    alt = (
        p / math.cos(lat)
        - n
    )

    return (
        math.degrees(lat),
        math.degrees(lon),
        alt,
    )


def parse_epoch(raw: str) -> datetime:
    epoch = datetime.fromisoformat(
        raw.replace(
            "Z",
            "+00:00",
        )
    )

    if epoch.tzinfo is None:
        epoch = epoch.replace(
            tzinfo=timezone.utc
        )

    return epoch


def propagate_record(
    record: dict,
    now: datetime,
    max_age_hours: float,
):
    epoch = parse_epoch(
        record["date"]
    )

    age_hours = (
        now - epoch
    ).total_seconds() / 3600

    if age_hours > max_age_hours:
        return None, "STALE"

    satellite = Satrec.twoline2rv(
        record["line1"],
        record["line2"],
    )

    second = (
        now.second
        + now.microsecond
        / 1_000_000
    )

    jd, fraction = jday(
        now.year,
        now.month,
        now.day,
        now.hour,
        now.minute,
        second,
    )

    error, position, velocity = (
        satellite.sgp4(
            jd,
            fraction,
        )
    )

    if error != 0:
        return None, "SGP4_ERROR"

    ecef = teme_to_ecef(
        position,
        jd + fraction,
    )

    lat, lon, alt = (
        ecef_to_geodetic(
            *ecef
        )
    )

    speed = math.sqrt(
        velocity[0] ** 2
        + velocity[1] ** 2
        + velocity[2] ** 2
    )

    return {
        "id": str(
            record["satelliteId"]
        ),
        "noradId":
            record["satelliteId"],
        "name":
            record["name"],
        "constellation":
            "STARLINK",
        "source":
            "PUBLIC_TLE",
        "tleEpoch":
            epoch.isoformat(),
        "tleAgeHours":
            round(age_hours, 2),
        "position": {
            "lat":
                round(lat, 5),
            "lon":
                round(lon, 5),
            "altKm":
                round(alt, 2),
        },
        "velocity": {
            "vx":
                round(
                    velocity[0],
                    4,
                ),
            "vy":
                round(
                    velocity[1],
                    4,
                ),
            "vz":
                round(
                    velocity[2],
                    4,
                ),
            "speedKmS":
                round(
                    speed,
                    4,
                ),
        },
        "teme": {
            "x":
                round(
                    position[0],
                    2,
                ),
            "y":
                round(
                    position[1],
                    2,
                ),
            "z":
                round(
                    position[2],
                    2,
                ),
        },
    }, None


def get_live_orbits(
    limit: int = 100,
    max_age_hours: float = DEFAULT_MAX_AGE_HOURS,
):
    if not CACHE_FILE.exists():
        raise FileNotFoundError(
            f"Orbit cache missing: {CACHE_FILE}"
        )

    with CACHE_FILE.open(
        "r",
        encoding="utf-8",
    ) as file:
        payload = json.load(file)

    records = payload.get(
        "member",
        [],
    )

    now = datetime.now(
        timezone.utc
    )

    satellites = []

    stale_count = 0
    sgp4_error_count = 0

    for record in records:
        result, reason = (
            propagate_record(
                record,
                now,
                max_age_hours,
            )
        )

        if reason == "STALE":
            stale_count += 1
            continue

        if reason == "SGP4_ERROR":
            sgp4_error_count += 1
            continue

        if result is not None:
            satellites.append(
                result
            )

        if (
            len(satellites)
            >= limit
        ):
            break

    return {
        "mode":
            "REAL_ORBIT_SHADOW",
        "constellation":
            "STARLINK",
        "source":
            "PUBLIC_TLE",
        "propagator":
            "SGP4",
        "propagatedUtc":
            now.isoformat(),
        "maxTleAgeHours":
            max_age_hours,
        "inputRecords":
            len(records),
        "freshSatellites":
            len(satellites),
        "staleSkipped":
            stale_count,
        "sgp4Failed":
            sgp4_error_count,
        "satellites":
            satellites,
    }
