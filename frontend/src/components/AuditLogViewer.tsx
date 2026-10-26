import React from 'react';
import { Database, ShieldAlert } from 'lucide-react';
import { AuditLogEntry } from '../types/api';

interface AuditLogViewerProps {
  logs: AuditLogEntry[];
}

export const AuditLogViewer: React.FC<AuditLogViewerProps> = ({ logs }) => {
  if (!logs || logs.length === 0) {
    return (
      <div className="p-8 text-center text-slate-500 font-mono text-xs rounded-xl bg-[#0a101d] border border-[#172238]">
        No audit log records found.
      </div>
    );
  }

  return (
    <div className="p-4 bg-[#0a101d] border border-[#172238] rounded-xl space-y-3">
      <div className="flex items-center justify-between pb-3 border-b border-[#172238]">
        <div className="flex items-center space-x-2 text-xs font-mono text-slate-300">
          <Database className="w-4 h-4 text-cyan-400" />
          <span>Immutable Audit Log Store</span>
        </div>
        <span className="text-[10px] font-mono text-emerald-400 px-2 py-0.5 rounded bg-emerald-950/60 border border-emerald-800">
          TAMPER-EVIDENT SQLITE
        </span>
      </div>

      <div className="space-y-2 max-h-96 overflow-y-auto">
        {logs.map((log) => (
          <div
            key={log.id}
            className="p-3 rounded-lg bg-[#070b14] border border-[#141e33] flex items-start justify-between text-xs font-mono"
          >
            <div className="space-y-1">
              <div className="flex items-center space-x-2">
                <span className="font-bold text-cyan-300">{log.event_type}</span>
                <span className="text-slate-400">•</span>
                <span className="text-slate-400">{log.entity_id}</span>
              </div>
              <div className="text-[11px] text-slate-400 bg-[#050811] p-1.5 rounded border border-[#11192b]">
                {JSON.stringify(log.details)}
              </div>
            </div>
            <span className="text-[10px] text-slate-400 whitespace-nowrap ml-4">
              {new Date(log.timestamp).toLocaleTimeString()}
            </span>
          </div>
        ))}
      </div>
    </div>
  );
};
