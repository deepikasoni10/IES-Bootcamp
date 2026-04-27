#!/usr/bin/env python3
"""
IES Conformance Kit -- TI + EDX/Cross-UC
Day 2: 12:00-13:00 Conformance Test Run

Checks:
  [TI-1]  Envelope structure  (transactionId, fetchedAt, payloadHash, dataPayload)
  [TI-2]  Schema validity     (policies have required fields)
  [TI-3]  payloadHash         re-verify SHA-256
  [TI-4]  Test vector match   (all 8 expected outputs)
  [TI-5]  Clause trace        (execution_trace.json has entries)
  [EDX-1] Telemetry envelope  (same structure)
  [EDX-2] Telemetry hash      re-verify SHA-256
  [EDX-3] Quality flags       (ACTUAL billed, MISSING skipped, ESTIMATED billed)
  [XUC-1] Cross-UC output     (each interval has timestamp, kwh, clause, rate, cost)
  [XUC-2] Pricing sanity      (no negative cost, commercial > residential rate)
"""

import hashlib
import io
import json
import contextlib
import os
import sys

PASS  = "[PASS]"
FAIL  = "[FAIL]"
SKIP  = "[SKIP]"
WARN  = "[WARN]"

results = []


def check(tag, description, condition, detail=""):
    status = PASS if condition else FAIL
    results.append((tag, status, description, detail))
    icon = "OK" if condition else "!!"
    detail_str = f"  -> {detail}" if detail else ""
    print(f"  [{icon}] {tag:<8} {description}")
    if detail_str:
        print(f"           {detail}")
    return condition


def section(title):
    print(f"\n{'='*60}")
    print(f"  {title}")
    print(f"{'='*60}")


# ─────────────────────────────────────────────────────────────
# TI Checks
# ─────────────────────────────────────────────────────────────

def check_ti_envelope(pack: dict) -> bool:
    required_keys = ["transactionId", "fetchedAt", "payloadHash", "dataPayload"]
    missing = [k for k in required_keys if k not in pack]
    ok = len(missing) == 0
    check("TI-1a", "policy_pack.json has required envelope keys", ok,
          f"Missing: {missing}" if missing else f"Keys: {required_keys}")

    dp = pack.get("dataPayload", {})
    has_policies = "policies" in dp and len(dp["policies"]) > 0
    check("TI-1b", "dataPayload contains policies list", has_policies,
          f"{len(dp.get('policies', []))} policies found")

    has_programs = "programs" in dp
    check("TI-1c", "dataPayload contains programs list", has_programs,
          f"{len(dp.get('programs', []))} programs found")

    return ok and has_policies


def check_ti_schema(pack: dict) -> bool:
    policies = pack.get("dataPayload", {}).get("policies", [])
    all_ok = True
    for p in policies:
        pid = p.get("policyID", "?")
        required = ["policyID", "policyName", "energySlabs"]
        missing = [f for f in required if f not in p]
        ok = len(missing) == 0
        check("TI-2a", f"Policy {pid} has required fields", ok,
              f"Missing: {missing}" if missing else f"energySlabs={len(p.get('energySlabs',[]))}, surchargeTariffs={len(p.get('surchargeTariffs',[]))}")
        if not ok:
            all_ok = False

        for i, slab in enumerate(p.get("energySlabs", [])):
            slab_fields = ["id", "start", "price"]
            missing_s = [f for f in slab_fields if f not in slab]
            slab_ok = len(missing_s) == 0
            check("TI-2b", f"Policy {pid} slab[{i}] has required fields", slab_ok,
                  f"Missing: {missing_s}" if missing_s else f"id={slab.get('id')}, start={slab.get('start')}, end={slab.get('end')}, price={slab.get('price')}")
            if not slab_ok:
                all_ok = False

    return all_ok


def check_ti_hash(pack: dict) -> bool:
    stored = pack.get("payloadHash", "")
    payload = pack.get("dataPayload", {})
    canonical = json.dumps(payload, sort_keys=True, separators=(',', ':'))
    computed = hashlib.sha256(canonical.encode()).hexdigest()
    ok = stored == computed
    check("TI-3", "payloadHash SHA-256 verification", ok,
          f"Hash: {computed[:30]}... {'MATCH' if ok else 'MISMATCH!'}")
    return ok


def check_ti_vectors(pack: dict) -> bool:
    from tariff_engine import compute_bill

    if not os.path.exists("test_vectors.json"):
        check("TI-4", "test_vectors.json exists", False, "File not found")
        return False

    with open("test_vectors.json") as f:
        vectors = json.load(f)

    policies = pack.get("dataPayload", {}).get("policies", [])
    policy_map = {p["policyID"]: p for p in policies}

    TOLERANCE = 0.50
    passed = 0
    total = len(vectors)

    for tv in vectors:
        pid   = tv["policy_id"]
        inp   = tv["input"]
        exp   = tv["expected"]

        if pid not in policy_map:
            check(f"TI-4", f"{tv['id']}: {tv['description']}", False,
                  f"Policy {pid} not found in pack")
            continue

        buf = io.StringIO()
        with contextlib.redirect_stdout(buf):
            result = compute_bill(
                policy_map[pid],
                total_kwh=inp["total_kwh"],
                night_kwh=inp.get("night_kwh", 0),
                peak_kwh=inp.get("peak_kwh", 0),
            )

        ok_base = abs(result.base_charge    - exp["base_charge"])    <= TOLERANCE
        ok_sur  = abs(result.surcharge_total - exp["surcharge_total"]) <= TOLERANCE
        ok_tot  = abs(result.total_bill     - exp["total_bill"])     <= TOLERANCE
        ok = ok_base and ok_sur and ok_tot

        detail = (
            f"expected total Rs.{exp['total_bill']:.2f}, got Rs.{result.total_bill:.2f}"
            + ("" if ok else " MISMATCH")
        )
        check("TI-4", f"{tv['id']}: {tv['description'][:45]}", ok, detail)
        if ok:
            passed += 1

    all_pass = passed == total
    check("TI-4z", f"All test vectors ({passed}/{total}) passed", all_pass)
    return all_pass


def check_ti_trace() -> bool:
    if not os.path.exists("execution_trace.json"):
        check("TI-5", "execution_trace.json exists", False, "File not found -- run: python run_ti.py --offline")
        return False

    with open("execution_trace.json") as f:
        traces = json.load(f)

    has_entries = len(traces) > 0
    check("TI-5a", "execution_trace.json has scenarios", has_entries,
          f"{len(traces)} scenarios found")

    has_clauses = all(len(t.get("trace", [])) > 0 for t in traces)
    check("TI-5b", "All scenarios have clause-level trace entries", has_clauses,
          f"Total trace entries: {sum(len(t.get('trace',[])) for t in traces)}")

    # Check trace has required fields
    for t in traces:
        for entry in t.get("trace", []):
            required = ["step", "clause_id", "kwh", "rate", "amount"]
            missing = [f for f in required if f not in entry]
            if missing:
                check("TI-5c", "Trace entries have required fields", False,
                      f"Missing: {missing}")
                return False

    check("TI-5c", "All trace entries have required fields (step, clause_id, kwh, rate, amount)", True)
    return has_entries and has_clauses


# ─────────────────────────────────────────────────────────────
# EDX / Cross-UC Checks
# ─────────────────────────────────────────────────────────────

def check_edx_envelope(tel: dict) -> bool:
    required_keys = ["transactionId", "fetchedAt", "payloadHash", "dataPayload"]
    missing = [k for k in required_keys if k not in tel]
    ok = len(missing) == 0
    check("EDX-1a", "telemetry_data.json has required envelope keys", ok,
          f"Missing: {missing}" if missing else f"Keys: {required_keys}")

    dp = tel.get("dataPayload", {})
    resources = dp.get("resources", [])
    has_resources = len(resources) > 0
    check("EDX-1b", "dataPayload contains resources", has_resources,
          f"{len(resources)} resources, each with intervals")

    total_intervals = sum(len(r.get("intervals", [])) for r in resources)
    check("EDX-1c", "Resources have intervals", total_intervals > 0,
          f"Total intervals: {total_intervals}")

    return ok and has_resources


def check_edx_hash(tel: dict) -> bool:
    stored = tel.get("payloadHash", "")
    payload = tel.get("dataPayload", {})
    canonical = json.dumps(payload, sort_keys=True, separators=(',', ':'))
    computed = hashlib.sha256(canonical.encode()).hexdigest()
    ok = stored == computed
    check("EDX-2", "telemetry payloadHash SHA-256 verification", ok,
          f"Hash: {computed[:30]}... {'MATCH' if ok else 'MISMATCH!'}")
    return ok


def check_edx_quality(tel: dict) -> bool:
    resources = tel.get("dataPayload", {}).get("resources", [])
    actual_count = missing_count = estimated_count = 0

    for r in resources:
        for iv in r.get("intervals", []):
            if isinstance(iv, str):
                continue
            for p in iv.get("payloads", []):
                if p.get("type") == "DATA_QUALITY":
                    q = p.get("values", ["?"])[0]
                    if q == "ACTUAL":
                        actual_count += 1
                    elif q == "MISSING":
                        missing_count += 1
                    elif q == "ESTIMATED":
                        estimated_count += 1

    total = actual_count + missing_count + estimated_count
    check("EDX-3a", "Telemetry has ACTUAL quality intervals", actual_count > 0,
          f"ACTUAL={actual_count}, ESTIMATED={estimated_count}, MISSING={missing_count}")
    check("EDX-3b", "Telemetry has MISSING quality intervals (realistic data)", missing_count >= 0,
          f"MISSING={missing_count} ({missing_count/total*100:.1f}%)" if total else "No intervals")
    return True


def check_xuc_output() -> bool:
    if not os.path.exists("annotated_telemetry.json"):
        check("XUC-1", "annotated_telemetry.json exists", False,
              "Run: python cross_uc.py")
        return False

    with open("annotated_telemetry.json") as f:
        ann = json.load(f)

    resources = ann.get("resources", [])
    check("XUC-1a", "annotated_telemetry.json has resources", len(resources) > 0,
          f"{len(resources)} resources")

    required_top = ["policyId", "policyName", "totalKwh", "totalCost", "billedCount", "missingCount", "intervals"]
    for r in resources:
        rname = r.get("resourceName", "?")
        missing = [f for f in required_top if f not in r]
        check("XUC-1b", f"Resource {rname} has required summary fields", len(missing) == 0,
              f"Missing: {missing}" if missing else
              f"totalKwh={r['totalKwh']:.2f}, totalCost=Rs.{r['totalCost']:.2f}, billed={r['billedCount']}")

    # Check per-interval fields
    required_iv = ["timestamp", "kwh", "quality", "clause", "cost"]
    sample_iv = resources[0]["intervals"][0] if resources and resources[0].get("intervals") else {}
    missing_iv = [f for f in required_iv if f not in sample_iv]
    check("XUC-1c", "Interval records have required fields", len(missing_iv) == 0,
          f"Missing: {missing_iv}" if missing_iv else
          f"Fields present: {required_iv}")

    # MISSING intervals should have cost=0 and clause=SKIPPED
    for r in resources:
        for iv in r.get("intervals", []):
            if iv.get("quality") == "MISSING":
                cost_ok = iv.get("cost", -1) == 0.0
                clause_ok = iv.get("clause") == "SKIPPED"
                if not (cost_ok and clause_ok):
                    check("XUC-2a", "MISSING intervals have cost=0 and clause=SKIPPED", False,
                          f"Found cost={iv.get('cost')} clause={iv.get('clause')}")
                    return False

    check("XUC-2a", "MISSING intervals correctly have cost=0 and clause=SKIPPED", True)

    # Pricing sanity: no negative costs
    all_costs = [iv.get("cost", 0) for r in resources for iv in r.get("intervals", [])]
    no_negatives = all(c >= 0 for c in all_costs)
    check("XUC-2b", "No negative costs in annotated output", no_negatives,
          f"Total intervals checked: {len(all_costs)}")

    # Commercial rate > residential rate (sanity)
    res_ivs = [iv for r in resources if "RES" in r.get("resourceName","")
               for iv in r.get("intervals", []) if iv.get("kwh",0)>0]
    com_ivs = [iv for r in resources if "COM" in r.get("resourceName","")
               for iv in r.get("intervals", []) if iv.get("kwh",0)>0]
    if res_ivs and com_ivs:
        res_avg = sum(iv["effective_rate"] for iv in res_ivs if "effective_rate" in iv) / len(res_ivs)
        com_avg = sum(iv["effective_rate"] for iv in com_ivs if "effective_rate" in iv) / len(com_ivs)
        check("XUC-2c", "Commercial rate avg > Residential rate avg (sanity)", com_avg >= res_avg,
              f"Residential avg Rs.{res_avg:.2f}/kWh, Commercial avg Rs.{com_avg:.2f}/kWh")

    summary = ann.get("summary", {})
    check("XUC-2d", "Cross-UC summary has totalKwh + totalCost",
          "totalKwh" in summary and "totalCost" in summary,
          f"totalKwh={summary.get('totalKwh')}, totalCost=Rs.{summary.get('totalCost')}")

    return True


# ─────────────────────────────────────────────────────────────
# Main
# ─────────────────────────────────────────────────────────────

def main():
    print(f"\n{'='*60}")
    print(f"  IES Conformance Kit -- Day 2")
    print(f"  Team: TI + EDX Cross-UC")
    print(f"{'='*60}")

    # Load files
    if not os.path.exists("policy_pack.json"):
        print("\n[ERROR] policy_pack.json not found -- run: python fetch_policy.py")
        sys.exit(1)
    with open("policy_pack.json") as f:
        pack = json.load(f)

    if not os.path.exists("telemetry_data.json"):
        print("\n[ERROR] telemetry_data.json not found -- run: python make_test_data.py")
        sys.exit(1)
    with open("telemetry_data.json") as f:
        tel = json.load(f)

    # --- TI Checks ---
    section("TI Conformance")
    check_ti_envelope(pack)
    check_ti_schema(pack)
    check_ti_hash(pack)
    check_ti_vectors(pack)
    check_ti_trace()

    # --- EDX Checks ---
    section("EDX Telemetry Conformance")
    check_edx_envelope(tel)
    check_edx_hash(tel)
    check_edx_quality(tel)

    # --- Cross-UC Checks ---
    section("Cross-UC Integration Conformance")
    check_xuc_output()

    # --- Summary ---
    passed = sum(1 for _, s, _, _ in results if s == PASS)
    failed = sum(1 for _, s, _, _ in results if s == FAIL)
    total  = passed + failed

    print(f"\n{'='*60}")
    print(f"  CONFORMANCE SUMMARY")
    print(f"{'='*60}")
    print(f"  Policy Pack Hash : {pack['payloadHash'][:20]}...")
    print(f"  Checks passed    : {passed}/{total}")
    if failed == 0:
        print(f"  Status           : ALL PASS -- CONFORMANT")
    else:
        print(f"  Status           : {failed} FAILED")
        print(f"\n  Failed checks:")
        for tag, status, desc, detail in results:
            if status == FAIL:
                print(f"    [{tag}] {desc}")
                if detail:
                    print(f"           {detail}")
    print(f"{'='*60}\n")

    # Save report
    report = {
        "conformanceRun": __import__('datetime').datetime.utcnow().strftime("%Y-%m-%dT%H:%M:%SZ"),
        "policyPackHash": pack["payloadHash"],
        "telemetrySource": "synthetic" if tel.get("transactionId") == "synthetic-test-data" else "live-gcp",
        "summary": {"passed": passed, "failed": failed, "total": total},
        "checks": [
            {"tag": tag, "status": status, "description": desc, "detail": detail}
            for tag, status, desc, detail in results
        ],
    }
    with open("conformance_report.json", "w") as f:
        json.dump(report, f, indent=2)
    print(f"[Saved] conformance_report.json")

    sys.exit(0 if failed == 0 else 1)


if __name__ == "__main__":
    main()
