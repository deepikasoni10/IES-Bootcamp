import { useCallback, useState } from 'react';
import { useDropzone } from 'react-dropzone';
import { Upload, FileSpreadsheet, CheckCircle2, ArrowRight, Loader2, AlertCircle } from 'lucide-react';
import { useFilingStore } from '../../../store/filingStore';

const SAMPLE_PREVIEW_HEADERS = ['Financial Year', 'Total Revenue (Rs Cr)', 'Power Purchase Cost', 'O&M Expenses', 'Peak Demand (MW)'];
const SAMPLE_PREVIEW_ROWS = [
  { 'Financial Year': '2026-27', 'Total Revenue (Rs Cr)': '48250.5', 'Power Purchase Cost': '31200.0', 'O&M Expenses': '4800.0', 'Peak Demand (MW)': '24500' },
  { 'Financial Year': '2025-26', 'Total Revenue (Rs Cr)': '45100.0', 'Power Purchase Cost': '29800.0', 'O&M Expenses': '4500.0', 'Peak Demand (MW)': '22100' },
];

export default function Step1Upload() {
  const { wizard, uploadFile, useSample, nextStep } = useFilingStore();
  const [localFile, setLocalFile] = useState(null);

  const onDrop = useCallback((files) => {
    if (files[0]) { setLocalFile(files[0]); }
  }, []);

  const { getRootProps, getInputProps, isDragActive } = useDropzone({
    onDrop,
    accept: {
      'text/csv': ['.csv'],
      'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet': ['.xlsx'],
      'application/vnd.ms-excel': ['.xls'],
    },
    maxFiles: 1,
  });

  const displayFile = wizard.uploadedFile || localFile;
  const canContinue = !!(wizard.isSample || wizard.uploadId || localFile);

  const handleUseSample = () => { useSample(); setLocalFile(null); };

  const handleContinue = async () => {
    if (wizard.isSample)   { nextStep(); return; }
    if (wizard.uploadId && !localFile) { nextStep(); return; } // already uploaded this session
    if (!localFile)        return;
    try {
      await uploadFile(localFile);
      nextStep();
    } catch { /* error shown in wizard.error */ }
  };

  // Preview: real rows from backend, or sample fallback
  const previewCols = wizard.preview?.columns || SAMPLE_PREVIEW_HEADERS;
  const previewRows = wizard.preview?.rows    || SAMPLE_PREVIEW_ROWS;
  const totalRows   = wizard.preview?.totalRows ?? '—';
  const totalCols   = wizard.preview?.columns?.length ?? 17;

  return (
    <div className="max-w-2xl mx-auto space-y-6">
      <div>
        <h3 className="text-base font-bold text-slate-100">Upload DISCOM Data File</h3>
        <p className="text-sm text-slate-500 mt-1">
          Upload your ARR data in CSV or Excel format. The system will automatically map columns
          to IES DatasetPayload schema.
        </p>
      </div>

      {/* Drop zone */}
      <div
        {...getRootProps()}
        className={`border-2 border-dashed rounded-xl p-10 text-center cursor-pointer transition-all duration-200 ${
          isDragActive
            ? 'border-blue-500 bg-blue-500/10'
            : displayFile
            ? 'border-emerald-500/50 bg-emerald-500/5'
            : 'border-slate-700 hover:border-slate-500 hover:bg-slate-800/40'
        }`}
      >
        <input {...getInputProps()} />
        {displayFile ? (
          <div className="flex flex-col items-center gap-3">
            <div className="w-14 h-14 rounded-2xl bg-emerald-500/15 flex items-center justify-center">
              <CheckCircle2 size={28} className="text-emerald-400" />
            </div>
            <div>
              <p className="text-sm font-semibold text-emerald-400">{displayFile.name}</p>
              <p className="text-xs text-slate-500 mt-1">
                {displayFile.isSample
                  ? 'Sample file — pre-loaded'
                  : `${(displayFile.size / 1024).toFixed(1)} KB`}
                &nbsp;· Click to change
              </p>
              {wizard.uploadId && !wizard.isSample && (
                <p className="text-xs text-emerald-600 mt-1 font-mono">
                  upload_id: {wizard.uploadId.slice(0, 8)}…
                </p>
              )}
            </div>
          </div>
        ) : (
          <div className="flex flex-col items-center gap-3">
            <div className="w-14 h-14 rounded-2xl bg-slate-800 flex items-center justify-center">
              <Upload size={24} className="text-slate-500" />
            </div>
            <div>
              <p className="text-sm font-semibold text-slate-300">
                {isDragActive ? 'Drop file here…' : 'Drag & drop your file'}
              </p>
              <p className="text-xs text-slate-500 mt-1">Supports .csv, .xlsx, .xls</p>
            </div>
            <span className="text-xs text-slate-600">or click to browse</span>
          </div>
        )}
      </div>

      {/* Error */}
      {wizard.error && (
        <div className="flex items-center gap-2 p-3 rounded-lg bg-red-500/10 border border-red-500/20 text-xs text-red-400">
          <AlertCircle size={13} className="flex-shrink-0" />
          {wizard.error}
        </div>
      )}

      {/* Sample divider */}
      {!displayFile && (
        <>
          <div className="flex items-center gap-3">
            <div className="flex-1 h-px bg-slate-800" />
            <span className="text-xs text-slate-600">or use sample data</span>
            <div className="flex-1 h-px bg-slate-800" />
          </div>
          <button onClick={handleUseSample} className="w-full flex items-center gap-3 p-4 card card-hover border-dashed">
            <FileSpreadsheet size={20} className="text-emerald-400 flex-shrink-0" />
            <div className="text-left flex-1">
              <div className="text-sm font-medium text-slate-200">msedcl_arr_2026-27.xlsx</div>
              <div className="text-xs text-slate-500">Sample ARR data — Maharashtra DISCOM · FY 2026-27</div>
            </div>
            <ArrowRight size={14} className="text-slate-600" />
          </button>
        </>
      )}

      {/* Preview table */}
      {displayFile && (
        <div>
          <p className="text-xs font-semibold text-slate-400 uppercase tracking-wider mb-2">Data Preview</p>
          <div className="card overflow-hidden">
            <div className="overflow-x-auto">
              <table className="w-full text-xs">
                <thead>
                  <tr className="border-b border-slate-800 bg-slate-800/50">
                    {previewCols.slice(0, 5).map(h => (
                      <th key={h} className="text-left px-3 py-2 text-slate-400 font-semibold whitespace-nowrap">{h}</th>
                    ))}
                  </tr>
                </thead>
                <tbody>
                  {previewRows.slice(0, 2).map((row, i) => (
                    <tr key={i} className="border-b border-slate-800/50 hover:bg-slate-800/30">
                      {previewCols.slice(0, 5).map((col, j) => (
                        <td key={j} className="px-3 py-2 text-slate-300 whitespace-nowrap font-mono">
                          {row[col] ?? '—'}
                        </td>
                      ))}
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
            <div className="px-3 py-2 bg-slate-800/30 text-xs text-slate-600">
              Showing {Math.min(2, previewRows.length)} of {totalRows} rows · {totalCols} columns detected
            </div>
          </div>
        </div>
      )}

      {/* Format chips */}
      <div className="flex gap-2 text-xs text-slate-600">
        {['CSV', 'XLSX', 'XLS'].map(f => (
          <span key={f} className="px-2 py-0.5 rounded bg-slate-800 text-slate-500">.{f.toLowerCase()}</span>
        ))}
        <span className="ml-auto">Max file size: 50 MB</span>
      </div>

      {/* CTA */}
      <div className="flex justify-end pt-2">
        <button onClick={handleContinue} disabled={!canContinue || wizard.loading} className="btn-primary">
          {wizard.loading ? (
            <><Loader2 size={15} className="animate-spin" /> Uploading…</>
          ) : (
            <>Continue to Schema Mapping <ArrowRight size={15} /></>
          )}
        </button>
      </div>
    </div>
  );
}
