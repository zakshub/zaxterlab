/**
 * Deterministic Mock Adapter for ZaxterLab
 * EXPLICITLY LABELED: DEMO — SIMULATED EVENTS
 */

import {
  ApiClient,
  AuditLogEntry,
  FileContentResponse,
  Session,
  SystemHealth,
  Task,
  TaskStatus,
  WorkspaceFilesResponse,
} from '../types/api';

export class MockApiAdapter implements ApiClient {
  public isDemo = true;

  private tasks: Task[] = [
    {
      task_id: 'task_demo_01',
      title: 'Initialize System Security Perimeter',
      description: 'Audit workspace boundaries, initialize SQLite tables, verify $0.00 spend guard.',
      status: 'COMPLETED',
      assigned_agent_id: 'reem-worker-1',
      input_context: { priority: 'high', security_level: 'tier_2' },
      result_summary: 'All boundary invariants passed. Workspace confined to /root/zakxterlab/workspace.',
      created_at: new Date(Date.now() - 3600000).toISOString(),
      updated_at: new Date(Date.now() - 3500000).toISOString(),
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
      updated_at: new Date().toISOString(),
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
      updated_at: new Date(Date.now() - 400000).toISOString(),
    },
  ];

  private sessions: Record<string, Session> = {
    task_demo_02: {
      session_id: 'sess_demo_02_alpha',
      task_id: 'task_demo_02',
      agent_id: 'reem-worker-1',
      status: 'ACTIVE',
      current_step: 3,
      state_data: { current_stage: 'TOOL_CALL', target_module: 'dispatch' },
      total_token_usage: {
        prompt_tokens: 140,
        completion_tokens: 180,
        total_tokens: 320,
        estimated_cost_usd: 0.0,
      },
      created_at: new Date(Date.now() - 1200000).toISOString(),
      updated_at: new Date().toISOString(),
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
            {
              call_id: 'call_scaffold_01',
              tool_name: 'write_file',
              arguments: { path: 'dispatch.py', content: '# ZaxterLab Dispatch Engine\n' },
            },
          ],
          tool_results: [
            {
              call_id: 'call_scaffold_01',
              tool_name: 'write_file',
              success: true,
              output: 'Successfully wrote 32 characters to dispatch.py',
            },
          ],
          evaluation: 'File written successfully. Executing syntax and lint check.',
          token_usage: { prompt_tokens: 50, completion_tokens: 60, total_tokens: 110, estimated_cost_usd: 0.0 },
          created_at: new Date(Date.now() - 800000).toISOString(),
        },
        {
          step_number: 3,
          phase: 'TOOL_CALL',
          observation: 'Invoking test verification through CommandGuard.',
          plan: 'Execute python3 -m unittest on generated code.',
          tool_calls: [
            {
              call_id: 'call_test_01',
              tool_name: 'run_command',
              arguments: { command: 'python3 -m unittest discover -s tests -v' },
            },
          ],
          tool_results: [
            {
              call_id: 'call_test_01',
              tool_name: 'run_command',
              success: true,
              output: 'Ran 27 tests in 5.6s - OK',
            },
          ],
          evaluation: 'Verification passed with 100% test assertions satisfied.',
          token_usage: { prompt_tokens: 50, completion_tokens: 70, total_tokens: 120, estimated_cost_usd: 0.0 },
          created_at: new Date(Date.now() - 200000).toISOString(),
        },
      ],
    },
  };

  async getHealth(): Promise<SystemHealth> {
    return {
      status: 'healthy',
      version: '0.1.0-demo',
      mode: 'demo',
      worker: {
        agent_id: 'reem-worker-1',
        name: 'Reem',
        role: 'Construction and Programming',
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
    };
  }

  async listTasks(status?: TaskStatus): Promise<Task[]> {
    if (status) {
      return this.tasks.filter((t) => t.status === status);
    }
    return [...this.tasks];
  }

  async createTask(title: string, description: string, inputContext: Record<string, any> = {}): Promise<Task> {
    const newTask: Task = {
      task_id: `task_demo_${Date.now().toString(36)}`,
      title,
      description,
      status: 'SUBMITTED',
      assigned_agent_id: 'reem-worker-1',
      input_context: inputContext,
      created_at: new Date().toISOString(),
      updated_at: new Date().toISOString(),
    };
    this.tasks.unshift(newTask);
    return newTask;
  }

  async getTaskDetails(taskId: string): Promise<{ task: Task; session: Session | null }> {
    const task = this.tasks.find((t) => t.task_id === taskId);
    if (!task) throw new Error(`Task '${taskId}' not found in demo data.`);
    const session = this.sessions[taskId] || null;
    return { task, session };
  }

  async executeTask(taskId: string): Promise<{ task: Task; session: Session }> {
    const { task } = await this.getTaskDetails(taskId);
    task.status = 'COMPLETED';
    task.result_summary = 'Demo execution completed successfully.';
    task.updated_at = new Date().toISOString();

    let session = this.sessions[taskId];
    if (!session) {
      session = {
        session_id: `sess_${taskId}_demo`,
        task_id: taskId,
        agent_id: 'reem-worker-1',
        status: 'COMPLETED',
        current_step: 1,
        state_data: {},
        step_traces: [
          {
            step_number: 1,
            phase: 'CYCLE',
            observation: 'Executed task in simulated environment.',
            plan: 'Run simulation and record trace',
            tool_calls: [],
            tool_results: [],
            evaluation: 'Simulated task completed.',
            token_usage: { prompt_tokens: 25, completion_tokens: 35, total_tokens: 60, estimated_cost_usd: 0.0 },
            created_at: new Date().toISOString(),
          },
        ],
        total_token_usage: { prompt_tokens: 25, completion_tokens: 35, total_tokens: 60, estimated_cost_usd: 0.0 },
        created_at: new Date().toISOString(),
        updated_at: new Date().toISOString(),
      };
      this.sessions[taskId] = session;
    } else {
      session.status = 'COMPLETED';
    }

    return { task, session };
  }

  async suspendSession(sessionId: string): Promise<{ session_id: string; status: string; step: number; message: string }> {
    return {
      session_id: sessionId,
      status: 'SUSPENDED',
      step: 2,
      message: 'Demo session paused and state saved to mock store.',
    };
  }

  async resumeSession(sessionId: string): Promise<{ task: Task; session: Session }> {
    const session = Object.values(this.sessions).find((s) => s.session_id === sessionId);
    if (!session) throw new Error(`Session ${sessionId} not found`);
    session.status = 'ACTIVE';
    const task = this.tasks.find((t) => t.task_id === session.task_id)!;
    task.status = 'RUNNING';
    return { task, session };
  }

  async terminateSession(sessionId: string): Promise<{ task: Task; session: Session; message: string }> {
    const session = Object.values(this.sessions).find((s) => s.session_id === sessionId);
    if (!session) throw new Error(`Session ${sessionId} not found`);
    session.status = 'FAILED';
    const task = this.tasks.find((t) => t.task_id === session.task_id)!;
    task.status = 'BLOCKED';
    task.result_summary = 'Terminated by demo operator.';
    return { task, session, message: 'Session terminated.' };
  }

  async listWorkspaceFiles(): Promise<WorkspaceFilesResponse> {
    return {
      workspace_root: '/root/zakxterlab/workspace',
      current_path: '.',
      entries: [
        { name: 'dispatch.py', is_directory: false, size_bytes: 4096 },
        { name: 'config.json', is_directory: false, size_bytes: 512 },
        { name: 'tests', is_directory: true, size_bytes: 0 },
        { name: 'artifacts', is_directory: true, size_bytes: 0 },
      ],
    };
  }

  async getFileContent(path: string): Promise<FileContentResponse> {
    return {
      path,
      content: `# ZaxterLab Workspace File: ${path}\n# Governed by USD $0.00 spend guard and sandboxed environment.\n\nprint("Worker 1 operational.")\n`,
      size_bytes: 128,
    };
  }

  async getAuditLogs(): Promise<AuditLogEntry[]> {
    return [
      {
        id: 1,
        timestamp: new Date(Date.now() - 3600000).toISOString(),
        event_type: 'SYSTEM_BOOT',
        entity_id: 'reem-worker-1',
        details: { mode: 'DEMO', spend_bound_usd: 0.0 },
      },
      {
        id: 2,
        timestamp: new Date(Date.now() - 1200000).toISOString(),
        event_type: 'SESSION_CREATED',
        entity_id: 'sess_demo_02_alpha',
        details: { task_id: 'task_demo_02', agent: 'reem-worker-1' },
      },
      {
        id: 3,
        timestamp: new Date(Date.now() - 800000).toISOString(),
        event_type: 'STEP_EXECUTED',
        entity_id: 'sess_demo_02_alpha',
        details: { step: 2, tools_called: 1, tool_name: 'write_file' },
      },
    ];
  }
}
