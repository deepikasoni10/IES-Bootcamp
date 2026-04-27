import { create } from 'zustand';
import { MOCK_FILINGS, SAMPLE_DATASET_PAYLOAD, SAMPLE_CSV_COLUMNS } from '../data/mockData';
import * as api from '../services/api';

// ── Normalize backend filing record → frontend shape ──────────────────
function buildSteps(f) {
  const done = (s) => ['formally_submitted','accepted','rejected','disclosed'].includes(s);
  const acc  = (s) => ['accepted','rejected','disclosed'].includes(s);
  return [
    { name: 'Data Prepared',      status: 'done',   completedAt: f.createdAt },
    { name: 'Draft Submitted',    status: f.status !== 'preparing' ? 'done' : 'pending', completedAt: f.draftSubmittedAt || null },
    { name: 'Validation Report',  status: f.status === 'draft_validated' || done(f.status) ? 'done' : 'pending', completedAt: f.draftValidatedAt || null },
    { name: 'Formal Submitted',   status: done(f.status) ? 'done' : 'pending', completedAt: f.formalSubmittedAt || null },
    { name: 'Receipt Received',   status: acc(f.status)  ? 'done' : 'pending', completedAt: f.acceptedAt || f.rejectedAt || null },
    { name: 'Publicly Disclosed', status: f.status === 'disclosed' ? 'done' : 'pending', completedAt: f.disclosedAt || null },
  ];
}

function normalizeBackendFiling(f) {
  return {
    id:            f.filingId || f.txnId,
    txnId:         f.txnId,
    title:         `ARR Petition FY ${f.financialYear || '2026-27'}`,
    financialYear: f.financialYear || '2026-27',
    status:        f.status,
    filedAt:       f.createdAt || f.draftSubmittedAt || new Date().toISOString(),
    acceptedAt:    f.acceptedAt  || null,
    disclosedAt:   f.disclosedAt || null,
    payloadHash:   f.payloadHash,
    totalRevenue:  f.datasetPayload?.data?.revenue_requirement?.total_revenue_rs_crore || 0,
    observations:  f.validationReport?.observations || [],
    disclosureUrl: f.disclosureUrl || null,
    steps:         buildSteps(f),
    datasetPayload: f.datasetPayload || null,
    receipt:        f.receipt       || null,
    isLive:         true,
  };
}

// ── Store ─────────────────────────────────────────────────────────────
export const useFilingStore = create((set, get) => ({
  filings:       MOCK_FILINGS,
  filingsLoaded: false,

  // ── Wizard state ────────────────────────────────────────────────────
  wizard: {
    active:          false,
    currentStep:     0,
    isSample:        false,
    // Step 1
    uploadedFile:    null,
    uploadId:        null,
    preview:         null,
    // Step 2
    mappingStatus:   null,
    datasetPayload:  null,
    // Step 4
    payloadHash:     null,
    validationResult: null,
    // Step 5
    txnId:            null,
    validationReport: null,
    // Step 6
    receipt:          null,
    filingId:         null,
    // Meta
    error:   null,
    loading: false,
  },

  // ── Load filings from backend ───────────────────────────────────────
  loadFilings: async () => {
    try {
      const data = await api.listFilings();
      const live = (data.filings || []).map(normalizeBackendFiling);
      // Prepend live filings; keep mock filings so dashboard is always populated
      set({ filings: live.length ? [...live, ...MOCK_FILINGS] : MOCK_FILINGS, filingsLoaded: true });
    } catch {
      set({ filingsLoaded: true });
    }
  },

  // ── Wizard lifecycle ────────────────────────────────────────────────
  startWizard: () => set(s => ({
    wizard: {
      ...s.wizard,
      active: true, currentStep: 0,
      isSample: false,
      uploadedFile: null, uploadId: null, preview: null,
      mappingStatus: null, datasetPayload: null,
      payloadHash: null, validationResult: null,
      txnId: null, validationReport: null,
      receipt: null, filingId: null,
      error: null, loading: false,
    },
  })),
  closeWizard: () => set(s => ({ wizard: { ...s.wizard, active: false } })),
  setStep:     (step) => set(s => ({ wizard: { ...s.wizard, currentStep: step } })),
  nextStep:    ()     => set(s => ({ wizard: { ...s.wizard, currentStep: Math.min(s.wizard.currentStep + 1, 5) } })),
  prevStep:    ()     => set(s => ({ wizard: { ...s.wizard, currentStep: Math.max(s.wizard.currentStep - 1, 0) } })),

  // ── Step 1: Upload real file to backend ────────────────────────────
  uploadFile: async (file) => {
    set(s => ({ wizard: { ...s.wizard, loading: true, error: null } }));
    try {
      const data = await api.uploadFile(file);
      set(s => ({ wizard: { ...s.wizard, uploadedFile: file, uploadId: data.uploadId, preview: data.preview, loading: false } }));
      return data;
    } catch (e) {
      set(s => ({ wizard: { ...s.wizard, loading: false, error: e.message } }));
      throw e;
    }
  },

  // ── Step 1 (alt): Use built-in sample — skip real upload ───────────
  useSample: () => set(s => ({
    wizard: {
      ...s.wizard,
      isSample:      true,
      uploadedFile:  { name: 'msedcl_arr_2026-27.xlsx', size: 42800, isSample: true },
      uploadId:      'sample',
      preview:       null,
      datasetPayload: SAMPLE_DATASET_PAYLOAD,
      mappingStatus: SAMPLE_CSV_COLUMNS,
    },
  })),

  // ── Step 2: Map columns → DatasetPayload ───────────────────────────
  generatePayload: async () => {
    const { uploadId, isSample, datasetPayload } = get().wizard;
    if (isSample) return { datasetPayload }; // already seeded from useSample()

    set(s => ({ wizard: { ...s.wizard, loading: true, error: null } }));
    try {
      const data = await api.mapPayload({ uploadId, discomId: 'discom-maharashtra-001', financialYear: '2026-27' });
      set(s => ({ wizard: { ...s.wizard, datasetPayload: data.datasetPayload, mappingStatus: data.mappingStatus, loading: false } }));
      return data;
    } catch (e) {
      set(s => ({ wizard: { ...s.wizard, loading: false, error: e.message } }));
      throw e;
    }
  },

  // ── Step 4: Compute hash + validate schema ─────────────────────────
  hashAndValidate: async () => {
    const { datasetPayload } = get().wizard;
    if (!datasetPayload) return;
    set(s => ({ wizard: { ...s.wizard, loading: true, error: null } }));
    try {
      const [hashData, validateData] = await Promise.all([
        api.hashPayload(datasetPayload),
        api.validatePayload(datasetPayload),
      ]);
      set(s => ({ wizard: { ...s.wizard, payloadHash: hashData.payloadHash, validationResult: validateData, loading: false } }));
      return { hashData, validateData };
    } catch (e) {
      set(s => ({ wizard: { ...s.wizard, loading: false, error: e.message } }));
      throw e;
    }
  },

  // ── Step 5: Beckn /init — draft validation ─────────────────────────
  submitDraft: async () => {
    const { datasetPayload, payloadHash } = get().wizard;
    set(s => ({ wizard: { ...s.wizard, loading: true, error: null } }));
    try {
      const data = await api.submitDraft({ datasetPayload, payloadHash, discomId: 'discom-maharashtra-001', financialYear: '2026-27' });
      set(s => ({ wizard: { ...s.wizard, txnId: data.txnId, validationReport: data.validationReport, loading: false } }));
      return data;
    } catch (e) {
      set(s => ({ wizard: { ...s.wizard, loading: false, error: e.message } }));
      throw e;
    }
  },

  // ── Step 6: Beckn /confirm — formal filing ─────────────────────────
  submitFormal: async () => {
    const { txnId, datasetPayload, payloadHash } = get().wizard;
    set(s => ({ wizard: { ...s.wizard, loading: true, error: null } }));
    try {
      const data = await api.submitFormal({ txnId, datasetPayload, payloadHash, discomId: 'discom-maharashtra-001' });
      set(s => ({ wizard: { ...s.wizard, receipt: data.receipt, filingId: data.filingId, loading: false } }));
      get().loadFilings(); // refresh history
      return data;
    } catch (e) {
      set(s => ({ wizard: { ...s.wizard, loading: false, error: e.message } }));
      throw e;
    }
  },

  getFilingById: (id) => get().filings.find(f => f.id === id || f.txnId === id),
}));

// ── App-level state (sidebar, user) ──────────────────────────────────
export const useAppStore = create((set) => ({
  sidebarOpen: true,
  toggleSidebar: () => set(s => ({ sidebarOpen: !s.sidebarOpen })),
  user: {
    name:   'Rahul Sharma',
    role:   'Filing Officer',
    discom: 'MSEDCL',
    avatar: 'RS',
  },
}));
