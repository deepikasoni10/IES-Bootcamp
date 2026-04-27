# Demand Flexibility - Draft - To be finalized
**Standardised Program Catalogue, Dispatch, Verification & Settlement**  
**India Energy Stack (IES)**

---

## Table of Contents
- [Overview](#overview)
- [Use Case Narrative](#use-case-narrative)
- [Applicability of IES](#applicability-of-ies)
- [Stakeholders](#stakeholders)
- [Key Performance Indicators](#key-performance-indicators)
- [Data Models and Standards](#data-models-and-standards)

---

## Overview

| Field | Value |
|---|---|
| **Use Case Name** | Consumer Side Flexibility |
| **Category** | Demand Response & Grid Services |
| **Status** | Active |

---

## Use Case Narrative

Consumer-side flexibility is technically feasible but operationally hard to scale because **enrolment, control, verification, and settlement** are fragmented across actors and systems. Consumers do not have a simple, trusted way to share their **connection identity, device capability, and program consent** with an app or aggregator, and DISCOMs struggle to dispatch reliably and verify outcomes quickly.

Today, flexibility is fragmented across utility IDs, device ecosystems, apps, DRMS tooling, and AMI systems. Even where each component exists, the end-to-end workflow is not standardised, which makes enrolment slow, dispatch unreliable, verification contested, and settlement delayed.

### What breaks today
- **Program discoverability is weak:** DR programs aren’t published as consistent, machine-readable catalogues
- **Identity-to-connection linkage is brittle:** Consumer ID, connection ID, premise, and meter mapping are inconsistent
- **Consent capture is non-reusable:** Permissions are collected as one-off forms without standard scope, validity, revocation
- **Device enrolment is siloed:** EVSEs, smart ACs, plugs expose different control models with no common capability descriptor
- **Dispatch messages are inconsistent:** Curtail/shed/restore signals vary by vendor and pilot
- **Telemetry is not aligned:** Device telemetry and AMI interval data arrive at different cadences and formats
- **Baseline and M&V are contested:** Approved methodologies aren’t operationalised as versioned logic with test vectors
- **Opt-out/override handling is messy:** Consumer comfort constraints and override reasons aren’t standardised
- **Settlement is slow and dispute-prone:** Computation is often spreadsheet-driven; statements lack itemisation
- **End-to-end auditability is missing:** No immutable linkage from enrolment → dispatch → verification → settlement
- **Security controls are uneven:** Remote control and data access vary across implementations

Consumer-Side Flexibility enables a standard end-to-end workflow where a consumer uses an app to:
- Discover flexibility programs
- Enrol eligible devices/assets (rooftop solar, BTM storage, EVs, flexible loads) with explicit consent
- Receive and execute dispatch signals during events
- Produce verifiable outcomes (telemetry summaries + meter-based verification)
- Complete settlement with an audit trail

The workflow is anchored in four interoperable exchanges:
1. **Program publication** (DISCOM or Market)
2. **Credential and consent** (consumer wallet)
3. **Device control and telemetry** (DER / home automation)
4. **Verification and settlement** (AMI interval data, baseline methodology, payout computation)

### Outcomes
- **Primary:** Reliable, measurable peak reduction that a DISCOM can dispatch and verify at low administrative cost
- **Secondary:** Consumer participation that is simple, transparent, reversible, and benefit-realising (faster settlement)

---

## Applicability of IES

Flexibility is inherently cross-actor: consumer identity is with the utility, device control is with OEM/home automation, dispatch is with DISCOM DRMS (or a market platform), and verification is with AMI/MDMS. Without common rails, each pilot becomes a bespoke integration that cannot scale.

IES provides the interoperability and trust primitives needed to make flexibility repeatable:
- Standard identifiers for **consumer–connection–meter–device** relationships
- **Consent-based data sharing** (minimal disclosure, revocable, time-scoped)
- **Policy-as-Code rulebooks** for eligibility, opt-out rules, comfort constraints, baseline/M&V and settlement logic (versioned, testable)
- **Tamper-evident receipts** linking enrolment, dispatch, verification, and settlement artifacts to an auditable history

> IES is not a central flexibility platform. It is the **protocol and governance layer** that allows many apps and aggregators to participate while keeping privacy, control, and accountability intact.

### Before IES vs After IES (Value Delivered)

| Step / Pain Point | Before IES | After IES (with IES) | Where IES Specifically Adds Value |
|---|---|---|---|
| Program publication | PDFs/portal pages; inconsistent program fields | Machine-readable program catalogues | Standardised Program Catalogue schema |
| Participant identity linkage | Fragmented IDs; weak consumer–meter mapping | Verifiable consumer–connection–meter linkage | Energy Credential primitives |
| Consent handling | One-off forms; non-reusable scopes | Reusable, revocable, time-scoped consent | Consent rails + standard scopes/revocation |
| Device capability description | OEM-specific models; no common descriptor | Standard capability descriptors for enrolment & control | Capability schema + conformance checks |
| Dispatch/event messages | Vendor-specific formats; inconsistent actions | Standard event objects (notify/curtail/restore) | Dispatch and event messaging patterns |
| Opt-out/override reasons | Ad-hoc; not comparable | Standard reason codes + traceability | Policy-as-Code + standard event records |
| Verification inputs | Mixed telemetry + AMI data; hard to align | Standard artefacts packaging AMI extracts & telemetry summaries | Verification artefact schemas |
| Baseline/M&V disputes | Method ambiguous; spreadsheets; inconsistent | Versioned M&V logic with test vectors | Policy-as-Code rulebooks + test vectors |
| Settlement computation | Spreadsheet-driven; opaque statements | Itemised settlement statements linked to data/method | Settlement artefacts + rulebooks |
| Auditability | No end-to-end evidence chain | Trace IDs + hashes linking enrolment→dispatch→verify→settle | Audit linkage + tamper-evident receipts |
| Security consistency | Uneven control/data access practices | Consistent interfaces and validation requirements | Conformance kit + validation gate |

### IES Contribution
- **Standardised Program Catalogue schema:** Common format for DISCOMs and market platforms to publish DR and flexibility programs
- **Energy Credential and consent rails:** Reusable mechanism for consumer wallet to share credentials and permissions
- **Policy-as-Code rulebooks for program execution:** Eligibility checks, opt-out rules, comfort constraints, baseline methods, settlement computations (versioned, testable)
- **Dispatch and event messaging patterns:** Standard event objects for curtail, shed, restore, notification
- **Verification and settlement artefacts:** Standard packaging of interval-meter extracts, telemetry summaries, baseline output, settlement statements
- **Audit linkage and receipts:** Non-repudiable evidence linked by trace IDs and hashes
- **Conformance kit:** Reference validator, simulator test harness, certification checklist

### Outside IES Scope
- Device firmware design/certification, home gateway design, OEM control stacks
- Tariff redesign beyond incentives and program constructs
- Market-wide ancillary services clearing and complex co-optimised dispatch
- Sub-4-second real-time frequency response

---

## Stakeholders

| Stakeholder | Role | What they provide | What they get | Impact |
|---|---|---|---|---|
| **Consumer (household / MSME)** | Program participant and consent holder | Wallet-held credential proof, device enrolment approvals, comfort preferences | Incentives/savings, transparent event history, verified performance statement | Higher trust and agency |
| **DISCOM (DR program owner + DRMS operator)** | Publisher, dispatcher, verifier of record | Program catalogue, eligibility rules, event scheduling/targeting | Dispatchable peak reduction, verifiable outcomes, reduced admin cost | Dependable peak management |
| **Consumer app / Aggregator** | Orchestrator and service provider | Consumer UX, consent capture, device-control integration, event execution | Scalable operations across DISCOMs, track record | Lower integration friction, faster scaling |
| **AMI/MDMS** | Meter-data verification provider | Interval reads, quality flags, standard extracts | Standard interface for verification requests | Faster verification cycles |
| **DER OEM / Home automation providers** | Control and capability providers | Capability descriptors, secure control endpoints, telemetry summaries | Program participation via interoperable specs | Larger addressable market |
| **Billing / Payments** | Credit or payout execution | Bill credit posting or payout references | Reduced payout friction | Faster benefit realisation |
| **Regulator / State program owner** | Oversight and method approval | Baseline method approval, consumer protection requirements | Evidence base for review | Clearer oversight |

---

## Key Performance Indicators

- **Enrolment conversion rate:** Eligible consumers who complete enrolment within 10 minutes end-to-end
- **Event participation rate:** Enrolled devices that respond to dispatch (acknowledged and executed)
- **Verified load reduction:** kWh and kW reduction during event window using AMI interval data and approved baselines
- **Dispatch-to-verification latency:** Time from event end to verified results
- **Settlement cycle time:** Time from verification to payout/bill credit
- **Opt-out and override rate:** Share of events opted out/overridden with standard reason codes
- **Dispute rate:** Disputes per 1,000 participants and time to resolve with evidence bundle

---

## Data Models and Standards

### Core Entities
- **FlexProgram:** Program catalogue entry with eligibility, incentives, baseline method, opt-out rules
- **Enrolment:** Consumer + device + program linkage with consent
- **Device Capability:** Control bounds, comfort constraints, restore behavior
- **Dispatch Event:** Event notification with times, actions, rulebooks
- **Participation Record:** Event execution status, opt-outs, overrides, telemetry summary
- **Verification Result:** Baseline output, verified reduction, evidence refs
- **Settlement Statement:** Consumer-level incentive calculation with method and data refs
- **Energy Credential:** Verifiable consumer–connection–meter linkage

### Standards Referenced
- Device control: OpenADR, IEEE 2030.5 (SEP 2.0)
- Baseline methodologies: IPMVP-compatible versioned rulebooks
- Consent management: DPDP Act 2023 compliant
- Audit trail: Cryptographic receipts with trace IDs

