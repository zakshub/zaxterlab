"""Unit tests for Worker 1 execution loop: Read -> Plan -> Tool Call -> Evaluate -> Log."""

import os
import shutil
import tempfile
import unittest

from zaxterlab.contracts.types import (
    AgentDefinition,
    PermissionTier,
    SessionStatus,
    Task,
    TaskStatus,
    TokenUsage,
    ToolCall,
)
from zaxterlab.db.sqlite import SQLiteStore
from zaxterlab.engine.worker import Worker1Engine, get_default_worker1_definition
from zaxterlab.models.base import CompletionResponse
from zaxterlab.models.mock import MockProvider
from zaxterlab.security.guard import BoundaryGuard
from zaxterlab.tools.registry import ToolRegistry


class TestWorkerEngine(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.mkdtemp(prefix="zaxterlab_engine_")
        self.db_path = os.path.join(self.temp_dir, "zaxterlab.db")
        self.workspace_dir = os.path.join(self.temp_dir, "workspace")
        os.makedirs(self.workspace_dir, exist_ok=True)

        self.store = SQLiteStore(self.db_path)
        self.guard = BoundaryGuard(workspace_root=self.workspace_dir, authorized_spend_usd=0.0)
        self.tools = ToolRegistry(self.guard)
        self.agent = get_default_worker1_definition()

    def tearDown(self):
        self.store.close()
        shutil.rmtree(self.temp_dir, ignore_errors=True)

    def test_worker1_successful_multi_step_execution(self):
        # Scripted 2-step model response:
        # Step 1: writes a file
        # Step 2: verifies file and completes
        scripted_responses = [
            CompletionResponse(
                text="Drafting greeting file.",
                plan="Plan: Write greeting.txt with verified message",
                tool_calls=[
                    ToolCall(
                        call_id="call-write-1",
                        tool_name="write_file",
                        arguments={"path": "greeting.txt", "content": "ZaxterLab Phase 1 Active\n"},
                    )
                ],
                is_final=False,
                evaluation="File written, need to verify.",
                token_usage=TokenUsage(20, 30, 50, 0.0),
            ),
            CompletionResponse(
                text="Verified greeting.txt successfully.",
                plan="Plan: Read greeting.txt and complete task",
                tool_calls=[
                    ToolCall(
                        call_id="call-read-1",
                        tool_name="read_file",
                        arguments={"path": "greeting.txt"},
                    )
                ],
                is_final=True,
                evaluation="Task objectives verified and fulfilled.",
                token_usage=TokenUsage(25, 35, 60, 0.0),
            ),
        ]

        model = MockProvider(responses=scripted_responses)
        engine = Worker1Engine(self.agent, model, self.guard, self.store, self.tools)

        task = Task(
            task_id="task-e2e-001",
            title="Create Verified File",
            description="Write greeting.txt and verify its contents.",
        )
        self.store.save_task(task)

        # Execute
        session = engine.execute_task(task)

        # 1. Verify Session & Task State
        self.assertEqual(session.status, SessionStatus.COMPLETED)
        self.assertEqual(session.current_step, 2)
        self.assertEqual(session.total_token_usage.total_tokens, 110)
        self.assertEqual(session.total_token_usage.estimated_cost_usd, 0.0)

        persisted_task = self.store.get_task("task-e2e-001")
        self.assertIsNotNone(persisted_task)
        self.assertEqual(persisted_task.status, TaskStatus.COMPLETED)
        self.assertEqual(persisted_task.result_summary, "Verified greeting.txt successfully.")

        # 2. Verify File Creation on disk in Workspace
        target_file = os.path.join(self.workspace_dir, "greeting.txt")
        self.assertTrue(os.path.exists(target_file))
        with open(target_file, "r", encoding="utf-8") as f:
            content = f.read()
        self.assertEqual(content, "ZaxterLab Phase 1 Active\n")

        # 3. Verify Step Traces
        traces = self.store.get_step_traces(session.session_id)
        self.assertEqual(len(traces), 2)

        # Trace 1 checks (Write)
        self.assertEqual(traces[0].step_number, 1)
        self.assertIn("Task: Create Verified File", traces[0].observation)
        self.assertEqual(traces[0].tool_calls[0].tool_name, "write_file")
        self.assertTrue(traces[0].tool_results[0].success)

        # Trace 2 checks (Read and Evaluate)
        self.assertEqual(traces[1].step_number, 2)
        self.assertEqual(traces[1].tool_calls[0].tool_name, "read_file")
        self.assertTrue(traces[1].tool_results[0].success)
        self.assertEqual(traces[1].tool_results[0].output, "ZaxterLab Phase 1 Active\n")
        self.assertEqual(traces[1].evaluation, "Task objectives verified and fulfilled.")

        # 4. Verify Audit Logs
        audit_events = self.store.get_audit_logs()
        event_types = [e["event_type"] for e in audit_events]
        self.assertIn("SESSION_CREATED", event_types)
        self.assertIn("STEP_EXECUTED", event_types)
        self.assertIn("TASK_COMPLETED", event_types)


if __name__ == "__main__":
    unittest.main()
