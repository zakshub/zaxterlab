"""Security, permission boundaries, workspace sandboxing, and zero-spend enforcement."""

from __future__ import annotations

import os
import shlex
from pathlib import Path
from typing import Optional

from zaxterlab.contracts.types import AgentDefinition, PermissionTier


class SecurityViolationError(Exception):
    """Base exception for all security boundary violations."""
    pass


class SpendViolationError(SecurityViolationError):
    """Raised when an operation attempts to exceed the authorized monetary budget."""
    pass


class PermissionDeniedError(SecurityViolationError):
    """Raised when an agent attempts an action outside its granted permissions."""
    pass


class WorkspacePathViolationError(SecurityViolationError):
    """Raised when a file operation attempts to escape the configured workspace."""
    pass


class CommandSecurityViolationError(SecurityViolationError):
    """Raised when an unsafe or unapproved command is submitted for execution."""
    pass


class SpendGuard:
    """Enforces a hard monetary spend boundary (default USD $0.00)."""

    def __init__(self, authorized_spend_usd: float = 0.0) -> None:
        self.authorized_spend_usd = float(authorized_spend_usd)
        self.cumulative_spent_usd: float = 0.0

    def validate_cost(self, estimated_cost_usd: float) -> None:
        """Validate whether an estimated cost is permitted under the authorized spend."""
        if estimated_cost_usd < 0.0:
            raise SpendViolationError(f"Negative cost estimate is invalid: ${estimated_cost_usd}")

        projected_spend = round(self.cumulative_spent_usd + estimated_cost_usd, 6)
        if projected_spend > self.authorized_spend_usd:
            raise SpendViolationError(
                f"Spend boundary violation: projected spend ${projected_spend:.4f} "
                f"exceeds authorized limit ${self.authorized_spend_usd:.4f}. "
                "Default is $0.00; explicit owner authorization required."
            )

    def record_cost(self, actual_cost_usd: float) -> None:
        """Record verified incurred spend."""
        self.validate_cost(actual_cost_usd)
        self.cumulative_spent_usd = round(self.cumulative_spent_usd + actual_cost_usd, 6)


class WorkspaceGuard:
    """Enforces sandboxing of file operations to an explicitly configured workspace directory."""

    def __init__(self, workspace_root: str | Path) -> None:
        self.workspace_root = Path(workspace_root).resolve()
        if not self.workspace_root.exists():
            self.workspace_root.mkdir(parents=True, exist_ok=True)

    def resolve_safe_path(self, target_path: str | Path) -> Path:
        """Resolve a relative or absolute path and verify it remains strictly within the workspace."""
        path_obj = Path(target_path)
        if path_obj.is_absolute():
            resolved = path_obj.resolve()
        else:
            resolved = (self.workspace_root / path_obj).resolve()

        try:
            resolved.relative_to(self.workspace_root)
        except ValueError:
            raise WorkspacePathViolationError(
                f"Path traversal detected: '{target_path}' resolves to '{resolved}', "
                f"which is outside the workspace root '{self.workspace_root}'."
            )

        return resolved


class CommandGuard:
    """Enforces safe command execution and rejects destructive or unrestricted shell commands."""

    # Disallowed dangerous commands, tokens, or shell utilities
    FORBIDDEN_TOKENS = {
        "rm", "rmdir", "sudo", "su", "curl", "wget", "nc", "netcat",
        "mkfs", "dd", "chmod", "chown", "ssh", "scp", "reboot", "shutdown",
        "kill", "pkill", "mkfifo", ">/dev/", ":(){ :|:& };:"
    }

    # Explicitly allowed command prefixes for safe local operations
    ALLOWED_PREFIXES = (
        ("python3", "-m", "unittest"),
        ("python3", "-c"),
        ("python3",),
        ("git", "status"),
        ("git", "diff"),
        ("git", "log"),
        ("ls",),
        ("echo",),
        ("cat",),
    )

    @classmethod
    def validate_command(cls, command: str) -> list[str]:
        """Validate that a command string is safe and return parsed tokens."""
        if not command or not command.strip():
            raise CommandSecurityViolationError("Empty command string provided.")

        try:
            tokens = shlex.split(command.strip())
        except ValueError as err:
            raise CommandSecurityViolationError(f"Malformed command syntax: {err}")

        if not tokens:
            raise CommandSecurityViolationError("Command parsed to empty tokens.")

        # Check for forbidden dangerous tokens
        for token in tokens:
            token_clean = token.strip(";\"'&|<>").lower()
            if token_clean in cls.FORBIDDEN_TOKENS:
                raise CommandSecurityViolationError(
                    f"Forbidden command token detected: '{token}' is blocked by CommandGuard."
                )

        # Check if the command matches any allowed prefix
        matches_prefix = False
        for prefix in cls.ALLOWED_PREFIXES:
            if len(tokens) >= len(prefix) and tuple(tokens[:len(prefix)]) == prefix:
                matches_prefix = True
                break

        if not matches_prefix:
            raise CommandSecurityViolationError(
                f"Command '{tokens[0]}' is not in the authorized safe command whitelist. "
                "Unrestricted shell commands are strictly forbidden."
            )

        return tokens


class BoundaryGuard:
    """Unified boundary controller for permissions, workspace, commands, and spend."""

    def __init__(
        self,
        workspace_root: str | Path,
        authorized_spend_usd: float = 0.0,
    ) -> None:
        self.workspace = WorkspaceGuard(workspace_root)
        self.spend = SpendGuard(authorized_spend_usd)
        self.command = CommandGuard()

    def validate_tool_access(self, agent: AgentDefinition, tool_name: str) -> None:
        """Verify that the agent definition explicitly permits invoking the given tool."""
        if tool_name not in agent.allowed_tools:
            raise PermissionDeniedError(
                f"Agent '{agent.name}' ({agent.agent_id}) is not authorized to invoke tool '{tool_name}'. "
                f"Allowed tools: {agent.allowed_tools}"
            )

    def validate_permission_tier(
        self,
        agent: AgentDefinition,
        action_tier: PermissionTier,
    ) -> None:
        """Verify action tier against agent's permission tier."""
        tier_order = {
            PermissionTier.TIER_1_SAFE: 1,
            PermissionTier.TIER_2_REVERSIBLE: 2,
            PermissionTier.TIER_3_CONSEQUENTIAL: 3,
        }

        if tier_order[action_tier] > tier_order[agent.permission_tier]:
            raise PermissionDeniedError(
                f"Action requires '{action_tier.value}', but agent '{agent.name}' "
                f"is restricted to '{agent.permission_tier.value}'."
            )
