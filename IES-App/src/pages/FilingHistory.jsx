import { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import { Search, Filter, FileText, Eye, ArrowUpDown, Plus, Download, Loader2 } from 'lucide-react';
import Header from '../components/layout/Header';
import StatusBadge from '../components/ui/StatusBadge';
import { useFilingStore } from '../store/filingStore';

const STATUS_FILTER = ['all', 'disclosed', 'accepted', 'draft_validated', 'formally_submitted', 'draft_submitted', 'rejected'];

export default function FilingHistory() {
  const navigate = useNavigate();
  const { filings, filingsLoaded, startWizard, loadFilings } = useFilingStore();

  useEffect(() => { loadFilings(); }, []); // eslint-disable-line react-hooks/exhaustive-deps
  const [search, setSearch] = useState('');
  const [statusFilter, setStatusFilter] = useState('all');
  const [sortDesc, setSortDesc] = useState(true);

  const filtered = filings
    .filter(f =>
      (statusFilter === 'all' || f.status === statusFilter) &&
      (f.title.toLowerCase().includes(search.toLowerCase()) ||
       f.id.toLowerCase().includes(search.toLowerCase()) ||
       f.financialYear.includes(search))
    )
    .sort((a, b) => sortDesc
      ? new Date(b.filedAt) - new Date(a.filedAt)
      : new Date(a.filedAt) - new Date(b.filedAt)
    );

  return (
    <div className="animate-fade-in">
      <Header title="My Filings" subtitle="All ARR petition filings and their status" />

      <div className="p-6 space-y-5">

        {/* Toolbar */}
        <div className="flex flex-col sm:flex-row gap-3">
          <div className="relative flex-1">
            <Search size={14} className="absolute left-3 top-1/2 -translate-y-1/2 text-slate-500" />
            <input
              value={search}
              onChange={e => setSearch(e.target.value)}
              className="input pl-9 text-sm"
              placeholder="Search by title, ID, or financial year…"
            />
          </div>
          <div className="flex gap-2">
            <div className="relative">
              <Filter size={14} className="absolute left-3 top-1/2 -translate-y-1/2 text-slate-500" />
              <select
                value={statusFilter}
                onChange={e => setStatusFilter(e.target.value)}
                className="input pl-9 text-sm w-44 appearance-none cursor-pointer"
              >
                {STATUS_FILTER.map(s => (
                  <option key={s} value={s}>{s === 'all' ? 'All Statuses' : s.replace(/_/g, ' ')}</option>
                ))}
              </select>
            </div>
            <button
              onClick={() => setSortDesc(d => !d)}
              className="btn-secondary text-sm gap-1.5"
            >
              <ArrowUpDown size={14} />
              {sortDesc ? 'Newest' : 'Oldest'}
            </button>
            <button onClick={startWizard} className="btn-primary text-sm">
              <Plus size={15} /> New
            </button>
          </div>
        </div>

        {/* Count */}
        <div className="flex items-center justify-between">
          <p className="text-xs text-slate-500">{filtered.length} filing{filtered.length !== 1 ? 's' : ''} found</p>
          <button className="btn-ghost text-xs py-1 px-2">
            <Download size={13} /> Export CSV
          </button>
        </div>

        {/* Table */}
        <div className="card overflow-hidden">
          {/* Header row */}
          <div className="grid grid-cols-12 gap-3 px-5 py-3 bg-slate-800/60 border-b border-slate-800 text-[10px] font-semibold text-slate-500 uppercase tracking-wider">
            <div className="col-span-4">Title / ID</div>
            <div className="col-span-2 text-center">FY</div>
            <div className="col-span-2 text-center">Status</div>
            <div className="col-span-2 text-center">Revenue</div>
            <div className="col-span-1 text-center">Filed</div>
            <div className="col-span-1 text-center">Action</div>
          </div>

          {filtered.length === 0 ? (
            <div className="flex flex-col items-center gap-3 py-16 text-slate-600">
              <FileText size={32} />
              <div className="text-sm">No filings match your filter</div>
              <button onClick={startWizard} className="btn-primary text-sm mt-2">
                <Plus size={15} /> Create First Filing
              </button>
            </div>
          ) : (
            <div className="divide-y divide-slate-800/60">
              {filtered.map(filing => (
                <div
                  key={filing.id}
                  onClick={() => navigate(`/filing/${encodeURIComponent(filing.id)}`)}
                  className="grid grid-cols-12 gap-3 px-5 py-4 hover:bg-slate-800/40 cursor-pointer transition-colors group items-center"
                >
                  {/* Title + ID */}
                  <div className="col-span-4 min-w-0">
                    <div className="flex items-center gap-2">
                      <div className="w-7 h-7 rounded-lg bg-surface-600 flex items-center justify-center flex-shrink-0">
                        <FileText size={13} className="text-slate-400" />
                      </div>
                      <div className="min-w-0">
                        <div className="text-sm font-medium text-slate-200 truncate group-hover:text-blue-300 transition-colors">
                          {filing.title}
                        </div>
                        <div className="text-[10px] font-mono text-slate-600 truncate">{filing.id}</div>
                      </div>
                    </div>
                  </div>

                  {/* FY */}
                  <div className="col-span-2 text-center">
                    <span className="text-xs font-mono text-slate-400">{filing.financialYear}</span>
                  </div>

                  {/* Status */}
                  <div className="col-span-2 flex justify-center">
                    <StatusBadge status={filing.status} />
                  </div>

                  {/* Revenue */}
                  <div className="col-span-2 text-center">
                    <span className="text-xs text-slate-300 font-semibold">
                      ₹{(filing.totalRevenue / 1000).toFixed(1)}K Cr
                    </span>
                  </div>

                  {/* Filed date */}
                  <div className="col-span-1 text-center">
                    <span className="text-xs text-slate-500">
                      {new Date(filing.filedAt).toLocaleDateString('en-IN', { day: '2-digit', month: 'short' })}
                    </span>
                  </div>

                  {/* Action */}
                  <div className="col-span-1 flex justify-center">
                    <Eye size={15} className="text-slate-700 group-hover:text-blue-400 transition-colors" />
                  </div>
                </div>
              ))}
            </div>
          )}
        </div>

        {/* Observations summary */}
        {filtered.some(f => f.observations?.length > 0) && (
          <div className="card p-4">
            <p className="text-xs font-semibold text-slate-400 mb-3">Open Observations</p>
            <div className="space-y-2">
              {filtered
                .filter(f => f.observations?.length > 0)
                .flatMap(f => f.observations.map(o => ({ ...o, filingId: f.id })))
                .map((o, i) => (
                  <div key={i} className="flex items-start gap-2.5 text-xs">
                    <span className={o.severity === 'warning' ? 'badge-yellow' : o.severity === 'error' ? 'badge-red' : 'badge-blue'}>
                      {o.severity}
                    </span>
                    <span className="font-mono text-slate-500">{o.filingId}</span>
                    <span className="text-slate-400">{o.message}</span>
                  </div>
                ))}
            </div>
          </div>
        )}

      </div>
    </div>
  );
}
