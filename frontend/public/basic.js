// ZaxterLab Form 2: Basic Graphical Interface (Utilitarian Desktop GUI Script)
// Exposes 100% real operations through native desktop-style window frames.

const state = {
  health: null,
  tasks: [],
  projects: [],
  specialists: [],
  auditLogs: [],
  workspaceDir: '',
  workspaceFiles: [],
  selectedFile: null,
  busy: false,
};

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

function logConsole(title, data = null) {
  const el = document.getElementById('console-output');
  const statusEl = document.getElementById('console-status');
  if (!el) return;

  const ts = new Date().toLocaleTimeString();
  let text = `[${ts}] ${title}\n`;
  if (data) {
    text += typeof data === 'string' ? data : JSON.stringify(data, null, 2);
    text += '\n';
  }
  el.textContent = text + el.textContent;
  if (statusEl) statusEl.textContent = title.slice(0, 35);
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
    const [h, tRes, pRes, sRes, aRes, fRes] = await Promise.all([
      api('/api/health'),
      api('/api/tasks'),
      api('/api/projects'),
      api('/api/specialists'),
      api('/api/audit-logs?limit=30'),
      api(`/api/workspace/files?subdir=${encodeURIComponent(state.workspaceDir)}`),
    ]);

    state.health = h;
    state.tasks = tRes.tasks || [];
    state.projects = pRes.projects || [];
    state.specialists = sRes.specialists || [];
    state.auditLogs = aRes.audit_logs || [];
    state.workspaceFiles = fRes.entries || [];

    renderMetrics();
    renderTasks();
    renderSpecialists();
    renderFiles();
    renderAudit();
  } catch (err) {
    logConsole(`Refresh Error: ${err.message}`);
  }
}

function renderMetrics() {
  const h = state.health || {};
  const spend = h.spend_guard || {};
  const cost = Number(spend.cumulative_spent_usd || 0).toFixed(2);
  const max = Number(spend.authorized_spend_usd || 0).toFixed(2);

  document.getElementById('val-health').textContent = (h.status || 'HEALTHY').toUpperCase();
  document.getElementById('val-spend').textContent = `$${cost} (LOCKED $${max})`;
  document.getElementById('val-specialists').textContent = state.specialists.length;
  document.getElementById('val-tasks').textContent = state.tasks.length;
  document.getElementById('val-projects').textContent = state.projects.length;
  document.getElementById('spend-indicator').textContent = `Spend: $${cost} / $${max}`;
  document.getElementById('spec-count').textContent = state.specialists.length;

  // Populate specialist dropdown
  const select = document.getElementById('task-specialist');
  if (select && select.children.length === 0) {
    select.innerHTML = state.specialists
      .map((s) => `<option value="${escapeHtml(s.name)}">${escapeHtml(s.name)} (${escapeHtml(s.department)})</option>`)
      .join('');
  }
}

function renderTasks() {
  const tbody = document.getElementById('tasks-tbody');
  if (!tbody) return;

  if (state.tasks.length === 0) {
    tbody.innerHTML = `<tr><td colspan="5" class="empty-state">No tasks in queue. Create one above.</td></tr>`;
    return;
  }

  tbody.innerHTML = state.tasks
    .map((t) => {
      const s = String(t.status || 'PENDING').toLowerCase();
      return `
        <tr>
          <td><code>${escapeHtml(t.task_id)}</code></td>
          <td><strong>${escapeHtml(t.title)}</strong></td>
          <td>${escapeHtml(t.assigned_specialist || '-')}</td>
          <td><span class="status-badge ${escapeHtml(s)}">${escapeHtml(t.status)}</span></td>
          <td>
            <button class="btn-sm primary" data-exec-task="${escapeHtml(t.task_id)}">Execute</button>
            <button class="btn-sm" data-trace-task="${escapeHtml(t.task_id)}">Trace</button>
          </td>
        </tr>
      `;
    })
    .join('');

  tbody.querySelectorAll('[data-exec-task]').forEach((btn) => {
    btn.onclick = async () => {
      const id = btn.getAttribute('data-exec-task');
      logConsole(`Executing task ${id}...`);
      try {
        const res = await api(`/api/tasks/${encodeURIComponent(id)}/execute`, { method: 'POST', body: '{}' });
        logConsole(`Task ${id} executed successfully:`, res);
        await refreshAll();
      } catch (e) {
        logConsole(`Task execution error: ${e.message}`);
      }
    };
  });

  tbody.querySelectorAll('[data-trace-task]').forEach((btn) => {
    btn.onclick = async () => {
      const id = btn.getAttribute('data-trace-task');
      try {
        const res = await api(`/api/tasks/${encodeURIComponent(id)}/sessions`);
        logConsole(`Execution Sessions & Step Traces for ${id}:`, res);
      } catch (e) {
        logConsole(`Trace error: ${e.message}`);
      }
    };
  });
}

function renderSpecialists() {
  const tbody = document.getElementById('specialists-tbody');
  if (!tbody) return;

  tbody.innerHTML = state.specialists
    .map(
      (s) => `
    <tr>
      <td><strong>${escapeHtml(s.name)}</strong></td>
      <td>${escapeHtml(s.role)}</td>
      <td>${escapeHtml(s.department)}</td>
      <td><code>${escapeHtml(s.permission_tier)}</code></td>
      <td><span class="status-badge available">${escapeHtml(s.runtime_status || 'AVAILABLE')}</span></td>
    </tr>
  `
    )
    .join('');
}

function renderFiles() {
  const list = document.getElementById('files-list');
  const dirLabel = document.getElementById('current-dir-label');
  if (!list) return;

  if (dirLabel) dirLabel.textContent = state.workspaceDir ? `./${state.workspaceDir}` : './';

  if (state.workspaceFiles.length === 0) {
    list.innerHTML = `<li class="empty-state">No files in this directory.</li>`;
    return;
  }

  list.innerHTML = state.workspaceFiles
    .map((f) => {
      const icon = f.type === 'directory' ? '&#128193;' : '&#128196;';
      return `<li data-path="${escapeHtml(f.relative_path)}" data-type="${escapeHtml(f.type)}">
        <span>${icon}</span>
        <strong>${escapeHtml(f.name)}</strong>
        <span style="margin-left:auto;font-size:10px;color:#777;">${f.size_bytes != null ? `${f.size_bytes}B` : ''}</span>
      </li>`;
    })
    .join('');

  list.querySelectorAll('li[data-path]').forEach((li) => {
    li.onclick = async () => {
      const path = li.getAttribute('data-path');
      const type = li.getAttribute('data-type');
      if (type === 'directory') {
        state.workspaceDir = path;
        await refreshAll();
      } else {
        list.querySelectorAll('li').forEach((el) => el.classList.remove('selected'));
        li.classList.add('selected');
        await readFile(path);
      }
    };
  });
}

async function readFile(relPath) {
  const label = document.getElementById('selected-file-label');
  const view = document.getElementById('file-content-view');
  if (label) label.textContent = `Reading: ${relPath}`;
  try {
    const res = await api(`/api/workspace/file-content?path=${encodeURIComponent(relPath)}`);
    if (view) view.textContent = res.content || '(Empty file)';
    logConsole(`Opened file: ${relPath} (${res.size_bytes} bytes)`);
  } catch (err) {
    if (view) view.textContent = `Error reading file: ${err.message}`;
    logConsole(`File read error: ${err.message}`);
  }
}

function renderAudit() {
  const tbody = document.getElementById('audit-tbody');
  if (!tbody) return;

  tbody.innerHTML = state.auditLogs
    .slice(-25)
    .reverse()
    .map(
      (l) => `
    <tr>
      <td><code>${escapeHtml(l.id)}</code></td>
      <td>${escapeHtml((l.timestamp || '').slice(0, 19))}</td>
      <td><strong>${escapeHtml(l.event_type)}</strong></td>
      <td><code>${escapeHtml(l.entity_id)}</code></td>
      <td>${escapeHtml(typeof l.details === 'string' ? l.details : JSON.stringify(l.details || {}))}</td>
    </tr>
  `
    )
    .join('');
}

function bindGuiEvents() {
  // Quick pipeline
  const btnPipe = document.getElementById('btn-quick-pipeline');
  const menuPipe = document.getElementById('menu-run-pipeline');
  const runPipeHandler = async () => {
    logConsole('Running 2-Stage Multi-Worker DAG Pipeline...');
    try {
      const res = await api('/api/pipeline/run', {
        method: 'POST',
        body: JSON.stringify({ module_name: 'payment_engine', feature_spec: 'Double-entry ledger verification' }),
      });
      logConsole('2-Stage Pipeline Finished:', res);
      await refreshAll();
    } catch (e) {
      logConsole(`Pipeline Error: ${e.message}`);
    }
  };
  if (btnPipe) btnPipe.onclick = runPipeHandler;
  if (menuPipe) menuPipe.onclick = runPipeHandler;

  // Refresh
  const btnRefresh = document.querySelectorAll('.btn-refresh-data, #menu-refresh');
  btnRefresh.forEach((b) => (b.onclick = () => refreshAll()));

  // Internal transform
  const btnInternal = document.getElementById('btn-quick-internal');
  const menuInternal = document.getElementById('menu-run-internal');
  const runInternalHandler = async () => {
    logConsole('Executing Section 18 Internal Transformation DAG (7 Tasks)...');
    try {
      const res = await api('/api/projects/internal-transformation', { method: 'POST', body: '{}' });
      logConsole('Internal Transformation Completed:', res);
      await refreshAll();
    } catch (e) {
      logConsole(`Transformation Error: ${e.message}`);
    }
  };
  if (btnInternal) btnInternal.onclick = runInternalHandler;
  if (menuInternal) menuInternal.onclick = runInternalHandler;

  // Evaluator
  const btnEval = document.getElementById('btn-quick-eval');
  const menuEval = document.getElementById('menu-run-evaluator');
  const runEvalHandler = async () => {
    logConsole('Running Workload Evaluator...');
    try {
      const res = await api('/api/evaluator/evaluate', { method: 'POST', body: '{}' });
      logConsole('Workload Evaluation Results:', res);
      await refreshAll();
    } catch (e) {
      logConsole(`Evaluator Error: ${e.message}`);
    }
  };
  if (btnEval) btnEval.onclick = runEvalHandler;
  if (menuEval) menuEval.onclick = runEvalHandler;

  // Task form
  const formTask = document.getElementById('task-create-form');
  const btnExecNow = document.getElementById('btn-create-exec-task');
  if (formTask) {
    const handleTask = async (executeNow) => {
      const title = document.getElementById('task-title').value.trim();
      const spec = document.getElementById('task-specialist').value;
      const desc = document.getElementById('task-desc').value.trim();
      const depsRaw = document.getElementById('task-deps').value.trim();
      const deps = depsRaw ? depsRaw.split(',').map((s) => s.trim()).filter(Boolean) : [];
      if (!title) return;

      logConsole(`Creating task: "${title}" assigned to ${spec}...`);
      try {
        const res = await api('/api/tasks', {
          method: 'POST',
          body: JSON.stringify({ title, description: desc, assigned_specialist: spec, depends_on: deps }),
        });
        const taskId = res.task?.task_id;
        logConsole(`Task created: ${taskId}`);

        if (executeNow && taskId) {
          logConsole(`Executing ${taskId} immediately...`);
          const execRes = await api(`/api/tasks/${encodeURIComponent(taskId)}/execute`, { method: 'POST', body: '{}' });
          logConsole(`Execution finished for ${taskId}:`, execRes);
        }
        formTask.reset();
        await refreshAll();
      } catch (e) {
        logConsole(`Task creation/execution failed: ${e.message}`);
      }
    };

    formTask.onsubmit = (e) => {
      e.preventDefault();
      handleTask(false);
    };
    if (btnExecNow) btnExecNow.onclick = () => handleTask(true);
  }

  // SaaS Builder form
  const saasForm = document.getElementById('saas-form');
  if (saasForm) {
    saasForm.onsubmit = async (e) => {
      e.preventDefault();
      const name = document.getElementById('saas-name').value.trim();
      const domain = document.getElementById('saas-domain').value.trim();
      const reqs = document.getElementById('saas-reqs').value.trim();
      if (!name || !domain || !reqs) return;

      logConsole(`Launching 5-Department SaaS Venture: "${name}" (${domain})...`);
      try {
        const res = await api('/api/project/saas', {
          method: 'POST',
          body: JSON.stringify({ name, domain, requirements: reqs }),
        });
        logConsole(`SaaS Venture "${name}" successfully generated:`, res);

        // Display artifacts
        const panel = document.getElementById('saas-output-panel');
        const list = document.getElementById('saas-artifacts-list');
        if (panel && list) {
          panel.classList.remove('hidden');
          const files = res.files_created || [];
          const relDir = res.workspace_relative_path || '';
          list.innerHTML = files
            .map(
              (f) =>
                `<button class="artifact-pill" data-read="${escapeHtml(relDir)}/${escapeHtml(f)}">&#128196; ${escapeHtml(f)}</button>`
            )
            .join('');
          list.querySelectorAll('[data-read]').forEach((b) => {
            b.onclick = () => readFile(b.getAttribute('data-read'));
          });
        }
        await refreshAll();
      } catch (err) {
        logConsole(`SaaS Generation Error: ${err.message}`);
      }
    };
  }

  // Spawn Specialist Form
  const btnToggleSpawn = document.getElementById('btn-toggle-spawn');
  const spawnForm = document.getElementById('spawn-form');
  if (btnToggleSpawn && spawnForm) {
    btnToggleSpawn.onclick = () => spawnForm.classList.toggle('hidden');
    spawnForm.onsubmit = async (e) => {
      e.preventDefault();
      const name = document.getElementById('spawn-name').value.trim();
      const role = document.getElementById('spawn-role').value.trim();
      const dept = document.getElementById('spawn-dept').value.trim();
      const gap = document.getElementById('spawn-gap').value.trim();
      const autoApprove = document.getElementById('spawn-approve').checked;

      logConsole(`Spawning specialist "${name}" for role "${role}"...`);
      try {
        const res = await api('/api/specialists/spawn', {
          method: 'POST',
          body: JSON.stringify({
            name,
            role_title: role,
            department: dept,
            justification: gap,
            capability_gap: gap,
            auto_approve: autoApprove,
            authorize_immediately: autoApprove,
          }),
        });
        logConsole(`Specialist operation result:`, res);
        spawnForm.reset();
        spawnForm.classList.add('hidden');
        await refreshAll();
      } catch (err) {
        logConsole(`Spawn Specialist Error: ${err.message}`);
      }
    };
  }

  // Root dir button
  const btnRoot = document.getElementById('btn-ws-root');
  if (btnRoot) {
    btnRoot.onclick = async () => {
      state.workspaceDir = '';
      await refreshAll();
    };
  }

  // Keyboard shortcuts
  window.onkeydown = (e) => {
    if (e.target.tagName === 'INPUT' || e.target.tagName === 'TEXTAREA') return;
    if (e.key === 'p' || e.key === 'P') {
      runPipeHandler();
    } else if (e.key === 'r' || e.key === 'R') {
      refreshAll();
    }
  };
}

// Start
bindGuiEvents();
refreshAll();
