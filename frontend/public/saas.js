// ZaxterLab Form 3: SaaS Operations Platform (Modern Web Application Controller)
// Exposes 100% of ZaxterLab operations through a unified Linear/Vercel-grade SaaS workbench.

const state = {
  activeView: 'view-overview',
  health: null,
  tasks: [],
  projects: [],
  specialists: [],
  auditLogs: [],
  workspaceDir: '',
  workspaceFiles: [],
  selectedFile: null,
  taskFilter: 'all',
  searchQuery: '',
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

function showToast(message, type = 'info') {
  const container = document.getElementById('toast-container');
  if (!container) return;

  const toast = document.createElement('div');
  toast.className = `toast ${type}`;
  toast.textContent = message;
  container.appendChild(toast);

  setTimeout(() => {
    toast.style.opacity = '0';
    toast.style.transition = 'opacity 0.3s ease';
    setTimeout(() => toast.remove(), 300);
  }, 3500);
}

function escapeHtml(str) {
  return String(str ?? '')
    .replace(/&/g, '&amp;')
    .replace(/</g, '&lt;')
    .replace(/>/g, '&gt;')
    .replace(/"/g, '&quot;');
}

function renderBadge(status) {
  const s = String(status || '').toUpperCase();
  if (s === 'COMPLETED' || s === 'APPROVED' || s === 'HEALTHY' || s === 'AVAILABLE') {
    return `<span class="badge badge-success">${escapeHtml(s)}</span>`;
  }
  if (s === 'RUNNING' || s === 'ACTIVE') {
    return `<span class="badge badge-info">${escapeHtml(s)}</span>`;
  }
  if (s === 'FAILED' || s === 'REJECTED' || s === 'BLOCKED') {
    return `<span class="badge badge-danger">${escapeHtml(s)}</span>`;
  }
  return `<span class="badge badge-warning">${escapeHtml(s || 'PENDING')}</span>`;
}

async function refreshAll() {
  try {
    const [h, tRes, pRes, sRes, aRes, fRes] = await Promise.all([
      api('/api/health'),
      api('/api/tasks'),
      api('/api/projects'),
      api('/api/specialists'),
      api('/api/audit-logs?limit=40'),
      api(`/api/workspace/files?subdir=${encodeURIComponent(state.workspaceDir)}`),
    ]);

    state.health = h;
    state.tasks = tRes.tasks || [];
    state.projects = pRes.projects || [];
    state.specialists = sRes.specialists || [];
    state.auditLogs = aRes.audit_logs || [];
    state.workspaceFiles = fRes.entries || [];

    updateKPIs();
    renderOverview();
    renderTasks();
    renderVentures();
    renderSpecialists();
    renderFiles();
    renderAudit();
  } catch (err) {
    showToast(`Refresh error: ${err.message}`, 'error');
  }
}

function updateKPIs() {
  const h = state.health || {};
  const spend = h.spend_guard || {};
  const cost = Number(spend.cumulative_spent_usd || 0).toFixed(2);
  const max = Number(spend.authorized_spend_usd || 0).toFixed(2);

  document.getElementById('kpi-health').textContent = (h.status || 'HEALTHY').toUpperCase();
  document.getElementById('kpi-spend').textContent = `$${cost}`;
  document.getElementById('kpi-specialists').textContent = state.specialists.length;
  document.getElementById('kpi-tasks').textContent = state.tasks.length;
  document.getElementById('kpi-projects').textContent = state.projects.length;

  document.getElementById('sidebar-spend').textContent = `$${cost} / $${max}`;
  document.getElementById('badge-tasks-count').textContent = state.tasks.length;
  document.getElementById('badge-ventures-count').textContent = state.projects.length;
  document.getElementById('badge-specialists-count').textContent = state.specialists.length;

  // Populate specialist options in modals
  const specSelect = document.getElementById('modal-task-spec');
  if (specSelect && specSelect.children.length === 0) {
    specSelect.innerHTML = state.specialists
      .map((s) => `<option value="${escapeHtml(s.name)}">${escapeHtml(s.name)} (${escapeHtml(s.department)})</option>`)
      .join('');
  }
}

function renderOverview() {
  // 1. Overview recent tasks
  const tasksTbody = document.getElementById('overview-tasks-tbody');
  if (tasksTbody) {
    const recent = state.tasks.slice(-5).reverse();
    if (recent.length === 0) {
      tasksTbody.innerHTML = `<tr><td colspan="4" class="empty-state">No tasks created yet.</td></tr>`;
    } else {
      tasksTbody.innerHTML = recent
        .map(
          (t) => `
        <tr>
          <td><strong>${escapeHtml(t.title)}</strong></td>
          <td>${escapeHtml(t.assigned_specialist || '-')}</td>
          <td>${renderBadge(t.status)}</td>
          <td>
            <button class="btn btn-sm btn-secondary" data-inspect-task="${escapeHtml(t.task_id)}">Inspect</button>
          </td>
        </tr>
      `
        )
        .join('');
    }
  }

  // 2. Overview specialists mini list
  const specList = document.getElementById('overview-specialists-list');
  if (specList) {
    specList.innerHTML = state.specialists
      .slice(0, 5)
      .map(
        (s) => `
      <div class="spec-mini-item">
        <div class="spec-avatar">${escapeHtml(s.name.charAt(0))}</div>
        <div class="spec-info">
          <div class="spec-name">${escapeHtml(s.name)}</div>
          <div class="spec-role">${escapeHtml(s.role)} &bull; ${escapeHtml(s.department)}</div>
        </div>
        ${renderBadge(s.runtime_status || 'AVAILABLE')}
      </div>
    `
      )
      .join('');
  }

  bindInspectButtons();
}

function renderTasks() {
  const tbody = document.getElementById('tasks-full-tbody');
  if (!tbody) return;

  let filtered = state.tasks;
  if (state.taskFilter !== 'all') {
    filtered = filtered.filter((t) => String(t.status).toUpperCase() === state.taskFilter);
  }
  if (state.searchQuery) {
    const q = state.searchQuery.toLowerCase();
    filtered = filtered.filter(
      (t) =>
        t.title.toLowerCase().includes(q) ||
        (t.assigned_specialist || '').toLowerCase().includes(q) ||
        t.task_id.toLowerCase().includes(q)
    );
  }

  if (filtered.length === 0) {
    tbody.innerHTML = `<tr><td colspan="6" class="empty-state">No matching tasks found.</td></tr>`;
    return;
  }

  tbody.innerHTML = filtered
    .map((t) => {
      const deps = (t.depends_on || []).map((d) => `<code>${escapeHtml(d)}</code>`).join(' ') || '-';
      return `
      <tr>
        <td><code>${escapeHtml(t.task_id)}</code></td>
        <td>
          <strong>${escapeHtml(t.title)}</strong>
          <div style="font-size:11px;color:var(--text-muted);margin-top:2px;">${escapeHtml(t.description || '')}</div>
        </td>
        <td><strong>${escapeHtml(t.assigned_specialist || '-')}</strong></td>
        <td>${deps}</td>
        <td>${renderBadge(t.status)}</td>
        <td>
          <button class="btn btn-sm btn-primary" data-exec-task="${escapeHtml(t.task_id)}">Execute</button>
          <button class="btn btn-sm btn-secondary" data-inspect-task="${escapeHtml(t.task_id)}">Drawer</button>
        </td>
      </tr>
    `;
    })
    .join('');

  tbody.querySelectorAll('[data-exec-task]').forEach((btn) => {
    btn.onclick = async () => {
      const taskId = btn.getAttribute('data-exec-task');
      showToast(`Executing task ${taskId}...`, 'info');
      try {
        const res = await api(`/api/tasks/${encodeURIComponent(taskId)}/execute`, { method: 'POST', body: '{}' });
        showToast(`Task ${taskId} completed!`, 'success');
        await refreshAll();
      } catch (e) {
        showToast(`Execution failed: ${e.message}`, 'error');
      }
    };
  });

  bindInspectButtons();
}

function renderVentures() {
  const container = document.getElementById('ventures-container');
  if (!container) return;

  if (state.projects.length === 0) {
    container.innerHTML = `<div class="empty-state" style="grid-column: 1 / -1;">No SaaS ventures launched yet. Click "+ Launch New SaaS Venture" above.</div>`;
    return;
  }

  container.innerHTML = state.projects
    .map((p) => {
      const artifacts = Array.isArray(p.artifacts) ? p.artifacts : [];
      return `
      <div class="venture-card">
        <div class="venture-header">
          <div>
            <div class="venture-title">${escapeHtml(p.name)}</div>
            <div class="venture-domain">${escapeHtml(p.domain || p.project_type)}</div>
          </div>
          ${renderBadge(p.status)}
        </div>
        <div class="venture-desc">${escapeHtml(p.objective || '')}</div>
        <div style="font-size:11px;color:var(--text-muted);">
          Workspace: <code>${escapeHtml(p.workspace_path || '-')}</code>
        </div>
        <div class="venture-artifacts">
          ${artifacts
            .map((a) => `<button class="artifact-chip" data-read-file="${escapeHtml(a)}">&#128196; ${escapeHtml(a.split('/').pop())}</button>`)
            .join('')}
        </div>
      </div>
    `;
    })
    .join('');

  container.querySelectorAll('[data-read-file]').forEach((btn) => {
    btn.onclick = () => {
      const file = btn.getAttribute('data-read-file');
      switchView('view-workspace');
      readFile(file);
    };
  });
}

function renderSpecialists() {
  const container = document.getElementById('specialists-container');
  if (!container) return;

  container.innerHTML = state.specialists
    .map((s) => {
      const tools = (s.allowed_tools || []).map((t) => `<span class="tool-tag">${escapeHtml(t)}</span>`).join('');
      return `
      <div class="specialist-card">
        <div class="specialist-card-header">
          <div class="spec-avatar">${escapeHtml(s.name.charAt(0))}</div>
          <div>
            <div class="spec-name">${escapeHtml(s.name)}</div>
            <div class="spec-role">${escapeHtml(s.role)}</div>
          </div>
          <div style="margin-left:auto;">${renderBadge(s.runtime_status || 'AVAILABLE')}</div>
        </div>
        <div style="font-size:11px;color:var(--text-secondary);">
          Department: <strong>${escapeHtml(s.department)}</strong> &bull; Tier: <code>${escapeHtml(s.permission_tier)}</code>
        </div>
        <div style="font-size:11px;color:var(--text-muted);">${escapeHtml(s.instructions || s.capability_gap_filled || '')}</div>
        <div>
          <div style="font-size:10px;font-weight:700;color:var(--text-muted);margin-bottom:4px;">ALLOWED TOOLS:</div>
          <div class="specialist-tools-list">${tools}</div>
        </div>
      </div>
    `;
    })
    .join('');
}

function renderFiles() {
  const tree = document.getElementById('saas-file-tree');
  const label = document.getElementById('ws-breadcrumb-label');
  if (!tree) return;

  if (label) label.textContent = state.workspaceDir ? `./${state.workspaceDir}` : './';

  if (state.workspaceFiles.length === 0) {
    tree.innerHTML = `<li class="empty-state">Folder is empty.</li>`;
    return;
  }

  tree.innerHTML = state.workspaceFiles
    .map((f) => {
      const icon = f.type === 'directory' ? '&#128193;' : '&#128196;';
      return `
      <li data-relpath="${escapeHtml(f.relative_path)}" data-type="${escapeHtml(f.type)}">
        <span>${icon}</span>
        <span>${escapeHtml(f.name)}</span>
        <span style="margin-left:auto;font-size:10px;color:var(--text-muted);">${f.size_bytes != null ? `${f.size_bytes}B` : ''}</span>
      </li>
    `;
    })
    .join('');

  tree.querySelectorAll('li[data-relpath]').forEach((li) => {
    li.onclick = async () => {
      const p = li.getAttribute('data-relpath');
      const t = li.getAttribute('data-type');
      if (t === 'directory') {
        state.workspaceDir = p;
        await refreshAll();
      } else {
        tree.querySelectorAll('li').forEach((el) => el.classList.remove('active'));
        li.classList.add('active');
        await readFile(p);
      }
    };
  });
}

async function readFile(relPath) {
  const header = document.getElementById('saas-file-viewer-header');
  const viewer = document.getElementById('saas-file-code');
  if (header) header.textContent = `Viewing: ${relPath}`;
  try {
    const res = await api(`/api/workspace/file-content?path=${encodeURIComponent(relPath)}`);
    if (viewer) viewer.textContent = res.content || '(Empty file)';
  } catch (err) {
    if (viewer) viewer.textContent = `Error reading file: ${err.message}`;
    showToast(`Read file error: ${err.message}`, 'error');
  }
}

function renderAudit() {
  const tbody = document.getElementById('saas-audit-tbody');
  if (!tbody) return;

  tbody.innerHTML = state.auditLogs
    .slice(-30)
    .reverse()
    .map(
      (l) => `
    <tr>
      <td><code>${escapeHtml(l.id)}</code></td>
      <td>${escapeHtml((l.timestamp || '').slice(0, 19))}</td>
      <td><strong>${escapeHtml(l.event_type)}</strong></td>
      <td><code>${escapeHtml(l.entity_id)}</code></td>
      <td style="font-family:var(--font-mono);font-size:11px;">${escapeHtml(
        typeof l.details === 'string' ? l.details : JSON.stringify(l.details || {})
      )}</td>
    </tr>
  `
    )
    .join('');
}

function bindInspectButtons() {
  document.querySelectorAll('[data-inspect-task]').forEach((btn) => {
    btn.onclick = async () => {
      const taskId = btn.getAttribute('data-inspect-task');
      await openTaskDrawer(taskId);
    };
  });
}

async function openTaskDrawer(taskId) {
  const drawer = document.getElementById('task-drawer');
  const backdrop = document.getElementById('drawer-backdrop');
  const titleEl = document.getElementById('drawer-task-title');
  const bodyEl = document.getElementById('drawer-task-body');
  if (!drawer || !backdrop) return;

  titleEl.textContent = `Task: ${taskId}`;
  bodyEl.innerHTML = `<div class="empty-state">Loading sessions & step traces...</div>`;
  drawer.classList.remove('hidden');
  backdrop.classList.remove('hidden');

  try {
    const [taskData, sessionsData] = await Promise.all([
      api(`/api/tasks/${encodeURIComponent(taskId)}`),
      api(`/api/tasks/${encodeURIComponent(taskId)}/sessions`),
    ]);

    const t = taskData.task || {};
    const sessions = sessionsData.sessions || [];

    bodyEl.innerHTML = `
      <div class="card">
        <div class="card-body">
          <div style="font-size:16px;font-weight:700;">${escapeHtml(t.title)}</div>
          <div style="margin-top:4px;color:var(--text-secondary);font-size:12px;">${escapeHtml(t.description || 'No description provided')}</div>
          <div style="margin-top:10px;display:flex;gap:8px;align-items:center;">
            ${renderBadge(t.status)}
            <span style="font-size:12px;color:var(--text-muted);">Specialist: <strong>${escapeHtml(t.assigned_specialist || '-')}</strong></span>
          </div>
        </div>
      </div>

      <h4 style="font-size:13px;font-weight:700;color:var(--text-primary);margin-top:8px;">Execution Sessions (${sessions.length})</h4>
      ${
        sessions.length === 0
          ? `<div class="empty-state">No execution sessions recorded yet.</div>`
          : sessions
              .map(
                (s) => `
          <div class="card" style="margin-bottom:8px;">
            <div class="card-header">
              <span>Session: <code>${escapeHtml(s.session_id)}</code></span>
              ${renderBadge(s.status)}
            </div>
            <div class="card-body" style="font-size:12px;">
              <div>Tokens Used: <strong>${s.total_tokens_used || 0}</strong> &bull; Cost: <strong>$${Number(s.total_cost_usd || 0).toFixed(2)}</strong></div>
              <div style="margin-top:8px;">
                <strong>Step Traces:</strong>
                ${
                  (s.steps || []).length === 0
                    ? `<div style="color:var(--text-muted);font-size:11px;margin-top:4px;">No intermediate steps recorded.</div>`
                    : (s.steps || [])
                        .map(
                          (st, idx) => `
                    <div style="background:var(--bg-base);padding:6px;border-radius:4px;margin-top:4px;font-family:var(--font-mono);font-size:11px;">
                      Step ${idx + 1}: ${escapeHtml(st.tool_action || st.thought || 'Executed')} &rarr; ${renderBadge(st.status)}
                    </div>
                  `
                        )
                        .join('')
                }
              </div>
            </div>
          </div>
        `
              )
              .join('')
      }
    `;
  } catch (err) {
    bodyEl.innerHTML = `<div class="empty-state" style="color:var(--accent-danger);">Error loading details: ${err.message}</div>`;
  }
}

function closeTaskDrawer() {
  document.getElementById('task-drawer')?.classList.add('hidden');
  document.getElementById('drawer-backdrop')?.classList.add('hidden');
}

function switchView(viewId) {
  state.activeView = viewId;
  document.querySelectorAll('.app-view').forEach((el) => el.classList.remove('active'));
  document.querySelectorAll('.nav-item').forEach((btn) => btn.classList.remove('active'));

  const activeViewEl = document.getElementById(viewId);
  const activeNavBtn = document.querySelector(`.nav-item[data-view="${viewId}"]`);
  if (activeViewEl) activeViewEl.classList.add('active');
  if (activeNavBtn) activeNavBtn.classList.add('active');

  const breadcrumbView = document.getElementById('breadcrumb-view');
  if (breadcrumbView && activeNavBtn) {
    breadcrumbView.textContent = activeNavBtn.textContent.trim().replace(/^\S+\s*/, '');
  }
}

function bindEvents() {
  // Navigation
  document.querySelectorAll('.nav-item[data-view]').forEach((btn) => {
    btn.onclick = () => switchView(btn.getAttribute('data-view'));
  });

  document.querySelectorAll('[data-switch-to]').forEach((btn) => {
    btn.onclick = () => switchView(btn.getAttribute('data-switch-to'));
  });

  // Header quick buttons
  document.getElementById('btn-refresh-header')?.addEventListener('click', () => {
    refreshAll();
    showToast('Data refreshed.', 'info');
  });

  document.getElementById('btn-run-pipeline-header')?.addEventListener('click', async () => {
    showToast('Running 2-Stage Multi-Worker DAG Pipeline...', 'info');
    try {
      const res = await api('/api/pipeline/run', {
        method: 'POST',
        body: JSON.stringify({ module_name: 'saas_billing_engine', feature_spec: 'Multi-tenant ledger sync' }),
      });
      showToast(`Pipeline execution finished: ${res.succeeded_count} succeeded!`, 'success');
      await refreshAll();
    } catch (e) {
      showToast(`Pipeline error: ${e.message}`, 'error');
    }
  });

  document.getElementById('btn-evaluator-trigger')?.addEventListener('click', async () => {
    showToast('Evaluating specialist workload...', 'info');
    try {
      const res = await api('/api/evaluator/evaluate', { method: 'POST', body: '{}' });
      showToast(`Workload evaluated: ${res.proposals?.length || 0} proposals generated`, 'success');
      await refreshAll();
    } catch (e) {
      showToast(`Evaluator error: ${e.message}`, 'error');
    }
  });

  document.getElementById('btn-internal-initiative')?.addEventListener('click', async () => {
    showToast('Executing Section 18 Internal Initiative DAG (7 Tasks)...', 'info');
    try {
      const res = await api('/api/projects/internal-transformation', { method: 'POST', body: '{}' });
      showToast(`Internal initiative completed: ${res.tasks_executed?.length || 7} tasks verified!`, 'success');
      await refreshAll();
    } catch (e) {
      showToast(`Initiative error: ${e.message}`, 'error');
    }
  });

  // Drawer close
  document.getElementById('btn-close-drawer')?.addEventListener('click', closeTaskDrawer);
  document.getElementById('drawer-backdrop')?.addEventListener('click', closeTaskDrawer);

  // Modals open/close
  document.querySelectorAll('.btn-close-modal').forEach((btn) => {
    btn.onclick = () => {
      const modalId = btn.getAttribute('data-modal');
      document.getElementById(modalId)?.classList.add('hidden');
    };
  });

  document.querySelectorAll('#btn-open-new-task, #btn-create-task-view').forEach((btn) => {
    btn.onclick = () => document.getElementById('modal-task')?.classList.remove('hidden');
  });

  document.getElementById('btn-open-venture-modal')?.addEventListener('click', () => {
    document.getElementById('modal-venture')?.classList.remove('hidden');
  });

  document.getElementById('btn-open-spawn-modal')?.addEventListener('click', () => {
    document.getElementById('modal-spawn')?.classList.remove('hidden');
  });

  // Modal forms
  const taskModalForm = document.getElementById('form-create-task-modal');
  if (taskModalForm) {
    taskModalForm.onsubmit = async (e) => {
      e.preventDefault();
      const submitter = e.submitter;
      const mode = submitter ? submitter.value : 'create';
      const title = document.getElementById('modal-task-title').value.trim();
      const specialist = document.getElementById('modal-task-spec').value;
      const desc = document.getElementById('modal-task-desc').value.trim();
      const depsRaw = document.getElementById('modal-task-deps').value.trim();
      const deps = depsRaw ? depsRaw.split(',').map((s) => s.trim()).filter(Boolean) : [];

      showToast(`Creating task "${title}"...`, 'info');
      try {
        const res = await api('/api/tasks', {
          method: 'POST',
          body: JSON.stringify({ title, description: desc, assigned_specialist: specialist, depends_on: deps }),
        });
        const taskId = res.task?.task_id;
        document.getElementById('modal-task')?.classList.add('hidden');
        taskModalForm.reset();

        if (mode === 'execute' && taskId) {
          showToast(`Executing task ${taskId}...`, 'info');
          await api(`/api/tasks/${encodeURIComponent(taskId)}/execute`, { method: 'POST', body: '{}' });
          showToast(`Task ${taskId} completed!`, 'success');
        } else {
          showToast(`Task ${taskId} created!`, 'success');
        }
        await refreshAll();
      } catch (err) {
        showToast(`Task creation error: ${err.message}`, 'error');
      }
    };
  }

  const ventureModalForm = document.getElementById('form-launch-venture-modal');
  if (ventureModalForm) {
    ventureModalForm.onsubmit = async (e) => {
      e.preventDefault();
      const name = document.getElementById('modal-venture-name').value.trim();
      const domain = document.getElementById('modal-venture-domain').value.trim();
      const reqs = document.getElementById('modal-venture-reqs').value.trim();

      showToast(`Executing 5-Department Delivery for "${name}"...`, 'info');
      document.getElementById('modal-venture')?.classList.add('hidden');
      try {
        const res = await api('/api/project/saas', {
          method: 'POST',
          body: JSON.stringify({ name, domain, requirements: reqs }),
        });
        showToast(`SaaS Venture "${name}" launched! 5 artifacts created.`, 'success');
        ventureModalForm.reset();
        await refreshAll();
      } catch (err) {
        showToast(`Venture launch error: ${err.message}`, 'error');
      }
    };
  }

  const spawnModalForm = document.getElementById('form-spawn-specialist-modal');
  if (spawnModalForm) {
    spawnModalForm.onsubmit = async (e) => {
      e.preventDefault();
      const name = document.getElementById('modal-spawn-name').value.trim();
      const role = document.getElementById('modal-spawn-role').value.trim();
      const dept = document.getElementById('modal-spawn-dept').value.trim();
      const gap = document.getElementById('modal-spawn-gap').value.trim();
      const toolsRaw = document.getElementById('modal-spawn-tools').value.trim();
      const tools = toolsRaw ? toolsRaw.split(',').map((s) => s.trim()).filter(Boolean) : ['read_file', 'write_file'];
      const autoApprove = document.getElementById('modal-spawn-approve').checked;

      showToast(`Spawning specialist "${name}"...`, 'info');
      document.getElementById('modal-spawn')?.classList.add('hidden');
      try {
        const res = await api('/api/specialists/spawn', {
          method: 'POST',
          body: JSON.stringify({
            name,
            role_title: role,
            department: dept,
            justification: gap,
            capability_gap: gap,
            allowed_tools: tools,
            auto_approve: autoApprove,
            authorize_immediately: autoApprove,
          }),
        });
        showToast(`Specialist "${name}" registered in workforce!`, 'success');
        spawnModalForm.reset();
        await refreshAll();
      } catch (err) {
        showToast(`Spawn error: ${err.message}`, 'error');
      }
    };
  }

  // Filter buttons
  document.querySelectorAll('.btn-filter').forEach((btn) => {
    btn.onclick = () => {
      document.querySelectorAll('.btn-filter').forEach((b) => b.classList.remove('active'));
      btn.classList.add('active');
      state.taskFilter = btn.getAttribute('data-filter');
      renderTasks();
    };
  });

  // Search
  const searchInput = document.getElementById('global-search');
  if (searchInput) {
    searchInput.oninput = () => {
      state.searchQuery = searchInput.value.trim();
      renderTasks();
    };
  }

  // Root workspace dir button
  document.getElementById('btn-ws-root-saas')?.addEventListener('click', async () => {
    state.workspaceDir = '';
    await refreshAll();
  });

  // Audit refresh
  document.getElementById('btn-refresh-audit-saas')?.addEventListener('click', () => {
    refreshAll();
    showToast('Audit trail refreshed.', 'info');
  });

  // Keyboard shortcut Ctrl+K to search
  window.addEventListener('keydown', (e) => {
    if ((e.ctrlKey || e.metaKey) && e.key === 'k') {
      e.preventDefault();
      searchInput?.focus();
    }
  });
}

// Initialize
bindEvents();
refreshAll();
