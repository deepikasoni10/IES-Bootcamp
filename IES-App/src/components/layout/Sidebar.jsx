import { NavLink } from 'react-router-dom';
import {
  LayoutDashboard, FileText, History, Settings,
  Zap, ChevronLeft, ChevronRight, Shield, Globe
} from 'lucide-react';
import { useAppStore, useFilingStore } from '../../store/filingStore';

const NAV = [
  { to: '/',        Icon: LayoutDashboard, label: 'Dashboard' },
  { to: '/history', Icon: History,         label: 'My Filings' },
  { to: '/settings',Icon: Settings,        label: 'Settings' },
];

export default function Sidebar() {
  const { sidebarOpen, toggleSidebar, user } = useAppStore();
  const { startWizard } = useFilingStore();

  return (
    <aside className={`flex flex-col h-screen bg-surface-800 border-r border-slate-800 transition-all duration-300 z-20 ${sidebarOpen ? 'w-60' : 'w-16'}`}>

      {/* Logo */}
      <div className="flex items-center gap-3 px-4 py-5 border-b border-slate-800">
        <div className="w-8 h-8 rounded-lg bg-gradient-to-br from-blue-500 to-violet-600 flex items-center justify-center flex-shrink-0">
          <Zap size={16} className="text-white" />
        </div>
        {sidebarOpen && (
          <div className="animate-fade-in overflow-hidden">
            <div className="font-bold text-sm text-white leading-tight">IES Platform</div>
            <div className="text-[10px] text-slate-500 leading-tight">Regulatory Exchange</div>
          </div>
        )}
      </div>

      {/* New Filing Button */}
      <div className="p-3 border-b border-slate-800">
        <button
          onClick={startWizard}
          className={`w-full flex items-center gap-2 bg-blue-600 hover:bg-blue-500 text-white font-semibold rounded-lg transition-all duration-200 ${sidebarOpen ? 'px-3 py-2.5 text-sm' : 'p-2.5 justify-center'}`}
        >
          <FileText size={16} />
          {sidebarOpen && <span>New Filing</span>}
        </button>
      </div>

      {/* Nav */}
      <nav className="flex-1 p-3 space-y-1">
        {NAV.map(({ to, Icon, label }) => (
          <NavLink
            key={to}
            to={to}
            end={to === '/'}
            className={({ isActive }) =>
              `flex items-center gap-3 px-3 py-2.5 rounded-lg text-sm font-medium transition-all duration-200 ${
                isActive
                  ? 'bg-blue-600/20 text-blue-400 border border-blue-500/25'
                  : 'text-slate-400 hover:text-slate-200 hover:bg-slate-800/60'
              } ${!sidebarOpen ? 'justify-center' : ''}`
            }
          >
            <Icon size={17} />
            {sidebarOpen && <span>{label}</span>}
          </NavLink>
        ))}

        {sidebarOpen && (
          <div className="pt-4">
            <p className="text-[10px] text-slate-600 font-semibold tracking-widest uppercase px-3 mb-2">Status</p>
            <div className="space-y-1.5">
              <div className="flex items-center gap-2 px-3 py-1.5 text-xs text-slate-500">
                <Shield size={12} className="text-emerald-400" />
                <span>VC Active</span>
                <span className="ml-auto w-1.5 h-1.5 rounded-full bg-emerald-400 animate-pulse"></span>
              </div>
              <div className="flex items-center gap-2 px-3 py-1.5 text-xs text-slate-500">
                <Globe size={12} className="text-blue-400" />
                <span>ONIX Connected</span>
                <span className="ml-auto w-1.5 h-1.5 rounded-full bg-blue-400 animate-pulse"></span>
              </div>
            </div>
          </div>
        )}
      </nav>

      {/* User + Collapse */}
      <div className="border-t border-slate-800">
        {sidebarOpen && (
          <div className="flex items-center gap-3 px-4 py-3">
            <div className="w-8 h-8 rounded-full bg-gradient-to-br from-blue-500 to-purple-600 flex items-center justify-center text-xs font-bold text-white flex-shrink-0">
              {user.avatar}
            </div>
            <div className="overflow-hidden">
              <div className="text-sm font-semibold text-slate-200 truncate">{user.name}</div>
              <div className="text-xs text-slate-500 truncate">{user.role} · {user.discom}</div>
            </div>
          </div>
        )}
        <button
          onClick={toggleSidebar}
          className="w-full flex items-center justify-center gap-2 py-3 text-slate-500 hover:text-slate-300 hover:bg-slate-800/50 transition-colors text-xs border-t border-slate-800"
        >
          {sidebarOpen ? <><ChevronLeft size={14} /><span>Collapse</span></> : <ChevronRight size={14} />}
        </button>
      </div>
    </aside>
  );
}
