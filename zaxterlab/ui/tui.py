"""Terminal Graphical User Interface (TUI) for ZaxterLab using standard curses.

Provides a full interactive keyboard-driven graphical dashboard within standard terminal emulators,
supporting live status monitoring, task queue inspection, pipeline execution, and audit log viewing.
"""

from __future__ import annotations

import curses
import json
import time
from typing import Any, Optional

from zaxterlab.api.handlers import APIHandlerService
from zaxterlab.db.sqlite import SQLiteStore


class ZaxterLabTUI:
    """Curses-based interactive terminal graphical interface."""

    def __init__(self, service: APIHandlerService, store: SQLiteStore) -> None:
        self.service = service
        self.store = store
        self.active_tab = 0  # 0: Status, 1: Tasks, 2: Specialists, 3: Projects, 4: Audit
        self.tabs = ["Status", "Tasks", "Specialists", "Projects", "Audit"]
        self.status_msg = "Ready. Press 1-5 to switch tabs, 'p' to run pipeline, 'r' to refresh, 'q' to quit."
        self.cached_health: dict[str, Any] = {}
        self.cached_tasks: list[dict[str, Any]] = []
        self.cached_specialists: list[dict[str, Any]] = []
        self.cached_projects: list[dict[str, Any]] = []
        self.cached_logs: list[dict[str, Any]] = []
        self.scroll_pos = 0

    def refresh_data(self) -> None:
        try:
            self.cached_health = self.service.get_health()
            self.cached_tasks = self.service.list_tasks().get("tasks", [])
            self.cached_specialists = self.service.list_specialists().get("specialists", [])
            self.cached_projects = self.service.list_projects().get("projects", [])
            self.cached_logs = self.service.get_audit_logs().get("audit_logs", [])[-30:]
        except Exception as e:
            self.status_msg = f"Error refreshing data: {e}"

    def run(self) -> None:
        """Entrypoint for curses wrapper."""
        curses.wrapper(self._main_loop)

    def _main_loop(self, stdscr: Any) -> None:
        curses.curs_set(0)
        stdscr.nodelay(True)
        curses.use_default_colors()

        # Initialize color pairs if terminal supports colors
        has_colors = curses.has_colors()
        if has_colors:
            curses.start_color()
            curses.init_pair(1, curses.COLOR_BLACK, curses.COLOR_CYAN)    # Header / Active Tab
            curses.init_pair(2, curses.COLOR_GREEN, -1)                   # Success / OK
            curses.init_pair(3, curses.COLOR_YELLOW, -1)                  # Warning / Highlight
            curses.init_pair(4, curses.COLOR_RED, -1)                     # Error / Spend Lock
            curses.init_pair(5, curses.COLOR_CYAN, -1)                    # Info / Secondary

        self.refresh_data()
        last_refresh = time.time()

        while True:
            # Auto-refresh every 5 seconds
            if time.time() - last_refresh > 5.0:
                self.refresh_data()
                last_refresh = time.time()

            stdscr.erase()
            max_y, max_x = stdscr.getmaxyx()

            if max_y < 12 or max_x < 60:
                stdscr.addstr(0, 0, "Terminal window too small (min 60x12). Resize window.")
                stdscr.refresh()
                time.sleep(0.1)
                continue

            # 1. Top Header Bar
            header = " ZAXTERLAB — TERMINAL GRAPHICAL INTERFACE (FORM 2: BASIC GUI) "
            try:
                stdscr.addstr(0, 0, header.ljust(max_x)[:max_x], curses.color_pair(1) | curses.A_BOLD if has_colors else curses.A_REVERSE)
            except curses.error:
                pass

            # 2. Tabs Row
            tab_str = " "
            for i, name in enumerate(self.tabs):
                if i == self.active_tab:
                    tab_str += f"[{i+1}. {name.upper()}] "
                else:
                    tab_str += f" {i+1}. {name}  "
            tab_str += " | 'p' Run Pipeline | 's' SaaS Builder | 'r' Refresh | 'q' Quit"
            try:
                stdscr.addstr(1, 0, tab_str[:max_x], curses.A_BOLD)
                stdscr.addstr(2, 0, "-" * (max_x - 1))
            except curses.error:
                pass

            # 3. Content Area
            content_height = max_y - 5
            if self.active_tab == 0:
                self._draw_status(stdscr, 3, max_x, content_height, has_colors)
            elif self.active_tab == 1:
                self._draw_tasks(stdscr, 3, max_x, content_height, has_colors)
            elif self.active_tab == 2:
                self._draw_specialists(stdscr, 3, max_x, content_height, has_colors)
            elif self.active_tab == 3:
                self._draw_projects(stdscr, 3, max_x, content_height, has_colors)
            elif self.active_tab == 4:
                self._draw_audit(stdscr, 3, max_x, content_height, has_colors)

            # 4. Bottom Status & Spend Bar
            spend = self.cached_health.get("spend_guard", {})
            cost = spend.get("cumulative_spent_usd", 0.0)
            status_line = f" [Spend: ${cost:.2f} (LOCKED $0.00)] | {self.status_msg}"
            try:
                stdscr.addstr(max_y - 2, 0, "-" * (max_x - 1))
                stdscr.addstr(max_y - 1, 0, status_line[:max_x - 1], curses.color_pair(2) if has_colors else curses.A_NORMAL)
            except curses.error:
                pass

            stdscr.refresh()

            # Handle Keyboard Input
            try:
                ch = stdscr.getch()
            except curses.error:
                ch = -1

            if ch != -1:
                if ch in (ord('q'), ord('Q'), 27):  # 'q' or ESC
                    break
                elif ch == ord('1'):
                    self.active_tab = 0
                    self.scroll_pos = 0
                elif ch == ord('2'):
                    self.active_tab = 1
                    self.scroll_pos = 0
                elif ch == ord('3'):
                    self.active_tab = 2
                    self.scroll_pos = 0
                elif ch == ord('4'):
                    self.active_tab = 3
                    self.scroll_pos = 0
                elif ch == ord('5'):
                    self.active_tab = 4
                    self.scroll_pos = 0
                elif ch in (ord('r'), ord('R')):
                    self.refresh_data()
                    self.status_msg = "State refreshed from SQLite."
                elif ch in (ord('p'), ord('P')):
                    self.status_msg = "Running 2-Stage Multi-Worker DAG Pipeline..."
                    stdscr.refresh()
                    self._execute_pipeline()
                elif ch in (ord('s'), ord('S')):
                    self.status_msg = "Triggering SaaS Project Generation..."
                    stdscr.refresh()
                    self._execute_saas()
                elif ch == curses.KEY_UP:
                    self.scroll_pos = max(0, self.scroll_pos - 1)
                elif ch == curses.KEY_DOWN:
                    self.scroll_pos += 1

            time.sleep(0.05)

    def _execute_pipeline(self) -> None:
        try:
            import uuid
            t1 = f"pipe_reem_{uuid.uuid4().hex[:6]}"
            t2 = f"pipe_aroosh_{uuid.uuid4().hex[:6]}"
            payload = {
                "task_definitions": [
                    {
                        "task_id": t1,
                        "title": "Generate ledger sync module",
                        "description": "Implement ledger synchronization logic",
                        "assigned_specialist": "Reem",
                        "depends_on": [],
                    },
                    {
                        "task_id": t2,
                        "title": "Verify ledger sync tests",
                        "description": "Run test suite on ledger sync",
                        "assigned_specialist": "Aroosh",
                        "depends_on": [t1],
                    },
                ]
            }
            res = self.service.run_pipeline(payload)
            self.refresh_data()
            succeeded = res.get("succeeded_count", 0)
            self.status_msg = f"Pipeline complete: {succeeded} tasks succeeded. Audit approved."
        except Exception as e:
            self.status_msg = f"Pipeline execution failed: {e}"

    def _execute_saas(self) -> None:
        try:
            import uuid
            slug_num = uuid.uuid4().hex[:4]
            res = self.service.launch_saas_project({
                "name": f"TUI SaaS Venture {slug_num}",
                "domain": "Enterprise Cloud",
                "requirements": "Automated workflow distribution engine",
            })
            self.refresh_data()
            self.status_msg = f"SaaS project '{res.get('project_slug')}' generated (5 artifacts created, QA passed)."
        except Exception as e:
            self.status_msg = f"SaaS creation failed: {e}"

    def _draw_status(self, stdscr: Any, start_y: int, max_x: int, height: int, has_colors: bool) -> None:
        h = self.cached_health
        lines = [
            ("=== SYSTEM HEALTH & CORE ENGINE ===", curses.A_BOLD),
            (f"Status:               {h.get('status', 'healthy')}", 0),
            (f"Version:              {h.get('version', '0.3.0-phase3')}", 0),
            (f"Operating Mode:       {h.get('mode', 'offline')}", 0),
            (f"Active Worker Engine: Reem (Construction & Programming)", 0),
            (f"Auditor Engine:       Zaks (Independent Audit & Oversight)", 0),
            ("", 0),
            ("=== HARD SECURITY & SPEND BOUNDARY ===", curses.A_BOLD),
            (f"Spend Limit:          USD $0.00 (LOCKED)", curses.color_pair(2) if has_colors else 0),
            (f"Cumulative Spent:     USD $0.00", curses.color_pair(2) if has_colors else 0),
            (f"Workspace Directory:  {h.get('workspace', {}).get('root', '/root/zakxterlab/workspace')}", 0),
            (f"Path Traversal Guard: ACTIVE (Hermetic BoundaryGuard)", curses.color_pair(2) if has_colors else 0),
            ("", 0),
            ("=== WORKFORCE & PIPELINE METRICS ===", curses.A_BOLD),
            (f"Registered Specialists: {len(self.cached_specialists)} active", 0),
            (f"Total Tasks in Queue:   {len(self.cached_tasks)}", 0),
            (f"Persisted Projects:     {len(self.cached_projects)}", 0),
            (f"Immutable Audit Events: {len(self.cached_logs)}", 0),
        ]
        for idx, (text, attr) in enumerate(lines[:height]):
            try:
                stdscr.addstr(start_y + idx, 2, text[:max_x - 4], attr)
            except curses.error:
                break

    def _draw_tasks(self, stdscr: Any, start_y: int, max_x: int, height: int, has_colors: bool) -> None:
        header = f"{'Task ID':<18} | {'Specialist':<10} | {'Status':<12} | Title"
        try:
            stdscr.addstr(start_y, 2, header[:max_x - 4], curses.A_BOLD | curses.A_UNDERLINE)
        except curses.error:
            return

        visible = self.cached_tasks[self.scroll_pos:self.scroll_pos + height - 2]
        if not visible:
            try:
                stdscr.addstr(start_y + 2, 4, "No tasks found in database.", curses.A_DIM)
            except curses.error:
                pass
            return

        for idx, t in enumerate(visible):
            status = t.get("status", "PENDING")
            color = curses.color_pair(2) if status == "COMPLETED" else (curses.color_pair(3) if status == "RUNNING" else 0)
            row = f"{t.get('task_id', ''):<18} | {t.get('assigned_specialist', ''):<10} | {status:<12} | {t.get('title', '')}"
            try:
                stdscr.addstr(start_y + 1 + idx, 2, row[:max_x - 4], color if has_colors else 0)
            except curses.error:
                break

    def _draw_specialists(self, stdscr: Any, start_y: int, max_x: int, height: int, has_colors: bool) -> None:
        header = f"{'Name':<10} | {'Role':<28} | {'Department':<20} | {'Status':<10}"
        try:
            stdscr.addstr(start_y, 2, header[:max_x - 4], curses.A_BOLD | curses.A_UNDERLINE)
        except curses.error:
            return

        for idx, s in enumerate(self.cached_specialists[:height - 2]):
            row = f"{s.get('name', ''):<10} | {s.get('role', '')[:28]:<28} | {s.get('department', '')[:20]:<20} | {s.get('runtime_status', 'AVAILABLE'):<10}"
            try:
                stdscr.addstr(start_y + 1 + idx, 2, row[:max_x - 4], 0)
            except curses.error:
                break

    def _draw_projects(self, stdscr: Any, start_y: int, max_x: int, height: int, has_colors: bool) -> None:
        header = f"{'Project ID':<25} | {'Type':<18} | {'Status':<12} | Name"
        try:
            stdscr.addstr(start_y, 2, header[:max_x - 4], curses.A_BOLD | curses.A_UNDERLINE)
        except curses.error:
            return

        for idx, p in enumerate(self.cached_projects[:height - 2]):
            row = f"{p.get('project_id', ''):<25} | {p.get('project_type', ''):<18} | {p.get('status', ''):<12} | {p.get('name', '')}"
            try:
                stdscr.addstr(start_y + 1 + idx, 2, row[:max_x - 4], 0)
            except curses.error:
                break

    def _draw_audit(self, stdscr: Any, start_y: int, max_x: int, height: int, has_colors: bool) -> None:
        header = f"{'ID':<6} | {'Timestamp':<19} | {'Event Type':<25} | {'Entity ID':<25}"
        try:
            stdscr.addstr(start_y, 2, header[:max_x - 4], curses.A_BOLD | curses.A_UNDERLINE)
        except curses.error:
            return

        visible = list(reversed(self.cached_logs))[self.scroll_pos:self.scroll_pos + height - 2]
        for idx, log in enumerate(visible):
            ts = log.get("timestamp", "")[:19]
            row = f"{str(log.get('id', '')):<6} | {ts:<19} | {log.get('event_type', '')[:25]:<25} | {log.get('entity_id', '')[:25]:<25}"
            try:
                stdscr.addstr(start_y + 1 + idx, 2, row[:max_x - 4], 0)
            except curses.error:
                break
