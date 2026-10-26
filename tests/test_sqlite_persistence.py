"""Unit tests for SQLiteStore persistence engine."""

import os
import shutil
import tempfile
import unittest
from pathlib import Path

from zaxterlab.contracts.types import (
    Session,
    SessionStatus,
    StepTrace,
    Task,
    TaskStatus,
    TokenUsage,
    ToolCall,
    ToolResult,
)
from zaxterlab.db.sqlite import SQLiteStore


class TestSQLiteStore(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.mkdtemp(prefix="zaxterlab_db_")
        self.db_path = os.path.join(self.temp_dir, "test_zaxterlab.db")
        self.store = SQLiteStore(self.db_path)

    def tearDown(self):
        self.store.close()
        shutil.rmtree(self.temp_dir, ignore_errors=True)

    def test_task_crud_and_status_filtering(self):
        t1 = Task(
            task_id="t-1",
            title="Task One",
            description="First task",
            status=TaskStatus.QUEUED,
            input_context={"key": "val1"},
        )
        t2 = Task(
            task_id="t-2",
            title="Task Two",
            description="Second task",
            status=TaskStatus.COMPLETED,
            input_context={"key": "val2"},
        )

        self.store.save_task(t1)
        self.store.save_task(t2)

        # Retrieve by ID
        fetched_t1 = self.store.get_task("t-1")
        self.assertIsNotNone(fetched_t1)
        self.assertEqual(fetched_t1.title, "Task One")
        self.assertEqual(fetched_t1.status, TaskStatus.QUEUED)
        self.assertEqual(fetched_t1.input_context["key"], "val1")

        # List all
        all_tasks = self.store.list_tasks()
        self.assertEqual(len(all_tasks), 2)

        # Filter by status
        completed_tasks = self.store.list_tasks(status=TaskStatus.COMPLETED)
        self.assertEqual(len(completed_tasks), 1)
        self.assertEqual(completed_tasks[0].task_id, "t-2")

        # Update task
        t1.status = TaskStatus.RUNNING
        t1.result_summary = "In progress"
        self.store.save_task(t1)
        updated_t1 = self.store.get_task("t-1")
        self.assertEqual(updated_t1.status, TaskStatus.RUNNING)
        self.assertEqual(updated_t1.result_summary, "In progress")

    def test_session_and_step_traces_persistence(self):
        task = Task(task_id="t-session", title="Session Task", description="Testing session storage")
        self.store.save_task(task)

        trace1 = StepTrace(
            step_number=1,
            phase="CYCLE",
            observation="Obs 1",
            plan="Plan 1",
            tool_calls=[ToolCall("c1", "list_dir")],
            tool_results=[ToolResult("c1", "list_dir", True, "['a', 'b']")],
            evaluation="Success step 1",
            token_usage=TokenUsage(10, 20, 30, 0.0),
        )

        session = Session(
            session_id="s-100",
            task_id="t-session",
            agent_id="reem-worker-1",
            status=SessionStatus.ACTIVE,
            current_step=1,
            state_data={"data": 123},
            step_traces=[trace1],
            total_token_usage=TokenUsage(10, 20, 30, 0.0),
        )

        self.store.save_session(session)

        # Retrieve session
        fetched_sess = self.store.get_session("s-100")
        self.assertIsNotNone(fetched_sess)
        self.assertEqual(fetched_sess.session_id, "s-100")
        self.assertEqual(fetched_sess.current_step, 1)
        self.assertEqual(fetched_sess.state_data["data"], 123)
        self.assertEqual(len(fetched_sess.step_traces), 1)
        self.assertEqual(fetched_sess.step_traces[0].plan, "Plan 1")
        self.assertEqual(fetched_sess.step_traces[0].tool_calls[0].tool_name, "list_dir")

        # Add second step trace and re-save
        trace2 = StepTrace(
            step_number=2,
            phase="CYCLE",
            observation="Obs 2",
            plan="Plan 2",
            tool_calls=[],
            tool_results=[],
            evaluation="Finished",
            token_usage=TokenUsage(5, 5, 10, 0.0),
        )
        session.current_step = 2
        session.step_traces.append(trace2)
        session.total_token_usage = session.total_token_usage.add(TokenUsage(5, 5, 10, 0.0))
        self.store.save_session(session)

        # Re-fetch
        fetched_sess2 = self.store.get_session("s-100")
        self.assertEqual(fetched_sess2.current_step, 2)
        self.assertEqual(len(fetched_sess2.step_traces), 2)
        self.assertEqual(fetched_sess2.total_token_usage.total_tokens, 40)

    def test_audit_logs(self):
        self.store.log_audit("EVENT_TEST", "entity-01", {"info": "test audit entry"})
        logs = self.store.get_audit_logs("entity-01")
        self.assertEqual(len(logs), 1)
        self.assertEqual(logs[0]["event_type"], "EVENT_TEST")
        self.assertEqual(logs[0]["details"]["info"], "test audit entry")


if __name__ == "__main__":
    unittest.main()
