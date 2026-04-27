/**
 * In-memory Filing Store (Map-based).
 * Key: txnId (transaction_id — stable across lifecycle)
 *
 * In production: replace with PostgreSQL (filing_id as PK, txn_id as index).
 */

class FilingStore {
  constructor() {
    this._byTxn     = new Map();  // txnId → filing
    this._byId      = new Map();  // filing_id → txnId
    this._uploads   = new Map();  // uploadId → { path, originalName, parsedData }
  }

  // ── Filings ────────────────────────────────────────────────────────

  save(filing) {
    this._byTxn.set(filing.txnId, { ...filing, updatedAt: new Date().toISOString() });
    if (filing.filingId) this._byId.set(filing.filingId, filing.txnId);
    return this.getByTxn(filing.txnId);
  }

  getByTxn(txnId) {
    return this._byTxn.get(txnId) || null;
  }

  getByFilingId(filingId) {
    const txnId = this._byId.get(filingId);
    return txnId ? this._byTxn.get(txnId) : null;
  }

  getAll() {
    return Array.from(this._byTxn.values()).sort(
      (a, b) => new Date(b.createdAt) - new Date(a.createdAt)
    );
  }

  update(txnId, patch) {
    const existing = this._byTxn.get(txnId);
    if (!existing) throw new Error(`Filing not found: txnId=${txnId}`);
    const updated = { ...existing, ...patch, updatedAt: new Date().toISOString() };
    this._byTxn.set(txnId, updated);
    if (updated.filingId) this._byId.set(updated.filingId, txnId);
    return updated;
  }

  delete(txnId) {
    const f = this._byTxn.get(txnId);
    if (f?.filingId) this._byId.delete(f.filingId);
    this._byTxn.delete(txnId);
  }

  // ── Uploaded files ─────────────────────────────────────────────────

  saveUpload(uploadId, data) {
    this._uploads.set(uploadId, data);
  }

  getUpload(uploadId) {
    return this._uploads.get(uploadId) || null;
  }

  deleteUpload(uploadId) {
    this._uploads.delete(uploadId);
  }
}

export const store = new FilingStore();
