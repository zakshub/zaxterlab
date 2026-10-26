"""Independent Auditor (Zaks - Vision) Engine for Dual-Worker Verification."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Optional

from zaxterlab.contracts.types import (
    AgentDefinition,
    AuditDecision,
    PermissionTier,
    Session,
    Task,
    TokenUsage,
    utc_now_iso,
)
from zaxterlab.db.sqlite import SQLiteStore
from zaxterlab.models.base import CompletionRequest, CompletionResponse, ModelProvider
from zaxterlab.security.guard import BoundaryGuard, SpendViolationError
from zaxterlab.tools.registry import ToolRegistry


def get_default_auditor_definition() -> AgentDefinition:
    """Return canonical specification for the second worker: Zaks (Independent Audit & Oversight)."""
    return AgentDefinition(
        agent_id="zaks-auditor",
        name="Zaks",
        role="Independent Audit and Oversight",
        description="Impartial auditor validating task outputs, safety boundaries, test coverage, and constitution compliance.",
        allowed_tools=["read_file", "list_dir"],
        max_iterations=5,
        permission_tier=PermissionTier.TIER_1_SAFE,
    )


class AuditorEngine:
    """Engine for the second worker (Zaks) performing independent quality control and audit."""

    def __init__(
        self,
        agent: Optional[AgentDefinition] = None,
        model: Optional[ModelProvider] = None,
        boundary_guard: Optional[BoundaryGuard] = None,
        store: Optional[SQLiteStore] = None,
        tool_registry: Optional[ToolRegistry] = None,
    ) -> None:
        self.agent = agent or get_default_auditor_definition()
        self.boundary_guard = boundary_guard
        self.store = store
        self.tool_registry = tool_registry
        self.model = model

    def audit_session(self, task: Task, session: Session) -> AuditDecision:
        """Perform an objective audit of Worker 1's execution session and artifacts."""
        findings: list[str] = []
        review_tokens = TokenUsage(prompt_tokens=15, completion_tokens=20, total_tokens=35, estimated_cost_usd=0.0)

        # 1. Forensic Step Trace Inspection
        if not session.step_traces:
            return AuditDecision(
                approved=False,
                feedback="Audit Rejected: No step traces recorded in session.",
                findings=["Empty execution session"],
                token_usage=review_tokens,
            )

        # 2. Check for unresolved tool execution errors
        for trace in session.step_traces:
            for tr in trace.tool_results:
                if not tr.success:
                    findings.append(f"Tool error in step {trace.step_number} ({tr.tool_name}): {tr.error}")

        # 3. Grounded Artifact Verification (Anti-Hallucination Check)
        # Scan tool calls for written files and verify they genuinely exist on disk
        if self.boundary_guard:
            workspace_root = self.boundary_guard.workspace.workspace_root
            for trace in session.step_traces:
                for tc in trace.tool_calls:
                    if tc.tool_name == "write_file":
                        target_rel = tc.arguments.get("path")
                        if target_rel:
                            try:
                                resolved_path = self.boundary_guard.workspace.resolve_safe_path(target_rel)
                                if not resolved_path.exists():
                                    findings.append(
                                        f"Hallucination detected: Worker claimed to write '{target_rel}', but file does not exist on disk."
                                    )
                                elif resolved_path.stat().st_size == 0:
                                    findings.append(f"Suspicious artifact: File '{target_rel}' exists but is 0 bytes.")
                            except Exception as e:
                                findings.append(f"Workspace path verification error for '{target_rel}': {e}")

        # 4. Model Provider Audit Reasoning (if model is supplied)
        if self.model:
            audit_prompt = (
                f"Audit Review Request for Task '{task.title}' (ID: {task.task_id}).\n"
                f"Description: {task.description}\n"
                f"Result Claimed: {task.result_summary}\n"
                f"Number of Steps: {len(session.step_traces)}\n"
                f"Preliminary Forensic Findings: {findings}\n"
                "Evaluate whether the work satisfies acceptance criteria and should be APPROVED or REJECTED."
            )

            req = CompletionRequest(
                system_prompt=(
                    f"You are {self.agent.name}, {self.agent.role}. "
                    "You are an impartial constitutional auditor. Be rigorous, verify evidence, and reject hallucinated or incomplete work."
                ),
                prompt=audit_prompt,
                tools=[],
            )

            # Spend check
            if self.boundary_guard:
                self.boundary_guard.spend.validate_cost(self.model.get_cost_estimate(req))

            response: CompletionResponse = self.model.complete(req)
            review_tokens = review_tokens.add(response.token_usage)

            # If model explicitly indicates rejection or if forensic findings exist
            if "REJECT" in response.text.upper() or findings:
                approved = False
                feedback = response.text if "REJECT" in response.text.upper() else f"Rejected by Auditor: {'; '.join(findings)}"
            else:
                approved = True
                feedback = response.text or "Approved by independent audit."
        else:
            # Deterministic rule-based audit fallback
            if findings:
                approved = False
                feedback = f"Rejected by Auditor: {'; '.join(findings)}"
            else:
                approved = True
                feedback = "Approved: All step traces verified, tool executions succeeded, and artifacts verified on disk."

        decision = AuditDecision(
            approved=approved,
            feedback=feedback,
            findings=findings,
            token_usage=review_tokens,
            audited_at=utc_now_iso(),
        )

        # Log audit trail if store is present
        if self.store:
            self.store.log_audit(
                "TASK_AUDITED",
                task.task_id,
                {
                    "auditor": self.agent.agent_id,
                    "approved": decision.approved,
                    "feedback": decision.feedback,
                    "findings_count": len(decision.findings),
                    "review_tokens": review_tokens.total_tokens,
                },
            )

        return decision
