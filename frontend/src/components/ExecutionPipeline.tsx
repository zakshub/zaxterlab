import React from 'react';
import { ArrowRight, BookOpen, CheckCircle, Cpu, FileText, Wrench } from 'lucide-react';

interface ExecutionPipelineProps {
  currentPhase: string;
}

export const ExecutionPipeline: React.FC<ExecutionPipelineProps> = ({ currentPhase }) => {
  const stages = [
    { id: 'READ', label: '1. Read', icon: BookOpen, desc: 'Context & Workspace' },
    { id: 'PLAN', label: '2. Plan', icon: Cpu, desc: 'Model Reasoning' },
    { id: 'TOOL_CALL', label: '3. Tool Call', icon: Wrench, desc: 'Sandboxed Tools' },
    { id: 'EVALUATE', label: '4. Evaluate', icon: CheckCircle, desc: 'Acceptance QC' },
    { id: 'LOG', label: '5. Log', icon: FileText, desc: 'SQLite Persistence' },
  ];

  return (
    <div className="w-full p-3 bg-[#0a101d] border border-[#172238] rounded-xl flex items-center justify-between">
      {stages.map((stage, idx) => {
        const Icon = stage.icon;
        const isActive = currentPhase === stage.id;
        const isPast = ['READ', 'PLAN', 'TOOL_CALL', 'EVALUATE', 'LOG'].indexOf(currentPhase) > idx;

        let borderClass = 'border-[#1b2842]';
        let bgClass = 'bg-[#0e1628]';
        let textClass = 'text-slate-400';
        let iconClass = 'text-slate-400';

        if (isActive) {
          borderClass = 'border-cyan-500 shadow-md shadow-cyan-500/20';
          bgClass = 'bg-cyan-950/40';
          textClass = 'text-cyan-300 font-semibold';
          iconClass = 'text-cyan-400 animate-pulse';
        } else if (isPast) {
          borderClass = 'border-emerald-500/40';
          bgClass = 'bg-emerald-950/20';
          textClass = 'text-emerald-300';
          iconClass = 'text-emerald-400';
        }

        return (
          <React.Fragment key={stage.id}>
            <div
              className={`flex-1 flex items-center space-x-2.5 px-3 py-2 rounded-lg border transition-all ${borderClass} ${bgClass}`}
            >
              <div className="p-1.5 rounded-md bg-[#070b14] border border-[#1d2b48]">
                <Icon className={`w-3.5 h-3.5 ${iconClass}`} />
              </div>
              <div className="min-w-0">
                <div className={`text-xs font-mono truncate ${textClass}`}>{stage.label}</div>
                <div className="text-[10px] text-slate-400 truncate">{stage.desc}</div>
              </div>
            </div>

            {idx < stages.length - 1 && (
              <ArrowRight className="w-3.5 h-3.5 text-slate-600 mx-1 flex-shrink-0" />
            )}
          </React.Fragment>
        );
      })}
    </div>
  );
};
