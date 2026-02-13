"""
Tool System Service - Orchestrates Registry, Loader, Validator, Sandbox, Accumulation.

This is the main entry point for all tool operations.
It wires together the components and exposes a clean async API.
"""

from __future__ import annotations

import time
from typing import Any, Dict, List, Optional

from loguru import logger

from .accumulation import AccumulationEngine
from .loader import ToolLoader, ToolLoadError
from .registry import ToolRegistry
from .sandbox import ToolSandbox
from .schemas import (
    ToolDefinition,
    ToolExecutionRequest,
    ToolExecutionResult,
    ToolListResponse,
    ToolRegisterRequest,
    ToolSearchRequest,
    ToolStatus,
    ToolSystemInfo,
    ToolSystemStats,
    ToolUpdateRequest,
)
from .validator import ToolValidator

# EventStream (optional)
try:
    from mission_control_core.core import EventStream
except ImportError:
    EventStream = None


MODULE_NAME = "brain.tool_system"
MODULE_VERSION = "1.0.0"


class ToolSystemService:
    """
    Unified service for the Tool Accumulation System.

    Workflow:
        register → validate → activate → load → execute → accumulate
    """

    def __init__(self, event_stream: Optional["EventStream"] = None) -> None:
        self.registry = ToolRegistry(event_stream=event_stream)
        self.loader = ToolLoader()
        self.validator = ToolValidator()
        self.sandbox = ToolSandbox()
        self.accumulation = AccumulationEngine(self.registry)

        logger.info("🧰 ToolSystemService initialized (v%s)", MODULE_VERSION)

    # ------------------------------------------------------------------
    # Registration & Validation
    # ------------------------------------------------------------------

    async def register_tool(self, request: ToolRegisterRequest) -> ToolDefinition:
        """
        Register a new tool. Automatically runs validation.

        If validation passes → status becomes VALIDATED.
        If validation fails → status becomes REJECTED.
        """
        tool = await self.registry.register(request)

        # Auto-validate
        result = await self.validator.validate(tool)

        if result.passed:
            await self.registry.set_status(
                tool.tool_id, ToolStatus.VALIDATED,
                reason="Passed all validation checks",
            )
            tool.karma_score = result.karma_score
            tool.policy_approved = result.policy_approved
            await self.registry.update_karma(tool.tool_id, result.karma_score)
        else:
            await self.registry.set_status(
                tool.tool_id, ToolStatus.REJECTED,
                reason=f"Validation failed: {', '.join(result.checks_failed)}",
            )

        return await self.registry.get(tool.tool_id) or tool

    async def activate_tool(self, tool_id: str) -> Optional[ToolDefinition]:
        """
        Activate a validated tool, making it available for execution.

        Only VALIDATED tools can be activated.
        """
        tool = await self.registry.get(tool_id)
        if not tool:
            return None

        if tool.status != ToolStatus.VALIDATED:
            logger.warning(
                "Cannot activate tool %s (status=%s, need VALIDATED)",
                tool_id, tool.status.value,
            )
            return None

        await self.registry.set_status(tool_id, ToolStatus.ACTIVE, reason="Activated by service")
        return await self.registry.get(tool_id)

    # ------------------------------------------------------------------
    # Execution
    # ------------------------------------------------------------------

    async def execute_tool(self, request: ToolExecutionRequest) -> ToolExecutionResult:
        """
        Execute a tool within its sandbox.

        Full pipeline: load → sandbox execute → accumulate.
        Only ACTIVE tools can be executed.
        """
        tool = await self.registry.get(request.tool_id)
        if not tool:
            return ToolExecutionResult(
                tool_id=request.tool_id,
                success=False,
                error=f"Tool '{request.tool_id}' not found",
            )

        if tool.status != ToolStatus.ACTIVE:
            return ToolExecutionResult(
                tool_id=request.tool_id,
                success=False,
                error=f"Tool '{request.tool_id}' is not active (status={tool.status.value})",
            )

        # Load
        try:
            tool_fn = await self.loader.load(tool)
        except ToolLoadError as e:
            return ToolExecutionResult(
                tool_id=request.tool_id,
                success=False,
                error=f"Load error: {e}",
            )

        # Execute in sandbox
        result = await self.sandbox.execute(tool, tool_fn, request)

        # Accumulate learning
        await self.accumulation.record_execution(
            tool_id=request.tool_id,
            result=result,
            parameters=request.parameters,
        )

        return result

    # ------------------------------------------------------------------
    # CRUD pass-through
    # ------------------------------------------------------------------

    async def get_tool(self, tool_id: str) -> Optional[ToolDefinition]:
        return await self.registry.get(tool_id)

    async def list_tools(self, status: Optional[ToolStatus] = None) -> ToolListResponse:
        tools = await self.registry.list_tools(status=status)
        return ToolListResponse(total=len(tools), tools=tools)

    async def update_tool(self, tool_id: str, request: ToolUpdateRequest) -> Optional[ToolDefinition]:
        return await self.registry.update(tool_id, request)

    async def delete_tool(self, tool_id: str) -> bool:
        self.loader.unload(tool_id)
        return await self.registry.delete(tool_id)

    async def search_tools(self, request: ToolSearchRequest) -> ToolListResponse:
        tools = await self.registry.search(request)
        return ToolListResponse(total=len(tools), tools=tools)

    # ------------------------------------------------------------------
    # Accumulation
    # ------------------------------------------------------------------

    async def get_recommendations(self, tool_id: str) -> Dict:
        return await self.accumulation.get_recommendations(tool_id)

    async def run_maintenance(self) -> Dict:
        return await self.accumulation.run_maintenance()

    async def record_cooccurrence(self, tool_ids: List[str]) -> None:
        await self.accumulation.record_cooccurrence(tool_ids)

    # ------------------------------------------------------------------
    # Stats & Info
    # ------------------------------------------------------------------

    async def get_stats(self) -> ToolSystemStats:
        return await self.registry.get_stats()

    async def get_info(self) -> ToolSystemInfo:
        return ToolSystemInfo(
            name=MODULE_NAME,
            version=MODULE_VERSION,
        )


# ============================================================================
# Singleton
# ============================================================================

_service: Optional[ToolSystemService] = None


def get_tool_system_service(
    event_stream: Optional["EventStream"] = None,
) -> ToolSystemService:
    global _service
    if _service is None:
        _service = ToolSystemService(event_stream=event_stream)
    return _service
