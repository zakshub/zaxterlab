import React, { useEffect, useState } from 'react';
import { File, Folder, HardDrive, RefreshCw } from 'lucide-react';
import { FileContentResponse, WorkspaceEntry } from '../types/api';

interface WorkspaceViewerProps {
  onListFiles: (path?: string) => Promise<{ entries: WorkspaceEntry[]; current_path: string }>;
  onGetContent: (path: string) => Promise<FileContentResponse>;
}

export const WorkspaceViewer: React.FC<WorkspaceViewerProps> = ({ onListFiles, onGetContent }) => {
  const [entries, setEntries] = useState<WorkspaceEntry[]>([]);
  const [currentPath, setCurrentPath] = useState<string>('.');
  const [selectedFile, setSelectedFile] = useState<string | null>(null);
  const [fileContent, setFileContent] = useState<string | null>(null);
  const [loading, setLoading] = useState<boolean>(false);
  const [error, setError] = useState<string | null>(null);

  const loadDirectory = async (path: string = '.') => {
    setLoading(true);
    setError(null);
    try {
      const res = await onListFiles(path);
      setEntries(res.entries);
      setCurrentPath(res.current_path);
    } catch (err: any) {
      setError(err.message || 'Failed to list directory');
    } finally {
      setLoading(false);
    }
  };

  const openFile = async (fileName: string) => {
    setLoading(true);
    setError(null);
    try {
      const fullPath = currentPath === '.' ? fileName : `${currentPath}/${fileName}`;
      const res = await onGetContent(fullPath);
      setSelectedFile(fullPath);
      setFileContent(res.content);
    } catch (err: any) {
      setError(err.message || 'Failed to read file');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadDirectory('.');
  }, []);

  return (
    <div className="grid grid-cols-1 md:grid-cols-2 gap-4 h-full">
      {/* File Tree */}
      <div className="p-4 bg-[#0a101d] border border-[#172238] rounded-xl flex flex-col justify-between">
        <div>
          <div className="flex items-center justify-between pb-3 border-b border-[#172238] mb-3">
            <div className="flex items-center space-x-2 text-xs font-mono text-slate-300">
              <HardDrive className="w-4 h-4 text-cyan-400" />
              <span>Workspace: {currentPath}</span>
            </div>
            <button
              onClick={() => loadDirectory(currentPath)}
              className="p-1 rounded hover:bg-slate-800 text-slate-400 hover:text-cyan-300 transition-all"
              title="Refresh"
            >
              <RefreshCw className={`w-3.5 h-3.5 ${loading ? 'animate-spin' : ''}`} />
            </button>
          </div>

          {error && (
            <div className="p-2 mb-3 rounded bg-rose-950/40 border border-rose-800 text-xs text-rose-300 font-mono">
              {error}
            </div>
          )}

          <div className="space-y-1">
            {entries.length === 0 && !loading && (
              <div className="text-xs font-mono text-slate-500 py-4 text-center">
                Workspace directory is currently empty.
              </div>
            )}

            {entries.map((entry) => (
              <button
                key={entry.name}
                onClick={() => (entry.is_directory ? loadDirectory(entry.name) : openFile(entry.name))}
                className={`w-full flex items-center justify-between p-2 rounded-lg text-xs font-mono transition-all ${
                  selectedFile === entry.name
                    ? 'bg-cyan-950/40 text-cyan-300 border border-cyan-800/60'
                    : 'text-slate-300 hover:bg-[#0e1628]'
                }`}
              >
                <div className="flex items-center space-x-2 truncate">
                  {entry.is_directory ? (
                    <Folder className="w-4 h-4 text-amber-400 flex-shrink-0" />
                  ) : (
                    <File className="w-4 h-4 text-cyan-400 flex-shrink-0" />
                  )}
                  <span className="truncate">{entry.name}</span>
                </div>
                {!entry.is_directory && (
                  <span className="text-[10px] text-slate-400 font-mono">{entry.size_bytes}B</span>
                )}
              </button>
            ))}
          </div>
        </div>

        <div className="pt-3 border-t border-[#172238] text-[10px] font-mono text-slate-400">
          Sandboxed path traversal protection enabled.
        </div>
      </div>

      {/* File Content Preview */}
      <div className="p-4 bg-[#0a101d] border border-[#172238] rounded-xl flex flex-col justify-between">
        <div>
          <div className="flex items-center justify-between pb-3 border-b border-[#172238] mb-3">
            <span className="text-xs font-mono text-slate-300 truncate">
              {selectedFile ? `File: ${selectedFile}` : 'Select a file to inspect'}
            </span>
          </div>

          <div className="rounded-lg bg-[#070b14] border border-[#141e33] p-3 h-80 overflow-auto font-mono text-xs">
            {fileContent !== null ? (
              <pre className="text-slate-300 whitespace-pre-wrap">{fileContent}</pre>
            ) : (
              <div className="h-full flex items-center justify-center text-slate-600">
                No file selected.
              </div>
            )}
          </div>
        </div>

        <div className="pt-3 border-t border-[#172238] text-[10px] font-mono text-slate-400">
          Read-only inspection buffer.
        </div>
      </div>
    </div>
  );
};
