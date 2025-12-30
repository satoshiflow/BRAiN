"""
NeuroRail - Ethical Governor Rail Execution System.

NeuroRail provides mechanical execution guarantees with complete observability:
- One-way door execution (no interpretation, strict state machines)
- Complete trace chain (mission → plan → job → attempt → resource)
- Budget enforcement (time, retries, resources)
- Reflex system (automatic safety responses)
- Immutable audit trail

Inspired by SGLang Model Gateway v0.3.0.
"""

from backend.app.modules.neurorail.errors import (
    NeuroRailError,
    NeuroRailErrorCode,
    ErrorCategory,
    ExecutionTimeoutError,
    BudgetExceededError,
    RetryExhaustedError,
    OrphanKilledError,
    get_error_info,
    is_retriable,
    get_category,
)

__all__ = [
    # Error handling
    "NeuroRailError",
    "NeuroRailErrorCode",
    "ErrorCategory",
    "ExecutionTimeoutError",
    "BudgetExceededError",
    "RetryExhaustedError",
    "OrphanKilledError",
    "get_error_info",
    "is_retriable",
    "get_category",
]
