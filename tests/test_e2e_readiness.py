"""End-to-End Readiness Review and Comprehensive Integration Verification Suite.

Verifies:
1. End-to-end organic scaling: Workload evaluation -> Spawning Proposal -> Owner Approval -> Specialist Activation.
2. Multi-Worker DAG Pipeline Execution: Topological sequencing, dependency satisfaction, specialist routing, and auditor sign-off.
3. Upstream Failure Propagation: Downstream tasks safely blocked by upstream failure.
4. Execution Telemetry & Performance Evaluation: Accurate token accounting, auditor pass rates, and bottleneck identification.
5. Absolute USD $0.00 spend guard and workspace sandboxing guarantees throughout multi-worker workflows.
"""

from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from zaxterlab.contracts.types import (
    AgentDefinition,
    PermissionTier,
    ProposalStatus,
    Task,
    TaskStatus,
)
from zaxterlab.db.sqlite import SQLiteStore
from zaxterlab.engine.auditor import AuditorEngine
from zaxterlab.engine.evaluator import SpecializationEvaluator
from zaxterlab.engine.orchestrator import MultiWorkerOrchestrator
from zaxterlab.engine.telemetry import WorkerPerformanceEvaluator
from zaxterlab.engine.worker import Worker1Engine
from zaxterlab.models.mock import MockProvider
from zaxterlab.security.guard import (
    BoundaryGuard,
    WorkspaceGuard,
    WorkspacePathViolationError,
)
from zaxterlab.tools.registry import ToolRegistry


class TestEndToEndReadiness(unittest.TestCase):
    """Hermetic end-to-end verification suite testing all core operating system capabilities."""

    def setUp(self) -> None:
        self.tmp_dir = tempfile.TemporaryDirectory()
        self.workspace_root = Path(self.tmp_dir.name) / "workspace"
        self.workspace_root.mkdir(parents=True, exist_ok=True)
        self.db_path = Path(self.tmp_dir.name) / "zaxterlab_test.db"

        self.store = SQLiteStore(str(self.db_path))
        self.boundary_guard = BoundaryGuard(workspace_root=self.workspace_root)

        self.worker_agent = AgentDefinition(
            agent_id="reem-worker-1",
            name="Reem",
            role="Construction and Programming",
            description="Autonomous construction worker.",
            allowed_tools=["read_file", "write_file", "list_dir", "run_command"],
            max_iterations=10,
            permission_tier=PermissionTier.TIER_2_REVERSIBLE,
        )

        self.auditor_agent = AgentDefinition(
            agent_id="zaks-auditor",
            name="Zaks",
            role="Independent Audit and Oversight",
            description="Read-only independent auditor.",
            allowed_tools=["read_file", "list_dir"],
            max_iterations=5,
            permission_tier=PermissionTier.TIER_1_SAFE,
        )

        self.mock_model = MockProvider()
        self.tool_registry = ToolRegistry(self.boundary_guard)

        self.auditor_engine = AuditorEngine(
            agent=self.auditor_agent,
            model=self.mock_model,
            boundary_guard=self.boundary_guard,
            store=self.store,
            tool_registry=self.tool_registry,
        )

        self.worker_engine = Worker1Engine(
            agent=self.worker_agent,
            model=self.mock_model,
            boundary_guard=self.boundary_guard,
            store=self.store,
            tool_registry=self.tool_registry,
            auditor=self.auditor_engine,
        )

        self.evaluator = SpecializationEvaluator(self.store)
        self.telemetry = WorkerPerformanceEvaluator(self.store)
        self.orchestrator = MultiWorkerOrchestrator(
            store=self.store,
            worker_engine=self.worker_engine,
            boundary_guard=self.boundary_guard,
            model_provider=self.mock_model,
        )

    def tearDown(self) -> None:
        self.tmp_dir.cleanup()

    def test_complete_e2e_scaling_pipeline_and_telemetry(self) -> None:
        """Full organizational workflow:

        1. Seed workload history with context-switching overhead.
        2. Evaluator authors SpawningProposal for Aroosh (QA).
        3. Owner Zak reviews and signs approval.
        4. Specialist Aroosh is activated and routed for QA tasks.
        5. Multi-Worker DAG executes: Reem (build) -> Aroosh (verify) -> Zaks (audit).
        6. Telemetry confirms 100% completion, $0.00 spend, and complete audit trail.
        """
        # Step 1: Seed a task that failed/blocked to provide empirical evidence
        seed_task = Task(
            task_id="seed_task_01",
            title="Complex Parser",
            description="Initial parser task requiring heavy verification.",
            status=TaskStatus.BLOCKED,
            assigned_agent_id="reem-worker-1",
        )
        self.store.save_task(seed_task)

        # Step 2: Run Evaluator analysis
        eval_result = self.evaluator.evaluate_workload()
        self.assertEqual(eval_result["decision"], "PROPOSE_SPECIALIST")
        proposal_dict = eval_result["proposal"]
        self.assertIsNotNone(proposal_dict)
        proposal_id = proposal_dict["proposal_id"]
        self.assertEqual(proposal_dict["target_role_name"], "Aroosh")
        self.assertEqual(proposal_dict["status"], ProposalStatus.PENDING_APPROVAL.value)

        # Step 3: Owner Approval Gate (Signing with custom authorization note)
        approved_proposal = self.evaluator.approve_proposal(
            proposal_id, approver="Zak", reason="Approved QA Specialist for pipeline verification"
        )
        self.assertEqual(approved_proposal.status, ProposalStatus.APPROVED)
        self.assertIn("Signed: Zak", approved_proposal.decision_reason)

        # Step 4: Refresh Orchestrator specialist roster
        self.orchestrator._refresh_active_specialists()
        self.assertIn("aroosh", self.orchestrator.active_specialists)
        aroosh_agent = self.orchestrator.active_specialists["aroosh"]
        self.assertEqual(aroosh_agent.permission_tier, PermissionTier.TIER_1_SAFE)

        # Step 5: Define 2-stage multi-worker DAG pipeline
        build_task = Task(
            task_id="e2e_task_build",
            title="Build Math Module",
            description="Implement math functions in math_mod.py.",
            assigned_specialist="Reem",
            depends_on=[],
        )
        qa_task = Task(
            task_id="e2e_task_qa",
            title="Verify Math Module",
            description="Run assertions on math_mod.py.",
            assigned_specialist="Aroosh",
            depends_on=["e2e_task_build"],
        )
        self.store.save_task(build_task)
        self.store.save_task(qa_task)

        # Step 6: Execute multi-worker pipeline
        pipeline_outcome = self.orchestrator.run_pipeline(["e2e_task_build", "e2e_task_qa"])

        self.assertEqual(pipeline_outcome["total"], 2)
        self.assertEqual(pipeline_outcome["completed"], 2)
        self.assertEqual(pipeline_outcome["failed"], 0)
        self.assertEqual(pipeline_outcome["blocked"], 0)
        self.assertEqual(pipeline_outcome["execution_order"], ["e2e_task_build", "e2e_task_qa"])

        # Step 7: Verify tasks in store
        saved_build = self.store.get_task("e2e_task_build")
        saved_qa = self.store.get_task("e2e_task_qa")
        self.assertIsNotNone(saved_build)
        self.assertIsNotNone(saved_qa)
        self.assertEqual(saved_build.status, TaskStatus.COMPLETED)
        self.assertEqual(saved_qa.status, TaskStatus.COMPLETED)
        self.assertEqual(saved_build.assigned_agent_id, "reem-worker-1")
        self.assertEqual(saved_qa.assigned_agent_id, "aroosh-specialist")

        # Step 8: Verify Telemetry
        tel = self.telemetry.compute_telemetry()
        self.assertEqual(tel["summary"]["completed_tasks"], 2)
        self.assertEqual(tel["token_economics"]["cumulative_spend_usd"], 0.0)
        self.assertTrue(tel["token_economics"]["spend_bound_satisfied"])
        self.assertEqual(tel["auditor_efficiency"]["first_pass_approval_pct"], 100.0)
        self.assertEqual(tel["summary"]["specialist_task_distribution"]["Reem"], 2)
        self.assertEqual(tel["summary"]["specialist_task_distribution"]["Aroosh"], 1)

        # Step 9: Verify Audit Logs
        logs = self.store.get_audit_logs()
        event_types = [l["event_type"] for l in logs]
        self.assertIn("SPAWNING_PROPOSAL_AUTHORED", event_types)
        self.assertIn("SPECIALIST_ROLE_ACTIVATED", event_types)
        self.assertIn("TASK_AUDITED", event_types)
        self.assertIn("TASK_COMPLETED", event_types)

    def test_upstream_failure_propagation(self) -> None:
        """Upstream task failure safely halts dependent tasks and marks them BLOCKED_BY_UPSTREAM."""
        parent_task = Task(
            task_id="parent_failing_task",
            title="Broken Upstream Step",
            description="Upstream task that is blocked.",
            status=TaskStatus.BLOCKED,
        )
        child_task = Task(
            task_id="child_dependent_task",
            title="Downstream Verification",
            description="Should not execute if parent is blocked.",
            depends_on=["parent_failing_task"],
        )
        self.store.save_task(parent_task)
        self.store.save_task(child_task)

        executed_child = self.orchestrator.execute_task(child_task)

        self.assertEqual(executed_child.status, TaskStatus.BLOCKED_BY_UPSTREAM)
        self.assertIn("is BLOCKED", executed_child.error_message)

        # Confirm audit log records upstream block
        logs = self.store.get_audit_logs(entity_id="child_dependent_task")
        event_types = [l["event_type"] for l in logs]
        self.assertIn("TASK_BLOCKED_BY_UPSTREAM", event_types)

    def test_sandbox_path_traversal_aborts_safely(self) -> None:
        """Any attempt to access filesystem outside sandbox is immediately caught by BoundaryGuard."""
        with self.assertRaises(WorkspacePathViolationError):
            self.boundary_guard.workspace.resolve_safe_path("../../../etc/passwd")

        with self.assertRaises(WorkspacePathViolationError):
            self.boundary_guard.workspace.resolve_safe_path("/root/.ssh/id_rsa")


if __name__ == "__main__":
    unittest.main()
