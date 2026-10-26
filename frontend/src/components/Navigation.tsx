import React from 'react';
import {
  Activity,
  CheckSquare,
  Cpu,
  Database,
  FileCode,
  HardDrive,
  Home,
  Layers,
  Settings,
  ShieldAlert,
} from 'lucide-react';

export type NavTab = 'home' | 'tasks' | 'sessions' | 'agents' | 'workspace' | 'logs' | 'settings';

interface NavigationProps {
  activeTab: NavTab;
  onTabChange: (tab: NavTab) => void;
  taskCount: number;
}

export const Navigation: React.FC<NavigationProps> = ({ activeTab, onTabChange, taskCount }) => {
  const navItems = [
    { id: 'home', label: 'Overview', icon: Home },
    { id: 'tasks', label: 'Tasks', icon: CheckSquare, badge: taskCount },
    { id: 'sessions', label: 'Sessions', icon: Layers },
    { id: 'agents', label: 'Agents (1 Active)', icon: Cpu },
    { id: 'workspace', label: 'Workspace', icon: HardDrive },
    { id: 'logs', label: 'Audit Logs', icon: FileCode },
    { id: 'settings', label: 'Settings', icon: Settings },
  ];

  return (
    <aside className="w-64 h-full bg-[#080d1a] border-r border-[#1a2742] flex flex-col justify-between select-none">
      <div>
        {/* Brand Header */}
        <div className="p-4 border-b border-[#1a2742] flex items-center space-x-3">
          <div className="w-9 h-9 rounded-lg bg-gradient-to-tr from-cyan-500 to-blue-600 flex items-center justify-center shadow-lg shadow-cyan-500/20">
            <Activity className="w-5 h-5 text-white animate-pulse" />
          </div>
          <div>
            <h1 className="text-base font-bold tracking-wider text-slate-100 flex items-center space-x-1.5">
              <span>ZAXTERLAB</span>
              <span className="text-[10px] font-mono px-1.5 py-0.5 rounded bg-cyan-950 text-cyan-400 border border-cyan-800">
                v0.1.0
              </span>
            </h1>
            <p className="text-[11px] font-mono text-slate-400 tracking-tight">Adaptive AI Company OS</p>
          </div>
        </div>

        {/* Navigation Items */}
        <nav className="p-3 space-y-1">
          {navItems.map((item) => {
            const Icon = item.icon;
            const isActive = activeTab === item.id;
            return (
              <button
                key={item.id}
                onClick={() => onTabChange(item.id as NavTab)}
                className={`w-full flex items-center justify-between px-3 py-2.5 rounded-lg text-xs font-medium transition-all ${
                  isActive
                    ? 'bg-gradient-to-r from-cyan-500/20 to-blue-500/10 text-cyan-300 border border-cyan-500/30 shadow-sm'
                    : 'text-slate-400 hover:text-slate-200 hover:bg-[#0e1628]'
                }`}
              >
                <div className="flex items-center space-x-3">
                  <Icon className={`w-4 h-4 ${isActive ? 'text-cyan-400' : 'text-slate-400'}`} />
                  <span>{item.label}</span>
                </div>
                {item.badge !== undefined && item.badge > 0 && (
                  <span className="px-1.5 py-0.2 rounded-full text-[10px] font-mono bg-cyan-950 text-cyan-400 border border-cyan-800">
                    {item.badge}
                  </span>
                )}
              </button>
            );
          })}
        </nav>
      </div>

      {/* Spend Boundary Footer */}
      <div className="p-3 m-3 rounded-lg bg-[#0c1322] border border-[#1c2a47]">
        <div className="flex items-center justify-between mb-1.5">
          <span className="text-[11px] font-mono font-medium text-slate-400 flex items-center space-x-1">
            <ShieldAlert className="w-3.5 h-3.5 text-emerald-400" />
            <span>Spend Guard</span>
          </span>
          <span className="text-[10px] font-mono font-bold text-emerald-400 px-1.5 py-0.5 rounded bg-emerald-950/80 border border-emerald-800">
            LOCKED
          </span>
        </div>
        <div className="text-base font-mono font-bold text-slate-100">$0.00 <span className="text-xs font-normal text-slate-500">USD</span></div>
        <p className="text-[10px] text-slate-400 mt-1 leading-tight">
          Hard invariant: zero authorized spend. Paid integrations disabled.
        </p>
      </div>
    </aside>
  );
};
