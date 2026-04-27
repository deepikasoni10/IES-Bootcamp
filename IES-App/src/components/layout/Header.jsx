import { Bell, HelpCircle, RefreshCw } from 'lucide-react';
import { useAppStore } from '../../store/filingStore';

export default function Header({ title, subtitle }) {
  const { user } = useAppStore();

  return (
    <header className="flex items-center justify-between px-6 py-4 border-b border-slate-800 bg-surface-800/50 backdrop-blur-sm">
      <div>
        <h1 className="text-lg font-bold text-slate-100">{title}</h1>
        {subtitle && <p className="text-xs text-slate-500 mt-0.5">{subtitle}</p>}
      </div>

      <div className="flex items-center gap-2">
        <button className="btn-ghost text-xs py-1.5 px-2.5">
          <RefreshCw size={13} />
          <span className="hidden sm:inline">Refresh</span>
        </button>

        <div className="relative">
          <button className="relative w-8 h-8 flex items-center justify-center rounded-lg text-slate-400 hover:text-slate-200 hover:bg-slate-800 transition-colors">
            <Bell size={16} />
            <span className="absolute top-1.5 right-1.5 w-1.5 h-1.5 rounded-full bg-blue-500"></span>
          </button>
        </div>

        <button className="w-8 h-8 flex items-center justify-center rounded-lg text-slate-400 hover:text-slate-200 hover:bg-slate-800 transition-colors">
          <HelpCircle size={16} />
        </button>

        <div className="w-8 h-8 rounded-full bg-gradient-to-br from-blue-500 to-purple-600 flex items-center justify-center text-xs font-bold text-white ml-1 cursor-pointer">
          {user.avatar}
        </div>
      </div>
    </header>
  );
}
