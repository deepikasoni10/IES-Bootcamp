# India Energy Stack (IES)

This repository contains specifications, implementation guides, and schemas for the India Energy Stack (IES) — an open protocol stack for interoperable energy transactions in India.

## Overview

IES provides the **protocol and governance layer** that allows diverse energy stakeholders — consumers, prosumers, DISCOMs, aggregators, regulators, and technology providers — to interact using open, verifiable standards.

IES draws on existing DPIs and open standards including IEC 61850, Beckn Protocol, W3C Verifiable Credentials, and CIM Standards, and organises them around a set of core architecture primitives.

## Repository Structure

```
ies-docs/
├── architecture/           # Core IES architecture primitives
└── implementation-guides/  # Use case specifications and implementation guides
```

### Use Case Descriptions and Implementation Guides

The [`implementation-guides/`](./implementation-guides/) directory contains use case specifications. Each guide describes the problem statement, stakeholders, user journeys, data models, and API interaction patterns.

| Use Case | Description |
|----------|-------------|
| [Energy Data Exchange](./implementation-guides/data_exchange/) | Unified public and private data exchange — regulatory filings, policy packs, disclosures, and attested datasets |
| [DER Visibility](./implementation-guides/der_visibility/) | Standardised DER registry, MNRE M2M telemetry ingestion, and verified asset-to-grid linkage for DISCOMs |
| [Demand Side Flexibility](./implementation-guides/demand_flexibility/) | End-to-end workflow for demand response — programme discovery, enrolment, dispatch, verification, and settlement |
| [P2P Energy Exchange](./implementation-guides/p2p_energy_exchange/) | Intra-discom and inter-discom peer-to-peer energy trading specifications |
| [Energy Credentials](./implementation-guides/energy_credentials/) | DISCOM integration guide for issuing and sharing energy credentials via DigiLocker |

### Architecture

The [`architecture/`](./architecture/) directory documents the eight foundational primitives that underpin all IES use cases.

## Related Repositories

- [Digital Energy Grid (DEG)](https://github.com/Beckn-One/DEG) — upstream architecture documentation and full primitive specifications
- [Common Information Model (CIM)](https://www.iec.ch/iec61968)
- [IEC 61850](https://www.iec.ch/iec61850)

## License

This repository is licensed under the MIT License. See [LICENSE](./LICENSE) for details.
