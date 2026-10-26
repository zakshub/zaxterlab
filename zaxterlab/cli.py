"""ZaxterLab CLI & Terminal Interface.

Provides a unified command-line interface for the ZaxterLab AI Company Operating System,
supporting full task execution, pipeline runs, SaaS project builds, specialist spawning,
and SQLite audit inspection in standard terminal environments.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any, Optional

from zaxterlab.api.handlers import APIHandlerService
from zaxterlab.api.server import create_api_server
from zaxterlab.db.sqlite import SQLiteStore
from zaxterlab.engine.auditor import AuditorEngine
from zaxterlab.engine.worker import Worker1Engine, get_default_worker1_definition
from zaxterlab.models.mock import MockProvider
from zaxterlab.security.guard import BoundaryGuard
from zaxterlab.tools.registry import ToolRegistry


def init_service(db_path: str, workspace_path: str) -> tuple[APIHandlerService, SQLiteStore]:
    """Initialize core runtime subsystems and return APIHandlerService."""
    ws = Path(workspace_path)
    ws.mkdir(parents=True, exist_ok=True)

    store = SQLiteStore(db_path)
    guard = BoundaryGuard(workspace_root=ws, authorized_spend_usd=0.0)
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
    service = APIHandlerService(store=store, engine=engine, boundary_guard=guard)
    return service, store


def print_table(headers: list[str], rows: list[list[str]]) -> None:
    """Print an ASCII table in the terminal."""
    if not rows:
        print("  (None)")
        return
    col_widths = [len(h) for h in headers]
    for row in rows:
        for idx, cell in enumerate(row):
            if idx < len(col_widths):
                col_widths[idx] = max(col_widths[idx], len(str(cell)))

    header_line = " | ".join(h.ljust(col_widths[i]) for i, h in enumerate(headers))
    sep_line = "-+-".join("-" * col_widths[i] for i in range(len(headers)))
    print(header_line)
    print(sep_line)
    for row in rows:
        padded = []
        for i, cell in enumerate(row):
            w = col_widths[i] if i < len(col_widths) else len(str(cell))
            padded.append(str(cell).ljust(w))
        print(" | ".join(padded))


def cmd_status(service: APIHandlerService, args: argparse.Namespace) -> int:
    health = service.get_health()
    tasks_res = service.list_tasks()
    projects_res = service.list_projects()
    specialists_res = service.list_specialists()

    spend = health.get("spend_guard", {})
    ws = health.get("workspace", {})

    data = {
        "status": health.get("status"),
        "version": health.get("version"),
        "mode": health.get("mode"),
        "spend_guard": {
            "authorized_spend_usd": spend.get("authorized_spend_usd", 0.0),
            "cumulative_spent_usd": spend.get("cumulative_spent_usd", 0.0),
            "spend_locked": spend.get("spend_locked", True),
        },
        "workspace_root": ws.get("root"),
        "registered_specialists_count": len(specialists_res.get("specialists", [])),
        "tasks_count": len(tasks_res.get("tasks", [])),
        "projects_count": len(projects_res.get("projects", [])),
        "health_raw": health,
    }

    if getattr(args, "json", False):
        print(json.dumps(data, indent=2))
        return 0

    print("=================================================================")
    print("  ZAXTERLAB — AI Company Operating System Status")
    print("=================================================================")
    print(f"  Status:          {data['status']}")
    print(f"  Mode:            {data['mode']}")
    print(f"  Spend Guard:     USD ${data['spend_guard']['cumulative_spent_usd']:.2f} / ${data['spend_guard']['authorized_spend_usd']:.2f} (Locked: {data['spend_guard']['spend_locked']})")
    print(f"  Workspace:       {data['workspace_root']}")
    print(f"  Specialists:     {data['registered_specialists_count']} active")
    print(f"  Total Tasks:     {data['tasks_count']}")
    print(f"  Total Projects:  {data['projects_count']}")
    print("=================================================================")
    return 0


def cmd_task_list(service: APIHandlerService, args: argparse.Namespace) -> int:
    res = service.list_tasks(status=getattr(args, "status", None))
    tasks = res.get("tasks", [])
    if getattr(args, "json", False):
        print(json.dumps(tasks, indent=2))
        return 0

    headers = ["Task ID", "Title", "Specialist", "Status", "Depends On"]
    rows = [
        [
            t.get("task_id", ""),
            t.get("title", "")[:35],
            t.get("assigned_specialist", ""),
            t.get("status", ""),
            ", ".join(t.get("depends_on", [])),
        ]
        for t in tasks
    ]
    print(f"\n--- ZaxterLab Tasks ({len(tasks)} total) ---")
    print_table(headers, rows)
    return 0


def cmd_task_create(service: APIHandlerService, args: argparse.Namespace) -> int:
    depends = [d.strip() for d in args.depends.split(",") if d.strip()] if getattr(args, "depends", None) else []
    payload = {
        "title": args.title,
        "description": args.desc or "",
        "assigned_specialist": args.specialist or "Reem",
        "depends_on": depends,
    }
    res = service.create_task(payload)
    task = res.get("task", {})
    task_id = task.get("task_id")

    if getattr(args, "json", False) and not getattr(args, "execute", False):
        print(json.dumps(res, indent=2))
        return 0

    print(f"[OK] Task created: {task_id} ({task.get('title')}) assigned to {task.get('assigned_specialist')}")

    if getattr(args, "execute", False) and task_id:
        print(f"[RUN] Executing task {task_id} immediately...")
        exec_res = service.execute_task(task_id, {})
        if getattr(args, "json", False):
            print(json.dumps({"created": task, "executed": exec_res}, indent=2))
            return 0
        task_info = exec_res.get("task", {})
        status = task_info.get("status")
        session = exec_res.get("session") or {}
        print(f"[RESULT] Status: {status} (Session {session.get('session_id')}, Specialist: {task_info.get('assigned_specialist')})")
    return 0


def cmd_task_exec(service: APIHandlerService, args: argparse.Namespace) -> int:
    res = service.execute_task(args.task_id, {})
    if getattr(args, "json", False):
        print(json.dumps(res, indent=2))
        return 0

    task = res.get("task", {})
    status = task.get("status")
    session = res.get("session") or {}
    print(f"\n[OK] Task {args.task_id} Execution Finished:")
    print(f"  Title:        {task.get('title')}")
    print(f"  Status:       {status}")
    print(f"  Specialist:   {task.get('assigned_specialist')}")
    print(f"  Session ID:   {session.get('session_id')}")
    print(f"  Tokens Used:  {session.get('total_tokens_used', 0)}")
    print(f"  Cost (USD):   ${session.get('total_cost_usd', 0.0):.2f}")
    return 0


def cmd_task_show(service: APIHandlerService, args: argparse.Namespace) -> int:
    res = service.get_task_details(args.task_id)
    if getattr(args, "json", False):
        print(json.dumps(res, indent=2))
        return 0

    task = res.get("task", {})
    sessions = res.get("sessions", [])
    print(f"\n--- Task Details: {task.get('task_id')} ---")
    print(f"  Title:      {task.get('title')}")
    print(f"  Specialist: {task.get('assigned_specialist')}")
    print(f"  Status:     {task.get('status')}")
    print(f"  Created At: {task.get('created_at')}")
    print(f"  Depends On: {', '.join(task.get('depends_on', [])) or 'None'}")
    print(f"  Description:\n    {task.get('description')}")
    print(f"\n  Sessions ({len(sessions)}):")
    for s in sessions:
        print(f"    - Session {s.get('session_id')}: status={s.get('status')}, tokens={s.get('total_tokens_used')}, cost=${s.get('total_cost_usd', 0.0):.2f}")
    return 0


def cmd_pipeline_run(service: APIHandlerService, args: argparse.Namespace) -> int:
    mod = getattr(args, "module", "inventory_ledger") or "inventory_ledger"
    spec = getattr(args, "spec", "Deterministic balance check verification") or "Deterministic verification"

    import uuid
    t1_id = f"pipe_reem_{uuid.uuid4().hex[:6]}"
    t2_id = f"pipe_aroosh_{uuid.uuid4().hex[:6]}"

    payload = {
        "task_definitions": [
            {
                "task_id": t1_id,
                "title": f"Generate {mod} module code",
                "description": f"Implement core logic for {mod}: {spec}",
                "assigned_specialist": "Reem",
                "depends_on": [],
            },
            {
                "task_id": t2_id,
                "title": f"Run automated test verification on {mod}",
                "description": f"Execute test suite and verify coverage for {mod}",
                "assigned_specialist": "Aroosh",
                "depends_on": [t1_id],
            },
        ]
    }
    print(f"[RUN] Starting 2-Stage Multi-Worker DAG Pipeline ({mod})...")
    res = service.run_pipeline(payload)
    if getattr(args, "json", False):
        print(json.dumps(res, indent=2))
        return 0

    completed = res.get("succeeded_count", 0)
    failed = res.get("failed_count", 0)
    print(f"[OK] Pipeline Execution Finished:")
    print(f"  Completed Tasks: {completed}")
    print(f"  Failed Tasks:    {failed}")
    print(f"  Details:         {res.get('tasks', {})}")
    return 0


def cmd_project_list(service: APIHandlerService, args: argparse.Namespace) -> int:
    res = service.list_projects()
    projects = res.get("projects", [])
    if getattr(args, "json", False):
        print(json.dumps(projects, indent=2))
        return 0

    headers = ["Project ID", "Name", "Type", "Status", "Workspace Path"]
    rows = [
        [
            p.get("project_id", ""),
            p.get("name", "")[:28],
            p.get("project_type", ""),
            p.get("status", ""),
            p.get("workspace_path", "")[-30:],
        ]
        for p in projects
    ]
    print(f"\n--- ZaxterLab Projects ({len(projects)} total) ---")
    print_table(headers, rows)
    return 0


def cmd_project_saas(service: APIHandlerService, args: argparse.Namespace) -> int:
    payload = {
        "name": args.name,
        "domain": args.domain,
        "requirements": args.reqs,
    }
    print(f"[RUN] Generating 5-Department SaaS Project '{args.name}'...")
    res = service.launch_saas_project(payload)
    if getattr(args, "json", False):
        print(json.dumps(res, indent=2))
        return 0

    project_id = res.get("project_id")
    workspace = res.get("workspace_relative_path") or res.get("project_dir")
    files = res.get("files_created") or res.get("generated_files", [])
    qa_verified = res.get("qa_verified")

    print(f"\n[OK] SaaS Project Generated Successfully!")
    print(f"  Project ID:      {project_id}")
    print(f"  Workspace:       {workspace}")
    print(f"  Tests Passed:    {qa_verified}")
    print(f"  Artifacts Generated:")
    for f in files:
        print(f"    - {f}")
    return 0


def cmd_project_internal_transform(service: APIHandlerService, args: argparse.Namespace) -> int:
    print("[RUN] Executing Section 18 Internal Transformation Initiative (7-Task DAG)...")
    res = service.execute_internal_transformation_project(force_rerun=getattr(args, "force", False))
    if getattr(args, "json", False):
        print(json.dumps(res, indent=2))
        return 0

    print(f"[OK] Internal Transformation Completed!")
    print(f"  Status:             {res.get('status')}")
    print(f"  Tasks Executed:     {len(res.get('tasks_executed', []))}")
    print(f"  Artifacts Created:  {len(res.get('artifacts_created', []))}")
    return 0


def cmd_specialist_list(service: APIHandlerService, args: argparse.Namespace) -> int:
    res = service.list_specialists()
    specialists = res.get("specialists", [])
    if getattr(args, "json", False):
        print(json.dumps(specialists, indent=2))
        return 0

    headers = ["Worker ID", "Name", "Role", "Department", "Tier", "Status"]
    rows = [
        [
            s.get("worker_id", ""),
            s.get("name", ""),
            s.get("role", "")[:25],
            s.get("department", ""),
            s.get("permission_tier", ""),
            s.get("runtime_status", "idle"),
        ]
        for s in specialists
    ]
    print(f"\n--- ZaxterLab Specialist Workforce ({len(specialists)} registered) ---")
    print_table(headers, rows)
    return 0


def cmd_specialist_spawn(service: APIHandlerService, args: argparse.Namespace) -> int:
    tools = [t.strip() for t in args.tools.split(",") if t.strip()] if getattr(args, "tools", None) else ["read_file", "write_file"]
    auto_approve = bool(getattr(args, "approve", False))
    payload = {
        "name": args.name,
        "role_title": args.role,
        "role": args.role,
        "department": args.dept or "Engineering",
        "justification": args.gap,
        "capability_gap": args.gap,
        "allowed_tools": tools,
        "auto_approve": auto_approve,
        "authorize_immediately": auto_approve,
    }
    res = service.spawn_or_propose_specialist(payload)
    if getattr(args, "json", False):
        print(json.dumps(res, indent=2))
        return 0

    if res.get("status") in ("ACTIVATED", "registered_immediately") and res.get("specialist"):
        spec = res.get("specialist", {})
        print(f"[OK] Specialist '{spec.get('name')}' spawned & registered immediately (ID: {spec.get('worker_id')})")
    else:
        prop = res.get("proposal", {})
        role_name = prop.get("target_role_title") or prop.get("proposed_role") or args.role
        print(f"[PROPOSED] Specialist proposal created: {prop.get('proposal_id')} for role '{role_name}'")
    return 0


def cmd_evaluator_run(service: APIHandlerService, args: argparse.Namespace) -> int:
    res = service.trigger_evaluation()
    if getattr(args, "json", False):
        print(json.dumps(res, indent=2))
        return 0

    proposals = res.get("proposals", [])
    print(f"\n[OK] Workload Evaluation Completed. Generated {len(proposals)} proposals:")
    for p in proposals:
        print(f"  - [{p.get('status')}] {p.get('proposed_role')}: {p.get('justification')}")
    return 0


def cmd_audit_list(service: APIHandlerService, args: argparse.Namespace) -> int:
    limit = getattr(args, "limit", 25) or 25
    entity = getattr(args, "entity", None)
    res = service.get_audit_logs(entity_id=entity)
    logs = res.get("audit_logs", [])
    if limit > 0:
        logs = logs[-limit:]

    if getattr(args, "json", False):
        print(json.dumps(logs, indent=2))
        return 0

    headers = ["Log ID", "Timestamp", "Event Type", "Entity ID", "Details Summary"]
    rows = [
        [
            str(l.get("id", "")),
            l.get("timestamp", "")[:19],
            l.get("event_type", "")[:28],
            l.get("entity_id", "")[:25],
            str(l.get("details", ""))[:40],
        ]
        for l in logs
    ]
    print(f"\n--- Immutable SQLite Audit Trail (Latest {len(logs)}) ---")
    print_table(headers, rows)
    return 0


def build_parser() -> argparse.ArgumentParser:
    cwd = Path.cwd()
    default_db = str(cwd / "zaxterlab.db")
    default_workspace = str(cwd / "workspace")

    json_parent = argparse.ArgumentParser(add_help=False)
    json_parent.add_argument("--json", action="store_true", help="Output results in raw JSON format for scripting")

    parser = argparse.ArgumentParser(
        prog="zaxterlab",
        description="ZaxterLab AI Company Operating System — CLI & Multi-Interface Runtime",
        parents=[json_parent],
    )
    # Global flags
    parser.add_argument("--db", default=default_db, help=f"SQLite database path (default: {default_db})")
    parser.add_argument("--workspace", default=default_workspace, help=f"Sandbox workspace directory (default: {default_workspace})")

    # Backwards-compatible server options when no subcommand given
    parser.add_argument("--host", default=None, help="Server host (if running server)")
    parser.add_argument("--port", type=int, default=None, help="Server port (if running server)")

    subparsers = parser.add_subparsers(dest="subcommand", help="Available commands")

    # 1. status
    subparsers.add_parser("status", parents=[json_parent], help="Show system status, workers, spend guard, and stats")

    # 1b. tui (Terminal Graphical User Interface)
    subparsers.add_parser("tui", help="Launch interactive curses-based Terminal Graphical Interface (Form 2)")

    # 2. server
    p_server = subparsers.add_parser("server", help="Start the HTTP API & Web UI server")
    p_server.add_argument("--host", default="127.0.0.1", help="Host interface (default: 127.0.0.1)")
    p_server.add_argument("--port", type=int, default=8000, help="Port to listen on (default: 8000)")

    # 3. task
    p_task = subparsers.add_parser("task", parents=[json_parent], help="Task management and execution")
    task_sub = p_task.add_subparsers(dest="task_action", help="Task actions")

    p_task_list = task_sub.add_parser("list", parents=[json_parent], help="List tasks")
    p_task_list.add_argument("--status", help="Filter by status (pending, completed, etc.)")

    p_task_create = task_sub.add_parser("create", parents=[json_parent], help="Create a task")
    p_task_create.add_argument("--title", required=True, help="Task title")
    p_task_create.add_argument("--desc", help="Detailed task description")
    p_task_create.add_argument("--specialist", default="Reem", help="Assigned specialist name (default: Reem)")
    p_task_create.add_argument("--depends", help="Comma-separated prerequisite task IDs")
    p_task_create.add_argument("--execute", action="store_true", help="Execute immediately after creation")

    p_task_exec = task_sub.add_parser("exec", parents=[json_parent], help="Execute an existing task")
    p_task_exec.add_argument("task_id", help="Task ID to execute")

    p_task_show = task_sub.add_parser("show", parents=[json_parent], help="Show details and execution history of a task")
    p_task_show.add_argument("task_id", help="Task ID to inspect")

    # 4. pipeline
    p_pipe = subparsers.add_parser("pipeline", parents=[json_parent], help="Multi-worker DAG pipeline")
    pipe_sub = p_pipe.add_subparsers(dest="pipeline_action", help="Pipeline actions")
    p_pipe_run = pipe_sub.add_parser("run", parents=[json_parent], help="Run 2-stage multi-worker DAG pipeline")
    p_pipe_run.add_argument("--module", default="inventory_ledger", help="Module name to generate")
    p_pipe_run.add_argument("--spec", default="Deterministic balance check verification", help="Specification")

    # 5. project
    p_proj = subparsers.add_parser("project", parents=[json_parent], help="Projects registry and generation")
    proj_sub = p_proj.add_subparsers(dest="project_action", help="Project actions")
    proj_sub.add_parser("list", parents=[json_parent], help="List all projects")
    p_proj_saas = proj_sub.add_parser("saas", parents=[json_parent], help="Generate 5-department SaaS project")
    p_proj_saas.add_argument("--name", required=True, help="SaaS project name")
    p_proj_saas.add_argument("--domain", required=True, help="Domain / Industry")
    p_proj_saas.add_argument("--reqs", required=True, help="Requirements specification")

    p_proj_trans = proj_sub.add_parser("internal-transform", parents=[json_parent], help="Run Section 18 internal transformation initiative")
    p_proj_trans.add_argument("--force", action="store_true", help="Force rerun even if already executed")

    # 6. specialist
    p_spec = subparsers.add_parser("specialist", parents=[json_parent], help="Specialist workforce inspection and spawning")
    spec_sub = p_spec.add_subparsers(dest="specialist_action", help="Specialist actions")
    spec_sub.add_parser("list", parents=[json_parent], help="List registered specialists")
    p_spec_spawn = spec_sub.add_parser("spawn", parents=[json_parent], help="Dynamically spawn a specialist")
    p_spec_spawn.add_argument("--name", required=True, help="Specialist name")
    p_spec_spawn.add_argument("--role", required=True, help="Role title")
    p_spec_spawn.add_argument("--dept", default="Engineering", help="Department")
    p_spec_spawn.add_argument("--gap", required=True, help="Capability gap justification")
    p_spec_spawn.add_argument("--tools", default="read_file,write_file,run_tests", help="Allowed tools")
    p_spec_spawn.add_argument("--approve", action="store_true", help="Auto-approve and register immediately")

    # 7. evaluator
    p_eval = subparsers.add_parser("evaluator", parents=[json_parent], help="Workload evaluator and proposals")
    eval_sub = p_eval.add_subparsers(dest="evaluator_action", help="Evaluator actions")
    eval_sub.add_parser("run", parents=[json_parent], help="Run workload evaluator")

    # 8. audit
    p_audit = subparsers.add_parser("audit", parents=[json_parent], help="SQLite immutable audit logs")
    audit_sub = p_audit.add_subparsers(dest="audit_action", help="Audit actions")
    p_audit_list = audit_sub.add_parser("list", parents=[json_parent], help="List audit log entries")
    p_audit_list.add_argument("--limit", type=int, default=25, help="Number of logs to retrieve")

    return parser


def run_server(args: argparse.Namespace) -> int:
    host = args.host or "127.0.0.1"
    port = args.port or 8000
    db = args.db
    workspace = args.workspace

    service, store = init_service(db, workspace)
    # create server with service
    from zaxterlab.api.server import ZaxterLabAPIServer
    server = ZaxterLabAPIServer(host=host, port=port, service=service)

    print("=================================================================")
    print("  ZAXTERLAB — AI Company Operating System Server")
    print(f"  Server URL:  http://{host}:{port}")
    print(f"  Database:    {db}")
    print(f"  Workspace:   {workspace}")
    print(f"  Spend Limit: USD $0.00 (LOCKED)")
    print("=================================================================")

    try:
        server.httpd.serve_forever()
    except KeyboardInterrupt:
        print("\nShutting down ZaxterLab server...")
        server.stop()
        store.close()
        return 0
    return 0


def main(argv: Optional[list[str]] = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)

    # Backwards compatibility: if host/port provided without subcommand, or no subcommand at all, run server
    if args.subcommand is None or args.subcommand == "server":
        return run_server(args)

    # Initialize service for CLI commands
    service, store = init_service(args.db, args.workspace)

    try:
        if args.subcommand == "status":
            return cmd_status(service, args)

        elif args.subcommand == "tui":
            from zaxterlab.ui.tui import ZaxterLabTUI
            tui_app = ZaxterLabTUI(service=service, store=store)
            tui_app.run()
            return 0

        elif args.subcommand == "task":
            action = getattr(args, "task_action", "list") or "list"
            if action == "list":
                return cmd_task_list(service, args)
            elif action == "create":
                return cmd_task_create(service, args)
            elif action == "exec":
                return cmd_task_exec(service, args)
            elif action == "show":
                return cmd_task_show(service, args)

        elif args.subcommand == "pipeline":
            action = getattr(args, "pipeline_action", "run") or "run"
            if action == "run":
                return cmd_pipeline_run(service, args)

        elif args.subcommand == "project":
            action = getattr(args, "project_action", "list") or "list"
            if action == "list":
                return cmd_project_list(service, args)
            elif action == "saas":
                return cmd_project_saas(service, args)
            elif action == "internal-transform":
                return cmd_project_internal_transform(service, args)

        elif args.subcommand == "specialist":
            action = getattr(args, "specialist_action", "list") or "list"
            if action == "list":
                return cmd_specialist_list(service, args)
            elif action == "spawn":
                return cmd_specialist_spawn(service, args)

        elif args.subcommand == "evaluator":
            action = getattr(args, "evaluator_action", "run") or "run"
            if action == "run":
                return cmd_evaluator_run(service, args)

        elif args.subcommand == "audit":
            action = getattr(args, "audit_action", "list") or "list"
            if action == "list":
                return cmd_audit_list(service, args)

        parser.print_help()
        return 1

    finally:
        store.close()


if __name__ == "__main__":
    sys.exit(main())
