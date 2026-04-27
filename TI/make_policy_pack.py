#!/usr/bin/env python3
"""
Infosys TI - Tariff Pack Producer
===================================
Apna khud ka tariff pack banao aur save karo.

Ye script:
  1. Infosys-defined tariff policies banata hai
  2. SHA-256 hash compute karta hai
  3. infosys_policy_pack.json save karta hai
  4. bpp_server.py is file ko serve karega

Run: python make_policy_pack.py
"""

import hashlib
import json
from datetime import datetime, timezone


def now():
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def make_policy_pack():
    """
    Infosys ka apna tariff pack.

    Hum SERC ki jagah ek naya publisher hain:
      Publisher  : Infosys TI Tariff Engine
      Consumer   : Any DISCOM / VAS provider
      Data       : Residential + Commercial tariff slabs
    """

    data_payload = {
        "@type":       "IES_PolicyPack",
        "objectType":  "POLICY_PACK",
        "packName":    "Infosys IES Tariff Pack - FY 2024-25",
        "publishedBy": "infosys-ti-bpp",
        "version":     "1.0.0",

        # Programs = grouping of policies
        "programs": [
            {
                "id":          "infosys-res-program-001",
                "programName": "Infosys Residential Tariff Program",
                "description": "Telescopic slab billing for residential consumers",
                "policyIds":   ["INF-RES-T1"]
            },
            {
                "id":          "infosys-com-program-001",
                "programName": "Infosys Commercial ToD Program",
                "description": "Time-of-Day billing for commercial consumers",
                "policyIds":   ["INF-COM-TOU1"]
            }
        ],

        # Policies = actual tariff rules
        "policies": [

            # ── Residential: Telescopic slabs ──────────────────────
            {
                "policyID":   "INF-RES-T1",
                "policyName": "Infosys Residential Telescopic Standard",
                "applicableTo": "RESIDENTIAL",
                "currency":   "INR",
                "unit":       "KWH",

                # Telescopic: jitna zyada use, utna zyada rate
                # Slab 1: 0-100 kWh   → Rs. 4.00/kWh  (low consumers)
                # Slab 2: 101-300 kWh → Rs. 7.00/kWh  (medium)
                # Slab 3: 301+ kWh    → Rs. 10.00/kWh (high)
                "energySlabs": [
                    {"id": "inf-s1", "start": 0,   "end": 100,  "price": 4.00},
                    {"id": "inf-s2", "start": 101,  "end": 300,  "price": 7.00},
                    {"id": "inf-s3", "start": 301,  "end": None, "price": 10.00},
                ],

                # Night discount: 23:00 - 05:00 (6 hrs) → -10%
                "surchargeTariffs": [
                    {
                        "id":    "inf-night-discount",
                        "interval": {
                            "start":    "T23:00:00Z",
                            "duration": "PT6H"
                        },
                        "value": -10,
                        "unit":  "PERCENT",
                        "description": "Off-peak night discount (-10%)"
                    }
                ]
            },

            # ── Commercial: Flat rate + Evening peak surcharge ─────
            {
                "policyID":   "INF-COM-TOU1",
                "policyName": "Infosys Commercial Time-of-Day Standard",
                "applicableTo": "COMMERCIAL",
                "currency":   "INR",
                "unit":       "KWH",

                # Flat base rate for all commercial
                "energySlabs": [
                    {"id": "inf-com-base", "start": 0, "end": None, "price": 9.00},
                ],

                # Evening peak: 18:00 - 22:00 (4 hrs) → +Rs.2.0/kWh
                "surchargeTariffs": [
                    {
                        "id":    "inf-evening-peak",
                        "interval": {
                            "start":    "T18:00:00Z",
                            "duration": "PT4H"
                        },
                        "value": 2.0,
                        "unit":  "INR_PER_KWH",
                        "description": "Evening peak surcharge (+Rs.2.0/kWh)"
                    }
                ]
            }
        ]
    }

    # SHA-256 hash — tamper-proof proof
    canonical  = json.dumps(data_payload, sort_keys=True, separators=(',', ':'))
    hash_val   = hashlib.sha256(canonical.encode()).hexdigest()

    pack = {
        "transactionId": "infosys-ti-pack-v1",
        "fetchedAt":     now(),
        "publishedBy":   "infosys-ti-bpp",
        "payloadHash":   hash_val,
        "dataPayload":   data_payload,
    }

    # Save
    with open("infosys_policy_pack.json", "w") as f:
        json.dump(pack, f, indent=2)

    # Print summary
    print(f"\n{'='*55}")
    print(f"  Infosys Tariff Pack Created")
    print(f"{'='*55}")
    print(f"  Hash      : {hash_val[:30]}...")
    print(f"  Programs  : {len(data_payload['programs'])}")
    print(f"  Policies  : {len(data_payload['policies'])}")
    print()
    for p in data_payload['policies']:
        slabs = p['energySlabs']
        surcharges = p['surchargeTariffs']
        print(f"  [{p['policyID']}] {p['policyName']}")
        print(f"    Slabs:")
        for s in slabs:
            end = f"{s['end']}" if s['end'] else "unlimited"
            print(f"      {s['id']:15s}  {s['start']:>4}-{end:<10}  Rs.{s['price']:.2f}/kWh")
        print(f"    Surcharges:")
        for sur in surcharges:
            sign = "+" if sur['value'] > 0 else ""
            unit = "%" if sur['unit'] == "PERCENT" else "INR/kWh"
            print(f"      {sur['id']:20s}  {sign}{sur['value']}{unit}  [{sur['interval']['start']} for {sur['interval']['duration']}]")
        print()

    print(f"  Saved to  : infosys_policy_pack.json")
    print(f"{'='*55}\n")

    return pack


if __name__ == "__main__":
    pack = make_policy_pack()

    # Verify with tariff engine
    print("Verifying with tariff engine...\n")
    from tariff_engine import compute_bill

    policies = pack["dataPayload"]["policies"]
    policy_map = {p["policyID"]: p for p in policies}

    compute_bill(policy_map["INF-RES-T1"],  total_kwh=350.0, timestamp="FY 2024-25")
    compute_bill(policy_map["INF-COM-TOU1"], total_kwh=500.0, peak_kwh=100.0, timestamp="FY 2024-25")
