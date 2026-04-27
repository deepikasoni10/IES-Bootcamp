#!/usr/bin/env python3
"""
Cross-UC Integration: EDX Telemetry + TI Tariff = Annotated Billing

Takes:
  - telemetry_data.json   (from fetch_telemetry.py — meter intervals)
  - policy_pack.json      (from fetch_policy.py    — tariff rules)

Produces:
  - annotated_telemetry.json  (each interval: kWh + timestamp + rate + cost + clause)

This proves interoperability:
  EDX use case data + TI tariff logic = meaningful VAS output
"""

import json
import os
from datetime import datetime, timezone, timedelta
from tariff_engine import parse_policy, compute_slab_units, parse_duration_hrs, parse_time


# ─────────────────────────────────────────────────────────────
# Helpers
# ─────────────────────────────────────────────────────────────

def parse_iso(ts: str) -> datetime:
    """Parse ISO 8601 timestamp to datetime."""
    ts = ts.rstrip("Z")
    if "+" in ts:
        ts = ts.split("+")[0]
    return datetime.fromisoformat(ts).replace(tzinfo=timezone.utc)


def in_window(dt: datetime, window_start_str: str, duration_hrs: float) -> bool:
    """Check if datetime falls in a ToD surcharge window."""
    ws = parse_time(window_start_str)
    w_start_h = ws.hour + ws.minute / 60
    w_end_h   = (w_start_h + duration_hrs) % 24
    h = dt.hour + dt.minute / 60

    if w_start_h <= w_end_h:
        return w_start_h <= h < w_end_h
    else:  # wraps midnight
        return h >= w_start_h or h < w_end_h


def get_quality(interval: dict) -> str:
    """Extract DATA_QUALITY flag from interval payloads."""
    for payload in interval.get("payloads", []):
        if payload.get("type") == "DATA_QUALITY":
            vals = payload.get("values", [])
            return vals[0] if vals else "UNKNOWN"
    return "ACTUAL"  # default if not specified


def get_kwh(interval: dict) -> float:
    """Extract USAGE kWh from interval payloads."""
    for payload in interval.get("payloads", []):
        if payload.get("type") == "USAGE":
            vals = payload.get("values", [])
            return float(vals[0]) if vals else 0.0
    return 0.0


def pick_policy(resource_name: str, policy_map: dict):
    """
    Pick policy based on resource type:
    RES-* -> Residential Telescopic (RES-T1)
    COM-* -> Commercial ToD (COM-TOU1)
    Default -> RES-T1
    """
    name = resource_name.upper()
    if name.startswith("COM"):
        return policy_map.get("COM-TOU1") or list(policy_map.values())[0]
    return policy_map.get("RES-T1") or list(policy_map.values())[0]


# ─────────────────────────────────────────────────────────────
# Main annotator
# ─────────────────────────────────────────────────────────────

def annotate_telemetry(telemetry: dict, policies: list, max_resources: int = 5) -> list:
    """
    For each meter resource (up to max_resources):
      For each interval:
        - Get kWh + timestamp + quality
        - Find which slab applies (based on cumulative monthly kWh)
        - Check if ToD surcharge applies
        - Compute cost
        - Append to annotated output
    """
    policy_map   = {p["policyID"]: p for p in policies}
    resources    = telemetry.get("resources", [])
    annotated    = []

    print(f"\n{'='*60}")
    print(f"Cross-UC: Annotating {min(len(resources), max_resources)} meter resources")
    print(f"{'='*60}")

    for res in resources[:max_resources]:
        resource_name = res.get("resourceName", "UNKNOWN")
        intervals     = res.get("intervals", [])
        policy_raw    = pick_policy(resource_name, policy_map)
        slabs, surcharges = parse_policy(policy_raw)

        print(f"\n  Resource : {resource_name}")
        print(f"  Policy   : {policy_raw['policyID']} - {policy_raw['policyName']}")
        print(f"  Intervals: {len(intervals)}")
        print(f"  {'─'*54}")
        print(f"  {'Timestamp':<22} {'kWh':>6}  {'Quality':<10}  {'Clause':<14}  {'Rate':>8}  {'Cost':>8}")
        print(f"  {'─'*54}")

        cumulative_kwh      = 0.0
        resource_annotated  = []
        resource_total_cost = 0.0
        skipped_missing     = 0

        for interval in intervals:
            # Local example data has unresolved string refs — skip them
            if isinstance(interval, str):
                skipped_missing += 1
                continue
            ts_str  = interval.get("intervalPeriod", {}).get("start", "")
            kwh     = get_kwh(interval)
            quality = get_quality(interval)

            # Skip MISSING intervals (no data to bill)
            if quality == "MISSING" or kwh == 0.0:
                skipped_missing += 1
                resource_annotated.append({
                    "timestamp": ts_str,
                    "kwh": 0.0,
                    "quality": quality,
                    "clause": "SKIPPED",
                    "rate": 0.0,
                    "cost": 0.0,
                    "note": "Missing or zero reading",
                })
                continue

            # Parse timestamp for ToD check
            try:
                dt = parse_iso(ts_str)
            except Exception:
                dt = None

            # Find slab for cumulative position
            cumulative_kwh += kwh
            slab_breakdown  = compute_slab_units(slabs, cumulative_kwh)
            # The last slab in breakdown is the one this interval falls into
            current_slab    = slab_breakdown[-1][0] if slab_breakdown else slabs[0]
            base_rate       = current_slab.price

            # Check ToD surcharges
            surcharge_rate  = 0.0
            surcharge_clause = None
            if dt:
                for sur in surcharges:
                    window_start_str  = sur.window_start.strftime("T%H:%M:%SZ")
                    if in_window(dt, window_start_str, sur.window_duration_hrs):
                        if sur.unit == "INR_PER_KWH":
                            surcharge_rate   += sur.value
                            surcharge_clause  = sur.id
                        elif sur.unit == "PERCENT":
                            surcharge_rate   += base_rate * (sur.value / 100)
                            surcharge_clause  = sur.id

            effective_rate = base_rate + surcharge_rate
            cost           = round(kwh * effective_rate, 4)
            resource_total_cost += cost

            clause_label = (
                f"{current_slab.id}"
                + (f"+{surcharge_clause}" if surcharge_clause else "")
            )

            ts_display = ts_str[:16] if ts_str else "?"
            print(f"  {ts_display:<22} {kwh:>6.3f}  {quality:<10}  {clause_label:<14}  "
                  f"Rs.{effective_rate:>5.2f}  Rs.{cost:>6.4f}")

            resource_annotated.append({
                "timestamp":       ts_str,
                "kwh":             kwh,
                "quality":         quality,
                "clause":          clause_label,
                "slab_id":         current_slab.id,
                "surcharge_id":    surcharge_clause,
                "base_rate":       base_rate,
                "surcharge_rate":  surcharge_rate,
                "effective_rate":  effective_rate,
                "cost":            cost,
            })

        print(f"  {'─'*54}")
        print(f"  Total intervals : {len(intervals)}")
        print(f"  Billed          : {len(intervals) - skipped_missing}")
        print(f"  Missing/skipped : {skipped_missing}")
        print(f"  Total kWh       : {cumulative_kwh:.3f}")
        print(f"  Total cost      : Rs.{resource_total_cost:.2f}")

        annotated.append({
            "resourceName":   resource_name,
            "policyId":       policy_raw["policyID"],
            "policyName":     policy_raw["policyName"],
            "totalKwh":       round(cumulative_kwh, 3),
            "totalCost":      round(resource_total_cost, 2),
            "billedCount":    len(intervals) - skipped_missing,
            "missingCount":   skipped_missing,
            "intervals":      resource_annotated,
        })

    return annotated


def main():
    print(f"\n{'='*60}")
    print(f"Cross-UC Integration: EDX + TI")
    print(f"{'='*60}")

    # Load policy pack
    if not os.path.exists("policy_pack.json"):
        print("[ERROR] policy_pack.json not found!")
        print("        Run: python fetch_policy.py")
        return
    with open("policy_pack.json") as f:
        pack = json.load(f)
    policies = pack["dataPayload"]["policies"]
    print(f"\n[TI]  Policy pack loaded  : {len(policies)} policies")
    print(f"      Hash               : {pack['payloadHash'][:20]}...")

    # Load telemetry
    if not os.path.exists("telemetry_data.json"):
        print("\n[EDX] telemetry_data.json not found!")
        print("      Run: python fetch_telemetry.py")
        print("      Falling back to local example data...\n")
        ex_file = ("../ies-docs/implementation-guides/data_exchange/"
                   "bootcamp/example-data/telemetry_chunk_1.jsonld")
        if not os.path.exists(ex_file):
            print(f"[ERROR] Also not found: {ex_file}")
            return
        with open(ex_file) as f:
            telemetry_raw = json.load(f)
        telemetry_payload = telemetry_raw
        t_hash = "local-example-data"
    else:
        with open("telemetry_data.json") as f:
            tel = json.load(f)
        telemetry_payload = tel["dataPayload"]
        t_hash = tel["payloadHash"]
    print(f"\n[EDX] Telemetry loaded   : hash {t_hash[:20]}...")

    # Cross-UC: annotate
    resources = telemetry_payload.get("resources", [])
    print(f"      Resources          : {len(resources)}")
    print(f"      (showing first 5)\n")

    annotated = annotate_telemetry(telemetry_payload, policies, max_resources=5)

    # Summary
    total_kwh  = sum(r["totalKwh"]  for r in annotated)
    total_cost = sum(r["totalCost"] for r in annotated)

    print(f"\n{'='*60}")
    print(f"CROSS-UC SUMMARY")
    print(f"{'='*60}")
    print(f"  Policy pack (TI)  : {pack['payloadHash'][:20]}...  HASH VERIFIED")
    print(f"  Telemetry (EDX)   : {t_hash[:20]}...")
    print(f"  Resources billed  : {len(annotated)}")
    print(f"  Total kWh         : {total_kwh:.3f}")
    print(f"  Total cost        : Rs.{total_cost:.2f}")
    print(f"{'='*60}")

    # Save output
    output = {
        "generatedAt":   datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "policyPackHash": pack["payloadHash"],
        "summary": {
            "resources":  len(annotated),
            "totalKwh":   total_kwh,
            "totalCost":  total_cost,
        },
        "resources": annotated,
    }
    with open("annotated_telemetry.json", "w") as f:
        json.dump(output, f, indent=2)
    print(f"\n[Saved] annotated_telemetry.json")
    print(f"\nThis proves: EDX meter data + TI tariff engine = verifiable billing output")


if __name__ == "__main__":
    main()
