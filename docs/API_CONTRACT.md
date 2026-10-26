# ZaxterLab HTTP API Contract

**Version**: 1.0.0  
**Base URL**: `/api`  
**Governing Source of Truth**: `zaxterlab/contracts/types.py`  
**Spend Invariant**: Default USD $0.00 Authorized Limit  

---

## 1. Overview & Security Invariants

The ZaxterLab API provides a deterministic, lightweight JSON REST interface for the ZaxterLab AI Company Operating System.

### Invariants:
1. **Zero Spend Boundary**: Spend status is enforced at the backend level. No client request can authorize spending.
2. **Workspace Sandboxing**: Path inspections are constrained to the configured workspace root; arbitrary system paths are blocked.
3. **No Unrestricted Execution**: The API never accepts arbitrary shell commands. Only safe, whitelisted worker actions are executed.
4. **Human Authority**: Consequential actions fail closed.

---

## 2. Data Types & Lifecycle States

### Task Lifecycle Status (`TaskStatus`)
- `SUBMITTED`: Created and pending dispatch.
- `QUEUED`: Accepted by orchestrator and awaiting worker assignment.
- `RUNNING`: Actively executing a cycle step.
- `REVIEW`: Awaiting verification or audit.
- `COMPLETED`: Successfully executed and verified.
- `FAILED`: Aborted due to unrecoverable tool failure or maximum iteration limit.
- `SUSPENDED`: Execution paused; memory serialized to SQLite.
- `BLOCKED`: Halted by SpendGuard or security boundary violation.

### Session Lifecycle Status (`SessionStatus`)
- `CREATED`: Initialized but no steps executed.
- `ACTIVE`: Actively executing steps.
- `SUSPENDED`: Memory serialized to disk; idle.
- `COMPLETED`: Finished execution loop.
- `FAILED`: Execution terminated with error.

---

## 3. Endpoints

### 3.1 System Health & Spend Guard
- **`GET /api/health`**
  - **Description**: Returns system status, worker health, database connectivity, and spend-guard boundaries.
  - **Response `200 OK`**:
    ```json
    {
      "status": "healthy",
      "version": "0.1.0",
      "mode": "offline",
      "worker": {
        "agent_id": "reem-worker-1",
        "name": "Reem",
        "role": "Construction and Programming",
        "status": "IDLE"
      },
      "spend_guard": {
        "authorized_spend_usd": 0.0,
        "cumulative_spent_usd": 0.0,
        "spend_locked": true
      },
      "workspace": {
        "root": "/root/zakxterlab/workspace",
        "sandboxed": true
      }
    }
    ```

---

### 3.2 Task Management
- **`GET /api/tasks`**
  - **Description**: List all tasks, optionally filtered by status query parameter.
  - **Query Params**: `status` (optional, e.g. `?status=RUNNING`)
  - **Response `200 OK`**:
    ```json
    {
      "tasks": [
        {
          "task_id": "task-001",
          "title": "Build File Parser",
          "description": "Parse log files",
          "status": "COMPLETED",
          "assigned_agent_id": "reem-worker-1",
          "input_context": {},
          "result_summary": "Parsed 10 records",
          "created_at": "2026-10-26T00:00:00Z",
          "updated_at": "2026-10-26T00:01:00Z"
        }
      ]
    }
    ```

- **`POST /api/tasks`**
  - **Description**: Submit a new task into the operating system.
  - **Request Body**:
    ```json
    {
      "title": "Create Project Readme",
      "description": "Generate README.md in workspace",
      "input_context": { "author": "Zak" }
    }
    ```
  - **Response `201 Created`**:
    ```json
    {
      "task": {
        "task_id": "task-abc123",
        "title": "Create Project Readme",
        "description": "Generate README.md in workspace",
        "status": "SUBMITTED",
        "assigned_agent_id": null,
        "input_context": { "author": "Zak" },
        "result_summary": null,
        "created_at": "2026-10-26T00:00:00Z",
        "updated_at": "2026-10-26T00:00:00Z"
      }
    }
    ```

- **`GET /api/tasks/{task_id}`**
  - **Description**: Fetch detailed task record including latest session and step traces.
  - **Response `200 OK`**:
    ```json
    {
      "task": { ... },
      "session": {
        "session_id": "sess_task-abc123_01",
        "task_id": "task-abc123",
        "agent_id": "reem-worker-1",
        "status": "COMPLETED",
        "current_step": 2,
        "total_token_usage": {
          "prompt_tokens": 45,
          "completion_tokens": 60,
          "total_tokens": 105,
          "estimated_cost_usd": 0.0
        },
        "step_traces": [ ... ]
      }
    }
    ```

---

### 3.3 Task Execution & Session Controls
- **`POST /api/tasks/{task_id}/execute`**
  - **Description**: Trigger or continue execution of a task with Worker 1.
  - **Request Body**: Optional `{ "max_steps": 5 }`
  - **Response `200 OK`**: Returns updated task and session objects.

- **`POST /api/sessions/{session_id}/suspend`**
  - **Description**: Suspend an active session, serializing working memory to SQLite.
  - **Response `200 OK`**:
    ```json
    {
      "session_id": "sess_001",
      "status": "SUSPENDED",
      "step": 1,
      "message": "Session suspended and state preserved."
    }
    ```

- **`POST /api/sessions/{session_id}/resume`**
  - **Description**: Resume a suspended session from stored episodic memory.
  - **Response `200 OK`**: Returns resumed session with status `ACTIVE` or `COMPLETED`.

- **`POST /api/sessions/{session_id}/terminate`**
  - **Description**: Safely cancel or terminate an active or suspended session.
  - **Request Body**: Optional `{ "reason": "User abort" }`
  - **Response `200 OK`**: Returns terminated session with status `FAILED` and task status `BLOCKED`.

---

### 3.4 Workspace & File Inspection
- **`GET /api/workspace/files`**
  - **Description**: List files and directories within the sandboxed workspace.
  - **Query Params**: `path` (optional, relative to workspace root)
  - **Response `200 OK`**:
    ```json
    {
      "workspace_root": "/root/zakxterlab/workspace",
      "current_path": ".",
      "entries": ["greeting.txt", "output.json", "subfolder"]
    }
    ```

- **`GET /api/workspace/file-content`**
  - **Description**: Safely read file content within the sandboxed workspace.
  - **Query Params**: `path` (required)
  - **Response `200 OK`**:
    ```json
    {
      "path": "greeting.txt",
      "content": "ZaxterLab Phase 1 Active\n",
      "size_bytes": 26
    }
    ```

---

### 3.5 Audit & Execution Traces
- **`GET /api/audit-logs`**
  - **Description**: Retrieve immutable audit log events.
  - **Query Params**: `entity_id` (optional)
  - **Response `200 OK`**:
    ```json
    {
      "audit_logs": [
        {
          "id": 1,
          "timestamp": "2026-10-26T00:00:00Z",
          "event_type": "SESSION_CREATED",
          "entity_id": "sess_001",
          "details": { "agent": "reem-worker-1" }
        }
      ]
    }
    ```

---

## 4. Error Responses

Standard JSON error envelopes:
```json
{
  "error": {
    "code": "NOT_FOUND | VALIDATION_ERROR | SPEND_VIOLATION | PERMISSION_DENIED | SECURITY_VIOLATION",
    "message": "Human-readable description of error.",
    "details": {}
  }
}
```
