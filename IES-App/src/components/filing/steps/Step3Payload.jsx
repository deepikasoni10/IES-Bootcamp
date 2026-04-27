import { ArrowRight, ArrowLeft, FileJson, Info } from 'lucide-react';
import { useFilingStore } from '../../../store/filingStore';
import JsonViewer from '../../ui/JsonViewer';

function safeSchema(context) {
  if (!context || typeof context !== 'string') return 'ies/schemas/v1';
  const parts = context.split('/');
  return parts.slice(-3, -1).join('/') || context;
}

export default function Step3Payload() {
  const { wizard, nextStep, prevStep } = useFilingStore();
  const payload = wizard.datasetPayload;

  const fields = payload ? [
    { label: 'Schema',         value: safeSchema(payload['@context']),                                   mono: true },
    { label: 'Type',           value: payload['@type'] || '—',                                           mono: true },
    { label: 'Financial Year', value: payload.financial_year || '—' },
    { label: 'DISCOM ID',      value: payload.discom_id || '—',                                          mono: true },
    { label: 'Total Revenue',  value: payload.data?.revenue_requirement?.total_revenue_rs_crore != null
        ? `₹ ${Number(payload.data.revenue_requirement.total_revenue_rs_crore).toLocaleString('en-IN')} Cr` : '—' },
    { label: 'Peak Demand',    value: payload.data?.demand_forecast?.peak_demand_mw != null
        ? `${Number(payload.data.demand_forecast.peak_demand_mw).toLocaleString('en-IN')} MW` : '—' },
    { label: 'Consumer Count', value: payload.data?.demand_forecast?.consumer_count != null
        ? Number(payload.data.demand_forecast.consumer_count).toLocaleString('en-IN') : '—' },
    { label: 'AT&C Losses',   value: payload.data?.cost_of_supply?.at_losses_percent != null
        ? `${payload.data.cost_of_supply.at_losses_percent}%` : '—' },
  ] : [];

  return (
    <div className="space-y-5">
      <div className="flex items-start justify-between">
        <div>
          <h3 className="text-base font-bold text-slate-100">DatasetPayload Review</h3>
          <p className="text-sm text-slate-500 mt-1">
            Review the generated IES-compliant JSON-LD payload before computing the hash.
          </p>
        </div>
        <span className="badge-blue flex-shrink-0">ies:DatasetPayload:ARR:v1.0</span>
      </div>

      {/* Summary cards */}
      <div className="grid grid-cols-2 sm:grid-cols-4 gap-3">
        {fields.map(({ label, value, mono }) => (
          <div key={label} className="card p-3">
            <div className="text-[10px] text-slate-500 uppercase tracking-wider mb-1">{label}</div>
            <div className={`text-xs font-semibold text-slate-200 ${mono ? 'font-mono' : ''}`}>{value}</div>
          </div>
        ))}
      </div>

      {/* Info */}
      <div className="flex items-start gap-2 p-3 rounded-lg bg-blue-500/8 border border-blue-500/20 text-xs text-slate-400">
        <Info size={13} className="text-blue-400 flex-shrink-0 mt-0.5" />
        <span>
          This payload will be <strong className="text-slate-300">canonicalized</strong> (sorted keys, no whitespace)
          before SHA-256 hashing. Any modification produces a different hash, detectable by SERC.
        </span>
      </div>

      {payload && <JsonViewer data={payload} title="DatasetPayload JSON-LD" maxHeight="360px" />}

      <div className="flex justify-between pt-2">
        <button onClick={prevStep} className="btn-secondary">
          <ArrowLeft size={15} /> Back
        </button>
        <button onClick={nextStep} className="btn-primary">
          Compute Hash &amp; Validate <ArrowRight size={15} />
        </button>
      </div>
    </div>
  );
}
