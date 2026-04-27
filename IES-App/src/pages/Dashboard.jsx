import { useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import {
  FileText, CheckCircle2, Clock, AlertTriangle, TrendingUp,
  ArrowRight, Plus, Eye, Hash, Shield, Activity
} from 'lucide-react';
import { BarChart, Bar, XAxis, YAxis, Tooltip, ResponsiveContainer, CartesianGrid } from 'recharts';
import Header from '../components/layout/Header';
import StatusBadge from '../components/ui/StatusBadge';
import { useFilingStore } from '../store/filingStore';
import { MONTHLY_FILING_STATS, DISCOM_INFO } from '../data/mockData';

function StatCard({ icon: Icon, label, value, sub, color, glow }) {
  const colors = {
    blue:   'from-blue-500/20 to-blue-600/5 border-blue-500/20 text-blue-400',
    green:  'from-emerald-500/20 to-emerald-600/5 border-emerald-500/20 text-emerald-400',
    yellow: 'from-amber-500/20 to-amber-600/5 border-amber-500/20 text-amber-400',
    purple: 'from-purple-500/20 to-purple-600/5 border-purple-500/20 text-purple-400',
  };
  return (
    <div className={`card card-hover p-5 bg-gradient-to-br ${colors[color]} animate-slide-up`}>
      <div className="flex items-start justify-between mb-4">
        <div className={`w-10 h-10 rounded-xl flex items-center justify-center ${color === 'blue' ? 'bg-blue-500/15' : color === 'green' ? 'bg-emerald-500/15' : color === 'yellow' ? 'bg-amber-500/15' : 'bg-purple-500/15'}`}>
          <Icon size={18} className={colors[color].split(' ')[2]} />
        </div>
        <TrendingUp size={14} className="text-slate-600" />
      </div>
      <div className="text-2xl font-bold text-slate-100 mb-1">{value}</div>
      <div className="text-sm text-slate-400">{label}</div>
      {sub && <div className="text-xs text-slate-600 mt-1">{sub}</div>}
    </div>
  );
}

const CustomTooltip = ({ active, payload, label }) => {
  if (!active || !payload?.length) return null;
  return (
    <div className="card px-3 py-2 text-xs">
      <p className="text-slate-400">{label}</p>
      <p className="text-blue-400 font-semibold">{payload[0].value} filings</p>
    </div>
  );
};

export default function Dashboard() {
  const navigate = useNavigate();
  const { filings, startWizard, loadFilings } = useFilingStore();

  useEffect(() => { loadFilings(); }, []); // eslint-disable-line react-hooks/exhaustive-deps

  const stats = {
    total: filings.length,
    accepted: filings.filter(f => ['accepted', 'disclosed'].includes(f.status)).length,
    pending: filings.filter(f => ['draft_submitted', 'draft_validated', 'formally_submitted'].includes(f.status)).length,
    rejected: filings.filter(f => f.status === 'rejected').length,
  };

  const recent = filings.slice(0, 3);

  return (
    <div className="animate-fade-in">
      <Header
        title="Dashboard"
        subtitle={`${DISCOM_INFO.name} · ${DISCOM_INFO.jurisdiction}`}
      />

      <div className="p-6 space-y-6">

        {/* DISCOM Info Banner */}
        <div className="card p-4 flex items-center gap-4 border-blue-500/15 bg-gradient-to-r from-blue-500/8 to-transparent">
          <div className="w-10 h-10 rounded-xl bg-blue-500/15 flex items-center justify-center flex-shrink-0">
            <Shield size={18} className="text-blue-400" />
          </div>
          <div className="flex-1">
            <div className="flex items-center gap-2 flex-wrap">
              <span className="text-sm font-semibold text-slate-200">{DISCOM_INFO.name}</span>
              <span className="badge-blue text-[10px]">VC Active</span>
              <span className="badge-green text-[10px]">ONIX Connected</span>
            </div>
            <div className="text-xs text-slate-500 mt-0.5">
              DID: <span className="font-mono text-slate-400">{DISCOM_INFO.did}</span>
              &nbsp;·&nbsp; License: {DISCOM_INFO.licenseNumber}
            </div>
          </div>
          <button onClick={startWizard} className="btn-primary text-sm whitespace-nowrap">
            <Plus size={15} /> New Filing
          </button>
        </div>

        {/* Stats */}
        <div className="grid grid-cols-2 lg:grid-cols-4 gap-4">
          <StatCard icon={FileText}     label="Total Filings"     value={stats.total}    color="blue"   />
          <StatCard icon={CheckCircle2} label="Accepted"          value={stats.accepted} color="green"  sub="Incl. disclosed" />
          <StatCard icon={Clock}        label="In Progress"       value={stats.pending}  color="yellow" />
          <StatCard icon={AlertTriangle}label="Rejected"          value={stats.rejected} color="purple" />
        </div>

        {/* Charts + Recent */}
        <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">

          {/* Chart */}
          <div className="card p-5 lg:col-span-2">
            <div className="flex items-center justify-between mb-4">
              <div>
                <h3 className="text-sm font-semibold text-slate-200">Filing Activity</h3>
                <p className="text-xs text-slate-500 mt-0.5">Filings submitted per month</p>
              </div>
              <Activity size={16} className="text-slate-600" />
            </div>
            <ResponsiveContainer width="100%" height={180}>
              <BarChart data={MONTHLY_FILING_STATS} barSize={28}>
                <CartesianGrid strokeDasharray="3 3" stroke="#1c2844" vertical={false} />
                <XAxis dataKey="month" tick={{ fill: '#64748b', fontSize: 11 }} axisLine={false} tickLine={false} />
                <YAxis tick={{ fill: '#64748b', fontSize: 11 }} axisLine={false} tickLine={false} width={24} />
                <Tooltip content={<CustomTooltip />} cursor={{ fill: 'rgba(59,130,246,0.06)' }} />
                <Bar dataKey="filings" fill="#3b82f6" radius={[4, 4, 0, 0]} />
              </BarChart>
            </ResponsiveContainer>
          </div>

          {/* Pipeline */}
          <div className="card p-5">
            <h3 className="text-sm font-semibold text-slate-200 mb-4">Filing Pipeline</h3>
            <div className="space-y-3">
              {[
                { label: 'Disclosed',       count: filings.filter(f => f.status === 'disclosed').length,          color: 'bg-emerald-500' },
                { label: 'Accepted',        count: filings.filter(f => f.status === 'accepted').length,           color: 'bg-blue-500' },
                { label: 'Draft Validated', count: filings.filter(f => f.status === 'draft_validated').length,   color: 'bg-amber-500' },
                { label: 'Rejected',        count: filings.filter(f => f.status === 'rejected').length,           color: 'bg-red-500' },
              ].map(({ label, count, color }) => (
                <div key={label}>
                  <div className="flex items-center justify-between text-xs mb-1">
                    <span className="text-slate-400">{label}</span>
                    <span className="text-slate-300 font-semibold">{count}</span>
                  </div>
                  <div className="h-1.5 bg-slate-800 rounded-full overflow-hidden">
                    <div
                      className={`h-full rounded-full transition-all duration-700 ${color}`}
                      style={{ width: `${(count / stats.total) * 100}%` }}
                    />
                  </div>
                </div>
              ))}
            </div>

            {/* Hash integrity */}
            <div className="mt-5 pt-4 border-t border-slate-800">
              <div className="flex items-center gap-2 text-xs text-slate-500 mb-2">
                <Hash size={12} className="text-slate-600" />
                <span>Latest Payload Hash</span>
              </div>
              <div className="font-mono text-[10px] text-emerald-400 break-all leading-relaxed">
                {filings[0]?.payloadHash}
              </div>
            </div>
          </div>
        </div>

        {/* Recent Filings */}
        <div className="card overflow-hidden">
          <div className="flex items-center justify-between px-5 py-4 border-b border-slate-800">
            <h3 className="text-sm font-semibold text-slate-200">Recent Filings</h3>
            <button onClick={() => navigate('/history')} className="btn-ghost text-xs py-1.5 px-2">
              View all <ArrowRight size={13} />
            </button>
          </div>
          <div className="divide-y divide-slate-800">
            {recent.map(filing => (
              <div
                key={filing.id}
                onClick={() => navigate(`/filing/${filing.id}`)}
                className="flex items-center gap-4 px-5 py-4 hover:bg-slate-800/40 cursor-pointer transition-colors group"
              >
                <div className="w-9 h-9 rounded-lg bg-surface-600 flex items-center justify-center flex-shrink-0">
                  <FileText size={15} className="text-slate-400" />
                </div>
                <div className="flex-1 min-w-0">
                  <div className="flex items-center gap-2">
                    <span className="text-sm font-medium text-slate-200 truncate">{filing.title}</span>
                    <StatusBadge status={filing.status} />
                  </div>
                  <div className="text-xs text-slate-500 mt-0.5 font-mono">{filing.id}</div>
                </div>
                <div className="text-right flex-shrink-0">
                  <div className="text-xs text-slate-400">
                    {new Date(filing.filedAt).toLocaleDateString('en-IN', { day: '2-digit', month: 'short', year: 'numeric' })}
                  </div>
                  <div className="text-xs text-slate-600 mt-0.5">FY {filing.financialYear}</div>
                </div>
                <Eye size={15} className="text-slate-700 group-hover:text-slate-400 transition-colors flex-shrink-0" />
              </div>
            ))}
          </div>
        </div>

      </div>
    </div>
  );
}
