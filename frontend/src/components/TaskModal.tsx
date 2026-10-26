import React, { useState } from 'react';
import { X, Send } from 'lucide-react';

interface TaskModalProps {
  isOpen: boolean;
  onClose: () => void;
  onSubmit: (title: string, description: string, inputContext: Record<string, any>) => Promise<void>;
}

export const TaskModal: React.FC<TaskModalProps> = ({ isOpen, onClose, onSubmit }) => {
  const [title, setTitle] = useState('');
  const [description, setDescription] = useState('');
  const [contextJson, setContextJson] = useState('{\n  "priority": "normal"\n}');
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);

  if (!isOpen) return null;

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!title.trim()) {
      setError('Task title is required.');
      return;
    }

    let parsedContext = {};
    try {
      parsedContext = contextJson ? JSON.parse(contextJson) : {};
    } catch {
      setError('Input context must be valid JSON.');
      return;
    }

    setIsSubmitting(true);
    setError(null);
    try {
      await onSubmit(title.trim(), description.trim(), parsedContext);
      setTitle('');
      setDescription('');
      onClose();
    } catch (err: any) {
      setError(err.message || 'Failed to submit task.');
    } finally {
      setIsSubmitting(false);
    }
  };

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/80 backdrop-blur-sm">
      <div className="w-full max-w-lg rounded-xl bg-[#0a101d] border border-cyan-500/40 p-6 shadow-2xl shadow-cyan-950/50">
        <div className="flex items-center justify-between pb-4 border-b border-[#172238] mb-4">
          <h2 className="text-base font-bold text-slate-100 flex items-center space-x-2">
            <span>Submit Autonomous Task</span>
            <span className="text-[10px] font-mono px-2 py-0.5 rounded bg-cyan-950 text-cyan-400 border border-cyan-800">
              Worker 1 Assignment
            </span>
          </h2>
          <button onClick={onClose} className="text-slate-400 hover:text-slate-200">
            <X className="w-5 h-5" />
          </button>
        </div>

        {error && (
          <div className="p-3 mb-4 rounded-lg bg-rose-950/40 border border-rose-800 text-xs text-rose-300 font-mono">
            {error}
          </div>
        )}

        <form onSubmit={handleSubmit} className="space-y-4">
          <div>
            <label className="block text-xs font-mono text-slate-300 mb-1">Task Title</label>
            <input
              type="text"
              value={title}
              onChange={(e) => setTitle(e.target.value)}
              placeholder="e.g. Implement Hermetic Test Validator"
              className="w-full px-3 py-2 rounded-lg bg-[#070b14] border border-[#1b2742] text-slate-200 text-xs font-mono focus:border-cyan-500 focus:outline-none"
              required
            />
          </div>

          <div>
            <label className="block text-xs font-mono text-slate-300 mb-1">Description & Requirements</label>
            <textarea
              rows={3}
              value={description}
              onChange={(e) => setDescription(e.target.value)}
              placeholder="Detailed step instructions for Worker 1..."
              className="w-full px-3 py-2 rounded-lg bg-[#070b14] border border-[#1b2742] text-slate-200 text-xs font-mono focus:border-cyan-500 focus:outline-none"
            />
          </div>

          <div>
            <label className="block text-xs font-mono text-slate-300 mb-1">Input Context (JSON)</label>
            <textarea
              rows={3}
              value={contextJson}
              onChange={(e) => setContextJson(e.target.value)}
              className="w-full px-3 py-2 rounded-lg bg-[#070b14] border border-[#1b2742] text-slate-200 text-xs font-mono focus:border-cyan-500 focus:outline-none"
            />
          </div>

          <div className="pt-3 border-t border-[#172238] flex items-center justify-end space-x-3">
            <button
              type="button"
              onClick={onClose}
              className="px-4 py-2 rounded-lg border border-[#1b2742] text-slate-400 hover:text-slate-200 text-xs font-mono"
            >
              Cancel
            </button>
            <button
              type="submit"
              disabled={isSubmitting}
              className="flex items-center space-x-2 px-5 py-2 rounded-lg bg-gradient-to-r from-cyan-500 to-blue-600 hover:from-cyan-400 hover:to-blue-500 text-slate-950 font-mono font-semibold text-xs shadow-lg shadow-cyan-500/20 active:scale-95 disabled:opacity-50"
            >
              <Send className="w-3.5 h-3.5 text-slate-950" />
              <span>{isSubmitting ? 'Submitting...' : 'Dispatch Task'}</span>
            </button>
          </div>
        </form>
      </div>
    </div>
  );
};
