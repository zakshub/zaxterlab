"""Core domain data contracts for ZaxterLab."""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Optional


def utc_now_iso() -> str:
    """Return current UTC timestamp in ISO 8601 format."""
    return datetime.now(timezone.utc).isoformat()


class TaskStatus(str, Enum):
    """Lifecycle states for a task."""

    SUBMITTED = "SUBMITTED"
    QUEUED = "QUEUED"
    RUNNING = "RUNNING"
    REVIEW = "REVIEW"
    REJECTED = "REJECTED"
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"
    SUSPENDED = "SUSPENDED"
    BLOCKED = "BLOCKED"


class SessionStatus(str, Enum):
    """Lifecycle states for an execution session."""

    CREATED = "CREATED"
    ACTIVE = "ACTIVE"
    SUSPENDED = "SUSPENDED"
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"


class PermissionTier(str, Enum):
    """Security permission tiers."""

    TIER_1_SAFE = "TIER_1_SAFE"
    TIER_2_REVERSIBLE = "TIER_2_REVERSIBLE"
    TIER_3_CONSEQUENTIAL = "TIER_3_CONSEQUENTIAL"


@dataclass
class TokenUsage:
    """Token consumption and financial accounting."""

    prompt_tokens: int = 0
    completion_tokens: int = 0
    total_tokens: int = 0
    estimated_cost_usd: float = 0.0

    def add(self, other: TokenUsage) -> TokenUsage:
        """Accumulate token usage and cost."""
        return TokenUsage(
            prompt_tokens=self.prompt_tokens + other.prompt_tokens,
            completion_tokens=self.completion_tokens + other.completion_tokens,
            total_tokens=self.total_tokens + other.total_tokens,
            estimated_cost_usd=round(self.estimated_cost_usd + other.estimated_cost_usd, 6),
        )

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> TokenUsage:
        return cls(
            prompt_tokens=int(data.get("prompt_tokens", 0)),
            completion_tokens=int(data.get("completion_tokens", 0)),
            total_tokens=int(data.get("total_tokens", 0)),
            estimated_cost_usd=float(data.get("estimated_cost_usd", 0.0)),
        )


@dataclass
class ToolCall:
    """A tool invocation requested by the reasoning engine."""

    call_id: str
    tool_name: str
    arguments: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> ToolCall:
        return cls(
            call_id=str(data.get("call_id", "")),
            tool_name=str(data.get("tool_name", "")),
            arguments=dict(data.get("arguments", {})),
        )


@dataclass
class ToolResult:
    """The outcome of an executed tool call."""

    call_id: str
    tool_name: str
    success: bool
    output: str
    error: Optional[str] = None

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> ToolResult:
        return cls(
            call_id=str(data.get("call_id", "")),
            tool_name=str(data.get("tool_name", "")),
            success=bool(data.get("success", False)),
            output=str(data.get("output", "")),
            error=data.get("error"),
        )


@dataclass
class AuditDecision:
    """Structured decision returned by the independent Auditor (Zaks)."""

    approved: bool
    feedback: str
    findings: list[str] = field(default_factory=list)
    token_usage: TokenUsage = field(default_factory=TokenUsage)
    audited_at: str = field(default_factory=utc_now_iso)

    def to_dict(self) -> dict[str, Any]:
        return {
            "approved": self.approved,
            "feedback": self.feedback,
            "findings": list(self.findings),
            "token_usage": self.token_usage.to_dict(),
            "audited_at": self.audited_at,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> AuditDecision:
        return cls(
            approved=bool(data.get("approved", False)),
            feedback=str(data.get("feedback", "")),
            findings=list(data.get("findings", [])),
            token_usage=TokenUsage.from_dict(data.get("token_usage", {})),
            audited_at=str(data.get("audited_at", utc_now_iso())),
        )


@dataclass
class StepTrace:
    """A single trace entry representing an execution cycle step."""

    step_number: int
    phase: str  # READ, PLAN, TOOL_CALL, EVALUATE, LOG
    observation: str
    plan: Optional[str] = None
    tool_calls: list[ToolCall] = field(default_factory=list)
    tool_results: list[ToolResult] = field(default_factory=list)
    evaluation: Optional[str] = None
    token_usage: TokenUsage = field(default_factory=TokenUsage)
    created_at: str = field(default_factory=utc_now_iso)

    def to_dict(self) -> dict[str, Any]:
        return {
            "step_number": self.step_number,
            "phase": self.phase,
            "observation": self.observation,
            "plan": self.plan,
            "tool_calls": [tc.to_dict() for tc in self.tool_calls],
            "tool_results": [tr.to_dict() for tr in self.tool_results],
            "evaluation": self.evaluation,
            "token_usage": self.token_usage.to_dict(),
            "created_at": self.created_at,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> StepTrace:
        return cls(
            step_number=int(data.get("step_number", 0)),
            phase=str(data.get("phase", "UNKNOWN")),
            observation=str(data.get("observation", "")),
            plan=data.get("plan"),
            tool_calls=[ToolCall.from_dict(tc) for tc in data.get("tool_calls", [])],
            tool_results=[ToolResult.from_dict(tr) for tr in data.get("tool_results", [])],
            evaluation=data.get("evaluation"),
            token_usage=TokenUsage.from_dict(data.get("token_usage", {})),
            created_at=str(data.get("created_at", utc_now_iso())),
        )


@dataclass
class AgentDefinition:
    """Declarative specification defining an agent's boundaries and capabilities."""

    agent_id: str
    name: str
    role: str
    description: str
    allowed_tools: list[str] = field(default_factory=list)
    max_iterations: int = 10
    permission_tier: PermissionTier = PermissionTier.TIER_2_REVERSIBLE

    def to_dict(self) -> dict[str, Any]:
        return {
            "agent_id": self.agent_id,
            "name": self.name,
            "role": self.role,
            "description": self.description,
            "allowed_tools": list(self.allowed_tools),
            "max_iterations": self.max_iterations,
            "permission_tier": self.permission_tier.value,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> AgentDefinition:
        tier_val = data.get("permission_tier", PermissionTier.TIER_2_REVERSIBLE.value)
        return cls(
            agent_id=str(data.get("agent_id", "")),
            name=str(data.get("name", "")),
            role=str(data.get("role", "")),
            description=str(data.get("description", "")),
            allowed_tools=list(data.get("allowed_tools", [])),
            max_iterations=int(data.get("max_iterations", 10)),
            permission_tier=PermissionTier(tier_val),
        )


@dataclass
class Task:
    """Unit of work managed by ZaxterLab."""

    task_id: str
    title: str
    description: str
    status: TaskStatus = TaskStatus.SUBMITTED
    assigned_agent_id: Optional[str] = None
    input_context: dict[str, Any] = field(default_factory=dict)
    result_summary: Optional[str] = None
    created_at: str = field(default_factory=utc_now_iso)
    updated_at: str = field(default_factory=utc_now_iso)

    def to_dict(self) -> dict[str, Any]:
        return {
            "task_id": self.task_id,
            "title": self.title,
            "description": self.description,
            "status": self.status.value,
            "assigned_agent_id": self.assigned_agent_id,
            "input_context": dict(self.input_context),
            "result_summary": self.result_summary,
            "created_at": self.created_at,
            "updated_at": self.updated_at,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> Task:
        return cls(
            task_id=str(data.get("task_id", "")),
            title=str(data.get("title", "")),
            description=str(data.get("description", "")),
            status=TaskStatus(data.get("status", TaskStatus.SUBMITTED.value)),
            assigned_agent_id=data.get("assigned_agent_id"),
            input_context=dict(data.get("input_context", {})),
            result_summary=data.get("result_summary"),
            created_at=str(data.get("created_at", utc_now_iso())),
            updated_at=str(data.get("updated_at", utc_now_iso())),
        )


@dataclass
class Session:
    """An active or serialized execution session for a task."""

    session_id: str
    task_id: str
    agent_id: str
    status: SessionStatus = SessionStatus.CREATED
    current_step: int = 0
    state_data: dict[str, Any] = field(default_factory=dict)
    step_traces: list[StepTrace] = field(default_factory=list)
    total_token_usage: TokenUsage = field(default_factory=TokenUsage)
    created_at: str = field(default_factory=utc_now_iso)
    updated_at: str = field(default_factory=utc_now_iso)

    def to_dict(self) -> dict[str, Any]:
        return {
            "session_id": self.session_id,
            "task_id": self.task_id,
            "agent_id": self.agent_id,
            "status": self.status.value,
            "current_step": self.current_step,
            "state_data": dict(self.state_data),
            "step_traces": [st.to_dict() for st in self.step_traces],
            "total_token_usage": self.total_token_usage.to_dict(),
            "created_at": self.created_at,
            "updated_at": self.updated_at,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> Session:
        return cls(
            session_id=str(data.get("session_id", "")),
            task_id=str(data.get("task_id", "")),
            agent_id=str(data.get("agent_id", "")),
            status=SessionStatus(data.get("status", SessionStatus.CREATED.value)),
            current_step=int(data.get("current_step", 0)),
            state_data=dict(data.get("state_data", {})),
            step_traces=[StepTrace.from_dict(st) for st in data.get("step_traces", [])],
            total_token_usage=TokenUsage.from_dict(data.get("total_token_usage", {})),
            created_at=str(data.get("created_at", utc_now_iso())),
            updated_at=str(data.get("updated_at", utc_now_iso())),
        )


class TradeoffChoice(str, Enum):
    """3-Way Trade-off decision for workload pressure."""

    PROMPT_TOOL_REFINEMENT = "PROMPT_TOOL_REFINEMENT"
    REUSE_EXISTING_WORKER = "REUSE_EXISTING_WORKER"
    PROPOSE_SPECIALIST = "PROPOSE_SPECIALIST"


class ProposalStatus(str, Enum):
    """Lifecycle status for a role spawning proposal."""

    PENDING_APPROVAL = "PENDING_APPROVAL"
    APPROVED = "APPROVED"
    REJECTED = "REJECTED"


@dataclass
class SpawningProposal:
    """Formal recommendation authored by SpecializationEvaluator for human owner review."""

    proposal_id: str
    target_role_name: str
    target_role_title: str
    archetype: str
    recommended_permission_tier: PermissionTier
    recommended_tools: list[str]
    tradeoff_choice: TradeoffChoice
    empirical_justification: str
    tradeoff_analysis: dict[str, str]
    status: ProposalStatus = ProposalStatus.PENDING_APPROVAL
    created_at: str = field(default_factory=utc_now_iso)
    decided_at: Optional[str] = None
    decision_reason: Optional[str] = None

    def to_dict(self) -> dict[str, Any]:
        return {
            "proposal_id": self.proposal_id,
            "target_role_name": self.target_role_name,
            "target_role_title": self.target_role_title,
            "archetype": self.archetype,
            "recommended_permission_tier": self.recommended_permission_tier.value,
            "recommended_tools": list(self.recommended_tools),
            "tradeoff_choice": self.tradeoff_choice.value,
            "empirical_justification": self.empirical_justification,
            "tradeoff_analysis": dict(self.tradeoff_analysis),
            "status": self.status.value,
            "created_at": self.created_at,
            "decided_at": self.decided_at,
            "decision_reason": self.decision_reason,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> SpawningProposal:
        return cls(
            proposal_id=str(data.get("proposal_id", "")),
            target_role_name=str(data.get("target_role_name", "")),
            target_role_title=str(data.get("target_role_title", "")),
            archetype=str(data.get("archetype", "")),
            recommended_permission_tier=PermissionTier(
                data.get("recommended_permission_tier", PermissionTier.TIER_1_SAFE.value)
            ),
            recommended_tools=list(data.get("recommended_tools", [])),
            tradeoff_choice=TradeoffChoice(
                data.get("tradeoff_choice", TradeoffChoice.PROPOSE_SPECIALIST.value)
            ),
            empirical_justification=str(data.get("empirical_justification", "")),
            tradeoff_analysis=dict(data.get("tradeoff_analysis", {})),
            status=ProposalStatus(data.get("status", ProposalStatus.PENDING_APPROVAL.value)),
            created_at=str(data.get("created_at", utc_now_iso())),
            decided_at=data.get("decided_at"),
            decision_reason=data.get("decision_reason"),
        )

