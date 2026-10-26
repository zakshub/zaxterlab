import React from 'react';
import { Play, Pause, RotateCcw, XCircle } from 'lucide-react';
import { TaskStatus, SessionStatus } from '../types/api';

interface SessionControlsProps {
  taskStatus?: TaskStatus;
  sessionStatus?: SessionStatus;
  onExecute: () => void;
  onSuspend: () => void;
  onResume: () => void;
  onTerminate: () => void;
  isOperating: boolean;
}

export const SessionControls: React.FC<SessionControlsProps> = ({
  taskStatus,
  sessionStatus,
  onExecute,
  onSuspend,
  onResume,
  onTerminate,
  isOperating,
}) => {
  const canExecute = taskStatus === 'SUBMITTED' || taskStatus === 'QUEUED';
  const canSuspend = sessionStatus === 'ACTIVE' || taskStatus === 'RUNNING';
  const canResume = sessionStatus === 'SUSPENDED' || taskStatus === 'SUSPENDED';
  const canTerminate = canSuspend || canResume;

  return (
    <div className="p-3 bg-[#0a101d] border border-[#172238] rounded-xl flex items-center justify-between">
      <div className="flex items-center space-x-2">
        <span className="text-xs font-mono font-medium text-slate-400">Controls:</span>

        {/* Execute Task */}
        <button
          onClick={onExecute}
          disabled={!canExecute || isOperating}
          className="flex items-center space-x-1.5 px-3 py-1.5 rounded-lg bg-cyan-600 hover:bg-cyan-500 disabled:opacity-30 disabled:hover:bg-cyan-600 text-slate-950 font-mono font-semibold text-xs transition-all active:scale-95"
        >
          <Play className="w-3.5 h-3.5 fill-current" />
          <span>Execute</span>
        </button>

        {/* Suspend Session */}
        <button
          onClick={onSuspend}
          disabled={!canSuspend || isOperating}
          className="flex items-center space-x-1.5 px-3 py-1.5 rounded-lg bg-amber-600/20 hover:bg-amber-600/30 border border-amber-600/40 disabled:opacity-30 text-amber-300 font-mono font-semibold text-xs transition-all active:scale-95"
        >
          <Pause className="w-3.5 h-3.5" />
          <span>Suspend</span>
        </button>

        {/* Resume Session */}
        <button
          onClick={onResume}
          disabled={!canResume || isOperating}
          className="flex items-center space-x-1.5 px-3 py-1.5 rounded-lg bg-emerald-600/20 hover:bg-emerald-600/30 border border-emerald-600/40 disabled:opacity-30 text-emerald-300 font-mono font-semibold text-xs transition-all active:scale-95"
        >
          <RotateCcw className="w-3.5 h-3.5" />
          <span>Resume</span>
        </button>
      </div>

      {/* Terminate Session */}
      <button
        onClick={onTerminate}
        disabled={!canTerminate || isOperating}
        className="flex items-center space-x-1.5 px-3 py-1.5 rounded-lg bg-rose-950/30 hover:bg-rose-900/40 border border-rose-800/40 disabled:opacity-30 text-rose-300 font-mono font-semibold text-xs transition-all active:scale-95"
      >
        <XCircle className="w-3.5 h-3.5 text-rose-400" />
        <span>End Session</span>
      </button>
    </div>
  );
};
