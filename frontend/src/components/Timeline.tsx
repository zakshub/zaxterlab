import React, { useState } from 'react';
import { ChevronDown, ChevronRight, CheckCircle2, AlertTriangle, Code, Terminal, Clock, Coins } from 'lucide-react';
import { StepTrace } from '../types/api';

interface TimelineProps {
  traces: StepTrace[];
}

export const Timeline: React.FC<TimelineProps> = ({ traces }) => {
  const [expandedSteps, setExpandedSteps] = useState<Record<number, boolean>>({});

  const toggleStep = (stepNumber: number) => {
    setExpandedSteps((prev) => ({
      ...prev,
      [stepNumber]: !prev[stepNumber],
    }));
  };

  if (!traces || traces.length === 0) {
    return (
      <div className="p-8 text-center text-slate-500 font-mono text-xs rounded-xl bg-[#0a101d] border border-[#172238]">
        No execution step traces recorded yet. Select or execute a task to view the timeline.
      </div>
    );
  }

  return (
    <div className="space-y-3">
      {traces.map((trace) => {
        const isExpanded = expandedSteps[trace.step_number] ?? true;
        const hasTools = trace.tool_calls && trace.tool_calls.length > 0;

        return (
          <div
            key={trace.step_number}
            className="rounded-xl bg-[#0a101d] border border-[#172238] hover:border-cyan-500/30 transition-all overflow-hidden"
          >
            {/* Step Header */}
            <div
              onClick={() => toggleStep(trace.step_number)}
              className="p-3.5 flex items-center justify-between cursor-pointer select-none bg-[#0c1424]/60 hover:bg-[#0e172a]"
            >
              <div className="flex items-center space-x-3">
                <span className="w-6 h-6 rounded-md bg-cyan-950 text-cyan-400 border border-cyan-800 flex items-center justify-center text-xs font-mono font-bold">
                  #{trace.step_number}
                </span>

                <span className="text-xs font-mono font-semibold text-slate-200">
                  Phase: <span className="text-cyan-300">{trace.phase}</span>
                </span>

                {hasTools && (
                  <span className="px-2 py-0.5 rounded text-[10px] font-mono bg-violet-950/80 text-violet-300 border border-violet-800">
                    {trace.tool_calls.length} Tool Invocation{trace.tool_calls.length > 1 ? 's' : ''}
                  </span>
                )}
              </div>

              <div className="flex items-center space-x-3 text-xs font-mono text-slate-400">
                <span className="flex items-center space-x-1">
                  <Coins className="w-3.5 h-3.5 text-cyan-400" />
                  <span>{trace.token_usage?.total_tokens || 0} tokens ($0.00)</span>
                </span>

                <span className="flex items-center space-x-1 text-slate-400">
                  <Clock className="w-3 h-3" />
                  <span>{new Date(trace.created_at).toLocaleTimeString()}</span>
                </span>

                {isExpanded ? (
                  <ChevronDown className="w-4 h-4 text-slate-400" />
                ) : (
                  <ChevronRight className="w-4 h-4 text-slate-400" />
                )}
              </div>
            </div>

            {/* Step Content */}
            {isExpanded && (
              <div className="p-4 space-y-3 border-t border-[#172238] text-xs">
                {/* Observation */}
                <div>
                  <div className="text-[10px] font-mono text-slate-400 uppercase tracking-wider mb-1">
                    Observation
                  </div>
                  <div className="p-2.5 rounded-lg bg-[#070b14] text-slate-300 font-mono text-xs border border-[#141e33] leading-relaxed">
                    {trace.observation}
                  </div>
                </div>

                {/* Plan */}
                {trace.plan && (
                  <div>
                    <div className="text-[10px] font-mono text-slate-400 uppercase tracking-wider mb-1">
                      Reasoning Plan
                    </div>
                    <div className="p-2.5 rounded-lg bg-[#070b14] text-cyan-200/90 font-mono text-xs border border-cyan-950/60 leading-relaxed">
                      {trace.plan}
                    </div>
                  </div>
                )}

                {/* Tool Calls & Results */}
                {hasTools && (
                  <div className="space-y-2">
                    <div className="text-[10px] font-mono text-slate-400 uppercase tracking-wider flex items-center space-x-1">
                      <Terminal className="w-3 h-3 text-violet-400" />
                      <span>Tool Execution Trace</span>
                    </div>

                    {trace.tool_calls.map((tc, idx) => {
                      const res = trace.tool_results?.[idx];
                      const isSuccess = res?.success ?? false;

                      return (
                        <div
                          key={tc.call_id || idx}
                          className="rounded-lg bg-[#070b14] border border-[#1a2640] p-3 space-y-2"
                        >
                          <div className="flex items-center justify-between text-xs font-mono">
                            <span className="font-semibold text-violet-300 flex items-center space-x-1.5">
                              <Code className="w-3.5 h-3.5 text-violet-400" />
                              <span>{tc.tool_name}</span>
                            </span>
                            {res && (
                              <span
                                className={`px-2 py-0.5 rounded text-[10px] flex items-center space-x-1 ${
                                  isSuccess
                                    ? 'bg-emerald-950 text-emerald-300 border border-emerald-800'
                                    : 'bg-rose-950 text-rose-300 border border-rose-800'
                                }`}
                              >
                                {isSuccess ? (
                                  <CheckCircle2 className="w-3 h-3 text-emerald-400" />
                                ) : (
                                  <AlertTriangle className="w-3 h-3 text-rose-400" />
                                )}
                                <span>{isSuccess ? 'SUCCESS' : 'FAILED'}</span>
                              </span>
                            )}
                          </div>

                          {/* Arguments */}
                          <div className="text-[11px] font-mono text-slate-400 bg-[#050811] p-2 rounded border border-[#141e33] overflow-x-auto">
                            <span className="text-slate-400">args:</span> {JSON.stringify(tc.arguments, null, 2)}
                          </div>

                          {/* Output or Error */}
                          {res && (
                            <div className="text-[11px] font-mono bg-[#050811] p-2 rounded border border-[#141e33] overflow-x-auto">
                              {isSuccess ? (
                                <span className="text-emerald-300 whitespace-pre-wrap">{res.output}</span>
                              ) : (
                                <span className="text-rose-400 whitespace-pre-wrap">{res.error}</span>
                              )}
                            </div>
                          )}
                        </div>
                      );
                    })}
                  </div>
                )}

                {/* Evaluation */}
                {trace.evaluation && (
                  <div>
                    <div className="text-[10px] font-mono text-slate-400 uppercase tracking-wider mb-1">
                      Evaluation Outcome
                    </div>
                    <div className="p-2.5 rounded-lg bg-[#070b14] text-emerald-300/90 font-mono text-xs border border-emerald-950/60 leading-relaxed">
                      {trace.evaluation}
                    </div>
                  </div>
                )}
              </div>
            )}
          </div>
        );
      })}
    </div>
  );
};
