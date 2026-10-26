"""SQLite persistence engine using Python's standard library sqlite3."""

from __future__ import annotations

import json
import sqlite3
from pathlib import Path
from typing import Any, Optional

from zaxterlab.contracts.types import (
    Session,
    SessionStatus,
    StepTrace,
    Task,
    TaskStatus,
    TokenUsage,
)


class SQLiteStore:
    """Hermetic SQLite storage engine for ZaxterLab state, tasks, and audit traces."""

    def __init__(self, db_path: str | Path = ":memory:") -> None:
        self.db_path = str(db_path)
        if self.db_path != ":memory:":
            Path(self.db_path).parent.mkdir(parents=True, exist_ok=True)

        self._conn = sqlite3.connect(self.db_path, check_same_thread=False)
        self._conn.row_factory = sqlite3.Row
        self._init_schema()

    def _init_schema(self) -> None:
        """Create tables and indexes if they do not exist."""
        with self._conn:
            self._conn.executescript(
                """
                PRAGMA foreign_keys = ON;

                CREATE TABLE IF NOT EXISTS tasks (
                    task_id TEXT PRIMARY KEY,
                    title TEXT NOT NULL,
                    description TEXT NOT NULL,
                    status TEXT NOT NULL,
                    assigned_agent_id TEXT,
                    input_context_json TEXT NOT NULL,
                    result_summary TEXT,
                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL
                );

                CREATE TABLE IF NOT EXISTS sessions (
                    session_id TEXT PRIMARY KEY,
                    task_id TEXT NOT NULL,
                    agent_id TEXT NOT NULL,
                    status TEXT NOT NULL,
                    current_step INTEGER NOT NULL,
                    state_data_json TEXT NOT NULL,
                    total_token_usage_json TEXT NOT NULL,
                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL,
                    FOREIGN KEY (task_id) REFERENCES tasks(task_id) ON DELETE CASCADE
                );

                CREATE TABLE IF NOT EXISTS step_traces (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    session_id TEXT NOT NULL,
                    step_number INTEGER NOT NULL,
                    phase TEXT NOT NULL,
                    observation TEXT NOT NULL,
                    plan TEXT,
                    tool_calls_json TEXT NOT NULL,
                    tool_results_json TEXT NOT NULL,
                    evaluation TEXT,
                    token_usage_json TEXT NOT NULL,
                    created_at TEXT NOT NULL,
                    FOREIGN KEY (session_id) REFERENCES sessions(session_id) ON DELETE CASCADE
                );

                CREATE TABLE IF NOT EXISTS audit_logs (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    timestamp TEXT NOT NULL,
                    event_type TEXT NOT NULL,
                    entity_id TEXT NOT NULL,
                    details_json TEXT NOT NULL
                );

                CREATE INDEX IF NOT EXISTS idx_tasks_status ON tasks(status);
                CREATE INDEX IF NOT EXISTS idx_sessions_task ON sessions(task_id);
                CREATE INDEX IF NOT EXISTS idx_step_traces_session ON step_traces(session_id);
                """
            )

    def close(self) -> None:
        """Close database connection."""
        self._conn.close()

    # --- Task Operations ---

    def save_task(self, task: Task) -> None:
        """Insert or update a task record."""
        with self._conn:
            self._conn.execute(
                """
                INSERT INTO tasks (
                    task_id, title, description, status,
                    assigned_agent_id, input_context_json,
                    result_summary, created_at, updated_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(task_id) DO UPDATE SET
                    title = excluded.title,
                    description = excluded.description,
                    status = excluded.status,
                    assigned_agent_id = excluded.assigned_agent_id,
                    input_context_json = excluded.input_context_json,
                    result_summary = excluded.result_summary,
                    updated_at = excluded.updated_at
                """,
                (
                    task.task_id,
                    task.title,
                    task.description,
                    task.status.value,
                    task.assigned_agent_id,
                    json.dumps(task.input_context),
                    task.result_summary,
                    task.created_at,
                    task.updated_at,
                ),
            )

    def get_task(self, task_id: str) -> Optional[Task]:
        """Fetch a task by ID."""
        cursor = self._conn.execute(
            "SELECT * FROM tasks WHERE task_id = ?",
            (task_id,),
        )
        row = cursor.fetchone()
        if not row:
            return None

        return Task(
            task_id=row["task_id"],
            title=row["title"],
            description=row["description"],
            status=TaskStatus(row["status"]),
            assigned_agent_id=row["assigned_agent_id"],
            input_context=json.loads(row["input_context_json"]),
            result_summary=row["result_summary"],
            created_at=row["created_at"],
            updated_at=row["updated_at"],
        )

    def list_tasks(self, status: Optional[TaskStatus] = None) -> list[Task]:
        """List all tasks, optionally filtered by status."""
        if status:
            cursor = self._conn.execute(
                "SELECT * FROM tasks WHERE status = ? ORDER BY created_at ASC",
                (status.value,),
            )
        else:
            cursor = self._conn.execute(
                "SELECT * FROM tasks ORDER BY created_at ASC"
            )

        results = []
        for row in cursor.fetchall():
            results.append(
                Task(
                    task_id=row["task_id"],
                    title=row["title"],
                    description=row["description"],
                    status=TaskStatus(row["status"]),
                    assigned_agent_id=row["assigned_agent_id"],
                    input_context=json.loads(row["input_context_json"]),
                    result_summary=row["result_summary"],
                    created_at=row["created_at"],
                    updated_at=row["updated_at"],
                )
            )
        return results

    # --- Session Operations ---

    def save_session(self, session: Session) -> None:
        """Insert or update an execution session and its step traces."""
        with self._conn:
            self._conn.execute(
                """
                INSERT INTO sessions (
                    session_id, task_id, agent_id, status,
                    current_step, state_data_json, total_token_usage_json,
                    created_at, updated_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(session_id) DO UPDATE SET
                    status = excluded.status,
                    current_step = excluded.current_step,
                    state_data_json = excluded.state_data_json,
                    total_token_usage_json = excluded.total_token_usage_json,
                    updated_at = excluded.updated_at
                """,
                (
                    session.session_id,
                    session.task_id,
                    session.agent_id,
                    session.status.value,
                    session.current_step,
                    json.dumps(session.state_data),
                    json.dumps(session.total_token_usage.to_dict()),
                    session.created_at,
                    session.updated_at,
                ),
            )

            # Persist any step traces not yet stored
            existing_count_row = self._conn.execute(
                "SELECT COUNT(*) as cnt FROM step_traces WHERE session_id = ?",
                (session.session_id,),
            ).fetchone()
            existing_count = existing_count_row["cnt"] if existing_count_row else 0

            for trace in session.step_traces[existing_count:]:
                self._conn.execute(
                    """
                    INSERT INTO step_traces (
                        session_id, step_number, phase, observation,
                        plan, tool_calls_json, tool_results_json,
                        evaluation, token_usage_json, created_at
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        session.session_id,
                        trace.step_number,
                        trace.phase,
                        trace.observation,
                        trace.plan,
                        json.dumps([tc.to_dict() for tc in trace.tool_calls]),
                        json.dumps([tr.to_dict() for tr in trace.tool_results]),
                        trace.evaluation,
                        json.dumps(trace.token_usage.to_dict()),
                        trace.created_at,
                    ),
                )

    def get_step_traces(self, session_id: str) -> list[StepTrace]:
        """Fetch all recorded step traces for a session."""
        cursor = self._conn.execute(
            "SELECT * FROM step_traces WHERE session_id = ? ORDER BY step_number ASC",
            (session_id,),
        )
        traces: list[StepTrace] = []
        for t_row in cursor.fetchall():
            trace_dict = {
                "step_number": t_row["step_number"],
                "phase": t_row["phase"],
                "observation": t_row["observation"],
                "plan": t_row["plan"],
                "tool_calls": json.loads(t_row["tool_calls_json"]),
                "tool_results": json.loads(t_row["tool_results_json"]),
                "evaluation": t_row["evaluation"],
                "token_usage": json.loads(t_row["token_usage_json"]),
                "created_at": t_row["created_at"],
            }
            traces.append(StepTrace.from_dict(trace_dict))
        return traces

    def get_session(self, session_id: str) -> Optional[Session]:
        """Fetch session and all its recorded step traces."""
        cursor = self._conn.execute(
            "SELECT * FROM sessions WHERE session_id = ?",
            (session_id,),
        )
        row = cursor.fetchone()
        if not row:
            return None

        traces = self.get_step_traces(session_id)

        return Session(
            session_id=row["session_id"],
            task_id=row["task_id"],
            agent_id=row["agent_id"],
            status=SessionStatus(row["status"]),
            current_step=row["current_step"],
            state_data=json.loads(row["state_data_json"]),
            step_traces=traces,
            total_token_usage=TokenUsage.from_dict(json.loads(row["total_token_usage_json"])),
            created_at=row["created_at"],
            updated_at=row["updated_at"],
        )

    def get_latest_session_for_task(self, task_id: str) -> Optional[Session]:
        """Fetch the most recent session for a given task ID."""
        cursor = self._conn.execute(
            "SELECT session_id FROM sessions WHERE task_id = ? ORDER BY updated_at DESC LIMIT 1",
            (task_id,),
        )
        row = cursor.fetchone()
        if not row:
            return None
        return self.get_session(row["session_id"])

    # --- Audit Operations ---

    def log_audit(self, event_type: str, entity_id: str, details: dict[str, Any]) -> None:
        """Record an immutable audit log entry."""
        from zaxterlab.contracts.types import utc_now_iso

        with self._conn:
            self._conn.execute(
                """
                INSERT INTO audit_logs (timestamp, event_type, entity_id, details_json)
                VALUES (?, ?, ?, ?)
                """,
                (utc_now_iso(), event_type, entity_id, json.dumps(details)),
            )

    def get_audit_logs(self, entity_id: Optional[str] = None) -> list[dict[str, Any]]:
        """Fetch audit log entries."""
        if entity_id:
            cursor = self._conn.execute(
                "SELECT * FROM audit_logs WHERE entity_id = ? ORDER BY id ASC",
                (entity_id,),
            )
        else:
            cursor = self._conn.execute(
                "SELECT * FROM audit_logs ORDER BY id ASC"
            )

        logs = []
        for row in cursor.fetchall():
            logs.append(
                {
                    "id": row["id"],
                    "timestamp": row["timestamp"],
                    "event_type": row["event_type"],
                    "entity_id": row["entity_id"],
                    "details": json.loads(row["details_json"]),
                }
            )
        return logs
