/**
 * TypeScript Data Models matching docs/API_CONTRACT.md
 */

export type TaskStatus =
  | 'SUBMITTED'
  | 'QUEUED'
  | 'RUNNING'
  | 'REVIEW'
  | 'COMPLETED'
  | 'FAILED'
  | 'SUSPENDED'
  | 'BLOCKED';

export type SessionStatus =
  | 'CREATED'
  | 'ACTIVE'
  | 'SUSPENDED'
  | 'COMPLETED'
  | 'FAILED';

export interface TokenUsage {
  prompt_tokens: number;
  completion_tokens: number;
  total_tokens: number;
  estimated_cost_usd: number;
}

export interface ToolCall {
  call_id: string;
  tool_name: string;
  arguments: Record<string, any>;
}

export interface ToolResult {
  call_id: string;
  tool_name: string;
  success: boolean;
  output: string;
  error?: string | null;
}

export interface StepTrace {
  step_number: number;
  phase: string; // READ, PLAN, TOOL_CALL, EVALUATE, LOG, CYCLE
  observation: string;
  plan?: string | null;
  tool_calls: ToolCall[];
  tool_results: ToolResult[];
  evaluation?: string | null;
  token_usage: TokenUsage;
  created_at: string;
}

export interface Task {
  task_id: string;
  title: string;
  description: string;
  status: TaskStatus;
  assigned_agent_id?: string | null;
  input_context: Record<string, any>;
  result_summary?: string | null;
  created_at: string;
  updated_at: string;
}

export interface Session {
  session_id: string;
  task_id: string;
  agent_id: string;
  status: SessionStatus;
  current_step: number;
  state_data: Record<string, any>;
  step_traces: StepTrace[];
  total_token_usage: TokenUsage;
  created_at: string;
  updated_at: string;
}

export interface WorkerInfo {
  agent_id: string;
  name: string;
  role: string;
  status: string;
  max_iterations: number;
  allowed_tools: string[];
}

export interface SpendGuardStatus {
  authorized_spend_usd: number;
  cumulative_spent_usd: number;
  spend_locked: boolean;
}

export interface WorkspaceStatus {
  root: string;
  sandboxed: boolean;
}

export interface SystemHealth {
  status: 'healthy' | 'degraded' | 'offline';
  version: string;
  mode: 'offline' | 'online' | 'demo';
  worker: WorkerInfo;
  spend_guard: SpendGuardStatus;
  workspace: WorkspaceStatus;
}

export interface WorkspaceEntry {
  name: string;
  is_directory: boolean;
  size_bytes: number;
}

export interface WorkspaceFilesResponse {
  workspace_root: string;
  current_path: string;
  entries: WorkspaceEntry[];
}

export interface FileContentResponse {
  path: string;
  content: string;
  size_bytes: number;
}

export interface AuditLogEntry {
  id: number;
  timestamp: string;
  event_type: string;
  entity_id: string;
  details: Record<string, any>;
}

export interface ApiClient {
  getHealth(): Promise<SystemHealth>;
  listTasks(status?: TaskStatus): Promise<Task[]>;
  createTask(title: string, description: string, inputContext?: Record<string, any>): Promise<Task>;
  getTaskDetails(taskId: string): Promise<{ task: Task; session: Session | null }>;
  executeTask(taskId: string, maxSteps?: number): Promise<{ task: Task; session: Session }>;
  suspendSession(sessionId: string): Promise<{ session_id: string; status: string; step: number; message: string }>;
  resumeSession(sessionId: string, maxSteps?: number): Promise<{ task: Task; session: Session }>;
  terminateSession(sessionId: string, reason?: string): Promise<{ task: Task; session: Session; message: string }>;
  listWorkspaceFiles(path?: string): Promise<WorkspaceFilesResponse>;
  getFileContent(path: string): Promise<FileContentResponse>;
  getAuditLogs(entityId?: string): Promise<AuditLogEntry[]>;
}
