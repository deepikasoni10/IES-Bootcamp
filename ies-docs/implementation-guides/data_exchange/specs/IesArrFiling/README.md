# IES ARR Filing Schema

Schema definitions for **Aggregate Revenue Requirement (ARR)** filings by distribution licensees to State Electricity Regulatory Commissions (SERCs).

## Files

| File | Description |
|------|-------------|
| `context.jsonld` | JSON-LD context mapping ARR terms to IES namespace URIs |
| `attributes.yaml` | OpenAPI 3.1.0 schema definitions (IES_ARR_Filing, IES_ARR_FiscalYear, IES_ARR_LineItem) |
| `IES_ARR_Filing.schema.json` | Self-contained JSON Schema for filing-level validation |
| `IES_ARR_FiscalYear.schema.json` | Self-contained JSON Schema for fiscal year validation |
| `IES_ARR_LineItem.schema.json` | Self-contained JSON Schema for line item validation |

## Schema Overview

An ARR filing is structured as:

```
IES_ARR_Filing
  ├── metadata (licensee, regulator, state, currency, etc.)
  └── fiscalYears[]
        ├── fiscalYear: "FY 2025-26"
        ├── yearType: BASE_YEAR | CONTROL_PERIOD | HISTORICAL
        ├── amountBasis: AUDITED | APPROVED | PROPOSED | TRUED_UP | NOT_FILED
        └── lineItems[]
              ├── lineItemId (stable kebab-case ID)
              ├── category: VARIABLE | FIXED | INCOME | SUB_TOTAL | ARR | ADJUSTMENT
              ├── subCategory: POWER_PURCHASE | NETWORK_COST | O_AND_M | ...
              ├── head (display name)
              ├── amount (INR crore, null if not applicable)
              ├── formula (lineItemId-based computation)
              └── componentOf (parent subtotal lineItemId)
```

## Supported Filing Formats

- **MYT (Multi-Year Tariff)**: Wide-format control period filings with base year + projected years
- **Annual**: Year-by-year historical data with SERC-approved amounts
- **True-up**: Reconciliation of actuals vs approved
- **Revised**: Amended filings with corrections

## Examples

- `../../examples/arr_filing_myt_example.jsonld` — MYT control period filing (6 fiscal years)
- `../../examples/arr_filing_annual_example.jsonld` — Annual historical filing (3 representative fiscal years)
- `../../bootcamp/arr_filings.jsonld` — Complete bootcamp dataset (2 DISCOMs, 19 fiscal years, 245 line items)
