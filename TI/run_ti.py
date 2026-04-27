#!/usr/bin/env python3
"""
TI Runner -- IES Tariff Intelligence

Orchestrates the full TI flow:
  1. Fetch Policy Pack from GCP via Beckn (or use cached)
  2. Verify content hash
  3. Parse TariffPlan (slabs, surcharges)
  4. Run test vectors -> pass/fail
  5. Print execution trace with clause traceability

Usage:
  python run_ti.py            # fetch live from GCP + run vectors
  python run_ti.py --offline  # use cached policy_pack.json
  python run_ti.py --local    # use local example data (no network)
"""

import argparse
import json
import os
import sys
from tariff_engine import compute_bill, parse_policy

TOLERANCE = 0.50   # INR tolerance for test vector comparison


def load_policy_pack(mode: str) -> dict:
    """Load the policy pack based on mode."""
    if mode == "local":
        print("[MODE] Using built-in local example data (no network)\n")
        return None  # tariff_engine fallback handles this

    cache_file = "policy_pack.json"

    if mode == "online" or not os.path.exists(cache_file):
        print("[MODE] Fetching live policy pack from GCP via Beckn...\n")
        from fetch_policy import fetch_tariff_policy
        return fetch_tariff_policy()
    else:
        print(f"[MODE] Using cached policy pack: {cache_file}\n")
        with open(cache_file) as f:
            return json.load(f)


def verify_hash(pack: dict) -> bool:
    """Re-verify the stored hash against the payload."""
    import hashlib
    stored_hash = pack.get("payloadHash", "")
    payload = pack.get("dataPayload", {})
    canonical = json.dumps(payload, sort_keys=True, separators=(',', ':'))
    computed = hashlib.sha256(canonical.encode()).hexdigest()

    if stored_hash == computed:
        print(f"[HASH] Verification PASS")
        print(f"       SHA-256: {computed}")
        return True
    else:
        print(f"[HASH] Verification FAIL!")
        print(f"       Stored  : {stored_hash}")
        print(f"       Computed: {computed}")
        return False


def run_test_vectors(policies: list) -> dict:
    """Run all test vectors and report pass/fail."""
    policy_map = {p["policyID"]: p for p in policies}

    with open("test_vectors.json") as f:
        vectors = json.load(f)

    passed = 0
    failed = 0
    results = []

    print(f"\n{'='*60}")
    print(f"Running {len(vectors)} Test Vectors")
    print(f"{'='*60}")

    for tv in vectors:
        pid   = tv["policy_id"]
        inp   = tv["input"]
        exp   = tv["expected"]

        if pid not in policy_map:
            print(f"  [SKIP] {tv['id']} -- policy {pid} not found")
            continue

        # Compute without printing the per-bill trace (quiet mode)
        import io, contextlib
        buf = io.StringIO()
        with contextlib.redirect_stdout(buf):
            result = compute_bill(
                policy_map[pid],
                total_kwh=inp["total_kwh"],
                night_kwh=inp.get("night_kwh", 0),
                peak_kwh=inp.get("peak_kwh", 0),
            )

        # Compare
        ok_base = abs(result.base_charge    - exp["base_charge"])    <= TOLERANCE
        ok_sur  = abs(result.surcharge_total - exp["surcharge_total"]) <= TOLERANCE
        ok_tot  = abs(result.total_bill     - exp["total_bill"])     <= TOLERANCE
        ok = ok_base and ok_sur and ok_tot

        status = "\033[32mPASS\033[0m" if ok else "\033[31mFAIL\033[0m"
        print(f"  [{status}] {tv['id']:12s}  {tv['description']}")

        if not ok:
            if not ok_base:
                print(f"           base_charge:    expected Rs.{exp['base_charge']:.2f}  got Rs.{result.base_charge:.2f}")
            if not ok_sur:
                print(f"           surcharge:      expected Rs.{exp['surcharge_total']:.2f}  got Rs.{result.surcharge_total:.2f}")
            if not ok_tot:
                print(f"           total_bill:     expected Rs.{exp['total_bill']:.2f}  got Rs.{result.total_bill:.2f}")

        if ok:
            passed += 1
        else:
            failed += 1

        results.append({
            "id": tv["id"],
            "passed": ok,
            "expected": exp,
            "actual": {
                "base_charge":     result.base_charge,
                "surcharge_total": result.surcharge_total,
                "total_bill":      result.total_bill,
            },
        })

    total = passed + failed
    print(f"\n{'='*60}")
    if failed == 0:
        print(f"\033[32mAll {total} test vectors passed.\033[0m")
    else:
        print(f"\033[31m{passed}/{total} passed, {failed} failed.\033[0m")
    print(f"{'='*60}")

    return {"passed": passed, "failed": failed, "total": total, "results": results}


def print_execution_trace(policies: list):
    """Print detailed execution trace for a set of demo scenarios."""
    policy_map = {p["policyID"]: p for p in policies}

    print(f"\n{'='*60}")
    print(f"EXECUTION TRACE -- Clause Traceability")
    print(f"{'='*60}")

    scenarios = [
        ("RES-T1",  350.0, 0.0,   0.0,   "Residential -- 350 kWh (all slabs)"),
        ("RES-T1",  350.0, 50.0,  0.0,   "Residential -- 350 kWh + 50 kWh night discount"),
        ("RES-T1",  80.0,  0.0,   0.0,   "Residential -- 80 kWh (slab 1 only)"),
        ("COM-TOU1",500.0, 0.0,  100.0,  "Commercial  -- 500 kWh + 100 kWh evening peak"),
    ]

    all_traces = []

    for pid, kwh, night, peak, label in scenarios:
        if pid not in policy_map:
            print(f"\n[SKIP] {label} -- policy {pid} not in pack")
            continue

        print(f"\nScenario: {label}")
        result = compute_bill(policy_map[pid], total_kwh=kwh, night_kwh=night, peak_kwh=peak)

        print(f"\n  Trace entries:")
        for i, entry in enumerate(result.trace, 1):
            print(f"  {i}. [{entry.step}] Clause:{entry.clause_id}")
            print(f"     {entry.description}")
            print(f"     {entry.kwh:.2f} kWh × Rs.{entry.rate:.4f}  =  Rs.{entry.amount:.2f}")

        all_traces.append({
            "scenario": label,
            "policy_id": pid,
            "total_kwh": kwh,
            "total_bill": result.total_bill,
            "trace": [
                {
                    "step": e.step,
                    "clause_id": e.clause_id,
                    "description": e.description,
                    "kwh": e.kwh,
                    "rate": e.rate,
                    "amount": e.amount,
                }
                for e in result.trace
            ],
        })

    # Save trace to file
    with open("execution_trace.json", "w") as f:
        json.dump(all_traces, f, indent=2)
    print(f"\n[Saved] execution_trace.json")

    return all_traces


def main():
    parser = argparse.ArgumentParser(description="IES Tariff Intelligence Runner")
    parser.add_argument("--offline", action="store_true",
                        help="Use cached policy_pack.json (skip network fetch)")
    parser.add_argument("--local", action="store_true",
                        help="Use built-in example data (no network, no file)")
    args = parser.parse_args()

    mode = "local" if args.local else ("offline" if args.offline else "online")

    print(f"\n{'='*60}")
    print(f"IES Tariff Intelligence -- Policy Executor")
    print(f"{'='*60}\n")

    # Step 1: Load policy pack
    pack = load_policy_pack(mode)

    if pack is None:
        # Local mode -- build inline fallback policy pack
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
        print(f"\n[Step 2] Hash Verification")
        print("  [SKIP] No hash in local mode (use online mode for hash verification)")
        hash_ok = True
        print(f"\n[Step 3] Parse Policy Pack (local)")
        for pol in policies:
            slabs, surcharges = parse_policy(pol)
            print(f"  - {pol['policyID']} : {pol['policyName']}")
            print(f"      slabs={len(slabs)}, surcharges={len(surcharges)}")
        print(f"\n[Step 4] Test Vectors")
        vector_results = run_test_vectors(policies)
        print(f"\n[Step 5] Execution Trace")
        print_execution_trace(policies)
        print(f"\n{'='*60}")
        print(f"SUMMARY")
        print(f"{'='*60}")
        print(f"  Policy pack hash : SKIPPED (local mode)")
        print(f"  Policies loaded  : {len(policies)}")
        print(f"  Test vectors     : {vector_results['passed']}/{vector_results['total']} passed")
        print(f"  Execution trace  : execution_trace.json")
        print(f"{'='*60}\n")
        return

    # Step 2: Verify hash
    print(f"\n[Step 2] Hash Verification")
    hash_ok = verify_hash(pack)
    if not hash_ok:
        print("[WARN] Hash mismatch -- data may be tampered. Continuing anyway for demo.")

    # Step 3: Parse policies
    policies = pack["dataPayload"]["policies"]
    programs = pack["dataPayload"]["programs"]
    print(f"\n[Step 3] Parse Policy Pack")
    print(f"  Programs: {len(programs)}")
    for prog in programs:
        print(f"    - {prog['id']} : {prog['programName']}")
    print(f"  Policies: {len(policies)}")
    for pol in policies:
        slabs, surcharges = parse_policy(pol)
        print(f"    - {pol['policyID']} : {pol['policyName']}")
        print(f"        slabs={len(slabs)}, surcharges={len(surcharges)}")

    # Step 4: Run test vectors
    print(f"\n[Step 4] Test Vectors")
    vector_results = run_test_vectors(policies)

    # Step 5: Execution trace
    print(f"\n[Step 5] Execution Trace")
    print_execution_trace(policies)

    # Summary
    print(f"\n{'='*60}")
    print(f"SUMMARY")
    print(f"{'='*60}")
    print(f"  Policy pack hash : {'VERIFIED' if hash_ok else 'MISMATCH'}")
    print(f"  Policies loaded  : {len(policies)}")
    print(f"  Test vectors     : {vector_results['passed']}/{vector_results['total']} passed")
    print(f"  Execution trace  : execution_trace.json")
    print(f"{'='*60}\n")


if __name__ == "__main__":
    main()
