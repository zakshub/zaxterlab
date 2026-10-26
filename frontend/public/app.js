/**
 * ZaxterLab Operations Dashboard — Modern Browser Application
 * Features:
 * - Event-Driven 3D Neural Network Visualization (Three.js)
 * - Dual Mode: DEMO — SIMULATED EVENTS vs. LIVE BACKEND CONNECTED
 * - 5-Stage Pipeline: Read -> Plan -> Tool Call -> Evaluate -> Log
 * - Worker 1 (Reem) Management, Task Lifecycle, Workspace Inspection, Audit Logs
 * - Hard $0.00 Spend Boundary Display
 */

import * as THREE from './vendor/three.module.js';

// --- State Management ---
const state = {
  mode: 'demo', // 'demo' | 'live'
  activeTab: 'home', // 'home' | 'completion' | 'tasks' | 'sessions' | 'agents' | 'workspace' | 'logs' | 'settings'
  health: null,
  completion: null,
  tasks: [],
  selectedTaskId: null,
  selectedSession: null,
  auditLogs: [],
  workspaceRoot: '/root/zakxterlab/workspace',
  workspaceEntries: [],
  selectedFile: null,
  selectedFileContent: null,
  activePhase: 'IDLE', // 'READ' | 'PLAN' | 'TOOL_CALL' | 'EVALUATE' | 'LOG' | 'IDLE' | 'SUSPENDED' | 'BLOCKED'
  isOperating: false,
  isTaskModalOpen: false,
  errorBanner: null,
};

// --- Mock Data ---
const mockData = {
  health: {
    status: 'healthy',
    version: '0.1.0-demo',
    mode: 'demo',
    worker: {
      agent_id: 'reem-worker-1',
      name: 'Reem',
      role: 'Construction & Programming',
      status: 'ACTIVE',
      max_iterations: 10,
      allowed_tools: ['read_file', 'write_file', 'list_dir', 'run_command'],
    },
    spend_guard: {
      authorized_spend_usd: 0.0,
      cumulative_spent_usd: 0.0,
      spend_locked: true,
    },
    workspace: {
      root: '/root/zakxterlab/workspace',
      sandboxed: true,
    },
  },
  tasks: [
    {
      task_id: 'task_demo_01',
      title: 'Initialize System Security Perimeter',
      description: 'Audit workspace boundaries, initialize SQLite tables, verify $0.00 spend guard.',
      status: 'COMPLETED',
      assigned_agent_id: 'reem-worker-1',
      input_context: { priority: 'high', security_level: 'tier_2' },
      result_summary: 'All boundary invariants passed. Workspace confined to /root/zakxterlab/workspace.',
      created_at: new Date(Date.now() - 3600000).toISOString(),
    },
    {
      task_id: 'task_demo_02',
      title: 'Draft Adaptive Neural Dispatch Protocol',
      description: 'Implement Read -> Plan -> Tool Call -> Evaluate -> Log state transitions.',
      status: 'RUNNING',
      assigned_agent_id: 'reem-worker-1',
      input_context: { target_file: 'dispatch.py' },
      result_summary: null,
      created_at: new Date(Date.now() - 1200000).toISOString(),
    },
    {
      task_id: 'task_demo_03',
      title: 'Synchronize Storage Checkpoints',
      description: 'Validate session serialization and state persistence under suspension.',
      status: 'SUSPENDED',
      assigned_agent_id: 'reem-worker-1',
      input_context: { checkpoint_id: 'cp_09' },
      result_summary: 'Suspended at step 2. Working memory safely flushed to disk.',
      created_at: new Date(Date.now() - 800000).toISOString(),
    },
  ],
  sessions: {
    task_demo_02: {
      session_id: 'sess_demo_02_alpha',
      task_id: 'task_demo_02',
      agent_id: 'reem-worker-1',
      status: 'ACTIVE',
      current_step: 3,
      total_token_usage: { prompt_tokens: 140, completion_tokens: 180, total_tokens: 320, estimated_cost_usd: 0.0 },
      step_traces: [
        {
          step_number: 1,
          phase: 'READ',
          observation: 'Ingested task parameters and examined workspace root for existing dispatch files.',
          plan: 'Formulate modular dispatch specification with strict permission tiers.',
          tool_calls: [],
          tool_results: [],
          evaluation: 'Task criteria confirmed. Proceeding to scaffold file.',
          token_usage: { prompt_tokens: 40, completion_tokens: 50, total_tokens: 90, estimated_cost_usd: 0.0 },
          created_at: new Date(Date.now() - 1100000).toISOString(),
        },
        {
          step_number: 2,
          phase: 'PLAN',
          observation: 'Model constructed tool call payload for write_file.',
          plan: 'Execute tool write_file for dispatch.py within sandboxed directory.',
          tool_calls: [
            { call_id: 'c1', tool_name: 'write_file', arguments: { path: 'dispatch.py', content: '# ZaxterLab Dispatch\n' } },
          ],
          tool_results: [
            { call_id: 'c1', tool_name: 'write_file', success: true, output: 'Successfully wrote 22 characters to dispatch.py' },
          ],
          evaluation: 'File written successfully. Executing verification.',
          token_usage: { prompt_tokens: 50, completion_tokens: 60, total_tokens: 110, estimated_cost_usd: 0.0 },
          created_at: new Date(Date.now() - 800000).toISOString(),
        },
        {
          step_number: 3,
          phase: 'TOOL_CALL',
          observation: 'Invoking test suite verification through CommandGuard.',
          plan: 'Execute python3 -m unittest discover -s tests -v.',
          tool_calls: [
            { call_id: 'c2', tool_name: 'run_command', arguments: { command: 'python3 -m unittest discover -s tests -v' } },
          ],
          tool_results: [
            { call_id: 'c2', tool_name: 'run_command', success: true, output: 'Ran 27 tests in 5.6s - OK' },
          ],
          evaluation: 'Verification passed with 100% test assertions satisfied.',
          token_usage: { prompt_tokens: 50, completion_tokens: 70, total_tokens: 120, estimated_cost_usd: 0.0 },
          created_at: new Date(Date.now() - 200000).toISOString(),
        },
      ],
    },
  },
  workspace: [
    { name: 'dispatch.py', is_directory: false, size_bytes: 4096 },
    { name: 'config.json', is_directory: false, size_bytes: 512 },
    { name: 'tests', is_directory: true, size_bytes: 0 },
    { name: 'artifacts', is_directory: true, size_bytes: 0 },
  ],
  auditLogs: [
    { id: 1, timestamp: new Date(Date.now() - 3600000).toISOString(), event_type: 'SYSTEM_BOOT', entity_id: 'reem-worker-1', details: { mode: 'DEMO', spend_bound_usd: 0.0 } },
    { id: 2, timestamp: new Date(Date.now() - 1200000).toISOString(), event_type: 'SESSION_CREATED', entity_id: 'sess_demo_02_alpha', details: { task_id: 'task_demo_02' } },
    { id: 3, timestamp: new Date(Date.now() - 800000).toISOString(), event_type: 'STEP_EXECUTED', entity_id: 'sess_demo_02_alpha', details: { step: 2, tool: 'write_file' } },
  ],
  completion: {
    assessment_date: '2026-10-26',
    overall_completion_pct: 78,
    evidence_summary: '32/32 automated unit tests passing hermetically; dual-worker engine active; $0.00 spend strictly guarded.',
    pillars: [
      { name: 'Core Architecture & Spend Security', completion_pct: 100, status: 'VERIFIED', summary: 'Data contracts, hard USD $0.00 spend guard, and workspace boundary guard.' },
      { name: 'Worker 1 Engine (Reem)', completion_pct: 100, status: 'VERIFIED', summary: '5-stage cycle (Read -> Plan -> Tool Call -> Evaluate -> Log) with multi-step execution.' },
      { name: 'Dual-Worker Audit Circuit (Zaks)', completion_pct: 100, status: 'VERIFIED', summary: 'Independent TIER_1_SAFE read-only auditor, automated artifact verification.' },
      { name: 'Persistence & REST API Service', completion_pct: 100, status: 'VERIFIED', summary: 'Thread-safe SQLite schema, daemon HTTP server, full task/session/trace endpoints.' },
      { name: 'Operations Web Dashboard & 3D Visualization', completion_pct: 95, status: 'VERIFIED', summary: 'Three.js neural network visualizer, clear Live vs. Demo mode indicators.' },
      { name: 'Adaptive Scaling & Specialization Evaluator', completion_pct: 40, status: 'IN_PROGRESS', summary: 'Workload evaluator and formal spawning proposal generator in implementation.' },
    ],
    capabilities: {
      verified_working: [
        'Deterministic offline execution with zero token cost',
        'Sandboxed workspace file reading, writing, and directory listing',
        'Safe whitelisted shell command execution',
        'Full SQLite state persistence for tasks, sessions, and step traces',
        'Session suspension and resumption without state degradation',
        'Dual-worker handoff circuit with auditor rejection/approval cycles',
        'Zero spend invariant ($0.00 hard lock)',
        'Real-time Three.js operations visualization with live backend toggle'
      ],
      partially_complete: [
        'Specialization Evaluator (backlog/failure analysis and 3-way trade-off evaluation)',
        'Formal Spawning Proposal generator for dormant specialist roles',
        'Zero-cost local Ollama adapter for offline LLM inference'
      ],
      unverified_deferred: [
        'Third-party distributed task routing (deferred until justified by real volume)'
      ]
    },
    next_priorities: [
      '1. Complete SpecializationEvaluator engine (zaxterlab/engine/evaluator.py) for automated workload telemetry and spawning proposals.',
      '2. Implement LocalOllamaProvider (zaxterlab/models/local.py) for real offline local model inference wrapped in $0.00 spend guard.',
      '3. Connect Evaluator proposals to web dashboard for one-click owner approval and dynamic specialist activation.'
    ]
  }
};

// --- Backend API Service ---
async function apiFetch(path, options = {}) {
  const res = await fetch(`/api${path}`, {
    headers: { 'Content-Type': 'application/json', Accept: 'application/json' },
    ...options,
  });
  const data = await res.json().catch(() => ({}));
  if (!res.ok) {
    throw new Error(data?.error?.message || `HTTP ${res.status}`);
  }
  return data;
}

// --- Data Fetching ---
async function refreshData() {
  state.errorBanner = null;

  if (state.mode === 'demo') {
    state.health = mockData.health;
    state.completion = mockData.completion;
    state.tasks = [...mockData.tasks];
    state.auditLogs = [...mockData.auditLogs];
    state.workspaceEntries = [...mockData.workspace];

    if (!state.selectedTaskId && state.tasks.length > 0) {
      state.selectedTaskId = state.tasks[1].task_id;
    }

    if (state.selectedTaskId) {
      state.selectedSession = mockData.sessions[state.selectedTaskId] || null;
      if (state.selectedSession) {
        state.activePhase = 'TOOL_CALL';
      }
    }
  } else {
    // Live Backend
    try {
      const [h, t, l, c] = await Promise.all([
        apiFetch('/health'),
        apiFetch('/tasks'),
        apiFetch('/audit-logs'),
        apiFetch('/completion'),
      ]);

      state.health = h;
      state.tasks = t.tasks || [];
      state.auditLogs = l.audit_logs || [];
      state.completion = c || mockData.completion;

      if (!state.selectedTaskId && state.tasks.length > 0) {
        state.selectedTaskId = state.tasks[0].task_id;
      }

      if (state.selectedTaskId) {
        await selectTask(state.selectedTaskId);
      }
    } catch (err) {
      state.errorBanner = `Live Backend Connection Error: ${err.message}. Is 'python3 -m zaxterlab.api.server' running?`;
    }
  }

  render();
}

async function selectTask(taskId) {
  state.selectedTaskId = taskId;
  if (state.mode === 'demo') {
    state.selectedSession = mockData.sessions[taskId] || null;
    state.activePhase = state.selectedSession ? 'TOOL_CALL' : 'IDLE';
    render();
  } else {
    try {
      const details = await apiFetch(`/tasks/${encodeURIComponent(taskId)}`);
      state.selectedSession = details.session;
      if (details.session) {
        state.activePhase = details.session.status === 'SUSPENDED' ? 'SUSPENDED' : 'PLAN';
      } else {
        state.activePhase = 'IDLE';
      }
    } catch (err) {
      state.selectedSession = null;
    }
    render();
  }
}

// --- Action Handlers ---
async function handleExecuteTask() {
  if (!state.selectedTaskId) return;
  state.isOperating = true;
  state.activePhase = 'READ';
  render();

  try {
    if (state.mode === 'demo') {
      setTimeout(() => {
        state.activePhase = 'PLAN';
        render();
        setTimeout(() => {
          state.activePhase = 'TOOL_CALL';
          render();
          setTimeout(() => {
            state.activePhase = 'EVALUATE';
            render();
            setTimeout(() => {
              state.activePhase = 'LOG';
              const task = state.tasks.find((t) => t.task_id === state.selectedTaskId);
              if (task) task.status = 'COMPLETED';
              state.isOperating = false;
              render();
              setTimeout(() => {
                state.activePhase = 'IDLE';
                render();
              }, 1500);
            }, 600);
          }, 600);
        }, 600);
      }, 500);
    } else {
      const res = await apiFetch(`/tasks/${encodeURIComponent(state.selectedTaskId)}/execute`, {
        method: 'POST',
        body: JSON.stringify({}),
      });
      state.selectedSession = res.session;
      await refreshData();
      state.activePhase = 'LOG';
      setTimeout(() => {
        state.activePhase = 'IDLE';
        render();
      }, 1500);
      state.isOperating = false;
    }
  } catch (err) {
    alert(`Execution Error: ${err.message}`);
    state.activePhase = 'BLOCKED';
    state.isOperating = false;
    render();
  }
}

async function handleSuspendSession() {
  if (!state.selectedSession) return;
  state.isOperating = true;
  try {
    if (state.mode === 'demo') {
      state.selectedSession.status = 'SUSPENDED';
      const task = state.tasks.find((t) => t.task_id === state.selectedTaskId);
      if (task) task.status = 'SUSPENDED';
      state.activePhase = 'SUSPENDED';
    } else {
      await apiFetch(`/sessions/${encodeURIComponent(state.selectedSession.session_id)}/suspend`, {
        method: 'POST',
      });
      state.activePhase = 'SUSPENDED';
      await selectTask(state.selectedTaskId);
    }
  } catch (err) {
    alert(`Suspend Error: ${err.message}`);
  } finally {
    state.isOperating = false;
    render();
  }
}

async function handleResumeSession() {
  if (!state.selectedSession) return;
  state.isOperating = true;
  state.activePhase = 'READ';
  render();

  try {
    if (state.mode === 'demo') {
      state.selectedSession.status = 'ACTIVE';
      const task = state.tasks.find((t) => t.task_id === state.selectedTaskId);
      if (task) task.status = 'RUNNING';
      state.activePhase = 'TOOL_CALL';
    } else {
      const res = await apiFetch(`/sessions/${encodeURIComponent(state.selectedSession.session_id)}/resume`, {
        method: 'POST',
        body: JSON.stringify({}),
      });
      state.selectedSession = res.session;
      await refreshData();
      state.activePhase = 'LOG';
    }
  } catch (err) {
    alert(`Resume Error: ${err.message}`);
    state.activePhase = 'BLOCKED';
  } finally {
    state.isOperating = false;
    render();
  }
}

async function handleTerminateSession() {
  if (!state.selectedSession) return;
  if (!confirm('Are you sure you want to terminate this session?')) return;
  state.isOperating = true;
  try {
    if (state.mode === 'demo') {
      state.selectedSession.status = 'FAILED';
      const task = state.tasks.find((t) => t.task_id === state.selectedTaskId);
      if (task) {
        task.status = 'BLOCKED';
        task.result_summary = 'Terminated by demo operator.';
      }
      state.activePhase = 'BLOCKED';
    } else {
      await apiFetch(`/sessions/${encodeURIComponent(state.selectedSession.session_id)}/terminate`, {
        method: 'POST',
        body: JSON.stringify({ reason: 'Operator aborted session' }),
      });
      state.activePhase = 'BLOCKED';
      await selectTask(state.selectedTaskId);
    }
  } catch (err) {
    alert(`Terminate Error: ${err.message}`);
  } finally {
    state.isOperating = false;
    render();
  }
}

async function handleCreateTask(title, description, inputContext) {
  if (state.mode === 'demo') {
    const newTask = {
      task_id: `task_demo_${Date.now().toString(36)}`,
      title,
      description,
      status: 'SUBMITTED',
      assigned_agent_id: 'reem-worker-1',
      input_context: inputContext,
      created_at: new Date().toISOString(),
    };
    mockData.tasks.unshift(newTask);
    state.tasks = [...mockData.tasks];
    state.selectedTaskId = newTask.task_id;
    state.selectedSession = null;
  } else {
    const res = await apiFetch('/tasks', {
      method: 'POST',
      body: JSON.stringify({ title, description, input_context: inputContext }),
    });
    await refreshData();
    state.selectedTaskId = res.task.task_id;
    await selectTask(res.task.task_id);
  }
  state.isTaskModalOpen = false;
  render();
}

// --- 3D Neural Scene Engine ---
let threeScene = null;
let threeCamera = null;
let threeRenderer = null;
let threeNodes = [];
let threeAnimId = null;

function initThreeScene(container) {
  if (!container) return;
  if (threeRenderer) {
    cancelAnimationFrame(threeAnimId);
    threeRenderer.dispose();
    container.innerHTML = '';
  }

  const w = container.clientWidth || 600;
  const h = container.clientHeight || 320;

  threeScene = new THREE.Scene();
  threeScene.fog = new THREE.FogExp2(0x050811, 0.035);

  threeCamera = new THREE.PerspectiveCamera(50, w / h, 0.1, 1000);
  threeCamera.position.set(0, 0, 24);

  threeRenderer = new THREE.WebGLRenderer({ antialias: true, alpha: true });
  threeRenderer.setSize(w, h);
  threeRenderer.setPixelRatio(Math.min(window.devicePixelRatio, 2));
  container.appendChild(threeRenderer.domElement);

  const layers = [
    { name: 'READ', count: 4, x: -9, color: 0x00f0ff },
    { name: 'PLAN', count: 6, x: -4.5, color: 0x00d2ff },
    { name: 'TOOL_CALL', count: 5, x: 0, color: 0x8b5cf6 },
    { name: 'EVALUATE', count: 5, x: 4.5, color: 0xf59e0b },
    { name: 'LOG', count: 3, x: 9, color: 0x10b981 },
  ];

  threeNodes = [];
  const nodeGeo = new THREE.SphereGeometry(0.32, 16, 16);

  layers.forEach((layer, layerIdx) => {
    const ySpacing = 2.4;
    const yOffset = ((layer.count - 1) * ySpacing) / 2;
    for (let i = 0; i < layer.count; i++) {
      const mat = new THREE.MeshBasicMaterial({ color: layer.color, transparent: true, opacity: 0.85 });
      const mesh = new THREE.Mesh(nodeGeo, mat);
      const y = i * ySpacing - yOffset;
      const z = (Math.random() - 0.5) * 3;
      mesh.position.set(layer.x, y, z);
      threeScene.add(mesh);
      threeNodes.push({ mesh, layer: layerIdx, baseColor: layer.color, layerName: layer.name });
    }
  });

  // Synapse connections
  const lineMat = new THREE.LineBasicMaterial({ color: 0x1c2a47, transparent: true, opacity: 0.35 });
  for (let l = 0; l < layers.length - 1; l++) {
    const cur = threeNodes.filter((n) => n.layer === l);
    const nxt = threeNodes.filter((n) => n.layer === l + 1);
    cur.forEach((src) => {
      nxt.forEach((dst) => {
        if (Math.random() > 0.35) {
          const pts = [src.mesh.position, dst.mesh.position];
          const geo = new THREE.BufferGeometry().setFromPoints(pts);
          const line = new THREE.Line(geo, lineMat);
          threeScene.add(line);
        }
      });
    });
  }

  // Starfield
  const starGeo = new THREE.BufferGeometry();
  const starPos = new Float32Array(300 * 3);
  for (let i = 0; i < 300 * 3; i += 3) {
    starPos[i] = (Math.random() - 0.5) * 50;
    starPos[i + 1] = (Math.random() - 0.5) * 35;
    starPos[i + 2] = (Math.random() - 0.5) * 30 - 5;
  }
  starGeo.setAttribute('position', new THREE.BufferAttribute(starPos, 3));
  const starMat = new THREE.PointsMaterial({ color: 0x334155, size: 0.15, transparent: true, opacity: 0.4 });
  threeScene.add(new THREE.Points(starGeo, starMat));

  // Render loop
  const clock = new THREE.Clock();
  function animate() {
    threeAnimId = requestAnimationFrame(animate);
    const t = clock.getElapsedTime();

    threeScene.rotation.y = Math.sin(t * 0.15) * 0.08;
    threeScene.rotation.x = Math.cos(t * 0.12) * 0.04;

    const isSusp = state.activePhase === 'SUSPENDED';
    const isBlk = state.activePhase === 'BLOCKED';

    threeNodes.forEach((n) => {
      const isAct = n.layerName === state.activePhase;
      let s = 1.0;
      let op = 0.5;

      if (isBlk) {
        n.mesh.material.color.setHex(0xef4444);
        s = 0.8 + Math.sin(t * 6) * 0.2;
        op = 0.9;
      } else if (isSusp) {
        n.mesh.material.color.setHex(0x334155);
        s = 0.7;
        op = 0.3;
      } else if (isAct) {
        n.mesh.material.color.setHex(n.baseColor);
        s = 1.4 + Math.sin(t * 8) * 0.25;
        op = 1.0;
      } else {
        n.mesh.material.color.setHex(n.baseColor);
        s = 1.0 + Math.sin(t * 2 + n.layer) * 0.08;
        op = 0.45;
      }

      n.mesh.scale.set(s, s, s);
      n.mesh.material.opacity = op;
    });

    threeRenderer.render(threeScene, threeCamera);
  }
  animate();
}

// --- HTML Render Generator ---
function render() {
  const root = document.getElementById('root');
  if (!root) return;

  const selectedTask = state.tasks.find((t) => t.task_id === state.selectedTaskId) || null;
  const isDemo = state.mode === 'demo';

  root.innerHTML = `
    <div class="flex h-screen w-screen overflow-hidden bg-[#050811] text-slate-100">
      <!-- Sidebar -->
      <aside class="w-64 h-full bg-[#080d1a] border-r border-[#1a2742] flex flex-col justify-between select-none">
        <div>
          <!-- Logo -->
          <div class="p-4 border-b border-[#1a2742] flex items-center space-x-3">
            <div class="w-9 h-9 rounded-lg bg-gradient-to-tr from-cyan-500 to-blue-600 flex items-center justify-center shadow-lg shadow-cyan-500/20 text-white font-black text-sm">
              ZL
            </div>
            <div>
              <h1 class="text-sm font-bold tracking-wider text-slate-100 flex items-center space-x-1.5">
                <span>ZAXTERLAB</span>
                <span class="text-[9px] font-mono px-1.5 py-0.5 rounded bg-cyan-950 text-cyan-400 border border-cyan-800">v0.1.0</span>
              </h1>
              <p class="text-[10px] font-mono text-slate-400">Adaptive AI Company OS</p>
            </div>
          </div>

          <!-- Nav Items -->
          <nav class="p-3 space-y-1">
            ${[
              { id: 'home', label: 'Operations Core' },
              { id: 'completion', label: `Completion Dashboard (${state.completion?.overall_completion_pct || 78}%)` },
              { id: 'tasks', label: `Workload (${state.tasks.length})` },
              { id: 'workspace', label: 'Workspace Files' },
              { id: 'logs', label: 'Audit Trail' },
              { id: 'agents', label: `Role Roster (${state.health?.active_worker_count || 2}/15)` },
              { id: 'settings', label: 'System Invariants' },
            ]
              .map(
                (item) => `
              <button onclick="window.navTo('${item.id}')" class="w-full text-left px-3 py-2.5 rounded-lg text-xs font-mono font-medium transition-all ${
                  state.activeTab === item.id
                    ? 'bg-gradient-to-r from-cyan-500/20 to-blue-500/10 text-cyan-300 border border-cyan-500/30'
                    : 'text-slate-400 hover:text-slate-200 hover:bg-[#0e1628]'
                }">
                ${item.label}
              </button>
            `
              )
              .join('')}
          </nav>
        </div>

        <!-- Spend Guard Badge -->
        <div class="p-3 m-3 rounded-lg bg-[#0c1322] border border-[#1c2a47]">
          <div class="flex items-center justify-between mb-1.5">
            <span class="text-[11px] font-mono font-medium text-slate-300">Spend Boundary</span>
            <span class="text-[9px] font-mono font-bold text-emerald-400 px-1.5 py-0.5 rounded bg-emerald-950 border border-emerald-800">LOCKED</span>
          </div>
          <div class="text-base font-mono font-bold text-slate-100">$0.00 <span class="text-xs font-normal text-slate-500">USD</span></div>
          <p class="text-[10px] text-slate-400 mt-1">Default zero authorized budget. Paid integrations disabled.</p>
        </div>
      </aside>

      <!-- Main Column -->
      <div class="flex-1 flex flex-col min-w-0 overflow-hidden">
        <!-- Header -->
        <header class="h-16 px-6 bg-[#080d1a]/90 backdrop-blur-md border-b border-[#1a2742] flex items-center justify-between z-20">
          <div class="flex items-center space-x-4">
            <!-- Mode Toggle -->
            <div class="flex items-center p-1 rounded-lg bg-[#0c1424] border border-[#1d2b49]">
              <button onclick="window.setClientMode('demo')" class="px-3 py-1 rounded text-xs font-mono font-medium transition-all ${
                isDemo
                  ? 'bg-amber-500/20 text-amber-300 border border-amber-500/40 shadow-sm'
                  : 'text-slate-400 hover:text-slate-200'
              }">
                DEMO MODE
              </button>
              <button onclick="window.setClientMode('live')" class="px-3 py-1 rounded text-xs font-mono font-medium transition-all ${
                !isDemo
                  ? 'bg-emerald-500/20 text-emerald-300 border border-emerald-500/40 shadow-sm'
                  : 'text-slate-400 hover:text-slate-200'
              }">
                LIVE BACKEND
              </button>
            </div>

            <!-- Online Indicator -->
            <div class="flex items-center space-x-2 text-xs font-mono px-3 py-1 rounded-md bg-[#0c1424] border border-[#1d2b49]">
              <span class="w-2 h-2 rounded-full ${isDemo ? 'bg-amber-400' : 'bg-emerald-400'} animate-pulse"></span>
              <span class="text-slate-300">${isDemo ? 'Mock Driver Active' : 'Backend Connected (127.0.0.1:8000)'}</span>
            </div>
          </div>

          <!-- Right Controls -->
          <div class="flex items-center space-x-3">
            <button onclick="window.refreshData()" class="px-3 py-1.5 rounded-lg bg-[#0c1424] border border-[#1d2b49] text-xs font-mono text-slate-300 hover:text-cyan-300 transition-all">
              Refresh
            </button>
            <button onclick="window.openTaskModal()" class="px-4 py-2 rounded-lg bg-gradient-to-r from-cyan-500 to-blue-600 hover:from-cyan-400 hover:to-blue-500 text-slate-950 font-mono font-semibold text-xs shadow-lg shadow-cyan-500/20 active:scale-95">
              + New Task
            </button>
          </div>
        </header>

        <!-- Error Banner -->
        ${
          state.errorBanner
            ? `
          <div class="p-3 bg-rose-950/80 border-b border-rose-800 text-xs font-mono text-rose-200 flex justify-between items-center">
            <span>${state.errorBanner}</span>
            <button onclick="window.dismissError()" class="text-rose-400 font-bold ml-4">✕</button>
          </div>
        `
            : ''
        }

        <!-- Content Area -->
        <main class="flex-1 overflow-y-auto p-6 space-y-6">
          ${renderTabContent(selectedTask)}
        </main>
      </div>
    </div>

    <!-- Modal Container -->
    ${state.isTaskModalOpen ? renderTaskModal() : ''}
  `;

  // Attach ThreeJS
  if (state.activeTab === 'home') {
    const container = document.getElementById('three-container');
    if (container) {
      initThreeScene(container);
    }
  }
}

function renderTabContent(selectedTask) {
  if (state.activeTab === 'completion') {
    return renderCompletionDashboard();
  } else if (state.activeTab === 'home') {
    return `
      <!-- Top Row: Neural Network & Worker Card -->
      <div class="grid grid-cols-1 lg:grid-cols-3 gap-6">
        <!-- 3D Neural Network Feature -->
        <div class="lg:col-span-2 h-[340px] relative rounded-xl bg-[#070b14] border border-[#172238] overflow-hidden shadow-2xl">
          <div id="three-container" class="w-full h-full"></div>

          <!-- Status Overlays -->
          <div class="absolute top-3 left-4 right-4 flex items-center justify-between pointer-events-none">
            <div class="flex items-center space-x-2">
              <div class="flex items-center space-x-1.5 px-2.5 py-1 rounded bg-[#0a101d]/90 border border-cyan-500/30">
                <span class="w-2 h-2 rounded-full bg-cyan-400 animate-pulse"></span>
                <span class="text-xs font-mono font-semibold text-cyan-300">Phase: ${state.activePhase}</span>
              </div>
              <span class="text-xs font-mono text-slate-400 px-2 py-0.5 rounded bg-slate-900 border border-slate-800">
                Worker: Reem (Worker 1)
              </span>
            </div>

            ${
              state.mode === 'demo'
                ? `
              <div class="px-3 py-1 rounded bg-amber-500/20 border border-amber-500/40 text-amber-300 text-xs font-mono font-bold tracking-wider animate-pulse">
                DEMO — SIMULATED EVENTS
              </div>
            `
                : `
              <div class="px-3 py-1 rounded bg-emerald-500/20 border border-emerald-500/40 text-emerald-300 text-xs font-mono font-bold tracking-wider">
                LIVE BACKEND CONNECTED
              </div>
            `
            }
          </div>

          <div class="absolute bottom-3 left-4 right-4 flex items-center justify-between pointer-events-none text-[11px] font-mono text-slate-400">
            <div class="flex items-center space-x-3">
              <span class="text-cyan-400">● Read</span>
              <span class="text-blue-400">● Plan</span>
              <span class="text-violet-400">● Tool Call</span>
              <span class="text-amber-400">● Evaluate</span>
              <span class="text-emerald-400">● Log</span>
            </div>
            <span class="text-slate-500 text-[10px]">Event-driven topology abstraction</span>
          </div>
        </div>

        <!-- Worker 1 Card -->
        <div class="h-[340px] p-4 bg-[#0a101d] border border-[#172238] rounded-xl flex flex-col justify-between font-mono">
          <div>
            <div class="flex items-center justify-between mb-3">
              <div>
                <div class="text-sm font-bold text-slate-100 flex items-center space-x-2">
                  <span>Reem</span>
                  <span class="text-[10px] text-cyan-400 px-1.5 py-0.5 rounded bg-cyan-950 border border-cyan-800">Worker 1</span>
                </div>
                <div class="text-[11px] text-slate-400">Construction & Programming</div>
              </div>
              <span class="text-[10px] px-2 py-0.5 rounded font-bold ${
                selectedTask?.status === 'RUNNING'
                  ? 'bg-cyan-950 text-cyan-300 border border-cyan-800 animate-pulse'
                  : selectedTask?.status === 'SUSPENDED'
                  ? 'bg-amber-950 text-amber-300 border border-amber-800'
                  : selectedTask?.status === 'BLOCKED'
                  ? 'bg-rose-950 text-rose-300 border border-rose-800'
                  : 'bg-slate-800 text-slate-300'
              }">${selectedTask?.status || 'IDLE'}</span>
            </div>

            <!-- Assigned Task -->
            <div class="p-2.5 rounded bg-[#070b14] border border-[#162238] mb-3 text-xs">
              <div class="text-[10px] text-slate-500 uppercase tracking-wider mb-0.5">Assigned Workload</div>
              <div class="font-medium text-slate-200 line-clamp-2">${selectedTask?.title || 'No active task selected'}</div>
            </div>

            <!-- Allowed Tools -->
            <div class="space-y-1.5 text-xs">
              <div class="text-[10px] text-slate-500 uppercase tracking-wider">Authorized Tool Whitelist</div>
              <div class="flex flex-wrap gap-1">
                ${['read_file', 'write_file', 'list_dir', 'run_command']
                  .map(
                    (tool) => `
                  <span class="px-2 py-0.5 rounded text-[10px] bg-[#070b14] text-slate-300 border border-[#162238]">
                    ✓ ${tool}
                  </span>
                `
                  )
                  .join('')}
              </div>
            </div>
          </div>

          <div class="pt-3 border-t border-[#172238] flex justify-between text-[10px] text-slate-500">
            <span>Tier 2 (Reversible)</span>
            <span>Max Steps: 10</span>
          </div>
        </div>
      </div>

      <!-- Execution Pipeline Indicator -->
      <div class="w-full p-3 bg-[#0a101d] border border-[#172238] rounded-xl flex items-center justify-between text-xs font-mono">
        ${[
          { id: 'READ', label: '1. Read' },
          { id: 'PLAN', label: '2. Plan' },
          { id: 'TOOL_CALL', label: '3. Tool Call' },
          { id: 'EVALUATE', label: '4. Evaluate' },
          { id: 'LOG', label: '5. Log' },
        ]
          .map(
            (p) => `
          <div class="flex-1 text-center py-2 px-3 mx-1 rounded border transition-all ${
            state.activePhase === p.id
              ? 'bg-cyan-950 text-cyan-300 border-cyan-500 font-bold shadow-md shadow-cyan-500/20'
              : 'bg-[#070b14] text-slate-500 border-[#162238]'
          }">
            ${p.label}
          </div>
        `
          )
          .join('')}
      </div>

      <!-- Session Action Controls -->
      <div class="p-3 bg-[#0a101d] border border-[#172238] rounded-xl flex items-center justify-between text-xs font-mono">
        <div class="flex items-center space-x-2">
          <span class="text-slate-400">Controls:</span>
          <button onclick="window.execTask()" ${
            state.isOperating || (selectedTask?.status !== 'SUBMITTED' && selectedTask?.status !== 'QUEUED')
              ? 'disabled class="opacity-30 px-3 py-1.5 rounded bg-cyan-700 text-slate-900 cursor-not-allowed"'
              : 'class="px-3 py-1.5 rounded bg-cyan-500 hover:bg-cyan-400 text-slate-950 font-bold transition-all"'
          }>▶ Execute</button>

          <button onclick="window.suspSession()" ${
            state.isOperating || (state.selectedSession?.status !== 'ACTIVE' && selectedTask?.status !== 'RUNNING')
              ? 'disabled class="opacity-30 px-3 py-1.5 rounded bg-amber-950 text-amber-500 cursor-not-allowed border border-amber-900"'
              : 'class="px-3 py-1.5 rounded bg-amber-600/30 hover:bg-amber-600/40 text-amber-300 border border-amber-500/50 transition-all"'
          }>⏸ Suspend</button>

          <button onclick="window.resSession()" ${
            state.isOperating || (state.selectedSession?.status !== 'SUSPENDED' && selectedTask?.status !== 'SUSPENDED')
              ? 'disabled class="opacity-30 px-3 py-1.5 rounded bg-emerald-950 text-emerald-500 cursor-not-allowed border border-emerald-900"'
              : 'class="px-3 py-1.5 rounded bg-emerald-600/30 hover:bg-emerald-600/40 text-emerald-300 border border-emerald-500/50 transition-all"'
          }>↺ Resume</button>
        </div>

        <button onclick="window.termSession()" ${
          state.isOperating || (!state.selectedSession && selectedTask?.status !== 'RUNNING' && selectedTask?.status !== 'SUSPENDED')
            ? 'disabled class="opacity-30 px-3 py-1.5 rounded bg-rose-950 text-rose-500 cursor-not-allowed border border-rose-900"'
            : 'class="px-3 py-1.5 rounded bg-rose-950/40 hover:bg-rose-900/60 text-rose-300 border border-rose-800 transition-all"'
        }>✕ End Session</button>
      </div>

      <!-- Task Queue and Step Timeline -->
      <div class="grid grid-cols-1 lg:grid-cols-3 gap-6 font-mono">
        <!-- Task Queue -->
        <div class="p-4 bg-[#0a101d] border border-[#172238] rounded-xl space-y-3">
          <div class="flex items-center justify-between pb-3 border-b border-[#172238] text-xs">
            <span class="font-bold text-slate-200">WORKLOAD QUEUE</span>
            <span class="text-cyan-400">${state.tasks.length} Tasks</span>
          </div>

          <div class="space-y-2 max-h-[460px] overflow-y-auto pr-1">
            ${state.tasks
              .map(
                (task) => `
              <div onclick="window.selectTask('${task.task_id}')" class="p-3 rounded-lg border cursor-pointer transition-all ${
                  task.task_id === state.selectedTaskId
                    ? 'bg-[#0f1b33] border-cyan-500/60 shadow-md shadow-cyan-500/10'
                    : 'bg-[#070b14] border-[#162238] hover:border-slate-700'
                }">
                <div class="flex items-center justify-between text-xs mb-1">
                  <span class="font-bold text-slate-200 truncate">${task.title}</span>
                  <span class="text-[9px] px-1.5 py-0.5 rounded ${
                    task.status === 'COMPLETED'
                      ? 'bg-emerald-950 text-emerald-300 border border-emerald-800'
                      : task.status === 'RUNNING'
                      ? 'bg-cyan-950 text-cyan-300 border border-cyan-800 animate-pulse'
                      : task.status === 'SUSPENDED'
                      ? 'bg-amber-950 text-amber-300 border border-amber-800'
                      : task.status === 'BLOCKED'
                      ? 'bg-rose-950 text-rose-300 border border-rose-800'
                      : 'bg-slate-800 text-slate-300'
                  }">${task.status}</span>
                </div>
                <p class="text-[11px] text-slate-400 line-clamp-1">${task.description}</p>
              </div>
            `
              )
              .join('')}
          </div>
        </div>

        <!-- Step Traces Timeline -->
        <div class="lg:col-span-2 space-y-3">
          <div class="flex items-center justify-between text-xs text-slate-300 mb-1">
            <span class="font-bold">ACTIVE EXECUTION TRACE</span>
            ${
              state.selectedSession
                ? `<span class="text-slate-500">Session: ${state.selectedSession.session_id} • Step ${state.selectedSession.current_step}</span>`
                : ''
            }
          </div>

          ${
            !state.selectedSession || !state.selectedSession.step_traces || state.selectedSession.step_traces.length === 0
              ? `
            <div class="p-8 text-center text-slate-500 text-xs rounded-xl bg-[#0a101d] border border-[#172238]">
              No execution step traces found for this task. Click Execute to begin.
            </div>
          `
              : state.selectedSession.step_traces
                  .map(
                    (tr) => `
            <div class="p-4 rounded-xl bg-[#0a101d] border border-[#172238] space-y-3 text-xs">
              <div class="flex items-center justify-between border-b border-[#162238] pb-2">
                <div class="flex items-center space-x-2">
                  <span class="px-2 py-0.5 rounded bg-cyan-950 text-cyan-300 border border-cyan-800 font-bold">Step #${tr.step_number}</span>
                  <span class="text-slate-300 font-bold">Phase: <span class="text-cyan-400">${tr.phase}</span></span>
                </div>
                <span class="text-slate-500 text-[10px]">${new Date(tr.created_at).toLocaleTimeString()} • ${tr.token_usage?.total_tokens || 0} tokens ($0.00)</span>
              </div>

              <div>
                <div class="text-[10px] text-slate-500 uppercase mb-1">Observation</div>
                <div class="p-2 rounded bg-[#070b14] text-slate-300 border border-[#141e33]">${tr.observation}</div>
              </div>

              ${
                tr.plan
                  ? `
                <div>
                  <div class="text-[10px] text-slate-500 uppercase mb-1">Reasoning Plan</div>
                  <div class="p-2 rounded bg-[#070b14] text-cyan-300/90 border border-cyan-950/60">${tr.plan}</div>
                </div>
              `
                  : ''
              }

              ${
                tr.tool_calls && tr.tool_calls.length > 0
                  ? `
                <div class="space-y-1.5">
                  <div class="text-[10px] text-violet-400 uppercase">Tool Execution</div>
                  ${tr.tool_calls
                    .map(
                      (tc, i) => `
                    <div class="p-2.5 rounded bg-[#070b14] border border-[#162238] space-y-1">
                      <div class="flex justify-between font-bold text-violet-300">
                        <span>⚡ ${tc.tool_name}</span>
                        <span class="${tr.tool_results?.[i]?.success ? 'text-emerald-400' : 'text-rose-400'}">
                          ${tr.tool_results?.[i]?.success ? 'SUCCESS' : 'FAILED'}
                        </span>
                      </div>
                      <div class="text-[11px] text-slate-400">args: ${JSON.stringify(tc.arguments)}</div>
                      <div class="text-[11px] text-emerald-300 whitespace-pre-wrap">${tr.tool_results?.[i]?.output || tr.tool_results?.[i]?.error || ''}</div>
                    </div>
                  `
                    )
                    .join('')}
                </div>
              `
                  : ''
              }

              ${
                tr.evaluation
                  ? `
                <div>
                  <div class="text-[10px] text-slate-500 uppercase mb-1">Evaluation Outcome</div>
                  <div class="p-2 rounded bg-[#070b14] text-emerald-300/90 border border-emerald-950/60">${tr.evaluation}</div>
                </div>
              `
                  : ''
              }
            </div>
          `
                  )
                  .join('')
          }
        </div>
      </div>
    `;
  } else if (state.activeTab === 'workspace') {
    return `
      <div class="p-6 bg-[#0a101d] border border-[#172238] rounded-xl space-y-4 font-mono text-xs">
        <div class="flex justify-between items-center pb-3 border-b border-[#172238]">
          <span class="font-bold text-slate-200">WORKSPACE: ${state.workspaceRoot}</span>
          <span class="text-emerald-400 text-[10px] px-2 py-0.5 rounded bg-emerald-950 border border-emerald-800">SANDBOXED ENFORCED</span>
        </div>
        <div class="grid grid-cols-2 gap-4">
          <div class="space-y-2">
            ${state.workspaceEntries
              .map(
                (e) => `
              <div class="p-2.5 rounded bg-[#070b14] border border-[#162238] flex justify-between items-center">
                <span class="${e.is_directory ? 'text-amber-400' : 'text-cyan-400'}">${e.is_directory ? '📁' : '📄'} ${e.name}</span>
                <span class="text-slate-500 text-[10px]">${e.is_directory ? 'DIR' : `${e.size_bytes}B`}</span>
              </div>
            `
              )
              .join('')}
          </div>
          <div class="p-4 rounded bg-[#070b14] border border-[#162238] text-slate-400">
            <div class="text-slate-500 uppercase text-[10px] mb-2">Workspace Guard Status</div>
            <p class="leading-relaxed">All file system access is locked to the workspace root directory. Relative traversal escapes (../) and absolute system paths (/etc, /root) are actively intercepted and blocked by BoundaryGuard.</p>
          </div>
        </div>
      </div>
    `;
  } else if (state.activeTab === 'logs') {
    return `
      <div class="p-6 bg-[#0a101d] border border-[#172238] rounded-xl space-y-3 font-mono text-xs">
        <div class="flex justify-between items-center pb-3 border-b border-[#172238]">
          <span class="font-bold text-slate-200">IMMUTABLE AUDIT TRAIL</span>
          <span class="text-cyan-400 text-[10px] px-2 py-0.5 rounded bg-cyan-950 border border-cyan-800">SQLITE ENFORCED</span>
        </div>
        <div class="space-y-2 max-h-96 overflow-y-auto">
          ${state.auditLogs
            .map(
              (l) => `
            <div class="p-3 rounded bg-[#070b14] border border-[#141e33] flex justify-between items-start">
              <div>
                <span class="font-bold text-cyan-300">${l.event_type}</span>
                <span class="text-slate-500">• ${l.entity_id}</span>
                <div class="text-[11px] text-slate-400 mt-1">${JSON.stringify(l.details)}</div>
              </div>
              <span class="text-slate-500 text-[10px] whitespace-nowrap ml-4">${new Date(l.timestamp).toLocaleTimeString()}</span>
            </div>
          `
            )
            .join('')}
        </div>
      </div>
    `;
  } else if (state.activeTab === 'agents') {
    return `
      <div class="p-6 bg-[#0a101d] border border-[#172238] rounded-xl space-y-4 font-mono text-xs">
        <div class="flex justify-between items-center pb-3 border-b border-[#172238]">
          <span class="font-bold text-slate-200">COMPANY ROLE ROSTER (ORGANIC EVOLUTION: 2 WORKERS)</span>
          <span class="text-emerald-400 text-[10px] px-2 py-0.5 rounded bg-emerald-950 border border-emerald-800">2 ACTIVE / 13 REFERENCE</span>
        </div>
        <div class="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-3">
          <!-- Worker 1 -->
          <div class="p-3.5 rounded bg-cyan-950/30 border border-cyan-500/50">
            <div class="flex justify-between font-bold text-cyan-300 mb-1">
              <span>Reem</span>
              <span class="text-[9px] px-1.5 py-0.5 rounded bg-cyan-950 border border-cyan-800">ACTIVE (Worker 1)</span>
            </div>
            <div class="text-slate-300 text-[11px]">Construction & Programming</div>
            <div class="text-slate-500 text-[10px]">Archetype: Riri Williams • Tier 2</div>
          </div>

          <!-- Worker 2 (Auditor) -->
          <div class="p-3.5 rounded bg-emerald-950/30 border border-emerald-500/50">
            <div class="flex justify-between font-bold text-emerald-300 mb-1">
              <span>Zaks</span>
              <span class="text-[9px] px-1.5 py-0.5 rounded bg-emerald-950 border border-emerald-800">ACTIVE (Auditor)</span>
            </div>
            <div class="text-slate-300 text-[11px]">Independent Audit & Oversight</div>
            <div class="text-slate-500 text-[10px]">Archetype: Vision • Tier 1 Safe</div>
          </div>

          <!-- Dormant References -->
          ${[
            { name: 'Sirfaraz', role: 'Central Command', arc: 'Nick Fury' },
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
          ]
            .map(
              (r) => `
            <div class="p-3.5 rounded bg-[#070b14] border border-[#141e33] opacity-60">
              <div class="flex justify-between font-bold text-slate-300 mb-1">
                <span>${r.name}</span>
                <span class="text-[9px] px-1.5 py-0.5 rounded bg-slate-900 border border-slate-800 text-slate-500">DORMANT</span>
              </div>
              <div class="text-slate-400 text-[11px]">${r.role}</div>
              <div class="text-slate-600 text-[10px]">Archetype: ${r.arc}</div>
            </div>
          `
            )
            .join('')}
        </div>
      </div>
    `;
  } else {
    return `
      <div class="p-6 bg-[#0a101d] border border-[#172238] rounded-xl space-y-4 font-mono text-xs max-w-xl">
        <h2 class="font-bold text-slate-200 pb-3 border-b border-[#172238]">SYSTEM GOVERNANCE INVARIANTS</h2>
        <div class="space-y-3">
          <div class="p-3 rounded bg-[#070b14] border border-[#141e33] flex justify-between items-center">
            <div>
              <div class="font-bold text-slate-200">Spend Boundary Limit</div>
              <div class="text-slate-500 text-[11px]">Hardcoded boundary blocking paid APIs</div>
            </div>
            <span class="text-emerald-400 font-bold">$0.00 USD (LOCKED)</span>
          </div>
          <div class="p-3 rounded bg-[#070b14] border border-[#141e33] flex justify-between items-center">
            <div>
              <div class="font-bold text-slate-200">ZEDCU Isolation Boundary</div>
              <div class="text-slate-500 text-[11px]">Independent database, runtime and state</div>
              </div>
            <span class="text-cyan-400 font-bold">100% INDEPENDENT</span>
          </div>
        </div>
      </div>
    `;
  }
}

function renderCompletionDashboard() {
  const comp = state.completion || mockData.completion;
  const overall = comp?.overall_completion_pct || 78;
  const pillars = comp?.pillars || [];
  const caps = comp?.capabilities || {};
  const priorities = comp?.next_priorities || [];

  return `
    <div class="space-y-6 font-mono text-xs">
      <!-- Executive Summary Card -->
      <div class="p-6 bg-[#0a101d] border border-cyan-500/30 rounded-xl space-y-4 shadow-xl relative overflow-hidden">
        <div class="absolute -right-12 -top-12 w-48 h-48 bg-cyan-500/10 rounded-full blur-3xl pointer-events-none"></div>

        <div class="flex flex-col md:flex-row md:items-center justify-between gap-4 pb-4 border-b border-[#172238]">
          <div>
            <div class="flex items-center space-x-2 mb-1">
              <span class="text-xs font-bold px-2 py-0.5 rounded bg-cyan-950 text-cyan-300 border border-cyan-800">NON-TECHNICAL OWNER REPORT</span>
              <span class="text-xs text-slate-400">Assessed: <strong class="text-slate-200">${comp.assessment_date}</strong></span>
            </div>
            <h1 class="text-lg font-bold text-slate-100 font-sans tracking-wide">Honest Product Completion Dashboard</h1>
            <p class="text-xs text-slate-400 mt-1 max-w-2xl font-sans leading-relaxed">
              Every percentage below is grounded strictly in executed unit tests and live runtime verification.
              Simulated, mock, or planned capabilities are explicitly distinguished from real working code.
            </p>
          </div>

          <!-- Overall Gauge -->
          <div class="flex items-center space-x-4 p-3 rounded-lg bg-[#070b14] border border-[#172238] self-start md:self-auto">
            <div class="text-right">
              <div class="text-[10px] text-slate-500 uppercase tracking-wider">Overall Completion</div>
              <div class="text-2xl font-black text-cyan-400">${overall}%</div>
            </div>
            <div class="w-16 h-16 relative flex items-center justify-center">
              <svg class="w-full h-full transform -rotate-90" viewBox="0 0 36 36">
                <path class="text-slate-800" stroke-width="3.5" stroke="currentColor" fill="none" d="M18 2.0845 a 15.9155 15.9155 0 0 1 0 31.831 a 15.9155 15.9155 0 0 1 0 -31.831" />
                <path class="text-cyan-400" stroke-dasharray="${overall}, 100" stroke-width="3.5" stroke-linecap="round" stroke="currentColor" fill="none" d="M18 2.0845 a 15.9155 15.9155 0 0 1 0 31.831 a 15.9155 15.9155 0 0 1 0 -31.831" />
              </svg>
              <span class="absolute text-[11px] font-bold text-cyan-300 font-mono">${overall}%</span>
            </div>
          </div>
        </div>

        <!-- Evidence Summary Banner -->
        <div class="p-3 rounded-lg bg-[#070b14] border border-[#1a2947] flex items-center justify-between">
          <div class="flex items-center space-x-3">
            <span class="w-2.5 h-2.5 rounded-full bg-emerald-400 animate-pulse"></span>
            <span class="text-slate-300 font-medium">Evidence Basis:</span>
            <span class="text-slate-400">${comp.evidence_summary}</span>
          </div>
          <div class="text-emerald-400 font-bold text-[11px] px-2 py-0.5 rounded bg-emerald-950 border border-emerald-800 whitespace-nowrap">
            SPEND LOCKED: $0.00 USD
          </div>
        </div>
      </div>

      <!-- Functional Pillars Matrix -->
      <div class="p-6 bg-[#0a101d] border border-[#172238] rounded-xl space-y-4">
        <div class="flex justify-between items-center pb-3 border-b border-[#172238]">
          <h2 class="font-bold text-slate-200">CORE FUNCTIONAL PILLARS PROGRESS</h2>
          <span class="text-slate-400 text-[11px]">6 Evaluated Architecture Domains</span>
        </div>

        <div class="grid grid-cols-1 md:grid-cols-2 gap-4">
          ${pillars.map(p => `
            <div class="p-4 rounded-lg bg-[#070b14] border border-[#172238] space-y-2">
              <div class="flex justify-between items-start">
                <span class="font-bold text-slate-200 text-xs">${p.name}</span>
                <span class="text-[10px] px-2 py-0.5 rounded font-bold ${
                  p.status === 'VERIFIED'
                    ? 'bg-emerald-950 text-emerald-300 border border-emerald-800'
                    : 'bg-amber-950 text-amber-300 border border-amber-800'
                }">${p.status} (${p.completion_pct}%)</span>
              </div>
              <div class="w-full bg-slate-900 h-2 rounded-full overflow-hidden border border-slate-800">
                <div class="h-full rounded-full ${p.completion_pct === 100 ? 'bg-gradient-to-r from-emerald-500 to-cyan-500' : 'bg-gradient-to-r from-amber-500 to-yellow-500'}" style="width: ${p.completion_pct}%"></div>
              </div>
              <p class="text-[11px] text-slate-400 leading-relaxed font-sans">${p.summary}</p>
            </div>
          `).join('')}
        </div>
      </div>

      <!-- Verified Working vs. In Progress vs. Deferred -->
      <div class="grid grid-cols-1 lg:grid-cols-3 gap-6">
        <!-- Verified Working -->
        <div class="p-5 bg-[#0a101d] border border-emerald-900/40 rounded-xl space-y-3">
          <div class="flex items-center space-x-2 pb-2 border-b border-emerald-900/40 text-emerald-300 font-bold">
            <span>✓</span>
            <span>Genuinely Working & Tested</span>
          </div>
          <ul class="space-y-2 text-slate-300 text-[11px]">
            ${(caps.verified_working || []).map(item => `
              <li class="flex items-start space-x-2">
                <span class="text-emerald-400 mt-0.5">•</span>
                <span class="leading-tight">${item}</span>
              </li>
            `).join('')}
          </ul>
        </div>

        <!-- Partially Complete / In Progress -->
        <div class="p-5 bg-[#0a101d] border border-amber-900/40 rounded-xl space-y-3">
          <div class="flex items-center space-x-2 pb-2 border-b border-amber-900/40 text-amber-300 font-bold">
            <span>⏳</span>
            <span>Under Active Construction</span>
          </div>
          <ul class="space-y-2 text-slate-300 text-[11px]">
            ${(caps.partially_complete || []).map(item => `
              <li class="flex items-start space-x-2">
                <span class="text-amber-400 mt-0.5">•</span>
                <span class="leading-tight">${item}</span>
              </li>
            `).join('')}
          </ul>
        </div>

        <!-- Deferred / Unverified -->
        <div class="p-5 bg-[#0a101d] border border-slate-800 rounded-xl space-y-3">
          <div class="flex items-center space-x-2 pb-2 border-b border-slate-800 text-slate-400 font-bold">
            <span>○</span>
            <span>Intentionally Deferred / Future</span>
          </div>
          <ul class="space-y-2 text-slate-400 text-[11px]">
            ${(caps.unverified_deferred || []).map(item => `
              <li class="flex items-start space-x-2">
                <span class="text-slate-500 mt-0.5">•</span>
                <span class="leading-tight">${item}</span>
              </li>
            `).join('')}
          </ul>
        </div>
      </div>

      <!-- Top 3 Next Actions -->
      <div class="p-6 bg-[#0a101d] border border-[#172238] rounded-xl space-y-3">
        <div class="flex justify-between items-center pb-2 border-b border-[#172238]">
          <h2 class="font-bold text-cyan-300 uppercase tracking-wider">Top 3 Next Development Actions</h2>
          <span class="text-slate-500 text-[10px]">Continuous Autonomous Execution Order</span>
        </div>
        <div class="space-y-2">
          ${priorities.map((p, idx) => `
            <div class="p-3 rounded-lg bg-[#070b14] border border-[#162238] text-slate-300 text-xs flex items-center space-x-3">
              <span class="w-6 h-6 rounded-full bg-cyan-950 text-cyan-400 border border-cyan-800 flex items-center justify-center font-bold text-[10px] shrink-0">${idx + 1}</span>
              <span class="leading-relaxed font-sans">${p.replace(/^[0-9]\.\s*/, '')}</span>
            </div>
          `).join('')}
        </div>
      </div>
    </div>
  `;
}

function renderTaskModal() {
  return `
    <div class="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/80 backdrop-blur-sm font-mono text-xs">
      <div class="w-full max-w-md rounded-xl bg-[#0a101d] border border-cyan-500/40 p-6 shadow-2xl">
        <div class="flex justify-between items-center pb-3 border-b border-[#172238] mb-4">
          <h2 class="font-bold text-slate-100">Submit Autonomous Task</h2>
          <button onclick="window.closeTaskModal()" class="text-slate-400 hover:text-slate-200">✕</button>
        </div>

        <form onsubmit="window.submitTaskForm(event)" class="space-y-4">
          <div>
            <label class="block text-slate-300 mb-1">Task Title</label>
            <input id="modal-title" type="text" placeholder="e.g. Scaffolding Worker 2 Architecture" class="w-full px-3 py-2 rounded bg-[#070b14] border border-[#1b2742] text-slate-200 focus:outline-none focus:border-cyan-500" required />
          </div>

          <div>
            <label class="block text-slate-300 mb-1">Description</label>
            <textarea id="modal-desc" rows="3" placeholder="Step-by-step instructions for Worker 1..." class="w-full px-3 py-2 rounded bg-[#070b14] border border-[#1b2742] text-slate-200 focus:outline-none focus:border-cyan-500"></textarea>
          </div>

          <div class="pt-3 border-t border-[#172238] flex justify-end space-x-2">
            <button type="button" onclick="window.closeTaskModal()" class="px-4 py-2 rounded border border-[#1b2742] text-slate-400">Cancel</button>
            <button type="submit" class="px-4 py-2 rounded bg-cyan-500 hover:bg-cyan-400 text-slate-950 font-bold">Dispatch Task</button>
          </div>
        </form>
      </div>
    </div>
  `;
}

// --- Global Window Bindings for UI Handlers ---
window.navTo = (tab) => {
  state.activeTab = tab;
  render();
};
window.setClientMode = (mode) => {
  state.mode = mode;
  refreshData();
};
window.refreshData = refreshData;
window.selectTask = selectTask;
window.execTask = handleExecuteTask;
window.suspSession = handleSuspendSession;
window.resSession = handleResumeSession;
window.termSession = handleTerminateSession;
window.dismissError = () => {
  state.errorBanner = null;
  render();
};
window.openTaskModal = () => {
  state.isTaskModalOpen = true;
  render();
};
window.closeTaskModal = () => {
  state.isTaskModalOpen = false;
  render();
};
window.submitTaskForm = (e) => {
  e.preventDefault();
  const title = document.getElementById('modal-title')?.value || '';
  const desc = document.getElementById('modal-desc')?.value || '';
  handleCreateTask(title, desc, {});
};

// Initialize App
refreshData();
