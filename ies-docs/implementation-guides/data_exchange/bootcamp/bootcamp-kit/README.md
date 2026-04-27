# IES Data Exchange Bootcamp Kit

End-to-end beckn v2.0 data exchange testbed for the India Energy Stack.
Two components — one runs on a server (BPP), the other runs locally by each participant (BAP).

## Structure

```
bootcamp-kit/
├── example-data/         # Shared IES test data (telemetry, ARR, tariff)
│
├── mock-bpp-server/      # Deploy on GCP — the data provider
│   ├── docker-compose.yml  # Mounts ../example-data as /data/bootcamp
│   ├── mock-bpp/         # FastAPI app with lifecycle state machine
│   └── config/           # ONIX BAP + BPP adapter configs
│
├── mock-bap-client/      # Run locally — the data consumer
│   ├── bap_client.py     # Test client script
│   ├── docker-compose.yml # Local ONIX BAP (redis + onix-bap)
│   ├── config/           # BAP routing configs
│   └── requirements.txt
│
└── README.md             # This file
```

## Architecture

```
Participant's machine (mock-bap-client)        GCP server (mock-bpp-server)
┌──────────────────────────────┐               ┌──────────────────────────┐
│ bap_client.py                │               │                          │
│   ↕                          │  beckn v2.0   │                          │
│ ONIX BAP (:8081)             │──────────────→│ ONIX BPP (:8082)         │
│   ↕ signs, validates         │               │   ↕ signs, validates     │
│ callback server (:9000)      │←──────────────│ Mock BPP (:3002)         │
│   ↕ receives on_* with data  │  on_* reply   │   ↕ IES data + lifecycle │
└──────────────────────────────┘               └──────────────────────────┘
```

Each participant runs their own BAP — business logic + ONIX adapter is one unit.
The BPP server is shared infrastructure that serves IES energy data.

## Use Cases

| # | Name | Data |
|---|------|------|
| 1 | **Telemetry** | AMI smart meter 15-min interval kWh readings |
| 2 | **ARR Filings** | Aggregate Revenue Requirement — 2 DISCOMs, 19 fiscal years |
| 3 | **Tariff Policies** | Machine-readable rate structures, energy slabs, surcharges |

## Setup

### 1. Deploy the BPP server (one-time, on GCP)

See [`mock-bpp-server/README.md`](mock-bpp-server/README.md) for full instructions.

```bash
cd mock-bpp-server
# Upload to GCP VM and run:
docker compose up -d --build
```

Verify: `curl http://<GCP_IP>:3002/api/health`

### 2. Run the BAP client (each participant)

See [`mock-bap-client/README.md`](mock-bap-client/README.md) for full instructions.

```bash
cd mock-bap-client

# Start local ONIX BAP
docker compose up -d

# Install Python deps and run
pip install -r requirements.txt
python bap_client.py --mode local-bap --usecase all
```

### Quick Test (no Docker needed)

If a participant can't run Docker, poll mode works without a local BAP:

```bash
cd mock-bap-client
pip install -r requirements.txt
python bap_client.py --mode poll --usecase all
```

## Beckn Lifecycle

The mock BPP supports the full beckn v2.0 flow:

```
publish ──→ catalog registered (mock DEDI, auto on startup)

discover ──→ on_discover (browse catalog)
   ↓
select ──→ init ──→ confirm ──→ status ──→ status ──→ ...
  │          │         │          │          │
  ↓          ↓         ↓          ↓          ↓
SELECTED  INITIALIZED CONFIRMED  DELIVERING DELIVERED
                                 (chunk 1)  (last chunk)
```

- `discover` returns the full catalog — optional, not part of the transaction lifecycle
- `publish` registers catalog in mock DEDI (in production: `fabric.nfh.global`)
- `select` picks a specific dataset and starts a transaction
- `status` delivers data chunk by chunk for large datasets (e.g., telemetry = 10 chunks)
- Skipping steps → NACK with descriptive error
- Each transaction tracks the BAP that started it
- `status` can be re-called after delivery (re-fetch, resets to chunk 0)
- `select` resets the transaction

## IES Schemas

All responses reference IES schemas from:
- `https://github.com/beckn/DEG/tree/ies-specs/specification/external/schema/ies/core` — telemetry, tariff
- `https://github.com/beckn/DEG/tree/ies-specs/specification/external/schema/ies/arr` — ARR filings

## Requirements

| Component | Needs |
|-----------|-------|
| BPP server | Docker, GCP VM (e2-medium), ports 8081/8082/3001/3002 open |
| BAP client | Python 3.10–3.13, Docker (for local-bap mode) |
