"""
NeuroRail Execution Module.

Provides observation wrapper for job execution:
- Complete trace chain generation
- State machine transitions
- Audit logging
- Telemetry collection

Phase 1: Observation only (no budget enforcement)
Phase 2: Budget enforcement (timeouts, retries, limits)
"""

from app.modules.neurorail.execution.schemas import (
    ExecutionContext,
    ExecutionResult,
    ExecutionRequest,
)
from app.modules.neurorail.execution.service import (
    ExecutionService,
    get_execution_service,
)
from app.modules.neurorail.execution.router import router

__all__ = [
    # Schemas
    "ExecutionContext",
    "ExecutionResult",
    "ExecutionRequest",
    # Service
    "ExecutionService",
    "get_execution_service",
    # Router
    "router",
]
