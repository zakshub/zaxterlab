"""Hermetic unit tests for ZaxterLab CLI (Form 1: Terminal / CLI Interface)."""

import io
import json
import shutil
import tempfile
import unittest
from contextlib import redirect_stdout
from pathlib import Path

from zaxterlab.cli import main


class TestCLIInterface(unittest.TestCase):
    """Hermetic test suite verifying all CLI commands, formatting, and JSON piping."""

    def setUp(self) -> None:
        self.tmp_dir = tempfile.mkdtemp(prefix="zaxterlab_cli_test_")
        self.db_path = str(Path(self.tmp_dir) / "test.db")
        self.ws_path = str(Path(self.tmp_dir) / "workspace")

    def tearDown(self) -> None:
        shutil.rmtree(self.tmp_dir, ignore_errors=True)

    def _run_cli(self, args: list[str]) -> tuple[int, str]:
        full_args = ["--db", self.db_path, "--workspace", self.ws_path] + args
        f = io.StringIO()
        with redirect_stdout(f):
            ret = main(full_args)
        return ret, f.getvalue()

    def test_cli_status_text_and_json(self) -> None:
        ret, out = self._run_cli(["status"])
        self.assertEqual(ret, 0)
        self.assertIn("ZAXTERLAB — AI Company Operating System Status", out)
        self.assertIn("healthy", out)
        self.assertIn("USD $0.00", out)

        ret_json, out_json = self._run_cli(["status", "--json"])
        self.assertEqual(ret_json, 0)
        data = json.loads(out_json)
        self.assertEqual(data["status"], "healthy")
        self.assertEqual(data["spend_guard"]["authorized_spend_usd"], 0.0)
        self.assertEqual(data["spend_guard"]["cumulative_spent_usd"], 0.0)

    def test_cli_task_lifecycle_create_and_exec(self) -> None:
        # 1. Create task
        ret, out = self._run_cli([
            "task", "create",
            "--title", "CLI Unit Task",
            "--desc", "Testing task creation via CLI",
            "--specialist", "Reem",
            "--json"
        ])
        self.assertEqual(ret, 0)
        created_data = json.loads(out)
        task_id = created_data["task"]["task_id"]
        self.assertTrue(task_id.startswith("task_"))

        # 2. List tasks
        ret, out = self._run_cli(["task", "list"])
        self.assertEqual(ret, 0)
        self.assertIn(task_id, out)
        self.assertIn("CLI Unit Task", out)

        # 3. Execute task
        ret, out = self._run_cli(["task", "exec", task_id])
        self.assertEqual(ret, 0)
        self.assertIn("Execution Finished", out)
        self.assertIn("COMPLETED", out)

        # 4. Show task
        ret, out = self._run_cli(["task", "show", task_id])
        self.assertEqual(ret, 0)
        self.assertIn(task_id, out)
        self.assertIn("COMPLETED", out)

    def test_cli_pipeline_run(self) -> None:
        ret, out = self._run_cli(["pipeline", "run", "--module", "order_service"])
        self.assertEqual(ret, 0)
        self.assertIn("Pipeline Execution Finished", out)
        self.assertIn("Completed Tasks: 2", out)
        self.assertIn("Failed Tasks:    0", out)

    def test_cli_specialists_list_and_spawn(self) -> None:
        ret, out = self._run_cli(["specialist", "list"])
        self.assertEqual(ret, 0)
        self.assertIn("Reem", out)
        self.assertIn("Zaks", out)
        self.assertIn("Sirfaraz", out)

        ret, out = self._run_cli([
            "specialist", "spawn",
            "--name", "Tariq",
            "--role", "Penetration Tester",
            "--dept", "Security",
            "--gap", "Specialized fuzzing required",
            "--approve"
        ])
        self.assertEqual(ret, 0)
        self.assertIn("spawned & registered immediately", out)

        ret, out = self._run_cli(["specialist", "list", "--json"])
        self.assertEqual(ret, 0)
        specs = json.loads(out)
        names = [s["name"] for s in specs]
        self.assertIn("Tariq", names)

    def test_cli_saas_project_generation(self) -> None:
        ret, out = self._run_cli([
            "project", "saas",
            "--name", "CloudBilling",
            "--domain", "Fintech SaaS",
            "--reqs", "Automated recurring invoice generation"
        ])
        self.assertEqual(ret, 0)
        self.assertIn("SaaS Project Generated Successfully!", out)
        self.assertIn("PRD.md", out)
        self.assertIn("ARCHITECTURE.md", out)
        self.assertIn("app.py", out)
        self.assertIn("test_suite.py", out)
        self.assertIn("AUDIT_REPORT.md", out)

        ret, out = self._run_cli(["project", "list"])
        self.assertEqual(ret, 0)
        self.assertIn("CloudBilling", out)

    def test_cli_audit_trail(self) -> None:
        # Trigger an action to create audit logs
        self._run_cli(["status"])
        ret, out = self._run_cli(["audit", "list", "--limit", "10"])
        self.assertEqual(ret, 0)
        self.assertIn("Immutable SQLite Audit Trail", out)


if __name__ == "__main__":
    unittest.main()
