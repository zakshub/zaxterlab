import React from 'react';
import { Bot, Check, Shield, Terminal, Wrench } from 'lucide-react';
import { WorkerInfo } from '../types/api';

interface WorkerCardProps {
  worker: WorkerInfo | null;
  status: string;
  currentTaskTitle?: string;
}

export const WorkerCard: React.FC<WorkerCardProps> = ({ worker, status, currentTaskTitle }) => {
  const isSuspended = status === 'SUSPENDED';
  const isBlocked = status === 'BLOCKED';
  const isRunning = status === 'RUNNING';

  let statusBadge = (
    <span className="px-2 py-0.5 rounded text-[10px] font-mono font-bold bg-slate-800 text-slate-300 border border-slate-700">
      IDLE
    </span>
  );

  if (isRunning) {
    statusBadge = (
      <span className="px-2 py-0.5 rounded text-[10px] font-mono font-bold bg-cyan-950 text-cyan-300 border border-cyan-700 animate-pulse">
        RUNNING
      </span>
    );
  } else if (isSuspended) {
    statusBadge = (
      <span className="px-2 py-0.5 rounded text-[10px] font-mono font-bold bg-amber-950 text-amber-300 border border-amber-700">
        SUSPENDED
      </span>
    );
  } else if (isBlocked) {
    statusBadge = (
      <span className="px-2 py-0.5 rounded text-[10px] font-mono font-bold bg-rose-950 text-rose-300 border border-rose-700">
        BLOCKED
      </span>
    );
  } else if (status === 'COMPLETED') {
    statusBadge = (
      <span className="px-2 py-0.5 rounded text-[10px] font-mono font-bold bg-emerald-950 text-emerald-300 border border-emerald-700">
        READY
      </span>
    );
  }

  return (
    <div className="p-4 bg-[#0a101d] border border-[#172238] rounded-xl flex flex-col justify-between">
      {/* Header */}
      <div>
        <div className="flex items-center justify-between mb-3">
          <div className="flex items-center space-x-2.5">
            <div className="w-8 h-8 rounded-lg bg-gradient-to-tr from-cyan-600 to-blue-700 flex items-center justify-center text-white shadow-md shadow-cyan-500/20">
              <Bot className="w-4 h-4" />
            </div>
            <div>
              <div className="text-sm font-bold text-slate-100 flex items-center space-x-2">
                <span>{worker?.name || 'Reem'}</span>
                <span className="text-[10px] font-mono text-cyan-400 px-1.5 py-0.2 rounded bg-cyan-950/80 border border-cyan-800">
                  Worker 1
                </span>
              </div>
              <div className="text-[11px] text-slate-400 font-mono">
                {worker?.role || 'Construction & Programming'}
              </div>
            </div>
          </div>
          {statusBadge}
        </div>

        {/* Current Task Description */}
        <div className="p-2.5 rounded-lg bg-[#0e1628] border border-[#1d2a45] mb-3">
          <div className="text-[10px] font-mono text-slate-400 uppercase tracking-wider mb-1">Assigned Workload</div>
          <div className="text-xs text-slate-200 font-medium line-clamp-2">
            {currentTaskTitle || 'No active task. Worker ready for assignment.'}
          </div>
        </div>

        {/* Allowed Tool Whitelist */}
        <div className="space-y-1.5">
          <div className="text-[10px] font-mono text-slate-400 uppercase tracking-wider flex items-center space-x-1">
            <Wrench className="w-3 h-3 text-cyan-400" />
            <span>Authorized Tool Matrix</span>
          </div>
          <div className="flex flex-wrap gap-1.5">
            {(worker?.allowed_tools || ['read_file', 'write_file', 'list_dir', 'run_command']).map((tool) => (
              <span
                key={tool}
                className="px-2 py-0.5 rounded text-[10px] font-mono bg-[#0e1628] text-slate-300 border border-[#1e2c4a] flex items-center space-x-1"
              >
                <Check className="w-2.5 h-2.5 text-cyan-400" />
                <span>{tool}</span>
              </span>
            ))}
          </div>
        </div>
      </div>

      {/* Security Tag */}
      <div className="mt-4 pt-3 border-t border-[#172238] flex items-center justify-between text-[10px] font-mono text-slate-400">
        <span className="flex items-center space-x-1">
          <Shield className="w-3 h-3 text-emerald-400" />
          <span>Tier 2 (Reversible)</span>
        </span>
        <span>Max Iterations: {worker?.max_iterations || 10}</span>
      </div>
    </div>
  );
};
