# P2P Trade Representation in Data Exchange

P2P trading represents a new paradigm in energy consumption where consumers can trade energy with each other. This is enabled by the availability of smart meters and the ability to measure and record energy consumption in real-time. The trade is entered in trading platforms that are separate from the utilities. The trade is aligned with the utilities and the committed trades must be reconciled with actual consumption and injection for the purposes of trade settlement and utility billing.

To capture energy trade commitments like Peer-to-Peer (P2P) trading within the OpenADR 3.1.0 framework, we extend the payloadType and attributes to represent the commitments as events. These can then be correlated to the actual consumption and injection data in energy reports for the purposes of trade settlement and utility billing. The settlement can be captured within the annotated energy reports itself.

## Schema Extension Details

### New Payload Types
* `TRADE_COMMITMENT_EXPORT`: Represents a volume of energy the consumer is committed to exporting (P2P).
* `TRADE_COMMITMENT_IMPORT`: Represents a volume of energy the consumer is committed to importing (P2P).

### New Attributes (Metadata)
* `TRADE_ID`: A unique identifier for the P2P transaction to link buyers and sellers.
* `P2P_PARTICIPANT_ID`: Masked ID of the trading counterparty.

The attributes can be added to events and when reconciling the actual data - they could annotate the energy reports to enable trade settlement and utility billing. The billing computation itself could be facilitated via tariff captured as policy document published by the appropriate authority in a public data exchange.

## OpenADR 3.1.0 Extended Event: P2P Trade Commitments
This event combines native PRICE and LIMIT signals with our new TRADE_COMMITMENT extensions for tomorrow.

```json
{
  "objectType": "EVENT",
  "programID": "prog-p2p-trading-2026",
  "eventName": "Tomorrow_P2P_Trade_Schedule",
  "priority": 0,
  "payloadDescriptors": [
    {
      "objectType": "EVENT_PAYLOAD_DESCRIPTOR",
      "payloadType": "PRICE",
      "units": "KWH",
      "currency": "INR"
    },
    {
      "objectType": "EVENT_PAYLOAD_DESCRIPTOR",
      "payloadType": "EXPORT_CAPACITY_LIMIT",
      "units": "KW"
    },
    {
      "objectType": "EVENT_PAYLOAD_DESCRIPTOR",
      "payloadType": "TRADE_COMMITMENT_EXPORT",
      "units": "KWH"
    },
    {
      "objectType": "EVENT_PAYLOAD_DESCRIPTOR",
      "payloadType": "TRADE_COMMITMENT_IMPORT",
      "units": "KWH"
    }
  ],
  "intervals": [
    {
      "id": 100,
      "intervalPeriod": {
        "start": "2026-04-01T14:00:00Z",
        "duration": "PT2H"
      },
      "payloads": [
        { "type": "PRICE", "values": [10.50] },
        { "type": "EXPORT_CAPACITY_LIMIT", "values": [5.0] },
        { "type": "TRADE_COMMITMENT_EXPORT", "values": [3.0] }
      ],
      "attributes": [
        { "type": "TRADE_ID", "values": ["TXN-9988-ABC"] },
        { "type": "P2P_PARTICIPANT_ID", "values": ["COUNTERPARTY_MASK_88"] }
      ]
    },
    {
      "id": 101,
      "intervalPeriod": {
        "start": "2026-04-01T16:00:00Z",
        "duration": "PT1H"
      },
      "payloads": [
        { "type": "PRICE", "values": [8.00] },
        { "type": "TRADE_COMMITMENT_IMPORT", "values": [2.0] }
      ],
      "attributes": [
        { "type": "TRADE_ID", "values": ["TXN-9989-XYZ"] }
      ]
    }
  ]
}
```
