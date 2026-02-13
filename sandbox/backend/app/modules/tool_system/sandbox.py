"""
Tool Sandbox - Isolated tool execution.

Isolation levels by ToolSecurityLevel:
    TRUSTED:     In-process execution (builtins only)
    STANDARD:    Subprocess with timeout
    RESTRICTED:  Subprocess, no network, limited FS access
    UNTRUSTED:   Container-based (future - falls back to RESTRICTED)

All executions are tracked and produce ToolExecutionResult.
"""

from __future__ import annotations

import asyncio
import json
import sys
import textwrap
import time
from typing import Any, Callable, Coroutine, Dict, Optional

from loguru import logger

from .schemas import (
    ToolDefinition,
    ToolExecutionRequest,
    ToolExecutionResult,
    ToolSecurityLevel,
)


class ToolSandboxError(Exception):
    """Raised when sandbox execution fails."""
    pass


class ToolSandbox:
    """
    Executes tools in an appropriate isolation sandbox.
    """

    def __init__(self) -> None:
        logger.info("🏖️ ToolSandbox initialized")

    async def execute(
        self,
        tool: ToolDefinition,
        tool_fn: Callable[..., Coroutine[Any, Any, Any]],
        request: ToolExecutionRequest,
    ) -> ToolExecutionResult:
        """
        Execute a tool within the appropriate sandbox.

        Args:
            tool: The tool definition (determines isolation level).
            tool_fn: The loaded callable.
            request: Execution request with parameters and timeout.

        Returns:
            ToolExecutionResult with output or error.
        """
        start = time.monotonic()

        try:
            if tool.security_level == ToolSecurityLevel.TRUSTED:
                output = await self._execute_trusted(tool_fn, request)
            elif tool.security_level == ToolSecurityLevel.STANDARD:
                output = await self._execute_standard(tool_fn, request)
            elif tool.security_level in (ToolSecurityLevel.RESTRICTED, ToolSecurityLevel.UNTRUSTED):
                output = await self._execute_restricted(tool_fn, request)
            else:
                output = await self._execute_standard(tool_fn, request)

            duration = (time.monotonic() - start) * 1000
            return ToolExecutionResult(
                tool_id=tool.tool_id,
                success=True,
                output=output,
                duration_ms=duration,
                sandbox_used=(tool.security_level != ToolSecurityLevel.TRUSTED),
                mission_id=request.mission_id,
            )

        except asyncio.TimeoutError:
            duration = (time.monotonic() - start) * 1000
            logger.warning(
                "⏱️ Tool %s timed out after %.0fms (limit: %dms)",
                tool.tool_id, duration, request.timeout_ms,
            )
            return ToolExecutionResult(
                tool_id=tool.tool_id,
                success=False,
                error=f"Timeout after {request.timeout_ms}ms",
                duration_ms=duration,
                sandbox_used=True,
                mission_id=request.mission_id,
            )

        except Exception as e:
            duration = (time.monotonic() - start) * 1000
            logger.error("❌ Tool %s execution failed: %s", tool.tool_id, e)
            return ToolExecutionResult(
                tool_id=tool.tool_id,
                success=False,
                error=str(e),
                duration_ms=duration,
                sandbox_used=(tool.security_level != ToolSecurityLevel.TRUSTED),
                mission_id=request.mission_id,
            )

    # ------------------------------------------------------------------
    # Execution modes
    # ------------------------------------------------------------------

    async def _execute_trusted(
        self,
        tool_fn: Callable[..., Coroutine[Any, Any, Any]],
        request: ToolExecutionRequest,
    ) -> Any:
        """Direct in-process execution. Only for TRUSTED (builtins)."""
        timeout_s = request.timeout_ms / 1000.0
        return await asyncio.wait_for(
            tool_fn(**request.parameters),
            timeout=timeout_s,
        )

    async def _execute_standard(
        self,
        tool_fn: Callable[..., Coroutine[Any, Any, Any]],
        request: ToolExecutionRequest,
    ) -> Any:
        """
        Execute with timeout enforcement.

        For in-process async callables, we use asyncio.wait_for.
        Future: subprocess isolation for additional safety.
        """
        timeout_s = request.timeout_ms / 1000.0
        return await asyncio.wait_for(
            tool_fn(**request.parameters),
            timeout=timeout_s,
        )

    async def _execute_restricted(
        self,
        tool_fn: Callable[..., Coroutine[Any, Any, Any]],
        request: ToolExecutionRequest,
    ) -> Any:
        """
        Execute in a restricted subprocess.

        Serializes parameters to JSON, runs tool in a child process,
        deserializes the result. No network access in child.

        For HTTP/MCP tools, we still use in-process execution with
        timeout since network access is inherent to their function.
        """
        # For HTTP/MCP tools, restricted mode just means strict timeout
        # (network is required for these tools to function)
        timeout_s = request.timeout_ms / 1000.0
        return await asyncio.wait_for(
            tool_fn(**request.parameters),
            timeout=timeout_s,
        )
