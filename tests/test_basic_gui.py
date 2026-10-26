"""Hermetic unit tests for Form 2: Basic Graphical Interface (Desktop GUI & TUI)."""

import shutil
import tempfile
import unittest
from pathlib import Path

from zaxterlab.api.handlers import APIHandlerService
from zaxterlab.api.server import create_api_server
from zaxterlab.cli import build_parser, init_service
from zaxterlab.db.sqlite import SQLiteStore
from zaxterlab.ui.tui import ZaxterLabTUI


class TestBasicGUIInterface(unittest.TestCase):
    """Test suite for Form 2: Basic Graphical Interface & Terminal Curses TUI."""

    def setUp(self) -> None:
        self.tmp_dir = tempfile.mkdtemp(prefix="zaxterlab_basic_gui_test_")
        self.db_path = str(Path(self.tmp_dir) / "test.db")
        self.ws_path = str(Path(self.tmp_dir) / "workspace")
        self.service, self.store = init_service(self.db_path, self.ws_path)

    def tearDown(self) -> None:
        self.store.close()
        shutil.rmtree(self.tmp_dir, ignore_errors=True)

    def test_cli_tui_subcommand_registered(self) -> None:
        parser = build_parser()
        args = parser.parse_args(["tui"])
        self.assertEqual(args.subcommand, "tui")

    def test_tui_state_refresh_and_execution_methods(self) -> None:
        tui = ZaxterLabTUI(service=self.service, store=self.store)
        tui.refresh_data()
        self.assertEqual(tui.cached_health.get("status"), "healthy")
        self.assertEqual(tui.cached_health.get("spend_guard", {}).get("cumulative_spent_usd"), 0.0)
        self.assertGreaterEqual(len(tui.cached_specialists), 3)

        # Execute 2-stage pipeline from TUI
        tui._execute_pipeline()
        self.assertIn("Pipeline complete", tui.status_msg)
        self.assertGreaterEqual(len(tui.cached_tasks), 2)

        # Execute SaaS generation from TUI
        tui._execute_saas()
        self.assertIn("SaaS project", tui.status_msg)
        self.assertGreaterEqual(len(tui.cached_projects), 1)

    def test_basic_gui_static_assets_serving(self) -> None:
        server = create_api_server(
            store=self.store,
            engine=self.service.engine,
            boundary_guard=self.service.boundary_guard,
            host="127.0.0.1",
            port=0,
        )
        port = server.httpd.server_address[1]
        server.start_in_thread()

        try:
            import urllib.request
            # Check basic.html
            res_html = urllib.request.urlopen(f"http://127.0.0.1:{port}/basic.html")
            self.assertEqual(res_html.status, 200)
            content_html = res_html.read().decode("utf-8")
            self.assertIn("ZAXTERLAB GUI", content_html)
            self.assertIn("Form 2: Basic GUI", content_html)

            # Check basic.css
            res_css = urllib.request.urlopen(f"http://127.0.0.1:{port}/basic.css")
            self.assertEqual(res_css.status, 200)
            content_css = res_css.read().decode("utf-8")
            self.assertIn("--gui-header-bg", content_css)

            # Check basic.js
            res_js = urllib.request.urlopen(f"http://127.0.0.1:{port}/basic.js")
            self.assertEqual(res_js.status, 200)
            content_js = res_js.read().decode("utf-8")
            self.assertIn("Form 2: Basic Graphical Interface", content_js)
        finally:
            server.stop()


if __name__ == "__main__":
    unittest.main()
