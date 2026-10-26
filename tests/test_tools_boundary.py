"""Unit tests for ToolRegistry, workspace sandboxing, and CommandGuard."""

import os
import shutil
import tempfile
import unittest
from pathlib import Path

from zaxterlab.contracts.types import AgentDefinition, PermissionTier, ToolCall
from zaxterlab.security.guard import (
    BoundaryGuard,
    CommandSecurityViolationError,
    PermissionDeniedError,
    WorkspacePathViolationError,
)
from zaxterlab.tools.registry import ToolRegistry


class TestToolsAndBoundaries(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.mkdtemp(prefix="zaxterlab_ws_")
        self.guard = BoundaryGuard(workspace_root=self.temp_dir, authorized_spend_usd=0.0)
        self.tools = ToolRegistry(self.guard)

    def tearDown(self):
        shutil.rmtree(self.temp_dir, ignore_errors=True)

    def test_safe_file_write_and_read(self):
        # Write file
        write_call = ToolCall(
            call_id="c1",
            tool_name="write_file",
            arguments={"path": "nested/hello.txt", "content": "Line 1\nLine 2\nLine 3\n"},
        )
        res_write = self.tools.execute(write_call)
        self.assertTrue(res_write.success)
        self.assertIn("Successfully wrote", res_write.output)

        # Read full file
        read_call = ToolCall(
            call_id="c2",
            tool_name="read_file",
            arguments={"path": "nested/hello.txt"},
        )
        res_read = self.tools.execute(read_call)
        self.assertTrue(res_read.success)
        self.assertEqual(res_read.output, "Line 1\nLine 2\nLine 3\n")

        # Read line range
        read_range_call = ToolCall(
            call_id="c3",
            tool_name="read_file",
            arguments={"path": "nested/hello.txt", "start_line": 2, "end_line": 2},
        )
        res_range = self.tools.execute(read_range_call)
        self.assertTrue(res_range.success)
        self.assertEqual(res_range.output, "Line 2\n")

    def test_workspace_path_traversal_blocked(self):
        # Escaping workspace with relative ../
        traversal_call = ToolCall(
            call_id="c4",
            tool_name="write_file",
            arguments={"path": "../escaped.txt", "content": "exploit"},
        )
        res = self.tools.execute(traversal_call)
        self.assertFalse(res.success)
        self.assertIn("Security violation", res.error)
        self.assertIn("Path traversal detected", res.error)

        # Escaping with absolute system path
        abs_call = ToolCall(
            call_id="c5",
            tool_name="read_file",
            arguments={"path": "/etc/passwd"},
        )
        res_abs = self.tools.execute(abs_call)
        self.assertFalse(res_abs.success)
        self.assertIn("Security violation", res_abs.error)

    def test_safe_command_execution(self):
        cmd_call = ToolCall(
            call_id="c6",
            tool_name="run_command",
            arguments={"command": 'python3 -c "print(10 + 20)"'},
        )
        res = self.tools.execute(cmd_call)
        self.assertTrue(res.success)
        self.assertIn("30", res.output)
        self.assertIn("[exit_code]: 0", res.output)

    def test_forbidden_command_rejection(self):
        # Destructive command
        rm_call = ToolCall(
            call_id="c7",
            tool_name="run_command",
            arguments={"command": "rm -rf ."},
        )
        res = self.tools.execute(rm_call)
        self.assertFalse(res.success)
        self.assertIn("Forbidden command token detected", res.error)

        # Sudo rejection
        sudo_call = ToolCall(
            call_id="c8",
            tool_name="run_command",
            arguments={"command": "sudo ls"},
        )
        res_sudo = self.tools.execute(sudo_call)
        self.assertFalse(res_sudo.success)
        self.assertIn("Forbidden command token detected", res_sudo.error)

        # Network curl rejection
        curl_call = ToolCall(
            call_id="c9",
            tool_name="run_command",
            arguments={"command": "curl http://example.com"},
        )
        res_curl = self.tools.execute(curl_call)
        self.assertFalse(res_curl.success)
        self.assertIn("Forbidden command token detected", res_curl.error)

    def test_agent_tool_access_whitelist(self):
        restricted_agent = AgentDefinition(
            agent_id="readonly-1",
            name="Auditor",
            role="Audit",
            description="Read only",
            allowed_tools=["read_file", "list_dir"],
            permission_tier=PermissionTier.TIER_1_SAFE,
        )

        # Allowed tool passes check
        self.guard.validate_tool_access(restricted_agent, "read_file")

        # Disallowed tool raises PermissionDeniedError
        with self.assertRaises(PermissionDeniedError):
            self.guard.validate_tool_access(restricted_agent, "write_file")

        with self.assertRaises(PermissionDeniedError):
            self.guard.validate_tool_access(restricted_agent, "run_command")


if __name__ == "__main__":
    unittest.main()
