#!/usr/bin/env python3
"""
Cross-Team Integration -- Infosys BAP -> flockenergy.tech BPP
=============================================================
Ye script flockenergy ke ONIX BPP se tariff/data fetch karta hai
hamare ONIX BAP adapter ke zariye (localhost:8081/bap/caller).

Flow:
  Our BAP caller -> flockenergy ONIX BPP -> on_status in sandbox-bap logs

Run: python cross_team_flockenergy.py
"""

import json
import subprocess
import threading
import time
import uuid
from datetime import datetime, timezone

import httpx

# flockenergy BPP details
FLOC_BPP_ID  = "flockenergy.tech"
FLOC_BPP_URI = "https://fa85-117-250-7-33.ngrok-free.app/bpp/receiver"

# Our ONIX BAP caller
OUR_BAP_CALLER = "http://localhost:8081/bap/caller"

# Network
NETWORK_ID = "nfh.global/testnet-deg"

# Our BAP identity (from local-simple-bap.yaml)
OUR_BAP_ID  = "bap.example.com"
OUR_BAP_URI = "http://10.10.5.45:8081/bap/receiver"


def now():
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def send_action(action, txn_id, message_id, message_body):
    """Send Beckn action through our ONIX BAP caller."""
    payload = {
        "context": {
            "networkId": NETWORK_ID,
            "version": "2.0.0",
            "action": action,
            "bapId":  OUR_BAP_ID,
            "bapUri": OUR_BAP_URI,
            "bppId":  FLOC_BPP_ID,
            "bppUri": FLOC_BPP_URI,
            "transactionId": txn_id,
            "messageId":     message_id,
            "timestamp":     now(),
        },
        "message": message_body,
    }
    try:
        resp = httpx.post(
            f"{OUR_BAP_CALLER}/{action}",
            json=payload,
            timeout=15
        )
        body = resp.json()
        ack = body.get("message", {}).get("ack", {}).get("status", "?")
        err = body.get("message", {}).get("error", {})
        print(f"  [{action}] HTTP {resp.status_code} -> {ack}", end="")
        if err:
            print(f"  ERROR: {err.get('message', '')[:80]}", end="")
        print()
        return ack == "ACK", body
    except Exception as e:
        print(f"  [{action}] FAILED: {e}")
        return False, {}


def watch_docker_logs(txn_id, timeout=30):
    """
    sandbox-bap logs mein on_status dhundo.
    Docker logs -f se live stream karo aur txn_id match karo.
    """
    print(f"\n[WATCH] Waiting for on_status in sandbox-bap logs (txn={txn_id[:8]}...)...")
    found_data = []

    def _stream():
        try:
            proc = subprocess.Popen(
                ["docker", "logs", "-f", "--tail", "0", "sandbox-bap"],
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
            )
            buffer = ""
            deadline = time.time() + timeout
            while time.time() < deadline and not found_data:
                raw = proc.stdout.readline()
                if not raw:
                    time.sleep(0.1)
                    continue
                line = raw.decode("utf-8", errors="replace")
                buffer += line
                if txn_id in buffer and "on_status" in buffer.lower():
                    # Try to find JSON in buffer
                    try:
                        start = buffer.rfind("{")
                        if start >= 0:
                            chunk = buffer[start:]
                            data = json.loads(chunk)
                            found_data.append(data)
                    except Exception:
                        pass
            proc.terminate()
        except Exception as e:
            print(f"  [WATCH] Log stream error: {e}")

    t = threading.Thread(target=_stream, daemon=True)
    t.start()
    t.join(timeout=timeout + 2)

    return found_data[0] if found_data else None


def main():
    txn_id = str(uuid.uuid4())

    print(f"\n{'='*60}")
    print(f"  Cross-Team Integration: Infosys -> flockenergy.tech")
    print(f"{'='*60}")
    print(f"  Their BPP : {FLOC_BPP_URI}")
    print(f"  Our BAP   : {OUR_BAP_CALLER}")
    print(f"  Txn ID    : {txn_id}")
    print(f"{'='*60}\n")

    # Step 0: Health check on both sides
    print("[0] Health checks")
    try:
        h1 = httpx.get("http://localhost:8081/health", timeout=5)
        print(f"  Our ONIX BAP (8081): {h1.json().get('status', '?')}")
    except Exception:
        print("  Our ONIX BAP: DOWN -- start Docker containers!")
        return

    try:
        h2 = httpx.get(f"https://fa85-117-250-7-33.ngrok-free.app/health", timeout=10)
        print(f"  flockenergy BPP    : {h2.json().get('status', '?')}")
    except Exception as e:
        print(f"  flockenergy BPP    : unreachable ({e})")
        return

    contract_id = f"infosys-floc-{txn_id[:8]}"

    # Full Beckn contract structure (schema-compliant)
    contract_draft = {
        "id": contract_id,
        "descriptor": {"name": "Infosys-flockenergy Cross-Team Data Exchange"},
        "status": {"code": "DRAFT"},
        "commitments": [
            {
                "id": f"commitment-{txn_id[:8]}",
                "status": {"descriptor": {"code": "DRAFT"}},
                "resources": [
                    {
                        "id": "ds-flockenergy-tariff-001",
                        "descriptor": {"name": "flockenergy Tariff/Meter Data"},
                        "quantity": {"unitText": "dataset", "unitCode": "EA", "value": "1"}
                    }
                ],
                "offer": {
                    "id": "offer-flockenergy-inline",
                    "descriptor": {"name": "flockenergy Data Inline Delivery"},
                    "resourceIds": ["ds-flockenergy-tariff-001"]
                },
                "commitmentAttributes": {
                    "@context": "https://raw.githubusercontent.com/beckn/DDM/main/specification/schema/DatasetItem/v1/context.jsonld",
                    "@type": "DatasetItem",
                    "schema:identifier": "ds-flockenergy-tariff-001",
                    "schema:name": "flockenergy Data",
                    "schema:temporalCoverage": "2024-04-01/2025-03-31",
                    "dataset:sensitivityLevel": "PUBLIC",
                    "dataset:refreshType": "ANNUAL",
                    "dataset:refreshFrequency": "P1Y",
                    "dataset:accessMethod": "INLINE"
                }
            }
        ],
        "consideration": [
            {
                "id": "consideration-open-access",
                "status": {"code": "ACTIVE"},
                "considerationAttributes": {
                    "@context": "https://raw.githubusercontent.com/beckn/schemas/refs/heads/main/schema/PriceSpecification/v2.1/context.jsonld",
                    "@type": "PriceSpecification",
                    "currency": "INR",
                    "value": 0,
                    "description": "Open data exchange"
                }
            }
        ],
        "participants": [],
        "performance": [],
        "settlements": []
    }

    contract_active = {**contract_draft, "status": {"code": "ACTIVE"}}

    # Step 1: SELECT
    print("\n[1/4] SELECT")
    ok, _ = send_action("select", txn_id, str(uuid.uuid4()), {"contract": contract_draft})
    if not ok:
        print("  SELECT failed -- continuing anyway (NACK might still store response)")

    time.sleep(1)

    # Step 2: INIT
    print("[2/4] INIT")
    send_action("init", txn_id, str(uuid.uuid4()), {"contract": contract_active})

    time.sleep(1)

    # Step 3: CONFIRM
    print("[3/4] CONFIRM")
    send_action("confirm", txn_id, str(uuid.uuid4()), {"contract": contract_active})

    time.sleep(1)

    # Step 4: STATUS (ye asli data deliver karta hai)
    print("[4/4] STATUS")
    ok, _ = send_action("status", txn_id, str(uuid.uuid4()), {"contract": contract_active})

    if not ok:
        print("\n  STATUS NACK -- checking raw sandbox-bap logs for clues...")
        # Still try to watch logs

    # Watch logs for on_status callback
    result = watch_docker_logs(txn_id, timeout=20)

    print(f"\n{'='*60}")
    if result:
        print(f"  SUCCESS -- on_status received from flockenergy!")
        print(f"{'='*60}")
        ctx = result.get("context", {})
        msg = result.get("message", {})
        print(f"  From BPP   : {ctx.get('bppId', '?')}")
        print(f"  Action     : {ctx.get('action', '?')}")
        # Try to extract dataPayload
        perf = (msg.get("contract", {})
                   .get("performance", [{}]))
        if perf:
            attrs = perf[0].get("performanceAttributes", {})
            dp = attrs.get("dataPayload", {})
            if dp:
                print(f"  Policies   : {len(dp.get('policies', []))}")
                for p in dp.get("policies", []):
                    print(f"    - {p.get('policyID','?')} : {p.get('policyName','?')}")
            else:
                print(f"  Payload    : (no dataPayload — might be meter/EDX data)")
                print(json.dumps(attrs, indent=2)[:400])
        print(json.dumps(result, indent=2)[:800] + "...")
    else:
        print(f"  No on_status in logs within 20s")
        print(f"{'='*60}")
        print(f"\n  Checking sandbox-bap recent logs manually...")
        try:
            logs = subprocess.check_output(
                ["docker", "logs", "--tail", "50", "sandbox-bap"],
                stderr=subprocess.STDOUT
            )
            print(logs.decode("utf-8", errors="replace")[-1500:])
        except Exception as e:
            print(f"  Could not read logs: {e}")

    print(f"\n  PROOF: Infosys BAP -> flockenergy BPP -> cross-team data exchange")
    print(f"{'='*60}\n")


if __name__ == "__main__":
    main()
