# India Energy Stack - Architecture

The India Energy Stack (IES) is built on a decentralized, open architecture that enables seamless interactions between diverse energy stakeholders - from individual consumers and distributed energy resources (DERs) to utilities, aggregators, and service providers.

## Core Primitives

The IES architecture has identified eight fundamental primitives (non-exhaustive) that together enable trustworthy, efficient energy transactions:

### 1. [Energy Resource](./01_Energy_Resource.md)
Physical or logical entities in the energy ecosystem - including generation assets (solar panels, wind turbines), storage systems (batteries), consumption devices (EVs, appliances), infrastructure (transformers, meters), and service providers. Energy resources can act as consumers, providers, or both (prosumers). [Full documentation →](https://github.com/Beckn-One/DEG/blob/main/architecture/Energy%20resource.md)

### 2. [Energy Resource Address (ERA)](./02_Energy_Resource_Address.md)
Globally or locally unique digital identifiers assigned to energy resources, enabling seamless addressability and discovery. ERAs function like internet domain names, allowing systems to uniformly recognize and interact with energy resources across platforms. [Full documentation →](https://github.com/Beckn-One/DEG/blob/main/architecture/Energy%20resource%20address.md)

### 3. [Energy Credentials](./03_Energy_Credentials.md)
Digital attestations tied to Energy Resource Addresses that provide verifiable claims about resources - such as green energy certification, ownership status, maintenance logs, subsidy eligibility, and transaction history. Built on W3C Verifiable Credentials standard for cryptographic security and privacy preservation. [Full documentation →](https://github.com/Beckn-One/DEG/blob/main/architecture/Energy%20credentials.md)

### 4. [Energy Registries](./04_Energy_Registries.md)
Authoritative, machine-readable repositories holding critical information that serves as the root of trust - including lists of certified manufacturers, approved operators, public keys of participating entities, revoked licenses, registered ERAs, grid interconnection approvals, subsidy eligibility lists, and tariff schedules - accessible through standardized, cryptographically verifiable APIs.

### 5. [Energy Intent](./05_Energy_Intent.md)
Digital representation of energy demand or requirements, detailing what is needed, preferred conditions, constraints, and acceptable terms. Intents express the "ask" side of transactions - from simple needs ("charge my EV") to complex requirements ("20 kWh solar energy between 6-9 PM at ₹7/kWh or less"). [Full documentation →](https://github.com/Beckn-One/DEG/blob/main/architecture/Energy%20intent.md)

### 6. [Energy Catalogue](./06_Energy_Catalogue.md)
Structured listings of available energy resources, services, or offerings - including quantities, locations, timing, pricing, constraints, and delivery methods. Catalogues represent the "offer" side of transactions, published by providers to match against consumer intents. [Full documentation →](https://github.com/Beckn-One/DEG/blob/main/architecture/Energy%20catalogue.md)

### 7. [Energy Contract](./07_Energy_Contract.md)
Formalized agreement that emerges when an energy intent successfully matches with a catalogue offering. Contracts define the boundaries of interactions between parties, encompassing everything from simple acknowledgments to complex multi-party agreements. [Full documentation →](https://github.com/Beckn-One/DEG/blob/main/architecture/Energy%20contract.md)

### 8. [Energy Policy as Code](./08_Energy_Policy_as_Code.md)
Machine-readable representations of policies, rules, and constraints that govern energy transactions and system operations. Policies can include demand response program rules, dynamic pricing policies, grid interconnection requirements, geographic constraints, and fee calculations that systems can automatically validate and apply.

## How the Primitives Work Together

```
         Energy Resources
                ↓
        Assigned ERAs
                ↓
        Carry Credentials ←→ Registries (verify)
           ↙         ↘
    Express         Publish
    Intents         Catalogues
       ↓                ↓
       └────(Match)─────┘
                ↓
       (Validate against Policies)
                ↓
         Energy Contract
                ↓
         Contract Execution
```


## Implementation Examples

For detailed implementation guides and examples, see the [DEG Implementation Guides](https://github.com/Beckn-One/DEG/tree/main/docs/implementation-guides/v2):

- [EV Charging Implementation Guide](https://github.com/Beckn-One/DEG/blob/main/docs/implementation-guides/v2/EV_Charging_V0.8-draft.md)
- [P2P Energy Trading Implementation Guide](https://github.com/Beckn-One/DEG/blob/main/docs/implementation-guides/v2/P2P_Energy_Trading_V1.0-draft.md) (draft)

## Learn More

For comprehensive documentation on each primitive, visit the [DEG Architecture Documentation](https://github.com/Beckn-One/DEG/tree/main/architecture).
