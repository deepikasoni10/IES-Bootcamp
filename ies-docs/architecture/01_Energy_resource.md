# Energy Resource

## Overview

An Energy Resource is any physical, virtual or logical entity within the energy ecosystem that participates in energy generation, storage, consumption, transmission, distribution, or service delivery.

## Key Points

- **Types**: Generation assets (solar panels, wind turbines), storage systems (batteries), consumption devices (EVs, appliances), infrastructure (transformers, meters), service providers and more
- **Characteristics**: Identified by ERAs, carry credentials, have capacity/performance attributes, location context, and operational constraints

## Draft examples (not to be interpreted as final schema)

**EV Charging Station (EVSE)**
- Identity: EVSE ID, connector type
- Capacity: 60kW max power
- Location: GPS coordinates, address
- Attributes: Connector type (CCS2), availability status

**Prosumer Household**
- Generation: 5kW solar array
- Storage: 10kWh battery
- Role: Consumer (morning/evening), Provider (afternoon export)

## Learn More

For more information, see [Energy Resource - DEG Architecture](https://github.com/Beckn-One/DEG/blob/main/architecture/Energy%20resource.md).
