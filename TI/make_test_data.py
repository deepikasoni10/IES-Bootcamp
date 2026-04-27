#!/usr/bin/env python3
"""
Generate realistic test telemetry data (same format as GCP on_status response).
Used when GCP server is unavailable.

Creates telemetry_data.json with 3 resources x 96 intervals (1 day @ 15-min).
Quality flags: mostly ACTUAL, some ESTIMATED, few MISSING.
"""

import json
import hashlib
import random
from datetime import datetime, timedelta, timezone

random.seed(42)  # reproducible


def now():
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def make_interval(start_dt, kwh, quality="ACTUAL"):
    return {
        "intervalPeriod": {
            "start": start_dt.strftime("%Y-%m-%dT%H:%M:%SZ"),
            "duration": "PT15M",
        },
        "payloads": [
            {"type": "USAGE",        "values": [round(kwh, 4)]},
            {"type": "DATA_QUALITY", "values": [quality]},
        ],
    }


def generate_resource(name, base_kwh, date_str="2024-04-15"):
    """
    Generate 96 intervals (1 full day @ 15-min) with realistic consumption.
    - Night (23:00-05:00): lower consumption
    - Morning peak (06:00-10:00): higher
    - Evening peak (18:00-22:00): highest
    - Few MISSING, some ESTIMATED readings
    """
    intervals = []
    start = datetime.fromisoformat(f"{date_str}T00:00:00").replace(tzinfo=timezone.utc)

    for i in range(96):  # 96 slots per day
        dt = start + timedelta(minutes=15 * i)
        hour = dt.hour

        # Consumption pattern
        if 0 <= hour < 5:       # night: low
            factor = 0.3
        elif 5 <= hour < 8:     # early morning: rising
            factor = 0.6
        elif 8 <= hour < 12:    # morning peak: high
            factor = 1.2
        elif 12 <= hour < 14:   # afternoon: medium
            factor = 0.9
        elif 14 <= hour < 18:   # afternoon-evening: rising
            factor = 1.0
        elif 18 <= hour < 22:   # evening peak: highest
            factor = 1.5
        else:                   # late night: low
            factor = 0.4

        kwh = base_kwh * factor * (0.85 + random.random() * 0.3)

        # Quality flags: 90% ACTUAL, 7% ESTIMATED, 3% MISSING
        r = random.random()
        if r < 0.03:
            quality = "MISSING"
            kwh = 0.0
        elif r < 0.10:
            quality = "ESTIMATED"
        else:
            quality = "ACTUAL"

        intervals.append(make_interval(dt, round(kwh, 4), quality))

    return {
        "resourceName": name,
        "intervalPeriod": {"start": f"{date_str}T00:00:00Z", "duration": "PT15M"},
        "intervals": intervals,
    }


def main():
    print("Generating test telemetry data...")

    resources = [
        generate_resource("RES-001_IMPORT", base_kwh=0.35),   # residential
        generate_resource("RES-002_IMPORT", base_kwh=0.28),   # residential
        generate_resource("COM-001_IMPORT", base_kwh=1.20),   # commercial
    ]

    data_payload = {
        "@type":      "IES_Report",
        "objectType": "REPORT",
        "reportName": "Bootcamp Telemetry Sample (generated)",
        "clientName": "IntelliGrid AMI Services",
        "payloadDescriptors": [
            {"objectType": "REPORT_PAYLOAD_DESCRIPTOR", "payloadType": "USAGE",        "units": "KWH", "readingType": "DIRECT_READ"},
            {"objectType": "REPORT_PAYLOAD_DESCRIPTOR", "payloadType": "DATA_QUALITY", "readingType": "ANNOTATION"},
        ],
        "resources": resources,
    }

    canonical  = json.dumps(data_payload, sort_keys=True, separators=(',', ':'))
    hash_val   = hashlib.sha256(canonical.encode()).hexdigest()

    total_intervals = sum(len(r["intervals"]) for r in resources)
    actual_count    = sum(
        1 for r in resources for iv in r["intervals"]
        for p in iv["payloads"] if p["type"] == "DATA_QUALITY" and p["values"][0] == "ACTUAL"
    )

    out = {
        "transactionId": "synthetic-test-data",
        "fetchedAt":     now(),
        "payloadHash":   hash_val,
        "dataPayload":   data_payload,
    }

    with open("telemetry_data.json", "w") as f:
        json.dump(out, f, indent=2)

    print(f"  Resources  : {len(resources)}")
    print(f"  Intervals  : {total_intervals} (96 per resource)")
    print(f"  ACTUAL     : {actual_count}")
    print(f"  Hash       : {hash_val[:20]}...")
    print(f"  Saved to   : telemetry_data.json")


if __name__ == "__main__":
    main()
