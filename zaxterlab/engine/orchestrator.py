"""Multi-Worker Task Orchestrator with DAG dependencies, retries, and specialist routing."""

from __future__ import annotations

import collections
from typing import Any, Callable, Optional

from zaxterlab.contracts.types import (
    AgentDefinition,
    PermissionTier,
    ProposalStatus,
    Session,
    Task,
    TaskStatus,
    utc_now_iso,
)
from zaxterlab.db.sqlite import SQLiteStore
from zaxterlab.engine.worker import Worker1Engine
from zaxterlab.models.base import CompletionRequest, CompletionResponse, ModelProvider
from zaxterlab.security.guard import BoundaryGuard
from zaxterlab.tools.registry import ToolRegistry


class CyclicDependencyError(Exception):
    """Raised when task dependency graph contains a cycle."""

    pass


class MultiWorkerOrchestrator:
    """Coordinates multi-worker execution graphs, dependency ordering, retries, and reviews."""

    def __init__(
        self,
        store: SQLiteStore,
        worker_engine: Worker1Engine,
        boundary_guard: BoundaryGuard,
        model_provider: ModelProvider,
    ) -> None:
        self.store = store
        self.worker_engine = worker_engine
        self.boundary_guard = boundary_guard
        self.model_provider = model_provider
        self.active_specialists: dict[str, AgentDefinition] = {}
        self._refresh_active_specialists()

    def _refresh_active_specialists(self) -> None:
        """Load all owner-approved specialists from database."""
        approved_proposals = self.store.list_proposals(status=ProposalStatus.APPROVED)
        for p in approved_proposals:
            agent = AgentDefinition(
                agent_id=f"{p.target_role_name.lower()}-specialist",
                name=p.target_role_name,
                role=p.target_role_title,
                description=f"Specialist activated via proposal {p.proposal_id}",
                allowed_tools=list(p.recommended_tools),
                max_iterations=10,
                permission_tier=p.recommended_permission_tier,
            )
            self.active_specialists[p.target_role_name.lower()] = agent

    def validate_dag(self, tasks: list[Task]) -> list[str]:
        """Validate acyclic dependency graph and return topological execution order."""
        task_map = {t.task_id: t for t in tasks}
        in_degree: dict[str, int] = {t.task_id: 0 for t in tasks}
        adjacency: dict[str, list[str]] = collections.defaultdict(list)

        for t in tasks:
            for dep_id in t.depends_on:
                if dep_id in task_map:
                    adjacency[dep_id].append(t.task_id)
                    in_degree[t.task_id] += 1

        # Kahn's algorithm
        queue = collections.deque([t_id for t_id, deg in in_degree.items() if deg == 0])
        topological_order: list[str] = []

        while queue:
            curr = queue.popleft()
            topological_order.append(curr)
            for neighbor in adjacency[curr]:
                in_degree[neighbor] -= 1
                if in_degree[neighbor] == 0:
                    queue.append(neighbor)

        if len(topological_order) != len(tasks):
            raise CyclicDependencyError(
                f"Cyclic dependency detected among tasks. Resolved only {len(topological_order)} of {len(tasks)} tasks."
            )

        return topological_order

    def can_task_execute(self, task: Task) -> tuple[bool, Optional[str]]:
        """Check if all upstream dependencies are satisfied."""
        if not task.depends_on:
            return True, None

        for dep_id in task.depends_on:
            parent = self.store.get_task(dep_id)
            if not parent:
                return False, f"Missing dependency task: {dep_id}"
            if parent.status in (
                TaskStatus.FAILED,
                TaskStatus.BLOCKED,
                TaskStatus.BLOCKED_BY_UPSTREAM,
            ):
                return False, f"Upstream dependency '{dep_id}' is {parent.status.value}"
            if parent.status != TaskStatus.COMPLETED:
                return False, f"Upstream dependency '{dep_id}' is not yet completed (current: {parent.status.value})"

        return True, None

    def execute_task(self, task: Task) -> Task:
        """Route and execute a single task with failure handling, review, and retries."""
        self._refresh_active_specialists()

        # 1. Check dependency readiness
        can_run, reason = self.can_task_execute(task)
        if not can_run:
            if "is FAILED" in (reason or "") or "is BLOCKED" in (reason or ""):
                task.status = TaskStatus.BLOCKED_BY_UPSTREAM
                task.error_message = reason
                self.store.save_task(task)
                self.store.log_audit(
                    event_type="TASK_BLOCKED_BY_UPSTREAM",
                    entity_id=task.task_id,
                    details={"reason": reason},
                )
                return task
            else:
                # Still waiting on running parent
                task.status = TaskStatus.QUEUED
                self.store.save_task(task)
                return task

        # 2. Specialist Routing
        specialist_name = (task.assigned_specialist or "").lower()
        active_agent = self.active_specialists.get(specialist_name)

        if active_agent:
            # Route to dedicated specialist agent
            task.assigned_agent_id = active_agent.agent_id
            tools = ToolRegistry(self.boundary_guard)
            engine = Worker1Engine(
                agent=active_agent,
                model=self.model_provider,
                boundary_guard=self.boundary_guard,
                store=self.store,
                tool_registry=tools,
                auditor=self.worker_engine.auditor,
            )
        else:
            # Fallback to default Worker 1 (Reem)
            task.assigned_agent_id = self.worker_engine.agent.agent_id
            engine = self.worker_engine

        # 3. Execution attempt
        session = engine.execute_task(task)
        updated_task = self.store.get_task(task.task_id) or task

        # 4. Failure handling and retry logic
        if updated_task.status in (TaskStatus.FAILED, TaskStatus.REJECTED, TaskStatus.BLOCKED):
            if updated_task.retry_count < updated_task.max_retries:
                updated_task.retry_count += 1
                updated_task.status = TaskStatus.QUEUED
                updated_task.input_context["last_failure_feedback"] = (
                    updated_task.result_summary or updated_task.error_message or "Execution or audit verification failed. Retrying."
                )
                self.store.save_task(updated_task)
                self.store.log_audit(
                    event_type="TASK_RETRY_DISPATCHED",
                    entity_id=updated_task.task_id,
                    details={
                        "attempt": updated_task.retry_count,
                        "max_retries": updated_task.max_retries,
                    },
                )
                # Re-execute retry
                return self.execute_task(updated_task)
            else:
                updated_task.status = TaskStatus.BLOCKED
                updated_task.error_message = (
                    f"Max retries ({updated_task.max_retries}) exceeded without passing verification."
                )
                self.store.save_task(updated_task)
                self.store.log_audit(
                    event_type="TASK_FAILED_MAX_RETRIES_EXCEEDED",
                    entity_id=updated_task.task_id,
                    details={"retries": updated_task.retry_count},
                )

        return updated_task

    def run_pipeline(self, task_ids: list[str]) -> dict[str, Any]:
        """Execute a graph of tasks until completion or terminal blockage."""
        tasks = [self.store.get_task(t_id) for t_id in task_ids]
        present_tasks = [t for t in tasks if t is not None]

        if not present_tasks:
            return {"total": 0, "completed": 0, "failed": 0, "blocked": 0, "tasks": []}

        order = self.validate_dag(present_tasks)
        executed_tasks: list[dict[str, Any]] = []

        for task_id in order:
            task = self.store.get_task(task_id)
            if not task:
                continue

            result = self.execute_task(task)
            executed_tasks.append(result.to_dict())

        completed = sum(1 for t in executed_tasks if t["status"] == TaskStatus.COMPLETED.value)
        failed = sum(1 for t in executed_tasks if t["status"] == TaskStatus.FAILED.value)
        blocked = sum(
            1
            for t in executed_tasks
            if t["status"] in (TaskStatus.BLOCKED.value, TaskStatus.BLOCKED_BY_UPSTREAM.value)
        )

        return {
            "total": len(executed_tasks),
            "completed": completed,
            "failed": failed,
            "blocked": blocked,
            "execution_order": order,
            "tasks": executed_tasks,
        }
