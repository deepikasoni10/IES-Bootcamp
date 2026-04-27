# Mock BAP Client

Test the IES mock BPP running on GCP by sending beckn v2.0 requests
(select → init → confirm → status) and receiving real IES energy data.

## What's Inside

```
mock-bap-client/
├── config.json           # BPP server IP — change this one file when IP changes
├── bap_client.py         # BAP client script (reads config.json)
├── requirements.txt      # Python dependencies
├── docker-compose.yml    # Local ONIX BAP (redis + onix-bap)
└── config/
    ├── bap.yaml                  # ONIX BAP adapter config
    ├── routing-BAPCaller.yaml    # Routes requests → GCP BPP (auto-patched by bap_client.py)
    └── routing-BAPReceiver.yaml  # Routes callbacks (for future use)
```

## Quick Start (Local BAP — Recommended)

Run your own ONIX BAP locally. Your requests go through real beckn
signing and validation before reaching the GCP BPP.

**Prerequisites:** Docker, Python 3.10–3.13

```bash
# 1. Start your local ONIX BAP
docker compose up -d

# 2. Install Python deps
pip install -r requirements.txt

# 3. Run all use cases
python bap_client.py --mode local-bap --usecase all

# Or a single use case
python bap_client.py --mode local-bap --usecase telemetry
```

### Changing the BPP Server IP

Edit `config.json` — this is the only file you need to change:

```json
{
  "bpp_server_ip": "34.180.51.14"
}
```

The routing config is auto-patched when you run `bap_client.py`.
After changing the IP, restart your local BAP: `docker compose restart onix-bap`.

### How It Works

```
Your machine                              GCP server
┌──────────────────────────┐              ┌─────────────────────────┐
│ bap_client.py            │              │                         │
│   ↕ sends requests       │  beckn v2.0  │                         │
│ ONIX BAP (:8081)         │─────────────→│ ONIX BPP (:8082)        │
│   signs & validates      │              │   ↕ validates & routes  │
│                          │              │ Mock BPP (:3002)         │
│   polls for response  ←──│──────────────│   ↕ stores response     │
└──────────────────────────┘              └─────────────────────────┘
```

1. `bap_client.py` sends `select` to your local ONIX BAP (localhost:8081)
2. Your ONIX BAP signs the request and forwards to ONIX BPP on GCP
3. ONIX BPP validates and routes to Mock BPP
4. Mock BPP generates `on_select` with IES data and stores it
5. `bap_client.py` polls mock BPP's response store and prints the data
6. Repeat for `init` → `confirm` → `status` (actual data arrives in `on_status`)

### Verify Local BAP Is Running

```bash
curl http://localhost:8081/health
```

### Pointing to a Different BPP Server

Edit `config/routing-BAPCaller.yaml` and change the target URL:

```yaml
target:
  url: "http://<your-bpp-ip>:8082/bpp/receiver"
```

Then restart: `docker compose restart onix-bap`

## Alternative: Poll Mode (No Docker Needed)

If you can't run Docker locally, use poll mode. This sends requests through
a shared BAP on GCP and polls the mock BPP's response store for results.

```bash
pip install -r requirements.txt
python bap_client.py --mode poll --usecase all
```

No local Docker needed — just Python.

## Use Cases

| Name | Description | Data |
|------|-------------|------|
| `telemetry` | AMI smart meter data | 15-min interval kWh readings |
| `arr` | Annual Revenue Requirement filings | 2 DISCOMs, 19 fiscal years |
| `tariff` | Tariff rate structures | Policies, programs, energy slabs |

## Lifecycle Enforcement

The mock BPP enforces the beckn lifecycle. You must follow the order:

```
select → init → confirm → status
```

- Skipping steps returns a NACK with a descriptive error
- Each transaction tracks which BAP started it
- `status` can be called multiple times after `confirm` (re-fetch)
- Calling `select` again resets the transaction

Inspect transaction state:

```bash
curl http://34.180.51.14:3002/api/transactions
curl http://34.180.51.14:3002/api/transactions/<txn_id>
```

## Requirements

- Python 3.10–3.13 (3.14 beta is **not** supported — FastAPI/pydantic don't work with it yet)
- Docker (for local-bap mode only)
- Network access to `34.180.51.14` ports 8082 and 3002

## Troubleshooting

| Problem | Fix |
|---------|-----|
| Port 6379 already in use | Normal — Redis only runs inside Docker network, no host port needed |
| `docker compose up` fails on Mac M1/M2 | ONIX image is amd64 — Docker Desktop handles emulation automatically |
| `Connection refused` on port 8081 | Run `docker compose up -d` first, wait 10s for ONIX to start |
| Poll mode timeout | Check GCP is reachable: `curl http://34.180.51.14:3002/api/health` |
