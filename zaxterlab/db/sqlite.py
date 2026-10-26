"""SQLite persistence engine using Python's standard library sqlite3."""

from __future__ import annotations

import json
import sqlite3
from pathlib import Path
from typing import Any, Optional

from zaxterlab.contracts.types import (
    CompanyProject,
    PermissionTier,
    ProposalStatus,
    RegisteredSpecialist,
    Session,
    SessionStatus,
    SpawningProposal,
    StepTrace,
    Task,
    TaskStatus,
    TokenUsage,
    TradeoffChoice,
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
                    assigned_specialist TEXT,
                    input_context_json TEXT NOT NULL,
                    depends_on_json TEXT NOT NULL DEFAULT '[]',
                    retry_count INTEGER NOT NULL DEFAULT 0,
                    max_retries INTEGER NOT NULL DEFAULT 2,
                    result_summary TEXT,
                    error_message TEXT,
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

                CREATE TABLE IF NOT EXISTS spawning_proposals (
                    proposal_id TEXT PRIMARY KEY,
                    target_role_name TEXT NOT NULL,
                    target_role_title TEXT NOT NULL,
                    archetype TEXT NOT NULL,
                    recommended_permission_tier TEXT NOT NULL,
                    recommended_tools_json TEXT NOT NULL,
                    tradeoff_choice TEXT NOT NULL,
                    empirical_justification TEXT NOT NULL,
                    tradeoff_analysis_json TEXT NOT NULL,
                    status TEXT NOT NULL,
                    created_at TEXT NOT NULL,
                    decided_at TEXT,
                    decision_reason TEXT
                );

                CREATE TABLE IF NOT EXISTS specialists (
                    worker_id TEXT PRIMARY KEY,
                    name TEXT NOT NULL,
                    role TEXT NOT NULL,
                    archetype TEXT NOT NULL,
                    department TEXT NOT NULL,
                    capabilities_json TEXT NOT NULL DEFAULT '[]',
                    capability_gap_filled TEXT NOT NULL DEFAULT '',
                    instructions TEXT NOT NULL DEFAULT '',
                    operating_boundaries TEXT NOT NULL DEFAULT '',
                    allowed_tools_json TEXT NOT NULL DEFAULT '[]',
                    permission_tier TEXT NOT NULL,
                    eligible_for_assignment INTEGER NOT NULL DEFAULT 1,
                    is_temporary INTEGER NOT NULL DEFAULT 0,
                    reusable INTEGER NOT NULL DEFAULT 1,
                    lifecycle_state TEXT NOT NULL DEFAULT 'ACTIVE',
                    runtime_status TEXT NOT NULL DEFAULT 'AVAILABLE',
                    current_task_id TEXT,
                    tasks_completed INTEGER NOT NULL DEFAULT 0,
                    tokens_used INTEGER NOT NULL DEFAULT 0,
                    recent_outputs_json TEXT NOT NULL DEFAULT '[]',
                    proposal_id TEXT,
                    deactivation_rule TEXT NOT NULL DEFAULT '',
                    mascot_profile_json TEXT NOT NULL DEFAULT '{}',
                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL
                );

                CREATE TABLE IF NOT EXISTS projects (
                    project_id TEXT PRIMARY KEY,
                    name TEXT NOT NULL,
                    slug TEXT NOT NULL,
                    project_type TEXT NOT NULL,
                    priority TEXT NOT NULL,
                    objective TEXT NOT NULL,
                    domain TEXT NOT NULL,
                    status TEXT NOT NULL,
                    current_stage TEXT NOT NULL,
                    lead_specialist TEXT NOT NULL,
                    workspace_path TEXT NOT NULL,
                    epics_json TEXT NOT NULL DEFAULT '[]',
                    capability_assessment_json TEXT NOT NULL DEFAULT '{}',
                    acceptance_criteria_json TEXT NOT NULL DEFAULT '[]',
                    artifacts_json TEXT NOT NULL DEFAULT '[]',
                    approvals_json TEXT NOT NULL DEFAULT '[]',
                    spend_usd REAL NOT NULL DEFAULT 0.0,
                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL
                );

                CREATE INDEX IF NOT EXISTS idx_tasks_status ON tasks(status);
                CREATE INDEX IF NOT EXISTS idx_sessions_task ON sessions(task_id);
                CREATE INDEX IF NOT EXISTS idx_step_traces_session ON step_traces(session_id);
                CREATE INDEX IF NOT EXISTS idx_proposals_status ON spawning_proposals(status);
                """
            )
            # Migration check: add new columns if table existed before
            cursor = self._conn.execute("PRAGMA table_info(tasks)")
            cols = {row["name"] for row in cursor.fetchall()}
            if "depends_on_json" not in cols:
                self._conn.execute("ALTER TABLE tasks ADD COLUMN depends_on_json TEXT DEFAULT '[]'")
            if "retry_count" not in cols:
                self._conn.execute("ALTER TABLE tasks ADD COLUMN retry_count INTEGER DEFAULT 0")
            if "max_retries" not in cols:
                self._conn.execute("ALTER TABLE tasks ADD COLUMN max_retries INTEGER DEFAULT 2")
            if "assigned_specialist" not in cols:
                self._conn.execute("ALTER TABLE tasks ADD COLUMN assigned_specialist TEXT")
            if "error_message" not in cols:
                self._conn.execute("ALTER TABLE tasks ADD COLUMN error_message TEXT")
            if "project_id" not in cols:
                self._conn.execute("ALTER TABLE tasks ADD COLUMN project_id TEXT")
            if "epic_id" not in cols:
                self._conn.execute("ALTER TABLE tasks ADD COLUMN epic_id TEXT")
            if "epic_title" not in cols:
                self._conn.execute("ALTER TABLE tasks ADD COLUMN epic_title TEXT")
            if "feature_id" not in cols:
                self._conn.execute("ALTER TABLE tasks ADD COLUMN feature_id TEXT")
            if "feature_title" not in cols:
                self._conn.execute("ALTER TABLE tasks ADD COLUMN feature_title TEXT")
            if "department" not in cols:
                self._conn.execute("ALTER TABLE tasks ADD COLUMN department TEXT")
            if "priority" not in cols:
                self._conn.execute("ALTER TABLE tasks ADD COLUMN priority TEXT DEFAULT 'NORMAL'")
            if "acceptance_criteria_json" not in cols:
                self._conn.execute("ALTER TABLE tasks ADD COLUMN acceptance_criteria_json TEXT DEFAULT '[]'")
            if "artifact_paths_json" not in cols:
                self._conn.execute("ALTER TABLE tasks ADD COLUMN artifact_paths_json TEXT DEFAULT '[]'")
            if "verification_evidence" not in cols:
                self._conn.execute("ALTER TABLE tasks ADD COLUMN verification_evidence TEXT")

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
                    assigned_agent_id, assigned_specialist,
                    input_context_json, depends_on_json,
                    retry_count, max_retries,
                    result_summary, error_message,
                    project_id, epic_id, epic_title,
                    feature_id, feature_title, department,
                    priority, acceptance_criteria_json,
                    artifact_paths_json, verification_evidence,
                    created_at, updated_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(task_id) DO UPDATE SET
                    title = excluded.title,
                    description = excluded.description,
                    status = excluded.status,
                    assigned_agent_id = excluded.assigned_agent_id,
                    assigned_specialist = excluded.assigned_specialist,
                    input_context_json = excluded.input_context_json,
                    depends_on_json = excluded.depends_on_json,
                    retry_count = excluded.retry_count,
                    max_retries = excluded.max_retries,
                    result_summary = excluded.result_summary,
                    error_message = excluded.error_message,
                    project_id = excluded.project_id,
                    epic_id = excluded.epic_id,
                    epic_title = excluded.epic_title,
                    feature_id = excluded.feature_id,
                    feature_title = excluded.feature_title,
                    department = excluded.department,
                    priority = excluded.priority,
                    acceptance_criteria_json = excluded.acceptance_criteria_json,
                    artifact_paths_json = excluded.artifact_paths_json,
                    verification_evidence = excluded.verification_evidence,
                    updated_at = excluded.updated_at
                """,
                (
                    task.task_id,
                    task.title,
                    task.description,
                    task.status.value,
                    task.assigned_agent_id,
                    task.assigned_specialist,
                    json.dumps(task.input_context),
                    json.dumps(task.depends_on),
                    task.retry_count,
                    task.max_retries,
                    task.result_summary,
                    task.error_message,
                    task.project_id,
                    task.epic_id,
                    task.epic_title,
                    task.feature_id,
                    task.feature_title,
                    task.department,
                    task.priority,
                    json.dumps(task.acceptance_criteria),
                    json.dumps(task.artifact_paths),
                    task.verification_evidence,
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
        return self._row_to_task(row)

    def list_tasks(self, status: Optional[TaskStatus] = None, project_id: Optional[str] = None) -> list[Task]:
        """List all tasks, optionally filtered by status or project_id."""
        if status and project_id:
            cursor = self._conn.execute(
                "SELECT * FROM tasks WHERE status = ? AND project_id = ? ORDER BY created_at ASC",
                (status.value, project_id),
            )
        elif status:
            cursor = self._conn.execute(
                "SELECT * FROM tasks WHERE status = ? ORDER BY created_at ASC",
                (status.value,),
            )
        elif project_id:
            cursor = self._conn.execute(
                "SELECT * FROM tasks WHERE project_id = ? ORDER BY created_at ASC",
                (project_id,),
            )
        else:
            cursor = self._conn.execute(
                "SELECT * FROM tasks ORDER BY created_at ASC"
            )

        return [self._row_to_task(row) for row in cursor.fetchall()]

    def _row_to_task(self, row: sqlite3.Row) -> Task:
        cols = row.keys()
        depends_on = json.loads(row["depends_on_json"]) if "depends_on_json" in cols and row["depends_on_json"] else []
        retry_count = int(row["retry_count"]) if "retry_count" in cols and row["retry_count"] is not None else 0
        max_retries = int(row["max_retries"]) if "max_retries" in cols and row["max_retries"] is not None else 2
        assigned_specialist = row["assigned_specialist"] if "assigned_specialist" in cols else None
        error_message = row["error_message"] if "error_message" in cols else None
        project_id = row["project_id"] if "project_id" in cols else None
        epic_id = row["epic_id"] if "epic_id" in cols else None
        epic_title = row["epic_title"] if "epic_title" in cols else None
        feature_id = row["feature_id"] if "feature_id" in cols else None
        feature_title = row["feature_title"] if "feature_title" in cols else None
        department = row["department"] if "department" in cols else None
        priority = row["priority"] if "priority" in cols and row["priority"] else "NORMAL"
        acceptance_criteria = (
            json.loads(row["acceptance_criteria_json"])
            if "acceptance_criteria_json" in cols and row["acceptance_criteria_json"]
            else []
        )
        artifact_paths = (
            json.loads(row["artifact_paths_json"])
            if "artifact_paths_json" in cols and row["artifact_paths_json"]
            else []
        )
        verification_evidence = row["verification_evidence"] if "verification_evidence" in cols else None

        return Task(
            task_id=row["task_id"],
            title=row["title"],
            description=row["description"],
            status=TaskStatus(row["status"]),
            assigned_agent_id=row["assigned_agent_id"],
            assigned_specialist=assigned_specialist,
            input_context=json.loads(row["input_context_json"]),
            depends_on=depends_on,
            retry_count=retry_count,
            max_retries=max_retries,
            result_summary=row["result_summary"],
            error_message=error_message,
            project_id=project_id,
            epic_id=epic_id,
            epic_title=epic_title,
            feature_id=feature_id,
            feature_title=feature_title,
            department=department,
            priority=priority,
            acceptance_criteria=acceptance_criteria,
            artifact_paths=artifact_paths,
            verification_evidence=verification_evidence,
            created_at=row["created_at"],
            updated_at=row["updated_at"],
        )

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

    # --- Spawning Proposal Operations ---

    def save_proposal(self, proposal: SpawningProposal) -> None:
        """Insert or update a spawning proposal."""
        with self._conn:
            self._conn.execute(
                """
                INSERT INTO spawning_proposals (
                    proposal_id, target_role_name, target_role_title, archetype,
                    recommended_permission_tier, recommended_tools_json,
                    tradeoff_choice, empirical_justification, tradeoff_analysis_json,
                    status, created_at, decided_at, decision_reason
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(proposal_id) DO UPDATE SET
                    status = excluded.status,
                    decided_at = excluded.decided_at,
                    decision_reason = excluded.decision_reason
                """,
                (
                    proposal.proposal_id,
                    proposal.target_role_name,
                    proposal.target_role_title,
                    proposal.archetype,
                    proposal.recommended_permission_tier.value,
                    json.dumps(proposal.recommended_tools),
                    proposal.tradeoff_choice.value,
                    proposal.empirical_justification,
                    json.dumps(proposal.tradeoff_analysis),
                    proposal.status.value,
                    proposal.created_at,
                    proposal.decided_at,
                    proposal.decision_reason,
                ),
            )

    def get_proposal(self, proposal_id: str) -> Optional[SpawningProposal]:
        """Fetch proposal by ID."""
        cursor = self._conn.execute(
            "SELECT * FROM spawning_proposals WHERE proposal_id = ?",
            (proposal_id,),
        )
        row = cursor.fetchone()
        if not row:
            return None
        return self._row_to_proposal(row)

    def list_proposals(self, status: Optional[ProposalStatus] = None) -> list[SpawningProposal]:
        """List proposals, optionally filtered by status."""
        if status:
            cursor = self._conn.execute(
                "SELECT * FROM spawning_proposals WHERE status = ? ORDER BY created_at DESC",
                (status.value,),
            )
        else:
            cursor = self._conn.execute(
                "SELECT * FROM spawning_proposals ORDER BY created_at DESC"
            )

        return [self._row_to_proposal(row) for row in cursor.fetchall()]

    def _row_to_proposal(self, row: sqlite3.Row) -> SpawningProposal:
        return SpawningProposal(
            proposal_id=row["proposal_id"],
            target_role_name=row["target_role_name"],
            target_role_title=row["target_role_title"],
            archetype=row["archetype"],
            recommended_permission_tier=PermissionTier(row["recommended_permission_tier"]),
            recommended_tools=json.loads(row["recommended_tools_json"]),
            tradeoff_choice=TradeoffChoice(row["tradeoff_choice"]),
            empirical_justification=row["empirical_justification"],
            tradeoff_analysis=json.loads(row["tradeoff_analysis_json"]),
            status=ProposalStatus(row["status"]),
            created_at=row["created_at"],
            decided_at=row["decided_at"],
            decision_reason=row["decision_reason"],
        )

    # --- Registered Specialist Workforce Operations ---

    def save_specialist(self, specialist: RegisteredSpecialist) -> None:
        """Insert or update a registered specialist in the runtime database."""
        with self._conn:
            self._conn.execute(
                """
                INSERT INTO specialists (
                    worker_id, name, role, archetype, department,
                    capabilities_json, capability_gap_filled,
                    instructions, operating_boundaries, allowed_tools_json,
                    permission_tier, eligible_for_assignment, is_temporary, reusable,
                    lifecycle_state, runtime_status, current_task_id,
                    tasks_completed, tokens_used, recent_outputs_json,
                    proposal_id, deactivation_rule, mascot_profile_json,
                    created_at, updated_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(worker_id) DO UPDATE SET
                    name = excluded.name,
                    role = excluded.role,
                    archetype = excluded.archetype,
                    department = excluded.department,
                    capabilities_json = excluded.capabilities_json,
                    capability_gap_filled = excluded.capability_gap_filled,
                    instructions = excluded.instructions,
                    operating_boundaries = excluded.operating_boundaries,
                    allowed_tools_json = excluded.allowed_tools_json,
                    permission_tier = excluded.permission_tier,
                    eligible_for_assignment = excluded.eligible_for_assignment,
                    is_temporary = excluded.is_temporary,
                    reusable = excluded.reusable,
                    lifecycle_state = excluded.lifecycle_state,
                    runtime_status = excluded.runtime_status,
                    current_task_id = excluded.current_task_id,
                    tasks_completed = excluded.tasks_completed,
                    tokens_used = excluded.tokens_used,
                    recent_outputs_json = excluded.recent_outputs_json,
                    proposal_id = excluded.proposal_id,
                    deactivation_rule = excluded.deactivation_rule,
                    mascot_profile_json = excluded.mascot_profile_json,
                    updated_at = excluded.updated_at
                """,
                (
                    specialist.worker_id,
                    specialist.name,
                    specialist.role,
                    specialist.archetype,
                    specialist.department,
                    json.dumps(specialist.capabilities),
                    specialist.capability_gap_filled,
                    specialist.instructions,
                    specialist.operating_boundaries,
                    json.dumps(specialist.allowed_tools),
                    specialist.permission_tier.value,
                    1 if specialist.eligible_for_assignment else 0,
                    1 if specialist.is_temporary else 0,
                    1 if specialist.reusable else 0,
                    specialist.lifecycle_state,
                    specialist.runtime_status,
                    specialist.current_task_id,
                    specialist.tasks_completed,
                    specialist.tokens_used,
                    json.dumps(specialist.recent_outputs),
                    specialist.proposal_id,
                    specialist.deactivation_rule,
                    json.dumps(specialist.mascot_profile),
                    specialist.created_at,
                    specialist.updated_at,
                ),
            )

    def get_specialist(self, worker_id: str) -> Optional[RegisteredSpecialist]:
        """Fetch registered specialist by worker_id."""
        cursor = self._conn.execute(
            "SELECT * FROM specialists WHERE worker_id = ?",
            (worker_id,),
        )
        row = cursor.fetchone()
        if not row:
            return None
        return self._row_to_specialist(row)

    def get_specialist_by_name(self, name: str) -> Optional[RegisteredSpecialist]:
        """Fetch registered specialist by case-insensitive name."""
        cursor = self._conn.execute(
            "SELECT * FROM specialists WHERE LOWER(name) = LOWER(?)",
            (name,),
        )
        row = cursor.fetchone()
        if not row:
            return None
        return self._row_to_specialist(row)

    def list_specialists(self, lifecycle_state: Optional[str] = None) -> list[RegisteredSpecialist]:
        """List all registered specialists."""
        if lifecycle_state:
            cursor = self._conn.execute(
                "SELECT * FROM specialists WHERE lifecycle_state = ? ORDER BY created_at ASC",
                (lifecycle_state,),
            )
        else:
            cursor = self._conn.execute(
                "SELECT * FROM specialists ORDER BY created_at ASC"
            )
        return [self._row_to_specialist(row) for row in cursor.fetchall()]

    def _row_to_specialist(self, row: sqlite3.Row) -> RegisteredSpecialist:
        return RegisteredSpecialist(
            worker_id=row["worker_id"],
            name=row["name"],
            role=row["role"],
            archetype=row["archetype"],
            department=row["department"],
            capabilities=json.loads(row["capabilities_json"] or "[]"),
            capability_gap_filled=row["capability_gap_filled"],
            instructions=row["instructions"],
            operating_boundaries=row["operating_boundaries"],
            allowed_tools=json.loads(row["allowed_tools_json"] or "[]"),
            permission_tier=PermissionTier(row["permission_tier"]),
            eligible_for_assignment=bool(row["eligible_for_assignment"]),
            is_temporary=bool(row["is_temporary"]),
            reusable=bool(row["reusable"]),
            lifecycle_state=row["lifecycle_state"],
            runtime_status=row["runtime_status"],
            current_task_id=row["current_task_id"],
            tasks_completed=int(row["tasks_completed"]),
            tokens_used=int(row["tokens_used"]),
            recent_outputs=json.loads(row["recent_outputs_json"] or "[]"),
            proposal_id=row["proposal_id"],
            deactivation_rule=row["deactivation_rule"],
            mascot_profile=json.loads(row["mascot_profile_json"] or "{}"),
            created_at=row["created_at"],
            updated_at=row["updated_at"],
        )

    # --- Company Project Operations ---

    def save_project(self, project: CompanyProject) -> None:
        """Insert or update a persistent company project record."""
        with self._conn:
            self._conn.execute(
                """
                INSERT INTO projects (
                    project_id, name, slug, project_type, priority,
                    objective, domain, status, current_stage,
                    lead_specialist, workspace_path, epics_json,
                    capability_assessment_json, acceptance_criteria_json,
                    artifacts_json, approvals_json, spend_usd,
                    created_at, updated_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(project_id) DO UPDATE SET
                    name = excluded.name,
                    slug = excluded.slug,
                    project_type = excluded.project_type,
                    priority = excluded.priority,
                    objective = excluded.objective,
                    domain = excluded.domain,
                    status = excluded.status,
                    current_stage = excluded.current_stage,
                    lead_specialist = excluded.lead_specialist,
                    workspace_path = excluded.workspace_path,
                    epics_json = excluded.epics_json,
                    capability_assessment_json = excluded.capability_assessment_json,
                    acceptance_criteria_json = excluded.acceptance_criteria_json,
                    artifacts_json = excluded.artifacts_json,
                    approvals_json = excluded.approvals_json,
                    spend_usd = excluded.spend_usd,
                    updated_at = excluded.updated_at
                """,
                (
                    project.project_id,
                    project.name,
                    project.slug,
                    project.project_type,
                    project.priority,
                    project.objective,
                    project.domain,
                    project.status,
                    project.current_stage,
                    project.lead_specialist,
                    project.workspace_path,
                    json.dumps(project.epics),
                    json.dumps(project.capability_assessment),
                    json.dumps(project.acceptance_criteria),
                    json.dumps(project.artifacts),
                    json.dumps(project.approvals),
                    project.spend_usd,
                    project.created_at,
                    project.updated_at,
                ),
            )

    def get_project(self, project_id: str) -> Optional[CompanyProject]:
        """Fetch project by ID."""
        cursor = self._conn.execute(
            "SELECT * FROM projects WHERE project_id = ?",
            (project_id,),
        )
        row = cursor.fetchone()
        if not row:
            return None
        return self._row_to_project(row)

    def list_projects(self, project_type: Optional[str] = None) -> list[CompanyProject]:
        """List persistent projects."""
        if project_type:
            cursor = self._conn.execute(
                "SELECT * FROM projects WHERE project_type = ? ORDER BY created_at DESC",
                (project_type,),
            )
        else:
            cursor = self._conn.execute(
                "SELECT * FROM projects ORDER BY created_at DESC"
            )
        return [self._row_to_project(row) for row in cursor.fetchall()]

    def _row_to_project(self, row: sqlite3.Row) -> CompanyProject:
        return CompanyProject(
            project_id=row["project_id"],
            name=row["name"],
            slug=row["slug"],
            project_type=row["project_type"],
            priority=row["priority"],
            objective=row["objective"],
            domain=row["domain"],
            status=row["status"],
            current_stage=row["current_stage"],
            lead_specialist=row["lead_specialist"],
            workspace_path=row["workspace_path"],
            epics=json.loads(row["epics_json"] or "[]"),
            capability_assessment=json.loads(row["capability_assessment_json"] or "{}"),
            acceptance_criteria=json.loads(row["acceptance_criteria_json"] or "[]"),
            artifacts=json.loads(row["artifacts_json"] or "[]"),
            approvals=json.loads(row["approvals_json"] or "[]"),
            spend_usd=float(row["spend_usd"]),
            created_at=row["created_at"],
            updated_at=row["updated_at"],
        )

