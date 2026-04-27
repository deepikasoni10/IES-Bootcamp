/**
 * Filing Routes — orchestrates all 10 components
 *
 * POST /api/filings/upload           → parse CSV/Excel
 * GET  /api/filings/upload/:id/preview
 * POST /api/filings/map              → DatasetPayload from mapping
 * POST /api/filings/hash             → SHA-256 hash
 * POST /api/filings/validate         → IES schema validation
 * POST /api/filings/search           → Beckn /search
 * POST /api/filings/init             → Beckn /init (draft)
 * POST /api/filings/confirm          → Beckn /confirm (formal)
 * GET  /api/filings/:txnId/status    → Beckn /status
 * GET  /api/filings                  → list all
 * GET  /api/filings/:txnId           → get one
 */
import express            from 'express';
import multer             from 'multer';
import { randomUUID }     from 'crypto';
import { join, dirname }  from 'path';
import { fileURLToPath }  from 'url';
import { mkdirSync }      from 'fs';

import { parseFile, getPreview }           from '../services/fileParser.js';
import { mapToDatasetPayload, getMappingStatus } from '../services/schemaMapper.js';
import { computeHash, verifyHash }         from '../services/hasher.js';
import { validateDatasetPayload }          from '../services/validator.js';
import { buildEnvelope, buildDraftFiling, buildFormalFiling } from '../services/envelopeBuilder.js';
import { buildSearch, buildInit, buildConfirm, buildStatus }  from '../services/becknMessageBuilder.js';
import { executeBecknAction }              from '../services/becknClient.js';
import { getVerifiableCredential, signPayload } from '../services/credentialService.js';
import { processReceipt }                  from '../services/receiptProcessor.js';
import { STATES, transition }             from '../services/stateMachine.js';
import { store }                           from '../store/filingStore.js';
import { callbackBus }                     from '../store/callbackBus.js';
import { config }                          from '../config/index.js';

const router = express.Router();
const __dir  = dirname(fileURLToPath(import.meta.url));
const UPLOAD_DIR = join(__dir, '../../uploads');
mkdirSync(UPLOAD_DIR, { recursive: true });

// Multer config
const upload = multer({
  dest: UPLOAD_DIR,
  limits: { fileSize: 50 * 1024 * 1024 }, // 50 MB
  fileFilter: (req, file, cb) => {
    const allowed = ['text/csv', 'application/vnd.ms-excel',
      'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'];
    if (allowed.includes(file.mimetype) ||
        file.originalname.match(/\.(csv|xls|xlsx)$/i)) {
      cb(null, true);
    } else {
      cb(new Error('Only CSV and Excel files are accepted'));
    }
  },
});

// ── Helper ─────────────────────────────────────────────────────────────
function ok(res, data, status = 200) {
  return res.status(status).json({ success: true, ...data });
}

// ══════════════════════════════════════════════════════════════════════
// COMPONENT 1: Upload & Parse
// ══════════════════════════════════════════════════════════════════════
router.post('/upload', upload.single('file'), async (req, res) => {
  if (!req.file) throw Object.assign(new Error('No file uploaded'), { status: 400 });

  const uploadId   = randomUUID();
  const parsedData = await parseFile(req.file.path, req.file.originalname);
  const preview    = getPreview(parsedData);

  store.saveUpload(uploadId, {
    path:         req.file.path,
    originalName: req.file.originalname,
    parsedData,
  });

  return ok(res, { uploadId, preview, columns: parsedData.columns }, 201);
});

router.get('/upload/:uploadId/preview', (req, res) => {
  const up = store.getUpload(req.params.uploadId);
  if (!up) throw Object.assign(new Error('Upload not found'), { status: 404 });
  return ok(res, { preview: getPreview(up.parsedData), columns: up.parsedData.columns });
});

// ══════════════════════════════════════════════════════════════════════
// COMPONENT 2: Schema Mapping → DatasetPayload
// ══════════════════════════════════════════════════════════════════════
router.post('/map', (req, res) => {
  const { uploadId, discomId, financialYear, mappingConfig } = req.body;
  if (!uploadId || !financialYear) {
    throw Object.assign(new Error('uploadId and financialYear are required'), { status: 400 });
  }

  const up = store.getUpload(uploadId);
  if (!up) throw Object.assign(new Error('Upload not found — re-upload the file'), { status: 404 });

  const datasetPayload  = mapToDatasetPayload(up.parsedData, discomId || config.credential.discomId, financialYear, mappingConfig);
  const mappingStatus   = getMappingStatus(up.parsedData.columns, mappingConfig);
  const mappedCount     = mappingStatus.filter(m => m.mapped).length;

  return ok(res, { datasetPayload, mappingStatus, mappedCount, totalColumns: up.parsedData.columns.length });
});

// ══════════════════════════════════════════════════════════════════════
// COMPONENT 3: Hash Computation
// ══════════════════════════════════════════════════════════════════════
router.post('/hash', (req, res) => {
  const { datasetPayload } = req.body;
  if (!datasetPayload) throw Object.assign(new Error('datasetPayload is required'), { status: 400 });

  const payloadHash = computeHash(datasetPayload);
  return ok(res, { payloadHash, algorithm: 'sha256', canonicalization: 'sorted-keys-no-whitespace' });
});

// ══════════════════════════════════════════════════════════════════════
// COMPONENT 10: Schema Validation
// ══════════════════════════════════════════════════════════════════════
router.post('/validate', (req, res) => {
  const { datasetPayload } = req.body;
  if (!datasetPayload) throw Object.assign(new Error('datasetPayload is required'), { status: 400 });

  const result = validateDatasetPayload(datasetPayload);
  return ok(res, { ...result, passedAll: result.valid });
});

// ══════════════════════════════════════════════════════════════════════
// Beckn /search — discover SERC endpoint
// ══════════════════════════════════════════════════════════════════════
router.post('/search', async (req, res) => {
  const txnId      = randomUUID();
  const becknMsg   = buildSearch(txnId);
  const ack        = await executeBecknAction(becknMsg);

  // Wait for on_search (mock bus or incoming HTTP)
  const catalog = await waitForCallback('on_search', txnId, 5000).catch(() => null);

  return ok(res, { txnId, ack, catalog: catalog?.message?.catalog || null });
});

// ══════════════════════════════════════════════════════════════════════
// COMPONENT 5 + 7: Beckn /init — draft validation
// ══════════════════════════════════════════════════════════════════════
router.post('/init', async (req, res) => {
  const { datasetPayload, payloadHash, discomId, financialYear, uploadId } = req.body;
  if (!datasetPayload || !payloadHash) {
    throw Object.assign(new Error('datasetPayload and payloadHash are required'), { status: 400 });
  }

  // Verify hash is correct
  if (!verifyHash(datasetPayload, payloadHash)) {
    throw Object.assign(new Error('Payload hash mismatch — recompute hash before submitting'), { status: 400 });
  }

  const txnId  = randomUUID();
  const filing = buildDraftFiling({ datasetPayload, payloadHash, discomId, txnId });

  // Create filing record in store
  let filingRecord = {
    txnId,
    status:       STATES.PREPARING,
    discomId:     discomId || config.credential.discomId,
    financialYear,
    datasetPayload,
    payloadHash,
    createdAt:    new Date().toISOString(),
    history:      [],
    validationReport: null,
    receipt:          null,
    filingId:         null,
  };

  filingRecord = transition(filingRecord, STATES.DRAFT_SUBMITTED, { trigger: '/init' });
  store.save(filingRecord);

  // Build and send Beckn message to ONIX
  const becknMsg  = buildInit(txnId, filing);
  const ack       = await executeBecknAction(becknMsg);

  // Wait for async on_init callback (with timeout)
  const onInitPayload = await waitForCallback('on_init', txnId, config.mock.draftDelayMs + 2000);
  const report        = onInitPayload?.message?.validation_report;

  if (report) {
    filingRecord = transition(store.getByTxn(txnId), STATES.DRAFT_VALIDATED, { trigger: 'on_init' });
    store.update(txnId, { ...filingRecord, validationReport: report });
  }

  return ok(res, {
    txnId,
    ack,
    status:           store.getByTxn(txnId)?.status,
    validationReport: report || null,
    message: report ? 'Draft validated — proceed to formal filing' : 'Awaiting async validation report',
  });
});

// ══════════════════════════════════════════════════════════════════════
// COMPONENT 6 + 8: Beckn /confirm — formal filing
// ══════════════════════════════════════════════════════════════════════
router.post('/confirm', async (req, res) => {
  const { txnId, datasetPayload, payloadHash, discomId } = req.body;
  if (!txnId || !datasetPayload || !payloadHash) {
    throw Object.assign(new Error('txnId, datasetPayload and payloadHash are required'), { status: 400 });
  }

  let filingRecord = store.getByTxn(txnId);
  if (!filingRecord) throw Object.assign(new Error('Filing not found for txnId'), { status: 404 });

  // Fetch Verifiable Credential
  const credential = await getVerifiableCredential(discomId || config.credential.discomId);

  // Sign payload hash
  const signature  = signPayload(payloadHash, config.credential.discomDid);

  // Build formal filing object
  const formalFiling = buildFormalFiling({
    datasetPayload,
    payloadHash,
    discomId: discomId || config.credential.discomId,
    credential,
    signature,
    txnId,
    draftMsgId:      `msg-oninit-${txnId}`,
    draftValidatedAt: filingRecord.draftValidatedAt,
  });

  // Transition state
  filingRecord = transition(filingRecord, STATES.FORMALLY_SUBMITTED, { trigger: '/confirm' });
  store.update(txnId, filingRecord);

  // Send to ONIX
  const becknMsg = buildConfirm(txnId, formalFiling);
  const ack      = await executeBecknAction(becknMsg);

  // Wait for async on_confirm
  const onConfirmPayload = await waitForCallback('on_confirm', txnId, config.mock.formalDelayMs + 2000);
  const receipt          = onConfirmPayload?.message?.receipt;

  if (receipt) {
    // Process and verify receipt
    const processed = processReceipt(receipt, payloadHash);
    const nextState = receipt.status === 'accepted' ? STATES.ACCEPTED : STATES.REJECTED;

    filingRecord = transition(store.getByTxn(txnId), nextState, { trigger: 'on_confirm', filingId: receipt.filing_id });
    store.update(txnId, {
      ...filingRecord,
      receipt:         processed.receipt,
      filingId:        receipt.filing_id,
      disclosureUrl:   receipt.disclosure_catalog_url || null,
      receiptVerified: processed.valid,
    });
  }

  return ok(res, {
    txnId,
    ack,
    status:   store.getByTxn(txnId)?.status,
    receipt:  receipt || null,
    filingId: receipt?.filing_id || null,
    message:  receipt?.status === 'accepted'
      ? 'Filing accepted by SERC — receipt issued'
      : receipt?.status === 'rejected'
      ? 'Filing rejected by SERC — see receipt for observations'
      : 'Awaiting async receipt',
  });
});

// ══════════════════════════════════════════════════════════════════════
// Beckn /status
// ══════════════════════════════════════════════════════════════════════
router.get('/:txnId/status', async (req, res) => {
  const { txnId } = req.params;
  const filingRecord = store.getByTxn(txnId);
  if (!filingRecord) throw Object.assign(new Error('Filing not found'), { status: 404 });

  const becknMsg  = buildStatus(txnId, filingRecord.filingId);
  const ack       = await executeBecknAction(becknMsg);
  const onStatus  = await waitForCallback('on_status', txnId, 5000).catch(() => null);

  if (onStatus?.message?.filing_status === 'disclosed' && filingRecord.status === STATES.ACCEPTED) {
    const updated = transition(store.getByTxn(txnId), STATES.DISCLOSED, { trigger: 'on_status' });
    store.update(txnId, { ...updated, disclosureUrl: onStatus.message.disclosure?.catalog_url });
  }

  return ok(res, {
    txnId,
    status:      store.getByTxn(txnId)?.status,
    filingId:    filingRecord.filingId,
    disclosure:  onStatus?.message?.disclosure || null,
    filing:      store.getByTxn(txnId),
  });
});

// ══════════════════════════════════════════════════════════════════════
// CRUD
// ══════════════════════════════════════════════════════════════════════
router.get('/', (req, res) => {
  const { status, financialYear } = req.query;
  let filings = store.getAll();
  if (status)        filings = filings.filter(f => f.status === status);
  if (financialYear) filings = filings.filter(f => f.financialYear === financialYear);
  return ok(res, { filings, count: filings.length });
});

router.get('/:txnId', (req, res) => {
  const filing = store.getByTxn(req.params.txnId)
               || store.getByFilingId(req.params.txnId);
  if (!filing) throw Object.assign(new Error('Filing not found'), { status: 404 });
  return ok(res, { filing });
});

// ── Utility: wait for a Beckn callback event ──────────────────────────
function waitForCallback(event, txnId, timeoutMs = 5000) {
  return new Promise((resolve, reject) => {
    const timer = setTimeout(() => {
      callbackBus.off(event, handler);
      reject(new Error(`Timeout waiting for ${event} (txnId: ${txnId})`));
    }, timeoutMs);

    function handler(incomingTxnId, payload) {
      if (incomingTxnId === txnId) {
        clearTimeout(timer);
        callbackBus.off(event, handler);
        resolve(payload);
      }
    }
    callbackBus.on(event, handler);
  });
}

export default router;
