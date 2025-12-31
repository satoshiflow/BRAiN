"""
NeuroRail Execution Service.

Provides observation wrapper for job execution with:
- Complete trace chain generation
- Audit logging
- Telemetry collection
- State machine transitions

Phase 1: Observation only (no enforcement)
Phase 2: Budget enforcement (timeouts, retries, resource limits)
"""

from __future__ import annotations
import time
from typing import Optional, Callable, Any, Dict
from datetime import datetime
from loguru import logger
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.modules.neurorail.execution.schemas import (
    ExecutionContext,
    ExecutionResult,
)
from backend.app.modules.neurorail.identity.service import get_identity_service
from backend.app.modules.neurorail.lifecycle.service import get_lifecycle_service
from backend.app.modules.neurorail.lifecycle.schemas import TransitionRequest, AttemptState
from backend.app.modules.neurorail.audit.service import get_audit_service
from backend.app.modules.neurorail.audit.schemas import AuditEvent
from backend.app.modules.neurorail.telemetry.service import get_telemetry_service
from backend.app.modules.neurorail.telemetry.schemas import ExecutionMetrics
from backend.app.modules.neurorail.errors import (
    NeuroRailError,
    NeuroRailErrorCode,
    ExecutionTimeoutError,
    BudgetExceededError,
    OrphanKilledError,
)


class ExecutionService:
    """
    Service for executing jobs with NeuroRail observation.

    Wraps any executable function with:
    1. Trace chain management
    2. State machine transitions
    3. Audit event logging
    4. Telemetry collection
    5. Error handling and classification

    Phase 1: Observe-only (no budget enforcement)
    Phase 2: Budget enforcement (timeouts, retries, limits)
    """

    def __init__(self):
        self.identity_service = get_identity_service()
        self.lifecycle_service = get_lifecycle_service()
        self.audit_service = get_audit_service()
        self.telemetry_service = get_telemetry_service()

    # ========================================================================
    # Main Execution Wrapper
    # ========================================================================

    async def execute(
        self,
        context: ExecutionContext,
        executor: Callable[..., Any],
        db: AsyncSession
    ) -> ExecutionResult:
        """
        Execute a job with full NeuroRail observation.

        Args:
            context: Execution context with trace chain
            executor: Async function to execute
            db: Database session for audit/state transitions

        Returns:
            Execution result with metrics and trace

        Raises:
            NeuroRailError: If execution fails critically
        """
        started_at = time.time()
        audit_events = []
        state_transitions = []

        try:
            # 1. Verify parent context (orphan protection)
            if context.parent_context:
                await self._verify_parent_context(context, db)

            # 2. Transition attempt to RUNNING
            if context.trace_enabled:
                transition = await self.lifecycle_service.transition(
                    "attempt",
                    TransitionRequest(
                        entity_id=context.attempt_id,
                        transition="start",
                        metadata={
                            "job_type": context.job_type,
                            "job_parameters": context.job_parameters
                        }
                    ),
                    db
                )
                state_transitions.append(transition.event_id)

            # 3. Log execution start in audit
            if context.audit_enabled:
                start_audit = await self._log_execution_start(context, db)
                audit_events.append(start_audit.audit_id)

            # 4. Execute the job
            logger.info(f"Executing job {context.job_id} (attempt {context.attempt_id})")

            # Phase 1: No timeout enforcement - just execute
            # Phase 2: Add timeout wrapper here
            result_data = await executor(**context.job_parameters)

            # 5. Execution succeeded
            execution_time_ms = (time.time() - started_at) * 1000

            # 6. Transition attempt to SUCCEEDED
            if context.trace_enabled:
                transition = await self.lifecycle_service.transition(
                    "attempt",
                    TransitionRequest(
                        entity_id=context.attempt_id,
                        transition="complete",
                        metadata={"duration_ms": execution_time_ms}
                    ),
                    db
                )
                state_transitions.append(transition.event_id)

            # 7. Log success in audit
            if context.audit_enabled:
                success_audit = await self._log_execution_success(
                    context,
                    execution_time_ms,
                    result_data,
                    db
                )
                audit_events.append(success_audit.audit_id)

            # 8. Record telemetry
            if context.telemetry_enabled:
                await self._record_telemetry(
                    context,
                    started_at,
                    execution_time_ms,
                    success=True,
                    llm_tokens=self._extract_token_count(result_data)
                )

            # 9. Return result
            return ExecutionResult(
                attempt_id=context.attempt_id,
                status="succeeded",
                result=result_data,
                duration_ms=execution_time_ms,
                llm_tokens_used=self._extract_token_count(result_data),
                audit_events=audit_events,
                state_transitions=state_transitions
            )

        except Exception as e:
            # Execution failed
            execution_time_ms = (time.time() - started_at) * 1000

            # Classify error
            error_category, error_code = self._classify_error(e)

            # Transition to failed state
            if context.trace_enabled:
                transition = await self.lifecycle_service.transition(
                    "attempt",
                    TransitionRequest(
                        entity_id=context.attempt_id,
                        transition="fail",
                        metadata={
                            "error_category": error_category,
                            "error_code": error_code,
                            "error_message": str(e),
                            "duration_ms": execution_time_ms
                        }
                    ),
                    db
                )
                state_transitions.append(transition.event_id)

            # Log failure in audit
            if context.audit_enabled:
                failure_audit = await self._log_execution_failure(
                    context,
                    execution_time_ms,
                    error_category,
                    error_code,
                    str(e),
                    db
                )
                audit_events.append(failure_audit.audit_id)

            # Record telemetry
            if context.telemetry_enabled:
                await self._record_telemetry(
                    context,
                    started_at,
                    execution_time_ms,
                    success=False,
                    error_category=error_category,
                    error_code=error_code
                )

            # Return failure result
            return ExecutionResult(
                attempt_id=context.attempt_id,
                status=self._map_error_to_status(error_code),
                error=str(e),
                error_category=error_category,
                error_code=error_code,
                duration_ms=execution_time_ms,
                audit_events=audit_events,
                state_transitions=state_transitions
            )

    # ========================================================================
    # Helper Methods
    # ========================================================================

    async def _verify_parent_context(
        self,
        context: ExecutionContext,
        db: AsyncSession
    ) -> None:
        """
        Verify parent context exists (orphan protection).

        Raises:
            OrphanKilledError: If parent context is missing
        """
        if not context.parent_context:
            return

        # Check if parent exists
        # For now, we just log a warning (Phase 1)
        # Phase 2: Actually check and kill orphans
        logger.debug(f"Parent context check: {context.parent_context} (not enforced in Phase 1)")

    async def _log_execution_start(
        self,
        context: ExecutionContext,
        db: AsyncSession
    ) -> AuditEvent:
        """Log execution start to audit."""
        event = AuditEvent(
            mission_id=context.mission_id,
            plan_id=context.plan_id,
            job_id=context.job_id,
            attempt_id=context.attempt_id,
            event_type="execution_start",
            event_category="execution",
            severity="info",
            message=f"Starting execution of {context.job_type}",
            details={
                "job_type": context.job_type,
                "job_parameters": context.job_parameters,
                "max_attempts": context.max_attempts,
                "timeout_ms": context.timeout_ms,
                "max_llm_tokens": context.max_llm_tokens
            }
        )
        return await self.audit_service.log(event, db)

    async def _log_execution_success(
        self,
        context: ExecutionContext,
        duration_ms: float,
        result: Any,
        db: AsyncSession
    ) -> AuditEvent:
        """Log execution success to audit."""
        event = AuditEvent(
            mission_id=context.mission_id,
            plan_id=context.plan_id,
            job_id=context.job_id,
            attempt_id=context.attempt_id,
            event_type="execution_success",
            event_category="execution",
            severity="info",
            message=f"Execution of {context.job_type} succeeded in {duration_ms:.2f}ms",
            details={
                "duration_ms": duration_ms,
                "job_type": context.job_type,
                "has_result": result is not None
            }
        )
        return await self.audit_service.log(event, db)

    async def _log_execution_failure(
        self,
        context: ExecutionContext,
        duration_ms: float,
        error_category: str,
        error_code: str,
        error_message: str,
        db: AsyncSession
    ) -> AuditEvent:
        """Log execution failure to audit."""
        event = AuditEvent(
            mission_id=context.mission_id,
            plan_id=context.plan_id,
            job_id=context.job_id,
            attempt_id=context.attempt_id,
            event_type="execution_failure",
            event_category="execution",
            severity="error" if error_category == "ethical" else "warning",
            message=f"Execution of {context.job_type} failed: {error_code}",
            details={
                "duration_ms": duration_ms,
                "job_type": context.job_type,
                "error_category": error_category,
                "error_code": error_code,
                "error_message": error_message
            }
        )
        return await self.audit_service.log(event, db)

    async def _record_telemetry(
        self,
        context: ExecutionContext,
        started_at: float,
        duration_ms: float,
        success: bool,
        llm_tokens: int = 0,
        error_category: Optional[str] = None,
        error_code: Optional[str] = None
    ) -> None:
        """Record telemetry metrics."""
        metrics = ExecutionMetrics(
            entity_id=context.attempt_id,
            entity_type="attempt",
            started_at=datetime.fromtimestamp(started_at),
            completed_at=datetime.utcnow(),
            duration_ms=duration_ms,
            llm_tokens_consumed=llm_tokens,
            attempt_count=1,  # For now, single attempt
            retry_count=0,
            success=success,
            error_type=error_code,
            error_category=error_category
        )
        await self.telemetry_service.record_execution(metrics)

    def _classify_error(self, error: Exception) -> tuple[str, str]:
        """
        Classify error into category and code.

        Returns:
            (error_category, error_code)
        """
        # Check if it's a NeuroRailError
        if isinstance(error, NeuroRailError):
            return error.category, error.code

        # Classify common errors
        if isinstance(error, TimeoutError):
            return "mechanical", "NR-E001"  # EXEC_TIMEOUT
        if isinstance(error, MemoryError):
            return "mechanical", "NR-E100"  # RESOURCE_EXHAUSTED

        # Default: mechanical error
        return "mechanical", "NR-E005"  # BAD_RESPONSE_FORMAT

    def _map_error_to_status(self, error_code: str) -> str:
        """Map error code to attempt status."""
        if "TIMEOUT" in error_code or error_code == "NR-E001":
            return "failed_timeout"
        if "RESOURCE" in error_code or error_code == "NR-E100":
            return "failed_resource"
        return "failed_error"

    def _extract_token_count(self, result: Any) -> int:
        """Extract token count from result (if available)."""
        if isinstance(result, dict):
            return result.get("tokens_used", 0) or result.get("usage", {}).get("total_tokens", 0)
        return 0


# Singleton instance
_execution_service: Optional[ExecutionService] = None


def get_execution_service() -> ExecutionService:
    """Get singleton execution service instance."""
    global _execution_service
    if _execution_service is None:
        _execution_service = ExecutionService()
    return _execution_service
