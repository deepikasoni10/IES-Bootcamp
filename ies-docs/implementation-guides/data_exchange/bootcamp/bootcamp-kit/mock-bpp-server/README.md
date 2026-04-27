# Mock BPP Server

A self-contained beckn BPP (Backend Provider Platform) that serves IES energy data for 3 use cases:

| Dataset | Description | Size |
|---------|-------------|------|
| **Telemetry** | AMI smart meter 15-min interval readings | 100 resources, 8760 intervals |
| **ARR Filings** | Aggregate Revenue Requirement filings | 2 DISCOMs, 19 fiscal years |
| **Tariff Policies** | Machine-readable rate structures | 2 policies, 2 programs |

## Architecture

```
Client (your machine)                    This server (GCP)
┌─────────────┐                  ┌──────────────────────────────────┐
│ bap_client  │ ──select/init──→ │ ONIX BAP (:8081)                 │
│ (poll mode) │                  │   ↕ signs, validates             │
│             │                  │ ONIX BPP (:8082)                 │
│             │                  │   ↕ signs, validates, routes     │
│             │ ←─poll──────────→│ Mock BPP (:3002)                 │
└─────────────┘                  │   ↕ lifecycle + IES data         │
                                 │ Sandbox BAP (:3001) — logs on_*  │
                                 │ Redis                            │
                                 └──────────────────────────────────┘
```

> The ONIX BAP is included here as a shared test instance. In production,
> each Network Participant runs their own BAP alongside their business logic.

The mock BPP supports the full beckn v2.0 flow:
- `publish` → registers catalog in mock DEDI (auto-published on startup)
- `discover` → browse available datasets (catalog search)
- `select` → pick a specific dataset, get terms (starts transaction)
- `init` → activate the contract (requires prior `select`)
- `confirm` → lock the contract (requires prior `init`)
- `status` → deliver data inline, chunked for large datasets (requires prior `confirm`)

Discover/publish use a local mock DEDI — in production these go through `fabric.nfh.global`.
Skipping lifecycle steps returns a NACK with a descriptive error message.

## What's Inside

```
mock-bpp-server/
├── docker-compose.yml        # 5 services: redis, onix-bap, onix-bpp, sandbox-bap, mock-bpp
├── config/
│   ├── bootcamp-bap.yaml                   # ONIX BAP adapter config
│   ├── bootcamp-bpp.yaml                   # ONIX BPP adapter config
│   ├── bootcamp-routing-BAPReceiver.yaml   # routes on_* → sandbox-bap
│   ├── bootcamp-routing-BPPReceiver.yaml   # routes inbound → mock-bpp
│   ├── local-simple-routing-BAPCaller.yaml # routes BAP outbound → BPP
│   └── local-simple-routing-BPPCaller.yaml # routes BPP outbound → BAP
├── mock-bpp/
│   ├── app.py                # FastAPI app with lifecycle state machine
│   ├── Dockerfile            # python:3.12-slim
│   └── requirements.txt      # fastapi, uvicorn, httpx
└── README.md

Data files live in ../example-data/ (shared across the bootcamp-kit).
The docker-compose volume mounts ../example-data as /data/bootcamp inside the container.

## Deploy to GCP

### 1. Create the VM

```bash
gcloud compute instances create ies-bootcamp \
  --zone=us-central1-a \
  --machine-type=e2-medium \
  --image-family=ubuntu-2204-lts \
  --image-project=ubuntu-os-cloud \
  --boot-disk-size=20GB \
  --metadata=startup-script='#!/bin/bash
    apt-get update
    apt-get install -y docker.io docker-compose-v2 unzip
    systemctl enable docker
    systemctl start docker
    usermod -aG docker $(ls /home | head -1)'
```

### 2. Open firewall ports

```bash
gcloud compute firewall-rules create allow-bootcamp-ports \
  --allow=tcp:8081,tcp:8082,tcp:3001,tcp:3002 \
  --target-tags=http-server \
  --description="ONIX BAP (8081), ONIX BPP (8082), Sandbox BAP (3001), Mock BPP (3002)"
```

Add the network tag to your VM:

```bash
gcloud compute instances add-tags ies-bootcamp \
  --zone=us-central1-a \
  --tags=http-server
```

### 3. Upload and start

```bash
# From your local machine — upload the entire bootcamp-kit directory
cd implementation-guides/data_exchange/bootcamp
gcloud compute scp --recurse bootcamp-kit/ ies-bootcamp:~/bootcamp-kit --zone=us-central1-a

# SSH into the VM and start
gcloud compute ssh ies-bootcamp --zone=us-central1-a -- \
  'cd ~/bootcamp-kit/mock-bpp-server && docker compose up -d --build'
```

### 4. Verify

```bash
EXTERNAL_IP=$(curl -s ifconfig.me)

# Mock BPP health
curl http://$EXTERNAL_IP:3002/api/health

# ONIX BAP health
curl http://$EXTERNAL_IP:8081/health

# ONIX BPP health
curl http://$EXTERNAL_IP:8082/health

# List transactions (should be empty)
curl http://$EXTERNAL_IP:3002/api/transactions
```

## API Endpoints

### Mock BPP (port 3002)

| Endpoint | Description |
|----------|-------------|
| `GET /api/health` | Health check + dataset load status + catalog status |
| `GET /api/catalog` | View the published catalog (mock DEDI contents) |
| `GET /api/transactions` | List all transactions with state + chunk progress |
| `GET /api/transactions/{txn_id}` | Full transaction detail + lifecycle history |
| `GET /api/responses/{txn_id}` | Poll for on_* responses (used by bap_client.py) |
| `GET /api/responses/{txn_id}?action=on_select` | Filter responses by action |
| `POST /api/webhook` | Receives beckn requests from ONIX BPP (internal) |

### ONIX BPP Adapter (port 8082)

| Endpoint | Description |
|----------|-------------|
| `POST /bpp/receiver/{action}` | Receives signed beckn requests from BAP |
| `POST /bpp/caller/{action}` | Sends signed on_* responses back to BAP |

### ONIX BAP Adapter (port 8081)

| Endpoint | Description |
|----------|-------------|
| `POST /bap/caller/{action}` | Accepts beckn requests from clients, signs and forwards to BPP |
| `POST /bap/receiver/{action}` | Receives on_* callbacks and routes to sandbox-bap |

## Updating After Changes

```bash
# Upload updated bootcamp-kit
cd implementation-guides/data_exchange/bootcamp
gcloud compute scp --recurse bootcamp-kit/ ies-bootcamp:~/bootcamp-kit --zone=us-central1-a

# Rebuild and restart mock-bpp (only service that needs --build)
gcloud compute ssh ies-bootcamp --zone=us-central1-a -- \
  'cd ~/bootcamp-kit/mock-bpp-server && docker compose up -d --build mock-bpp'
```

Only `mock-bpp` needs `--build` — redis and onix adapters use pre-built images.

## Testing with bap_client.py

See the [bootcamp-kit](../bootcamp-kit/) directory for the client-side script that tests against this server.

```bash
pip install httpx fastapi uvicorn
python bap_client.py --mode poll \
  --bap-url http://<EXTERNAL_IP>:8082/bpp/caller \
  --mock-bpp-url http://<EXTERNAL_IP>:3002 \
  --usecase all
```

## Cost

- **e2-medium** (2 vCPU, 4GB RAM): ~$28/month
- Stop when not in use: `gcloud compute instances stop ies-bootcamp --zone=us-central1-a`
- Start again: `gcloud compute instances start ies-bootcamp --zone=us-central1-a`
