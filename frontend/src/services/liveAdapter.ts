/**
 * Live Backend API Adapter for ZaxterLab
 * Connects directly to http://127.0.0.1:8000/api
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

export class LiveApiAdapter implements ApiClient {
  public isDemo = false;
  private baseUrl: string;

  constructor(baseUrl: string = '/api') {
    this.baseUrl = baseUrl.replace(/\/$/, '');
  }

  private async request<T>(path: string, options: RequestInit = {}): Promise<T> {
    const url = `${this.baseUrl}${path}`;
    const headers: Record<string, string> = {
      'Content-Type': 'application/json',
      Accept: 'application/json',
      ...(options.headers as Record<string, string>),
    };

    const response = await fetch(url, { ...options, headers });
    const data = await response.json().catch(() => ({}));

    if (!response.ok) {
      const errorMsg = data?.error?.message || `HTTP ${response.status}: ${response.statusText}`;
      const errorCode = data?.error?.code || 'UNKNOWN_ERROR';
      const err = new Error(`[${errorCode}] ${errorMsg}`);
      (err as any).code = errorCode;
      (err as any).status = response.status;
      throw err;
    }

    return data as T;
  }

  async getHealth(): Promise<SystemHealth> {
    return this.request<SystemHealth>('/health');
  }

  async listTasks(status?: TaskStatus): Promise<Task[]> {
    const query = status ? `?status=${encodeURIComponent(status)}` : '';
    const res = await this.request<{ tasks: Task[] }>(`/tasks${query}`);
    return res.tasks;
  }

  async createTask(title: string, description: string, inputContext: Record<string, any> = {}): Promise<Task> {
    const res = await this.request<{ task: Task }>('/tasks', {
      method: 'POST',
      body: JSON.stringify({ title, description, input_context: inputContext }),
    });
    return res.task;
  }

  async getTaskDetails(taskId: string): Promise<{ task: Task; session: Session | null }> {
    return this.request<{ task: Task; session: Session | null }>(`/tasks/${encodeURIComponent(taskId)}`);
  }

  async executeTask(taskId: string, maxSteps?: number): Promise<{ task: Task; session: Session }> {
    return this.request<{ task: Task; session: Session }>(`/tasks/${encodeURIComponent(taskId)}/execute`, {
      method: 'POST',
      body: JSON.stringify(maxSteps ? { max_steps: maxSteps } : {}),
    });
  }

  async suspendSession(sessionId: string): Promise<{ session_id: string; status: string; step: number; message: string }> {
    return this.request<{ session_id: string; status: string; step: number; message: string }>(
      `/sessions/${encodeURIComponent(sessionId)}/suspend`,
      { method: 'POST' }
    );
  }

  async resumeSession(sessionId: string, maxSteps?: number): Promise<{ task: Task; session: Session }> {
    return this.request<{ task: Task; session: Session }>(
      `/sessions/${encodeURIComponent(sessionId)}/resume`,
      {
        method: 'POST',
        body: JSON.stringify(maxSteps ? { max_steps: maxSteps } : {}),
      }
    );
  }

  async terminateSession(sessionId: string, reason: string = 'User initiated'): Promise<{ task: Task; session: Session; message: string }> {
    return this.request<{ task: Task; session: Session; message: string }>(
      `/sessions/${encodeURIComponent(sessionId)}/terminate`,
      {
        method: 'POST',
        body: JSON.stringify({ reason }),
      }
    );
  }

  async listWorkspaceFiles(path: string = '.'): Promise<WorkspaceFilesResponse> {
    return this.request<WorkspaceFilesResponse>(`/workspace/files?path=${encodeURIComponent(path)}`);
  }

  async getFileContent(path: string): Promise<FileContentResponse> {
    return this.request<FileContentResponse>(`/workspace/file-content?path=${encodeURIComponent(path)}`);
  }

  async getAuditLogs(entityId?: string): Promise<AuditLogEntry[]> {
    const query = entityId ? `?entity_id=${encodeURIComponent(entityId)}` : '';
    const res = await this.request<{ audit_logs: AuditLogEntry[] }>(`/audit-logs${query}`);
    return res.audit_logs;
  }
}
