"""Unit tests for agent session suspension and resumption."""

import os
import shutil
import tempfile
import unittest

from zaxterlab.contracts.types import (
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


class TestSuspensionResumption(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.mkdtemp(prefix="zaxterlab_suspend_")
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

    def test_suspend_and_resume_lifecycle(self):
        # Step 1 response
        step1_resp = CompletionResponse(
            text="Step 1 completed",
            plan="Plan: Initialize workspace file",
            tool_calls=[
                ToolCall(
                    call_id="call-init",
                    tool_name="write_file",
                    arguments={"path": "state.txt", "content": "Initial State\n"},
                )
            ],
            is_final=False,
            evaluation="Partial progress. Awaiting next phase.",
            token_usage=TokenUsage(15, 20, 35, 0.0),
        )

        model1 = MockProvider(responses=[step1_resp])
        engine1 = Worker1Engine(self.agent, model1, self.guard, self.store, self.tools)

        task = Task(
            task_id="task-suspend-01",
            title="Suspension Test Task",
            description="Execute one step, suspend, and resume later.",
        )
        self.store.save_task(task)

        # 1. Execute only 1 step
        session = engine1.execute_task(task, max_steps_per_run=1)
        self.assertEqual(session.current_step, 1)

        # 2. Suspend session
        session = engine1.suspend_session(task, session)
        self.assertEqual(session.status, SessionStatus.SUSPENDED)
        self.assertEqual(task.status, TaskStatus.SUSPENDED)

        # Verify state in SQLite
        persisted_sess = self.store.get_session(session.session_id)
        self.assertIsNotNone(persisted_sess)
        self.assertEqual(persisted_sess.status, SessionStatus.SUSPENDED)
        self.assertEqual(persisted_sess.current_step, 1)

        persisted_task = self.store.get_task("task-suspend-01")
        self.assertIsNotNone(persisted_task)
        self.assertEqual(persisted_task.status, TaskStatus.SUSPENDED)

        # Check audit log for suspension
        audit_events = self.store.get_audit_logs(session.session_id)
        self.assertTrue(any(e["event_type"] == "SESSION_SUSPENDED" for e in audit_events))

        # 3. Resume session with fresh engine instance (simulating worker restart)
        step2_resp = CompletionResponse(
            text="Resumed and finished task.",
            plan="Plan: Append final note and complete",
            tool_calls=[
                ToolCall(
                    call_id="call-append",
                    tool_name="write_file",
                    arguments={"path": "state.txt", "content": "Resumed State\n", "append": True},
                )
            ],
            is_final=True,
            evaluation="Completed post-resumption.",
            token_usage=TokenUsage(20, 25, 45, 0.0),
        )

        model2 = MockProvider(responses=[step2_resp])
        engine2 = Worker1Engine(self.agent, model2, self.guard, self.store, self.tools)

        resumed_session = engine2.execute_task(task, resume_session_id=session.session_id)

        # 4. Verify completed state
        self.assertEqual(resumed_session.status, SessionStatus.COMPLETED)
        self.assertEqual(resumed_session.current_step, 2)
        self.assertEqual(resumed_session.total_token_usage.total_tokens, 80)

        # Verify on-disk file
        file_path = os.path.join(self.workspace_dir, "state.txt")
        with open(file_path, "r", encoding="utf-8") as f:
            content = f.read()
        self.assertEqual(content, "Initial State\nResumed State\n")

        # Verify audit logs include resumption
        audit_events_post = self.store.get_audit_logs(session.session_id)
        self.assertTrue(any(e["event_type"] == "SESSION_RESUMED" for e in audit_events_post))


if __name__ == "__main__":
    unittest.main()
