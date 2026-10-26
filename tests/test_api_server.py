"""Integration tests for ZaxterLab HTTP API server."""

import json
import os
import shutil
import socket
import tempfile
import unittest
from urllib.error import HTTPError
from urllib.request import Request, urlopen

from zaxterlab.api.server import create_api_server
from zaxterlab.contracts.types import (
    PermissionTier,
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


def find_free_port() -> int:
    """Find an available local TCP port."""
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.bind(("127.0.0.1", 0))
        return s.getsockname()[1]


class TestAPIServer(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.mkdtemp(prefix="zaxterlab_api_test_")
        self.db_path = os.path.join(self.temp_dir, "api_test.db")
        self.workspace_dir = os.path.join(self.temp_dir, "workspace")
        os.makedirs(self.workspace_dir, exist_ok=True)

        self.store = SQLiteStore(self.db_path)
        self.guard = BoundaryGuard(workspace_root=self.workspace_dir, authorized_spend_usd=0.0)
        self.tools = ToolRegistry(self.guard)
        self.agent = get_default_worker1_definition()

        # Seed mock provider
        self.mock_provider = MockProvider()
        self.engine = Worker1Engine(self.agent, self.mock_provider, self.guard, self.store, self.tools)

        self.port = find_free_port()
        self.base_url = f"http://127.0.0.1:{self.port}"
        self.server = create_api_server(
            store=self.store,
            engine=self.engine,
            boundary_guard=self.guard,
            host="127.0.0.1",
            port=self.port,
        )
        self.server.start_in_thread()

    def tearDown(self):
        self.server.stop()
        self.store.close()
        shutil.rmtree(self.temp_dir, ignore_errors=True)

    def _http_get(self, path: str) -> tuple[int, dict]:
        url = f"{self.base_url}{path}"
        req = Request(url, method="GET")
        try:
            with urlopen(req) as resp:
                data = json.loads(resp.read().decode("utf-8"))
                return resp.status, data
        except HTTPError as err:
            data = json.loads(err.read().decode("utf-8"))
            return err.code, data

    def _http_post(self, path: str, payload: dict) -> tuple[int, dict]:
        url = f"{self.base_url}{path}"
        req = Request(
            url,
            data=json.dumps(payload).encode("utf-8"),
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        try:
            with urlopen(req) as resp:
                data = json.loads(resp.read().decode("utf-8"))
                return resp.status, data
        except HTTPError as err:
            data = json.loads(err.read().decode("utf-8"))
            return err.code, data

    def test_health_endpoint(self):
        status, body = self._http_get("/api/health")
        self.assertEqual(status, 200)
        self.assertEqual(body["status"], "healthy")
        self.assertEqual(body["worker"]["name"], "Reem")
        self.assertEqual(body["spend_guard"]["authorized_spend_usd"], 0.0)
        self.assertTrue(body["spend_guard"]["spend_locked"])
        self.assertTrue(body["workspace"]["sandboxed"])

    def test_task_lifecycle_api(self):
        # 1. Create Task
        status, create_res = self._http_post(
            "/api/tasks",
            {"title": "Test Task via API", "description": "Write and test", "input_context": {"env": "test"}},
        )
        self.assertEqual(status, 201)
        task_id = create_res["task"]["task_id"]
        self.assertEqual(create_res["task"]["title"], "Test Task via API")
        self.assertEqual(create_res["task"]["status"], "SUBMITTED")

        # 2. List Tasks
        status, list_res = self._http_get("/api/tasks")
        self.assertEqual(status, 200)
        self.assertTrue(any(t["task_id"] == task_id for t in list_res["tasks"]))

        # 3. Get Task Details
        status, detail_res = self._http_get(f"/api/tasks/{task_id}")
        self.assertEqual(status, 200)
        self.assertEqual(detail_res["task"]["task_id"], task_id)

        # 4. Execute Task (mock provider produces default final completion)
        status, exec_res = self._http_post(f"/api/tasks/{task_id}/execute", {})
        self.assertEqual(status, 200)
        self.assertEqual(exec_res["task"]["status"], "COMPLETED")
        self.assertEqual(exec_res["session"]["status"], "COMPLETED")
        self.assertEqual(len(exec_res["session"]["step_traces"]), 1)

    def test_workspace_files_api_and_traversal_protection(self):
        # Create a safe file in workspace
        safe_file = os.path.join(self.workspace_dir, "test_file.txt")
        with open(safe_file, "w", encoding="utf-8") as f:
            f.write("Hello from workspace")

        # 1. List files
        status, list_res = self._http_get("/api/workspace/files")
        self.assertEqual(status, 200)
        filenames = [e["name"] for e in list_res["entries"]]
        self.assertIn("test_file.txt", filenames)

        # 2. Read file content
        status, content_res = self._http_get("/api/workspace/file-content?path=test_file.txt")
        self.assertEqual(status, 200)
        self.assertEqual(content_res["content"], "Hello from workspace")

        # 3. Path traversal attack blocked
        status, err_res = self._http_get("/api/workspace/file-content?path=../../etc/passwd")
        self.assertEqual(status, 403)
        self.assertEqual(err_res["error"]["code"], "SECURITY_VIOLATION")

    def test_audit_logs_endpoint(self):
        status, logs_res = self._http_get("/api/audit-logs")
        self.assertEqual(status, 200)
        self.assertIn("audit_logs", logs_res)

    def test_completion_endpoint(self):
        status, comp_res = self._http_get("/api/completion")
        self.assertEqual(status, 200)
        self.assertIn("overall_completion_pct", comp_res)
        self.assertIn("pillars", comp_res)
        self.assertIn("capabilities", comp_res)
        self.assertEqual(comp_res["overall_completion_pct"], 94)

    def test_pipeline_and_telemetry_api(self):
        # 1. Create task 1
        status, t1_res = self._http_post("/api/tasks", {"title": "Task 1", "description": "Desc 1"})
        self.assertEqual(status, 201)
        t1_id = t1_res["task"]["task_id"]

        # 2. Create task 2 depending on task 1
        status, t2_res = self._http_post(
            "/api/tasks",
            {"title": "Task 2", "description": "Desc 2", "depends_on": [t1_id]},
        )
        self.assertEqual(status, 201)
        t2_id = t2_res["task"]["task_id"]

        # 3. Run pipeline
        status, pipe_res = self._http_post("/api/pipeline/run", {"task_ids": [t1_id, t2_id]})
        self.assertEqual(status, 200)
        self.assertEqual(pipe_res["total"], 2)
        self.assertEqual(pipe_res["completed"], 2)

        # 4. Check telemetry endpoint
        status, telem_res = self._http_get("/api/telemetry")
        self.assertEqual(status, 200)
        self.assertIn("token_economics", telem_res)
        self.assertIn("auditor_efficiency", telem_res)
        self.assertTrue(telem_res["token_economics"]["spend_bound_satisfied"])

    def test_evaluator_api_endpoints(self):
        # 1. Check evaluator status
        status, eval_res = self._http_get("/api/evaluator/status")
        self.assertEqual(status, 200)
        self.assertIn("decision", eval_res)
        self.assertIn("telemetry", eval_res)

        # 2. Trigger proposal by seeding auditor rejections in store
        self.store.log_audit("AUDITOR_REJECTED", "task_fail_1", {"err": "test fail"})
        self.store.log_audit("AUDITOR_REJECTED", "task_fail_2", {"err": "test fail"})

        status, eval_res = self._http_get("/api/evaluator/status")
        self.assertEqual(status, 200)
        self.assertEqual(eval_res["decision"], "PROPOSE_SPECIALIST")
        proposal_id = eval_res["proposal"]["proposal_id"]

        # 3. List proposals
        status, prop_list = self._http_get("/api/evaluator/proposals")
        self.assertEqual(status, 200)
        self.assertGreaterEqual(len(prop_list["proposals"]), 1)

        # 4. Approve proposal via API
        status, app_res = self._http_post(
            f"/api/evaluator/proposals/{proposal_id}/approve",
            {"approver": "Zak", "reason": "Approved in API test"},
        )
        self.assertEqual(status, 200)
        self.assertEqual(app_res["proposal"]["status"], "APPROVED")

    def test_static_frontend_serving(self):
        # 1. Root serves index.html
        req = Request(f"{self.base_url}/", method="GET")
        with urlopen(req) as resp:
            self.assertEqual(resp.status, 200)
            self.assertIn("text/html", resp.headers.get("Content-Type", ""))
            content = resp.read().decode("utf-8")
            self.assertIn("<title>ZaxterLab", content)

        # 2. app.js is served
        req_js = Request(f"{self.base_url}/app.js", method="GET")
        with urlopen(req_js) as resp:
            self.assertEqual(resp.status, 200)
            self.assertIn("javascript", resp.headers.get("Content-Type", ""))
            content_js = resp.read().decode("utf-8")
            self.assertIn("ZaxterLab Operations Dashboard", content_js)

    def test_saas_project_launch_and_workspace_artifacts(self):
        """Test launching an end-to-end SaaS project generates real departmental artifacts in workspace."""
        payload = {
            "name": "SaaS Test Billing API",
            "domain": "Fintech / B2B SaaS",
            "requirements": "Multi-tenant auth tokens, subscription plan tiers, and usage quotas.",
        }
        status, res = self._http_post("/api/project/saas", payload)
        self.assertEqual(status, 201)
        self.assertTrue(res["success"])
        self.assertEqual(res["project_name"], "SaaS Test Billing API")
        self.assertTrue(res["qa_verified"])
        self.assertEqual(res["spend_usd"], 0.0)

        # Verify all 5 files were created in the sandboxed workspace
        expected_files = ["PRD.md", "ARCHITECTURE.md", "app.py", "test_suite.py", "AUDIT_REPORT.md"]
        self.assertEqual(res["files_created"], expected_files)

        slug = res["project_slug"]
        project_dir = os.path.join(self.workspace_dir, "projects", slug)
        self.assertTrue(os.path.isdir(project_dir))

        for filename in expected_files:
            file_path = os.path.join(project_dir, filename)
            self.assertTrue(os.path.isfile(file_path), f"File {filename} was not found at {file_path}")

        # Verify reading PRD file content via API
        status, file_res = self._http_get(f"/api/workspace/file-content?path=projects/{slug}/PRD.md")
        self.assertEqual(status, 200)
        self.assertIn("Product Requirements Document", file_res["content"])
        self.assertIn("Hadi (Planning & Requirements Specialist)", file_res["content"])

        # Verify reading AUDIT_REPORT via API
        status, audit_res = self._http_get(f"/api/workspace/file-content?path=projects/{slug}/AUDIT_REPORT.md")
        self.assertEqual(status, 200)
        self.assertIn("Chief Auditor: Zaks", audit_res["content"])
        self.assertIn("APPROVED", audit_res["content"])

    def test_internal_transformation_initiative_and_immersive_world_api(self):
        """Verify Section 18: Internal Company Project — ZaxterLab's Own Immersive Transformation."""
        # 1. Trigger internal transformation initiative via API
        status, init_res = self._http_post("/api/projects/internal-transformation", {"force_rerun": True})
        self.assertEqual(status, 200)
        project = init_res["project"]
        self.assertEqual(project["project_id"], "proj_zaxterlab_immersive_world")
        self.assertEqual(project["project_type"], "INTERNAL_INITIATIVE")
        self.assertEqual(project["priority"], "STRATEGIC")
        self.assertEqual(project["status"], "COMPLETED")
        self.assertEqual(len(init_res["tasks"]), 7)

        # 2. Verify all 7 departmental artifacts exist on disk in workspace/projects/zaxterlab-immersive-world/
        expected_artifacts = [
            "01_INITIATIVE_PRD_AND_DAG.md",
            "02_WORLD_TECHNICAL_ARCHITECTURE.md",
            "03_LIGHT_MODE_DESIGN_SYSTEM.md",
            "04_MASCOT_AND_MOTION_SPEC.md",
            "05_FRONTEND_IMPLEMENTATION_LOG.md",
            "06_QA_VERIFICATION_SUITE.py",
            "07_CHIEF_AUDITOR_CLEARANCE.md",
        ]
        init_dir = os.path.join(self.workspace_dir, "projects", "zaxterlab-immersive-world")
        self.assertTrue(os.path.isdir(init_dir))
        for fname in expected_artifacts:
            self.assertTrue(os.path.isfile(os.path.join(init_dir, fname)), f"Missing {fname}")

        # 3. Verify /api/world/state returns typed Event-to-Visual-World adapter
        status, world = self._http_get("/api/world/state")
        self.assertEqual(status, 200)
        self.assertEqual(world["theme_mode"], "LIGHT_MODE_MANDATORY")
        self.assertIn("brain", world)
        self.assertEqual(len(world["brain"]["supported_states"]), 11)
        self.assertTrue(world["brain"]["spend_guard"]["locked"])
        self.assertEqual(world["brain"]["spend_guard"]["authorized_spend_usd"], 0.0)

        # 4. Verify Musab was dynamically spawned and registered alongside existing workforce
        specialist_names = {s["name"] for s in world["specialists"]}
        for expected_name in ["Hadi", "Sirfaraz", "Musab", "Hania", "Reem", "Aroosh", "Zaks"]:
            self.assertIn(expected_name, specialist_names)

        # 5. Verify /api/projects and /api/projects/{id}
        status, projs_res = self._http_get("/api/projects?project_type=INTERNAL_INITIATIVE")
        self.assertEqual(status, 200)
        self.assertTrue(any(p["project_id"] == "proj_zaxterlab_immersive_world" for p in projs_res["projects"]))

        status, proj_detail = self._http_get("/api/projects/proj_zaxterlab_immersive_world")
        self.assertEqual(status, 200)
        self.assertEqual(len(proj_detail["tasks"]), 7)

        # 6. Verify static serving of Studio 3D assets, SVG rigs, and light-mode design tokens
        for asset_path, expected_mime in [
            ("/design-tokens.css", "text/css"),
            ("/assets/ASSET_MANIFEST.json", "application/json"),
            ("/assets/brain-core.svg", "image/svg+xml"),
            ("/assets/brain-entity.jpg", "image/jpeg"),
            ("/assets/mascot-showcase.jpg", "image/jpeg"),
        ]:
            req = Request(f"{self.base_url}{asset_path}", method="GET")
            with urlopen(req) as resp:
                self.assertEqual(resp.status, 200)
                self.assertIn(expected_mime, resp.headers.get("Content-Type", ""))
                self.assertGreater(len(resp.read()), 100)

    def test_dynamic_specialist_spawning_endpoint(self):
        """Verify dynamic specialist spawning and runtime persistence."""
        status, spawn_res = self._http_post(
            "/api/specialists/spawn",
            {
                "name": "Tariq",
                "role_title": "Telemetry & Reliability Specialist",
                "department": "Operations & Governance",
                "capabilities": ["reliability_engineering", "metrics_analysis"],
                "justification": "Needed for specialized latency profiling.",
                "auto_approve": True,
                "approver": "Zak",
            },
        )
        self.assertEqual(status, 201)
        self.assertEqual(spawn_res["specialist"]["name"], "Tariq")
        self.assertEqual(spawn_res["specialist"]["lifecycle_state"], "ACTIVE")

        status, list_res = self._http_get("/api/specialists")
        self.assertEqual(status, 200)
        self.assertTrue(any(s["name"] == "Tariq" for s in list_res["specialists"]))


if __name__ == "__main__":
    unittest.main()
