# IES Bootcamp — Infosys TI Track
**India Energy Stack Bootcamp | April 15–17, 2026 | REC World HQ, Gurugram**

> Built by: **Deepika Soni, Infosys**
> Track: **Tariff Intelligence (TI)** — DISCOM Role on India Energy Stack

---

## What We Built

We implemented a **Tariff Intelligence system** on the India Energy Stack (IES) using the Beckn DEG protocol.

As a **DISCOM (Distribution Company)**, we:
- Fetch machine-readable Karnataka tariff policies from GCP SERC server
- Generate real telescopic electricity bills using those policies
- Publish BESCOM ARR Filing (real KERC data) to the Beckn network
- Serve tariff + ARR data to other teams via Beckn select → init → confirm → status flow

---

## Repository Structure

```
IES/
├── TI/                        # Tariff Intelligence — core implementation
│   ├── bpp_server.py          # BPP server (port 5000) — serves tariff + ARR filing
│   ├── dashboard.py           # Browser UI — bill calculator + policy viewer (port 5001)
│   ├── tariff_engine.py       # Telescopic billing calculator
│   ├── arr_filing.json        # Real BESCOM ARR data (KERC Tariff Order 2023)
│   ├── policy_pack.json       # Karnataka tariff policies (GCP fetched, SHA-256 verified)
│   ├── cross_team_billing.py  # Consumes Team B meter data, computes bills
│   └── generate_bill.py       # Generates formatted electricity bills
│
├── IES-App/                   # React + Node.js frontend app for ARR filing workflow
│   ├── src/                   # React frontend (Vite + Tailwind)
│   └── backend/               # Node.js Express backend
│
├── notes/
│   └── notes.md               # Demo notes, architecture, cross-questions & answers
│
└── architecture.html          # System architecture diagram
```

---

## TI Track — Key Features

### 1. Tariff Policy Fetch
- Fetches Karnataka SERC tariff from GCP server
- SHA-256 hash verification — tamper-proof data integrity
- 2 policies: **RES-T1** (residential telescopic) + **COM-TOU1** (commercial Time-of-Day)

### 2. Telescopic Bill Generation
- RES-T1 slabs: 0–100 @ ₹4.5 | 101–300 @ ₹7.5 | 301+ @ ₹10.5 per kWh
- COM-TOU1: ₹8.5 flat + ₹1.5 evening peak surcharge (6–10 PM)
- Night discount: –10% for off-peak consumption

**Example:** Ramesh Kumar, 350 units → **Bill: ₹2,439.64**

### 3. ARR Filing (Real KERC Data)
- Source: KERC Tariff Order 2023 (Official Karnataka Govt document)
- BESCOM Approved ARR: **₹28,872.87 Crores (FY 2023-24)**
- Line items: Power Purchase (₹20,500 Cr), Transmission (₹2,200 Cr), O&M (₹3,315.40 Cr), etc.
- Published via Beckn DEG as `IES_ARR_Filing` schema

### 4. Beckn Protocol Flow
```
BAP (other team)     →  select → init → confirm → status  →  OUR BPP (port 5000)
                     ←  on_status: { dataPayload: tariff / ARR filing }
```

### 5. Cross-Team Integration
- Consumed Team B smart meter data (10 meters, 96 intervals each)
- Computed bills using our tariff engine
- Total cross-team revenue: **₹8,664.57**

---

## How to Run

### BPP Server (Tariff + ARR Producer)
```bash
cd TI
pip install flask
python bpp_server.py
# Runs on http://localhost:5000
```

### Dashboard (Bill Calculator UI)
```bash
cd TI
python dashboard.py
# Open http://localhost:5001
```

### IES-App (ARR Filing Frontend)
```bash
cd IES-App
npm install
npm run dev
# Backend: cd backend && npm install && node src/server.js
```

---

## Key Numbers

| Metric | Value |
|--------|-------|
| Tariff policies loaded | 2 (RES-T1, COM-TOU1) |
| Policy hash (SHA-256) | `18c70df8c1dfc1dd...` |
| Sample bill (Ramesh Kumar, 350 units) | ₹2,439.64 |
| BESCOM Approved ARR | ₹28,872.87 Crores |
| Cross-team meters billed | 10 meters |
| Cross-team total revenue | ₹8,664.57 |

---

## External Repositories Used

| Repository | Purpose | Link |
|------------|---------|------|
| **beckn/DEG** | DEG Devkit — Beckn data exchange protocol implementation | [github.com/beckn/DEG](https://github.com/beckn/DEG/tree/main/devkits/data-exchange) |
| **beckn/beckn-onix** | Beckn ONIX — BAP/BPP adapter infrastructure | [github.com/beckn/beckn-onix](https://github.com/beckn/beckn-onix) |
| **India-Energy-Stack/ies-docs** | IES schemas, specs & implementation guides | [github.com/India-Energy-Stack/ies-docs](https://github.com/India-Energy-Stack/ies-docs/tree/main/implementation-guides/data_exchange) |
| **beckn/DDM** | Decentralised Data Marketplace spec | [github.com/beckn/DDM](https://github.com/beckn/DDM/tree/main) |

---

## Tech Stack

- **Backend:** Python (Flask), Node.js (Express)
- **Frontend:** React (Vite + Tailwind CSS)
- **Protocol:** Beckn DEG v2.0
- **Infrastructure:** Docker (ONIX adapter), ngrok (public tunnel)
- **Data:** Karnataka SERC tariff (GCP), KERC Tariff Order 2023

---

## Bootcamp Context

- **Event:** India Energy Stack Bootcamp, REC Limited, Gurugram
- **Dates:** April 15–17, 2026
- **Track:** Tariff Intelligence (TI)
- **Role played:** DISCOM (BPP) — Infosys Distribution Company Limited (IDCL)
- **Use cases implemented:** Usecase1 (Tariff Policy) + Usecase2 (ARR Filing)
