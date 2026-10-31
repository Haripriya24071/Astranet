import json
import math
from datetime import datetime, timezone

from sgp4.api import Satrec, jday


EARTH_A_KM = 6378.137
EARTH_E2 = 6.69437999014e-3

MAX_TLE_AGE_HOURS = 48


def gmst_radians(jd):
    t = (jd - 2451545.0) / 36525.0

    gmst_deg = (
        280.46061837
        + 360.98564736629
        * (jd - 2451545.0)
        + 0.000387933
        * t * t
        - (t * t * t)
        / 38710000.0
    )

    return math.radians(
        gmst_deg % 360.0
    )


def teme_to_ecef(
    position,
    jd,
):
    x, y, z = position

    theta = gmst_radians(jd)

    cos_t = math.cos(theta)
    sin_t = math.sin(theta)

    return (
        cos_t * x
        + sin_t * y,
        -sin_t * x
        + cos_t * y,
        z,
    )


def ecef_to_geodetic(
    x,
    y,
    z,
):
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


def propagate(record, now):
    epoch = datetime.fromisoformat(
        record["date"].replace(
            "Z",
            "+00:00",
        )
    )

    if epoch.tzinfo is None:
        epoch = epoch.replace(
            tzinfo=timezone.utc
        )

    age_hours = (
        now - epoch
    ).total_seconds() / 3600

    if age_hours > MAX_TLE_AGE_HOURS:
        return None

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
        return None

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
        "id":
            record["satelliteId"],

        "name":
            record["name"],

        "lat":
            lat,

        "lon":
            lon,

        "alt":
            alt,

        "speed":
            speed,

        "ageHours":
            age_hours,
    }


with open(
    "backend/starlink_batch_50.json",
    "r",
    encoding="utf-8",
) as f:
    payload = json.load(f)


records = payload.get(
    "member",
    [],
)

now = datetime.now(
    timezone.utc
)

results = []

stale = 0
failed = 0

for record in records:
    result = propagate(
        record,
        now,
    )

    if result is None:
        epoch = datetime.fromisoformat(
            record["date"].replace(
                "Z",
                "+00:00",
            )
        )

        if epoch.tzinfo is None:
            epoch = epoch.replace(
                tzinfo=timezone.utc
            )

        age = (
            now - epoch
        ).total_seconds() / 3600

        if age > MAX_TLE_AGE_HOURS:
            stale += 1
        else:
            failed += 1

        continue

    results.append(result)


print()
print("ASTRANET REAL ORBIT BATCH")
print("=========================")
print()

print("INPUT RECORDS :", len(records))
print("FRESH + VALID :", len(results))
print("STALE SKIPPED :", stale)
print("SGP4 FAILED   :", failed)
print("PROP UTC      :", now.isoformat())

print()
print("FIRST 20 REAL POSITIONS")
print("-----------------------")

for sat in results[:20]:
    print(
        f"{sat['name']:<24} "
        f"LAT {sat['lat']:>8.3f}°  "
        f"LON {sat['lon']:>9.3f}°  "
        f"ALT {sat['alt']:>7.1f} km  "
        f"SPD {sat['speed']:.3f} km/s  "
        f"AGE {sat['ageHours']:.1f}h"
    )

print()

if results:
    print(
        "✓ MULTI-SATELLITE REAL ORBIT PROPAGATION WORKING"
    )
else:
    print(
        "✗ NO FRESH SATELLITES FOUND"
    )
