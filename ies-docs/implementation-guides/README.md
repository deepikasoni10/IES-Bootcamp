# IES Implementation Guides

This directory contains implementation guides for the India Energy Stack (IES). Each guide covers the problem statement, stakeholders, data models, interaction patterns, and API specifications for a specific energy sector domain.

---

## Guides

### Energy Data Exchange
**Unified Public and Private Data Exchange Architecture**

Defines the unified architecture for data exchange across the power sector — covering both public data (policy packs, regulatory disclosures, DER registries, participant directories) and private data (regulatory filings, consumer data, brokered research access). Uses a common envelope, energy credentials, and an asynchronous request/callback protocol. Regulatory Data Exchange and Energy Policy as Code are both instances of this specification.

**[Read the Guide →](./data_exchange/)**

---

### DER Visibility
**Standardised DER Registry, Telemetry Ingestion & Verified Asset-to-Grid Linkage**

Establishes the standardised DER registry, MNRE M2M telemetry ingestion pipeline, and verified consumer-to-asset grid linkage for DISCOMs. Enables near-real-time generation visibility per transformer and feeder using inverter M2M data, underpinning scheduling, settlement, and flexibility programme participation.

**[Read the Guide →](./der_visibility/)**

---

### Consumer Side Flexibility
**Standardised Program Catalogue, Dispatch, Verification & Settlement** *(Draft)*

Defines the end-to-end workflow for consumer-side demand response — programme discovery and publication, consumer and device enrolment with consent, dispatch event messaging, baseline and M&V, and settlement with an auditable evidence chain.

**[Read the Guide →](./demand_flexibility/)**

---

### P2P Energy Exchange
**Intra-Discom and Inter-Discom Peer-to-Peer Energy Trading**

Specifications for peer-to-peer energy trading between prosumers within the same DISCOM (intra-discom) and across different DISCOMs (inter-discom).

**[Read the Guide →](./p2p_energy_exchange/)**

---

### Energy Credentials — DigiLocker Integration
**DISCOM Guide for Issuing Energy Credentials via DigiLocker**

Implementation guide for DISCOMs to integrate with DigiLocker, enabling consumers to receive and share IES Energy Credentials (connection proof, generation profile, consumption profile) as verifiable digital documents.

**[Read the Guide →](./energy_credentials/digilocker_integration_simplified.md)**

---

## Related Directories

- **[Architecture](../architecture/)** — Core IES architecture primitives and building blocks
