"""Sandboxed workspace tools and execution registry."""

from __future__ import annotations

import os
import subprocess
from pathlib import Path
from typing import Any, Callable, Optional

from zaxterlab.contracts.types import ToolCall, ToolResult
from zaxterlab.security.guard import BoundaryGuard, CommandSecurityViolationError, WorkspacePathViolationError


class ToolRegistry:
    """Registry of workspace-sandboxed tools available to ZaxterLab workers."""

    def __init__(self, boundary_guard: BoundaryGuard) -> None:
        self.boundary_guard = boundary_guard
        self._tools: dict[str, Callable[..., Any]] = {
            "read_file": self.read_file,
            "write_file": self.write_file,
            "list_dir": self.list_dir,
            "run_command": self.run_command,
        }

    @property
    def available_tools(self) -> list[str]:
        return sorted(self._tools.keys())

    def execute(self, tool_call: ToolCall) -> ToolResult:
        """Execute a tool call safely, returning a structured ToolResult."""
        if tool_call.tool_name not in self._tools:
            return ToolResult(
                call_id=tool_call.call_id,
                tool_name=tool_call.tool_name,
                success=False,
                output="",
                error=f"Tool '{tool_call.tool_name}' is not registered.",
            )

        tool_fn = self._tools[tool_call.tool_name]
        try:
            output = tool_fn(**tool_call.arguments)
            return ToolResult(
                call_id=tool_call.call_id,
                tool_name=tool_call.tool_name,
                success=True,
                output=str(output),
                error=None,
            )
        except (WorkspacePathViolationError, CommandSecurityViolationError) as sec_err:
            return ToolResult(
                call_id=tool_call.call_id,
                tool_name=tool_call.tool_name,
                success=False,
                output="",
                error=f"Security violation: {sec_err}",
            )
        except Exception as exc:
            return ToolResult(
                call_id=tool_call.call_id,
                tool_name=tool_call.tool_name,
                success=False,
                output="",
                error=f"Execution error: {exc}",
            )

    def read_file(
        self,
        path: str,
        start_line: Optional[int] = None,
        end_line: Optional[int] = None,
    ) -> str:
        """Read content of a file within the configured workspace."""
        safe_path = self.boundary_guard.workspace.resolve_safe_path(path)
        if not safe_path.exists():
            raise FileNotFoundError(f"File not found: {path}")
        if not safe_path.is_file():
            raise IsADirectoryError(f"Target is a directory, not a file: {path}")

        with open(safe_path, "r", encoding="utf-8") as f:
            lines = f.readlines()

        start = (start_line - 1) if (start_line and start_line > 0) else 0
        end = end_line if (end_line and end_line > 0) else len(lines)
        selected_lines = lines[start:end]
        return "".join(selected_lines)

    def write_file(self, path: str, content: str, append: bool = False) -> str:
        """Write or append text content to a file within the configured workspace."""
        safe_path = self.boundary_guard.workspace.resolve_safe_path(path)
        safe_path.parent.mkdir(parents=True, exist_ok=True)

        mode = "a" if append else "w"
        with open(safe_path, mode, encoding="utf-8") as f:
            f.write(content)

        return f"Successfully wrote {len(content)} characters to '{path}'."

    def list_dir(self, path: str = ".") -> list[str]:
        """List files and directories within a workspace subdirectory."""
        safe_path = self.boundary_guard.workspace.resolve_safe_path(path)
        if not safe_path.exists():
            raise FileNotFoundError(f"Directory not found: {path}")
        if not safe_path.is_dir():
            raise NotADirectoryError(f"Target is not a directory: {path}")

        entries = sorted(os.listdir(safe_path))
        return entries

    def run_command(self, command: str, timeout_seconds: int = 15) -> str:
        """Run an authorized safe command inside the workspace directory."""
        tokens = self.boundary_guard.command.validate_command(command)
        workspace_cwd = str(self.boundary_guard.workspace.workspace_root)

        result = subprocess.run(
            tokens,
            cwd=workspace_cwd,
            capture_output=True,
            text=True,
            timeout=timeout_seconds,
            check=False,
        )

        stdout = result.stdout.strip()
        stderr = result.stderr.strip()
        exit_code = result.returncode

        output_parts = []
        if stdout:
            output_parts.append(stdout)
        if stderr:
            output_parts.append(f"[stderr]: {stderr}")
        output_parts.append(f"[exit_code]: {exit_code}")

        return "\n".join(output_parts)
