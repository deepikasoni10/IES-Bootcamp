import { useState, useEffect } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import {
  ArrowLeft, CheckCircle2, Clock, Hash, ExternalLink, Shield,
  FileText, AlertTriangle, Download, Info, Eye, Copy, Check
} from 'lucide-react';
import Header from '../components/layout/Header';
import StatusBadge from '../components/ui/StatusBadge';
import JsonViewer from '../components/ui/JsonViewer';
import { useFilingStore } from '../store/filingStore';
import { MOCK_RECEIPT, SAMPLE_DATASET_PAYLOAD } from '../data/mockData';

function TimelineStep({ step, isLast }) {
  const isDone     = step.status === 'done';
  const isRejected = step.status === 'rejected';
  return (
    <div className="flex gap-4">
      <div className="flex flex-col items-center">
        <div className={`w-8 h-8 rounded-full flex items-center justify-center flex-shrink-0 ${
          isDone      ? 'bg-emerald-600 text-white' :
          isRejected  ? 'bg-red-600 text-white' :
                        'bg-surface-600 border-2 border-slate-700'
        }`}>
          {isDone     && <CheckCircle2 size={16} />}
          {isRejected && <AlertTriangle size={14} />}
          {!isDone && !isRejected && <Clock size={14} className="text-slate-500" />}
        </div>
        {!isLast && <div className={`w-px flex-1 mt-1 min-h-[24px] ${isDone ? 'bg-emerald-700/50' : 'bg-slate-800'}`} />}
      </div>
      <div className="pb-5 flex-1">
        <div className="flex items-center gap-2">
          <span className={`text-sm font-semibold ${isDone ? 'text-slate-200' : isRejected ? 'text-red-400' : 'text-slate-500'}`}>
            {step.name}
          </span>
          {isRejected && <span className="badge-red text-[10px]">Rejected</span>}
          {isDone && !step.completedAt && <span className="badge-slate text-[10px]">Queued</span>}
        </div>
        {step.completedAt && (
          <div className="text-xs text-slate-600 mt-0.5 font-mono">
            {new Date(step.completedAt).toLocaleString('en-IN')}
          </div>
        )}
      </div>
    </div>
  );
}

function HashDisplay({ hash }) {
  const [copied, setCopied] = useState(false);
  const copy = () => {
    navigator.clipboard.writeText(hash);
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  };
  return (
    <div className="flex items-center gap-2 p-3 rounded-lg bg-[#0d1424] border border-slate-700/50">
      <div className="font-mono text-xs text-amber-400 break-all flex-1">{hash}</div>
      <button onClick={copy} className="flex-shrink-0 text-slate-500 hover:text-slate-200 transition-colors">
        {copied ? <Check size={13} className="text-emerald-400" /> : <Copy size={13} />}
      </button>
    </div>
  );
}

export default function FilingDetail() {
  const { id }      = useParams();
  const navigate    = useNavigate();
  const { getFilingById, loadFilings, filingsLoaded } = useFilingStore();
  const [activeTab, setActiveTab] = useState('overview');

  // Ensure filings are loaded (in case user navigates directly to this URL)
  useEffect(() => { if (!filingsLoaded) loadFilings(); }, []); // eslint-disable-line react-hooks/exhaustive-deps

  const filing = getFilingById(decodeURIComponent(id));

  if (!filing) {
    return (
      <div className="p-6 text-center text-slate-500">
        <FileText size={40} className="mx-auto mb-3" />
        <p>Filing not found</p>
        <button onClick={() => navigate('/history')} className="btn-secondary mt-4 mx-auto">
          Back to History
        </button>
      </div>
    );
  }

  const TABS = [
    { id: 'overview', label: 'Overview' },
    { id: 'payload',  label: 'DatasetPayload' },
    { id: 'receipt',  label: 'Receipt' },
    { id: 'timeline', label: 'Timeline' },
  ];

  // Prefer real data stored on the filing, fall back to mock data for demo filings
  const payloadData = filing.datasetPayload || SAMPLE_DATASET_PAYLOAD;
  const receiptData = filing.receipt        || MOCK_RECEIPT;

  return (
    <div className="animate-fade-in">
      <Header
        title={filing.title}
        subtitle={`${filing.id} · FY ${filing.financialYear}`}
      />

      <div className="p-6 space-y-5">

        {/* Back + Status */}
        <div className="flex items-center gap-3 flex-wrap">
          <button onClick={() => navigate('/history')} className="btn-ghost text-xs py-1.5 px-2">
            <ArrowLeft size={14} /> Back
          </button>
          <StatusBadge status={filing.status} />
          {filing.status === 'disclosed' && (
            <a href={filing.disclosureUrl} target="_blank" rel="noreferrer" className="btn-ghost text-xs py-1.5 px-2">
              <ExternalLink size={13} /> View Disclosure
            </a>
          )}
          <div className="ml-auto">
            <button className="btn-ghost text-xs py-1.5 px-2">
              <Download size={13} /> Export
            </button>
          </div>
        </div>

        {/* Key info cards */}
        <div className="grid grid-cols-2 sm:grid-cols-4 gap-3">
          {[
            { label: 'Filing ID',      value: filing.id,             mono: true },
            { label: 'Financial Year', value: `FY ${filing.financialYear}` },
            { label: 'Total Revenue',  value: filing.totalRevenue ? `₹ ${Number(filing.totalRevenue).toLocaleString('en-IN')} Cr` : '—' },
            { label: 'Filed On',       value: filing.filedAt ? new Date(filing.filedAt).toLocaleDateString('en-IN', { day: '2-digit', month: 'short', year: 'numeric' }) : '—' },
          ].map(({ label, value, mono }) => (
            <div key={label} className="card p-3">
              <div className="text-[10px] text-slate-500 uppercase tracking-wider mb-1">{label}</div>
              <div className={`text-xs font-semibold text-slate-200 truncate ${mono ? 'font-mono' : ''}`}>{value}</div>
            </div>
          ))}
        </div>

        {/* Hash */}
        {filing.payloadHash && (
          <div className="card p-4">
            <div className="flex items-center gap-2 mb-2">
              <Hash size={14} className="text-amber-400" />
              <span className="text-xs font-semibold text-slate-300">Payload Hash (SHA-256)</span>
              <span className="badge-green ml-auto text-[10px]">Verified</span>
            </div>
            <HashDisplay hash={filing.payloadHash} />
          </div>
        )}

        {/* Observations */}
        {filing.observations?.length > 0 && (
          <div className="card p-4">
            <div className="flex items-center gap-2 mb-3">
              <AlertTriangle size={14} className="text-amber-400" />
              <span className="text-xs font-semibold text-slate-300">SERC Observations ({filing.observations.length})</span>
            </div>
            <div className="space-y-2">
              {filing.observations.map((obs, i) => (
                <div key={i} className="flex items-start gap-2.5 p-3 rounded-lg bg-slate-800/60 border border-slate-700/50">
                  {obs.severity === 'warning'
                    ? <AlertTriangle size={13} className="text-amber-400 flex-shrink-0 mt-0.5" />
                    : obs.severity === 'error'
                    ? <AlertTriangle size={13} className="text-red-400 flex-shrink-0 mt-0.5" />
                    : <Info size={13} className="text-blue-400 flex-shrink-0 mt-0.5" />
                  }
                  <div className="flex-1">
                    <div className="font-mono text-[11px] text-slate-400 mb-0.5">{obs.field}</div>
                    <div className="text-xs text-slate-300">{obs.message}</div>
                  </div>
                  <span className={
                    obs.severity === 'warning' ? 'badge-yellow' :
                    obs.severity === 'error'   ? 'badge-red' : 'badge-blue'
                  } style={{fontSize:'10px'}}>{obs.severity}</span>
                </div>
              ))}
            </div>
          </div>
        )}

        {/* Tabs */}
        <div>
          <div className="flex gap-1 border-b border-slate-800 mb-4">
            {TABS.map(tab => (
              <button
                key={tab.id}
                onClick={() => setActiveTab(tab.id)}
                className={`px-4 py-2 text-xs font-semibold border-b-2 transition-all duration-200 -mb-px ${
                  activeTab === tab.id
                    ? 'border-blue-500 text-blue-400'
                    : 'border-transparent text-slate-500 hover:text-slate-300'
                }`}
              >
                {tab.label}
              </button>
            ))}
          </div>

          {activeTab === 'overview' && (
            <div className="space-y-4 animate-slide-up">
              <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                <div className="card p-4">
                  <div className="flex items-center gap-2 mb-3">
                    <CheckCircle2 size={14} className="text-emerald-400" />
                    <span className="text-xs font-semibold text-slate-300">SERC Decision</span>
                  </div>
                  <div className="space-y-2 text-xs">
                    {[
                      { k: 'Status',      v: filing.status.replace(/_/g, ' '), hl: true },
                      { k: 'Filed At',    v: filing.filedAt    ? new Date(filing.filedAt).toLocaleString('en-IN')    : '—' },
                      { k: 'Accepted At', v: filing.acceptedAt ? new Date(filing.acceptedAt).toLocaleString('en-IN') : '—' },
                      { k: 'Disclosed',   v: filing.disclosedAt ? new Date(filing.disclosedAt).toLocaleString('en-IN') : 'Pending' },
                    ].map(({ k, v, hl }) => (
                      <div key={k} className="flex justify-between py-1.5 border-b border-slate-800/50">
                        <span className="text-slate-500">{k}</span>
                        <span className={`font-medium ${hl ? 'text-emerald-400' : 'text-slate-300'}`}>{v}</span>
                      </div>
                    ))}
                  </div>
                </div>
                <div className="card p-4">
                  <div className="flex items-center gap-2 mb-3">
                    <Shield size={14} className="text-purple-400" />
                    <span className="text-xs font-semibold text-slate-300">Credentials Used</span>
                  </div>
                  <div className="space-y-2 text-xs">
                    {[
                      { k: 'Issuer',    v: 'did:ies:credential-service' },
                      { k: 'Subject',   v: 'did:ies:discom-maharashtra-001' },
                      { k: 'Algorithm', v: 'Ed25519Signature2020' },
                      { k: 'License',   v: 'MERC/DISCOM/001' },
                    ].map(({ k, v }) => (
                      <div key={k} className="flex justify-between py-1.5 border-b border-slate-800/50">
                        <span className="text-slate-500">{k}</span>
                        <span className="font-mono text-slate-300 truncate max-w-[160px]">{v}</span>
                      </div>
                    ))}
                  </div>
                </div>
              </div>

              {filing.disclosureUrl && (
                <div className="flex items-center gap-3 p-4 rounded-xl bg-emerald-500/8 border border-emerald-500/20">
                  <Eye size={16} className="text-emerald-400 flex-shrink-0" />
                  <div className="flex-1">
                    <div className="text-sm font-semibold text-emerald-400">Publicly Disclosed on DeDi Catalog</div>
                    <div className="font-mono text-xs text-slate-400 mt-1 break-all">{filing.disclosureUrl}</div>
                  </div>
                  <a href={filing.disclosureUrl} target="_blank" rel="noreferrer" className="btn-secondary text-xs flex-shrink-0">
                    <ExternalLink size={13} /> Open
                  </a>
                </div>
              )}
            </div>
          )}

          {activeTab === 'payload' && (
            <div className="animate-slide-up">
              <JsonViewer data={payloadData} title="DatasetPayload JSON-LD" maxHeight="500px" />
            </div>
          )}

          {activeTab === 'receipt' && (
            <div className="animate-slide-up">
              {['disclosed', 'accepted'].includes(filing.status)
                ? <JsonViewer data={receiptData} title="Signed SERC Receipt (on_confirm)" maxHeight="500px" />
                : (
                  <div className="flex flex-col items-center gap-2 py-12 text-slate-600">
                    <FileText size={32} />
                    <p className="text-sm">Receipt not yet available for this filing</p>
                  </div>
                )
              }
            </div>
          )}

          {activeTab === 'timeline' && (
            <div className="animate-slide-up card p-6 max-w-lg">
              {(filing.steps || []).map((step, i) => (
                <TimelineStep key={i} step={step} isLast={i === filing.steps.length - 1} />
              ))}
            </div>
          )}
        </div>

      </div>
    </div>
  );
}
