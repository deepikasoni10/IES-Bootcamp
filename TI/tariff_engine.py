#!/usr/bin/env python3
"""
Tariff Engine -- IES Tariff Intelligence

Parses an IES Policy Pack (JSON-LD) and computes bills with full
clause-level execution trace showing which slab/surcharge applied at each step.

Supports:
  - Telescopic energy slabs
  - Time-of-Day surcharges (PERCENT or INR_PER_KWH)
"""

import json
from dataclasses import dataclass, field
from datetime import datetime, time, timedelta, timezone
from typing import Optional


# -------------------------------------------------------------
# Data Models
# -------------------------------------------------------------

@dataclass
class EnergySlab:
    id: str
    start: float
    end: Optional[float]   # None = unbounded (last slab)
    price: float           # INR per kWh

    def covers(self, unit_number: float) -> bool:
        """Does this slab cover the given cumulative unit position?"""
        if unit_number < self.start:
            return False
        if self.end is None:
            return True
        return unit_number <= self.end

    def units_in_slab(self, total_kwh: float) -> float:
        """How many kWh of total_kwh fall in this slab?"""
        slab_start = self.start
        slab_end   = self.end if self.end is not None else float('inf')
        low  = max(slab_start, 0)
        high = min(slab_end, total_kwh)
        return max(0.0, high - low + (1 if self.start > 0 else 0) - (1 if self.start > 0 else 0))


@dataclass
class SurchargeTariff:
    id: str
    window_start: time     # e.g. 23:00
    window_duration_hrs: float
    value: float           # e.g. -10 or 1.5
    unit: str              # "PERCENT" or "INR_PER_KWH"


@dataclass
class TraceEntry:
    step: str
    clause_id: str
    description: str
    kwh: float
    rate: float
    amount: float


@dataclass
class BillResult:
    policy_id: str
    policy_name: str
    total_kwh: float
    base_charge: float
    surcharge_total: float
    total_bill: float
    trace: list = field(default_factory=list)


# -------------------------------------------------------------
# Parser
# -------------------------------------------------------------

def parse_time(s: str) -> time:
    """Parse 'T23:00:00Z' or '23:00:00' -> time object."""
    s = s.lstrip("T").rstrip("Z")
    parts = s.split(":")
    return time(int(parts[0]), int(parts[1]), int(parts[2]) if len(parts) > 2 else 0)


def parse_duration_hrs(d: str) -> float:
    """Parse ISO duration 'PT6H' or 'PT30M' -> hours."""
    d = d.upper().lstrip("PT")
    if d.endswith("H"):
        return float(d[:-1])
    if d.endswith("M"):
        return float(d[:-1]) / 60
    return float(d)


def parse_policy(raw: dict) -> tuple:
    """Parse a raw policy dict -> (slabs, surcharges)."""
    slabs = []
    for s in raw.get("energySlabs", []):
        slabs.append(EnergySlab(
            id=s["id"],
            start=s["start"],
            end=s.get("end"),       # None if null/missing
            price=s["price"],
        ))
    # Sort slabs by start
    slabs.sort(key=lambda x: x.start)

    surcharges = []
    for st in raw.get("surchargeTariffs", []):
        interval = st.get("interval", {})
        surcharges.append(SurchargeTariff(
            id=st["id"],
            window_start=parse_time(interval.get("start", "T00:00:00Z")),
            window_duration_hrs=parse_duration_hrs(interval.get("duration", "PT0H")),
            value=st["value"],
            unit=st["unit"],
        ))
    return slabs, surcharges


# -------------------------------------------------------------
# Billing Engine
# -------------------------------------------------------------

def compute_slab_units(slabs: list, total_kwh: float) -> list:
    """
    Split total_kwh across telescopic slabs.
    Returns list of (slab, kwh_in_slab).
    """
    result = []
    remaining = total_kwh

    for i, slab in enumerate(slabs):
        if remaining <= 0:
            break

        slab_capacity = (slab.end - slab.start + 1) if slab.end is not None else float('inf')

        # How many units fall in this slab?
        # Slab covers [start, end], but billing is cumulative:
        # slab 1 covers 0-100 (100 units), slab 2 covers 101-300 (200 units), etc.
        if i == 0:
            slab_size = slab.end if slab.end is not None else float('inf')
        else:
            prev_end = slabs[i-1].end
            if slab.end is None:
                slab_size = float('inf')
            else:
                slab_size = slab.end - prev_end

        units = min(remaining, slab_size)
        result.append((slab, units))
        remaining -= units

    return result


def hours_in_window(window_start: time, duration_hrs: float, consumption_hour: Optional[int] = None) -> bool:
    """
    If consumption_hour is given: check if that hour falls in the surcharge window.
    If None: assume full-day consumption (return True if window exists).
    """
    if consumption_hour is None:
        return True  # apply to any unspecified consumption

    w_start = window_start.hour + window_start.minute / 60
    w_end   = (w_start + duration_hrs) % 24

    h = float(consumption_hour)
    if w_start <= w_end:
        return w_start <= h < w_end
    else:  # wraps midnight
        return h >= w_start or h < w_end


def compute_bill(policy: dict, total_kwh: float,
                 night_kwh: float = 0.0,
                 peak_kwh: float = 0.0,
                 timestamp: Optional[str] = None) -> BillResult:
    """
    Compute the full bill for a given consumption.

    Args:
        policy:    raw policy dict from policy pack
        total_kwh: total energy consumed in the billing period
        night_kwh: kWh consumed during night window (for PERCENT surcharges)
        peak_kwh:  kWh consumed during peak window (for INR_PER_KWH surcharges)
        timestamp: ISO timestamp of consumption (optional, for display)

    Returns:
        BillResult with full execution trace
    """
    slabs, surcharges = parse_policy(policy)
    trace = []

    print(f"\n{'-'*60}")
    print(f"Policy  : {policy['policyName']}  [{policy['policyID']}]")
    print(f"Consumed: {total_kwh} kWh")
    if timestamp:
        print(f"Period  : {timestamp}")
    print(f"{'-'*60}")

    # -- Step 1: Slab-based base charge --------------------------
    slab_breakdown = compute_slab_units(slabs, total_kwh)
    base_charge = 0.0

    print("\n[SLABS] Telescopic billing:")
    for slab, units in slab_breakdown:
        amount = round(units * slab.price, 2)
        base_charge += amount
        label = f"0-{slab.end}" if slab.end else f"{slab.start}+"
        print(f"  Clause {slab.id:12s}  {units:7.2f} kWh × Rs.{slab.price:.2f}  =  Rs.{amount:.2f}  [{label} kWh]")
        trace.append(TraceEntry(
            step="SLAB",
            clause_id=slab.id,
            description=f"{label} kWh @ Rs.{slab.price}/kWh",
            kwh=units,
            rate=slab.price,
            amount=amount,
        ))

    base_charge = round(base_charge, 2)
    print(f"  {'-'*52}")
    print(f"  Base charge: Rs.{base_charge:.2f}")

    # -- Step 2: Surcharges / ToD adjustments --------------------
    surcharge_total = 0.0
    print("\n[SURCHARGES] Time-of-Day adjustments:")

    for sur in surcharges:
        w_start = sur.window_start.strftime("%H:%M")
        # Work out window end
        end_hr = (sur.window_start.hour + sur.window_duration_hrs) % 24
        w_end = f"{int(end_hr):02d}:{int((end_hr % 1)*60):02d}"

        if sur.unit == "PERCENT":
            # Surcharge applies only to explicitly provided night_kwh
            # If no night breakdown given, surcharge = 0 (no estimation)
            affected_kwh = night_kwh
            if affected_kwh <= 0:
                print(f"  Clause {sur.id:18s}  no night kWh provided  {sur.value:+.0f}%  ->  Rs.0.00  (skipped)")
                trace.append(TraceEntry(step="SURCHARGE", clause_id=sur.id,
                    description=f"ToD {sur.value:+.0f}% [{w_start}-{w_end}]: no data provided",
                    kwh=0, rate=0, amount=0))
                continue

            note = "(actual night consumption provided)"
            avg_rate = base_charge / total_kwh if total_kwh > 0 else 0
            adj = round(affected_kwh * avg_rate * (sur.value / 100), 2)
            surcharge_total += adj
            label = f"Rs.{adj:.2f}" if adj >= 0 else f"-Rs.{abs(adj):.2f}"
            print(f"  Clause {sur.id:18s}  {affected_kwh:.2f} kWh in [{w_start}-{w_end}]"
                  f"  {sur.value:+.0f}%  ->  {label}  {note}")
            trace.append(TraceEntry(
                step="SURCHARGE",
                clause_id=sur.id,
                description=f"ToD {sur.value:+.0f}% [{w_start}-{w_end}] on {affected_kwh:.2f} kWh",
                kwh=affected_kwh,
                rate=avg_rate * sur.value / 100,
                amount=adj,
            ))

        elif sur.unit == "INR_PER_KWH":
            # Surcharge applies only to explicitly provided peak_kwh
            affected_kwh = peak_kwh
            if affected_kwh <= 0:
                print(f"  Clause {sur.id:18s}  no peak kWh provided   Rs.{sur.value:+.2f}/kWh  ->  Rs.0.00  (skipped)")
                trace.append(TraceEntry(step="SURCHARGE", clause_id=sur.id,
                    description=f"ToD Rs.{sur.value:+.2f}/kWh [{w_start}-{w_end}]: no data provided",
                    kwh=0, rate=0, amount=0))
                continue

            note = "(actual peak consumption provided)"
            adj = round(affected_kwh * sur.value, 2)
            surcharge_total += adj
            label = f"Rs.{adj:.2f}" if adj >= 0 else f"-Rs.{abs(adj):.2f}"
            print(f"  Clause {sur.id:18s}  {affected_kwh:.2f} kWh in [{w_start}-{w_end}]"
                  f"  Rs.{sur.value:+.2f}/kWh  ->  {label}  {note}")
            trace.append(TraceEntry(
                step="SURCHARGE",
                clause_id=sur.id,
                description=f"ToD Rs.{sur.value:+.2f}/kWh [{w_start}-{w_end}] on {affected_kwh:.2f} kWh",
                kwh=affected_kwh,
                rate=sur.value,
                amount=adj,
            ))

    surcharge_total = round(surcharge_total, 2)
    if not surcharges:
        print("  (none applicable)")

    # -- Step 3: Total --------------------------------------------
    total_bill = round(base_charge + surcharge_total, 2)
    print(f"\n[TOTAL]")
    print(f"  Base charge   : Rs.{base_charge:.2f}")
    print(f"  Surcharges    : Rs.{surcharge_total:.2f}")
    print(f"  ---------------------")
    print(f"  Total bill    : Rs.{total_bill:.2f}")

    return BillResult(
        policy_id=policy["policyID"],
        policy_name=policy["policyName"],
        total_kwh=total_kwh,
        base_charge=base_charge,
        surcharge_total=surcharge_total,
        total_bill=total_bill,
        trace=trace,
    )


# -------------------------------------------------------------
# Main -- run directly with local policy data
# -------------------------------------------------------------

if __name__ == "__main__":
    import sys

    # Load policy pack -- from fetched file or local example data
    pack_file = "policy_pack.json"
    try:
        with open(pack_file) as f:
            pack = json.load(f)
        policies = pack["dataPayload"]["policies"]
        print(f"Loaded policy pack from {pack_file}")
        print(f"Hash: {pack['payloadHash']}")
    except FileNotFoundError:
        # Fallback: use local example data
        print(f"[!] {pack_file} not found -- using local example data")
        print("    Run fetch_policy.py first to get live data from GCP\n")
        policies = [
            {
                "policyID": "RES-T1",
                "policyName": "Residential Telescopic Standard",
                "energySlabs": [
                    {"id": "s1", "start": 0, "end": 100,  "price": 4.5},
                    {"id": "s2", "start": 101, "end": 300, "price": 7.5},
                    {"id": "s3", "start": 301, "end": None, "price": 10.5},
                ],
                "surchargeTariffs": [
                    {"id": "night-discount", "interval": {"start": "T23:00:00Z", "duration": "PT6H"},
                     "value": -10, "unit": "PERCENT"},
                ],
            },
            {
                "policyID": "COM-TOU1",
                "policyName": "Commercial ToD Standard",
                "energySlabs": [
                    {"id": "fixed-base", "start": 0, "end": None, "price": 8.5},
                ],
                "surchargeTariffs": [
                    {"id": "evening-peak", "interval": {"start": "T18:00:00Z", "duration": "PT4H"},
                     "value": 1.5, "unit": "INR_PER_KWH"},
                ],
            },
        ]

    policy_map = {p["policyID"]: p for p in policies}

    print(f"\nAvailable policies: {list(policy_map.keys())}")

    # --- Sample computations ---
    res_policy = policy_map["RES-T1"]
    com_policy = policy_map["COM-TOU1"]

    # Residential: 350 kWh, standard month
    compute_bill(res_policy, total_kwh=350.0, timestamp="April 2024")

    # Residential: 80 kWh (stays in slab 1)
    compute_bill(res_policy, total_kwh=80.0, timestamp="April 2024")

    # Residential: 350 kWh with 50 kWh at night -> discount
    compute_bill(res_policy, total_kwh=350.0, night_kwh=50.0, timestamp="April 2024 (with night data)")

    # Commercial: 500 kWh, 100 kWh during evening peak
    compute_bill(com_policy, total_kwh=500.0, peak_kwh=100.0, timestamp="April 2024")
