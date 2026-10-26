"""Lightweight standard library HTTP server for ZaxterLab API."""

from __future__ import annotations

import json
import threading
from http.server import BaseHTTPRequestHandler, HTTPServer
from pathlib import Path
from typing import Any, Optional
from urllib.parse import parse_qs, urlparse

from zaxterlab.api.handlers import APIHandlerService
from zaxterlab.db.sqlite import SQLiteStore
from zaxterlab.engine.worker import Worker1Engine
from zaxterlab.security.guard import (
    BoundaryGuard,
    PermissionDeniedError,
    SecurityViolationError,
    SpendViolationError,
    WorkspacePathViolationError,
)

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
DEFAULT_FRONTEND_DIR = (PROJECT_ROOT / "frontend" / "public").resolve()


class ZaxterLabHTTPHandler(BaseHTTPRequestHandler):
    """HTTP request handler routing requests to APIHandlerService."""

    service: APIHandlerService
    frontend_dir: Path = DEFAULT_FRONTEND_DIR

    def log_message(self, format: str, *args: Any) -> None:
        """Silence default stderr log spam; keep execution hermetic."""
        pass

    def _set_headers(self, status_code: int = 200) -> None:
        self.send_response(status_code)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "GET, POST, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type, Authorization")
        self.end_headers()

    def do_OPTIONS(self) -> None:
        """Handle preflight CORS requests."""
        self._set_headers(204)

    def do_HEAD(self) -> None:
        """Handle HEAD requests by sending headers without body."""
        parsed_url = urlparse(self.path)
        path = parsed_url.path.rstrip("/")
        if path.startswith("/api"):
            self._set_headers(200, content_type="application/json; charset=utf-8")
            return

        frontend_dir = getattr(self, "frontend_dir", DEFAULT_FRONTEND_DIR).resolve()
        req_file = path.lstrip("/")
        if not req_file or req_file == "":
            req_file = "index.html"
        target_file = (frontend_dir / req_file).resolve()
        try:
            target_file.relative_to(frontend_dir)
        except ValueError:
            self._set_headers(403, content_type="text/plain; charset=utf-8")
            return

        if target_file.exists() and target_file.is_file():
            content_types = {
                ".html": "text/html; charset=utf-8",
                ".js": "application/javascript; charset=utf-8",
                ".mjs": "application/javascript; charset=utf-8",
                ".css": "text/css; charset=utf-8",
                ".json": "application/json; charset=utf-8",
                ".png": "image/png",
                ".svg": "image/svg+xml",
            }
            ctype = content_types.get(target_file.suffix, "application/octet-stream")
            self._set_headers(200, content_type=ctype)
        else:
            self._set_headers(404, content_type="text/plain; charset=utf-8")

    def _send_json(self, data: Any, status_code: int = 200) -> None:
        payload = json.dumps(data, indent=2).encode("utf-8")
        self._set_headers(status_code)
        self.wfile.write(payload)

    def _send_error(self, code: str, message: str, status_code: int = 400, details: Optional[dict] = None) -> None:
        error_body = {
            "error": {
                "code": code,
                "message": message,
                "details": details or {},
            }
        }
        self._send_json(error_body, status_code=status_code)

    def _read_json_body(self) -> dict[str, Any]:
        content_length = int(self.headers.get("Content-Length", 0))
        if content_length == 0:
            return {}
        body_bytes = self.rfile.read(content_length)
        if not body_bytes:
            return {}
        try:
            return json.loads(body_bytes.decode("utf-8"))
        except json.JSONDecodeError as err:
            raise ValueError(f"Malformed JSON body: {err}")

    def do_GET(self) -> None:
        parsed_url = urlparse(self.path)
        path = parsed_url.path.rstrip("/")
        query = parse_qs(parsed_url.query)

        # 1. API Endpoints
        if path.startswith("/api"):
            try:
                if path == "/api/health":
                    self._send_json(self.service.get_health())

                elif path == "/api/tasks":
                    status = query.get("status", [None])[0]
                    self._send_json(self.service.list_tasks(status=status))

                elif path.startswith("/api/tasks/"):
                    parts = path.split("/")
                    if len(parts) == 4:
                        task_id = parts[3]
                        self._send_json(self.service.get_task_details(task_id))
                    else:
                        self._send_error("NOT_FOUND", "Unknown task endpoint", 404)

                elif path == "/api/workspace/files":
                    rel_path = query.get("path", ["."])[0]
                    self._send_json(self.service.list_workspace_files(rel_path))

                elif path == "/api/workspace/file-content":
                    rel_path = query.get("path", [""])[0]
                    if not rel_path:
                        self._send_error("VALIDATION_ERROR", "Query parameter 'path' is required.", 400)
                        return
                    self._send_json(self.service.get_file_content(rel_path))

                elif path == "/api/audit-logs":
                    entity_id = query.get("entity_id", [None])[0]
                    self._send_json(self.service.get_audit_logs(entity_id))

                elif path == "/api/completion":
                    self._send_json(self.service.get_completion_status())

                elif path == "/api/evaluator/status":
                    self._send_json(self.service.get_evaluator_status())

                elif path == "/api/evaluator/proposals":
                    status = query.get("status", [None])[0]
                    self._send_json(self.service.list_proposals(status=status))

                elif path == "/api/telemetry":
                    self._send_json(self.service.get_performance_telemetry())

                else:
                    self._send_error("NOT_FOUND", f"Endpoint '{path}' not found.", 404)

            except FileNotFoundError as e:
                self._send_error("NOT_FOUND", str(e), 404)
            except (WorkspacePathViolationError, SecurityViolationError) as e:
                self._send_error("SECURITY_VIOLATION", str(e), 403)
            except Exception as e:
                self._send_error("INTERNAL_ERROR", str(e), 500)
            return

        # 2. Static Frontend Serving
        frontend_dir = getattr(self, "frontend_dir", DEFAULT_FRONTEND_DIR).resolve()
        req_file = path.lstrip("/")
        if not req_file or req_file == "":
            req_file = "index.html"

        target_file = (frontend_dir / req_file).resolve()

        # Security check: ensure path stays within frontend_dir
        try:
            target_file.relative_to(frontend_dir)
        except ValueError:
            self._send_error("SECURITY_VIOLATION", "Access denied.", 403)
            return

        if not target_file.exists() or not target_file.is_file():
            self._send_error("NOT_FOUND", f"File '{req_file}' not found.", 404)
            return

        content_types = {
            ".html": "text/html; charset=utf-8",
            ".js": "application/javascript; charset=utf-8",
            ".mjs": "application/javascript; charset=utf-8",
            ".css": "text/css; charset=utf-8",
            ".json": "application/json; charset=utf-8",
            ".png": "image/png",
            ".svg": "image/svg+xml",
        }
        ctype = content_types.get(target_file.suffix, "application/octet-stream")

        try:
            with open(target_file, "rb") as f:
                content = f.read()

            self.send_response(200)
            self.send_header("Content-Type", ctype)
            self.send_header("Content-Length", str(len(content)))
            self.send_header("Access-Control-Allow-Origin", "*")
            self.end_headers()
            self.wfile.write(content)
        except Exception as e:
            self._send_error("INTERNAL_ERROR", f"Failed to serve file: {e}", 500)

    def do_POST(self) -> None:
        parsed_url = urlparse(self.path)
        path = parsed_url.path.rstrip("/")

        try:
            body = self._read_json_body()

            if path == "/api/tasks":
                result = self.service.create_task(body)
                self._send_json(result, status_code=201)

            elif path == "/api/pipeline/run":
                self._send_json(self.service.run_pipeline(body))

            elif path.startswith("/api/tasks/") and path.endswith("/execute"):
                parts = path.split("/")
                # /api/tasks/{task_id}/execute
                if len(parts) == 5:
                    task_id = parts[3]
                    self._send_json(self.service.execute_task(task_id, body))
                else:
                    self._send_error("NOT_FOUND", "Unknown execute endpoint", 404)

            elif path.startswith("/api/sessions/"):
                parts = path.split("/")
                # /api/sessions/{session_id}/{action}
                if len(parts) == 5:
                    session_id = parts[3]
                    action = parts[4]
                    if action == "suspend":
                        self._send_json(self.service.suspend_session(session_id))
                    elif action == "resume":
                        self._send_json(self.service.resume_session(session_id, body))
                    elif action == "terminate":
                        self._send_json(self.service.terminate_session(session_id, body))
                    else:
                        self._send_error("NOT_FOUND", f"Unknown session action: '{action}'.", 404)
                else:
                    self._send_error("NOT_FOUND", "Unknown session endpoint", 404)

            elif path == "/api/evaluator/evaluate":
                self._send_json(self.service.trigger_evaluation())

            elif path.startswith("/api/evaluator/proposals/"):
                parts = path.split("/")
                # /api/evaluator/proposals/{proposal_id}/{action}
                if len(parts) == 6:
                    proposal_id = parts[4]
                    action = parts[5]
                    if action == "approve":
                        self._send_json(self.service.approve_proposal(proposal_id, body))
                    elif action == "reject":
                        self._send_json(self.service.reject_proposal(proposal_id, body))
                    else:
                        self._send_error("NOT_FOUND", f"Unknown proposal action: '{action}'.", 404)
                else:
                    self._send_error("NOT_FOUND", "Unknown proposal endpoint", 404)

            else:
                self._send_error("NOT_FOUND", f"Endpoint '{path}' not found.", 404)

        except ValueError as e:
            self._send_error("VALIDATION_ERROR", str(e), 400)
        except FileNotFoundError as e:
            self._send_error("NOT_FOUND", str(e), 404)
        except SpendViolationError as e:
            self._send_error("SPEND_VIOLATION", str(e), 403)
        except PermissionDeniedError as e:
            self._send_error("PERMISSION_DENIED", str(e), 403)
        except (WorkspacePathViolationError, SecurityViolationError) as e:
            self._send_error("SECURITY_VIOLATION", str(e), 403)
        except Exception as e:
            self._send_error("INTERNAL_ERROR", str(e), 500)


class ZaxterLabAPIServer:
    """Threaded wrapper around HTTPServer for local API serving."""

    def __init__(self, host: str, port: int, service: APIHandlerService) -> None:
        self.host = host
        self.port = port
        self.service = service

        class CustomHandler(ZaxterLabHTTPHandler):
            pass

        CustomHandler.service = service
        CustomHandler.frontend_dir = getattr(service, "frontend_dir", DEFAULT_FRONTEND_DIR)
        self.httpd = HTTPServer((host, port), CustomHandler)
        self._thread: Optional[threading.Thread] = None

    def start_in_thread(self) -> None:
        """Start the server in a background daemon thread."""
        self._thread = threading.Thread(target=self.httpd.serve_forever, daemon=True)
        self._thread.start()

    def stop(self) -> None:
        """Shut down the HTTP server."""
        self.httpd.shutdown()
        self.httpd.server_close()
        if self._thread:
            self._thread.join(timeout=2.0)


def create_api_server(
    store: SQLiteStore,
    engine: Worker1Engine,
    boundary_guard: BoundaryGuard,
    host: str = "127.0.0.1",
    port: int = 8000,
) -> ZaxterLabAPIServer:
    """Factory creating an API server instance."""
    service = APIHandlerService(store=store, engine=engine, boundary_guard=boundary_guard)
    return ZaxterLabAPIServer(host=host, port=port, service=service)
