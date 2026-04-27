import { useEffect } from 'react';
import { ArrowRight, ArrowLeft, CheckCircle2, XCircle, Hash, Shield, Loader2, AlertCircle } from 'lucide-react';
import { useFilingStore } from '../../../store/filingStore';

const CHECK_LABELS = {
  context_present:      '@context present',
  type_correct:         '@type = ARRPetition',
  financial_year_valid: 'financial_year format',
  revenue_fields:       'revenue_requirement fields',
  cost_fields:          'cost_of_supply fields',
  demand_fields:        'demand_forecast fields',
  capex_fields:         'capital_expenditure fields',
  all_required_present: 'All required fields present',
};

export default function Step4HashValidate() {
  const { wizard, nextStep, prevStep, hashAndValidate } = useFilingStore();

  // Compute hash + validate as soon as this step mounts (if not already done)
  useEffect(() => {
    if (!wizard.payloadHash && wizard.datasetPayload && !wizard.loading) {
      hashAndValidate();
    }
  }, []); // eslint-disable-line react-hooks/exhaustive-deps

  const result = wizard.validationResult;
  const checks = result?.checks
    ? Object.entries(CHECK_LABELS).map(([key, label]) => ({ label, pass: !!result.checks[key] }))
    : Object.values(CHECK_LABELS).map(label => ({ label, pass: false }));
  const passCount = checks.filter(c => c.pass).length;
  const allPass   = result ? result.passedAll : false;

  return (
    <div className="space-y-5">
      <div>
        <h3 className="text-base font-bold text-slate-100">Hash Computation &amp; Schema Validation</h3>
        <p className="text-sm text-slate-500 mt-1">
          SHA-256 hash computed over canonical JSON. Payload validated against IES schema before submission.
        </p>
      </div>

      {/* Loading state */}
      {wizard.loading && (
        <div className="flex items-center gap-3 p-4 rounded-lg bg-blue-500/8 border border-blue-500/20">
          <Loader2 size={16} className="animate-spin text-blue-400" />
          <span className="text-sm text-blue-400">Computing SHA-256 hash and validating IES schema…</span>
        </div>
      )}

      {/* Error */}
      {wizard.error && (
        <div className="flex items-center gap-2 p-3 rounded-lg bg-red-500/10 border border-red-500/20 text-xs text-red-400">
          <AlertCircle size={13} className="flex-shrink-0" />
          {wizard.error}
        </div>
      )}

      {!wizard.loading && (
        <div className="grid grid-cols-1 md:grid-cols-2 gap-5">
          {/* Hash card */}
          <div className="card p-5 space-y-4">
            <div className="flex items-center gap-2">
              <div className="w-8 h-8 rounded-lg bg-amber-500/15 flex items-center justify-center">
                <Hash size={16} className="text-amber-400" />
              </div>
              <span className="text-sm font-semibold text-slate-200">SHA-256 Hash</span>
              {wizard.payloadHash
                ? <span className="badge-green ml-auto">Computed</span>
                : <span className="badge-slate ml-auto">Pending</span>
              }
            </div>

            <div className="p-3 rounded-lg bg-[#0d1424] border border-slate-700/50 min-h-[60px]">
              <div className="text-[10px] text-slate-600 uppercase tracking-wider mb-2">Canonical JSON → Hash</div>
              {wizard.payloadHash ? (
                <div className="font-mono text-[11px] text-amber-400 break-all leading-relaxed">
                  {wizard.payloadHash}
                </div>
              ) : (
                <div className="text-xs text-slate-600 italic">Not yet computed</div>
              )}
            </div>

            <div className="space-y-2 text-xs text-slate-500">
              {[
                'Keys sorted alphabetically',
                'No whitespace in canonical form',
                'UTF-8 encoded before hashing',
              ].map(t => (
                <div key={t} className="flex items-center gap-2">
                  <CheckCircle2 size={13} className="text-emerald-400" />
                  <span>{t}</span>
                </div>
              ))}
            </div>

            <div className="p-3 rounded-lg bg-slate-800/60 text-xs font-mono text-slate-500 leading-relaxed">
              <span className="text-slate-600"># Python equivalent</span><br/>
              <span className="text-blue-400">canonical</span> = json.dumps(payload,<br/>
              &nbsp;&nbsp;<span className="text-green-400">sort_keys</span>=True,<br/>
              &nbsp;&nbsp;<span className="text-green-400">separators</span>=(',',':'))<br/>
              <span className="text-blue-400">hash</span> = hashlib.sha256(<br/>
              &nbsp;&nbsp;canonical.encode(<span className="text-amber-400">'utf-8'</span>)).hexdigest()
            </div>
          </div>

          {/* Schema validation card */}
          <div className="card p-5 space-y-4">
            <div className="flex items-center gap-2">
              <div className="w-8 h-8 rounded-lg bg-blue-500/15 flex items-center justify-center">
                <Shield size={16} className="text-blue-400" />
              </div>
              <span className="text-sm font-semibold text-slate-200">Schema Validation</span>
              {result
                ? <span className={`ml-auto ${allPass ? 'badge-green' : 'badge-yellow'}`}>{passCount}/{checks.length} Pass</span>
                : <span className="badge-slate ml-auto">Pending</span>
              }
            </div>

            <div className="space-y-2">
              {checks.map(({ label, pass }) => (
                <div key={label} className="flex items-center gap-2.5 py-1">
                  {pass
                    ? <CheckCircle2 size={14} className="text-emerald-400 flex-shrink-0" />
                    : <XCircle      size={14} className="text-red-400    flex-shrink-0" />
                  }
                  <span className="text-xs text-slate-300">{label}</span>
                </div>
              ))}
            </div>

            {result && (
              <div className={`p-3 rounded-lg text-xs border ${
                allPass
                  ? 'bg-emerald-500/8 border-emerald-500/20 text-emerald-400'
                  : 'bg-amber-500/8 border-amber-500/20 text-amber-400'
              }`}>
                {allPass
                  ? 'All IES schema checks pass. Payload is valid and ready for SERC submission.'
                  : `${checks.length - passCount} check(s) failed — review payload before submitting.`}
              </div>
            )}
          </div>
        </div>
      )}

      {/* CommonEnvelope preview */}
      {wizard.payloadHash && (
        <div className="card p-4">
          <div className="flex items-center gap-2 mb-3">
            <Shield size={14} className="text-purple-400" />
            <span className="text-xs font-semibold text-slate-300">CommonEnvelope</span>
            <span className="badge-purple ml-1 text-[10px]">ies:CommonEnvelope:v1.0</span>
          </div>
          <div className="grid grid-cols-2 sm:grid-cols-4 gap-3 text-xs">
            {[
              { k: 'schema_version', v: 'ies:CommonEnvelope:v1.0' },
              { k: 'content_hash',   v: wizard.payloadHash.slice(0, 20) + '…' },
              { k: 'issuer_id',      v: 'discom-maharashtra-001' },
              { k: 'created_at',     v: new Date().toISOString().slice(0, 19) + 'Z' },
            ].map(({ k, v }) => (
              <div key={k}>
                <div className="text-[10px] text-slate-500 mb-1">{k}</div>
                <div className="font-mono text-slate-300 truncate">{v}</div>
              </div>
            ))}
          </div>
        </div>
      )}

      <div className="flex justify-between pt-2">
        <button onClick={prevStep} disabled={wizard.loading} className="btn-secondary">
          <ArrowLeft size={15} /> Back
        </button>
        <button onClick={nextStep} disabled={!wizard.payloadHash || wizard.loading} className="btn-primary">
          Submit Draft to SERC <ArrowRight size={15} />
        </button>
      </div>
    </div>
  );
}
