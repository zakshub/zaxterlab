"""CLI and Server entrypoint for ZaxterLab."""

import argparse
import sys
from pathlib import Path

from zaxterlab.api.server import create_api_server
from zaxterlab.db.sqlite import SQLiteStore
from zaxterlab.engine.auditor import AuditorEngine
from zaxterlab.engine.worker import Worker1Engine, get_default_worker1_definition
from zaxterlab.models.mock import MockProvider
from zaxterlab.security.guard import BoundaryGuard
from zaxterlab.tools.registry import ToolRegistry


def main() -> None:
    parser = argparse.ArgumentParser(description="ZaxterLab AI Company Operating System Server")
    parser.add_argument("--host", default="127.0.0.1", help="Host interface (default: 127.0.0.1)")
    parser.add_argument("--port", type=int, default=8000, help="Port to listen on (default: 8000)")
    parser.add_argument("--db", default="/root/zakxterlab/zaxterlab.db", help="SQLite database path")
    parser.add_argument("--workspace", default="/root/zakxterlab/workspace", help="Sandboxed workspace directory")
    args = parser.parse_args()

    # Create workspace if not existing
    workspace_path = Path(args.workspace)
    workspace_path.mkdir(parents=True, exist_ok=True)

    # Initialize subsystems
    store = SQLiteStore(args.db)
    guard = BoundaryGuard(workspace_root=workspace_path, authorized_spend_usd=0.0)
    tools = ToolRegistry(guard)
    agent = get_default_worker1_definition()
    model = MockProvider()
    auditor = AuditorEngine(model=model, boundary_guard=guard, store=store, tool_registry=tools)
    engine = Worker1Engine(
        agent=agent,
        model=model,
        boundary_guard=guard,
        store=store,
        tool_registry=tools,
        auditor=auditor,
    )

    server = create_api_server(store=store, engine=engine, boundary_guard=guard, host=args.host, port=args.port)

    print(f"=================================================================")
    print(f"  ZAXTERLAB — AI Company Operating System (Phase 1 + UI)")
    print(f"  Server URL: http://{args.host}:{args.port}")
    print(f"  API Docs:   docs/API_CONTRACT.md")
    print(f"  Database:   {args.db}")
    print(f"  Workspace:  {args.workspace}")
    print(f"  Spend Limit: USD $0.00 (LOCKED)")
    print(f"=================================================================")

    try:
        server.httpd.serve_forever()
    except KeyboardInterrupt:
        print("\nShutting down ZaxterLab server...")
        server.stop()
        store.close()
        sys.exit(0)


if __name__ == "__main__":
    main()
