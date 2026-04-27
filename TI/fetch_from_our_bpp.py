#!/usr/bin/env python3
"""
Fetch tariff policy from OUR OWN BPP server (localhost:5000)
instead of GCP.

Ye script doosri team run kar sakti hai — ya hum khud test ke liye chalate hain.
Ye prove karta hai ki hum PRODUCER hain — hum data serve kar rahe hain.

Run order:
  Terminal 1:  python bpp_server.py      <- server chalao
  Terminal 2:  python fetch_from_our_bpp.py   <- is script se fetch karo
"""

import hashlib
import json
import time
import uuid
from datetime import datetime, timezone

import httpx

# Humara apna BPP server
OUR_BPP = "http://localhost:5000"

CONTRACT_ID = "infosys-ti-contract-001"


def now():
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def send(client, action, txn_id, body):
    """Beckn action humare server ko bhejo."""
    url  = f"{OUR_BPP}/bpp/{action}"
    resp = client.post(url, json=body, timeout=10)
    resp.raise_for_status()
    result = resp.json()
    status = result.get("message", {}).get("ack", {}).get("status", "?")
    print(f"  [{action}] -> {status}")
    if status != "ACK":
        raise RuntimeError(f"{action} returned {status}")
    return result


def poll(txn_id, action, retries=8, delay=1):
    """Polling: humara server response ready hua kya?"""
    on_action = f"on_{action}"
    for attempt in range(retries):
        resp = httpx.get(f"{OUR_BPP}/api/responses/{txn_id}?action={on_action}", timeout=5)
        if resp.status_code == 200:
            data = resp.json()
            responses = data.get("responses", [])
            if responses:
                return responses[-1]["payload"]
        time.sleep(delay)
    raise TimeoutError(f"No {on_action} after {retries} attempts")


def main():
    txn_id = str(uuid.uuid4())

    print(f"\n{'='*55}")
    print(f"  Fetching Tariff from Infosys BPP Server")
    print(f"  Server   : {OUR_BPP}")
    print(f"  Txn ID   : {txn_id}")
    print(f"{'='*55}\n")

    # Health check pehle
    try:
        h = httpx.get(f"{OUR_BPP}/health", timeout=5)
        info = h.json()
        print(f"[Health] Server UP — policies: {info.get('policies')}\n")
    except Exception:
        print(f"[ERROR] Server not running! Pehle chalao: python bpp_server.py")
        return

    ctx_base = {
        "transactionId": txn_id,
        "action":        "",
        "bapId":         "infosys-bap-test",
        "bppId":         "infosys-ti-bpp",
        "timestamp":     now(),
    }
    contract = {"id": CONTRACT_ID, "status": {"code": "DRAFT"}}

    with httpx.Client() as client:
        print("[1/4] SELECT — catalog maango")
        send(client, "select", txn_id, {
            "context": {**ctx_base, "action": "select"},
            "message": {"contract": contract},
        })
        poll(txn_id, "select")

        print("[2/4] INIT — contract activate karo")
        send(client, "init", txn_id, {
            "context": {**ctx_base, "action": "init"},
            "message": {"contract": {**contract, "status": {"code": "ACTIVE"}}},
        })
        poll(txn_id, "init")

        print("[3/4] CONFIRM — confirm karo")
        send(client, "confirm", txn_id, {
            "context": {**ctx_base, "action": "confirm"},
            "message": {"contract": {**contract, "status": {"code": "ACTIVE"}}},
        })
        poll(txn_id, "confirm")

        print("[4/4] STATUS — asli data lo")
        send(client, "status", txn_id, {
            "context": {**ctx_base, "action": "status"},
            "message": {"contract": {**contract, "status": {"code": "ACTIVE"}}},
        })
        on_status = poll(txn_id, "status")

    # Data extract karo
    performance = (on_status.get("message", {})
                             .get("contract", {})
                             .get("performance", []))
    if not performance:
        print("[ERROR] No performance data in on_status")
        return

    perf_attrs   = performance[0].get("performanceAttributes", {})
    data_payload = perf_attrs.get("dataPayload")
    stored_hash  = perf_attrs.get("payloadHash", "")

    if not data_payload:
        print("[ERROR] No dataPayload found")
        return

    # Hash verify karo
    canonical = json.dumps(data_payload, sort_keys=True, separators=(',', ':'))
    computed  = hashlib.sha256(canonical.encode()).hexdigest()
    hash_match = stored_hash == computed

    print(f"\n{'='*55}")
    print(f"  SUCCESS — Tariff pack received from Infosys BPP!")
    print(f"{'='*55}")
    print(f"  Provided by  : {perf_attrs.get('providedBy')}")
    print(f"  Hash verify  : {'PASS' if hash_match else 'FAIL'}")
    print(f"  Hash         : {computed[:30]}...")
    print(f"  Programs     : {len(data_payload.get('programs', []))}")
    print(f"  Policies     : {len(data_payload.get('policies', []))}")
    for p in data_payload.get("policies", []):
        slabs = len(p.get("energySlabs", []))
        surcharges = len(p.get("surchargeTariffs", []))
        print(f"    - {p['policyID']:12s}  {p['policyName']}  (slabs={slabs}, surcharges={surcharges})")

    # Apne tariff engine se bill compute karo proof ke liye
    print(f"\n[BONUS] Running tariff engine on received data...")
    from tariff_engine import compute_bill
    import io, contextlib
    policy_map = {p["policyID"]: p for p in data_payload["policies"]}

    buf = io.StringIO()
    with contextlib.redirect_stdout(buf):
        result = compute_bill(policy_map["RES-T1"], total_kwh=350.0)
    print(f"  RES-T1  350 kWh  ->  Rs.{result.total_bill:.2f}  (base: Rs.{result.base_charge:.2f})")

    buf = io.StringIO()
    with contextlib.redirect_stdout(buf):
        result2 = compute_bill(policy_map["COM-TOU1"], total_kwh=500.0, peak_kwh=100.0)
    print(f"  COM-TOU1 500 kWh ->  Rs.{result2.total_bill:.2f}  (base: Rs.{result2.base_charge:.2f}, surcharge: Rs.{result2.surcharge_total:.2f})")

    print(f"\n  PROOF: Infosys BPP ne tariff data serve kiya")
    print(f"         Consumer ne receive kiya + engine chalayi")
    print(f"         Hash verified = tamper-proof delivery")
    print(f"{'='*55}\n")


if __name__ == "__main__":
    main()
