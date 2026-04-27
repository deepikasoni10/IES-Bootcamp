/**
 * Component 10: JSON Schema Validator
 * Validates payloads against IES JSON schemas using AJV.
 */
import Ajv from 'ajv';
import addFormats from 'ajv-formats';

const ajv = new Ajv({ allErrors: true, coerceTypes: false });
addFormats(ajv);

// ── IES Inline Schemas (until official .json files are available from GitHub) ──

const DatasetPayloadSchema = {
  $schema: 'http://json-schema.org/draft-07/schema#',
  $id: 'ies:DatasetPayload:ARR:v1.0',
  type: 'object',
  required: ['@context', '@type', 'financial_year', 'filing_category', 'discom_id', 'data'],
  properties: {
    '@context':        { type: 'string' },
    '@type':           { type: 'string', enum: ['ARRPetition'] },
    financial_year:    { type: 'string', pattern: '^\\d{4}-\\d{2}$' },
    filing_category:   { type: 'string' },
    discom_id:         { type: 'string' },
    data: {
      type: 'object',
      required: ['revenue_requirement', 'cost_of_supply', 'demand_forecast', 'capital_expenditure'],
      properties: {
        revenue_requirement: {
          type: 'object',
          required: ['total_revenue_rs_crore'],
          properties: {
            total_revenue_rs_crore:          { type: 'number' },
            power_purchase_cost_rs_crore:    { type: 'number' },
            om_expenses_rs_crore:            { type: 'number' },
            depreciation_rs_crore:           { type: 'number' },
            interest_on_loans_rs_crore:      { type: 'number' },
            return_on_equity_rs_crore:       { type: 'number' },
          },
        },
        cost_of_supply: {
          type: 'object',
          required: ['cost_per_unit_rs'],
          properties: {
            cost_per_unit_rs:                { type: 'number' },
            at_losses_percent:               { type: 'number', minimum: 0, maximum: 100 },
            distribution_losses_percent:     { type: 'number', minimum: 0, maximum: 100 },
          },
        },
        demand_forecast: {
          type: 'object',
          required: ['peak_demand_mw'],
          properties: {
            peak_demand_mw:       { type: 'number', minimum: 0 },
            energy_requirement_mu:{ type: 'number', minimum: 0 },
            connected_load_mw:    { type: 'number', minimum: 0 },
            consumer_count:       { type: 'number', minimum: 0 },
          },
        },
        capital_expenditure: {
          type: 'object',
          required: ['total_capex_rs_crore'],
          properties: {
            total_capex_rs_crore:             { type: 'number' },
            distribution_network_rs_crore:    { type: 'number' },
            metering_rs_crore:                { type: 'number' },
            it_systems_rs_crore:              { type: 'number' },
          },
        },
      },
    },
  },
};

const CommonEnvelopeSchema = {
  $schema: 'http://json-schema.org/draft-07/schema#',
  $id: 'ies:CommonEnvelope:v1.0',
  type: 'object',
  required: ['schema_version', 'content_hash', 'issuer_id', 'created_at'],
  properties: {
    schema_version: { type: 'string' },
    content_type:   { type: 'string' },
    content_hash:   { type: 'string', pattern: '^sha256:[0-9a-f]{64}$' },
    issuer_id:      { type: 'string' },
    created_at:     { type: 'string', format: 'date-time' },
    provenance:     { type: 'object' },
    content:        { type: 'object' },
  },
};

const ReceiptSchema = {
  $schema: 'http://json-schema.org/draft-07/schema#',
  $id: 'ies:Receipt:v1.0',
  type: 'object',
  required: ['@context', '@type', 'filing_id', 'status', 'issuer', 'accepted_payload_hash', 'issued_at', 'proof'],
  properties: {
    '@context':             { type: 'string' },
    '@type':                { type: 'string' },
    filing_id:              { type: 'string' },
    status:                 { type: 'string', enum: ['accepted', 'rejected', 'observations'] },
    issuer:                 { type: 'object', required: ['id', 'name'] },
    accepted_payload_hash:  { type: 'string' },
    issued_at:              { type: 'string', format: 'date-time' },
    observations:           { type: 'array' },
    disclosure_catalog_url: { type: 'string' },
    proof:                  { type: 'object', required: ['type', 'verificationMethod', 'proofValue'] },
  },
};

// Compile schemas
const validatePayload  = ajv.compile(DatasetPayloadSchema);
const validateEnvelope = ajv.compile(CommonEnvelopeSchema);
const validateReceipt  = ajv.compile(ReceiptSchema);

/**
 * Validate a DatasetPayload against IES schema
 * @returns {{ valid: boolean, errors: array, checks: object }}
 */
export function validateDatasetPayload(payload) {
  const valid  = validatePayload(payload);
  const errors = validatePayload.errors || [];

  // Build granular check results
  const checks = {
    context_present:      !!(payload?.['@context']),
    type_correct:         payload?.['@type'] === 'ARRPetition',
    financial_year_valid: /^\d{4}-\d{2}$/.test(payload?.financial_year || ''),
    revenue_fields:       !!(payload?.data?.revenue_requirement?.total_revenue_rs_crore),
    cost_fields:          !!(payload?.data?.cost_of_supply?.cost_per_unit_rs),
    demand_fields:        !!(payload?.data?.demand_forecast?.peak_demand_mw),
    capex_fields:         !!(payload?.data?.capital_expenditure?.total_capex_rs_crore),
    all_required_present: valid || errors.filter(e => e.keyword === 'required').length === 0,
  };

  return { valid, errors, checks };
}

/**
 * Validate a CommonEnvelope
 */
export function validateEnvelopeObj(envelope) {
  const valid  = validateEnvelope(envelope);
  const errors = validateEnvelope.errors || [];
  return { valid, errors };
}

/**
 * Validate a Receipt from SERC
 */
export function validateReceiptObj(receipt) {
  const valid  = validateReceipt(receipt);
  const errors = validateReceipt.errors || [];
  return { valid, errors };
}
