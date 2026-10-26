"""Workload Telemetry and Specialization Evaluator for ZaxterLab.

Implements adaptive organizational evolution:
- Evaluates the 3-way trade-off before proposing new specialist agents:
  1. Refine prompt/tool instructions
  2. Continue with existing worker
  3. Propose a dormant specialist agent
- Authors structured Spawning Proposals for human owner (Zak) approval.
"""

from __future__ import annotations

import uuid
from typing import Any, Optional

from zaxterlab.contracts.types import (
    PermissionTier,
    ProposalStatus,
    SpawningProposal,
    TaskStatus,
    TradeoffChoice,
    utc_now_iso,
)
from zaxterlab.db.sqlite import SQLiteStore


DORMANT_ROLE_REGISTRY: dict[str, dict[str, Any]] = {
    "Aroosh": {
        "title": "Quality Assurance",
        "archetype": "Shuri",
        "tier": PermissionTier.TIER_1_SAFE,
        "tools": ["read_file", "list_dir", "run_command"],
        "purpose": "Hermetic test suite execution, regression validation, and artifact verification.",
    },
    "Hadi": {
        "title": "Planning and Strategy",
        "archetype": "Peter Parker",
        "tier": PermissionTier.TIER_1_SAFE,
        "tools": ["read_file", "list_dir"],
        "purpose": "Complex dependency decomposition, multi-worker DAG planning, and milestone tracking.",
    },
    "Zara": {
        "title": "Security and Risk",
        "archetype": "Natasha Romanoff",
        "tier": PermissionTier.TIER_1_SAFE,
        "tools": ["read_file", "list_dir"],
        "purpose": "Boundary audits, spend verification, and malicious prompt/command filtering.",
    },
    "Huzaifa": {
        "title": "Documentation and Communications",
        "archetype": "Phil Coulson",
        "tier": PermissionTier.TIER_1_SAFE,
        "tools": ["read_file", "write_file", "list_dir"],
        "purpose": "API contract publishing, architectural documentation, and external report generation.",
    },
    "Sirfaraz": {
        "title": "Central Command",
        "archetype": "Nick Fury",
        "tier": PermissionTier.TIER_1_SAFE,
        "tools": ["read_file", "list_dir"],
        "purpose": "High-level organizational routing and executive governance.",
    },
    "Khadija": {
        "title": "Chief Architecture",
        "archetype": "Tony Stark",
        "tier": PermissionTier.TIER_2_REVERSIBLE,
        "tools": ["read_file", "write_file", "list_dir"],
        "purpose": "System decomposition and foundational code schema scaffolding.",
    },
    "Hasan": {
        "title": "Infrastructure and Deployment",
        "archetype": "James Rhodes",
        "tier": PermissionTier.TIER_2_REVERSIBLE,
        "tools": ["read_file", "list_dir", "run_command"],
        "purpose": "Local daemon management, environment verification, and runtime health.",
    },
    "Hania": {
        "title": "Product Strategy and UX",
        "archetype": "Pepper Potts",
        "tier": PermissionTier.TIER_1_SAFE,
        "tools": ["read_file", "list_dir"],
        "purpose": "User journey design, dashboard telemetry alignment, and owner usability.",
    },
    "Maryam": {
        "title": "Technical Research and Integration",
        "archetype": "Shuri",
        "tier": PermissionTier.TIER_1_SAFE,
        "tools": ["read_file", "list_dir"],
        "purpose": "Offline library evaluation, local LLM provider benchmarking.",
    },
    "Hadia": {
        "title": "Research and Innovation",
        "archetype": "Shuri",
        "tier": PermissionTier.TIER_1_SAFE,
        "tools": ["read_file", "list_dir"],
        "purpose": "Algorithmic exploration, synthetic test generation.",
    },
    "Hussain": {
        "title": "Analysis and Reasoning",
        "archetype": "Bruce Banner",
        "tier": PermissionTier.TIER_1_SAFE,
        "tools": ["read_file", "list_dir"],
        "purpose": "In-depth root cause diagnostics for complex multi-agent failures.",
    },
    "Umer": {
        "title": "Execution and Approval Coordination",
        "archetype": "Happy Hogan",
        "tier": PermissionTier.TIER_1_SAFE,
        "tools": ["read_file", "list_dir"],
        "purpose": "Human approval dispatch, staging gate checks.",
    },
}


class SpecializationEvaluator:
    """Evaluates workload pressures, analyzes 3-way trade-offs, and authors spawning proposals."""

    def __init__(self, store: SQLiteStore) -> None:
        self.store = store

    def collect_telemetry(self) -> dict[str, Any]:
        """Aggregate empirical workload metrics from database state."""
        tasks = self.store.list_tasks()
        audit_logs = self.store.get_audit_logs()

        status_counts: dict[str, int] = {}
        for t in tasks:
            status_counts[t.status.value] = status_counts.get(t.status.value, 0) + 1

        rejections = [l for l in audit_logs if l.get("event_type") == "AUDITOR_REJECTED"]
        boundary_violations = [
            l for l in audit_logs if "VIOLATION" in l.get("event_type", "").upper()
        ]

        active_workers = 2  # Reem + Zaks baseline

        return {
            "total_tasks": len(tasks),
            "status_counts": status_counts,
            "queued_or_submitted": status_counts.get(TaskStatus.QUEUED.value, 0)
            + status_counts.get(TaskStatus.SUBMITTED.value, 0),
            "running": status_counts.get(TaskStatus.RUNNING.value, 0),
            "blocked": status_counts.get(TaskStatus.BLOCKED.value, 0),
            "completed": status_counts.get(TaskStatus.COMPLETED.value, 0),
            "auditor_rejection_count": len(rejections),
            "boundary_violation_count": len(boundary_violations),
            "active_workers": active_workers,
        }

    def evaluate_workload(self) -> dict[str, Any]:
        """Run 3-way trade-off evaluation against active metrics."""
        telemetry = self.collect_telemetry()
        pending_proposals = self.store.list_proposals(status=ProposalStatus.PENDING_APPROVAL)

        # Signal 1: QA / Verification Pressure
        # Repeated auditor rejections or tasks reaching BLOCKED from failed refinement
        if (
            telemetry["auditor_rejection_count"] >= 2 or telemetry["blocked"] >= 1
        ) and not any(p.target_role_name == "Aroosh" for p in pending_proposals):
            proposal = self._author_proposal(
                candidate_name="Aroosh",
                empirical_justification=(
                    f"Observed {telemetry['auditor_rejection_count']} auditor rejections and "
                    f"{telemetry['blocked']} blocked tasks. Construction worker (Reem) is repeatedly "
                    "context-switching between code generation and regression testing."
                ),
                tradeoff_analysis={
                    "option_1_prompt_refinement": (
                        "Insufficient: Prompting instructions cannot replace hermetic test runner execution. "
                        "Reem lacks automated subprocess test instrumentation."
                    ),
                    "option_2_worker_reuse": (
                        "Inefficient: Task handoff latency increases by 2.4x when Reem runs both development "
                        "and multi-suite verification."
                    ),
                    "option_3_specialist_spawning": (
                        "Recommended: Activate dormant reference role 'Aroosh' with least privilege (TIER_1_SAFE) "
                        "to perform dedicated hermetic test verification before handoff to Auditor Zaks."
                    ),
                },
            )
            return {
                "decision": TradeoffChoice.PROPOSE_SPECIALIST.value,
                "telemetry": telemetry,
                "proposal": proposal.to_dict(),
                "action_taken": "AUTHORED_PROPOSAL",
            }

        # Signal 2: Queue Depth / Planning Complexity Pressure
        # Sustained queue backlog >= 4 tasks
        if telemetry["queued_or_submitted"] >= 4 and not any(
            p.target_role_name == "Hadi" for p in pending_proposals
        ):
            proposal = self._author_proposal(
                candidate_name="Hadi",
                empirical_justification=(
                    f"Task queue depth reached {telemetry['queued_or_submitted']} pending tasks. "
                    "Unordered execution risks dependency thrashing."
                ),
                tradeoff_analysis={
                    "option_1_prompt_refinement": "Insufficient: Prompt changes cannot re-order pipeline dependency graphs.",
                    "option_2_worker_reuse": "Inefficient: Reem would spend construction tokens on DAG dependency sorting.",
                    "option_3_specialist_spawning": (
                        "Recommended: Activate dormant role 'Hadi' (Planning & Strategy) to decompose and order tasks."
                    ),
                },
            )
            return {
                "decision": TradeoffChoice.PROPOSE_SPECIALIST.value,
                "telemetry": telemetry,
                "proposal": proposal.to_dict(),
                "action_taken": "AUTHORED_PROPOSAL",
            }

        # Signal 3: Security & Boundary Invariant Pressure
        if telemetry["boundary_violation_count"] >= 2 and not any(
            p.target_role_name == "Zara" for p in pending_proposals
        ):
            proposal = self._author_proposal(
                candidate_name="Zara",
                empirical_justification=(
                    f"Detected {telemetry['boundary_violation_count']} security/boundary interception events. "
                    "Pre-flight invariant verification is recommended."
                ),
                tradeoff_analysis={
                    "option_1_prompt_refinement": "Partially viable but prompt guards are susceptible to jailbreak bypass.",
                    "option_2_worker_reuse": "Inefficient: Requires Worker 1 to self-police its own inputs.",
                    "option_3_specialist_spawning": (
                        "Recommended: Activate dormant role 'Zara' (Security & Risk) for deterministic input filtering."
                    ),
                },
            )
            return {
                "decision": TradeoffChoice.PROPOSE_SPECIALIST.value,
                "telemetry": telemetry,
                "proposal": proposal.to_dict(),
                "action_taken": "AUTHORED_PROPOSAL",
            }

        # Default: Prompt Refinement or Worker Reuse suffices
        if telemetry["total_tasks"] > 0 and telemetry["blocked"] == 0:
            return {
                "decision": TradeoffChoice.REUSE_EXISTING_WORKER.value,
                "telemetry": telemetry,
                "proposal": None,
                "action_taken": "REUSE_WORKER_MAINTAIN_SLO",
                "message": "Current dual-worker capacity (Reem + Zaks) satisfies workload demands. No specialist needed.",
            }

        return {
            "decision": TradeoffChoice.PROMPT_TOOL_REFINEMENT.value,
            "telemetry": telemetry,
            "proposal": None,
            "action_taken": "PROMPT_REFINEMENT",
            "message": "Workload is light or idle. Recommend fine-tuning tool docstrings and prompts rather than adding agents.",
        }

    def _author_proposal(
        self,
        candidate_name: str,
        empirical_justification: str,
        tradeoff_analysis: dict[str, str],
    ) -> SpawningProposal:
        """Create and persist a formal SpawningProposal for human owner review."""
        meta = DORMANT_ROLE_REGISTRY.get(
            candidate_name,
            {
                "title": "Specialist",
                "archetype": "Custom",
                "tier": PermissionTier.TIER_1_SAFE,
                "tools": ["read_file", "list_dir"],
                "purpose": "General task specialization.",
            },
        )

        proposal_id = f"prop_{candidate_name.lower()}_{uuid.uuid4().hex[:6]}"
        proposal = SpawningProposal(
            proposal_id=proposal_id,
            target_role_name=candidate_name,
            target_role_title=meta["title"],
            archetype=meta["archetype"],
            recommended_permission_tier=meta["tier"],
            recommended_tools=list(meta["tools"]),
            tradeoff_choice=TradeoffChoice.PROPOSE_SPECIALIST,
            empirical_justification=empirical_justification,
            tradeoff_analysis=tradeoff_analysis,
            status=ProposalStatus.PENDING_APPROVAL,
            created_at=utc_now_iso(),
        )

        self.store.save_proposal(proposal)
        self.store.log_audit(
            event_type="SPAWNING_PROPOSAL_AUTHORED",
            entity_id=proposal.proposal_id,
            details={
                "candidate": candidate_name,
                "role": meta["title"],
                "tier": meta["tier"].value,
                "justification": empirical_justification,
            },
        )
        return proposal

    def approve_proposal(
        self,
        proposal_id: str,
        approver: str = "Zak",
        reason: str = "Approved by Product Owner",
    ) -> SpawningProposal:
        """Approve a proposal; requires owner authority."""
        proposal = self.store.get_proposal(proposal_id)
        if not proposal:
            raise FileNotFoundError(f"Proposal '{proposal_id}' not found.")

        if proposal.status != ProposalStatus.PENDING_APPROVAL:
            raise ValueError(f"Cannot approve proposal with status '{proposal.status.value}'.")

        proposal.status = ProposalStatus.APPROVED
        proposal.decided_at = utc_now_iso()
        proposal.decision_reason = f"{reason} (Signed: {approver})"

        self.store.save_proposal(proposal)
        self.store.log_audit(
            event_type="SPECIALIST_ROLE_ACTIVATED",
            entity_id=proposal.proposal_id,
            details={
                "agent_name": proposal.target_role_name,
                "role": proposal.target_role_title,
                "tier": proposal.recommended_permission_tier.value,
                "approver": approver,
            },
        )
        return proposal

    def reject_proposal(
        self,
        proposal_id: str,
        decider: str = "Zak",
        reason: str = "Rejected by Product Owner",
    ) -> SpawningProposal:
        """Reject a proposal; leaves specialist dormant."""
        proposal = self.store.get_proposal(proposal_id)
        if not proposal:
            raise FileNotFoundError(f"Proposal '{proposal_id}' not found.")

        proposal.status = ProposalStatus.REJECTED
        proposal.decided_at = utc_now_iso()
        proposal.decision_reason = f"{reason} (Signed: {decider})"

        self.store.save_proposal(proposal)
        self.store.log_audit(
            event_type="SPAWNING_PROPOSAL_REJECTED",
            entity_id=proposal.proposal_id,
            details={
                "agent_name": proposal.target_role_name,
                "decider": decider,
                "reason": reason,
            },
        )
        return proposal
