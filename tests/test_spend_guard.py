"""Unit tests for SpendGuard and zero-spend boundary enforcement."""

import unittest
from zaxterlab.contracts.types import AgentDefinition, PermissionTier, Task, TaskStatus
from zaxterlab.db.sqlite import SQLiteStore
from zaxterlab.engine.worker import Worker1Engine
from zaxterlab.models.mock import MockProvider
from zaxterlab.security.guard import BoundaryGuard, SpendGuard, SpendViolationError
from zaxterlab.tools.registry import ToolRegistry


class TestSpendGuard(unittest.TestCase):
    def test_default_zero_spend_allows_zero(self):
        guard = SpendGuard(authorized_spend_usd=0.0)
        # 0.0 spend is completely valid
        guard.validate_cost(0.0)
        guard.record_cost(0.0)
        self.assertEqual(guard.cumulative_spent_usd, 0.0)

    def test_rejection_of_positive_cost(self):
        guard = SpendGuard(authorized_spend_usd=0.0)
        with self.assertRaises(SpendViolationError) as ctx:
            guard.validate_cost(0.000001)

        self.assertIn("Spend boundary violation", str(ctx.exception))
        self.assertIn("Default is $0.00", str(ctx.exception))

    def test_rejection_of_negative_cost(self):
        guard = SpendGuard(authorized_spend_usd=0.0)
        with self.assertRaises(SpendViolationError):
            guard.validate_cost(-0.05)

    def test_engine_spend_guard_integration(self):
        # Setup engine with a model simulating cost
        store = SQLiteStore(":memory:")
        guard = BoundaryGuard(workspace_root="/tmp/zaxterlab_test_ws", authorized_spend_usd=0.0)
        tools = ToolRegistry(guard)
        agent = AgentDefinition(
            agent_id="reem-test",
            name="Reem",
            role="Worker",
            description="Test worker",
            allowed_tools=["read_file"],
            permission_tier=PermissionTier.TIER_2_REVERSIBLE,
        )
        costly_model = MockProvider(simulated_cost_usd=0.005)
        engine = Worker1Engine(agent, costly_model, guard, store, tools)

        task = Task(task_id="task-cost-1", title="Expensive task", description="Run expensive step")
        store.save_task(task)

        # Execution must fail and block the task
        with self.assertRaises(SpendViolationError):
            engine.execute_task(task)

        persisted_task = store.get_task("task-cost-1")
        self.assertIsNotNone(persisted_task)
        self.assertEqual(persisted_task.status, TaskStatus.BLOCKED)
        self.assertIn("Blocked by SpendGuard", persisted_task.result_summary)

        # Check audit log recorded the violation
        audit_logs = store.get_audit_logs("task-cost-1")
        self.assertTrue(any(l["event_type"] == "SPEND_VIOLATION_HALT" for l in audit_logs))
        store.close()


if __name__ == "__main__":
    unittest.main()
