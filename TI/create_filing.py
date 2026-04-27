#!/usr/bin/env python3
"""
Create Filing -- Infosys DISCOM ARR Filing
==========================================
DISCOM (Infosys) SERC ko ARR Filing bhejta hai.

ARR = Aggregate Revenue Requirement
  "Humara bijli supply karne ka kharcha itna hai,
   isliye humein ye tariff chahiye"

Ye filing serve hogi bpp_server.py ke zariye.
Run: python create_filing.py
"""

import hashlib
import json
from datetime import datetime, timezone


def now():
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def create_arr_filing():
    """
    Infosys DISCOM ki ARR Filing banao.
    Schema: bootcamp-kit/example-data/arr_filings.jsonld ke jaisa
    """

    filing = {
        "@context": "https://raw.githubusercontent.com/beckn/DEG/ies-specs/specification/external/schema/ies/arr/context.jsonld",
        "objectType": "ARR_FILING",
        "@type": "ARR_FILING",
        "id": "arr-infosys-discom-fy2024-25",
        "filingId": "INFOSYS/ARR/IDCL/MYT/2024-25",
        "filingDate": "2025-04-16",
        "filingType": "ANNUAL",
        "licensee": "Infosys Distribution Company Limited",
        "licenseeCode": "IDCL",
        "stateProvince": "Karnataka",
        "regulatoryCommission": "KERC",
        "controlPeriodStart": "FY 2024-25",
        "controlPeriodEnd": "FY 2024-25",
        "currency": "INR",
        "unitScale": "CRORE",
        "status": "SUBMITTED",

        # FY 2024-25 ka revenue requirement
        "fiscalYears": [
            {
                "fiscalYear": "FY 2024-25",
                "yearType": "CURRENT_YEAR",
                "amountBasis": "ESTIMATED",
                "lineItems": [
                    {
                        "lineItemId": "transmission-cost",
                        "serialNumber": 1,
                        "category": "FIXED",
                        "subCategory": "NETWORK_COST",
                        "head": "Transmission Cost",
                        "amount": 920.50
                    },
                    {
                        "lineItemId": "distribution-cost",
                        "serialNumber": 2,
                        "category": "FIXED",
                        "subCategory": "NETWORK_COST",
                        "head": "Net Distribution Cost",
                        "amount": 1750.25
                    },
                    {
                        "lineItemId": "power-purchase-cost",
                        "serialNumber": 3,
                        "category": "VARIABLE",
                        "subCategory": "ENERGY_COST",
                        "head": "Power Purchase Cost",
                        "amount": 4200.00
                    },
                    {
                        "lineItemId": "employee-cost",
                        "serialNumber": 4,
                        "category": "FIXED",
                        "subCategory": "OPEX",
                        "head": "Employee Cost",
                        "amount": 380.75
                    },
                    {
                        "lineItemId": "rd-and-loss",
                        "serialNumber": 5,
                        "category": "VARIABLE",
                        "subCategory": "LOSS",
                        "head": "Distribution Loss",
                        "amount": 210.30
                    }
                ],
                "totalRevenueRequirement": 7461.80,
                "projectedUnitsConsumed": 8500.0,
                "projectedUnitsConsumedUnit": "MU",
                "averageCostOfSupply": 8.78
            }
        ]
    }

    # Wrap in IES envelope
    canonical  = json.dumps(filing, sort_keys=True, separators=(',', ':'))
    hash_val   = hashlib.sha256(canonical.encode()).hexdigest()

    envelope = {
        "transactionId": "infosys-arr-filing-fy2024-25",
        "filingCreatedAt": now(),
        "filedBy":         "infosys-ti-bpp",
        "payloadHash":     hash_val,
        "dataPayload":     filing,
    }

    with open("arr_filing.json", "w") as f:
        json.dump(envelope, f, indent=2)

    print(f"\n{'='*55}")
    print(f"  Infosys ARR Filing Created")
    print(f"{'='*55}")
    print(f"  Filing ID  : {filing['filingId']}")
    print(f"  Licensee   : {filing['licensee']}")
    print(f"  Status     : {filing['status']}")
    print(f"  Hash       : {hash_val[:30]}...")
    print()
    print(f"  Line Items:")
    for item in filing["fiscalYears"][0]["lineItems"]:
        print(f"    {item['serialNumber']}. {item['head']:<35} Rs.{item['amount']:>8.2f} Cr")
    fy = filing["fiscalYears"][0]
    print(f"  {'-'*52}")
    print(f"  Total Revenue Requirement: Rs.{fy['totalRevenueRequirement']:.2f} Cr")
    print(f"  Avg Cost of Supply       : Rs.{fy['averageCostOfSupply']:.2f}/kWh")
    print(f"{'='*55}")
    print(f"  Saved to: arr_filing.json")
    print(f"{'='*55}\n")

    return envelope


if __name__ == "__main__":
    create_arr_filing()
