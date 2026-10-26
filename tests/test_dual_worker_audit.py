"""Integration tests for Phase 2: Dual-Worker Verification and Independent Audit Loop."""

import os
import shutil
import tempfile
import unittest

from zaxterlab.contracts.types import (
    PermissionTier,
    SessionStatus,
    Task,
    TaskStatus,
    TokenUsage,
    ToolCall,
)
from zaxterlab.db.sqlite import SQLiteStore
from zaxterlab.engine.auditor import AuditorEngine, get_default_auditor_definition
from zaxterlab.engine.worker import Worker1Engine, get_default_worker1_definition
from zaxterlab.models.base import CompletionResponse
from zaxterlab.models.mock import MockProvider
from zaxterlab.security.guard import BoundaryGuard, PermissionDeniedError
from zaxterlab.tools.registry import ToolRegistry


class TestDualWorkerAudit(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.mkdtemp(prefix="zaxterlab_audit_test_")
        self.db_path = os.path.join(self.temp_dir, "audit_test.db")
        self.workspace_dir = os.path.join(self.temp_dir, "workspace")
        os.makedirs(self.workspace_dir, exist_ok=True)

        self.store = SQLiteStore(self.db_path)
        self.guard = BoundaryGuard(workspace_root=self.workspace_dir, authorized_spend_usd=0.0)
        self.tools = ToolRegistry(self.guard)

        self.worker1_agent = get_default_worker1_definition()
        self.auditor_agent = get_default_auditor_definition()

    def tearDown(self):
        self.store.close()
        shutil.rmtree(self.temp_dir, ignore_errors=True)

    def test_auditor_approval_flow_and_coordination_telemetry(self):
        # Worker 1 writes a genuine file and completes
        worker_resp = [
            CompletionResponse(
                text="Generated artifact",
                plan="Write verified file",
                tool_calls=[
                    ToolCall("c1", "write_file", {"path": "module.py", "content": "print('verified')\n"})
                ],
                is_final=True,
                evaluation="Finished draft",
                token_usage=TokenUsage(30, 40, 70, 0.0),
            )
        ]
        worker_model = MockProvider(responses=worker_resp)

        # Auditor approves work
        auditor_resp = [
            CompletionResponse(
                text="Approved: File exists and passes constitutional criteria.",
                is_final=True,
                token_usage=TokenUsage(10, 15, 25, 0.0),
            )
        ]
        auditor_model = MockProvider(responses=auditor_resp)

        auditor = AuditorEngine(
            agent=self.auditor_agent,
            model=auditor_model,
            boundary_guard=self.guard,
            store=self.store,
            tool_registry=self.tools,
        )

        engine = Worker1Engine(
            agent=self.worker1_agent,
            model=worker_model,
            boundary_guard=self.guard,
            store=self.store,
            tool_registry=self.tools,
            auditor=auditor,
        )

        task = Task(
            task_id="task_dual_01",
            title="Implement verified module",
            description="Write module.py and submit for review",
        )
        self.store.save_task(task)

        # Execute
        session = engine.execute_task(task)

        # 1. Verification of Task & Session Status
        self.assertEqual(task.status, TaskStatus.COMPLETED)
        self.assertEqual(session.status, SessionStatus.COMPLETED)
        self.assertIn("[Audited: Approved]", task.result_summary)

        # 2. Verification of Coordination Telemetry
        self.assertIn("coordination_tokens", session.state_data)
        self.assertGreater(session.state_data["coordination_tokens"], 0)
        self.assertIn("coordination_overhead_pct", session.state_data)
        self.assertGreater(session.state_data["coordination_overhead_pct"], 0.0)

        # 3. Verification of Audit Trail
        audit_logs = self.store.get_audit_logs("task_dual_01")
        event_types = [e["event_type"] for e in audit_logs]
        self.assertIn("TASK_AUDITED", event_types)
        self.assertIn("TASK_COMPLETED", event_types)

    def test_auditor_catches_hallucination_and_rejects(self):
        # Worker 1 claims it wrote a file without calling write_file tool
        worker_resp = [
            CompletionResponse(
                text="I have completed creating fake_file.txt",
                plan="Claim completed without tool call",
                tool_calls=[
                    ToolCall("c_fake", "write_file", {"path": "nonexistent_file.txt", "content": ""})
                ],
                is_final=True,
                evaluation="Claim complete",
                token_usage=TokenUsage(20, 20, 40, 0.0),
            )
        ]
        # Delete file if somehow created
        fake_path = os.path.join(self.workspace_dir, "nonexistent_file.txt")
        if os.path.exists(fake_path):
            os.remove(fake_path)

        worker_model = MockProvider(responses=worker_resp)

        # Auditor uses rule-based forensic check (detects 0 bytes or nonexistent file)
        auditor = AuditorEngine(
            agent=self.auditor_agent,
            model=None,  # Rule-based detector
            boundary_guard=self.guard,
            store=self.store,
            tool_registry=self.tools,
        )

        engine = Worker1Engine(
            agent=self.worker1_agent,
            model=worker_model,
            boundary_guard=self.guard,
            store=self.store,
            tool_registry=self.tools,
            auditor=auditor,
        )

        task = Task(task_id="task_dual_fake", title="Fake Task", description="Write fake file")
        self.store.save_task(task)

        # Execute only 1 step
        session = engine.execute_task(task, max_steps_per_run=1)

        # Must be rejected by Auditor
        self.assertEqual(task.status, TaskStatus.REJECTED)
        self.assertIn("Rejected by Auditor", task.result_summary)
        self.assertEqual(session.state_data.get("refinement_cycles"), 1)

    def test_refinement_cycle_exhaustion_blocks_task(self):
        # Worker 1 keeps submitting failing work
        worker_resp = [
            CompletionResponse(
                text="Draft attempt",
                tool_calls=[],
                is_final=True,
                token_usage=TokenUsage(10, 10, 20, 0.0),
            )
            for _ in range(5)
        ]
        worker_model = MockProvider(responses=worker_resp)

        # Auditor explicitly rejects every cycle
        auditor_resp = [
            CompletionResponse(text="REJECT: Inadequate work quality.", is_final=True)
            for _ in range(5)
        ]
        auditor_model = MockProvider(responses=auditor_resp)

        auditor = AuditorEngine(
            agent=self.auditor_agent,
            model=auditor_model,
            boundary_guard=self.guard,
            store=self.store,
            tool_registry=self.tools,
        )

        # Limit to 2 refinement cycles
        engine = Worker1Engine(
            agent=self.worker1_agent,
            model=worker_model,
            boundary_guard=self.guard,
            store=self.store,
            tool_registry=self.tools,
            auditor=auditor,
            max_refinement_cycles=2,
        )

        task = Task(task_id="task_exhaust", title="Exhaust Task", description="Exhaust cycles")
        self.store.save_task(task)

        session = engine.execute_task(task)

        # After 2 rejected cycles, task transitions to BLOCKED
        self.assertEqual(task.status, TaskStatus.BLOCKED)
        self.assertEqual(session.status, SessionStatus.FAILED)
        self.assertIn("Blocked by Auditor", task.result_summary)

        # Check audit trail recorded the block
        audit_logs = self.store.get_audit_logs("task_exhaust")
        self.assertTrue(any(e["event_type"] == "TASK_BLOCKED_BY_AUDITOR" for e in audit_logs))

    def test_auditor_read_only_boundary_enforcement(self):
        # Zaks (Auditor) must be strictly TIER_1_SAFE with read-only tools
        self.assertEqual(self.auditor_agent.permission_tier, PermissionTier.TIER_1_SAFE)
        self.assertIn("read_file", self.auditor_agent.allowed_tools)
        self.assertIn("list_dir", self.auditor_agent.allowed_tools)

        # Auditor is forbidden from write_file and run_command
        with self.assertRaises(PermissionDeniedError):
            self.guard.validate_tool_access(self.auditor_agent, "write_file")

        with self.assertRaises(PermissionDeniedError):
            self.guard.validate_tool_access(self.auditor_agent, "run_command")


if __name__ == "__main__":
    unittest.main()
