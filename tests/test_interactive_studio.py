"""Hermetic unit tests for Form 4: Rich Interactive Application (DAG Node Studio)."""

import shutil
import tempfile
import unittest
from pathlib import Path

from zaxterlab.api.server import create_api_server
from zaxterlab.cli import init_service


class TestInteractiveDAGStudio(unittest.TestCase):
    """Test suite for Form 4: Rich Interactive Application (DAG Node Studio)."""

    def setUp(self) -> None:
        self.tmp_dir = tempfile.mkdtemp(prefix="zaxterlab_studio_test_")
        self.db_path = str(Path(self.tmp_dir) / "test.db")
        self.ws_path = str(Path(self.tmp_dir) / "workspace")
        self.service, self.store = init_service(self.db_path, self.ws_path)

        self.server = create_api_server(
            store=self.store,
            engine=self.service.engine,
            boundary_guard=self.service.boundary_guard,
            host="127.0.0.1",
            port=0,
        )
        self.port = self.server.httpd.server_address[1]
        self.server.start_in_thread()

    def tearDown(self) -> None:
        self.server.stop()
        self.store.close()
        shutil.rmtree(self.tmp_dir, ignore_errors=True)

    def test_studio_static_assets_serving_and_dom_structure(self) -> None:
        import urllib.request

        # 1. HTML
        res_html = urllib.request.urlopen(f"http://127.0.0.1:{self.port}/studio.html")
        self.assertEqual(res_html.status, 200)
        html_bytes = res_html.read()
        html = html_bytes.decode("utf-8")
        self.assertIn("ZAXTERLAB DAG STUDIO", html)
        self.assertIn("Form 4: Interactive Node Canvas", html)
        self.assertIn("svg-connections", html)
        self.assertIn("nodes-container", html)
        self.assertIn("node-inspector", html)
        self.assertIn("btn-run-dag", html)
        self.assertIn("btn-auto-layout", html)

        # 2. CSS
        res_css = urllib.request.urlopen(f"http://127.0.0.1:{self.port}/studio.css")
        self.assertEqual(res_css.status, 200)
        css_bytes = res_css.read()
        css = css_bytes.decode("utf-8")
        self.assertIn("--canvas-bg", css)
        self.assertIn(".dag-wire", css)
        self.assertIn(".dag-node", css)

        # 3. JS
        res_js = urllib.request.urlopen(f"http://127.0.0.1:{self.port}/studio.js")
        self.assertEqual(res_js.status, 200)
        js_bytes = res_js.read()
        js = js_bytes.decode("utf-8")
        self.assertIn("Form 4: Interactive DAG Studio", js)
        self.assertIn("calculateMissingPositions", js)
        self.assertIn("renderWires", js)

        # 4. Performance Budget: Total uncompressed bundle size < 100KB
        total_bundle_size = len(html_bytes) + len(css_bytes) + len(js_bytes)
        self.assertLess(total_bundle_size, 100000, f"Bundle size {total_bundle_size} exceeds 100KB budget")


if __name__ == "__main__":
    unittest.main()
