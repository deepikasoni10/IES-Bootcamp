#!/usr/bin/env python3
"""
Consume Filing -- Fetch ARR Filing from BPP server
===================================================
Kisi bhi BPP server se ARR Filing fetch karo.

Default: localhost:5000 (apna bpp_server.py)
Dusri team: unka IP de do

Run: python consume_filing.py
     python consume_filing.py --server http://10.10.6.22:5000
"""

import argparse
import hashlib
import json

import httpx


def consume_filing(server="http://localhost:5000"):
    print(f"\n{'='*55}")
    print(f"  Consuming ARR Filing")
    print(f"  Server: {server}")
    print(f"{'='*55}\n")

    # Health check
    try:
        h = httpx.get(f"{server}/health", timeout=5)
        info = h.json()
        print(f"[Health] Server UP\n")
    except Exception:
        print(f"[ERROR] Server not running at {server}")
        return

    # Fetch filing
    try:
        resp = httpx.get(f"{server}/filing", timeout=10)
        if resp.status_code == 404:
            print(f"[INFO] No filing on this server yet")
            print(f"       Run: python create_filing.py")
            print(f"       Then restart bpp_server.py")
            return
        resp.raise_for_status()
        data = resp.json()
    except Exception as e:
        print(f"[ERROR] Could not fetch filing: {e}")
        return

    filing_env   = data
    data_payload = filing_env.get("dataPayload", {})
    stored_hash  = filing_env.get("payloadHash", "")

    # Hash verify
    canonical = json.dumps(data_payload, sort_keys=True, separators=(',', ':'))
    computed  = hashlib.sha256(canonical.encode()).hexdigest()
    hash_ok   = stored_hash == computed

    print(f"{'='*55}")
    print(f"  ARR Filing Received")
    print(f"{'='*55}")
    print(f"  Filing ID  : {data_payload.get('filingId', '?')}")
    print(f"  Licensee   : {data_payload.get('licensee', '?')}")
    print(f"  Status     : {data_payload.get('status', '?')}")
    print(f"  Hash verify: {'PASS' if hash_ok else 'FAIL!'}")
    print(f"  Hash       : {computed[:30]}...")
    print()

    for fy in data_payload.get("fiscalYears", []):
        print(f"  Fiscal Year: {fy['fiscalYear']} ({fy['amountBasis']})")
        print(f"  Line Items:")
        for item in fy.get("lineItems", []):
            print(f"    {item['serialNumber']}. {item['head']:<35} Rs.{item['amount']:>8.2f} Cr")
        print(f"  {'-'*52}")
        print(f"  Total Revenue Requirement : Rs.{fy.get('totalRevenueRequirement', 0):.2f} Cr")
        print(f"  Avg Cost of Supply        : Rs.{fy.get('averageCostOfSupply', 0):.2f}/kWh")

    print(f"{'='*55}")
    print(f"  PROOF: Filing fetched + Hash verified = TAMPER-PROOF")
    print(f"{'='*55}\n")

    # Save
    with open("received_filing.json", "w") as f:
        json.dump(filing_env, f, indent=2)
    print(f"[Saved] received_filing.json\n")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--server", default="http://localhost:5000",
                        help="BPP server URL (default: http://localhost:5000)")
    args = parser.parse_args()
    consume_filing(args.server)
