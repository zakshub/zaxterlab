"""Execution Telemetry and Evidence-Based Worker Performance Evaluation."""

from __future__ import annotations

from typing import Any, Optional

from zaxterlab.contracts.types import TaskStatus
from zaxterlab.db.sqlite import SQLiteStore


class WorkerPerformanceEvaluator:
    """Computes empirical evidence-based metrics on worker efficiency, auditor accuracy, and system throughput."""

    def __init__(self, store: SQLiteStore) -> None:
        self.store = store

    def compute_telemetry(self) -> dict[str, Any]:
        """Aggregate granular execution statistics across all tasks, sessions, traces, and audit decisions."""
        tasks = self.store.list_tasks()
        audit_logs = self.store.get_audit_logs()

        total_tasks = len(tasks)
        status_counts: dict[str, int] = {}
        specialist_distribution: dict[str, int] = {}
        retry_distribution: dict[int, int] = {}

        total_tokens = 0
        total_prompt_tokens = 0
        total_completion_tokens = 0
        total_cost_usd = 0.0

        for t in tasks:
            status_counts[t.status.value] = status_counts.get(t.status.value, 0) + 1
            spec = t.assigned_specialist or "Reem"
            specialist_distribution[spec] = specialist_distribution.get(spec, 0) + 1
            retry_distribution[t.retry_count] = retry_distribution.get(t.retry_count, 0) + 1

            # Fetch latest session for token accumulation
            sess = self.store.get_latest_session_for_task(t.task_id)
            if sess:
                total_tokens += sess.total_token_usage.total_tokens
                total_prompt_tokens += sess.total_token_usage.prompt_tokens
                total_completion_tokens += sess.total_token_usage.completion_tokens
                total_cost_usd += sess.total_token_usage.estimated_cost_usd

        # Audit events telemetry
        auditor_approvals = [l for l in audit_logs if l.get("event_type") == "TASK_COMPLETED"]
        auditor_rejections = [l for l in audit_logs if l.get("event_type") == "AUDITOR_REJECTED"]
        retries_dispatched = [l for l in audit_logs if l.get("event_type") == "TASK_RETRY_DISPATCHED"]
        boundary_violations = [l for l in audit_logs if "VIOLATION" in l.get("event_type", "").upper()]

        total_audit_decisions = len(auditor_approvals) + len(auditor_rejections)
        first_pass_approval_pct = (
            round((len(auditor_approvals) / total_audit_decisions) * 100, 1)
            if total_audit_decisions > 0
            else 100.0
        )

        completed_count = status_counts.get(TaskStatus.COMPLETED.value, 0)
        completion_rate_pct = (
            round((completed_count / total_tasks) * 100, 1) if total_tasks > 0 else 0.0
        )

        # Bottleneck detection
        bottlenecks: list[str] = []
        if len(auditor_rejections) >= 2:
            bottlenecks.append(
                f"Elevated verification rejection count ({len(auditor_rejections)} rejections). Code generation requires tighter test assertions."
            )
        if status_counts.get(TaskStatus.BLOCKED.value, 0) > 0:
            bottlenecks.append(
                f"{status_counts.get(TaskStatus.BLOCKED.value)} tasks blocked due to refinement exhaustion. Review requirements clarity."
            )
        if len(boundary_violations) > 0:
            bottlenecks.append(
                f"{len(boundary_violations)} boundary interceptions detected. Workspace sandboxing actively maintained."
            )

        return {
            "summary": {
                "total_tasks_tracked": total_tasks,
                "completed_tasks": completed_count,
                "task_completion_rate_pct": completion_rate_pct,
                "status_counts": status_counts,
                "specialist_task_distribution": specialist_distribution,
                "retry_distribution": retry_distribution,
            },
            "token_economics": {
                "total_tokens_consumed": total_tokens,
                "prompt_tokens": total_prompt_tokens,
                "completion_tokens": total_completion_tokens,
                "cumulative_spend_usd": total_cost_usd,
                "spend_bound_satisfied": total_cost_usd == 0.0,
            },
            "auditor_efficiency": {
                "total_reviews": total_audit_decisions,
                "approvals": len(auditor_approvals),
                "rejections": len(auditor_rejections),
                "retries_dispatched": len(retries_dispatched),
                "first_pass_approval_pct": first_pass_approval_pct,
            },
            "governance": {
                "boundary_violations_blocked": len(boundary_violations),
                "identified_bottlenecks": bottlenecks,
                "evidence_standard": "Verified hermetically against SQLite records",
            },
        }
