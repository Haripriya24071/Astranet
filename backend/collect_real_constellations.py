import json
import subprocess
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import urlencode


API_BASE = "https://tle.ivanstanojevic.me/api/tle"

MAX_AGE_HOURS = 48.0
TARGET_PER_CONSTELLATION = 20
PAGE_SIZE = 100
MAX_PAGES_TO_SCAN = 14

OUTPUT = Path("backend/real_constellations.json")

CONSTELLATIONS = {
    "STARLINK": "starlink",
    "ONEWEB": "oneweb",
    "IRIDIUM": "iridium",
    "KUIPER": "kuiper",
    "QIANFAN": "qianfan",
    "GALILEO": "galileo",
}


def parse_epoch(raw):
    epoch = datetime.fromisoformat(
        raw.replace("Z", "+00:00")
    )

    if epoch.tzinfo is None:
        epoch = epoch.replace(
            tzinfo=timezone.utc
        )

    return epoch


def curl_json(url):
    result = subprocess.run(
        [
            "curl",
            "-fsSL",
            "--connect-timeout",
            "15",
            "--max-time",
            "60",
            "--retry",
            "2",
            url,
        ],
        capture_output=True,
        text=True,
    )

    if result.returncode != 0:
        raise RuntimeError(
            result.stderr.strip()
            or f"curl failed: {url}"
        )

    return json.loads(result.stdout)


def build_url(search, page):
    query = urlencode(
        {
            "search": search,
            "page": page,
            "page-size": PAGE_SIZE,
            "sort": "id",
        }
    )

    return f"{API_BASE}?{query}"


def is_fresh(record, now):
    raw = record.get("date")

    if not raw:
        return False

    try:
        epoch = parse_epoch(raw)
    except Exception:
        return False

    age_hours = (
        now - epoch
    ).total_seconds() / 3600

    return (
        0 <= age_hours <= MAX_AGE_HOURS
    )


def collect_constellation(
    constellation,
    search,
    now,
):
    print()
    print(
        f"=== {constellation} ==="
    )

    first = curl_json(
        build_url(search, 1)
    )

    total = int(
        first.get(
            "totalItems",
            0,
        )
    )

    if total == 0:
        print("No catalogue results.")
        return []

    last_page = max(
        1,
        (
            total
            + PAGE_SIZE
            - 1
        )
        // PAGE_SIZE,
    )

    print(
        "Catalogue matches:",
        total,
    )

    print(
        "Pages:",
        last_page,
    )

    # Search from BOTH ends.
    # This avoids depending on the API's
    # ordering behaviour.
    page_order = []

    low = 1
    high = last_page

    while (
        low <= high
        and len(page_order)
        < MAX_PAGES_TO_SCAN
    ):
        page_order.append(low)

        if (
            high != low
            and len(page_order)
            < MAX_PAGES_TO_SCAN
        ):
            page_order.append(high)

        low += 1
        high -= 1

    fresh = {}
    scanned = 0

    for page in page_order:
        try:
            if page == 1:
                payload = first
            else:
                payload = curl_json(
                    build_url(
                        search,
                        page,
                    )
                )
        except Exception as exc:
            print(
                f"Page {page}: ERROR {exc}"
            )
            continue

        members = payload.get(
            "member",
            [],
        )

        scanned += len(members)

        fresh_this_page = 0

        for record in members:
            if not is_fresh(
                record,
                now,
            ):
                continue

            sat_id = str(
                record.get(
                    "satelliteId",
                    ""
                )
            )

            if not sat_id:
                continue

            if sat_id in fresh:
                continue

            fresh[sat_id] = {
                "satelliteId":
                    record[
                        "satelliteId"
                    ],
                "name":
                    record[
                        "name"
                    ],
                "date":
                    record[
                        "date"
                    ],
                "line1":
                    record[
                        "line1"
                    ],
                "line2":
                    record[
                        "line2"
                    ],
                "constellation":
                    constellation,
            }

            fresh_this_page += 1

            if (
                len(fresh)
                >= TARGET_PER_CONSTELLATION
            ):
                break

        print(
            f"page {page}: "
            f"{fresh_this_page} fresh | "
            f"total fresh {len(fresh)}"
        )

        if (
            len(fresh)
            >= TARGET_PER_CONSTELLATION
        ):
            break

    records = list(
        fresh.values()
    )

    records.sort(
        key=lambda item:
            parse_epoch(
                item["date"]
            ),
        reverse=True,
    )

    print(
        f"{constellation}: "
        f"{len(records)} usable fresh satellites"
    )

    return records[
        :TARGET_PER_CONSTELLATION
    ]


def main():
    now = datetime.now(
        timezone.utc
    )

    all_records = []

    counts = {}

    for (
        constellation,
        search,
    ) in CONSTELLATIONS.items():
        records = (
            collect_constellation(
                constellation,
                search,
                now,
            )
        )

        all_records.extend(
            records
        )

        counts[
            constellation
        ] = len(records)

    payload = {
        "generatedUtc":
            now.isoformat(),
        "maxAgeHours":
            MAX_AGE_HOURS,
        "source":
            "PUBLIC_TLE_API",
        "counts":
            counts,
        "totalFresh":
            len(all_records),
        "satellites":
            all_records,
    }

    OUTPUT.write_text(
        json.dumps(
            payload,
            indent=2,
        ),
        encoding="utf-8",
    )

    print()
    print(
        "=============================="
    )
    print(
        "ASTRANET REAL CONSTELLATIONS"
    )
    print(
        "=============================="
    )

    for (
        name,
        count,
    ) in counts.items():
        print(
            f"{name:<12}: {count}"
        )

    print(
        "------------------------------"
    )

    print(
        "TOTAL FRESH :",
        len(all_records),
    )

    print(
        "OUTPUT      :",
        OUTPUT,
    )


if __name__ == "__main__":
    main()
