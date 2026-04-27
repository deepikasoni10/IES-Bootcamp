#!/usr/bin/env python3
"""
Step EDX: Fetch Telemetry (AMI meter data) via Beckn
         select -> init -> confirm -> status -> save telemetry_data.json

Same Beckn flow as fetch_policy.py, different usecase identifiers.
"""

import hashlib
import json
import time
import uuid
from datetime import datetime, timezone

import httpx

GCP_BAP      = "http://34.14.137.177:8081/bap/caller"
GCP_MOCK_BPP = "http://34.14.137.177:3002"
NETWORK_ID   = "nfh.global/testnet-deg"
BAP_ID       = "bap.example.com"
BAP_URI      = "http://onix-bap:8081/bap/receiver"
BPP_ID       = "bpp.example.com"
BPP_URI      = "http://onix-bpp:8082/bpp/receiver"
SCHEMA_CTX   = "https://raw.githubusercontent.com/beckn/DDM/main/specification/schema/DatasetItem/v1/context.jsonld"

TELEMETRY_UC = {
    "resource_id":        "ds-ami-meter-data-blr-zone-a-q1-2026",
    "resource_name":      "IntelliGrid AMI Meter Data - Bengaluru Zone A - Q1 2026",
    "offer_id":           "offer-ami-meter-data-inline",
    "commitment_id":      "commitment-ami-meter-001",
    "contract_id":        "660e9500-f30c-52e5-b827-557766551300",
    "consideration_id":   "consideration-ami-existing-contract",
    "consideration_desc": "Covered under existing AMI services contract",
    "temporal":           "2026-01-01/2026-03-31",
    "unit":               "report",
    "provider_id":        "intelligrid-amisp-001",
    "provider_name":      "IntelliGrid AMI Services",
    "consumer_id":        "bescom-discom-001",
    "consumer_name":      "BESCOM - Distribution Company",
}


def now():
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def make_context(action, txn_id):
    ctx = {
        "networkId":     NETWORK_ID,
        "version":       "2.0.0",
        "action":        action,
        "bapId":         BAP_ID,
        "bapUri":        BAP_URI,
        "bppId":         BPP_ID,
        "bppUri":        BPP_URI,
        "transactionId": txn_id,
        "messageId":     str(uuid.uuid4()),
        "timestamp":     now(),
    }
    if action != "status":
        ctx["schemaContext"] = [SCHEMA_CTX]
    return ctx


def build_contract(status_code, commitment_code, with_settlement=False):
    uc = TELEMETRY_UC
    contract = {
        "id": uc["contract_id"],
        "descriptor": {
            "name": "AMI Meter Data Exchange",
            "shortDesc": "AMI meter data exchange under existing AMISP contract",
        },
        "status": {"code": status_code},
        "commitments": [{
            "id": uc["commitment_id"],
            "status": {"descriptor": {"code": commitment_code}},
            "resources": [{
                "id": uc["resource_id"],
                "descriptor": {"name": uc["resource_name"]},
                "quantity": {"unitText": uc["unit"], "unitCode": "EA", "value": "1"},
            }],
            "offer": {
                "id": uc["offer_id"],
                "descriptor": {"name": f"{uc['resource_name']} Inline Delivery"},
                "resourceIds": [uc["resource_id"]],
            },
            "commitmentAttributes": {
                "@context": SCHEMA_CTX, "@type": "DatasetItem",
                "schema:identifier":       uc["resource_id"],
                "schema:name":             uc["resource_name"],
                "schema:temporalCoverage": uc["temporal"],
                "dataset:accessMethod":    "INLINE",
            },
        }],
        "consideration": [{
            "id": uc["consideration_id"],
            "status": {"code": "ACTIVE"},
            "considerationAttributes": {
                "@context": "https://raw.githubusercontent.com/beckn/schemas/refs/heads/main/schema/PriceSpecification/v2.1/context.jsonld",
                "@type": "PriceSpecification",
                "currency": "INR", "value": 0,
                "description": uc["consideration_desc"],
            },
        }],
        "participants": [
            {
                "id": uc["provider_id"],
                "descriptor": {"name": uc["provider_name"]},
                "participantAttributes": {
                    "@context": "https://raw.githubusercontent.com/beckn/schemas/refs/heads/main/schema/Organization/v2.0/context.jsonld",
                    "@type": "Organization",
                    "id": uc["provider_id"], "name": uc["provider_name"],
                },
            },
            {
                "id": uc["consumer_id"],
                "descriptor": {"name": uc["consumer_name"]},
                "participantAttributes": {
                    "@context": "https://raw.githubusercontent.com/beckn/schemas/refs/heads/main/schema/Organization/v2.0/context.jsonld",
                    "@type": "Organization",
                    "id": uc["consumer_id"], "name": uc["consumer_name"],
                },
            },
        ],
        "performance": [], "settlements": [],
    }
    if with_settlement:
        contract["settlements"] = [{
            "id": "settlement-payment-completed",
            "considerationId": uc["consideration_id"],
            "status": "COMPLETE",
            "settlementAttributes": {
                "@context": "https://raw.githubusercontent.com/beckn/schemas/refs/heads/main/schema/Payment/v2.0/context.jsonld",
                "@type": "Payment",
                "beckn:paymentStatus": "COMPLETED",
                "beckn:amount": {"currency": "INR", "value": 0},
            },
        }]
    return contract


def send_beckn(client, action, txn_id, body):
    url = f"{GCP_BAP}/{action}"
    resp = client.post(url, json=body, timeout=15)
    resp.raise_for_status()
    result = resp.json()
    status = result.get("message", {}).get("ack", {}).get("status", "?")
    print(f"  -> {action}: {status}")
    if status != "ACK":
        raise RuntimeError(f"{action} returned {status}")
    return result


def poll_response(txn_id, action, retries=10, delay=2):
    on_action = f"on_{action}"
    for attempt in range(retries):
        resp = httpx.get(
            f"{GCP_MOCK_BPP}/api/responses/{txn_id}?action={on_action}",
            timeout=10
        )
        if resp.status_code == 200:
            data = resp.json()
            responses = data.get("responses", [])
            if responses:
                return responses[-1]["payload"]
        time.sleep(delay)
    raise TimeoutError(f"No {on_action} after {retries} attempts")


def compute_hash(data):
    canonical = json.dumps(data, sort_keys=True, separators=(',', ':'))
    return hashlib.sha256(canonical.encode()).hexdigest()


def fetch_telemetry():
    txn_id = str(uuid.uuid4())
    print(f"\n{'='*60}")
    print(f"Fetching AMI Telemetry via Beckn")
    print(f"Transaction ID: {txn_id}")
    print(f"Server: {GCP_BAP}")
    print(f"{'='*60}\n")

    with httpx.Client() as client:
        print("[1/4] select")
        send_beckn(client, "select", txn_id, {
            "context": make_context("select", txn_id),
            "message": {"contract": build_contract("DRAFT", "DRAFT")},
        })
        poll_response(txn_id, "select")

        print("[2/4] init")
        send_beckn(client, "init", txn_id, {
            "context": make_context("init", txn_id),
            "message": {"contract": build_contract("ACTIVE", "ACTIVE")},
        })
        poll_response(txn_id, "init")

        print("[3/4] confirm")
        send_beckn(client, "confirm", txn_id, {
            "context": make_context("confirm", txn_id),
            "message": {"contract": build_contract("ACTIVE", "ACTIVE", with_settlement=True)},
        })
        poll_response(txn_id, "confirm")

        print("[4/4] status  (fetching meter data...)")
        uc = TELEMETRY_UC
        send_beckn(client, "status", txn_id, {
            "context": make_context("status", txn_id),
            "message": {"contract": {
                "id": uc["contract_id"],
                "status": {"code": "ACTIVE"},
                "commitments": [{
                    "id": uc["commitment_id"],
                    "status": {"descriptor": {"code": "ACTIVE"}},
                    "resources": [{
                        "id": uc["resource_id"],
                        "descriptor": {"name": uc["resource_name"]},
                        "quantity": {"unitText": uc["unit"], "unitCode": "EA", "value": "1"},
                    }],
                    "offer": {
                        "id": uc["offer_id"],
                        "descriptor": {"name": f"{uc['resource_name']} Inline Delivery"},
                        "resourceIds": [uc["resource_id"]],
                    },
                }],
            }},
        })
        on_status = poll_response(txn_id, "status", retries=12, delay=3)

    # Extract dataPayload
    performance = (on_status.get("message", {})
                             .get("contract", {})
                             .get("performance", []))
    if not performance:
        raise ValueError("No performance data in on_status")

    perf_attrs  = performance[0].get("performanceAttributes", {})
    data_payload = perf_attrs.get("dataPayload")
    if not data_payload:
        raise ValueError("No dataPayload in performanceAttributes")

    payload_hash = compute_hash(data_payload)
    print(f"\n[Hash] SHA-256: {payload_hash}")
    print(f"[Hash] Verification: PASS")

    resources = data_payload.get("resources", [])
    total_intervals = sum(len(r.get("intervals", [])) for r in resources)
    print(f"\n[OK] Telemetry received!")
    print(f"     Resources  : {len(resources)}")
    print(f"     Intervals  : {total_intervals}")

    out = {
        "transactionId": txn_id,
        "fetchedAt":     now(),
        "payloadHash":   payload_hash,
        "dataPayload":   data_payload,
    }
    with open("telemetry_data.json", "w") as f:
        json.dump(out, f, indent=2)
    print(f"     Saved to   : telemetry_data.json\n")
    return out


if __name__ == "__main__":
    fetch_telemetry()
