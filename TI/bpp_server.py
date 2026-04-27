#!/usr/bin/env python3
"""
BPP Server -- Tariff Policy Producer
=====================================
Ye server humara PRODUCER side hai.
Koi bhi team humse Beckn flow chalake tariff pack le sakti hai.

Endpoints:
  POST /bpp/select    <- doosri team select bhejti hai
  POST /bpp/init      <- doosri team init bhejti hai
  POST /bpp/confirm   <- doosri team confirm bhejti hai
  POST /bpp/status    <- doosri team status maangti hai (yahan data milta hai)
  GET  /api/responses/<txn_id>?action=on_status  <- polling endpoint
  GET  /health        <- server alive check

Run: python bpp_server.py
Port: 5000
"""

import hashlib
import json
import uuid
from datetime import datetime, timezone

from flask import Flask, jsonify, request

app = Flask(__name__)

# In-memory store: txn_id -> list of responses
# (same pattern as GCP mock BPP at port 3002)
response_store = {}


# ─────────────────────────────────────────────────────────────
# Load our tariff pack
# ─────────────────────────────────────────────────────────────

def load_policy():
    """Load policy_pack.json — ye humara tariff data hai jo hum serve karenge."""
    try:
        with open("policy_pack.json") as f:
            pack = json.load(f)
        policies = pack["dataPayload"]["policies"]
        print(f"[BPP] Loaded {len(policies)} policies from policy_pack.json")
        print(f"[BPP] Hash: {pack['payloadHash'][:30]}...")
        return pack["dataPayload"]
    except FileNotFoundError:
        print("[BPP] policy_pack.json not found! Run: python fetch_policy.py")
        raise


OUR_POLICY_DATA = load_policy()


# ─────────────────────────────────────────────────────────────
# Helper: store a response for polling
# ─────────────────────────────────────────────────────────────

def store_response(txn_id, action, payload):
    """
    Kisi bhi on_* response ko store karo taaki BAP poll kar sake.
    GCP mock BPP ka same pattern.
    """
    key = txn_id
    if key not in response_store:
        response_store[key] = {}
    on_action = f"on_{action}"
    if on_action not in response_store[key]:
        response_store[key][on_action] = []
    response_store[key][on_action].append({
        "payload": payload,
        "storedAt": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
    })
    print(f"[BPP] Stored {on_action} for txn {txn_id[:8]}...")


def now():
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


# ─────────────────────────────────────────────────────────────
# Step 1: SELECT — doosri team ne "mujhe tariff chahiye" kaha
# ─────────────────────────────────────────────────────────────

@app.route("/bpp/select", methods=["POST"])
@app.route("/bpp/receiver/select", methods=["POST"])
def handle_select():
    """
    SELECT aaya:
    - ACK bhejo (haan, request mili)
    - on_select store karo (catalog dikhao — kya kya available hai)
    """
    body    = request.json or {}
    ctx     = body.get("context", {})
    txn_id  = ctx.get("transactionId", str(uuid.uuid4()))

    print(f"\n[BPP] <- SELECT received  txn={txn_id[:8]}...")

    # on_select response — catalog / available policies batao
    on_select = {
        "context": {**ctx, "action": "on_select"},
        "message": {
            "contract": {
                "id": body.get("message", {}).get("contract", {}).get("id", ""),
                "status": {"code": "DRAFT"},
                "catalog": {
                    "descriptor": {"name": "IES Tariff Policy Catalog"},
                    "policies": [
                        {"id": p["policyID"], "name": p["policyName"]}
                        for p in OUR_POLICY_DATA.get("policies", [])
                    ],
                },
            }
        },
    }
    store_response(txn_id, "select", on_select)
    print(f"[BPP] -> on_select stored  (catalog: {len(OUR_POLICY_DATA.get('policies',[]))} policies)")

    return jsonify({"message": {"ack": {"status": "ACK"}}})


# ─────────────────────────────────────────────────────────────
# Step 2: INIT — doosri team ne "haan, ye chahiye" kaha
# ─────────────────────────────────────────────────────────────

@app.route("/bpp/init", methods=["POST"])
@app.route("/bpp/receiver/init", methods=["POST"])
def handle_init():
    """
    INIT aaya:
    - ACK bhejo
    - on_init store karo (contract ACTIVE hua)
    """
    body    = request.json or {}
    ctx     = body.get("context", {})
    txn_id  = ctx.get("transactionId", str(uuid.uuid4()))

    print(f"\n[BPP] <- INIT received    txn={txn_id[:8]}...")

    on_init = {
        "context": {**ctx, "action": "on_init"},
        "message": {
            "contract": {
                "id": body.get("message", {}).get("contract", {}).get("id", ""),
                "status": {"code": "ACTIVE"},
            }
        },
    }
    store_response(txn_id, "init", on_init)
    print(f"[BPP] -> on_init stored   (contract ACTIVE)")

    return jsonify({"message": {"ack": {"status": "ACK"}}})


# ─────────────────────────────────────────────────────────────
# Step 3: CONFIRM — doosri team ne "confirm" kiya
# ─────────────────────────────────────────────────────────────

@app.route("/bpp/confirm", methods=["POST"])
@app.route("/bpp/receiver/confirm", methods=["POST"])
def handle_confirm():
    """
    CONFIRM aaya:
    - ACK bhejo
    - on_confirm store karo (deal confirmed)
    """
    body    = request.json or {}
    ctx     = body.get("context", {})
    txn_id  = ctx.get("transactionId", str(uuid.uuid4()))

    print(f"\n[BPP] <- CONFIRM received txn={txn_id[:8]}...")

    on_confirm = {
        "context": {**ctx, "action": "on_confirm"},
        "message": {
            "contract": {
                "id": body.get("message", {}).get("contract", {}).get("id", ""),
                "status": {"code": "ACTIVE"},
                "settlements": [{"status": "COMPLETE"}],
            }
        },
    }
    store_response(txn_id, "confirm", on_confirm)
    print(f"[BPP] -> on_confirm stored (deal confirmed)")

    return jsonify({"message": {"ack": {"status": "ACK"}}})


# ─────────────────────────────────────────────────────────────
# Step 4: STATUS — asli data delivery
# ─────────────────────────────────────────────────────────────

def load_arr_filing():
    """Load arr_filing.json agar available hai."""
    try:
        with open("arr_filing.json") as f:
            return json.load(f)
    except FileNotFoundError:
        return None


@app.route("/bpp/status", methods=["POST"])
@app.route("/bpp/receiver/status", methods=["POST"])
def handle_status():
    """
    STATUS aaya — YE SABSE IMPORTANT STEP HAI.
    - ACK bhejo
    - on_status store karo WITH ACTUAL DATA
    - Agar ARR filing request hai to arr_filing.json ka data bhejo
    - Warna tariff policy data bhejo
    """
    body   = request.json or {}
    ctx    = body.get("context", {})
    txn_id = ctx.get("transactionId", str(uuid.uuid4()))

    # Detect request type: ARR filing ya tariff policy?
    msg_str    = json.dumps(body).lower()
    is_arr     = any(k in msg_str for k in ["arr", "filing", "aggregate revenue", "idcl", "aperc"])
    arr_filing = load_arr_filing()

    print(f"\n[BPP] <- STATUS received  txn={txn_id[:8]}...  type={'ARR_FILING' if (is_arr and arr_filing) else 'TARIFF_POLICY'}")

    if is_arr and arr_filing:
        # ── ARR Filing delivery (usecase2 format) ──
        filing_data = arr_filing["dataPayload"]
        canonical   = json.dumps(filing_data, sort_keys=True, separators=(',', ':'))
        payload_hash = hashlib.sha256(canonical.encode()).hexdigest()

        on_status = {
            "context": {**ctx, "action": "on_status"},
            "message": {
                "contract": {
                    "id": body.get("message", {}).get("contract", {}).get("id", ""),
                    "descriptor": {
                        "name": "ARR Filing Data Exchange",
                        "shortDesc": "ARR filing submission under regulatory mandate"
                    },
                    "status": {"code": "ACTIVE"},
                    "commitments": [
                        {
                            "id": "commitment-arr-filing-001",
                            "status": {"descriptor": {"code": "CLOSED"}},
                            "resources": [
                                {
                                    "id": "ds-idcl-arr-filing-fy2024-25",
                                    "descriptor": {"name": "IDCL ARR Filing - FY 2024-25"},
                                    "quantity": {"unitText": "filing", "unitCode": "EA", "value": "1"}
                                }
                            ],
                            "offer": {
                                "id": "offer-arr-filing-inline",
                                "descriptor": {"name": "ARR Filing Inline Delivery - IDCL FY 2024-25"},
                                "resourceIds": ["ds-idcl-arr-filing-fy2024-25"]
                            }
                        }
                    ],
                    "performance": [
                        {
                            "id": "perf-arr-filing-delivery-001",
                            "status": {
                                "code": "DELIVERY_COMPLETE",
                                "name": "ARR filing delivered inline via dataPayload"
                            },
                            "commitmentIds": ["commitment-arr-filing-001"],
                            "performanceAttributes": {
                                "@context": "https://raw.githubusercontent.com/beckn/DDM/main/specification/schema/DatasetItem/v1/context.jsonld",
                                "@type": "DatasetItem",
                                "schema:identifier": "ds-idcl-arr-filing-fy2024-25",
                                "schema:name": "IDCL ARR Filing - FY 2024-25",
                                "schema:temporalCoverage": "2024-04-01/2025-03-31",
                                "dataset:accessMethod": "INLINE",
                                "dataset:sensitivityLevel": "PUBLIC",
                                "dataset:refreshType": "ANNUAL",
                                "payloadHash": payload_hash,
                                "dataPayload": filing_data
                            }
                        }
                    ],
                    "participants": [
                        {"id": "idcl-discom-001", "descriptor": {"name": "Infosys Distribution Company Limited"}},
                        {"id": "kerc-regulator-001", "descriptor": {"name": "KERC - Karnataka Electricity Regulatory Commission"}}
                    ],
                    "settlements": [
                        {
                            "id": "settlement-regulatory-mandate",
                            "status": "COMPLETE",
                            "settlementAttributes": {
                                "@type": "Payment",
                                "beckn:paymentStatus": "COMPLETED",
                                "beckn:amount": {"currency": "INR", "value": 0}
                            }
                        }
                    ]
                }
            }
        }
        store_response(txn_id, "status", on_status)
        print(f"[BPP] -> on_status ARR filing delivered  (hash={payload_hash[:20]}...)")

    else:
        # ── Tariff Policy delivery (original flow) ──
        canonical    = json.dumps(OUR_POLICY_DATA, sort_keys=True, separators=(',', ':'))
        payload_hash = hashlib.sha256(canonical.encode()).hexdigest()

        on_status = {
            "context": {**ctx, "action": "on_status"},
            "message": {
                "contract": {
                    "id": body.get("message", {}).get("contract", {}).get("id", ""),
                    "status": {"code": "ACTIVE"},
                    "performance": [
                        {
                            "id": "perf-tariff-delivery-001",
                            "status": {"code": "DELIVERY_COMPLETE"},
                            "performanceAttributes": {
                                "@context": "https://raw.githubusercontent.com/beckn/DDM/main/specification/schema/DatasetItem/v1/context.jsonld",
                                "@type": "DatasetItem",
                                "schema:identifier": "ds-infosys-serc-tariff-policy-fy2024-25",
                                "schema:name": "SERC Tariff Policy - Karnataka RES & COM - FY 2024-25",
                                "schema:temporalCoverage": "2024-04-01/2025-03-31",
                                "dataset:accessMethod": "INLINE",
                                "dataset:sensitivityLevel": "PUBLIC",
                                "payloadHash": payload_hash,
                                "dataPayload": OUR_POLICY_DATA
                            }
                        }
                    ]
                }
            }
        }
        store_response(txn_id, "status", on_status)
        print(f"[BPP] -> on_status tariff delivered  ({len(OUR_POLICY_DATA.get('policies',[]))} policies, hash={payload_hash[:20]}...)")

    return jsonify({"message": {"ack": {"status": "ACK"}}})


# ─────────────────────────────────────────────────────────────
# Polling endpoint — BAP yahan se response uthata hai
# ─────────────────────────────────────────────────────────────

@app.route("/api/responses/<txn_id>", methods=["GET"])
def poll_response(txn_id):
    """
    BAP yahan poll karta hai: GET /api/responses/<txn_id>?action=on_status
    GCP mock BPP ka same format.
    """
    action = request.args.get("action", "on_status")

    txn_data = response_store.get(txn_id, {})
    responses = txn_data.get(action, [])

    if responses:
        print(f"[BPP] POLL {action} txn={txn_id[:8]}... -> {len(responses)} response(s) found")
    else:
        print(f"[BPP] POLL {action} txn={txn_id[:8]}... -> not ready yet")

    return jsonify({"responses": responses})


# ─────────────────────────────────────────────────────────────
# Filing endpoint -- ARR Filing serve karo
# ─────────────────────────────────────────────────────────────

@app.route("/filing", methods=["GET"])
def get_filing():
    """Agar arr_filing.json hai to serve karo, warna 404."""
    import os
    if not os.path.exists("arr_filing.json"):
        return jsonify({"error": "No filing available. Run: python create_filing.py"}), 404
    with open("arr_filing.json") as f:
        filing = json.load(f)
    print(f"[BPP] FILING served")
    return jsonify(filing)


# ─────────────────────────────────────────────────────────────
# Health check
# ─────────────────────────────────────────────────────────────

@app.route("/health", methods=["GET"])
def health():
    policies = OUR_POLICY_DATA.get("policies", [])
    return jsonify({
        "status":   "UP",
        "server":   "Infosys TI BPP Producer",
        "policies": [p["policyID"] for p in policies],
        "activeTransactions": len(response_store),
    })


# ─────────────────────────────────────────────────────────────
# Start
# ─────────────────────────────────────────────────────────────

if __name__ == "__main__":
    print("\n" + "="*55)
    print("  Infosys TI BPP Server -- Tariff Policy Producer")
    print("="*55)
    print(f"  Port    : 5000")
    print(f"  Endpoints:")
    print(f"    POST /bpp/select")
    print(f"    POST /bpp/init")
    print(f"    POST /bpp/confirm")
    print(f"    POST /bpp/status")
    print(f"    GET  /api/responses/<txn_id>?action=on_status")
    print(f"    GET  /health")
    print("="*55 + "\n")

    app.run(host="0.0.0.0", port=5000, debug=False)
