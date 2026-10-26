"""Worker 1 execution engine: Read -> Plan -> Tool Call -> Evaluate -> Log."""

from __future__ import annotations

import uuid
from typing import Any, Optional

from zaxterlab.contracts.types import (
    AgentDefinition,
    PermissionTier,
    Session,
    SessionStatus,
    StepTrace,
    Task,
    TaskStatus,
    TokenUsage,
    ToolCall,
    ToolResult,
    utc_now_iso,
)
from zaxterlab.db.sqlite import SQLiteStore
from zaxterlab.models.base import CompletionRequest, CompletionResponse, ModelProvider
from zaxterlab.security.guard import (
    BoundaryGuard,
    PermissionDeniedError,
    SecurityViolationError,
    SpendViolationError,
)
from zaxterlab.tools.registry import ToolRegistry


def get_default_worker1_definition() -> AgentDefinition:
    """Return canonical Worker 1 (Reem - Construction & Programming) specification."""
    return AgentDefinition(
        agent_id="reem-worker-1",
        name="Reem",
        role="Construction and Programming",
        description="First autonomous generalist worker handling code, file inspection, and tests.",
        allowed_tools=["read_file", "write_file", "list_dir", "run_command"],
        max_iterations=10,
        permission_tier=PermissionTier.TIER_2_REVERSIBLE,
    )


class Worker1Engine:
    """Single-worker execution loop implementing the strict 5-stage cycle:
    Read -> Plan -> Tool Call -> Evaluate -> Log.
    """

    def __init__(
        self,
        agent: AgentDefinition,
        model: ModelProvider,
        boundary_guard: BoundaryGuard,
        store: SQLiteStore,
        tool_registry: ToolRegistry,
    ) -> None:
        self.agent = agent
        self.model = model
        self.boundary_guard = boundary_guard
        self.store = store
        self.tool_registry = tool_registry

    def execute_task(
        self,
        task: Task,
        resume_session_id: Optional[str] = None,
        max_steps_per_run: Optional[int] = None,
    ) -> Session:
        """Run or resume an execution session for a task."""
        # 1. Initialize or resume session
        if resume_session_id:
            session = self.store.get_session(resume_session_id)
            if not session:
                raise ValueError(f"Session '{resume_session_id}' not found for resumption.")
            if session.task_id != task.task_id:
                raise ValueError(f"Session '{resume_session_id}' does not match task '{task.task_id}'.")
            if session.status != SessionStatus.SUSPENDED:
                raise ValueError(
                    f"Cannot resume session '{resume_session_id}' with status '{session.status.value}'. "
                    "Only SUSPENDED sessions can be resumed."
                )
            session.status = SessionStatus.ACTIVE
            session.updated_at = utc_now_iso()
            self.store.log_audit("SESSION_RESUMED", session.session_id, {"step": session.current_step})
        else:
            session_id = f"sess_{task.task_id}_{uuid.uuid4().hex[:8]}"
            session = Session(
                session_id=session_id,
                task_id=task.task_id,
                agent_id=self.agent.agent_id,
                status=SessionStatus.ACTIVE,
                current_step=0,
                state_data={"task_title": task.title},
                step_traces=[],
                total_token_usage=TokenUsage(),
            )
            self.store.log_audit("SESSION_CREATED", session.session_id, {"agent": self.agent.agent_id})

        task.status = TaskStatus.RUNNING
        task.assigned_agent_id = self.agent.agent_id
        task.updated_at = utc_now_iso()
        self.store.save_task(task)
        self.store.save_session(session)

        steps_executed_this_run = 0
        limit = max_steps_per_run or self.agent.max_iterations

        # 2. Main Execution Loop
        while session.current_step < self.agent.max_iterations and steps_executed_this_run < limit:
            step_num = session.current_step + 1

            # --- STAGE 1: READ ---
            observation = self._stage_read(task, session)

            # --- STAGE 2: PLAN ---
            try:
                plan_text, tool_calls, is_final, response_text, evaluation_text, step_usage = (
                    self._stage_plan(task, session, observation)
                )
            except SpendViolationError as spend_err:
                # Halt immediately on spend violation
                session.status = SessionStatus.FAILED
                task.status = TaskStatus.BLOCKED
                task.result_summary = f"Blocked by SpendGuard: {spend_err}"
                self.store.log_audit("SPEND_VIOLATION_HALT", task.task_id, {"error": str(spend_err)})
                self.store.save_task(task)
                self.store.save_session(session)
                raise

            # --- STAGE 3: TOOL CALL ---
            tool_results = self._stage_tool_call(tool_calls)

            # --- STAGE 4: EVALUATE ---
            eval_outcome, should_complete, should_fail = self._stage_evaluate(
                task, session, is_final, tool_results, evaluation_text
            )

            # --- STAGE 5: LOG ---
            trace = StepTrace(
                step_number=step_num,
                phase="CYCLE",
                observation=observation,
                plan=plan_text,
                tool_calls=tool_calls,
                tool_results=tool_results,
                evaluation=eval_outcome,
                token_usage=step_usage,
                created_at=utc_now_iso(),
            )

            session.step_traces.append(trace)
            session.current_step = step_num
            session.total_token_usage = session.total_token_usage.add(step_usage)
            session.updated_at = utc_now_iso()
            steps_executed_this_run += 1

            self.store.save_session(session)
            self.store.log_audit(
                "STEP_EXECUTED",
                session.session_id,
                {"step": step_num, "tools_called": len(tool_calls), "outcome": eval_outcome},
            )

            if should_complete:
                session.status = SessionStatus.COMPLETED
                task.status = TaskStatus.COMPLETED
                task.result_summary = response_text or eval_outcome
                task.updated_at = utc_now_iso()
                self.store.save_task(task)
                self.store.save_session(session)
                self.store.log_audit("TASK_COMPLETED", task.task_id, {"session_id": session.session_id})
                break

            if should_fail:
                session.status = SessionStatus.FAILED
                task.status = TaskStatus.FAILED
                task.result_summary = f"Failed at step {step_num}: {eval_outcome}"
                task.updated_at = utc_now_iso()
                self.store.save_task(task)
                self.store.save_session(session)
                self.store.log_audit("TASK_FAILED", task.task_id, {"session_id": session.session_id})
                break

        # Check if iteration limit reached without completion or suspension
        if session.status == SessionStatus.ACTIVE and session.current_step >= self.agent.max_iterations:
            session.status = SessionStatus.FAILED
            task.status = TaskStatus.FAILED
            task.result_summary = f"Exceeded maximum allowed iterations ({self.agent.max_iterations})."
            self.store.save_task(task)
            self.store.save_session(session)

        return session

    def suspend_session(self, task: Task, session: Session) -> Session:
        """Suspend an active session, persisting state and freeing runtime resources."""
        session.status = SessionStatus.SUSPENDED
        session.updated_at = utc_now_iso()
        task.status = TaskStatus.SUSPENDED
        task.updated_at = utc_now_iso()

        self.store.save_task(task)
        self.store.save_session(session)
        self.store.log_audit("SESSION_SUSPENDED", session.session_id, {"step": session.current_step})
        return session

    def terminate_session(self, task: Task, session: Session, reason: str = "User initiated termination") -> Session:
        """Explicitly terminate an active or suspended session, transitioning to FAILED/BLOCKED."""
        session.status = SessionStatus.FAILED
        session.updated_at = utc_now_iso()
        task.status = TaskStatus.BLOCKED
        task.result_summary = f"Terminated: {reason}"
        task.updated_at = utc_now_iso()

        self.store.save_task(task)
        self.store.save_session(session)
        self.store.log_audit(
            "SESSION_TERMINATED",
            session.session_id,
            {"task_id": task.task_id, "step": session.current_step, "reason": reason},
        )
        return session

    # --- Private Stage Implementations ---

    def _stage_read(self, task: Task, session: Session) -> str:
        """Read context: task parameters, recent step traces, and session state."""
        recent_context = []
        if session.step_traces:
            last_trace = session.step_traces[-1]
            recent_context.append(f"Previous Step ({last_trace.step_number}) Plan: {last_trace.plan}")
            recent_context.append(f"Previous Evaluation: {last_trace.evaluation}")
            if last_trace.tool_results:
                recent_context.append(
                    f"Previous Tool Results: {[r.output or r.error for r in last_trace.tool_results]}"
                )

        history_str = " | ".join(recent_context) if recent_context else "Initial execution cycle."
        return (
            f"Task: {task.title} (ID: {task.task_id}). "
            f"Description: {task.description}. "
            f"Inputs: {task.input_context}. "
            f"History: {history_str}"
        )

    def _stage_plan(
        self,
        task: Task,
        session: Session,
        observation: str,
    ) -> tuple[str, list[ToolCall], bool, str, Optional[str], TokenUsage]:
        """Formulate plan and query model provider while enforcing spend boundary."""
        tools_spec = [
            {"name": tool_name}
            for tool_name in self.agent.allowed_tools
        ]

        request = CompletionRequest(
            system_prompt=(
                f"You are {self.agent.name}, {self.agent.role}. "
                f"{self.agent.description} "
                f"Allowed tools: {self.agent.allowed_tools}. "
                "Execute the task methodically following Read -> Plan -> Tool Call -> Evaluate -> Log."
            ),
            prompt=observation,
            tools=tools_spec,
            context={"session_id": session.session_id, "step": session.current_step + 1},
        )

        # SpendGuard pre-flight validation
        estimated_cost = self.model.get_cost_estimate(request)
        self.boundary_guard.spend.validate_cost(estimated_cost)

        # Model completion
        response: CompletionResponse = self.model.complete(request)

        # SpendGuard post-execution record
        actual_cost = response.token_usage.estimated_cost_usd
        self.boundary_guard.spend.record_cost(actual_cost)

        plan_text = response.plan or f"Step {session.current_step + 1} plan"
        return (
            plan_text,
            response.tool_calls,
            response.is_final,
            response.text,
            response.evaluation,
            response.token_usage,
        )

    def _stage_tool_call(self, tool_calls: list[ToolCall]) -> list[ToolResult]:
        """Execute model-requested tool calls within strict permission boundaries."""
        results: list[ToolResult] = []
        for tc in tool_calls:
            try:
                # 1. Validate agent permission for tool
                self.boundary_guard.validate_tool_access(self.agent, tc.tool_name)
                # 2. Execute via registry
                result = self.tool_registry.execute(tc)
                results.append(result)
            except PermissionDeniedError as perm_err:
                results.append(
                    ToolResult(
                        call_id=tc.call_id,
                        tool_name=tc.tool_name,
                        success=False,
                        output="",
                        error=f"Permission Denied: {perm_err}",
                    )
                )
            except SecurityViolationError as sec_err:
                results.append(
                    ToolResult(
                        call_id=tc.call_id,
                        tool_name=tc.tool_name,
                        success=False,
                        output="",
                        error=f"Security Violation: {sec_err}",
                    )
                )

        return results

    def _stage_evaluate(
        self,
        task: Task,
        session: Session,
        is_final: bool,
        tool_results: list[ToolResult],
        evaluation_text: Optional[str],
    ) -> tuple[str, bool, bool]:
        """Evaluate step outcome, deciding whether to complete, continue, or fail."""
        # Check for tool errors
        has_tool_errors = any(not r.success for r in tool_results)

        if has_tool_errors:
            error_details = [r.error for r in tool_results if not r.success]
            eval_str = f"Tool errors encountered: {'; '.join(filter(None, error_details))}"
            # If all tools failed and model claimed final, fail
            if is_final:
                return eval_str, False, True
            return eval_str, False, False

        if is_final:
            eval_str = evaluation_text or "Task requirements satisfied."
            return eval_str, True, False

        eval_str = evaluation_text or f"Step {session.current_step + 1} completed successfully. Continuing."
        return eval_str, False, False
