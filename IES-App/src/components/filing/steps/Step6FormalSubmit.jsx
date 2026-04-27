import { useState } from 'react';
import { CheckCircle2, Shield, Award, Loader2, ExternalLink, Download, X, AlertCircle } from 'lucide-react';
import { useFilingStore } from '../../../store/filingStore';
import JsonViewer from '../../ui/JsonViewer';

export default function Step6FormalSubmit() {
  const { wizard, submitFormal, closeWizard, prevStep } = useFilingStore();
  const [done, setDone] = useState(false);

  const handleFormal = async () => {
    try {
      await submitFormal();
      setDone(true);
    } catch { /* error shown in wizard.error */ }
  };

  const receipt = wizard.receipt;

  return (
    <div className="space-y-5">
      <div>
        <h3 className="text-base font-bold text-slate-100">Formal Submission — /confirm</h3>
        <p className="text-sm text-slate-500 mt-1">
          Submit the official regulatory filing with your W3C Verifiable Credential and Ed25519 digital signature.
          SERC will verify your credential, validate the hash, and issue a signed receipt.
        </p>
      </div>

      {/* Error */}
      {wizard.error && (
        <div className="flex items-center gap-2 p-3 rounded-lg bg-red-500/10 border border-red-500/20 text-xs text-red-400">
          <AlertCircle size={13} className="flex-shrink-0" />
          {wizard.error}
        </div>
      )}

      {!done && (
        <>
          {/* Credential & Signature */}
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            <div className="card p-4 space-y-3">
              <div className="flex items-center gap-2">
                <Shield size={15} className="text-purple-400" />
                <span className="text-xs font-semibold text-slate-300">Verifiable Credential</span>
                <span className="badge-green ml-auto text-[10px]">Active</span>
              </div>
              <div className="space-y-2 text-xs">
                {[
                  { k: 'issuer',       v: 'did:ies:credential-service' },
                  { k: 'subject',      v: 'did:ies:discom-maharashtra-001' },
                  { k: 'role',         v: 'distribution_company' },
                  { k: 'jurisdiction', v: 'maharashtra' },
                  { k: 'license',      v: 'MERC/DISCOM/001' },
                  { k: 'algorithm',    v: 'Ed25519Signature2020' },
                ].map(({ k, v }) => (
                  <div key={k} className="flex justify-between items-center py-1 border-b border-slate-800/50">
                    <span className="text-slate-500">{k}</span>
                    <span className="font-mono text-slate-300 truncate max-w-[160px]">{v}</span>
                  </div>
                ))}
              </div>
            </div>
            <div className="card p-4 space-y-3">
              <div className="flex items-center gap-2">
                <Award size={15} className="text-amber-400" />
                <span className="text-xs font-semibold text-slate-300">Digital Signature</span>
                <span className="badge-green ml-auto text-[10px]">Ready</span>
              </div>
              <div className="space-y-2 text-xs">
                {[
                  { k: 'algorithm', v: 'Ed25519' },
                  { k: 'signer',    v: 'did:ies:discom-maharashtra-001' },
                  { k: 'signed',    v: wizard.payloadHash?.slice(0, 18) + '…' },
                ].map(({ k, v }) => (
                  <div key={k} className="flex justify-between items-center py-1 border-b border-slate-800/50">
                    <span className="text-slate-500">{k}</span>
                    <span className="font-mono text-slate-300 truncate max-w-[160px]">{v}</span>
                  </div>
                ))}
              </div>
              <div className="p-2 rounded bg-slate-800/60 text-[10px] font-mono text-slate-500 break-all">
                sig: base64:z3FXQjeKmP9qR2vY4wZ7aB1cD5eF6gH8iJ0kL2mN4oP6qR8sT0uV2w…
              </div>
              <div className="p-3 rounded-lg bg-amber-500/8 border border-amber-500/20 text-xs text-amber-400">
                Provenance links to draft validation: <span className="font-mono">{wizard.txnId ? `msg-oninit-${wizard.txnId.slice(0,8)}` : 'msg-oninit-…'}</span>
              </div>
            </div>
          </div>

          <div className="flex flex-col items-center gap-4 py-4">
            <p className="text-sm text-slate-400 text-center">
              This is the <strong className="text-slate-200">official regulatory submission</strong>.
              Once submitted, SERC will verify and issue a signed receipt.
            </p>
            <button onClick={handleFormal} disabled={wizard.loading} className="btn-primary px-8 py-3">
              {wizard.loading ? (
                <><Loader2 size={16} className="animate-spin" /> Submitting to SERC…</>
              ) : (
                <><Shield size={16} /> Submit Formal Filing /confirm</>
              )}
            </button>
            {wizard.loading && (
              <div className="text-xs text-slate-500 animate-pulse">
                Verifying credential → Checking hash → Issuing receipt → /on_confirm callback…
              </div>
            )}
          </div>
        </>
      )}

      {/* Receipt */}
      {done && receipt && (
        <div className="space-y-4 animate-slide-up">
          <div className="flex items-center gap-3 p-4 rounded-xl bg-emerald-500/10 border border-emerald-500/25">
            <div className="w-12 h-12 rounded-full bg-emerald-500/20 flex items-center justify-center flex-shrink-0">
              <CheckCircle2 size={24} className="text-emerald-400" />
            </div>
            <div>
              <div className="text-base font-bold text-emerald-400">Filing Accepted!</div>
              <div className="text-xs text-slate-400 mt-0.5">
                Filing ID: <span className="font-mono text-slate-300">{receipt.filing_id || wizard.filingId}</span>
              </div>
              <div className="text-xs text-slate-500 mt-0.5">
                Issued at: {receipt.issued_at ? new Date(receipt.issued_at).toLocaleString('en-IN') : '—'}
              </div>
            </div>
          </div>

          <div className="grid grid-cols-1 md:grid-cols-3 gap-3">
            <div className="card p-3 flex items-center gap-2">
              <CheckCircle2 size={14} className="text-emerald-400" />
              <div>
                <div className="text-[10px] text-slate-500">SERC Decision</div>
                <div className="text-xs font-bold text-emerald-400 uppercase">{receipt.status || 'accepted'}</div>
              </div>
            </div>
            <div className="card p-3 flex items-center gap-2">
              <Shield size={14} className="text-purple-400" />
              <div>
                <div className="text-[10px] text-slate-500">Signature</div>
                <div className="text-xs font-semibold text-purple-400">
                  {receipt.proof?.type || 'Ed25519Signature2020'}
                </div>
              </div>
            </div>
            <div className="card p-3 flex items-center gap-2">
              <Award size={14} className="text-blue-400" />
              <div>
                <div className="text-[10px] text-slate-500">Disclosure</div>
                <div className="text-xs font-semibold text-blue-400">DeDi Catalog</div>
              </div>
            </div>
          </div>

          <JsonViewer data={receipt} title="Signed SERC Receipt (on_confirm)" maxHeight="260px" />

          {receipt.disclosure_catalog_url && (
            <div className="flex items-center gap-3 p-3 rounded-lg bg-blue-500/8 border border-blue-500/20 text-xs">
              <ExternalLink size={13} className="text-blue-400 flex-shrink-0" />
              <div className="flex-1">
                <div className="text-slate-400">Public Disclosure URL (DeDi Catalog)</div>
                <div className="font-mono text-blue-300 mt-0.5 truncate">{receipt.disclosure_catalog_url}</div>
              </div>
              <Download size={13} className="text-slate-500 cursor-pointer hover:text-slate-200 flex-shrink-0" />
            </div>
          )}

          <div className="flex gap-3 justify-end pt-2">
            <button onClick={closeWizard} className="btn-secondary">
              <X size={15} /> Close
            </button>
            <button onClick={closeWizard} className="btn-primary">
              <CheckCircle2 size={15} /> View in Dashboard
            </button>
          </div>
        </div>
      )}

      {/* Done but no receipt (rejected / timeout) */}
      {done && !receipt && !wizard.loading && (
        <div className="p-4 rounded-lg bg-amber-500/8 border border-amber-500/20 text-xs text-amber-400">
          Submission sent. Awaiting async receipt from SERC callback…
        </div>
      )}

      {!done && (
        <div className="flex justify-between pt-2">
          <button onClick={prevStep} disabled={wizard.loading} className="btn-secondary">
            Back
          </button>
        </div>
      )}
    </div>
  );
}
