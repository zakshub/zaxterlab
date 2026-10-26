"""Hermetic unit tests for SpecializationEvaluator and Adaptive Scaling."""

import unittest

from zaxterlab.contracts.types import (
    PermissionTier,
    ProposalStatus,
    Task,
    TaskStatus,
    TradeoffChoice,
    utc_now_iso,
)
from zaxterlab.db.sqlite import SQLiteStore
from zaxterlab.engine.evaluator import SpecializationEvaluator


class TestSpecializationEvaluator(unittest.TestCase):
    def setUp(self):
        self.store = SQLiteStore(":memory:")
        self.evaluator = SpecializationEvaluator(self.store)

    def tearDown(self):
        self.store.close()

    def test_idle_or_light_workload_recommends_prompt_or_reuse(self):
        """No specialist should be spawned if queue is light."""
        result = self.evaluator.evaluate_workload()
        self.assertIn(
            result["decision"],
            [TradeoffChoice.PROMPT_TOOL_REFINEMENT.value, TradeoffChoice.REUSE_EXISTING_WORKER.value],
        )
        self.assertIsNone(result["proposal"])

    def test_auditor_rejections_trigger_aroosh_qa_proposal(self):
        """Repeated test/audit failures trigger a proposal for Aroosh (QA)."""
        # Seed 2 auditor rejection logs
        self.store.log_audit("AUDITOR_REJECTED", "task_01", {"reason": "Test assertion failure"})
        self.store.log_audit("AUDITOR_REJECTED", "task_02", {"reason": "Missing output artifact"})

        result = self.evaluator.evaluate_workload()
        self.assertEqual(result["decision"], TradeoffChoice.PROPOSE_SPECIALIST.value)
        self.assertIsNotNone(result["proposal"])

        proposal = result["proposal"]
        self.assertEqual(proposal["target_role_name"], "Aroosh")
        self.assertEqual(proposal["target_role_title"], "Quality Assurance")
        self.assertEqual(proposal["archetype"], "Shuri")
        self.assertEqual(proposal["recommended_permission_tier"], PermissionTier.TIER_1_SAFE.value)
        self.assertEqual(proposal["status"], ProposalStatus.PENDING_APPROVAL.value)

        # Verify trade-off analysis structure
        tradeoff = proposal["tradeoff_analysis"]
        self.assertIn("option_1_prompt_refinement", tradeoff)
        self.assertIn("option_2_worker_reuse", tradeoff)
        self.assertIn("option_3_specialist_spawning", tradeoff)

        # Ensure proposal is saved in SQLite
        saved = self.store.get_proposal(proposal["proposal_id"])
        self.assertIsNotNone(saved)
        self.assertEqual(saved.proposal_id, proposal["proposal_id"])

    def test_queue_backlog_triggers_hadi_planning_proposal(self):
        """Sustained queue backlog >= 4 triggers proposal for Hadi (Planning)."""
        for i in range(5):
            t = Task(
                task_id=f"task_backlog_{i}",
                title=f"Queued Task {i}",
                description="Long backlog item",
                status=TaskStatus.QUEUED,
            )
            self.store.save_task(t)

        result = self.evaluator.evaluate_workload()
        self.assertEqual(result["decision"], TradeoffChoice.PROPOSE_SPECIALIST.value)
        self.assertIsNotNone(result["proposal"])

        proposal = result["proposal"]
        self.assertEqual(proposal["target_role_name"], "Hadi")
        self.assertEqual(proposal["target_role_title"], "Planning and Strategy")
        self.assertEqual(proposal["archetype"], "Peter Parker")

    def test_boundary_violations_trigger_zara_security_proposal(self):
        """Multiple boundary violations trigger proposal for Zara (Security & Risk)."""
        self.store.log_audit("BOUNDARY_VIOLATION", "sess_01", {"path": "../../etc/passwd"})
        self.store.log_audit("BOUNDARY_VIOLATION", "sess_02", {"path": "../sensitive.key"})

        result = self.evaluator.evaluate_workload()
        self.assertEqual(result["decision"], TradeoffChoice.PROPOSE_SPECIALIST.value)
        proposal = result["proposal"]
        self.assertEqual(proposal["target_role_name"], "Zara")
        self.assertEqual(proposal["target_role_title"], "Security and Risk")

    def test_owner_approval_circuit(self):
        """Spawning proposals require explicit human owner approval before activation."""
        self.store.log_audit("AUDITOR_REJECTED", "task_01", {"reason": "Test fail 1"})
        self.store.log_audit("AUDITOR_REJECTED", "task_02", {"reason": "Test fail 2"})

        res = self.evaluator.evaluate_workload()
        proposal_id = res["proposal"]["proposal_id"]

        # 1. Proposal starts PENDING_APPROVAL
        prop = self.store.get_proposal(proposal_id)
        self.assertEqual(prop.status, ProposalStatus.PENDING_APPROVAL)

        # 2. Owner approves
        approved = self.evaluator.approve_proposal(proposal_id, approver="Zak", reason="Approved for testing automation")
        self.assertEqual(approved.status, ProposalStatus.APPROVED)
        self.assertIn("Zak", approved.decision_reason)
        self.assertIsNotNone(approved.decided_at)

        # Verify audit log recorded
        logs = self.store.get_audit_logs(entity_id=proposal_id)
        event_types = [l["event_type"] for l in logs]
        self.assertIn("SPECIALIST_ROLE_ACTIVATED", event_types)

    def test_owner_rejection_circuit(self):
        """Owner rejection marks proposal REJECTED and leaves role dormant."""
        self.store.log_audit("AUDITOR_REJECTED", "task_01", {"reason": "Test fail 1"})
        self.store.log_audit("AUDITOR_REJECTED", "task_02", {"reason": "Test fail 2"})

        res = self.evaluator.evaluate_workload()
        proposal_id = res["proposal"]["proposal_id"]

        rejected = self.evaluator.reject_proposal(proposal_id, decider="Zak", reason="Not justified yet")
        self.assertEqual(rejected.status, ProposalStatus.REJECTED)

        logs = self.store.get_audit_logs(entity_id=proposal_id)
        event_types = [l["event_type"] for l in logs]
        self.assertIn("SPAWNING_PROPOSAL_REJECTED", event_types)


if __name__ == "__main__":
    unittest.main()
