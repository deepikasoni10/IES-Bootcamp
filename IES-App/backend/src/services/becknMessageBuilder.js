/**
 * Component 5: Beckn Message Builder
 * Constructs well-formed Beckn protocol messages (context + message).
 * Handles UUID generation, timestamps, BAP/BPP identifiers.
 */
import { randomUUID } from 'crypto';
import { config } from '../config/index.js';

/**
 * Build the Beckn context block.
 * transaction_id is stable across the whole lifecycle.
 * message_id is unique per individual request.
 */
export function buildContext(action, txnId = null) {
  return {
    domain:         config.beckn.domain,
    action,
    version:        config.beckn.version,
    bap_id:         config.beckn.bapId,
    bap_uri:        config.beckn.bapUri,
    bpp_id:         config.beckn.bppId,
    bpp_uri:        config.beckn.bppUri,
    transaction_id: txnId    || randomUUID(),
    message_id:     randomUUID(),
    timestamp:      new Date().toISOString(),
  };
}

/** /search */
export function buildSearch(txnId) {
  return {
    context: buildContext('search', txnId),
    message: {
      intent: {
        category:     'regulatory_filing',
        type:         'ARR_petition',
        jurisdiction: 'state_electricity_regulatory_commission',
      },
    },
  };
}

/** /init — draft validation */
export function buildInit(txnId, filing) {
  return {
    context: buildContext('init', txnId),
    message: { filing },
  };
}

/** /confirm — formal submission */
export function buildConfirm(txnId, filing) {
  return {
    context: buildContext('confirm', txnId),
    message: { filing },
  };
}

/** /status */
export function buildStatus(txnId, filingId) {
  return {
    context: buildContext('status', txnId),
    message: { filing_id: filingId },
  };
}

/** Generic response message builder (for on_* callbacks sent back to BAP by BPP) */
export function buildOnContext(action, txnId, msgId = null) {
  return {
    domain:         config.beckn.domain,
    action,
    version:        config.beckn.version,
    bap_id:         config.beckn.bapId,
    bpp_id:         config.beckn.bppId,
    transaction_id: txnId,
    message_id:     msgId || randomUUID(),
    timestamp:      new Date().toISOString(),
  };
}
