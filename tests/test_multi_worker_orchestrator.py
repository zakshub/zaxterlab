"""Unit tests for MultiWorkerOrchestrator, DAG dependencies, and retries."""

import os
import shutil
import tempfile
import unittest

from zaxterlab.contracts.types import (
    AgentDefinition,
    PermissionTier,
    ProposalStatus,
    SpawningProposal,
    Task,
    TaskStatus,
    TradeoffChoice,
)
from zaxterlab.db.sqlite import SQLiteStore
from zaxterlab.engine.auditor import AuditorEngine, get_default_auditor_definition
from zaxterlab.engine.orchestrator import CyclicDependencyError, MultiWorkerOrchestrator
from zaxterlab.engine.worker import Worker1Engine, get_default_worker1_definition
from zaxterlab.models.base import CompletionRequest, CompletionResponse
from zaxterlab.models.mock import MockProvider
from zaxterlab.security.guard import BoundaryGuard
from zaxterlab.tools.registry import ToolRegistry


class TestMultiWorkerOrchestrator(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.mkdtemp(prefix="zaxterlab_orch_test_")
        self.db_path = os.path.join(self.temp_dir, "orch_test.db")
        self.workspace_dir = os.path.join(self.temp_dir, "workspace")
        os.makedirs(self.workspace_dir, exist_ok=True)

        self.store = SQLiteStore(self.db_path)
        self.guard = BoundaryGuard(workspace_root=self.workspace_dir, authorized_spend_usd=0.0)
        self.tools = ToolRegistry(self.guard)
        self.agent = get_default_worker1_definition()
        self.mock_provider = MockProvider()

        auditor_def = AgentDefinition(
            agent_id="zaks-auditor",
            name="Zaks",
            role="Independent Audit and Oversight",
            description="Auditor",
            allowed_tools=["read_file", "list_dir"],
            permission_tier=PermissionTier.TIER_1_SAFE,
        )
        self.auditor = AuditorEngine(auditor_def, self.mock_provider, self.guard, self.store, self.tools)
        self.worker_engine = Worker1Engine(
            self.agent, self.mock_provider, self.guard, self.store, self.tools, auditor=self.auditor
        )
        self.orchestrator = MultiWorkerOrchestrator(
            store=self.store,
            worker_engine=self.worker_engine,
            boundary_guard=self.guard,
            model_provider=self.mock_provider,
        )

    def tearDown(self):
        self.store.close()
        shutil.rmtree(self.temp_dir, ignore_errors=True)

    def test_dag_topological_sorting(self):
        """Orchestrator computes correct topological order for dependencies."""
        t1 = Task(task_id="t1", title="Init Schema", description="Base task")
        t2 = Task(task_id="t2", title="Build Models", description="Depends on t1", depends_on=["t1"])
        t3 = Task(task_id="t3", title="Build UI", description="Depends on t2", depends_on=["t2"])

        order = self.orchestrator.validate_dag([t3, t1, t2])
        self.assertEqual(order, ["t1", "t2", "t3"])

    def test_cyclic_dependency_rejected(self):
        """Cyclic task graph raises CyclicDependencyError."""
        t1 = Task(task_id="t1", title="Task 1", description="desc", depends_on=["t2"])
        t2 = Task(task_id="t2", title="Task 2", description="desc", depends_on=["t1"])

        with self.assertRaises(CyclicDependencyError):
            self.orchestrator.validate_dag([t1, t2])

    def test_pipeline_execution_honors_dependencies(self):
        """Upstream task must complete before downstream task can execute."""
        t1 = Task(task_id="t1", title="Task 1", description="Step 1")
        t2 = Task(task_id="t2", title="Task 2", description="Step 2", depends_on=["t1"])
        self.store.save_task(t1)
        self.store.save_task(t2)

        res = self.orchestrator.run_pipeline(["t1", "t2"])
        self.assertEqual(res["total"], 2)
        self.assertEqual(res["completed"], 2)
        self.assertEqual(res["execution_order"], ["t1", "t2"])

        updated_t1 = self.store.get_task("t1")
        updated_t2 = self.store.get_task("t2")
        self.assertEqual(updated_t1.status, TaskStatus.COMPLETED)
        self.assertEqual(updated_t2.status, TaskStatus.COMPLETED)

    def test_upstream_failure_blocks_downstream_task(self):
        """When an upstream task is blocked or failed, downstream task transitions to BLOCKED_BY_UPSTREAM."""
        t1 = Task(task_id="t1", title="Failing Task", description="Fails", status=TaskStatus.BLOCKED)
        t2 = Task(task_id="t2", title="Downstream Task", description="Blocked", depends_on=["t1"])
        self.store.save_task(t1)
        self.store.save_task(t2)

        result_t2 = self.orchestrator.execute_task(t2)
        self.assertEqual(result_t2.status, TaskStatus.BLOCKED_BY_UPSTREAM)
        self.assertIn("Upstream dependency 't1' is BLOCKED", result_t2.error_message)

    def test_specialist_routing_to_activated_agent(self):
        """Tasks assigned to an approved specialist are routed to that specialist agent."""
        # 1. Author and approve specialist Aroosh
        proposal = SpawningProposal(
            proposal_id="prop_aroosh_test",
            target_role_name="Aroosh",
            target_role_title="Quality Assurance",
            archetype="Shuri",
            recommended_permission_tier=PermissionTier.TIER_1_SAFE,
            recommended_tools=["read_file", "list_dir"],
            tradeoff_choice=TradeoffChoice.PROPOSE_SPECIALIST,
            empirical_justification="Need dedicated QA",
            tradeoff_analysis={},
            status=ProposalStatus.APPROVED,
            decided_at="2026-10-26T00:00:00Z",
        )
        self.store.save_proposal(proposal)

        # 2. Assign task to specialist
        t_qa = Task(
            task_id="t_qa",
            title="Regression Suite Audit",
            description="Run full QA verification",
            assigned_specialist="Aroosh",
        )
        self.store.save_task(t_qa)

        executed = self.orchestrator.execute_task(t_qa)
        self.assertEqual(executed.status, TaskStatus.COMPLETED)
        self.assertEqual(executed.assigned_agent_id, "aroosh-specialist")

    def test_retry_circuit_exhaustion(self):
        """Task retries up to max_retries upon failure before becoming BLOCKED."""
        # Create a mock provider that always simulates auditor rejection
        reject_response = CompletionResponse(
            text="Reject",
            plan="Plan",
            tool_calls=[],
            is_final=True,
            evaluation="Failed verification",
        )
        strict_mock = MockProvider(responder=lambda req: reject_response)

        # Auditor that rejects
        bad_auditor = AuditorEngine(self.auditor.agent, strict_mock, self.guard, self.store, self.tools)
        engine_with_rejection = Worker1Engine(
            self.agent, strict_mock, self.guard, self.store, self.tools, auditor=bad_auditor
        )
        orchestrator = MultiWorkerOrchestrator(
            self.store, engine_with_rejection, self.guard, strict_mock
        )

        t_failing = Task(
            task_id="t_failing",
            title="Unverifiable Task",
            description="Will trigger rejection",
            max_retries=2,
        )
        self.store.save_task(t_failing)

        res = orchestrator.execute_task(t_failing)
        self.assertEqual(res.status, TaskStatus.BLOCKED)
        self.assertGreaterEqual(res.retry_count, 2)


if __name__ == "__main__":
    unittest.main()
