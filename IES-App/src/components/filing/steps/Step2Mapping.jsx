import { CheckCircle2, ArrowRight, ArrowLeft, Link, Loader2, AlertCircle } from 'lucide-react';
import { useFilingStore } from '../../../store/filingStore';
import { SAMPLE_CSV_COLUMNS } from '../../../data/mockData';

const GROUPS = [
  { label: 'Revenue Requirement', prefix: 'data.revenue_requirement' },
  { label: 'Cost of Supply',      prefix: 'data.cost_of_supply' },
  { label: 'Demand Forecast',     prefix: 'data.demand_forecast' },
  { label: 'Capital Expenditure', prefix: 'data.capital_expenditure' },
];

export default function Step2Mapping() {
  const { wizard, nextStep, prevStep, generatePayload } = useFilingStore();

  const handleNext = async () => {
    try {
      await generatePayload();
      nextStep();
    } catch { /* error surfaced in wizard.error */ }
  };

  // Use backend mappingStatus (array) for real files, or SAMPLE_CSV_COLUMNS for sample
  const rawCols = wizard.mappingStatus
    ? (Array.isArray(wizard.mappingStatus)
        ? wizard.mappingStatus
        : SAMPLE_CSV_COLUMNS)
    : SAMPLE_CSV_COLUMNS;

  // Normalise to { source, target, mapped }
  const cols = rawCols.map(c => ({
    source: c.source,
    target: c.target || c.target,
    mapped: c.mapped !== false,
  }));

  const mappedCount = cols.filter(c => c.mapped).length;

  return (
    <div className="space-y-5">
      <div>
        <h3 className="text-base font-bold text-slate-100">Schema Mapping</h3>
        <p className="text-sm text-slate-500 mt-1">
          Your DISCOM CSV columns are automatically mapped to IES DatasetPayload JSON-LD fields.
          Review and confirm before generating the payload.
        </p>
      </div>

      {/* Mapping config banner */}
      <div className="flex items-center gap-3 p-3 rounded-lg bg-blue-500/8 border border-blue-500/20">
        <Link size={14} className="text-blue-400 flex-shrink-0" />
        <div className="text-xs text-slate-400">
          Using config: <span className="font-mono text-blue-400">mapping_config_mh_discom.yaml</span>
          &nbsp;· Target: <span className="font-mono text-blue-400">ies:DatasetPayload:ARR:v1.0</span>
        </div>
        <span className="badge-green ml-auto flex-shrink-0">{mappedCount}/{cols.length} Mapped</span>
      </div>

      {/* Error */}
      {wizard.error && (
        <div className="flex items-center gap-2 p-3 rounded-lg bg-red-500/10 border border-red-500/20 text-xs text-red-400">
          <AlertCircle size={13} className="flex-shrink-0" />
          {wizard.error}
        </div>
      )}

      {/* Columns grouped */}
      <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
        {GROUPS.map(group => {
          const groupCols = cols.filter(c => c.target && c.target.startsWith(group.prefix));
          return (
            <div key={group.label} className="card overflow-hidden">
              <div className="px-4 py-2.5 bg-slate-800/60 border-b border-slate-800 flex items-center justify-between">
                <span className="text-xs font-semibold text-slate-300">{group.label}</span>
                <span className="badge-green text-[10px]">{groupCols.length} fields</span>
              </div>
              <div className="divide-y divide-slate-800/50">
                {groupCols.map(col => (
                  <div key={col.source} className="flex items-center gap-2 px-4 py-2.5">
                    <div className="flex-1 min-w-0">
                      <div className="text-xs font-medium text-amber-400 truncate">{col.source}</div>
                    </div>
                    <div className="flex-shrink-0 flex items-center gap-1.5">
                      <div className="w-4 h-px bg-slate-600" />
                      <ArrowRight size={11} className="text-slate-600" />
                    </div>
                    <div className="flex-1 min-w-0">
                      <div className="text-xs font-mono text-blue-300 truncate">
                        {col.target?.split('.').pop() || col.source}
                      </div>
                    </div>
                    <CheckCircle2 size={13} className="text-emerald-400 flex-shrink-0" />
                  </div>
                ))}
              </div>
            </div>
          );
        })}
      </div>

      {/* JSON-LD note */}
      <div className="p-3 rounded-lg bg-purple-500/8 border border-purple-500/20 text-xs text-slate-400">
        <span className="text-purple-400 font-semibold">JSON-LD Metadata: </span>
        <span className="font-mono">@context: "https://ies.energy/schemas/v1/context.jsonld"</span>
        &nbsp;·&nbsp;
        <span className="font-mono">@type: "ARRPetition"</span>
        &nbsp;·&nbsp;
        <span className="font-mono">financial_year: "2026-27"</span>
      </div>

      <div className="flex justify-between pt-2">
        <button onClick={prevStep} disabled={wizard.loading} className="btn-secondary">
          <ArrowLeft size={15} /> Back
        </button>
        <button onClick={handleNext} disabled={wizard.loading} className="btn-primary">
          {wizard.loading ? (
            <><Loader2 size={15} className="animate-spin" /> Generating…</>
          ) : (
            <>Generate DatasetPayload <ArrowRight size={15} /></>
          )}
        </button>
      </div>
    </div>
  );
}
