"""
Executor Base - Production-Grade Foundation

Provides strict contracts, validation, idempotency, rollback hooks,
and audit integration for all Business Factory executors.

Version: 2.0.0 (Sprint 6 - Hardened)
"""

from __future__ import annotations

import time
import hashlib
from abc import ABC, abstractmethod
from typing import Any, Dict, List, Optional, Set
from datetime import datetime
from enum import Enum
from loguru import logger
from pydantic import BaseModel, Field

from app.modules.business_factory.schemas import (
    ExecutionStep,
    StepResult,
    StepStatus,
)

# Sprint 7: Metrics integration
try:
    from app.modules.monitoring.metrics import get_metrics_collector
    METRICS_AVAILABLE = True
except ImportError:
    METRICS_AVAILABLE = False

# Sprint 7.4: Safe mode integration
try:
    from app.modules.safe_mode.service import get_safe_mode_service
    SAFE_MODE_AVAILABLE = True
except ImportError:
    SAFE_MODE_AVAILABLE = False


class ExecutionMode(str, Enum):
    """Execution mode for safety controls"""
    DRY_RUN = "dry_run"      # Validate only, no changes
    NORMAL = "normal"         # Standard execution
    FORCE = "force"           # Skip some validations (dangerous)


class ExecutorCapability(str, Enum):
    """Executor capabilities for contract enforcement"""
    IDEMPOTENT = "idempotent"           # Can safely re-run
    ROLLBACKABLE = "rollbackable"       # Can undo changes
    ATOMIC = "atomic"                   # All-or-nothing
    RESUMABLE = "resumable"             # Can continue after failure


class ExecutionContext(BaseModel):
    """Context for executor execution"""
    plan_id: str
    step_id: str
    execution_mode: ExecutionMode = ExecutionMode.NORMAL
    timeout_seconds: Optional[float] = None
    retry_count: int = 0
    max_retries: int = 3
    dry_run: bool = False
    audit_enabled: bool = True
    previous_attempts: List[Dict[str, Any]] = Field(default_factory=list)

    # Idempotency tracking
    execution_hash: Optional[str] = None
    previous_execution_hash: Optional[str] = None


class ValidationError(Exception):
    """Raised when input validation fails"""
    pass


class ExecutionError(Exception):
    """Raised when execution fails"""
    pass


class RollbackError(Exception):
    """Raised when rollback fails"""
    pass


class ExecutorBase(ABC):
    """
    Base class for all Business Factory executors.

    Contract:
    1. MUST implement execute() - main execution logic
    2. MUST implement validate_input() - input validation
    3. SHOULD implement rollback() - undo changes
    4. SHOULD declare capabilities - what executor can do
    5. MUST be idempotent if capability declared
    6. MUST emit audit events
    7. MUST respect timeouts
    8. MUST handle retries correctly

    Fail-Closed Principles:
    - Invalid input → ValidationError → STOP
    - Execution error → ExecutionError → ROLLBACK (if capable)
    - Timeout → ExecutionError → ROLLBACK (if capable)
    - Unknown state → FAIL
    """

    def __init__(
        self,
        name: str,
        capabilities: Set[ExecutorCapability],
        default_timeout_seconds: float = 300.0,  # 5 minutes
        default_max_retries: int = 3,
    ):
        """
        Initialize executor.

        Args:
            name: Executor name (e.g., "WebsiteExecutor")
            capabilities: Set of capabilities this executor supports
            default_timeout_seconds: Default timeout
            default_max_retries: Default retry limit
        """
        self.name = name
        self.capabilities = capabilities
        self.default_timeout_seconds = default_timeout_seconds
        self.default_max_retries = default_max_retries

        # Execution state
        self._execution_history: List[Dict[str, Any]] = []
        self._rollback_stack: List[Dict[str, Any]] = []

        logger.info(
            f"Executor initialized: {self.name} "
            f"(capabilities={[c.value for c in capabilities]})"
        )

    # ========================================================================
    # Public Interface (Called by FactoryExecutor)
    # ========================================================================

    async def execute_step(
        self,
        step: ExecutionStep,
        context: ExecutionContext
    ) -> StepResult:
        """
        Execute a single step with full safety checks.

        This is the main entry point called by FactoryExecutor.

        Flow:
        1. Validate input
        2. Check idempotency (if capable)
        3. Execute with timeout
        4. Record success/failure
        5. Return result

        Args:
            step: Execution step to run
            context: Execution context

        Returns:
            StepResult with success status and data

        Raises:
            ValidationError: Input validation failed
            ExecutionError: Execution failed
            TimeoutError: Timeout exceeded
        """
        start_time = time.time()

        logger.info(
            f"[{self.name}] Executing step: {step.step_id} "
            f"(mode={context.execution_mode}, retry={context.retry_count})"
        )

        # Sprint 7.4: Safe Mode Check
        if SAFE_MODE_AVAILABLE:
            try:
                safe_mode = get_safe_mode_service()
                safe_mode.check_and_block(f"executor_{self.name}_step_{step.step_id}")
            except RuntimeError:
                # Safe mode is enabled - block execution
                raise
            except Exception as e:
                # Safe mode check failed - log but continue (fail-open for safety check)
                logger.warning(f"Safe mode check failed: {e}")

        try:
            # 1. Input Validation
            self._validate_input_strict(step, context)

            # 2. Idempotency Check
            if ExecutorCapability.IDEMPOTENT in self.capabilities:
                if await self._check_already_executed(step, context):
                    logger.info(f"[{self.name}] Step already executed (idempotent)")
                    return self._get_cached_result(step, context)

            # 3. Dry Run Mode
            if context.dry_run or context.execution_mode == ExecutionMode.DRY_RUN:
                logger.info(f"[{self.name}] Dry run mode - validating only")
                return await self._dry_run_execute(step, context)

            # 4. Execute with Timeout
            timeout = context.timeout_seconds or self.default_timeout_seconds

            try:
                result = await self._execute_with_timeout(step, context, timeout)
            except TimeoutError as e:
                logger.error(f"[{self.name}] Execution timeout after {timeout}s")

                # Sprint 7: Record executor failure (fail-safe)
                if METRICS_AVAILABLE:
                    try:
                        metrics = get_metrics_collector()
                        metrics.record_executor_failure()
                    except Exception:
                        pass  # Fail-safe: do not block on metrics

                raise ExecutionError(f"Execution timeout: {str(e)}")

            # 5. Record Success
            duration = time.time() - start_time
            self._record_execution(step, context, result, duration)

            # Sprint 7: Record successful execution (fail-safe)
            if METRICS_AVAILABLE:
                try:
                    metrics = get_metrics_collector()
                    metrics.record_success()
                except Exception:
                    pass  # Fail-safe: do not block on metrics

            logger.info(
                f"[{self.name}] Step completed: {step.step_id} "
                f"(duration={duration:.2f}s)"
            )

            return result

        except ValidationError as e:
            logger.error(f"[{self.name}] Validation failed: {e}")
            raise

        except ExecutionError as e:
            logger.error(f"[{self.name}] Execution failed: {e}")

            # Attempt rollback if capable
            if ExecutorCapability.ROLLBACKABLE in self.capabilities:
                logger.warning(f"[{self.name}] Attempting rollback...")
                try:
                    await self.rollback_step(step, context)
                except RollbackError as rb_err:
                    logger.error(f"[{self.name}] Rollback failed: {rb_err}")

            raise

        except Exception as e:
            logger.error(f"[{self.name}] Unexpected error: {e}")

            # Sprint 7: Record executor failure (fail-safe)
            if METRICS_AVAILABLE:
                try:
                    metrics = get_metrics_collector()
                    metrics.record_executor_failure()
                except Exception:
                    pass  # Fail-safe: do not block on metrics

            raise ExecutionError(f"Unexpected error: {str(e)}")

    async def rollback_step(
        self,
        step: ExecutionStep,
        context: ExecutionContext
    ) -> bool:
        """
        Rollback a previously executed step.

        Args:
            step: Step to rollback
            context: Execution context

        Returns:
            True if rollback succeeded

        Raises:
            RollbackError: Rollback failed
        """
        if ExecutorCapability.ROLLBACKABLE not in self.capabilities:
            raise RollbackError(
                f"Executor {self.name} does not support rollback"
            )

        logger.info(f"[{self.name}] Rolling back step: {step.step_id}")

        try:
            success = await self.rollback(step, context)

            if success:
                logger.info(f"[{self.name}] Rollback successful")
            else:
                logger.error(f"[{self.name}] Rollback reported failure")
                raise RollbackError("Rollback reported failure")

            return success

        except Exception as e:
            logger.error(f"[{self.name}] Rollback error: {e}")
            raise RollbackError(f"Rollback failed: {str(e)}")

    # ========================================================================
    # Abstract Methods (MUST implement)
    # ========================================================================

    @abstractmethod
    async def execute(
        self,
        step: ExecutionStep,
        context: ExecutionContext
    ) -> StepResult:
        """
        Execute the step.

        This is the main execution logic that each executor must implement.

        Args:
            step: Execution step with parameters
            context: Execution context

        Returns:
            StepResult with success status and data

        Raises:
            ExecutionError: If execution fails
        """
        pass

    @abstractmethod
    async def validate_input(
        self,
        step: ExecutionStep,
        context: ExecutionContext
    ) -> List[str]:
        """
        Validate step input parameters.

        Args:
            step: Execution step to validate
            context: Execution context

        Returns:
            List of validation errors (empty if valid)
        """
        pass

    async def rollback(
        self,
        step: ExecutionStep,
        context: ExecutionContext
    ) -> bool:
        """
        Rollback changes made by this step.

        Default implementation: no-op (returns False).
        Override if executor is ROLLBACKABLE.

        Args:
            step: Step to rollback
            context: Execution context

        Returns:
            True if rollback succeeded, False otherwise
        """
        logger.warning(
            f"[{self.name}] Rollback called but not implemented "
            f"(capability not declared)"
        )
        return False

    # ========================================================================
    # Validation Helpers
    # ========================================================================

    def _validate_input_strict(
        self,
        step: ExecutionStep,
        context: ExecutionContext
    ):
        """
        Strict input validation with fail-closed approach.

        Args:
            step: Step to validate
            context: Execution context

        Raises:
            ValidationError: If validation fails
        """
        errors = []

        # 1. Check required parameters
        if not step.parameters:
            errors.append("Step parameters are empty")

        # 2. Call executor-specific validation
        executor_errors = await self.validate_input(step, context)
        errors.extend(executor_errors)

        # 3. Validate timeout
        if context.timeout_seconds is not None:
            if context.timeout_seconds <= 0:
                errors.append(f"Invalid timeout: {context.timeout_seconds}")
            if context.timeout_seconds > 3600:  # 1 hour max
                errors.append(f"Timeout too large: {context.timeout_seconds}s (max 3600s)")

        # 4. Validate retry count
        if context.retry_count > context.max_retries:
            errors.append(
                f"Retry count ({context.retry_count}) exceeds max ({context.max_retries})"
            )

        # Fail-closed: Any error stops execution
        if errors:
            raise ValidationError(
                f"Input validation failed: {', '.join(errors)}"
            )

    # ========================================================================
    # Idempotency Support
    # ========================================================================

    def _compute_execution_hash(
        self,
        step: ExecutionStep,
        context: ExecutionContext
    ) -> str:
        """
        Compute hash of execution parameters for idempotency check.

        Args:
            step: Execution step
            context: Execution context

        Returns:
            SHA256 hash of execution parameters
        """
        import json

        # Include step parameters and relevant context
        hash_data = {
            "step_id": step.step_id,
            "executor": step.executor.value,
            "template_id": step.template_id,
            "parameters": step.parameters,
            "execution_mode": context.execution_mode.value,
        }

        hash_string = json.dumps(hash_data, sort_keys=True)
        return hashlib.sha256(hash_string.encode()).hexdigest()

    async def _check_already_executed(
        self,
        step: ExecutionStep,
        context: ExecutionContext
    ) -> bool:
        """
        Check if step was already executed with same parameters.

        Args:
            step: Execution step
            context: Execution context

        Returns:
            True if already executed
        """
        current_hash = self._compute_execution_hash(step, context)
        context.execution_hash = current_hash

        # Check execution history
        for record in self._execution_history:
            if record.get("execution_hash") == current_hash:
                if record.get("success"):
                    logger.info(
                        f"[{self.name}] Found successful execution with same hash"
                    )
                    return True

        return False

    def _get_cached_result(
        self,
        step: ExecutionStep,
        context: ExecutionContext
    ) -> StepResult:
        """
        Get cached result from previous execution.

        Args:
            step: Execution step
            context: Execution context

        Returns:
            Cached StepResult
        """
        current_hash = context.execution_hash

        for record in self._execution_history:
            if record.get("execution_hash") == current_hash:
                return StepResult(
                    step_id=step.step_id,
                    success=True,
                    data=record.get("result_data", {}),
                    evidence_files=record.get("evidence_files", []),
                    duration_seconds=0.0,  # Cached, no execution time
                )

        # Fallback (should not happen)
        return StepResult(
            step_id=step.step_id,
            success=True,
            data={"cached": True},
            evidence_files=[],
            duration_seconds=0.0,
        )

    # ========================================================================
    # Execution Helpers
    # ========================================================================

    async def _execute_with_timeout(
        self,
        step: ExecutionStep,
        context: ExecutionContext,
        timeout: float
    ) -> StepResult:
        """
        Execute with timeout enforcement.

        Args:
            step: Execution step
            context: Execution context
            timeout: Timeout in seconds

        Returns:
            StepResult

        Raises:
            TimeoutError: If timeout exceeded
        """
        import asyncio

        try:
            result = await asyncio.wait_for(
                self.execute(step, context),
                timeout=timeout
            )
            return result

        except asyncio.TimeoutError:
            raise TimeoutError(f"Execution exceeded timeout of {timeout}s")

    async def _dry_run_execute(
        self,
        step: ExecutionStep,
        context: ExecutionContext
    ) -> StepResult:
        """
        Execute in dry-run mode (validation only).

        Args:
            step: Execution step
            context: Execution context

        Returns:
            StepResult with dry_run=True
        """
        # Validation already passed
        return StepResult(
            step_id=step.step_id,
            success=True,
            data={
                "dry_run": True,
                "message": "Validation passed, no changes made"
            },
            evidence_files=[],
            duration_seconds=0.0,
        )

    def _record_execution(
        self,
        step: ExecutionStep,
        context: ExecutionContext,
        result: StepResult,
        duration: float
    ):
        """
        Record execution in history for idempotency.

        Args:
            step: Executed step
            context: Execution context
            result: Execution result
            duration: Execution duration
        """
        record = {
            "step_id": step.step_id,
            "executor": self.name,
            "execution_hash": context.execution_hash,
            "success": result.success,
            "result_data": result.data,
            "evidence_files": result.evidence_files,
            "duration_seconds": duration,
            "timestamp": datetime.utcnow().isoformat(),
            "retry_count": context.retry_count,
        }

        self._execution_history.append(record)

    # ========================================================================
    # Utility Methods
    # ========================================================================

    def has_capability(self, capability: ExecutorCapability) -> bool:
        """Check if executor has specific capability"""
        return capability in self.capabilities

    def get_execution_history(self) -> List[Dict[str, Any]]:
        """Get execution history"""
        return self._execution_history.copy()

    def clear_history(self):
        """Clear execution history (for testing)"""
        self._execution_history.clear()
        self._rollback_stack.clear()
