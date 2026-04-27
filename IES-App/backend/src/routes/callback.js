/**
 * Component 8: Async Callback Server
 * Receives on_search / on_init / on_confirm / on_status from SERC (BPP).
 * In real ONIX mode, these arrive as HTTP POST from the Beckn gateway.
 * In mock mode, events are fired directly on callbackBus (no HTTP needed).
 */
import express      from 'express';
import { callbackBus } from '../store/callbackBus.js';
import { store }    from '../store/filingStore.js';
import { processReceipt } from '../services/receiptProcessor.js';
import { transition, STATES } from '../services/stateMachine.js';

const router = express.Router();

function ack(res)     { res.status(200).json({ message: { ack: { status: 'ACK' } } }); }
function txnFrom(req) { return req.body?.context?.transaction_id; }

/** POST /callback/on_search */
router.post('/on_search', (req, res) => {
  const txnId = txnFrom(req);
  ack(res);
  if (txnId) callbackBus.emit('on_search', txnId, req.body);
});

/** POST /callback/on_init — ValidationReport */
router.post('/on_init', (req, res) => {
  const txnId  = txnFrom(req);
  const report = req.body?.message?.validation_report;

  ack(res);
  if (!txnId) return;

  callbackBus.emit('on_init', txnId, req.body);

  // Update store (real ONIX mode — mock mode handles via becknClient)
  try {
    const filing = store.getByTxn(txnId);
    if (filing && filing.status === STATES.DRAFT_SUBMITTED) {
      const updated = transition(filing, STATES.DRAFT_VALIDATED, { trigger: 'on_init_http' });
      store.update(txnId, { ...updated, validationReport: report });
    }
  } catch (e) { console.warn('[callback/on_init] state error:', e.message); }
});

/** POST /callback/on_confirm — Signed Receipt */
router.post('/on_confirm', (req, res) => {
  const txnId   = txnFrom(req);
  const receipt = req.body?.message?.receipt;

  ack(res);
  if (!txnId) return;

  callbackBus.emit('on_confirm', txnId, req.body);

  try {
    const filing = store.getByTxn(txnId);
    if (filing && filing.status === STATES.FORMALLY_SUBMITTED && receipt) {
      const processed = processReceipt(receipt, filing.payloadHash);
      const nextState = receipt.status === 'accepted' ? STATES.ACCEPTED : STATES.REJECTED;
      const updated   = transition(filing, nextState, { trigger: 'on_confirm_http' });
      store.update(txnId, {
        ...updated,
        receipt:       processed.receipt,
        filingId:      receipt.filing_id,
        disclosureUrl: receipt.disclosure_catalog_url || null,
      });
    }
  } catch (e) { console.warn('[callback/on_confirm] state error:', e.message); }
});

/** POST /callback/on_status — Disclosure info */
router.post('/on_status', (req, res) => {
  const txnId = txnFrom(req);
  ack(res);
  if (!txnId) return;

  callbackBus.emit('on_status', txnId, req.body);

  try {
    const filing = store.getByTxn(txnId);
    const disclosure = req.body?.message?.disclosure;
    if (filing && filing.status === STATES.ACCEPTED && disclosure) {
      const updated = transition(filing, STATES.DISCLOSED, { trigger: 'on_status_http' });
      store.update(txnId, { ...updated, disclosureUrl: disclosure.catalog_url });
    }
  } catch (e) { console.warn('[callback/on_status] state error:', e.message); }
});

export default router;
