import { useState } from 'react';
import { ArrowRight, ArrowLeft, Send, CheckCircle2, AlertTriangle, Info, Loader2, AlertCircle } from 'lucide-react';
import { useFilingStore } from '../../../store/filingStore';

export default function Step5DraftSubmit() {
  const { wizard, submitDraft, nextStep, prevStep } = useFilingStore();
  const [sent, setSent] = useState(false);

  const handleSubmit = async () => {
    try {
      await submitDraft();
      setSent(true);
    } catch { /* error shown in wizard.error */ }
  };

  const report = wizard.validationReport;

  const severityIcon = (s) => s === 'warning'
    ? <AlertTriangle size={13} className="text-amber-400 flex-shrink-0 mt-0.5" />
    : <Info size={13} className="text-blue-400 flex-shrink-0 mt-0.5" />;

  return (
    <div className="space-y-5">
      <div>
        <h3 className="text-base font-bold text-slate-100">Draft Validation — /init</h3>
        <p className="text-sm text-slate-500 mt-1">
          Submit a non-binding draft to Mock SERC for validation before formal filing.
          SERC will validate schema, hash, and completeness.
        </p>
      </div>

      {/* Beckn message preview */}
      <div className="card p-4 space-y-3">
        <div className="flex items-center gap-2">
          <Send size={14} className="text-blue-400" />
          <span className="text-xs font-semibold text-slate-300">Beckn /init Message</span>
          <span className="badge-blue ml-auto text-[10px]">ies:regulatory</span>
        </div>
        <div className="grid grid-cols-2 sm:grid-cols-3 gap-3 text-xs">
          {[
            { k: 'action',         v: 'init' },
            { k: 'transaction_id', v: wizard.txnId || '(generated on submit)' },
            { k: 'bap_id',         v: 'infosys-discom-bap.sandbox.ies' },
            { k: 'bpp_id',         v: 'mock-serc.sandbox.ies' },
            { k: 'filing.type',    v: 'draft_validation' },
            { k: 'payload_hash',   v: wizard.payloadHash ? wizard.payloadHash.slice(0, 18) + '…' : '—' },
          ].map(({ k, v }) => (
            <div key={k} className="p-2 rounded bg-slate-800/60">
              <div className="text-[10px] text-slate-500 mb-1">{k}</div>
              <div className="font-mono text-slate-300 truncate">{v}</div>
            </div>
          ))}
        </div>
      </div>

      {/* Error */}
      {wizard.error && (
        <div className="flex items-center gap-2 p-3 rounded-lg bg-red-500/10 border border-red-500/20 text-xs text-red-400">
          <AlertCircle size={13} className="flex-shrink-0" />
          {wizard.error}
        </div>
      )}

      {/* Submit button */}
      {!sent && (
        <div className="flex flex-col items-center gap-4 py-4">
          <div className="text-center">
            <p className="text-sm text-slate-400">Ready to submit draft to Mock SERC via Beckn ONIX Gateway</p>
            <p className="text-xs text-slate-600 mt-1">SERC will return a ValidationReport asynchronously to your callback URL</p>
          </div>
          <button onClick={handleSubmit} disabled={wizard.loading} className="btn-primary px-8 py-3">
            {wizard.loading ? (
              <><Loader2 size={16} className="animate-spin" /> Submitting via ONIX…</>
            ) : (
              <><Send size={16} /> Send /init to Mock SERC</>
            )}
          </button>
          {wizard.loading && (
            <div className="text-xs text-slate-500 animate-pulse">
              BAP → Gateway → Mock SERC → Processing → /on_init callback…
            </div>
          )}
        </div>
      )}

      {/* Validation Report */}
      {sent && report && (
        <div className="space-y-4 animate-slide-up">
          <div className="flex items-center gap-2 p-3 rounded-lg bg-emerald-500/8 border border-emerald-500/20">
            <CheckCircle2 size={16} className="text-emerald-400" />
            <div>
              <span className="text-sm font-semibold text-emerald-400">
                ACK Received (HTTP 200) · /on_init callback delivered
              </span>
              <div className="text-xs text-slate-500 mt-0.5">
                Transaction ID: <span className="font-mono text-blue-400">{wizard.txnId}</span>
              </div>
              <div className="text-xs text-slate-500 mt-0.5">
                Status: <span className="text-amber-400 font-medium">{report.status?.replace(/_/g, ' ') || 'validated'}</span>
              </div>
            </div>
          </div>

          <div className="card p-5 space-y-4">
            <h4 className="text-sm font-semibold text-slate-200">Validation Report</h4>
            <div className="grid grid-cols-3 gap-3">
              {[
                { label: 'Schema Check',  val: report.schema_check,       pass: report.schema_check === 'pass' },
                { label: 'Hash Check',    val: report.hash_check,         pass: report.hash_check === 'pass' },
                { label: 'Completeness',  val: report.completeness_check, pass: report.completeness_check === 'pass' },
              ].map(({ label, val, pass }) => (
                <div key={label} className={`p-3 rounded-lg border ${pass ? 'bg-emerald-500/8 border-emerald-500/20' : 'bg-amber-500/8 border-amber-500/20'}`}>
                  <div className="text-[10px] text-slate-500 mb-1">{label}</div>
                  <div className={`text-xs font-bold uppercase ${pass ? 'text-emerald-400' : 'text-amber-400'}`}>{val || '—'}</div>
                </div>
              ))}
            </div>

            {report.observations?.length > 0 && (
              <div>
                <p className="text-xs font-semibold text-slate-400 mb-2">Observations ({report.observations.length})</p>
                <div className="space-y-2">
                  {report.observations.map((obs, i) => (
                    <div key={i} className="flex items-start gap-2.5 p-3 rounded-lg bg-slate-800/60 border border-slate-700/50">
                      {severityIcon(obs.severity)}
                      <div>
                        <div className="font-mono text-[11px] text-slate-400 mb-0.5">{obs.field}</div>
                        <div className="text-xs text-slate-300">{obs.message}</div>
                      </div>
                      <span className={`ml-auto flex-shrink-0 ${obs.severity === 'warning' ? 'badge-yellow' : 'badge-blue'}`} style={{fontSize:'10px'}}>
                        {obs.severity}
                      </span>
                    </div>
                  ))}
                </div>
              </div>
            )}

            {report.recommendation && (
              <div className="p-3 rounded-lg bg-blue-500/8 border border-blue-500/20 text-xs text-blue-300">
                <strong>Recommendation:</strong> {report.recommendation.replace(/_/g, ' ')}
              </div>
            )}
          </div>
        </div>
      )}

      {/* No report yet but sent */}
      {sent && !report && !wizard.loading && (
        <div className="p-4 rounded-lg bg-amber-500/8 border border-amber-500/20 text-xs text-amber-400">
          Draft submitted. Awaiting async ValidationReport from SERC callback…
        </div>
      )}

      <div className="flex justify-between pt-2">
        <button onClick={prevStep} disabled={wizard.loading} className="btn-secondary">
          <ArrowLeft size={15} /> Back
        </button>
        <button onClick={nextStep} disabled={!sent} className="btn-primary">
          Proceed to Formal Filing <ArrowRight size={15} />
        </button>
      </div>
    </div>
  );
}
