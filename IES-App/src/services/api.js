/**
 * Frontend API client — all calls to the IES backend (localhost:4000)
 */

const BASE = 'http://localhost:4000/api';

async function request(method, path, body = null, isFormData = false) {
  const opts = {
    method,
    headers: isFormData ? {} : { 'Content-Type': 'application/json' },
  };
  if (body) opts.body = isFormData ? body : JSON.stringify(body);
  const res  = await fetch(`${BASE}${path}`, opts);
  const data = await res.json();
  if (!res.ok) throw new Error(data.error || `HTTP ${res.status}`);
  return data;
}

const get  = (path)         => request('GET',  path);
const post = (path, body, fd) => request('POST', path, body, fd);

// ── Upload ──────────────────────────────────────────────────────────────
export async function uploadFile(file) {
  const form = new FormData();
  form.append('file', file);
  return post('/filings/upload', form, true);
}

// ── Map (DatasetPayload) ────────────────────────────────────────────────
export function mapPayload({ uploadId, discomId, financialYear }) {
  return post('/filings/map', { uploadId, discomId, financialYear });
}

// ── Hash ────────────────────────────────────────────────────────────────
export function hashPayload(datasetPayload) {
  return post('/filings/hash', { datasetPayload });
}

// ── Validate ────────────────────────────────────────────────────────────
export function validatePayload(datasetPayload) {
  return post('/filings/validate', { datasetPayload });
}

// ── Beckn /init (draft) ─────────────────────────────────────────────────
export function submitDraft({ datasetPayload, payloadHash, discomId, financialYear }) {
  return post('/filings/init', { datasetPayload, payloadHash, discomId, financialYear });
}

// ── Beckn /confirm (formal) ─────────────────────────────────────────────
export function submitFormal({ txnId, datasetPayload, payloadHash, discomId }) {
  return post('/filings/confirm', { txnId, datasetPayload, payloadHash, discomId });
}

// ── Status ──────────────────────────────────────────────────────────────
export function getFilingStatus(txnId) {
  return get(`/filings/${txnId}/status`);
}

// ── CRUD ────────────────────────────────────────────────────────────────
export function listFilings(params = {}) {
  const q = new URLSearchParams(params).toString();
  return get(`/filings${q ? '?' + q : ''}`);
}

export function getFiling(txnId) {
  return get(`/filings/${txnId}`);
}

// ── Health ───────────────────────────────────────────────────────────────
export function getHealth() {
  return fetch('http://localhost:4000/api/health').then(r => r.json());
}
