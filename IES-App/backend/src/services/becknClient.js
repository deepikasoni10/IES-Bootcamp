/**
 * Beckn ONIX Client (Component 7 — Async Callback + ONIX routing)
 *
 * Two modes:
 *   REAL MODE  — sends HTTP to actual ONIX Gateway, waits for async callback
 *   MOCK MODE  — simulates SERC processing locally, fires callback internally
 *
 * Set USE_MOCK_ONIX=false in .env to use real ONIX sandbox.
 */
import axios from 'axios';
import { config } from '../config/index.js';
import { randomUUID } from 'crypto';
import { callbackBus } from '../store/callbackBus.js';
import { buildOnContext } from './becknMessageBuilder.js';

/** HTTP ACK wrapper */
const ACK = { message: { ack: { status: 'ACK' } } };

/**
 * Send a Beckn message to the ONIX Gateway (real mode).
 * The gateway routes to BPP, which sends an async callback.
 */
async function sendToGateway(becknMessage) {
  const { action } = becknMessage.context;
  const url = `${config.beckn.gatewayUrl}/${action}`;
  try {
    const res = await axios.post(url, becknMessage, {
      headers: { 'Content-Type': 'application/json' },
      timeout: 10_000,
    });
    return res.data;
  } catch (err) {
    throw new Error(`ONIX gateway unreachable: ${err.message}`);
  }
}

// ── MOCK SERC Responses ───────────────────────────────────────────────

function mockOnSearch(txnId) {
  return {
    context: buildOnContext('on_search', txnId),
    message: {
      catalog: {
        providers: [{
          id: 'serc-maharashtra',
          descriptor: { name: 'Maharashtra Electricity Regulatory Commission' },
          items: [{
            id: 'arr-filing',
            descriptor: { name: 'ARR Petition Filing' },
            schema_ref: 'ies:DatasetPayload:ARR:v1.0',
            accepted_formats: ['ies:Filing:v1.0'],
          }],
        }],
      },
    },
  };
}

function mockOnInit(txnId, msgId, filing) {
  const hash = filing?.payload_hash || '';
  const hasDemand = filing?.dataset_payload?.data?.demand_forecast?.peak_demand_mw;
  const observations = [];

  if (hasDemand && hasDemand > 22000) {
    observations.push({
      field: 'data.demand_forecast.peak_demand_mw',
      severity: 'warning',
      message: 'Value appears to deviate significantly from prior year trend (was 22,100 MW)',
    });
  }
  observations.push({
    field: 'data.capital_expenditure.distribution_losses',
    severity: 'info',
    message: 'Consider providing sub-category breakdowns per SERC format 4B',
  });

  const allGood = observations.every(o => o.severity === 'info');

  return {
    context: buildOnContext('on_init', txnId, `msg-oninit-${msgId}`),
    message: {
      validation_report: {
        status: allGood ? 'validated' : 'validated_with_observations',
        schema_check:       'pass',
        hash_check:         hash ? 'pass' : 'fail',
        completeness_check: observations.length > 0 ? 'partial' : 'pass',
        observations,
        recommendation: observations.some(o => o.severity === 'error')
          ? 'do_not_proceed'
          : 'may_proceed_to_formal_filing',
      },
    },
  };
}

function mockOnConfirm(txnId, msgId, filing) {
  const hash = filing?.payload_hash || 'sha256:unknown';
  const filingSeqNum = String(Math.floor(Math.random() * 900) + 100).padStart(3, '0');
  const filingId = `SERC/ARR/2026-27/MH/${filingSeqNum}`;

  return {
    context: buildOnContext('on_confirm', txnId, `msg-onconfirm-${msgId}`),
    message: {
      receipt: {
        '@context': 'https://ies.energy/schemas/v1/receipt.jsonld',
        '@type':    'RegulatoryFilingReceipt',
        filing_id:  filingId,
        status:     'accepted',
        issuer: {
          id:   'mock-serc.sandbox.ies',
          name: 'Maharashtra Electricity Regulatory Commission',
        },
        accepted_payload_hash: hash,
        issued_at:             new Date().toISOString(),
        observations:          [],
        disclosure_catalog_url: `https://dedi.ies.energy/catalogs/serc-mh/disclosures/${filingId.replace(/\//g, '-').toLowerCase()}.json`,
        proof: {
          type:               'Ed25519Signature2020',
          verificationMethod: 'did:ies:mock-serc#key-1',
          proofValue:         `z${randomUUID().replace(/-/g, '')}Kx8Nm3P`,
        },
      },
    },
  };
}

function mockOnStatus(txnId, filingId) {
  return {
    context: buildOnContext('on_status', txnId),
    message: {
      filing_status: 'disclosed',
      disclosure: {
        catalog_url:  `https://dedi.ies.energy/catalogs/serc-mh/disclosures/${filingId?.replace(/\//g, '-').toLowerCase()}.json`,
        published_at: new Date().toISOString(),
        content_hash: 'sha256:a3f2b8c9d1e4f5a6b7c8d9e0f1a2b3c4d5e6f7a8b9c0d1e2f3a4b5c6d7e8f9',
      },
    },
  };
}

// ── Public API ────────────────────────────────────────────────────────

/**
 * Execute a Beckn action.
 * If mock mode: simulates SERC, fires callback after delay, returns ACK.
 * If real mode: sends to ONIX Gateway, returns gateway ACK.
 */
export async function executeBecknAction(becknMessage) {
  const { action, transaction_id: txnId, message_id: msgId } = becknMessage.context;
  const filing = becknMessage.message?.filing;
  const filingId = becknMessage.message?.filing_id;

  if (config.beckn.useMockOnix) {
    // Fire async callback after realistic delay
    const delay = action === 'init' ? config.mock.draftDelayMs : config.mock.formalDelayMs;

    setTimeout(() => {
      let callbackPayload;
      switch (action) {
        case 'search':  callbackPayload = mockOnSearch(txnId);                break;
        case 'init':    callbackPayload = mockOnInit(txnId, msgId, filing);   break;
        case 'confirm': callbackPayload = mockOnConfirm(txnId, msgId, filing);break;
        case 'status':  callbackPayload = mockOnStatus(txnId, filingId);      break;
        default:        return;
      }
      // Emit to in-process callback bus (skips HTTP round-trip in mock mode)
      callbackBus.emit(`on_${action}`, txnId, callbackPayload);
    }, delay);

    return ACK;
  }

  // Real ONIX Gateway
  return sendToGateway(becknMessage);
}
