"""
Mock BPP for IES Bootcamp — handles 3 use cases:
  1. Meter Telemetry (AMISP role)     → serves IES_Report data
  2. ARR Filing (DISCOM role)         → serves IES_ARR_Filing data
  3. Tariff Policy (Policy Provider)  → serves IES_Policy + IES_Program data

Receives beckn requests from ONIX BPP adapter, builds on_* responses
with IES bootcamp test data, and sends them back through ONIX BPP caller.

Supports the full beckn v2.0 flow:
  publish  → catalog registered (mock local DEDI)
  discover → on_discover (browse catalog)
  select   → on_select   (pick a specific dataset, get terms)
  init     → on_init     (activate contract)
  confirm  → on_confirm  (lock contract)
  status   → on_status   (deliver data, chunked for large datasets)

In production, publish/discover go through DEDI (fabric.nfh.global).
For the bootcamp, they're mocked locally so no registry access is needed.

Maintains in-memory transaction state for lifecycle enforcement.
"""

import json
import uuid
import copy
import logging
import os
from datetime import datetime, timezone
from pathlib import Path

import httpx
from fastapi import FastAPI, Request

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
log = logging.getLogger("mock-bpp")

app = FastAPI(title="IES Bootcamp Mock BPP")

# ---------------------------------------------------------------------------
# Config
# ---------------------------------------------------------------------------
BPP_CALLER_URL = os.getenv("BPP_CALLER_URL", "http://onix-bpp:8082/bpp/caller")
DATA_DIR = Path(os.getenv("DATA_DIR", "/data/bootcamp"))

DATASET_SCHEMA_URL = "https://raw.githubusercontent.com/beckn/DDM/main/specification/schema/DatasetItem/v1/context.jsonld"
IES_CORE_CONTEXT = "https://raw.githubusercontent.com/beckn/DEG/ies-specs/specification/external/schema/ies/core/context.jsonld"
IES_ARR_CONTEXT = "https://raw.githubusercontent.com/beckn/DEG/ies-specs/specification/external/schema/ies/arr/context.jsonld"
ORG_CONTEXT = "https://raw.githubusercontent.com/beckn/schemas/refs/heads/main/schema/Organization/v2.0/context.jsonld"
PRICE_CONTEXT = "https://raw.githubusercontent.com/beckn/schemas/refs/heads/main/schema/PriceSpecification/v2.1/context.jsonld"
PAYMENT_CONTEXT = "https://raw.githubusercontent.com/beckn/schemas/refs/heads/main/schema/Payment/v2.0/context.jsonld"

# Maximum number of telemetry resources to include inline (full chunks are ~3MB)
TELEMETRY_SAMPLE_RESOURCES = 3

# ---------------------------------------------------------------------------
# Data catalog definition
# ---------------------------------------------------------------------------
CATALOG = {
    "telemetry": {
        "id": "ds-ies-meter-telemetry",
        "name": "AMI Meter Telemetry — 15-min Interval Readings",
        "short_desc": "Smart meter kWh readings for 100 resources across residential and commercial programs",
        "temporal_coverage": "2024-04-15/2024-07-13",
        "record_count": "100 resources x 8760 intervals",
        # Multiple chunks — delivered one per status call
        "chunks": [f"telemetry_chunk_{i}.jsonld" for i in range(1, 11)],
        "ies_context": IES_CORE_CONTEXT,
        "ies_type": "IES_Report",
        "provider_id": "amisp-intelligrid-001",
        "provider_name": "IntelliGrid AMI Services (Mock AMISP)",
    },
    "arr-filings": {
        "id": "ds-ies-arr-filings",
        "name": "ARR Filings — Regulatory Revenue Requirement Data",
        "short_desc": "Aggregate Revenue Requirement filings from 2 DISCOMs (MYT + Historical)",
        "temporal_coverage": "2011/2029",
        "record_count": "2 filings, 19 fiscal years, 245 line items",
        "chunks": ["arr_filings.jsonld"],
        "ies_context": IES_ARR_CONTEXT,
        "ies_type": "IES_ARR_Filing",
        "provider_id": "discom-xxdcl-001",
        "provider_name": "Alpha State DISCOM (Mock Filing Provider)",
    },
    "tariff-policy": {
        "id": "ds-ies-tariff-policies",
        "name": "Tariff Policies — Machine-Readable Rate Structures",
        "short_desc": "Residential telescopic and commercial ToD tariff policies with energy slabs and surcharges",
        "temporal_coverage": "2024/2025",
        "record_count": "2 policies, 2 programs",
        "chunks": ["policies.jsonld"],
        "ies_context": IES_CORE_CONTEXT,
        "ies_type": "IES_Policy",
        "provider_id": "serc-policy-provider-001",
        "provider_name": "Regulatory Policy Publisher (Mock SERC)",
    },
}

# ---------------------------------------------------------------------------
# Lifecycle state machine
# ---------------------------------------------------------------------------
# Valid transitions: select always allowed, then init→confirm→status in order.
# DELIVERING is used when a multi-chunk dataset is being streamed (between first and last chunk).
LIFECYCLE_ORDER = ["SELECTED", "INITIALIZED", "CONFIRMED", "DELIVERING", "DELIVERED"]

# What state is required before each action can proceed?
REQUIRED_STATE = {
    "select":  None,           # always allowed — creates or resets txn
    "init":    "SELECTED",     # must have done select first
    "confirm": "INITIALIZED",  # must have done init first
    "status":  "CONFIRMED",    # must have done confirm first (also allows DELIVERING/DELIVERED for chunks/re-fetch)
}

# ---------------------------------------------------------------------------
# In-memory state
# ---------------------------------------------------------------------------
# transactions[transactionId] = {
#   "state": str,
#   "bap_id": str,
#   "dataset_id": str,
#   "contract_id": str,
#   "history": [{"action": str, "state": str, "timestamp": str}, ...],
#   "created_at": str,
#   "updated_at": str,
# }
transactions: dict[str, dict] = {}

# sent_responses[transactionId] = [{"action": "on_select", "payload": {...}, "sent_at": str}, ...]
sent_responses: dict[str, list] = {}

# ---------------------------------------------------------------------------
# Mock DEDI — in-memory catalog registry
# ---------------------------------------------------------------------------
# In production, publish sends catalog to DEDI (fabric.nfh.global) via ONIX BPP caller.
# For bootcamp, we store it locally. discover reads from this store.
# published_catalog[provider_id] = {"catalog": [...], "published_at": str, "bpp_id": str}
published_catalog: dict[str, dict] = {}


def _check_lifecycle(action: str, txn_id: str, bap_id: str) -> str | None:
    """Check if the action is allowed given current transaction state.
    Returns an error message if not allowed, None if OK."""
    required = REQUIRED_STATE.get(action)
    if required is None:
        return None  # select is always allowed

    txn = transactions.get(txn_id)
    if txn is None:
        return (
            f"No transaction found for {txn_id}. "
            f"You must call 'select' first to start a transaction."
        )

    # Verify same BAP
    if txn["bap_id"] != bap_id:
        return (
            f"Transaction {txn_id} belongs to BAP '{txn['bap_id']}', "
            f"but this request is from '{bap_id}'. "
            f"Each BAP must use its own transaction."
        )

    current = txn["state"]

    # status is allowed on CONFIRMED, DELIVERING (next chunk), or DELIVERED (re-fetch)
    if action == "status" and current in ("CONFIRMED", "DELIVERING", "DELIVERED"):
        return None

    if current != required:
        current_idx = LIFECYCLE_ORDER.index(current) if current in LIFECYCLE_ORDER else -1
        required_idx = LIFECYCLE_ORDER.index(required)
        if current_idx < required_idx:
            return (
                f"Cannot call '{action}' — transaction is in state '{current}'. "
                f"You must call '{_action_for_state(required)}' first. "
                f"Lifecycle: select → init → confirm → status"
            )
        else:
            # Already past this step
            return (
                f"Transaction already past '{action}' stage (current state: '{current}'). "
                f"Call 'select' again to start a new transaction."
            )

    return None


def _action_for_state(state: str) -> str:
    """Map a required state back to the action that produces it."""
    return {"SELECTED": "select", "INITIALIZED": "init", "CONFIRMED": "confirm"}.get(state, state)


def _advance_state(txn_id: str, new_state: str, bap_id: str, ds_id: str, contract_id: str, action: str):
    """Create or update transaction state."""
    now = _now()
    if txn_id in transactions:
        txn = transactions[txn_id]
        txn["state"] = new_state
        txn["updated_at"] = now
        txn["history"].append({"action": action, "state": new_state, "timestamp": now})
        # Update dataset if re-selecting
        if action == "select":
            txn["dataset_id"] = ds_id
            txn["contract_id"] = contract_id
    else:
        transactions[txn_id] = {
            "state": new_state,
            "bap_id": bap_id,
            "dataset_id": ds_id,
            "contract_id": contract_id,
            "created_at": now,
            "updated_at": now,
            "history": [{"action": action, "state": new_state, "timestamp": now}],
        }

# ---------------------------------------------------------------------------
# Load test data at startup
# ---------------------------------------------------------------------------
datasets: dict[str, dict] = {}


def _load_json(path: Path):
    if path.exists():
        with open(path) as f:
            return json.load(f)
    log.warning("Data file not found: %s", path)
    return None


@app.on_event("startup")
def load_data():
    """Load all dataset chunks at startup. Each dataset gets a list of chunks."""
    for ds_id, meta in CATALOG.items():
        chunk_files = meta["chunks"]
        loaded_chunks = []
        for fname in chunk_files:
            data = _load_json(DATA_DIR / fname)
            if data is not None:
                loaded_chunks.append(data)
            else:
                log.warning("Chunk file missing for %s: %s", ds_id, fname)
        datasets[ds_id] = loaded_chunks
        total_kb = sum(len(json.dumps(c)) for c in loaded_chunks) // 1024
        log.info("Dataset %-20s %d/%d chunks loaded (%dKB total)", ds_id, len(loaded_chunks), len(chunk_files), total_kb)

    # Also load programs (needed for tariff policy context)
    programs = _load_json(DATA_DIR / "programs.jsonld")
    if programs:
        datasets["programs"] = programs
        log.info("Dataset %-20s loaded (%d programs)", "programs", len(programs))

    # Auto-publish catalog to local mock DEDI
    _publish_catalog_locally()


def _build_catalog_items() -> list[dict]:
    """Build catalog item list from CATALOG + loaded datasets."""
    items = []
    for ds_id, meta in CATALOG.items():
        if not datasets.get(ds_id):
            continue
        chunks = datasets[ds_id]
        total_size_kb = sum(len(json.dumps(c)) for c in chunks) // 1024
        items.append({
            "id": meta["id"],
            "descriptor": {
                "name": meta["name"],
                "shortDesc": meta["short_desc"],
            },
            "temporalCoverage": meta["temporal_coverage"],
            "recordCount": meta["record_count"],
            "totalChunks": len(chunks),
            "totalSizeKB": total_size_kb,
            "accessMethod": "INLINE",
            "schemaType": meta["ies_type"],
            "schemaContext": meta["ies_context"],
            "provider": {
                "id": meta["provider_id"],
                "name": meta["provider_name"],
            },
        })
    return items


def _publish_catalog_locally():
    """Publish catalog to in-memory mock DEDI store."""
    items = _build_catalog_items()
    # Group by provider
    by_provider: dict[str, list] = {}
    for item in items:
        pid = item["provider"]["id"]
        by_provider.setdefault(pid, []).append(item)

    for pid, provider_items in by_provider.items():
        published_catalog[pid] = {
            "catalog": provider_items,
            "published_at": _now(),
            "bpp_id": "bpp.example.com",
        }

    total = sum(len(v["catalog"]) for v in published_catalog.values())
    log.info("Published %d catalog items from %d provider(s) to mock DEDI", total, len(published_catalog))


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _now():
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _msg_id():
    return str(uuid.uuid4())


def _flip_ctx(ctx: dict, action: str, ies_context: str | None = None) -> dict:
    out = {**ctx, "action": action, "messageId": _msg_id(), "timestamp": _now()}
    schema_contexts = [DATASET_SCHEMA_URL]
    if ies_context and ies_context not in schema_contexts:
        schema_contexts.append(ies_context)
    out["schemaContext"] = schema_contexts
    return out


def _ack():
    return {"message": {"ack": {"status": "ACK"}}}


def _nack(msg: str):
    return {"message": {"ack": {"status": "NACK"}, "error": {"code": "Bad Request", "message": msg}}}


def _strip_context(obj):
    """Remove @context from nested IES data to avoid ONIX domain validation errors."""
    if isinstance(obj, dict):
        return {k: _strip_context(v) for k, v in obj.items() if k != "@context"}
    if isinstance(obj, list):
        return [_strip_context(item) for item in obj]
    return obj


async def _send_response(payload: dict):
    action = payload["context"]["action"]
    txn_id = payload["context"].get("transactionId", "?")
    url = f"{BPP_CALLER_URL}/{action}"

    # Store the response for polling via /api/responses
    sent_responses.setdefault(txn_id, []).append({
        "action": action,
        "payload": payload,
        "sent_at": _now(),
    })

    try:
        async with httpx.AsyncClient(timeout=30) as client:
            resp = await client.post(url, json=payload)
            log.info("-> BPP caller %s status=%s", action, resp.status_code)
            if resp.status_code >= 400:
                log.error("   Error: %s", resp.text[:500])
    except Exception as e:
        log.error("Failed to send %s: %s", action, e)


# ---------------------------------------------------------------------------
# Dataset detection
# ---------------------------------------------------------------------------

def _detect_dataset(incoming: dict) -> str:
    """Determine which dataset is being requested from resource IDs/names."""
    try:
        commitments = incoming["message"]["contract"].get("commitments", [])
        for c in commitments:
            for r in c.get("resources", []):
                rid = r.get("id", "").lower()
                name = r.get("descriptor", {}).get("name", "").lower()
                text = rid + " " + name

                if any(kw in text for kw in ["telemetry", "meter", "ami", "report", "usage"]):
                    return "telemetry"
                if any(kw in text for kw in ["arr", "revenue", "filing", "regulatory"]):
                    return "arr-filings"
                if any(kw in text for kw in ["tariff", "policy", "rate", "slab", "tod"]):
                    return "tariff-policy"

                # Check against catalog IDs
                for ds_id in CATALOG:
                    if CATALOG[ds_id]["id"] in rid:
                        return ds_id
    except (KeyError, TypeError):
        pass
    return "telemetry"  # default


def _extract_buyer(incoming: dict) -> dict:
    try:
        for p in incoming["message"]["contract"].get("participants", []):
            role = p.get("participantAttributes", {}).get("organizationAttributes", {}).get("role", "")
            if role == "BUYER":
                return p
        participants = incoming["message"]["contract"].get("participants", [])
        if participants:
            return participants[-1]
    except (KeyError, TypeError):
        pass
    return {
        "id": "bootcamp-participant",
        "descriptor": {"name": "Bootcamp Participant"},
        "participantAttributes": {
            "@context": ORG_CONTEXT, "@type": "Organization",
            "id": "bootcamp-participant", "name": "Bootcamp Participant",
        },
    }


def _provider(ds_id: str) -> dict:
    meta = CATALOG.get(ds_id, CATALOG["telemetry"])
    return {
        "id": meta["provider_id"],
        "descriptor": {"name": meta["provider_name"]},
        "participantAttributes": {
            "@context": ORG_CONTEXT, "@type": "Organization",
            "id": meta["provider_id"], "name": meta["provider_name"],
            "organizationAttributes": {"role": "SELLER"},
        },
    }


# ---------------------------------------------------------------------------
# Routes
# ---------------------------------------------------------------------------

@app.post("/api/webhook/{action_path}")
@app.post("/api/webhook")
async def webhook(request: Request, action_path: str | None = None):
    body = await request.json()
    action = body.get("context", {}).get("action") or action_path or "unknown"
    txn_id = body.get("context", {}).get("transactionId", "?")
    log.info("<- %s txn=%s", action, txn_id)

    handler = {
        "publish": handle_publish,
        "discover": handle_discover,
        "select": handle_select,
        "init": handle_init,
        "confirm": handle_confirm,
        "status": handle_status,
    }.get(action)

    if handler:
        return await handler(body)

    log.warning("No handler for action=%s", action)
    return _ack()


@app.get("/api/health")
def health():
    return {
        "status": "ok",
        "service": "ies-bootcamp-mock-bpp",
        "datasets": {
            ds_id: {
                "loaded": bool(datasets.get(ds_id)),
                "chunks": len(datasets.get(ds_id, [])),
                "total_chunks": len(CATALOG[ds_id]["chunks"]),
            }
            for ds_id in CATALOG
        },
        "active_transactions": len(transactions),
        "catalog_published": {
            pid: len(entry["catalog"])
            for pid, entry in published_catalog.items()
        },
    }


@app.get("/api/transactions")
def list_transactions():
    """List all transactions with their current state."""
    return {
        "count": len(transactions),
        "transactions": {
            txn_id: {
                "state": txn["state"],
                "bap_id": txn["bap_id"],
                "dataset_id": txn["dataset_id"],
                "chunk_index": txn.get("chunk_index", 0),
                "total_chunks": len(CATALOG.get(txn["dataset_id"], {}).get("chunks", [])),
                "created_at": txn["created_at"],
                "updated_at": txn["updated_at"],
            }
            for txn_id, txn in transactions.items()
        },
    }


@app.get("/api/transactions/{txn_id}")
def get_transaction(txn_id: str):
    """Get full detail for a single transaction including lifecycle history."""
    txn = transactions.get(txn_id)
    if not txn:
        return {"error": f"Transaction {txn_id} not found", "hint": "Call 'select' first to create a transaction."}
    return {"transactionId": txn_id, **txn}


@app.get("/api/responses/{txn_id}")
def get_responses(txn_id: str, action: str | None = None):
    """Retrieve on_* responses sent for a transaction. Poll this after sending requests."""
    entries = sent_responses.get(txn_id, [])
    if action:
        entries = [e for e in entries if e["action"] == action]
    return {"transactionId": txn_id, "count": len(entries), "responses": entries}


@app.get("/api/catalog")
def get_catalog():
    """View the published catalog (mock DEDI contents)."""
    all_items = []
    for pid, entry in published_catalog.items():
        all_items.extend(entry["catalog"])
    return {
        "source": "mock-dedi (local)",
        "note": "In production, this catalog lives on DEDI (fabric.nfh.global)",
        "providers": len(published_catalog),
        "total_items": len(all_items),
        "items": all_items,
        "published_at": next(
            (e["published_at"] for e in published_catalog.values()), None
        ),
    }


@app.get("/api/responses")
def list_all_responses():
    """List all transactions that have stored responses."""
    return {
        "transactions": {
            txn_id: [e["action"] for e in entries]
            for txn_id, entries in sent_responses.items()
        }
    }


# ---------------------------------------------------------------------------
# publish — register catalog in mock DEDI
# ---------------------------------------------------------------------------
# In production: ONIX BPP caller routes publish → DEDI (fabric.nfh.global/beckn/catalog)
# For bootcamp: we handle it locally, storing in published_catalog dict.

async def handle_publish(incoming: dict):
    """BPP publishes its catalog. Stores in local mock DEDI."""
    ctx = _flip_ctx(incoming["context"], "on_publish", IES_CORE_CONTEXT)
    bpp_id = incoming["context"].get("bppId", "bpp.example.com")

    # Re-publish catalog from current loaded datasets
    _publish_catalog_locally()

    all_items = []
    for entry in published_catalog.values():
        all_items.extend(entry["catalog"])

    log.info("  publish: %d catalog items registered in mock DEDI (bpp=%s)", len(all_items), bpp_id)

    response = {
        "context": ctx,
        "message": {
            "catalog": {
                "descriptor": {
                    "name": "IES Bootcamp Catalog",
                    "shortDesc": f"Published {len(all_items)} datasets to mock DEDI",
                },
                "providers": [
                    {
                        "id": pid,
                        "descriptor": {"name": entry["catalog"][0]["provider"]["name"] if entry["catalog"] else pid},
                        "items": entry["catalog"],
                        "publishedAt": entry["published_at"],
                    }
                    for pid, entry in published_catalog.items()
                ],
                "note": "Mock local DEDI — in production, this goes to fabric.nfh.global",
            },
        },
    }

    await _send_response(response)
    return _ack()


# ---------------------------------------------------------------------------
# discover → on_discover — browse the catalog
# ---------------------------------------------------------------------------
# In production: BAP sends discover → ONIX BAP → DEDI → returns matching catalog entries.
# For bootcamp: mock BPP returns catalog from local store.

async def handle_discover(incoming: dict):
    """BAP discovers available datasets. Returns catalog from mock DEDI."""
    ctx = _flip_ctx(incoming["context"], "on_discover", IES_CORE_CONTEXT)
    ctx["schemaContext"].append(IES_ARR_CONTEXT)
    txn_id = incoming["context"]["transactionId"]

    # Extract optional search filters from the incoming message
    search_intent = incoming.get("message", {}).get("intent", {})
    descriptor = search_intent.get("descriptor", {}) if search_intent else {}
    keyword = descriptor.get("name", "").lower()

    # Collect all published catalog items
    all_items = []
    for entry in published_catalog.values():
        all_items.extend(entry["catalog"])

    # Filter by keyword if provided
    if keyword:
        filtered = []
        for item in all_items:
            text = (
                item.get("descriptor", {}).get("name", "")
                + " " + item.get("descriptor", {}).get("shortDesc", "")
                + " " + item.get("schemaType", "")
            ).lower()
            if keyword in text:
                filtered.append(item)
        all_items = filtered

    log.info("  discover: returning %d catalog items (keyword=%r)", len(all_items), keyword or "(none)")

    # Store response for polling
    response = {
        "context": ctx,
        "message": {
            "catalog": {
                "descriptor": {
                    "name": "IES Bootcamp — Available Datasets",
                    "shortDesc": f"Found {len(all_items)} dataset(s)",
                },
                "items": all_items,
                "source": "mock-dedi (local)",
                "note": "In production, discover queries DEDI (fabric.nfh.global)",
            },
        },
    }

    await _send_response(response)
    return _ack()


# ---------------------------------------------------------------------------
# on_select — pick a specific dataset, get terms
# ---------------------------------------------------------------------------
# Unlike discover (which returns the full catalog), select is for a
# specific dataset. The BAP indicates which one via resource IDs/names.

async def handle_select(incoming: dict):
    txn_id = incoming["context"]["transactionId"]
    bap_id = incoming["context"].get("bapId", "unknown")
    ds_id = _detect_dataset(incoming)
    contract_id = incoming.get("message", {}).get("contract", {}).get("id", str(uuid.uuid4()))

    meta = CATALOG.get(ds_id, CATALOG["telemetry"])
    ctx = _flip_ctx(incoming["context"], "on_select", meta["ies_context"])

    # select always allowed — creates or resets transaction
    _advance_state(txn_id, "SELECTED", bap_id, ds_id, contract_id, "select")
    log.info("  txn %s: SELECTED (bap=%s, dataset=%s)", txn_id[:12], bap_id, ds_id)

    # Build commitment for the SELECTED dataset only (not full catalog)
    chunks = datasets.get(ds_id, [])
    total_chunks = len(chunks)

    commitment = {
        "id": f"commitment-{ds_id}",
        "status": {"descriptor": {"code": "DRAFT"}},
        "resources": [{
            "id": meta["id"],
            "descriptor": {"name": meta["name"], "shortDesc": meta["short_desc"]},
            "quantity": {"unitText": meta["record_count"], "unitCode": "EA", "value": "1"},
        }],
        "offer": {
            "id": f"offer-{ds_id}-inline",
            "descriptor": {"name": f"Inline Delivery — {meta['name']}"},
            "resourceIds": [meta["id"]],
        },
        "commitmentAttributes": {
            "@context": [DATASET_SCHEMA_URL, meta["ies_context"]],
            "@type": "DatasetItem",
            "schema:identifier": meta["id"],
            "schema:name": meta["name"],
            "schema:temporalCoverage": meta["temporal_coverage"],
            "dataset:accessMethod": "INLINE",
            "ies:schemaType": meta["ies_type"],
            "ies:schemaContext": meta["ies_context"],
            "totalChunks": total_chunks,
        },
    }

    response = {
        "context": ctx,
        "message": {
            "contract": {
                "id": contract_id,
                "descriptor": {
                    "name": f"IES Data Exchange — {meta['name']}",
                    "shortDesc": meta["short_desc"],
                },
                "status": {"code": "DRAFT"},
                "commitments": [commitment],
                "consideration": [{
                    "id": "consideration-bootcamp-free",
                    "status": {"code": "ACTIVE"},
                    "considerationAttributes": {
                        "@context": PRICE_CONTEXT,
                        "@type": "PriceSpecification",
                        "currency": "INR", "value": 0,
                        "description": "Bootcamp — free access",
                    },
                }],
                "participants": [_provider(ds_id), _extract_buyer(incoming)],
                "performance": [],
                "settlements": [],
            }
        },
    }

    await _send_response(response)
    return _ack()


# ---------------------------------------------------------------------------
# on_init — activate contract
# ---------------------------------------------------------------------------

async def handle_init(incoming: dict):
    txn_id = incoming["context"]["transactionId"]
    bap_id = incoming["context"].get("bapId", "unknown")

    # Enforce lifecycle: must have done select first
    err = _check_lifecycle("init", txn_id, bap_id)
    if err:
        log.warning("  txn %s: init REJECTED — %s", txn_id[:12], err)
        return _nack(err)

    ds_id = transactions[txn_id]["dataset_id"]
    meta = CATALOG.get(ds_id, CATALOG["telemetry"])
    ctx = _flip_ctx(incoming["context"], "on_init", meta["ies_context"])
    contract_id = incoming.get("message", {}).get("contract", {}).get("id", transactions[txn_id]["contract_id"])
    _advance_state(txn_id, "INITIALIZED", bap_id, ds_id, contract_id, "init")
    log.info("  txn %s: INITIALIZED", txn_id[:12])

    contract = copy.deepcopy(incoming.get("message", {}).get("contract", {}))
    contract["status"] = {"code": "ACTIVE"}
    for c in contract.get("commitments", []):
        c["status"] = {"descriptor": {"code": "ACTIVE"}}

    response = {"context": ctx, "message": {"contract": contract}}
    await _send_response(response)
    return _ack()


# ---------------------------------------------------------------------------
# on_confirm — lock contract
# ---------------------------------------------------------------------------

async def handle_confirm(incoming: dict):
    txn_id = incoming["context"]["transactionId"]
    bap_id = incoming["context"].get("bapId", "unknown")

    # Enforce lifecycle: must have done init first
    err = _check_lifecycle("confirm", txn_id, bap_id)
    if err:
        log.warning("  txn %s: confirm REJECTED — %s", txn_id[:12], err)
        return _nack(err)

    ds_id = transactions[txn_id]["dataset_id"]
    meta = CATALOG.get(ds_id, CATALOG["telemetry"])
    ctx = _flip_ctx(incoming["context"], "on_confirm", meta["ies_context"])
    contract_id = incoming.get("message", {}).get("contract", {}).get("id", transactions[txn_id]["contract_id"])
    _advance_state(txn_id, "CONFIRMED", bap_id, ds_id, contract_id, "confirm")
    log.info("  txn %s: CONFIRMED", txn_id[:12])

    contract = copy.deepcopy(incoming.get("message", {}).get("contract", {}))
    contract["status"] = {"code": "ACTIVE"}
    for c in contract.get("commitments", []):
        c["status"] = {"descriptor": {"code": "ACTIVE"}}

    response = {"context": ctx, "message": {"contract": contract}}
    await _send_response(response)
    return _ack()


# ---------------------------------------------------------------------------
# on_status — deliver actual data
# ---------------------------------------------------------------------------

async def handle_status(incoming: dict):
    txn_id = incoming["context"]["transactionId"]
    bap_id = incoming["context"].get("bapId", "unknown")
    contract_id = incoming.get("message", {}).get("contract", {}).get("id", str(uuid.uuid4()))

    # Enforce lifecycle: must have done confirm first
    err = _check_lifecycle("status", txn_id, bap_id)
    if err:
        log.warning("  txn %s: status REJECTED — %s", txn_id[:12], err)
        return _nack(err)

    ds_id = transactions[txn_id]["dataset_id"]
    meta = CATALOG.get(ds_id, CATALOG["telemetry"])
    ctx = _flip_ctx(incoming["context"], "on_status", meta["ies_context"])

    chunks = datasets.get(ds_id, [])
    total_chunks = len(chunks)

    if not chunks:
        _advance_state(txn_id, "DELIVERED", bap_id, ds_id, contract_id, "status")
        response = {
            "context": ctx,
            "message": {
                "contract": {
                    "id": contract_id,
                    "status": {"code": "ACTIVE"},
                    "commitments": [{
                        "id": f"commitment-{ds_id}",
                        "status": {"descriptor": {"code": "ACTIVE", "name": "Data not available"}},
                    }],
                    "performance": [],
                }
            },
        }
        await _send_response(response)
        return _ack()

    # --- Chunk tracking ---
    txn = transactions[txn_id]

    # Initialize chunk index on first status call
    if "chunk_index" not in txn:
        txn["chunk_index"] = 0

    chunk_idx = txn["chunk_index"]

    # If already delivered all chunks and re-fetching, reset to re-deliver
    if txn["state"] == "DELIVERED":
        txn["chunk_index"] = 0
        chunk_idx = 0
        log.info("  txn %s: re-fetch — resetting chunk index to 0", txn_id[:12])

    # Get the current chunk
    chunk_data = chunks[chunk_idx]
    is_last_chunk = (chunk_idx >= total_chunks - 1)

    # Advance state
    if is_last_chunk:
        new_state = "DELIVERED"
        delivery_code = "DELIVERY_COMPLETE"
    else:
        new_state = "DELIVERING"
        delivery_code = "DELIVERY_IN_PROGRESS"

    _advance_state(txn_id, new_state, bap_id, ds_id, contract_id, "status")

    # Advance chunk index for next call
    txn["chunk_index"] = chunk_idx + 1

    log.info("  txn %s: %s (dataset=%s, chunk %d/%d)", txn_id[:12], new_state, ds_id, chunk_idx + 1, total_chunks)

    # Prepare payload for this chunk
    payload_data = _prepare_payload(ds_id, chunk_data)

    # Chunk metadata included in performanceAttributes
    chunk_meta = {
        "chunkIndex": chunk_idx,
        "totalChunks": total_chunks,
        "isLastChunk": is_last_chunk,
    }

    response = {
        "context": ctx,
        "message": {
            "contract": {
                "id": contract_id,
                "descriptor": {
                    "name": f"IES Data Exchange — {meta['name']}",
                    "shortDesc": meta["short_desc"],
                },
                "status": {"code": "ACTIVE"},
                "commitments": [{
                    "id": f"commitment-{ds_id}",
                    "status": {"descriptor": {"code": "ACTIVE" if not is_last_chunk else "CLOSED"}},
                    "resources": [{
                        "id": meta["id"],
                        "descriptor": {"name": meta["name"]},
                        "quantity": {"unitText": meta["record_count"], "unitCode": "EA", "value": "1"},
                    }],
                    "offer": {
                        "id": f"offer-{ds_id}-inline",
                        "descriptor": {"name": f"Inline Delivery — {meta['name']}"},
                        "resourceIds": [meta["id"]],
                    },
                }],
                "performance": [{
                    "id": f"perf-{ds_id}-chunk-{chunk_idx}",
                    "status": {
                        "code": delivery_code,
                        "name": f"Chunk {chunk_idx + 1}/{total_chunks} — {meta['name']}",
                    },
                    "commitmentIds": [f"commitment-{ds_id}"],
                    "performanceAttributes": {
                        "@context": [DATASET_SCHEMA_URL, meta["ies_context"]],
                        "@type": "DatasetItem",
                        "schema:identifier": meta["id"],
                        "schema:name": meta["name"],
                        "schema:temporalCoverage": meta["temporal_coverage"],
                        "dataset:accessMethod": "INLINE",
                        "ies:schemaType": meta["ies_type"],
                        "ies:schemaContext": meta["ies_context"],
                        **chunk_meta,
                        "dataPayload": payload_data,
                    },
                }],
                "participants": [_provider(ds_id), _extract_buyer(incoming)],
                "settlements": [{
                    "id": "settlement-bootcamp",
                    "considerationId": "consideration-bootcamp-free",
                    "status": "COMPLETE",
                    "settlementAttributes": {
                        "@context": PAYMENT_CONTEXT,
                        "@type": "Payment",
                        "beckn:paymentStatus": "COMPLETED",
                        "beckn:amount": {"currency": "INR", "value": 0},
                    },
                }],
            },
        },
    }

    await _send_response(response)
    return _ack()


# ---------------------------------------------------------------------------
# Payload preparation per dataset type
# ---------------------------------------------------------------------------

def _prepare_payload(ds_id: str, chunk_data) -> dict | list:
    """Prepare a single chunk for inline delivery — strip @context and annotate."""

    if ds_id == "telemetry":
        return _prepare_telemetry(chunk_data)
    elif ds_id == "arr-filings":
        return _prepare_arr(chunk_data)
    elif ds_id == "tariff-policy":
        return _prepare_tariff(chunk_data)
    else:
        return _strip_context(chunk_data)


def _prepare_telemetry(chunk: dict) -> dict:
    """Prepare a single telemetry chunk. Each chunk has ~10 resources."""
    cleaned = _strip_context(chunk)
    if isinstance(cleaned, dict):
        cleaned["@type"] = "IES_Report"
        cleaned["objectType"] = "REPORT"
    return cleaned


def _prepare_arr(chunk) -> dict | list:
    """Prepare ARR filings chunk."""
    cleaned = _strip_context(chunk)
    if isinstance(cleaned, list):
        for filing in cleaned:
            if isinstance(filing, dict):
                filing["@type"] = "ARR_FILING"
                filing["objectType"] = "ARR_FILING"
    elif isinstance(cleaned, dict):
        cleaned["@type"] = "ARR_FILING"
        cleaned["objectType"] = "ARR_FILING"
    return cleaned


def _prepare_tariff(chunk) -> dict:
    """Combine policies chunk + programs into a single tariff intelligence payload."""
    policies = _strip_context(chunk)
    programs = _strip_context(datasets.get("programs", []))

    payload = {
        "@type": "IES_TariffIntelligence",
        "objectType": "TARIFF_INTELLIGENCE",
        "generatedAt": _now(),
        "description": "Machine-readable tariff policies with rate structures, energy slabs, and time-of-day surcharges",
        "programs": programs,
        "policies": policies if isinstance(policies, list) else [policies],
    }
    return payload
