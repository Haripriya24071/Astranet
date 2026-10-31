import json
import math
import urllib.request
from datetime import datetime, timezone

from sgp4 import omm
from sgp4.api import Satrec, jday


CELESTRAK_URL = (
    "https://celestrak.org/NORAD/elements/"
    "gp.php?CATNR=44714&FORMAT=JSON"
)

EARTH_A = 6378.137
EARTH_E2 = 6.69437999014e-3


def gmst_radians(jd):
    t = (jd - 2451545.0) / 36525.0

    gmst_deg = (
        280.46061837
        + 360.98564736629 * (jd - 2451545.0)
        + 0.000387933 * t * t
        - (t * t * t) / 38710000.0
    )

    return math.radians(gmst_deg % 360.0)


def teme_to_ecef(position_teme, jd):
    x, y, z = position_teme

    theta = gmst_radians(jd)

    cos_t = math.cos(theta)
    sin_t = math.sin(theta)

    x_ecef = cos_t * x + sin_t * y
    y_ecef = -sin_t * x + cos_t * y

    return x_ecef, y_ecef, z


def ecef_to_geodetic(x, y, z):
    lon = math.atan2(y, x)

    p = math.sqrt(x * x + y * y)

    lat = math.atan2(
        z,
        p * (1.0 - EARTH_E2)
    )

    for _ in range(8):
        sin_lat = math.sin(lat)

        n = EARTH_A / math.sqrt(
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
            )
        )

    sin_lat = math.sin(lat)

    n = EARTH_A / math.sqrt(
        1.0
        - EARTH_E2
        * sin_lat
        * sin_lat
    )

    alt = p / math.cos(lat) - n

    return (
        math.degrees(lat),
        math.degrees(lon),
        alt,
    )


def fetch_starlink():
    cache_path = "backend/starlink.json"

    print(
        f"Reading current Starlink OMM catalog from {cache_path}"
    )

    with open(
        cache_path,
        "r",
        encoding="utf-8",
    ) as response:
        records = json.load(response)

    if isinstance(records, dict):
        records = (
            records.get("data")
            or records.get("satellites")
            or records.get("objects")
            or []
        )

    return records


def propagate_record(record, now):
    satellite = Satrec()

    omm.initialize(
        satellite,
        record,
    )

    second = (
        now.second
        + now.microsecond / 1_000_000
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

    jd_total = jd + fraction

    ecef = teme_to_ecef(
        position,
        jd_total,
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
        "name":
            record.get(
                "OBJECT_NAME"
            ),
        "noradId":
            record.get(
                "NORAD_CAT_ID"
            ),
        "latitudeDeg":
            round(lat, 4),
        "longitudeDeg":
            round(lon, 4),
        "altitudeKm":
            round(alt, 2),
        "speedKmS":
            round(speed, 4),
        "epoch":
            record.get("EPOCH"),
        "propagatedUtc":
            now.isoformat(),
    }


def main():
    print(
        "Fetching REAL Starlink orbital elements..."
    )

    records = fetch_starlink()

    print(
        f"Received {len(records)} orbital records"
    )

    now = datetime.now(
        timezone.utc
    )

    print(
        "\nCurrent propagated positions:\n"
    )

    displayed = 0

    for record in records:
        result = propagate_record(
            record,
            now,
        )

        if not result:
            continue

        print(
            f"{result['name']:<24} "
            f"LAT {result['latitudeDeg']:>8}°  "
            f"LON {result['longitudeDeg']:>9}°  "
            f"ALT {result['altitudeKm']:>7} km  "
            f"SPD {result['speedKmS']} km/s"
        )

        displayed += 1

        if displayed >= 10:
            break


if __name__ == "__main__":
    main()
