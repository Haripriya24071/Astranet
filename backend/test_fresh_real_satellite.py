import json
import math
from datetime import datetime, timezone

from sgp4.api import Satrec, jday


EARTH_A_KM = 6378.137
EARTH_E2 = 6.69437999014e-3


def gmst_radians(jd):
    t = (jd - 2451545.0) / 36525.0

    gmst_deg = (
        280.46061837
        + 360.98564736629 * (jd - 2451545.0)
        + 0.000387933 * t * t
        - (t * t * t) / 38710000.0
    )

    return math.radians(
        gmst_deg % 360.0
    )


def teme_to_ecef(position_teme, jd):
    x, y, z = position_teme

    theta = gmst_radians(jd)

    cos_t = math.cos(theta)
    sin_t = math.sin(theta)

    x_ecef = (
        cos_t * x
        + sin_t * y
    )

    y_ecef = (
        -sin_t * x
        + cos_t * y
    )

    return (
        x_ecef,
        y_ecef,
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


with open(
    "backend/starlink_live_test.json",
    "r",
    encoding="utf-8",
) as f:
    record = json.load(f)


name = record["name"]
norad_id = record["satelliteId"]

line1 = record["line1"]
line2 = record["line2"]

satellite = Satrec.twoline2rv(
    line1,
    line2,
)

now = datetime.now(
    timezone.utc
)

seconds = (
    now.second
    + now.microsecond / 1_000_000
)

jd, fraction = jday(
    now.year,
    now.month,
    now.day,
    now.hour,
    now.minute,
    seconds,
)

error, position, velocity = (
    satellite.sgp4(
        jd,
        fraction,
    )
)

if error != 0:
    raise RuntimeError(
        f"SGP4 propagation error: {error}"
    )

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


print()
print("ASTRANET REAL ORBIT TEST")
print("========================")
print()

print("SATELLITE :", name)
print("NORAD ID  :", norad_id)

print(
    "TLE EPOCH :",
    record["date"],
)

print(
    "PROP UTC  :",
    now.isoformat(),
)

print()

print(
    "LATITUDE  :",
    round(lat, 5),
    "deg",
)

print(
    "LONGITUDE :",
    round(lon, 5),
    "deg",
)

print(
    "ALTITUDE  :",
    round(alt, 2),
    "km",
)

print(
    "SPEED     :",
    round(speed, 4),
    "km/s",
)

print()

print(
    "TEME X Y Z:",
    tuple(
        round(v, 2)
        for v in position
    ),
)

print(
    "VELOCITY  :",
    tuple(
        round(v, 4)
        for v in velocity
    ),
)

print()
print(
    "✓ REAL CURRENT-TIME ORBIT PROPAGATION WORKING"
)
