"""Unit tests for WorkerPerformanceEvaluator and execution telemetry."""

import unittest

from zaxterlab.contracts.types import (
    Session,
    SessionStatus,
    Task,
    TaskStatus,
    TokenUsage,
)
from zaxterlab.db.sqlite import SQLiteStore
from zaxterlab.engine.telemetry import WorkerPerformanceEvaluator


class TestPerformanceTelemetry(unittest.TestCase):
    def setUp(self):
        self.store = SQLiteStore(":memory:")
        self.evaluator = WorkerPerformanceEvaluator(self.store)

    def tearDown(self):
        self.store.close()

    def test_initial_telemetry(self):
        """Initial database state returns nominal baseline telemetry."""
        telem = self.evaluator.compute_telemetry()
        self.assertEqual(telem["summary"]["total_tasks_tracked"], 0)
        self.assertEqual(telem["token_economics"]["cumulative_spend_usd"], 0.0)
        self.assertTrue(telem["token_economics"]["spend_bound_satisfied"])
        self.assertEqual(telem["auditor_efficiency"]["first_pass_approval_pct"], 100.0)

    def test_token_and_status_accumulation(self):
        """Tokens and task statuses accumulate accurately across tasks."""
        t1 = Task(task_id="t1", title="Task 1", description="desc", status=TaskStatus.COMPLETED)
        t2 = Task(task_id="t2", title="Task 2", description="desc", status=TaskStatus.BLOCKED)
        self.store.save_task(t1)
        self.store.save_task(t2)

        s1 = Session(
            session_id="s1",
            task_id="t1",
            agent_id="reem-worker-1",
            status=SessionStatus.COMPLETED,
            total_token_usage=TokenUsage(prompt_tokens=50, completion_tokens=30, total_tokens=80),
        )
        s2 = Session(
            session_id="s2",
            task_id="t2",
            agent_id="reem-worker-1",
            status=SessionStatus.FAILED,
            total_token_usage=TokenUsage(prompt_tokens=60, completion_tokens=40, total_tokens=100),
        )
        self.store.save_session(s1)
        self.store.save_session(s2)

        telem = self.evaluator.compute_telemetry()
        self.assertEqual(telem["summary"]["total_tasks_tracked"], 2)
        self.assertEqual(telem["summary"]["completed_tasks"], 1)
        self.assertEqual(telem["summary"]["task_completion_rate_pct"], 50.0)
        self.assertEqual(telem["token_economics"]["total_tokens_consumed"], 180)
        self.assertEqual(telem["token_economics"]["prompt_tokens"], 110)
        self.assertEqual(telem["token_economics"]["completion_tokens"], 70)
        self.assertEqual(telem["token_economics"]["cumulative_spend_usd"], 0.0)

    def test_bottleneck_detection(self):
        """Identifies bottlenecks when rejections or blocked tasks occur."""
        t1 = Task(task_id="t1", title="Blocked Task", description="desc", status=TaskStatus.BLOCKED)
        self.store.save_task(t1)

        self.store.log_audit("AUDITOR_REJECTED", "t1", {"reason": "Test fail 1"})
        self.store.log_audit("AUDITOR_REJECTED", "t1", {"reason": "Test fail 2"})
        self.store.log_audit("BOUNDARY_VIOLATION", "s1", {"attempt": "../../escape"})

        telem = self.evaluator.compute_telemetry()
        bottlenecks = telem["governance"]["identified_bottlenecks"]
        self.assertGreaterEqual(len(bottlenecks), 2)
        self.assertTrue(any("rejection" in b.lower() for b in bottlenecks))
        self.assertTrue(any("blocked" in b.lower() for b in bottlenecks))
        self.assertTrue(any("boundary" in b.lower() for b in bottlenecks))


if __name__ == "__main__":
    unittest.main()
