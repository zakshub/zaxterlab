import React from 'react';
import { Database, PlusCircle, RefreshCw, ShieldCheck, Wifi, WifiOff } from 'lucide-react';
import { ClientMode } from '../services/apiClient';
import { SystemHealth } from '../types/api';

interface HeaderProps {
  mode: ClientMode;
  onModeToggle: (newMode: ClientMode) => void;
  health: SystemHealth | null;
  onRefresh: () => void;
  onOpenNewTaskModal: () => void;
  isLoading: boolean;
}

export const Header: React.FC<HeaderProps> = ({
  mode,
  onModeToggle,
  health,
  onRefresh,
  onOpenNewTaskModal,
  isLoading,
}) => {
  const isLive = mode === 'live';
  const isHealthy = health?.status === 'healthy';

  return (
    <header className="h-16 px-6 bg-[#080d1a]/90 backdrop-blur-md border-b border-[#1a2742] flex items-center justify-between z-20">
      {/* Left: Mode switcher and environment status */}
      <div className="flex items-center space-x-4">
        {/* Mode Toggle Button */}
        <div className="flex items-center p-1 rounded-lg bg-[#0c1424] border border-[#1d2b49]">
          <button
            onClick={() => onModeToggle('demo')}
            className={`px-3 py-1 rounded text-xs font-mono font-medium transition-all ${
              !isLive
                ? 'bg-amber-500/20 text-amber-300 border border-amber-500/40 shadow-sm'
                : 'text-slate-400 hover:text-slate-200'
            }`}
          >
            DEMO MODE
          </button>
          <button
            onClick={() => onModeToggle('live')}
            className={`px-3 py-1 rounded text-xs font-mono font-medium transition-all ${
              isLive
                ? 'bg-emerald-500/20 text-emerald-300 border border-emerald-500/40 shadow-sm'
                : 'text-slate-400 hover:text-slate-200'
            }`}
          >
            LIVE BACKEND
          </button>
        </div>

        {/* Live Status indicator */}
        <div className="flex items-center space-x-2 text-xs font-mono px-3 py-1 rounded-md bg-[#0c1424] border border-[#1d2b49]">
          {isHealthy ? (
            <>
              <span className="w-2 h-2 rounded-full bg-emerald-400 animate-pulse" />
              <span className="text-slate-300">{isLive ? 'Backend Online (127.0.0.1:8000)' : 'Mock Engine Online'}</span>
            </>
          ) : (
            <>
              <span className="w-2 h-2 rounded-full bg-rose-400" />
              <span className="text-rose-300">Offline / Standby</span>
            </>
          )}
        </div>
      </div>

      {/* Right Controls */}
      <div className="flex items-center space-x-3">
        {/* Spend Boundary Guard Badge */}
        <div className="flex items-center space-x-2 px-3 py-1.5 rounded-lg bg-[#0c1424] border border-cyan-500/30 text-xs font-mono">
          <ShieldCheck className="w-4 h-4 text-cyan-400" />
          <span className="text-slate-400">Budget:</span>
          <span className="font-bold text-cyan-300">$0.00</span>
          <span className="text-[10px] text-cyan-500 font-semibold px-1 py-0.2 rounded bg-cyan-950">ENFORCED</span>
        </div>

        {/* Refresh Button */}
        <button
          onClick={onRefresh}
          disabled={isLoading}
          className="p-2 rounded-lg bg-[#0c1424] border border-[#1d2b49] text-slate-300 hover:text-cyan-300 hover:border-cyan-500/40 transition-all disabled:opacity-50"
          title="Refresh State"
        >
          <RefreshCw className={`w-4 h-4 ${isLoading ? 'animate-spin text-cyan-400' : ''}`} />
        </button>

        {/* Submit Task Button */}
        <button
          onClick={onOpenNewTaskModal}
          className="flex items-center space-x-2 px-4 py-2 rounded-lg bg-gradient-to-r from-cyan-500 to-blue-600 hover:from-cyan-400 hover:to-blue-500 text-slate-950 font-semibold text-xs transition-all shadow-lg shadow-cyan-500/20 active:scale-95"
        >
          <PlusCircle className="w-4 h-4 text-slate-950" />
          <span>New Task</span>
        </button>
      </div>
    </header>
  );
};
