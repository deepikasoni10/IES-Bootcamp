#!/usr/bin/env python3
"""
IES Bootcamp — BAP Client

Sends beckn v2.0 requests through the full lifecycle:
  discover → select → init → confirm → status (chunked delivery)

Two modes of operation:

  local-bap (recommended):
    - Runs a local ONIX BAP (via docker compose) on your machine
    - BAP signs requests and forwards to the remote GCP BPP
    - Responses fetched via poll from mock-bpp's store

  poll mode (no Docker needed):
    - Sends requests through the shared BAP on GCP
    - Polls mock-bpp's response store for results
    - Simpler setup, but uses a shared BAP

Usage:
  # Local BAP mode — run local ONIX BAP first: docker compose up -d
  python bap_client.py --mode local-bap --usecase all

  # Poll mode — no local setup needed
  python bap_client.py --mode poll --usecase all
"""

import argparse
import asyncio
import json
import os
import subprocess
import sys
import threading
import time
import uuid
from datetime import datetime, timezone

import httpx
import uvicorn
from fastapi import FastAPI, Request

# ─────────────────────────────────────────────────────────────
# Callback webhook server — receives on_* from ONIX BAP
# ─────────────────────────────────────────────────────────────
webhook = FastAPI()
responses: dict[str, asyncio.Event] = {}
response_data: dict[str, dict] = {}
main_loop: asyncio.AbstractEventLoop = None


@webhook.post("/callback/{action}")
@webhook.post("/callback")
async def receive_callback(request: Request, action: str = None):
    body = await request.json()
    act = body.get("context", {}).get("action", action or "unknown")
    txn = body.get("context", {}).get("transactionId", "?")

    # Store the response
    key = f"{txn}:{act}"
    response_data[key] = body

    # Signal the waiting coroutine
    if key in responses:
        main_loop.call_soon_threadsafe(responses[key].set)

    return {"message": {"ack": {"status": "ACK"}}}


def start_webhook(port: int):
    uvicorn.run(webhook, host="0.0.0.0", port=port, log_level="warning")


# ─────────────────────────────────────────────────────────────
# BAP Client — sends beckn requests
# ─────────────────────────────────────────────────────────────
SCHEMA_CONTEXT = "https://raw.githubusercontent.com/beckn/DDM/main/specification/schema/DatasetItem/v1/context.jsonld"
ORG_CONTEXT = "https://raw.githubusercontent.com/beckn/schemas/refs/heads/main/schema/Organization/v2.0/context.jsonld"
PRICE_CONTEXT = "https://raw.githubusercontent.com/beckn/schemas/refs/heads/main/schema/PriceSpecification/v2.1/context.jsonld"
PAYMENT_CONTEXT = "https://raw.githubusercontent.com/beckn/schemas/refs/heads/main/schema/Payment/v2.0/context.jsonld"

# Use case definitions
USE_CASES = {
    "telemetry": {
        "name": "AMI Meter Data Exchange",
        "desc": "AMI meter data exchange under existing AMISP contract",
        "resource_id": "ds-ami-meter-data-blr-zone-a-q1-2026",
        "resource_name": "IntelliGrid AMI Meter Data - Bengaluru Zone A - Q1 2026",
        "offer_id": "offer-ami-meter-data-inline",
        "commitment_id": "commitment-ami-meter-001",
        "contract_id": "660e9500-f30c-52e5-b827-557766551300",
        "consideration_id": "consideration-ami-existing-contract",
        "consideration_desc": "Covered under existing AMI services contract",
        "temporal": "2026-01-01/2026-03-31",
        "unit": "report",
        "provider": ("intelligrid-amisp-001", "IntelliGrid AMI Services"),
        "consumer": ("bescom-discom-001", "BESCOM - Distribution Company"),
    },
    "arr": {
        "name": "ARR Filing Data Exchange",
        "desc": "ARR filing submission under regulatory mandate",
        "resource_id": "ds-bescom-arr-filing-fy2025-26",
        "resource_name": "BESCOM ARR Filing - FY 2025-26",
        "offer_id": "offer-arr-filing-inline",
        "commitment_id": "commitment-arr-filing-001",
        "contract_id": "660e9500-f30c-52e5-b827-557766551300",
        "consideration_id": "consideration-arr-regulatory-mandate",
        "consideration_desc": "Mandatory regulatory filing - no commercial consideration",
        "temporal": "2025-04-01/2026-03-31",
        "unit": "filing",
        "provider": ("bescom-discom-001", "BESCOM - Bangalore Electricity Supply Company"),
        "consumer": ("aperc-regulator-001", "APERC - AP Electricity Regulatory Commission"),
    },
    "tariff": {
        "name": "Tariff Policy Data Exchange",
        "desc": "Machine-readable tariff rate structures and energy programs",
        "resource_id": "ds-serc-tariff-policy-fy2024-25",
        "resource_name": "SERC Tariff Policy - Residential & Commercial - FY 2024-25",
        "offer_id": "offer-tariff-policy-inline",
        "commitment_id": "commitment-tariff-policy-001",
        "contract_id": "770f0611-a41d-53f6-c938-668877662411",
        "consideration_id": "consideration-tariff-open-access",
        "consideration_desc": "Tariff policies are publicly accessible under regulatory mandate",
        "temporal": "2024-04-01/2025-03-31",
        "unit": "policy",
        "provider": ("serc-policy-publisher-001", "State Electricity Regulatory Commission (SERC)"),
        "consumer": ("discom-tariff-consumer-001", "MeraShehar Distribution Company"),
    },
}


def now():
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def make_context(action: str, txn_id: str):
    ctx = {
        "networkId": "nfh.global/testnet-deg",
        "version": "2.0.0",
        "action": action,
        "bapId": "bap.example.com",
        "bapUri": "http://onix-bap:8081/bap/receiver",
        "bppId": "bpp.example.com",
        "bppUri": "http://onix-bpp:8082/bpp/receiver",
        "transactionId": txn_id,
        "messageId": str(uuid.uuid4()),
        "timestamp": now(),
    }
    if action != "status":
        ctx["schemaContext"] = [SCHEMA_CONTEXT]
    return ctx


def make_participant(pid, pname):
    return {
        "id": pid,
        "descriptor": {"name": pname},
        "participantAttributes": {
            "@context": ORG_CONTEXT, "@type": "Organization",
            "id": pid, "name": pname,
        },
    }


def build_contract(uc: dict, status_code: str, commitment_code: str, include_settlement=False):
    contract = {
        "id": uc["contract_id"],
        "descriptor": {"name": uc["name"], "shortDesc": uc["desc"]},
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
                "@context": SCHEMA_CONTEXT, "@type": "DatasetItem",
                "schema:identifier": uc["resource_id"],
                "schema:name": uc["resource_name"],
                "schema:temporalCoverage": uc["temporal"],
                "dataset:accessMethod": "INLINE",
            },
        }],
        "consideration": [{
            "id": uc["consideration_id"],
            "status": {"code": "ACTIVE"},
            "considerationAttributes": {
                "@context": PRICE_CONTEXT, "@type": "PriceSpecification",
                "currency": "INR", "value": 0,
                "description": uc["consideration_desc"],
            },
        }],
        "participants": [
            make_participant(*uc["provider"]),
            make_participant(*uc["consumer"]),
        ],
        "performance": [],
        "settlements": [],
    }
    if include_settlement:
        contract["settlements"] = [{
            "id": "settlement-payment-completed",
            "considerationId": uc["consideration_id"],
            "status": "COMPLETE",
            "settlementAttributes": {
                "@context": PAYMENT_CONTEXT, "@type": "Payment",
                "beckn:paymentStatus": "COMPLETED",
                "beckn:amount": {"currency": "INR", "value": 0},
            },
        }]
    return contract


# Track how many on_* responses we've already seen per txn:action for polling
_poll_seen: dict[str, int] = {}


async def send_and_wait(client: httpx.AsyncClient, bap_url: str, action: str,
                        txn_id: str, body: dict, timeout: float = 15.0,
                        mode: str = "webhook", mock_bpp_url: str = None):
    """Send a beckn request and wait for the on_* callback."""
    on_action = f"on_{action}"

    # Send the request
    print(f"\n{'='*60}")
    print(f">>> Sending {action.upper()}")
    print(f"    POST {bap_url}/{action}")
    resp = await client.post(f"{bap_url}/{action}", json=body)
    ack = resp.json()
    ack_status = ack.get("message", {}).get("ack", {}).get("status", "?")
    print(f"    ACK: {ack_status}")

    if ack_status != "ACK":
        print(f"    ERROR: {json.dumps(ack, indent=2)}")
        return None

    if mode == "webhook":
        # Wait for callback on local webhook server
        key = f"{txn_id}:{on_action}"
        evt = asyncio.Event()
        responses[key] = evt
        print(f"    Waiting for {on_action} callback...", end="", flush=True)
        try:
            await asyncio.wait_for(evt.wait(), timeout=timeout)
            data = response_data.get(key, {})
            print(f" RECEIVED!")
            return data
        except asyncio.TimeoutError:
            print(f" TIMEOUT after {timeout}s")
            return None

    elif mode == "poll":
        # Poll mock-bpp's /api/responses endpoint
        # Track which responses we've already seen so repeated status calls work
        seen_key = f"{txn_id}:{on_action}"
        already_seen = _poll_seen.get(seen_key, 0)

        print(f"    Polling mock-bpp for {on_action}...", end="", flush=True)
        poll_url = f"{mock_bpp_url}/api/responses/{txn_id}?action={on_action}"
        txn_url = f"{mock_bpp_url}/api/transactions/{txn_id}"
        deadline = time.time() + timeout
        while time.time() < deadline:
            await asyncio.sleep(1)
            try:
                poll_resp = await client.get(poll_url)
                poll_data = poll_resp.json()
                total = poll_data.get("count", 0)
                if total > already_seen:
                    # New response available — grab the latest unseen one
                    payload = poll_data["responses"][already_seen]["payload"]
                    _poll_seen[seen_key] = already_seen + 1
                    print(f" RECEIVED!")
                    return payload
                # Check transaction state for lifecycle errors
                # (skip for discover — it doesn't create transactions)
                if action != "discover":
                    txn_resp = await client.get(txn_url)
                    txn_data = txn_resp.json()
                    if "error" in txn_data:
                        # "not found" just means BPP hasn't processed yet — keep polling
                        if "not found" not in txn_data.get("error", "").lower():
                            print(f" LIFECYCLE ERROR")
                            print(f"    {txn_data['error']}")
                            print(f"    Hint: {txn_data.get('hint', '')}")
                            return None
                print(".", end="", flush=True)
            except Exception:
                print("x", end="", flush=True)
        print(f" TIMEOUT after {timeout}s")
        # On timeout, check transaction state for a helpful message
        try:
            txn_resp = await client.get(txn_url)
            txn_data = txn_resp.json()
            state = txn_data.get("state", "unknown")
            print(f"    Transaction state: {state}")
            if txn_data.get("history"):
                last = txn_data["history"][-1]
                print(f"    Last action: {last['action']} → {last['state']} at {last['timestamp']}")
        except Exception:
            pass
        return None


def print_response(action: str, data: dict):
    """Pretty-print the key parts of a beckn on_* response."""
    if not data:
        print("    (no data)")
        return

    ctx = data.get("context", {})
    msg = data.get("message", {})
    contract = msg.get("contract", {})

    print(f"\n<<< Received {action}")
    print(f"    transactionId: {ctx.get('transactionId')}")
    print(f"    contract status: {contract.get('status', {}).get('code')}")

    # Show commitment status
    for c in contract.get("commitments", []):
        code = c.get("status", {}).get("descriptor", {}).get("code", "?")
        print(f"    commitment [{c.get('id')}]: {code}")

    # Show performance (data delivery)
    for p in contract.get("performance", []):
        status = p.get("status", {})
        attrs = p.get("performanceAttributes", {})
        chunk_info = ""
        if attrs.get("totalChunks", 1) > 1:
            chunk_info = f" [chunk {attrs.get('chunkIndex', 0) + 1}/{attrs.get('totalChunks')}]"
        print(f"    performance: {status.get('code')} — {status.get('name', '')}{chunk_info}")

        attrs = p.get("performanceAttributes", {})
        if "dataPayload" in attrs:
            payload = attrs["dataPayload"]
            payload_size = len(json.dumps(payload))

            # dataPayload can be a dict or a list (e.g. ARR filings)
            if isinstance(payload, list):
                payload_type = "list"
                if payload and isinstance(payload[0], dict):
                    payload_type = payload[0].get("@type", payload[0].get("objectType", f"list[{len(payload)}]"))
            elif isinstance(payload, dict):
                payload_type = payload.get("@type", payload.get("objectType", "unknown"))
            else:
                payload_type = type(payload).__name__

            print(f"    dataPayload type: {payload_type}")
            print(f"    dataPayload size: {payload_size:,} bytes")

            # Print a summary based on type
            if payload_type in ("IES_Report", "REPORT"):
                resources = payload.get("resources", [])
                print(f"    resources: {len(resources)} meter(s)")
                for r in resources[:3]:
                    intervals = r.get("intervals", [])
                    print(f"      {r.get('resourceName')}: {len(intervals)} intervals")

            elif isinstance(payload, list):
                print(f"      items: {len(payload)}")
                for item in payload[:3]:
                    if isinstance(item, dict):
                        item_id = item.get("filingId", item.get("id", item.get("name", "?")))
                        fy = item.get("fiscalYears", [])
                        if fy:
                            print(f"      filing {item_id}: {len(fy)} fiscal years")
                        else:
                            print(f"      item: {item_id}")

            elif payload_type in ("ARR_FILING",):
                fy = payload.get("fiscalYears", [])
                print(f"      fiscal years: {len(fy)}")

            elif payload_type in ("IES_TariffIntelligence", "TARIFF_INTELLIGENCE"):
                policies = payload.get("policies", [])
                programs = payload.get("programs", [])
                print(f"      programs: {len(programs)}")
                print(f"      policies: {len(policies)}")
                for pol in policies:
                    slabs = pol.get("energySlabs", [])
                    surcharges = pol.get("surchargeTariffs", [])
                    print(f"        {pol.get('policyName')}: {len(slabs)} slabs, {len(surcharges)} surcharges")

            print(f"\n    --- Full dataPayload ---")
            print(json.dumps(payload, indent=2)[:3000])
            if len(json.dumps(payload)) > 3000:
                print(f"    ... (truncated, full payload is {payload_size:,} bytes)")


def print_discover(data: dict):
    """Pretty-print discover response (catalog listing)."""
    if not data:
        print("    (no discover response — catalog may not be available)")
        return

    ctx = data.get("context", {})
    catalog = data.get("message", {}).get("catalog", {})
    items = catalog.get("items", [])

    print(f"\n<<< Received on_discover")
    print(f"    source: {catalog.get('source', 'unknown')}")
    print(f"    datasets found: {len(items)}")

    for item in items:
        desc = item.get("descriptor", {})
        provider = item.get("provider", {})
        chunks = item.get("totalChunks", 1)
        size_kb = item.get("totalSizeKB", "?")
        print(f"    • {desc.get('name', item.get('id', '?'))}")
        print(f"      id: {item.get('id')}")
        print(f"      provider: {provider.get('name', '?')}")
        print(f"      coverage: {item.get('temporalCoverage', '?')}")
        print(f"      chunks: {chunks}, size: {size_kb}KB")

    if catalog.get("note"):
        print(f"    note: {catalog['note']}")


async def run_usecase(bap_url: str, usecase_name: str, txn_id: str,
                     mode: str = "webhook", mock_bpp_url: str = None):
    """Run a complete beckn lifecycle for one use case."""
    uc = USE_CASES[usecase_name]
    send_kw = {"mode": mode, "mock_bpp_url": mock_bpp_url}

    print(f"\n{'#'*60}")
    print(f"# Use Case: {uc['name']}")
    print(f"# Provider: {uc['provider'][1]}")
    print(f"# Consumer: {uc['consumer'][1]}")
    print(f"# Transaction: {txn_id}")
    print(f"# Mode: {mode}")
    print(f"{'#'*60}")

    async with httpx.AsyncClient(timeout=30) as client:
        # 0. DISCOVER — browse the catalog (optional but shows the full beckn flow)
        discover_body = {
            "context": make_context("discover", txn_id),
            "message": {
                "intent": {},
            },
        }
        on_discover = await send_and_wait(client, bap_url, "discover", txn_id, discover_body, **send_kw)
        print_discover(on_discover)

        # 1. SELECT — pick a specific dataset
        select_body = {
            "context": make_context("select", txn_id),
            "message": {"contract": build_contract(uc, "DRAFT", "DRAFT")},
        }
        on_select = await send_and_wait(client, bap_url, "select", txn_id, select_body, **send_kw)
        print_response("on_select", on_select)
        if not on_select:
            print("\n    Stopping — select failed. Cannot proceed.")
            return

        # 2. INIT
        init_body = {
            "context": make_context("init", txn_id),
            "message": {"contract": build_contract(uc, "ACTIVE", "ACTIVE")},
        }
        on_init = await send_and_wait(client, bap_url, "init", txn_id, init_body, **send_kw)
        print_response("on_init", on_init)
        if not on_init:
            print("\n    Stopping — init failed. Cannot proceed without select → init.")
            return

        # 3. CONFIRM
        confirm_body = {
            "context": make_context("confirm", txn_id),
            "message": {"contract": build_contract(uc, "ACTIVE", "ACTIVE", include_settlement=True)},
        }
        on_confirm = await send_and_wait(client, bap_url, "confirm", txn_id, confirm_body, **send_kw)
        print_response("on_confirm", on_confirm)
        if not on_confirm:
            print("\n    Stopping — confirm failed. Cannot proceed without init → confirm.")
            return

        # 4. STATUS — data delivery (may require multiple calls for chunked datasets)
        status_contract = {
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
        }

        all_chunks = []
        chunk_num = 0
        while True:
            chunk_num += 1
            status_body = {
                "context": make_context("status", txn_id),
                "message": {"contract": status_contract},
            }
            on_status = await send_and_wait(client, bap_url, "status", txn_id, status_body, timeout=20, **send_kw)
            if not on_status:
                print(f"\n    Status call #{chunk_num} failed — stopping.")
                break

            # Extract chunk metadata from performance
            perf = on_status.get("message", {}).get("contract", {}).get("performance", [])
            chunk_info = {}
            if perf:
                attrs = perf[0].get("performanceAttributes", {})
                chunk_info = {
                    "chunkIndex": attrs.get("chunkIndex", 0),
                    "totalChunks": attrs.get("totalChunks", 1),
                    "isLastChunk": attrs.get("isLastChunk", True),
                }
                delivery_code = perf[0].get("status", {}).get("code", "DELIVERY_COMPLETE")
            else:
                delivery_code = "DELIVERY_COMPLETE"

            total = chunk_info.get("totalChunks", 1)
            idx = chunk_info.get("chunkIndex", 0)

            if total > 1:
                print(f"\n    --- Chunk {idx + 1}/{total} ---")
            print_response(f"on_status (chunk {idx + 1}/{total})" if total > 1 else "on_status", on_status)

            all_chunks.append(on_status)

            if delivery_code == "DELIVERY_COMPLETE" or chunk_info.get("isLastChunk", True):
                if total > 1:
                    print(f"\n    All {total} chunks received!")
                break

            # Brief pause between chunk requests
            await asyncio.sleep(0.5)

    print(f"\n{'='*60}")
    if len(all_chunks) > 1:
        print(f"Done! Full lifecycle complete for: {uc['name']} ({len(all_chunks)} chunks delivered)")
    else:
        print(f"Done! Full lifecycle complete for: {uc['name']}")
    print(f"{'='*60}")


async def main(bap_url: str, usecase: str, mode: str, mock_bpp_url: str):
    global main_loop
    main_loop = asyncio.get_event_loop()

    is_local_bap = "localhost" in bap_url or "127.0.0.1" in bap_url
    if is_local_bap:
        print(f"Local BAP mode:")
        print(f"  Outbound: your requests → local ONIX BAP ({bap_url})")
        print(f"             → signs & forwards to GCP BPP")
        print(f"  Inbound:  poll mock-bpp at {mock_bpp_url}")
        print()
    else:
        print(f"Poll mode:")
        print(f"  Outbound: your requests → shared GCP BAP ({bap_url})")
        print(f"  Inbound:  poll mock-bpp at {mock_bpp_url}")
        print()

    run_kw = {"mode": mode, "mock_bpp_url": mock_bpp_url}

    if usecase == "all":
        for uc_name in USE_CASES:
            txn_id = str(uuid.uuid4())
            await run_usecase(bap_url, uc_name, txn_id, **run_kw)
            print()
    else:
        txn_id = str(uuid.uuid4())
        await run_usecase(bap_url, usecase, txn_id, **run_kw)


if __name__ == "__main__":
    # Load BPP server IP from config.json (one place to change)
    _config_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "config.json")
    with open(_config_path) as _f:
        _config = json.load(_f)
    BPP_IP = _config["bpp_server_ip"]

    GCP_BAP = f"http://{BPP_IP}:8081/bap/caller"
    GCP_MOCK_BPP = f"http://{BPP_IP}:3002"
    LOCAL_BAP = "http://localhost:8081/bap/caller"

    # Patch routing config with the BPP IP so ONIX routes to the right server
    _routing_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "config", "routing-BAPCaller.yaml")
    _routing_changed = False
    if os.path.exists(_routing_path):
        with open(_routing_path) as _f:
            _routing = _f.read()
        import re
        _new_routing = re.sub(r'http://[^:]+:8082/bpp/receiver', f'http://{BPP_IP}:8082/bpp/receiver', _routing)
        if _new_routing != _routing:
            with open(_routing_path, 'w') as _f:
                _f.write(_new_routing)
            print(f"Updated routing config → {BPP_IP}:8082")
            _routing_changed = True

    parser = argparse.ArgumentParser(
        description="IES Bootcamp BAP Client",
        epilog="""
Modes:
  local-bap  (recommended) Run your own local ONIX BAP (requires: docker compose up -d).
             Outbound requests go through YOUR BAP (real beckn signing/validation).
             Responses fetched via poll from mock-bpp's store.

  poll       Use the shared BAP on GCP (no Docker needed).
             Polls mock-bpp's response store for results.

Examples:
  # Local BAP mode (recommended) — start local BAP first
  docker compose up -d
  python bap_client.py --mode local-bap --usecase all

  # Poll mode — no local setup needed
  python bap_client.py --mode poll --usecase all

  # Single use case
  python bap_client.py --mode local-bap --usecase tariff
        """,
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument("--bap-url",
                        help=f"BAP caller URL (default: localhost:8081 for local-bap, GCP for poll)")
    parser.add_argument("--mock-bpp-url", default=GCP_MOCK_BPP,
                        help=f"Mock BPP URL for polling responses (default: {GCP_MOCK_BPP})")
    parser.add_argument("--mode", choices=["local-bap", "poll"], default="local-bap",
                        help="local-bap = your own ONIX BAP + poll, poll = shared GCP BAP + poll (default: local-bap)")
    parser.add_argument("--usecase", choices=["telemetry", "arr", "tariff", "all"],
                        default="telemetry", help="Which use case to run (default: telemetry)")
    args = parser.parse_args()

    # Store the user's chosen mode for display, then normalize to "poll" for the engine
    user_mode = args.mode
    if args.bap_url is None:
        args.bap_url = LOCAL_BAP if user_mode == "local-bap" else GCP_BAP
    args.mode = "poll"  # both modes use poll for receiving responses

    # If routing IP changed and we're using local BAP, restart ONIX so it picks up the new config
    if _routing_changed and user_mode == "local-bap":
        _compose_dir = os.path.dirname(os.path.abspath(__file__))
        print("BPP server IP changed — restarting local ONIX BAP to pick up new routing...")
        _restart = subprocess.run(
            ["docker", "compose", "restart", "onix-bap"],
            cwd=_compose_dir, capture_output=True, text=True,
        )
        if _restart.returncode == 0:
            print("ONIX BAP restarted. Waiting for it to be ready...")
            # Give ONIX a few seconds to reload config
            for _i in range(10):
                time.sleep(1)
                try:
                    import urllib.request
                    with urllib.request.urlopen("http://localhost:8081/health", timeout=2) as _resp:
                        if _resp.status == 200:
                            print("ONIX BAP is ready.\n")
                            break
                except Exception:
                    pass
            else:
                print("Warning: ONIX BAP may not be ready yet. Proceeding anyway...\n")
        else:
            print(f"Warning: Could not restart ONIX BAP: {_restart.stderr.strip()}")
            print("Run manually: docker compose restart onix-bap\n")

    try:
        asyncio.run(main(args.bap_url, args.usecase, args.mode, args.mock_bpp_url))
    except KeyboardInterrupt:
        print("\nStopped.")
