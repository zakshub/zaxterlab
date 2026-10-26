// ZaxterLab Form 4: Interactive DAG Studio (Node/Canvas Studio Controller)
// Exposes 100% real operations through interactive SVG node-canvas and topological graph execution.

const studioState = {
  tasks: [],
  specialists: [],
  health: null,
  nodePositions: {}, // taskId -> { x, y }
  selectedTaskId: null,
  panX: 80,
  panY: 80,
  scale: 1.0,
  isPanning: false,
  startPan: { x: 0, y: 0 },
  draggedNodeId: null,
  dragOffset: { x: 0, y: 0 },
};

const NODE_WIDTH = 230;
const NODE_HEIGHT = 120;

async function api(path, options = {}) {
  const res = await fetch(path, {
    headers: { 'Content-Type': 'application/json', ...(options.headers || {}) },
    ...options,
  });
  const data = await res.json().catch(() => ({ error: `HTTP ${res.status}` }));
  if (!res.ok) {
    throw new Error(data.error?.message || data.error || `HTTP ${res.status}`);
  }
  return data;
}

function showToast(msg, type = 'info') {
  const c = document.getElementById('studio-toast-container');
  if (!c) return;
  const t = document.createElement('div');
  t.className = `toast ${type}`;
  t.textContent = msg;
  c.appendChild(t);
  setTimeout(() => t.remove(), 3000);
}

function escapeHtml(str) {
  return String(str ?? '')
    .replace(/&/g, '&amp;')
    .replace(/</g, '&lt;')
    .replace(/>/g, '&gt;')
    .replace(/"/g, '&quot;');
}

async function refreshAll() {
  try {
    const [h, tRes, sRes] = await Promise.all([
      api('/api/health'),
      api('/api/tasks'),
      api('/api/specialists'),
    ]);
    studioState.health = h;
    studioState.tasks = tRes.tasks || [];
    studioState.specialists = sRes.specialists || [];

    updateTelemetry();
    calculateMissingPositions();
    renderNodes();
    renderWires();
    populateSelects();

    if (studioState.selectedTaskId) {
      inspectTask(studioState.selectedTaskId);
    }
  } catch (err) {
    showToast(`Error: ${err.message}`, 'error');
  }
}

function updateTelemetry() {
  const spend = studioState.health?.spend_guard || {};
  const cost = Number(spend.cumulative_spent_usd || 0).toFixed(2);
  const el = document.getElementById('studio-spend');
  if (el) el.textContent = `Spend: $${cost} (LOCKED $0.00)`;
}

function populateSelects() {
  const specSelect = document.getElementById('node-spec');
  const depsSelect = document.getElementById('node-deps-select');

  if (specSelect && specSelect.children.length === 0) {
    specSelect.innerHTML = studioState.specialists
      .map((s) => `<option value="${escapeHtml(s.name)}">${escapeHtml(s.name)} (${escapeHtml(s.department)})</option>`)
      .join('');
  }

  if (depsSelect) {
    depsSelect.innerHTML = studioState.tasks
      .map((t) => `<option value="${escapeHtml(t.task_id)}">${escapeHtml(t.title)} (${escapeHtml(t.task_id)})</option>`)
      .join('');
  }
}

// 1. Topological Auto-Layout Algorithm
function calculateMissingPositions() {
  // Compute in-degree and adjacency for layering
  const taskMap = {};
  studioState.tasks.forEach((t) => (taskMap[t.task_id] = t));

  // Depth calculation
  const depths = {};
  function getDepth(id, visited = new Set()) {
    if (depths[id] != null) return depths[id];
    if (visited.has(id)) return 0;
    visited.add(id);

    const task = taskMap[id];
    if (!task || !task.depends_on || task.depends_on.length === 0) {
      depths[id] = 0;
      return 0;
    }
    let maxParentDepth = 0;
    for (const dep of task.depends_on) {
      if (taskMap[dep]) {
        maxParentDepth = Math.max(maxParentDepth, getDepth(dep, visited) + 1);
      }
    }
    depths[id] = maxParentDepth;
    return maxParentDepth;
  }

  studioState.tasks.forEach((t) => getDepth(t.task_id));

  // Group by depth layer
  const layers = {};
  studioState.tasks.forEach((t) => {
    const d = depths[t.task_id] || 0;
    if (!layers[d]) layers[d] = [];
    layers[d].push(t.task_id);
  });

  // Assign x, y positions
  const X_SPACING = 320;
  const Y_SPACING = 150;
  Object.keys(layers).forEach((layerStr) => {
    const layer = Number(layerStr);
    const nodeIds = layers[layer];
    nodeIds.forEach((id, rowIdx) => {
      if (!studioState.nodePositions[id]) {
        studioState.nodePositions[id] = {
          x: 100 + layer * X_SPACING,
          y: 100 + rowIdx * Y_SPACING,
        };
      }
    });
  });
}

function autoLayoutAll() {
  studioState.nodePositions = {};
  calculateMissingPositions();
  renderNodes();
  renderWires();
  showToast('Graph auto-arranged by topological dependencies.', 'info');
}

// 2. Render Nodes
function renderNodes() {
  const container = document.getElementById('nodes-container');
  if (!container) return;

  container.innerHTML = '';
  studioState.tasks.forEach((task) => {
    const pos = studioState.nodePositions[task.task_id] || { x: 100, y: 100 };
    const status = (task.status || 'QUEUED').toLowerCase();
    const isSelected = task.task_id === studioState.selectedTaskId;

    const nodeEl = document.createElement('div');
    nodeEl.className = `dag-node status-${status} ${isSelected ? 'selected' : ''}`;
    nodeEl.id = `node-${task.task_id}`;
    nodeEl.style.left = `${pos.x}px`;
    nodeEl.style.top = `${pos.y}px`;

    nodeEl.innerHTML = `
      <div class="port port-input"></div>
      <div class="port port-output"></div>
      <div class="node-header-bar">
        <span class="node-specialist">
          <span class="node-status-dot ${status}"></span>
          ${escapeHtml(task.assigned_specialist || 'Agent')}
        </span>
        <button class="btn-icon btn-sm btn-node-exec" title="Execute this node" data-exec="${escapeHtml(task.task_id)}">&#9658;</button>
      </div>
      <div class="node-body">
        <div class="node-title">${escapeHtml(task.title)}</div>
        <div class="node-id">${escapeHtml(task.task_id)}</div>
      </div>
    `;

    // Select node on click
    nodeEl.addEventListener('click', (e) => {
      if (e.target.closest('.btn-node-exec')) return;
      selectNode(task.task_id);
    });

    // Drag node handler
    const headerBar = nodeEl.querySelector('.node-header-bar');
    headerBar.addEventListener('mousedown', (e) => {
      e.stopPropagation();
      studioState.draggedNodeId = task.task_id;
      const currentPos = studioState.nodePositions[task.task_id];
      studioState.dragOffset = {
        x: (e.clientX - studioState.panX) / studioState.scale - currentPos.x,
        y: (e.clientY - studioState.panY) / studioState.scale - currentPos.y,
      };
    });

    // Execute button on node
    const execBtn = nodeEl.querySelector('.btn-node-exec');
    if (execBtn) {
      execBtn.addEventListener('click', async (e) => {
        e.stopPropagation();
        await executeNode(task.task_id);
      });
    }

    container.appendChild(nodeEl);
  });
}

// 3. Render SVG Bezier Connections
function renderWires() {
  const g = document.getElementById('connections-group');
  if (!g) return;

  g.innerHTML = '';
  studioState.tasks.forEach((task) => {
    const dstPos = studioState.nodePositions[task.task_id];
    if (!dstPos) return;

    (task.depends_on || []).forEach((depId) => {
      const srcPos = studioState.nodePositions[depId];
      if (!srcPos) return;

      // Source output port -> Destination input port
      const x1 = srcPos.x + NODE_WIDTH;
      const y1 = srcPos.y + NODE_HEIGHT / 2;
      const x2 = dstPos.x;
      const y2 = dstPos.y + NODE_HEIGHT / 2;

      const dx = Math.max(40, (x2 - x1) * 0.5);
      const pathD = `M ${x1} ${y1} C ${x1 + dx} ${y1}, ${x2 - dx} ${y2}, ${x2} ${y2}`;

      const pathEl = document.createElementNS('http://www.w3.org/2000/svg', 'path');
      const isRunning = task.status === 'RUNNING';
      pathEl.setAttribute('d', pathD);
      pathEl.setAttribute('class', `dag-wire ${isRunning ? 'active' : ''}`);
      pathEl.setAttribute('marker-end', isRunning ? 'url(#arrow-active)' : 'url(#arrow)');
      g.appendChild(pathEl);
    });
  });
}

// 4. Node Inspector
function selectNode(taskId) {
  studioState.selectedTaskId = taskId;
  document.querySelectorAll('.dag-node').forEach((el) => el.classList.remove('selected'));
  document.getElementById(`node-${taskId}`)?.classList.add('selected');
  inspectTask(taskId);
}

async function inspectTask(taskId) {
  const panel = document.getElementById('node-inspector');
  if (!panel) return;

  const task = studioState.tasks.find((t) => t.task_id === taskId);
  if (!task) return;

  panel.classList.remove('hidden');
  document.getElementById('insp-title').textContent = task.title;
  document.getElementById('insp-id').textContent = task.task_id;
  document.getElementById('insp-specialist').textContent = `${task.assigned_specialist || 'Reem'} (${task.department || 'Engineering'})`;
  document.getElementById('insp-status').textContent = task.status;
  document.getElementById('insp-desc').textContent = task.description || 'No description provided.';

  const depsContainer = document.getElementById('insp-deps');
  if (depsContainer) {
    depsContainer.innerHTML = (task.depends_on || []).length > 0
      ? (task.depends_on || []).map((d) => `<code>${escapeHtml(d)}</code>`).join(' ')
      : '<span style="color:var(--text-dim);font-size:11px;">Root node (No prerequisites)</span>';
  }

  // Load session traces
  const sessContainer = document.getElementById('insp-sessions');
  if (sessContainer) {
    sessContainer.innerHTML = '<div class="empty-state">Loading traces...</div>';
    try {
      const res = await api(`/api/tasks/${encodeURIComponent(taskId)}/sessions`);
      const sessions = res.sessions || [];
      if (sessions.length === 0) {
        sessContainer.innerHTML = '<div class="empty-state">No execution sessions recorded yet.</div>';
      } else {
        sessContainer.innerHTML = sessions
          .map(
            (s) => `
          <div style="background:#111827;padding:8px;border-radius:4px;border:1px solid #1e293b;font-size:11px;">
            <div>Session: <code>${escapeHtml(s.session_id)}</code> &bull; ${escapeHtml(s.status)}</div>
            <div>Tokens: <strong>${s.total_tokens_used || 0}</strong> &bull; Cost: <strong>$${Number(s.total_cost_usd || 0).toFixed(2)}</strong></div>
            <div style="margin-top:4px;">
              ${(s.steps || []).map((st, i) => `<div>Step ${i + 1}: ${escapeHtml(st.tool_action || st.thought || 'Step')} &rarr; ${escapeHtml(st.status)}</div>`).join('')}
            </div>
          </div>
        `
          )
          .join('');
      }
    } catch (e) {
      sessContainer.innerHTML = `<div class="empty-state">Error: ${e.message}</div>`;
    }
  }
}

// 5. Operations
async function executeNode(taskId) {
  showToast(`Executing task node ${taskId}...`, 'info');
  try {
    const res = await api(`/api/tasks/${encodeURIComponent(taskId)}/execute`, { method: 'POST', body: '{}' });
    showToast(`Task ${taskId} completed!`, 'success');
    await refreshAll();
  } catch (e) {
    showToast(`Execution failed: ${e.message}`, 'error');
  }
}

async function runDagPipeline() {
  showToast('Orchestrating entire DAG graph topologically...', 'info');
  try {
    const res = await api('/api/pipeline/run', { method: 'POST', body: '{}' });
    showToast(`DAG Pipeline Complete: ${res.succeeded_count} succeeded, ${res.failed_count} failed!`, 'success');
    await refreshAll();
  } catch (e) {
    showToast(`Pipeline Error: ${e.message}`, 'error');
  }
}

async function runTwoStagePipeline() {
  showToast('Running 2-Stage Multi-Worker Pipeline...', 'info');
  try {
    const res = await api('/api/pipeline/run', {
      method: 'POST',
      body: JSON.stringify({ module_name: 'payment_engine', feature_spec: 'Double-entry balance check' }),
    });
    showToast('2-Stage Pipeline Complete & Audited!', 'success');
    await refreshAll();
  } catch (e) {
    showToast(`Error: ${e.message}`, 'error');
  }
}

async function loadSaasTemplate() {
  showToast('Generating 5-Department SaaS Venture Graph...', 'info');
  try {
    const slug = Math.random().toString(36).substring(2, 6);
    const res = await api('/api/project/saas', {
      method: 'POST',
      body: JSON.stringify({
        name: `VentureNode ${slug.toUpperCase()}`,
        domain: 'Cloud Infrastructure',
        requirements: 'Distributed consensus and telemetry pipeline',
      }),
    });
    showToast(`SaaS Venture "${res.project_name}" generated with 5 department milestones!`, 'success');
    await refreshAll();
    autoLayoutAll();
  } catch (e) {
    showToast(`SaaS Error: ${e.message}`, 'error');
  }
}

// 6. Viewport Pan & Zoom
function applyTransform() {
  const stage = document.getElementById('canvas-stage');
  const label = document.getElementById('zoom-label');
  if (stage) {
    stage.style.transform = `translate(${studioState.panX}px, ${studioState.panY}px) scale(${studioState.scale})`;
  }
  if (label) {
    label.textContent = `${Math.round(studioState.scale * 100)}%`;
  }
}

function bindCanvasControls() {
  const viewport = document.getElementById('canvas-viewport');
  if (!viewport) return;

  viewport.addEventListener('mousedown', (e) => {
    if (e.target.closest('.dag-node') || e.target.closest('#node-inspector')) return;
    studioState.isPanning = true;
    studioState.startPan = { x: e.clientX - studioState.panX, y: e.clientY - studioState.panY };
  });

  window.addEventListener('mousemove', (e) => {
    // 1. Pan
    if (studioState.isPanning) {
      studioState.panX = e.clientX - studioState.startPan.x;
      studioState.panY = e.clientY - studioState.startPan.y;
      applyTransform();
    }
    // 2. Drag Node
    if (studioState.draggedNodeId) {
      const id = studioState.draggedNodeId;
      const newX = Math.round((e.clientX - studioState.panX) / studioState.scale - studioState.dragOffset.x);
      const newY = Math.round((e.clientY - studioState.panY) / studioState.scale - studioState.dragOffset.y);
      studioState.nodePositions[id] = { x: newX, y: newY };

      const nodeEl = document.getElementById(`node-${id}`);
      if (nodeEl) {
        nodeEl.style.left = `${newX}px`;
        nodeEl.style.top = `${newY}px`;
      }
      renderWires();
    }
  });

  window.addEventListener('mouseup', () => {
    studioState.isPanning = false;
    studioState.draggedNodeId = null;
  });

  // Mouse wheel zoom
  viewport.addEventListener(
    'wheel',
    (e) => {
      e.preventDefault();
      const zoomFactor = e.deltaY < 0 ? 1.08 : 0.92;
      const newScale = Math.min(2.5, Math.max(0.3, studioState.scale * zoomFactor));

      const rect = viewport.getBoundingClientRect();
      const mouseX = e.clientX - rect.left;
      const mouseY = e.clientY - rect.top;

      studioState.panX = mouseX - (mouseX - studioState.panX) * (newScale / studioState.scale);
      studioState.panY = mouseY - (mouseY - studioState.panY) * (newScale / studioState.scale);
      studioState.scale = newScale;
      applyTransform();
    },
    { passive: false }
  );

  // Zoom buttons
  document.getElementById('btn-zoom-in')?.addEventListener('click', () => {
    studioState.scale = Math.min(2.5, studioState.scale * 1.2);
    applyTransform();
  });
  document.getElementById('btn-zoom-out')?.addEventListener('click', () => {
    studioState.scale = Math.max(0.3, studioState.scale / 1.2);
    applyTransform();
  });
  document.getElementById('btn-zoom-reset')?.addEventListener('click', () => {
    studioState.scale = 1.0;
    studioState.panX = 80;
    studioState.panY = 80;
    applyTransform();
  });

  // Action buttons
  document.getElementById('btn-refresh')?.addEventListener('click', () => refreshAll());
  document.getElementById('btn-auto-layout')?.addEventListener('click', autoLayoutAll);
  document.getElementById('btn-run-dag')?.addEventListener('click', runDagPipeline);
  document.getElementById('btn-pipeline-2stage')?.addEventListener('click', runTwoStagePipeline);
  document.getElementById('btn-template-saas')?.addEventListener('click', loadSaasTemplate);

  // Inspector buttons
  document.getElementById('btn-close-inspector')?.addEventListener('click', () => {
    document.getElementById('node-inspector')?.classList.add('hidden');
    studioState.selectedTaskId = null;
    document.querySelectorAll('.dag-node').forEach((el) => el.classList.remove('selected'));
  });

  document.getElementById('btn-exec-selected-node')?.addEventListener('click', async () => {
    if (studioState.selectedTaskId) {
      await executeNode(studioState.selectedTaskId);
    }
  });

  document.getElementById('btn-add-downstream')?.addEventListener('click', () => {
    if (studioState.selectedTaskId) {
      document.getElementById('modal-add-node')?.classList.remove('hidden');
      const depsSelect = document.getElementById('node-deps-select');
      if (depsSelect) {
        for (let opt of depsSelect.options) {
          opt.selected = opt.value === studioState.selectedTaskId;
        }
      }
    }
  });

  // Add Node Modal
  document.getElementById('btn-add-node')?.addEventListener('click', () => {
    document.getElementById('modal-add-node')?.classList.remove('hidden');
  });

  document.querySelectorAll('.btn-close-modal').forEach((btn) => {
    btn.onclick = () => {
      const modalId = btn.getAttribute('data-modal');
      document.getElementById(modalId)?.classList.add('hidden');
    };
  });

  const formNewNode = document.getElementById('form-new-node');
  if (formNewNode) {
    formNewNode.onsubmit = async (e) => {
      e.preventDefault();
      const title = document.getElementById('node-title').value.trim();
      const specialist = document.getElementById('node-spec').value;
      const desc = document.getElementById('node-desc').value.trim();
      const depsSelect = document.getElementById('node-deps-select');
      const deps = Array.from(depsSelect.selectedOptions).map((o) => o.value);

      showToast(`Adding task node "${title}"...`, 'info');
      try {
        const res = await api('/api/tasks', {
          method: 'POST',
          body: JSON.stringify({ title, description: desc, assigned_specialist: specialist, depends_on: deps }),
        });
        showToast(`Node ${res.task?.task_id} added to graph!`, 'success');
        document.getElementById('modal-add-node')?.classList.add('hidden');
        formNewNode.reset();
        await refreshAll();
      } catch (err) {
        showToast(`Add node failed: ${err.message}`, 'error');
      }
    };
  }
}

// Start
applyTransform();
bindCanvasControls();
refreshAll();
