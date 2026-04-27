# Energy Data Exchange — India Energy Stack (IES)
**Unified, Repeatable Data Exchange for the Power Sector**

---

## The Shift

IES has been developing two parallel specifications — **Regulatory Data Exchange** (attested filings between DISCOMs and regulators) and **Energy Policy as Code** (machine-readable, executable policy packs). In practice, both are data exchange problems: structured data moves between authorised parties, requires discovery, must be validated and attested, and produces verifiable receipts.

Treating these as separate use cases fragments the architecture. A tariff policy pack is data. A regulatory filing is data. A public disclosure derived from a filing is data. A consumer energy credential is data. The only things that change are **who can see it**, **how it moves**, and **what trust proof is attached**.

IES now unifies these under a single **Energy Data Exchange** architecture — one set of specifications, two exchange modes.

---

## Architecture: Public and Private Data Exchange

### Public Data Exchange

Public data is data containing no attributes with privacy or confidentiality implications — general-purpose datasets, regulatory aggregates, and data that is open by obligation or policy. It is **discoverable by anyone, verifiable by anyone, and hosted at source**, with no access-gating or purpose-limiting controls. If a custodian requires access control or usage constraints on a dataset, that dataset belongs in the private channel regardless of whether it contains consumer PII.

**What lives here:** published tariff policy packs, public regulatory disclosures (derived from accepted filings), DER registry entries, approved participant directories, revocation lists, tariff schedules, certified equipment lists, and any data a custodian designates as open.

**How it works:**

- **Directories and Decentralised Discovery (DeDi):** Custodians register **once** in DeDi with a URL pointing to a self-maintained catalog file — a static, cacheable JSON document listing all their published datasets (each entry carrying a dataset URL, schema reference, hash, and license terms URL). DeDi provides a cryptographically verifiable, on-chain layer for entity records, public keys, endpoints, and attestation status. There is no search API requirement for public data; catalog files are static and can be cached or crawled by any indexing layer.
- **Retrieval:** Once a catalog URL is resolved from DeDi, data is fetched directly from the custodian's endpoint. No central repository. Data stays at source; discovery is global.
- **Trust:** Integrity via content hashes, issuer signatures, and version chains. Public registries hold issuer public keys for verification.

Policy packs, public disclosures, and directory records all flow through this channel.

### Private Data Exchange

Private data is **access-controlled, consent-gated, and transacted via API-based protocols**. Private data may contain sensitive consumer or business data — though it need not. Any dataset requiring access control or usage terms belongs here.

**What lives here:** regulatory filings (DISCOM → regulator), consumer-level data (meter data, billing, connection details), restricted disclosures shared under policy, brokered datasets for research or planning, and any data that requires authorisation before access.

**How it works:**

- **API-Based Transactions:** IES defines an asynchronous request/callback protocol — a standard packet envelope with correlation IDs, immediate ACK/NACK, and async payload delivery via paired callbacks. This draws from established open-network transaction conventions (search/on_search, confirm/on_confirm, etc.). Data does not travel through the protocol packet; callbacks carry a **`payloadHash`** (sha256 digest for integrity verification) and a **`payloadUrl`** (time-limited, dynamically generated, authorization-enforced URL from which the requester fetches data directly from the custodian).
- **Credential-Gated Access:** Energy credentials (W3C Verifiable Credentials) determine who can access what. Institutional data access is governed by role-based credentials (regulator role, auditor role, researcher role with purpose constraints).
- **Consumer Data — Credential-Issuance-First:** Consumer personal data (consumption history, meter data, billing records, consumer profile) follows a distinct model. DISCOMs MUST issue these datasets as verifiable credentials delivered directly to the consumer — through their portal, app, DigiLocker, or equivalent interface — at regular intervals or on demand. An API endpoint for the same data is optional. DISCOMs that implement one MUST perform off-channel authentication of the consumer (OTP, app-based challenge, or equivalent) before releasing data; a credential reference alone is insufficient because credentials are bearer artefacts and do not prove the presenting party is the data subject.
- **Brokered Exchange:** For data shared with third parties (researchers, policymakers, market analysts), IES inherits principles from the Decentralised Data Marketplace (DDM) framework: data remains at source, contributor retains control, access terms are codified, and transactions produce receipts. The custodian sets differential access terms by accessor class.

Regulatory filings, consumer data sharing, and restricted research access all flow through this channel.

### The Common Layer

Both modes share:

- **IES Common Envelope** — every data object (filing, policy pack, disclosure, credential) uses the same outer packet structure with context routing and correlation.
- **Energy Credentials** — the trust glue. Credentials attest identity, authority, and access rights. Public data uses credentials for issuer verification. Private data uses credentials for access gating and consent.
- **Receipts and Provenance** — every meaningful exchange produces a verifiable receipt binding parties, content hashes, timestamps, and outcome status.
- **JSON-LD Semantics** — data objects carry their own semantic context, making them portable and interpretable across systems without shared databases.

---

## What This Delivers

| Outcome | How |
|---|---|
| **Policy as Code** stays visible | Tariff packs, once attested, are published to the public data exchange; anyone can discover and pull them via catalog |
| **Regulatory filings** stay private until disclosure | Filed via private exchange; accepted filings produce public disclosure objects if policy permits |
| **Consumer data** is credential-issuance-first | DISCOMs issue consumer credentials directly; API access is optional and requires off-channel consumer authentication |
| **Research / brokered access** is structured | DDM-aligned patterns: data stays at source, access terms codified, payloadHash + payloadUrl in receipt |
| **One spec, many use cases** | Same envelope, same credential model, same receipt structure — whether the data is a tariff slab, a filing, or a meter reading |

---

## Data Custodianship

IES does not centralise data. Custodianship stays where authority lies:

- **Regulators (SERCs/CERC)** own and host regulatory request objects, rulebooks, and acceptance receipts.
- **DISCOMs** own and host filings, consumer data, DER registries, and energy credentials they issue to consumers.
- **Policy publishers** (regulator or designated body) own and host attested policy packs.
- **Public directories** are maintained by designated operators (could be REC, could be federated across states) following IES directory specifications.
- **Consumers** hold their own credentials and consent artefacts.

IES defines the **envelope, the semantics, the interaction patterns, the credential model, and the conformance kit** — not the storage.

---

## Open Schema Principle

IES defines schemas for its anchor use cases. Beyond these, the ecosystem may define and publish additional schemas without requiring IES approval. Any schema used in an IES-based integration must be openly published — closed or proprietary schemas are not permitted for integrations that other parties depend on. IES does not act as a gatekeeper; it acts as a floor.

---

## Relationship to Existing Work

The schemas developed for Regulatory Data Exchange (Filing, Receipt, Disclosure, ValidationReport, Request) and Energy Policy as Code (PolicyRecord, EffectivePolicyObject, TariffPlan, ToDOverlay, DynamicPriceSignal) are **preserved**. They become payload profiles within the unified data exchange envelope — different body types, same header and interaction grammar. The DDM thesis from NFH/Beckn informs the brokered exchange philosophy without making IES dependent on any single protocol implementation.

---

*India Energy Stack — Ministry of Power | REC Limited (Programme Nodal Agency) | FSR Global (Knowledge Partner)*