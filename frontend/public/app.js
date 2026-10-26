// ZaxterLab Operations Dashboard — Zero-UI Raw Functional Control Panel (Branch: original)
// Exposes 100% of ZaxterLab backend APIs with plain HTML tables, forms, buttons, and raw JSON/file outputs.

const state = {
  health: null,
  tasks: [],
  projects: [],
  specialists: [],
  proposals: [],
  telemetry: null,
  auditLogs: [],
  workspaceSubdir: '',
  workspaceEntries: [],
  selectedFilePath: '',
  selectedFileContent: '',
  lastActionTitle: 'System Ready',
  lastActionPayload: null,
  busy: false,
};

async function apiCall(path, options = {}) {
  const res = await fetch(path, {
    headers: { 'Content-Type': 'application/json', ...(options.headers || {}) },
    ...options,
  });
  const data = await res.json().catch(() => ({ error: `Non-JSON response (${res.status})` }));
  if (!res.ok) {
    throw new Error(data.error || `HTTP ${res.status}`);
  }
  return data;
}

function escapeHtml(value) {
  return String(value ?? '')
    .replace(/&/g, '&amp;')
    .replace(/</g, '&lt;')
    .replace(/>/g, '&gt;')
    .replace(/"/g, '&quot;');
}

async function refreshAll() {
  try {
    const [health, tasksRes, projectsRes, specsRes, propsRes, telemetry, logsRes, filesRes] = await Promise.all([
      apiCall('/api/health'),
      apiCall('/api/tasks'),
      apiCall('/api/projects'),
      apiCall('/api/specialists'),
      apiCall('/api/evaluator/proposals'),
      apiCall('/api/telemetry'),
      apiCall('/api/audit-logs?limit=40'),
      apiCall(`/api/workspace/files?subdir=${encodeURIComponent(state.workspaceSubdir || '')}`),
    ]);
    state.health = health;
    state.tasks = tasksRes.tasks || [];
    state.projects = projectsRes.projects || [];
    state.specialists = specsRes.specialists || [];
    state.proposals = propsRes.proposals || [];
    state.telemetry = telemetry;
    state.auditLogs = logsRes.audit_logs || [];
    state.workspaceEntries = filesRes.entries || [];
    render();
  } catch (err) {
    state.lastActionTitle = 'Refresh Error';
    state.lastActionPayload = { error: err.message };
    render();
  }
}

async function runAction(title, fn) {
  state.busy = true;
  state.lastActionTitle = `RUNNING: ${title}...`;
  render();
  try {
    const result = await fn();
    state.lastActionTitle = `OK: ${title}`;
    state.lastActionPayload = result;
  } catch (err) {
    state.lastActionTitle = `ERROR: ${title}`;
    state.lastActionPayload = { error: err.message };
  } finally {
    state.busy = false;
    await refreshAll();
  }
}

async function openWorkspaceDir(subdir) {
  state.workspaceSubdir = subdir || '';
  const res = await apiCall(`/api/workspace/files?subdir=${encodeURIComponent(state.workspaceSubdir)}`);
  state.workspaceEntries = res.entries || [];
  render();
}

async function readWorkspaceFile(relPath) {
  try {
    const res = await apiCall(`/api/workspace/file-content?path=${encodeURIComponent(relPath)}`);
    state.selectedFilePath = res.path || relPath;
    state.selectedFileContent = res.content || '';
    state.lastActionTitle = `Read File: ${relPath}`;
    state.lastActionPayload = { path: res.path, size_bytes: res.size_bytes };
    render();
  } catch (err) {
    state.lastActionTitle = `File Read Error: ${relPath}`;
    state.lastActionPayload = { error: err.message };
    render();
  }
}

function renderStatusBadge(status) {
  const s = String(status || '').toLowerCase();
  if (s === 'completed' || s === 'approved' || s === 'ok' || s === 'passed' || s === 'idle') {
    return `<span class="status-pill status-ok">${escapeHtml(status)}</span>`;
  }
  if (s === 'failed' || s === 'rejected' || s === 'error') {
    return `<span class="status-pill status-err">${escapeHtml(status)}</span>`;
  }
  return `<span class="status-pill status-warn">${escapeHtml(status || 'pending')}</span>`;
}

function render() {
  const root = document.getElementById('root');
  if (!root) return;

  const h = state.health || {};
  const t = state.telemetry || {};

  root.innerHTML = `
    <h1>ZAXTERLAB — RAW FUNCTIONAL WORKBENCH (BRANCH: original / ZERO UI)</h1>

    <div class="bar">
      <span><strong>Status:</strong> ${renderStatusBadge(h.status || 'unknown')}</span>
      <span><strong>Provider:</strong> ${escapeHtml(h.provider_mode || 'local_deterministic')}</span>
      <span><strong>Spend Guard:</strong> $${Number(h.total_cost_usd || 0).toFixed(2)} / $${Number(h.max_spend_limit_usd || 0).toFixed(2)}</span>
      <span><strong>Specialists:</strong> ${state.specialists.length}</span>
      <span><strong>Tasks:</strong> ${state.tasks.length}</span>
      <span><strong>Projects:</strong> ${state.projects.length}</span>
      <span><strong>Workspace:</strong> ${escapeHtml(h.workspace_root || '.zaxterlab_workspace')}</span>
    </div>

    <div class="bar">
      <strong>Global Operations:</strong>
      <button id="btn-refresh" ${state.busy ? 'disabled' : ''}>Refresh All State</button>
      <button id="btn-run-evaluator" class="primary" ${state.busy ? 'disabled' : ''}>1. Run Workload Evaluator (POST /api/evaluator/evaluate)</button>
      <button id="btn-run-pipeline" class="primary" ${state.busy ? 'disabled' : ''}>2. Run 2-Stage DAG Pipeline (POST /api/pipeline/run)</button>
      <button id="btn-run-internal" class="primary" ${state.busy ? 'disabled' : ''}>3. Execute Internal Transformation Initiative (7-Task DAG)</button>
    </div>

    <!-- LAST ACTION / RAW INSPECTOR -->
    <section>
      <h2>0. LAST API EXECUTION OUTPUT / RAW JSON INSPECTOR — ${escapeHtml(state.lastActionTitle)}</h2>
      <pre id="raw-inspector">${escapeHtml(
        state.lastActionPayload
          ? JSON.stringify(state.lastActionPayload, null, 2)
          : 'Click any operation button below to execute and inspect its raw JSON response here.'
      )}</pre>
    </section>

    <div class="grid-2">
      <!-- SECTION 1: CREATE & EXECUTE TASK -->
      <section>
        <h2>1. CREATE &amp; DISPATCH TASK (POST /api/tasks)</h2>
        <form id="form-create-task">
          <div class="row">
            <div style="flex:2">
              <label>Task Title</label>
              <input type="text" name="title" required placeholder="e.g. Implement OAuth2 Token Validator" />
            </div>
            <div style="flex:1">
              <label>Assigned Specialist</label>
              <select name="assigned_specialist">
                ${state.specialists
                  .map(
                    (s) =>
                      `<option value="${escapeHtml(s.name)}">${escapeHtml(s.name)} (${escapeHtml(s.role || s.department)})</option>`
                  )
                  .join('')}
              </select>
            </div>
          </div>
          <div class="row">
            <div style="flex:1">
              <label>Task Description / Specification</label>
              <textarea name="description" placeholder="Detailed instructions for the specialist worker..."></textarea>
            </div>
          </div>
          <div class="row">
            <div style="flex:1">
              <label>Depends On Task IDs (comma-separated, optional)</label>
              <input type="text" name="depends_on" placeholder="e.g. task-1, task-2" />
            </div>
            <div>
              <button type="submit" name="mode" value="create" ${state.busy ? 'disabled' : ''}>Create Task Only</button>
              <button type="submit" name="mode" value="execute" class="primary" ${state.busy ? 'disabled' : ''}>Create &amp; Execute Immediately</button>
            </div>
          </div>
        </form>
      </section>

      <!-- SECTION 2: END-TO-END 5-DEPARTMENT SAAS BUILDER -->
      <section>
        <h2>2. BUILD 5-DEPARTMENT SAAS PROJECT (POST /api/project/saas)</h2>
        <form id="form-build-saas">
          <div class="row">
            <div style="flex:1">
              <label>SaaS Product Name</label>
              <input type="text" name="name" required placeholder="e.g. InvoicePulse B2B" />
            </div>
            <div style="flex:1">
              <label>Industry / Domain</label>
              <input type="text" name="domain" required placeholder="e.g. FinTech Billing Automation" />
            </div>
          </div>
          <div class="row">
            <div style="flex:1">
              <label>Customer / Business Requirements</label>
              <textarea name="requirements" required placeholder="Describe core features, user roles, billing logic, and compliance needs..."></textarea>
            </div>
          </div>
          <div class="row">
            <button type="submit" class="primary" ${state.busy ? 'disabled' : ''}>
              Execute Full 5-Stage SaaS Delivery (Hadi -&gt; Sirfaraz -&gt; Reem -&gt; Aroosh -&gt; Zaks)
            </button>
          </div>
        </form>
      </section>
    </div>

    <!-- SECTION 3: TASKS TABLE -->
    <section>
      <h2>3. TASKS QUEUE &amp; EXECUTION SESSIONS (GET /api/tasks — ${state.tasks.length} total)</h2>
      <table>
        <thead>
          <tr>
            <th>Task ID</th>
            <th>Title</th>
            <th>Specialist</th>
            <th>Depends On</th>
            <th>Status</th>
            <th>Actions</th>
          </tr>
        </thead>
        <tbody>
          ${
            state.tasks.length === 0
              ? `<tr><td colspan="6" class="muted">No tasks in database. Create a task above or run a pipeline.</td></tr>`
              : state.tasks
                  .map(
                    (task) => `
              <tr>
                <td><code>${escapeHtml(task.task_id)}</code></td>
                <td>
                  <strong>${escapeHtml(task.title)}</strong>
                  <div class="muted">${escapeHtml((task.description || '').slice(0, 120))}</div>
                </td>
                <td>${escapeHtml(task.assigned_specialist)}</td>
                <td><code>${escapeHtml((task.depends_on || []).join(', ') || '-')}</code></td>
                <td>${renderStatusBadge(task.status)}</td>
                <td>
                  <button data-exec-task="${escapeHtml(task.task_id)}" class="primary" ${state.busy ? 'disabled' : ''}>Execute</button>
                  <button data-sessions-task="${escapeHtml(task.task_id)}">Sessions/Traces</button>
                  <button data-json-task="${escapeHtml(task.task_id)}">Raw JSON</button>
                </td>
              </tr>
            `
                  )
                  .join('')
          }
        </tbody>
      </table>
    </section>

    <!-- SECTION 4: PROJECTS REGISTRY -->
    <section>
      <h2>4. PROJECTS REGISTRY (GET /api/projects — ${state.projects.length} total)</h2>
      <table>
        <thead>
          <tr>
            <th>Project ID</th>
            <th>Name</th>
            <th>Type</th>
            <th>Priority</th>
            <th>Status</th>
            <th>Workspace &amp; Artifacts</th>
            <th>Actions</th>
          </tr>
        </thead>
        <tbody>
          ${
            state.projects.length === 0
              ? `<tr><td colspan="7" class="muted">No projects created yet. Run SaaS Builder or Internal Transformation Initiative.</td></tr>`
              : state.projects
                  .map((p) => {
                    const artifacts = Array.isArray(p.artifacts) ? p.artifacts : [];
                    return `
                <tr>
                  <td><code>${escapeHtml(p.project_id)}</code></td>
                  <td><strong>${escapeHtml(p.name)}</strong><div class="muted">${escapeHtml(p.objective || '')}</div></td>
                  <td>${escapeHtml(p.project_type)}</td>
                  <td>${escapeHtml(p.priority)}</td>
                  <td>${renderStatusBadge(p.status)}</td>
                  <td>
                    <div><code>${escapeHtml(p.workspace_path || '-')}</code></div>
                    <div style="margin-top:4px;">
                      ${artifacts
                        .map(
                          (art) =>
                            `<button data-read-file="${escapeHtml(art)}" style="margin:1px;">Read: ${escapeHtml(art)}</button>`
                        )
                        .join(' ')}
                    </div>
                  </td>
                  <td>
                    <button data-inspect-project="${escapeHtml(p.project_id)}">Inspect JSON</button>
                    ${
                      p.workspace_path
                        ? `<button data-open-dir="${escapeHtml(p.workspace_path)}">Browse Folder</button>`
                        : ''
                    }
                  </td>
                </tr>
              `;
                  })
                  .join('')
          }
        </tbody>
      </table>
    </section>

    <!-- SECTION 5: SPECIALIST WORKFORCE & DYNAMIC SPAWNING -->
    <div class="grid-2">
      <section>
        <h2>5A. REGISTERED SPECIALISTS (GET /api/specialists — ${state.specialists.length})</h2>
        <table>
          <thead>
            <tr>
              <th>ID</th>
              <th>Name</th>
              <th>Role / Dept</th>
              <th>Tier</th>
              <th>Tools</th>
              <th>Status</th>
              <th>Tasks / Tokens</th>
            </tr>
          </thead>
          <tbody>
            ${state.specialists
              .map(
                (s) => `
              <tr>
                <td><code>${escapeHtml(s.worker_id || s.name)}</code></td>
                <td><strong>${escapeHtml(s.name)}</strong> ${s.is_dynamic ? '<span class="status-pill status-warn">spawned</span>' : ''}</td>
                <td>${escapeHtml(s.role)}<div class="muted">${escapeHtml(s.department)}</div></td>
                <td>${escapeHtml(s.permission_tier)}</td>
                <td><code>${escapeHtml((s.allowed_tools || []).join(', '))}</code></td>
                <td>${renderStatusBadge(s.runtime_status || 'idle')}</td>
                <td>${Number(s.tasks_completed || 0)} / ${Number(s.tokens_used || 0)}</td>
              </tr>
            `
              )
              .join('')}
          </tbody>
        </table>
      </section>

      <section>
        <h2>5B. SPAWN SPECIALIST &amp; PROPOSALS (POST /api/specialists/spawn)</h2>
        <form id="form-spawn-specialist" style="margin-bottom: 10px;">
          <div class="row">
            <div style="flex:1">
              <label>Specialist Name</label>
              <input type="text" name="name" required placeholder="e.g. Tariq" />
            </div>
            <div style="flex:1">
              <label>Role Title</label>
              <input type="text" name="role_title" required placeholder="e.g. Security & Penetration Specialist" />
            </div>
            <div style="flex:1">
              <label>Department</label>
              <input type="text" name="department" value="Security" required />
            </div>
          </div>
          <div class="row">
            <div style="flex:1">
              <label>Capability Gap &amp; Justification</label>
              <input type="text" name="justification" required placeholder="Why existing specialists cannot cover this scope..." />
            </div>
            <div style="flex:1">
              <label>Allowed Tools (comma-separated)</label>
              <input type="text" name="allowed_tools" value="read_file,write_file,run_tests" />
            </div>
          </div>
          <div class="row">
            <label style="display:flex;align-items:center;gap:4px;">
              <input type="checkbox" name="auto_approve" checked style="width:auto;" />
              Auto-Approve &amp; Register Immediately in Runtime
            </label>
            <button type="submit" class="primary" ${state.busy ? 'disabled' : ''}>Spawn / Propose Specialist</button>
          </div>
        </form>

        <h3>Workforce Spawning Proposals (${state.proposals.length})</h3>
        <table>
          <thead>
            <tr>
              <th>ID</th>
              <th>Proposed Role</th>
              <th>Confidence</th>
              <th>Status</th>
              <th>Justification</th>
              <th>Actions</th>
            </tr>
          </thead>
          <tbody>
            ${
              state.proposals.length === 0
                ? `<tr><td colspan="6" class="muted">No proposals yet. Click "Run Workload Evaluator" or submit form above.</td></tr>`
                : state.proposals
                    .map(
                      (p) => `
                <tr>
                  <td><code>${escapeHtml(p.proposal_id)}</code></td>
                  <td><strong>${escapeHtml(p.proposed_role)}</strong></td>
                  <td>${Number((p.confidence_score || 0) * 100).toFixed(0)}%</td>
                  <td>${renderStatusBadge(p.status)}</td>
                  <td>${escapeHtml(p.justification)}</td>
                  <td>
                    <button data-approve-prop="${escapeHtml(p.proposal_id)}" class="primary" ${p.status === 'approved' ? 'disabled' : ''}>Approve</button>
                    <button data-reject-prop="${escapeHtml(p.proposal_id)}" ${p.status === 'rejected' ? 'disabled' : ''}>Reject</button>
                  </td>
                </tr>
              `
                    )
                    .join('')
            }
          </tbody>
        </table>
      </section>
    </div>

    <!-- SECTION 6: WORKSPACE FILE BROWSER & FILE READER -->
    <div class="grid-2">
      <section>
        <h2>6A. WORKSPACE FILE BROWSER (GET /api/workspace/files)</h2>
        <div class="row" style="margin-bottom:8px;">
          <input type="text" id="input-subdir" value="${escapeHtml(state.workspaceSubdir)}" placeholder="Relative subdirectory (empty for root)" style="flex:1" />
          <button id="btn-browse-subdir">List Directory</button>
          <button id="btn-browse-root">Root (.)</button>
        </div>
        <table>
          <thead>
            <tr>
              <th>Name</th>
              <th>Type</th>
              <th>Size (B)</th>
              <th>Relative Path</th>
              <th>Action</th>
            </tr>
          </thead>
          <tbody>
            ${
              state.workspaceEntries.length === 0
                ? `<tr><td colspan="5" class="muted">Directory is empty.</td></tr>`
                : state.workspaceEntries
                    .map(
                      (entry) => `
                <tr>
                  <td><strong>${escapeHtml(entry.name)}</strong></td>
                  <td>${escapeHtml(entry.type)}</td>
                  <td>${entry.size_bytes ?? '-'}</td>
                  <td><code>${escapeHtml(entry.relative_path)}</code></td>
                  <td>
                    ${
                      entry.type === 'directory'
                        ? `<button data-open-dir="${escapeHtml(entry.relative_path)}">Open Dir</button>`
                        : `<button data-read-file="${escapeHtml(entry.relative_path)}" class="primary">Read File</button>`
                    }
                  </td>
                </tr>
              `
                    )
                    .join('')
            }
          </tbody>
        </table>
      </section>

      <section>
        <h2>6B. RAW FILE CONTENT VIEWER (${escapeHtml(state.selectedFilePath || 'no file selected')})</h2>
        <pre>${escapeHtml(state.selectedFileContent || 'Click "Read File" on any workspace file or project artifact to view its exact disk content here.')}</pre>
      </section>
    </div>

    <!-- SECTION 7: TELEMETRY & AUDIT LOGS -->
    <section>
      <h2>7. IMMUTABLE SQLITE AUDIT LOGS (GET /api/audit-logs — latest ${state.auditLogs.length})</h2>
      <table>
        <thead>
          <tr>
            <th>Log ID</th>
            <th>Timestamp</th>
            <th>Actor</th>
            <th>Action Type</th>
            <th>Target Entity</th>
            <th>Details JSON</th>
          </tr>
        </thead>
        <tbody>
          ${
            state.auditLogs.length === 0
              ? `<tr><td colspan="6" class="muted">No audit logs recorded yet.</td></tr>`
              : state.auditLogs
                  .map(
                    (log) => `
              <tr>
                <td><code>${escapeHtml(log.log_id)}</code></td>
                <td>${escapeHtml(log.timestamp)}</td>
                <td><strong>${escapeHtml(log.actor)}</strong></td>
                <td><code>${escapeHtml(log.action_type)}</code></td>
                <td><code>${escapeHtml(log.target_entity)}</code></td>
                <td><code>${escapeHtml(
                  typeof log.details_json === 'string' ? log.details_json : JSON.stringify(log.details_json)
                )}</code></td>
              </tr>
            `
                  )
                  .join('')
          }
        </tbody>
      </table>
    </section>
  `;

  bindEvents();
}

function bindEvents() {
  const btnRefresh = document.getElementById('btn-refresh');
  if (btnRefresh) btnRefresh.onclick = () => refreshAll();

  const btnEval = document.getElementById('btn-run-evaluator');
  if (btnEval) {
    btnEval.onclick = () =>
      runAction('POST /api/evaluator/evaluate', () =>
        apiCall('/api/evaluator/evaluate', { method: 'POST', body: JSON.stringify({}) })
      );
  }

  const btnPipe = document.getElementById('btn-run-pipeline');
  if (btnPipe) {
    btnPipe.onclick = () =>
      runAction('POST /api/pipeline/run', () =>
        apiCall('/api/pipeline/run', {
          method: 'POST',
          body: JSON.stringify({ module_name: 'inventory_ledger', feature_spec: 'Deterministic ledger balance check' }),
        })
      );
  }

  const btnInternal = document.getElementById('btn-run-internal');
  if (btnInternal) {
    btnInternal.onclick = () =>
      runAction('POST /api/projects/internal-transformation', () =>
        apiCall('/api/projects/internal-transformation', { method: 'POST', body: JSON.stringify({}) })
      );
  }

  const formCreateTask = document.getElementById('form-create-task');
  if (formCreateTask) {
    formCreateTask.onsubmit = async (e) => {
      e.preventDefault();
      const submitter = e.submitter;
      const mode = submitter ? submitter.value : 'create';
      const fd = new FormData(formCreateTask);
      const dependsRaw = String(fd.get('depends_on') || '').trim();
      const depends_on = dependsRaw
        ? dependsRaw
            .split(',')
            .map((s) => s.trim())
            .filter(Boolean)
        : [];
      const payload = {
        title: String(fd.get('title') || '').trim(),
        description: String(fd.get('description') || '').trim(),
        assigned_specialist: String(fd.get('assigned_specialist') || 'Reem').trim(),
        depends_on,
      };
      await runAction(`Create Task (${payload.title})`, async () => {
        const created = await apiCall('/api/tasks', { method: 'POST', body: JSON.stringify(payload) });
        if (mode === 'execute' && created.task && created.task.task_id) {
          const executed = await apiCall(`/api/tasks/${encodeURIComponent(created.task.task_id)}/execute`, {
            method: 'POST',
            body: JSON.stringify({}),
          });
          return { created: created.task, executed };
        }
        return created;
      });
    };
  }

  const formBuildSaas = document.getElementById('form-build-saas');
  if (formBuildSaas) {
    formBuildSaas.onsubmit = async (e) => {
      e.preventDefault();
      const fd = new FormData(formBuildSaas);
      const payload = {
        name: String(fd.get('name') || '').trim(),
        domain: String(fd.get('domain') || '').trim(),
        requirements: String(fd.get('requirements') || '').trim(),
      };
      await runAction(`Build 5-Department SaaS Project (${payload.name})`, async () => {
        const res = await apiCall('/api/project/saas', { method: 'POST', body: JSON.stringify(payload) });
        if (res.project_dir) {
          state.workspaceSubdir = res.project_dir;
        }
        return res;
      });
    };
  }

  const formSpawn = document.getElementById('form-spawn-specialist');
  if (formSpawn) {
    formSpawn.onsubmit = async (e) => {
      e.preventDefault();
      const fd = new FormData(formSpawn);
      const toolsRaw = String(fd.get('allowed_tools') || '').trim();
      const payload = {
        name: String(fd.get('name') || '').trim(),
        role_title: String(fd.get('role_title') || '').trim(),
        department: String(fd.get('department') || 'Engineering').trim(),
        justification: String(fd.get('justification') || '').trim(),
        capability_gap: String(fd.get('justification') || '').trim(),
        allowed_tools: toolsRaw ? toolsRaw.split(',').map((s) => s.trim()).filter(Boolean) : ['read_file', 'write_file'],
        auto_approve: fd.get('auto_approve') !== null,
      };
      await runAction(`Spawn Specialist (${payload.name})`, () =>
        apiCall('/api/specialists/spawn', { method: 'POST', body: JSON.stringify(payload) })
      );
    };
  }

  document.querySelectorAll('[data-exec-task]').forEach((btn) => {
    btn.onclick = () => {
      const taskId = btn.getAttribute('data-exec-task');
      runAction(`Execute Task ${taskId}`, () =>
        apiCall(`/api/tasks/${encodeURIComponent(taskId)}/execute`, { method: 'POST', body: JSON.stringify({}) })
      );
    };
  });

  document.querySelectorAll('[data-sessions-task]').forEach((btn) => {
    btn.onclick = async () => {
      const taskId = btn.getAttribute('data-sessions-task');
      const res = await apiCall(`/api/tasks/${encodeURIComponent(taskId)}/sessions`);
      state.lastActionTitle = `Sessions & Step Traces for Task ${taskId}`;
      state.lastActionPayload = res;
      render();
    };
  });

  document.querySelectorAll('[data-json-task]').forEach((btn) => {
    btn.onclick = async () => {
      const taskId = btn.getAttribute('data-json-task');
      const res = await apiCall(`/api/tasks/${encodeURIComponent(taskId)}`);
      state.lastActionTitle = `Task JSON: ${taskId}`;
      state.lastActionPayload = res;
      render();
    };
  });

  document.querySelectorAll('[data-inspect-project]').forEach((btn) => {
    btn.onclick = () => {
      const projId = btn.getAttribute('data-inspect-project');
      const proj = state.projects.find((p) => p.project_id === projId);
      state.lastActionTitle = `Project JSON: ${projId}`;
      state.lastActionPayload = proj || { error: 'Project not found' };
      render();
    };
  });

  document.querySelectorAll('[data-approve-prop]').forEach((btn) => {
    btn.onclick = () => {
      const propId = btn.getAttribute('data-approve-prop');
      runAction(`Approve Proposal ${propId}`, () =>
        apiCall(`/api/evaluator/proposals/${encodeURIComponent(propId)}/approve`, {
          method: 'POST',
          body: JSON.stringify({}),
        })
      );
    };
  });

  document.querySelectorAll('[data-reject-prop]').forEach((btn) => {
    btn.onclick = () => {
      const propId = btn.getAttribute('data-reject-prop');
      runAction(`Reject Proposal ${propId}`, () =>
        apiCall(`/api/evaluator/proposals/${encodeURIComponent(propId)}/reject`, {
          method: 'POST',
          body: JSON.stringify({}),
        })
      );
    };
  });

  document.querySelectorAll('[data-open-dir]').forEach((btn) => {
    btn.onclick = () => openWorkspaceDir(btn.getAttribute('data-open-dir'));
  });

  document.querySelectorAll('[data-read-file]').forEach((btn) => {
    btn.onclick = () => readWorkspaceFile(btn.getAttribute('data-read-file'));
  });

  const btnBrowseSubdir = document.getElementById('btn-browse-subdir');
  if (btnBrowseSubdir) {
    btnBrowseSubdir.onclick = () => {
      const input = document.getElementById('input-subdir');
      openWorkspaceDir(input ? input.value.trim() : '');
    };
  }

  const btnBrowseRoot = document.getElementById('btn-browse-root');
  if (btnBrowseRoot) {
    btnBrowseRoot.onclick = () => openWorkspaceDir('');
  }
}

refreshAll();
