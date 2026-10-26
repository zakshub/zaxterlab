"""JSON API request handlers for ZaxterLab."""

from __future__ import annotations

import os
import uuid
from typing import Any, Optional

from zaxterlab.contracts.types import SessionStatus, Task, TaskStatus, utc_now_iso
from zaxterlab.db.sqlite import SQLiteStore
from zaxterlab.engine.worker import Worker1Engine
from zaxterlab.security.guard import (
    BoundaryGuard,
    PermissionDeniedError,
    SecurityViolationError,
    SpendViolationError,
    WorkspacePathViolationError,
)


class APIHandlerService:
    """Core service executing API operations against the engine and store."""

    def __init__(
        self,
        store: SQLiteStore,
        engine: Worker1Engine,
        boundary_guard: BoundaryGuard,
    ) -> None:
        self.store = store
        self.engine = engine
        self.boundary_guard = boundary_guard

    def get_health(self) -> dict[str, Any]:
        """System health, dual-worker status, and spend guard status."""
        auditor_info = None
        if self.engine.auditor:
            auditor_info = {
                "agent_id": self.engine.auditor.agent.agent_id,
                "name": self.engine.auditor.agent.name,
                "role": self.engine.auditor.agent.role,
                "status": "ACTIVE",
                "permission_tier": self.engine.auditor.agent.permission_tier.value,
                "allowed_tools": self.engine.auditor.agent.allowed_tools,
            }

        return {
            "status": "healthy",
            "version": "0.2.0-phase2",
            "mode": "offline",
            "active_worker_count": 2 if self.engine.auditor else 1,
            "worker": {
                "agent_id": self.engine.agent.agent_id,
                "name": self.engine.agent.name,
                "role": self.engine.agent.role,
                "status": "IDLE",
                "max_iterations": self.engine.agent.max_iterations,
                "allowed_tools": self.engine.agent.allowed_tools,
            },
            "auditor": auditor_info,
            "spend_guard": {
                "authorized_spend_usd": self.boundary_guard.spend.authorized_spend_usd,
                "cumulative_spent_usd": self.boundary_guard.spend.cumulative_spent_usd,
                "spend_locked": True,
            },
            "workspace": {
                "root": str(self.boundary_guard.workspace.workspace_root),
                "sandboxed": True,
            },
        }

    def list_tasks(self, status: Optional[str] = None) -> dict[str, Any]:
        """List tasks, optionally filtered by status."""
        filter_status = None
        if status:
            try:
                filter_status = TaskStatus(status.upper())
            except ValueError:
                pass

        tasks = self.store.list_tasks(filter_status)
        return {"tasks": [t.to_dict() for t in tasks]}

    def create_task(self, data: dict[str, Any]) -> dict[str, Any]:
        """Create a new task."""
        title = data.get("title", "").strip()
        description = data.get("description", "").strip()
        if not title:
            raise ValueError("Task 'title' is required.")

        task_id = f"task_{uuid.uuid4().hex[:8]}"
        task = Task(
            task_id=task_id,
            title=title,
            description=description,
            status=TaskStatus.SUBMITTED,
            input_context=dict(data.get("input_context", {})),
            created_at=utc_now_iso(),
            updated_at=utc_now_iso(),
        )

        self.store.save_task(task)
        self.store.log_audit("TASK_CREATED_VIA_API", task.task_id, {"title": title})
        return {"task": task.to_dict()}

    def get_task_details(self, task_id: str) -> dict[str, Any]:
        """Get task with its latest session and step traces."""
        task = self.store.get_task(task_id)
        if not task:
            raise FileNotFoundError(f"Task '{task_id}' not found.")

        latest_session = self.store.get_latest_session_for_task(task_id)
        return {
            "task": task.to_dict(),
            "session": latest_session.to_dict() if latest_session else None,
        }

    def execute_task(self, task_id: str, data: Optional[dict[str, Any]] = None) -> dict[str, Any]:
        """Run or advance execution of a task."""
        task = self.store.get_task(task_id)
        if not task:
            raise FileNotFoundError(f"Task '{task_id}' not found.")

        max_steps = None
        if data and "max_steps" in data:
            max_steps = int(data["max_steps"])

        session = self.engine.execute_task(task, max_steps_per_run=max_steps)
        updated_task = self.store.get_task(task_id)

        return {
            "task": updated_task.to_dict() if updated_task else task.to_dict(),
            "session": session.to_dict(),
        }

    def suspend_session(self, session_id: str) -> dict[str, Any]:
        """Suspend an active session."""
        session = self.store.get_session(session_id)
        if not session:
            raise FileNotFoundError(f"Session '{session_id}' not found.")

        task = self.store.get_task(session.task_id)
        if not task:
            raise FileNotFoundError(f"Associated task '{session.task_id}' not found.")

        suspended_session = self.engine.suspend_session(task, session)
        return {
            "session_id": suspended_session.session_id,
            "status": suspended_session.status.value,
            "step": suspended_session.current_step,
            "message": "Session successfully suspended. State preserved.",
        }

    def resume_session(self, session_id: str, data: Optional[dict[str, Any]] = None) -> dict[str, Any]:
        """Resume a suspended session."""
        session = self.store.get_session(session_id)
        if not session:
            raise FileNotFoundError(f"Session '{session_id}' not found.")

        task = self.store.get_task(session.task_id)
        if not task:
            raise FileNotFoundError(f"Associated task '{session.task_id}' not found.")

        max_steps = None
        if data and "max_steps" in data:
            max_steps = int(data["max_steps"])

        resumed_session = self.engine.execute_task(
            task,
            resume_session_id=session_id,
            max_steps_per_run=max_steps,
        )
        updated_task = self.store.get_task(task.task_id)

        return {
            "task": updated_task.to_dict() if updated_task else task.to_dict(),
            "session": resumed_session.to_dict(),
        }

    def terminate_session(self, session_id: str, data: Optional[dict[str, Any]] = None) -> dict[str, Any]:
        """Explicitly terminate a session."""
        session = self.store.get_session(session_id)
        if not session:
            raise FileNotFoundError(f"Session '{session_id}' not found.")

        task = self.store.get_task(session.task_id)
        if not task:
            raise FileNotFoundError(f"Associated task '{session.task_id}' not found.")

        reason = (data or {}).get("reason", "Terminated by user request")
        terminated_session = self.engine.terminate_session(task, session, reason=reason)
        updated_task = self.store.get_task(task.task_id)

        return {
            "task": updated_task.to_dict() if updated_task else task.to_dict(),
            "session": terminated_session.to_dict(),
            "message": "Session terminated.",
        }

    def list_workspace_files(self, relative_path: str = ".") -> dict[str, Any]:
        """List files in the sandboxed workspace."""
        safe_path = self.boundary_guard.workspace.resolve_safe_path(relative_path)
        if not safe_path.exists():
            raise FileNotFoundError(f"Path not found: '{relative_path}'.")
        if not safe_path.is_dir():
            raise NotADirectoryError(f"Path is not a directory: '{relative_path}'.")

        entries = []
        for item in sorted(os.listdir(safe_path)):
            item_path = safe_path / item
            entries.append(
                {
                    "name": item,
                    "is_directory": item_path.is_dir(),
                    "size_bytes": item_path.stat().st_size if item_path.is_file() else 0,
                }
            )

        return {
            "workspace_root": str(self.boundary_guard.workspace.workspace_root),
            "current_path": relative_path,
            "entries": entries,
        }

    def get_file_content(self, relative_path: str) -> dict[str, Any]:
        """Read text file content safely within workspace."""
        safe_path = self.boundary_guard.workspace.resolve_safe_path(relative_path)
        if not safe_path.exists() or not safe_path.is_file():
            raise FileNotFoundError(f"File not found: '{relative_path}'.")

        with open(safe_path, "r", encoding="utf-8") as f:
            content = f.read()

        return {
            "path": relative_path,
            "content": content,
            "size_bytes": len(content),
        }

    def get_audit_logs(self, entity_id: Optional[str] = None) -> dict[str, Any]:
        """Retrieve audit events."""
        logs = self.store.get_audit_logs(entity_id)
        return {"audit_logs": logs}
