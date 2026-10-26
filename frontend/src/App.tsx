import React, { useEffect, useState } from 'react';
import { Header } from './components/Header';
import { Navigation, NavTab } from './components/Navigation';
import { NeuralNetwork3D } from './components/NeuralNetwork3D';
import { ExecutionPipeline } from './components/ExecutionPipeline';
import { WorkerCard } from './components/WorkerCard';
import { SessionControls } from './components/SessionControls';
import { Timeline } from './components/Timeline';
import { WorkspaceViewer } from './components/WorkspaceViewer';
import { AuditLogViewer } from './components/AuditLogViewer';
import { TaskModal } from './components/TaskModal';
import { clientManager, ClientMode } from './services/apiClient';
import { AuditLogEntry, Session, SystemHealth, Task } from './types/api';
import { CheckCircle2, AlertCircle, Clock, PauseCircle, ShieldAlert, Cpu } from 'lucide-react';

export const App: React.FC = () => {
  const [activeTab, setActiveTab] = useState<NavTab>('home');
  const [mode, setMode] = useState<ClientMode>('demo');
  const [health, setHealth] = useState<SystemHealth | null>(null);
  const [tasks, setTasks] = useState<Task[]>([]);
  const [selectedTaskId, setSelectedTaskId] = useState<string | null>(null);
  const [selectedSession, setSelectedSession] = useState<Session | null>(null);
  const [auditLogs, setAuditLogs] = useState<AuditLogEntry[]>([]);
  const [isLoading, setIsLoading] = useState<boolean>(false);
  const [isOperating, setIsOperating] = useState<boolean>(false);
  const [isTaskModalOpen, setIsTaskModalOpen] = useState<boolean>(false);
  const [activePhase, setActivePhase] = useState<string>('IDLE');

  const client = clientManager.getClient();

  const loadData = async () => {
    setIsLoading(true);
    try {
      const [h, t, l] = await Promise.all([
        client.getHealth().catch(() => null),
        client.listTasks().catch(() => []),
        client.getAuditLogs().catch(() => []),
      ]);

      setHealth(h);
      setTasks(t);
      setAuditLogs(l);

      if (t.length > 0 && !selectedTaskId) {
        setSelectedTaskId(t[0].task_id);
      }
    } finally {
      setIsLoading(false);
    }
  };

  const loadTaskDetails = async (taskId: string) => {
    try {
      const details = await client.getTaskDetails(taskId);
      setSelectedSession(details.session);

      if (details.session?.status === 'ACTIVE') {
        const lastTrace = details.session.step_traces.slice(-1)[0];
        setActivePhase(lastTrace?.phase || 'PLAN');
      } else if (details.session?.status === 'SUSPENDED') {
        setActivePhase('SUSPENDED');
      } else if (details.task.status === 'BLOCKED') {
        setActivePhase('BLOCKED');
      } else {
        setActivePhase('IDLE');
      }
    } catch {
      setSelectedSession(null);
    }
  };

  useEffect(() => {
    loadData();
  }, [mode]);

  useEffect(() => {
    if (selectedTaskId) {
      loadTaskDetails(selectedTaskId);
    }
  }, [selectedTaskId, mode]);

  const handleModeToggle = (newMode: ClientMode) => {
    clientManager.setMode(newMode);
    setMode(newMode);
    setSelectedTaskId(null);
    setSelectedSession(null);
  };

  const handleExecute = async () => {
    if (!selectedTaskId) return;
    setIsOperating(true);
    setActivePhase('READ');
    try {
      const res = await client.executeTask(selectedTaskId);
      setSelectedSession(res.session);
      await loadData();
      setActivePhase('LOG');
      setTimeout(() => setActivePhase('IDLE'), 2000);
    } catch (err: any) {
      alert(`Execution Error: ${err.message}`);
      setActivePhase('BLOCKED');
    } finally {
      setIsOperating(false);
    }
  };

  const handleSuspend = async () => {
    if (!selectedSession) return;
    setIsOperating(true);
    try {
      await client.suspendSession(selectedSession.session_id);
      setActivePhase('SUSPENDED');
      await loadData();
      if (selectedTaskId) await loadTaskDetails(selectedTaskId);
    } catch (err: any) {
      alert(`Suspension Error: ${err.message}`);
    } finally {
      setIsOperating(false);
    }
  };

  const handleResume = async () => {
    if (!selectedSession) return;
    setIsOperating(true);
    setActivePhase('READ');
    try {
      const res = await client.resumeSession(selectedSession.session_id);
      setSelectedSession(res.session);
      await loadData();
      setActivePhase('LOG');
      setTimeout(() => setActivePhase('IDLE'), 2000);
    } catch (err: any) {
      alert(`Resume Error: ${err.message}`);
      setActivePhase('BLOCKED');
    } finally {
      setIsOperating(false);
    }
  };

  const handleTerminate = async () => {
    if (!selectedSession) return;
    if (!confirm('Are you sure you want to terminate this session?')) return;
    setIsOperating(true);
    try {
      await client.terminateSession(selectedSession.session_id, 'User terminated via dashboard');
      setActivePhase('BLOCKED');
      await loadData();
      if (selectedTaskId) await loadTaskDetails(selectedTaskId);
    } catch (err: any) {
      alert(`Termination Error: ${err.message}`);
    } finally {
      setIsOperating(false);
    }
  };

  const handleCreateTask = async (title: string, description: string, inputContext: Record<string, any>) => {
    const newTask = await client.createTask(title, description, inputContext);
    await loadData();
    setSelectedTaskId(newTask.task_id);
  };

  const selectedTask = tasks.find((t) => t.task_id === selectedTaskId) || null;

  return (
    <div className="flex h-screen w-screen overflow-hidden bg-[#050811] text-slate-100">
      {/* Navigation Sidebar */}
      <Navigation activeTab={activeTab} onTabChange={setActiveTab} taskCount={tasks.length} />

      {/* Main App Container */}
      <div className="flex-1 flex flex-col min-w-0 overflow-hidden">
        <Header
          mode={mode}
          onModeToggle={handleModeToggle}
          health={health}
          onRefresh={loadData}
          onOpenNewTaskModal={() => setIsTaskModalOpen(true)}
          isLoading={isLoading}
        />

        {/* Tab Views */}
        <main className="flex-1 overflow-y-auto p-6 space-y-6">
          {activeTab === 'home' && (
            <div className="space-y-6">
              {/* Top 3D Neural Core & Worker Card */}
              <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
                <div className="lg:col-span-2 h-[340px]">
                  <NeuralNetwork3D
                    currentPhase={activePhase}
                    isDemo={mode === 'demo'}
                    workerName={health?.worker.name || 'Reem'}
                  />
                </div>
                <div className="h-[340px]">
                  <WorkerCard
                    worker={health?.worker || null}
                    status={selectedTask?.status || 'IDLE'}
                    currentTaskTitle={selectedTask?.title}
                  />
                </div>
              </div>

              {/* Execution Pipeline Indicator */}
              <ExecutionPipeline currentPhase={activePhase} />

              {/* Session Controls */}
              <SessionControls
                taskStatus={selectedTask?.status}
                sessionStatus={selectedSession?.status}
                onExecute={handleExecute}
                onSuspend={handleSuspend}
                onResume={handleResume}
                onTerminate={handleTerminate}
                isOperating={isOperating}
              />

              {/* Task Selection and Execution Timeline Grid */}
              <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
                {/* Task Selector */}
                <div className="p-4 bg-[#0a101d] border border-[#172238] rounded-xl space-y-3">
                  <div className="flex items-center justify-between pb-3 border-b border-[#172238]">
                    <span className="text-xs font-mono font-bold text-slate-200 uppercase tracking-wider">
                      Workload Queue
                    </span>
                    <span className="text-xs font-mono text-cyan-400">{tasks.length} Total</span>
                  </div>

                  <div className="space-y-2 max-h-[460px] overflow-y-auto pr-1">
                    {tasks.map((task) => {
                      const isSelected = task.task_id === selectedTaskId;
                      return (
                        <div
                          key={task.task_id}
                          onClick={() => setSelectedTaskId(task.task_id)}
                          className={`p-3 rounded-lg border cursor-pointer select-none transition-all ${
                            isSelected
                              ? 'bg-[#0f1b33] border-cyan-500/60 shadow-md shadow-cyan-500/10'
                              : 'bg-[#070b14] border-[#162238] hover:border-slate-700'
                          }`}
                        >
                          <div className="flex items-center justify-between text-xs mb-1">
                            <span className="font-semibold text-slate-200 truncate">{task.title}</span>
                            <span
                              className={`text-[9px] font-mono px-1.5 py-0.5 rounded font-bold ${
                                task.status === 'COMPLETED'
                                  ? 'bg-emerald-950 text-emerald-300 border border-emerald-800'
                                  : task.status === 'RUNNING'
                                  ? 'bg-cyan-950 text-cyan-300 border border-cyan-800 animate-pulse'
                                  : task.status === 'SUSPENDED'
                                  ? 'bg-amber-950 text-amber-300 border border-amber-800'
                                  : task.status === 'BLOCKED'
                                  ? 'bg-rose-950 text-rose-300 border border-rose-800'
                                  : 'bg-slate-800 text-slate-300'
                              }`}
                            >
                              {task.status}
                            </span>
                          </div>
                          <p className="text-[11px] text-slate-400 line-clamp-1">{task.description}</p>
                          <div className="text-[10px] font-mono text-slate-500 mt-2">
                            {new Date(task.created_at).toLocaleTimeString()}
                          </div>
                        </div>
                      );
                    })}
                  </div>
                </div>

                {/* Step Trace Timeline */}
                <div className="lg:col-span-2">
                  <div className="text-xs font-mono font-bold text-slate-300 mb-3 uppercase tracking-wider flex items-center justify-between">
                    <span>Active Execution Trace</span>
                    {selectedSession && (
                      <span className="text-slate-500">
                        Session: {selectedSession.session_id} • Step {selectedSession.current_step}
                      </span>
                    )}
                  </div>
                  <Timeline traces={selectedSession?.step_traces || []} />
                </div>
              </div>
            </div>
          )}

          {activeTab === 'workspace' && (
            <WorkspaceViewer
              onListFiles={(p) => client.listWorkspaceFiles(p)}
              onGetContent={(p) => client.getFileContent(p)}
            />
          )}

          {activeTab === 'logs' && <AuditLogViewer logs={auditLogs} />}

          {activeTab === 'agents' && (
            <div className="p-6 bg-[#0a101d] border border-[#172238] rounded-xl space-y-4">
              <div className="flex items-center justify-between pb-3 border-b border-[#172238]">
                <div>
                  <h2 className="text-sm font-bold text-slate-100 flex items-center space-x-2">
                    <Cpu className="w-4 h-4 text-cyan-400" />
                    <span>Company Role Directory</span>
                  </h2>
                  <p className="text-xs font-mono text-slate-400 mt-0.5">
                    Organic evolution rule: 1 active worker baseline. Specialists remain dormant until justified by workload.
                  </p>
                </div>
                <span className="text-xs font-mono text-emerald-400 px-2.5 py-1 rounded bg-emerald-950/60 border border-emerald-800">
                  1 ACTIVE / 14 REFERENCE
                </span>
              </div>

              <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-3 font-mono text-xs">
                {/* Active Worker */}
                <div className="p-3.5 rounded-lg bg-cyan-950/20 border border-cyan-500/40">
                  <div className="flex items-center justify-between mb-1.5">
                    <span className="font-bold text-cyan-300">Reem</span>
                    <span className="px-1.5 py-0.2 rounded text-[10px] bg-cyan-950 text-cyan-400 border border-cyan-800">
                      ACTIVE (Worker 1)
                    </span>
                  </div>
                  <div className="text-[11px] text-slate-300 mb-1">Construction & Programming</div>
                  <div className="text-[10px] text-slate-500">Archetype: Riri Williams</div>
                </div>

                {/* Dormant References */}
                {[
                  { name: 'Sirfaraz', role: 'Central Command', arc: 'Nick Fury' },
                  { name: 'Zaks', role: 'Audit & Oversight', arc: 'Vision' },
                  { name: 'Khadija', role: 'Chief Architecture', arc: 'Tony Stark' },
                  { name: 'Maryam', role: 'Tech Research & Integration', arc: 'Shuri' },
                  { name: 'Hadia', role: 'Research & Innovation', arc: 'Shuri' },
                  { name: 'Hussain', role: 'Analysis & Reasoning', arc: 'Bruce Banner' },
                  { name: 'Hadi', role: 'Planning & Strategy', arc: 'Peter Parker' },
                  { name: 'Aroosh', role: 'Quality Assurance', arc: 'Shuri' },
                  { name: 'Hania', role: 'Product Strategy & UX', arc: 'Pepper Potts' },
                  { name: 'Zara', role: 'Security & Risk', arc: 'Natasha Romanoff' },
                  { name: 'Hasan', role: 'Infrastructure & DevOps', arc: 'James Rhodes' },
                  { name: 'Huzaifa', role: 'Docs & Communications', arc: 'Phil Coulson' },
                  { name: 'Umer', role: 'Coordination & Approval', arc: 'Happy Hogan' },
                  { name: 'Musab', role: 'Specialist Reserve', arc: 'Unassigned' },
                ].map((spec) => (
                  <div key={spec.name} className="p-3.5 rounded-lg bg-[#070b14] border border-[#141e33] opacity-60">
                    <div className="flex items-center justify-between mb-1.5">
                      <span className="font-bold text-slate-300">{spec.name}</span>
                      <span className="px-1.5 py-0.2 rounded text-[10px] bg-slate-900 text-slate-500 border border-slate-800">
                        DORMANT
                      </span>
                    </div>
                    <div className="text-[11px] text-slate-400 mb-1">{spec.role}</div>
                    <div className="text-[10px] text-slate-600">Archetype: {spec.arc}</div>
                  </div>
                ))}
              </div>
            </div>
          )}

          {activeTab === 'tasks' && (
            <div className="p-6 bg-[#0a101d] border border-[#172238] rounded-xl space-y-4">
              <div className="flex items-center justify-between pb-3 border-b border-[#172238]">
                <h2 className="text-sm font-bold text-slate-100 font-mono">All Tasks ({tasks.length})</h2>
                <button
                  onClick={() => setIsTaskModalOpen(true)}
                  className="px-3 py-1.5 rounded-lg bg-cyan-600 text-slate-950 font-mono text-xs font-semibold"
                >
                  Create Task
                </button>
              </div>

              <div className="divide-y divide-[#172238]">
                {tasks.map((t) => (
                  <div key={t.task_id} className="py-3 flex items-center justify-between text-xs font-mono">
                    <div>
                      <div className="font-semibold text-slate-200">{t.title}</div>
                      <div className="text-slate-400 text-[11px]">{t.description}</div>
                    </div>
                    <div className="flex items-center space-x-3">
                      <span className="px-2 py-0.5 rounded text-[10px] bg-slate-800 text-slate-300">
                        {t.status}
                      </span>
                      <button
                        onClick={() => {
                          setSelectedTaskId(t.task_id);
                          setActiveTab('home');
                        }}
                        className="text-cyan-400 hover:underline"
                      >
                        Inspect
                      </button>
                    </div>
                  </div>
                ))}
              </div>
            </div>
          )}

          {activeTab === 'settings' && (
            <div className="p-6 bg-[#0a101d] border border-[#172238] rounded-xl space-y-4 max-w-2xl">
              <h2 className="text-sm font-bold text-slate-100 font-mono pb-3 border-b border-[#172238]">
                System Governance & Invariants
              </h2>

              <div className="space-y-3 font-mono text-xs">
                <div className="p-3 rounded-lg bg-[#070b14] border border-[#141e33] flex justify-between items-center">
                  <div>
                    <div className="text-slate-200 font-bold">Authorized Spend Boundary</div>
                    <div className="text-slate-500 text-[11px]">Hard boundary locking cloud and API billing</div>
                  </div>
                  <span className="text-emerald-400 font-bold">$0.00 USD (LOCKED)</span>
                </div>

                <div className="p-3 rounded-lg bg-[#070b14] border border-[#141e33] flex justify-between items-center">
                  <div>
                    <div className="text-slate-200 font-bold">Workspace Sandboxing</div>
                    <div className="text-slate-500 text-[11px]">File path traversal boundary</div>
                  </div>
                  <span className="text-cyan-400 font-bold">ENFORCED</span>
                </div>

                <div className="p-3 rounded-lg bg-[#070b14] border border-[#141e33] flex justify-between items-center">
                  <div>
                    <div className="text-slate-200 font-bold">Command Restriction Guard</div>
                    <div className="text-slate-500 text-[11px]">Destructive shell commands blocked</div>
                  </div>
                  <span className="text-cyan-400 font-bold">STRICT WHITELIST</span>
                </div>
              </div>
            </div>
          )}
        </main>
      </div>

      {/* New Task Modal */}
      <TaskModal
        isOpen={isTaskModalOpen}
        onClose={() => setIsTaskModalOpen(false)}
        onSubmit={handleCreateTask}
      />
    </div>
  );
};
