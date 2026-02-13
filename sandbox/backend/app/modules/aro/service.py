"""
ARO Service - Core Business Logic

Orchestrates all ARO components to provide secure repository operations.

Components:
- State Machine: Controls operation lifecycle
- Validators: Validate operations before execution
- Safety Checkpoints: Verify safety before execution
- Audit Logger: Record all events
- Policy Engine: Apply governance rules

Principles:
- Fail-closed: Deny by default
- Explicit authorization required
- Complete audit trail
- Deterministic behavior
"""

from __future__ import annotations

import time
import uuid
from datetime import datetime
from typing import Dict, List, Optional
from loguru import logger

from .schemas import (
    RepoOperation,
    RepoOperationContext,
    RepoOperationType,
    OperationState,
    AuthorizationLevel,
    ProposeOperationRequest,
    AuthorizeOperationRequest,
    OperationStatusResponse,
    AROStats,
    AROHealth,
    AROInfo,
)
from .state_machine import get_state_machine, StateTransitionError
from .validators import get_validator_manager
from .safety import get_safety_manager
from .audit_logger import get_audit_logger

# Optional: Policy Engine integration
try:
    from app.modules.policy.service import get_policy_engine
    from app.modules.policy.schemas import PolicyEvaluationContext

    POLICY_ENGINE_AVAILABLE = True
except ImportError:
    POLICY_ENGINE_AVAILABLE = False
    logger.warning("Policy Engine not available - ARO will work standalone")


MODULE_NAME = "brain.aro"
MODULE_VERSION = "1.0.0"


class AROService:
    """
    ARO Service - Orchestrates secure repository operations.

    This is the main service class that coordinates all ARO components.
    """

    def __init__(self):
        """Initialize ARO service"""
        # Get singleton instances
        self.state_machine = get_state_machine()
        self.validator_manager = get_validator_manager()
        self.safety_manager = get_safety_manager()
        self.audit_logger = get_audit_logger()

        # Optional: Policy Engine
        if POLICY_ENGINE_AVAILABLE:
            self.policy_engine = get_policy_engine()
        else:
            self.policy_engine = None

        # Operation storage (in-memory)
        # TODO: Migrate to database in production
        self.operations: Dict[str, RepoOperation] = {}

        # Statistics
        self.total_operations = 0
        self.operations_authorized = 0
        self.operations_denied = 0
        self.operations_completed = 0
        self.operations_failed = 0

        self.start_time = time.time()

        logger.info(
            f"🚀 ARO Service initialized (v{MODULE_VERSION}, "
            f"policy_engine={'enabled' if POLICY_ENGINE_AVAILABLE else 'disabled'})"
        )

    # ========================================================================
    # Core Operation Lifecycle Methods
    # ========================================================================

    async def propose_operation(
        self,
        request: ProposeOperationRequest
    ) -> RepoOperation:
        """
        Propose a new repository operation.

        This is step 1 in the operation lifecycle.

        Args:
            request: Operation proposal request

        Returns:
            Created operation (in PROPOSED state)

        Raises:
            ValueError: If request is invalid
        """
        # Generate unique operation ID
        operation_id = f"op_{uuid.uuid4().hex[:12]}"

        # Create operation context
        context = RepoOperationContext(
            operation_id=operation_id,
            operation_type=request.operation_type,
            agent_id=request.agent_id,
            repo_path=request.repo_path,
            branch=request.branch,
            params=request.params,
            requested_auth_level=request.requested_auth_level,
            granted_auth_level=AuthorizationLevel.NONE,  # Not yet authorized
        )

        # Create operation
        operation = RepoOperation(
            operation_id=operation_id,
            context=context,
            current_state=OperationState.PROPOSED,
        )

        # Store operation
        self.operations[operation_id] = operation
        self.total_operations += 1

        # Log to audit trail
        await self.audit_logger.log(
            operation_id=operation_id,
            operation_type=request.operation_type,
            agent_id=request.agent_id,
            event_type="proposed",
            message=f"Operation proposed: {request.operation_type.value}",
            new_state=OperationState.PROPOSED,
        )

        logger.info(
            f"📋 Operation proposed: {operation_id} "
            f"({request.operation_type.value} by {request.agent_id})"
        )

        return operation

    async def validate_operation(
        self,
        operation_id: str
    ) -> RepoOperation:
        """
        Validate a proposed operation.

        This is step 2 in the operation lifecycle.

        Args:
            operation_id: Operation ID to validate

        Returns:
            Updated operation (in VALIDATING or PENDING_AUTH state)

        Raises:
            ValueError: If operation not found or invalid state
        """
        # Get operation
        operation = self.operations.get(operation_id)
        if not operation:
            raise ValueError(f"Operation not found: {operation_id}")

        # Check state
        if operation.current_state != OperationState.PROPOSED:
            raise ValueError(
                f"Operation {operation_id} is not in PROPOSED state "
                f"(current: {operation.current_state.value})"
            )

        # Transition to VALIDATING
        self.state_machine.transition(
            operation,
            OperationState.VALIDATING,
            reason="Starting validation"
        )

        await self.audit_logger.log_state_change(
            operation_id=operation_id,
            operation_type=operation.context.operation_type,
            agent_id=operation.context.agent_id,
            previous_state=OperationState.PROPOSED,
            new_state=OperationState.VALIDATING,
            reason="Starting validation"
        )

        # Run all validators
        validation_results = await self.validator_manager.validate_all(
            operation.context
        )
        operation.validation_results = validation_results

        # Log validation results
        for result in validation_results:
            await self.audit_logger.log_validation(
                operation_id=operation_id,
                operation_type=operation.context.operation_type,
                agent_id=operation.context.agent_id,
                validator_id=result.validator_id,
                passed=result.valid,
                issues=result.issues,
            )

        # Check if all validations passed
        all_valid = self.validator_manager.is_valid(validation_results)

        if not all_valid:
            # Validation failed - transition to DENIED
            self.state_machine.transition(
                operation,
                OperationState.DENIED,
                reason="Validation failed"
            )

            await self.audit_logger.log_state_change(
                operation_id=operation_id,
                operation_type=operation.context.operation_type,
                agent_id=operation.context.agent_id,
                previous_state=OperationState.VALIDATING,
                new_state=OperationState.DENIED,
                reason="Validation failed"
            )

            self.operations_denied += 1

            logger.warning(f"❌ Validation failed for operation: {operation_id}")

        else:
            # Validation passed - transition to PENDING_AUTH
            self.state_machine.transition(
                operation,
                OperationState.PENDING_AUTH,
                reason="Validation passed"
            )

            await self.audit_logger.log_state_change(
                operation_id=operation_id,
                operation_type=operation.context.operation_type,
                agent_id=operation.context.agent_id,
                previous_state=OperationState.VALIDATING,
                new_state=OperationState.PENDING_AUTH,
                reason="Validation passed"
            )

            logger.info(f"✅ Validation passed for operation: {operation_id}")

        return operation

    async def authorize_operation(
        self,
        request: AuthorizeOperationRequest
    ) -> RepoOperation:
        """
        Authorize a validated operation.

        This is step 3 in the operation lifecycle.

        Args:
            request: Authorization request

        Returns:
            Updated operation (in AUTHORIZED or DENIED state)

        Raises:
            ValueError: If operation not found or invalid state
        """
        operation_id = request.operation_id

        # Get operation
        operation = self.operations.get(operation_id)
        if not operation:
            raise ValueError(f"Operation not found: {operation_id}")

        # Check state
        if operation.current_state != OperationState.PENDING_AUTH:
            raise ValueError(
                f"Operation {operation_id} is not in PENDING_AUTH state "
                f"(current: {operation.current_state.value})"
            )

        # Update authorization
        operation.context.granted_auth_level = request.grant_level
        operation.authorized_by = request.authorized_by
        operation.authorized_at = datetime.utcnow()

        # Check if granted level is sufficient (already validated, but double-check)
        sufficient = await self._check_authorization_sufficient(operation)

        if not sufficient:
            # Authorization insufficient - deny
            operation.authorization_granted = False
            self.state_machine.transition(
                operation,
                OperationState.DENIED,
                reason="Insufficient authorization level"
            )

            await self.audit_logger.log_state_change(
                operation_id=operation_id,
                operation_type=operation.context.operation_type,
                agent_id=operation.context.agent_id,
                previous_state=OperationState.PENDING_AUTH,
                new_state=OperationState.DENIED,
                reason="Insufficient authorization level"
            )

            self.operations_denied += 1

            logger.warning(
                f"❌ Authorization denied for operation: {operation_id} "
                f"(insufficient level)"
            )

        else:
            # Check with policy engine (if available)
            if POLICY_ENGINE_AVAILABLE and self.policy_engine:
                policy_allowed = await self._check_policy(operation)
                if not policy_allowed:
                    # Policy denied
                    operation.authorization_granted = False
                    self.state_machine.transition(
                        operation,
                        OperationState.DENIED,
                        reason="Denied by policy engine"
                    )

                    await self.audit_logger.log_state_change(
                        operation_id=operation_id,
                        operation_type=operation.context.operation_type,
                        agent_id=operation.context.agent_id,
                        previous_state=OperationState.PENDING_AUTH,
                        new_state=OperationState.DENIED,
                        reason="Denied by policy engine"
                    )

                    self.operations_denied += 1

                    logger.warning(
                        f"❌ Policy denied operation: {operation_id}"
                    )

                    return operation

            # Authorization granted
            operation.authorization_granted = True
            self.state_machine.transition(
                operation,
                OperationState.AUTHORIZED,
                reason="Authorization granted"
            )

            await self.audit_logger.log_state_change(
                operation_id=operation_id,
                operation_type=operation.context.operation_type,
                agent_id=operation.context.agent_id,
                previous_state=OperationState.PENDING_AUTH,
                new_state=OperationState.AUTHORIZED,
                reason=f"Authorized by {request.authorized_by}"
            )

            self.operations_authorized += 1

            logger.info(
                f"✅ Authorization granted for operation: {operation_id} "
                f"by {request.authorized_by}"
            )

        return operation

    async def execute_operation(
        self,
        operation_id: str
    ) -> RepoOperation:
        """
        Execute an authorized operation.

        This is step 4 in the operation lifecycle.

        Args:
            operation_id: Operation ID to execute

        Returns:
            Updated operation (in COMPLETED or FAILED state)

        Raises:
            ValueError: If operation not found or invalid state
        """
        # Get operation
        operation = self.operations.get(operation_id)
        if not operation:
            raise ValueError(f"Operation not found: {operation_id}")

        # Check state
        if operation.current_state != OperationState.AUTHORIZED:
            raise ValueError(
                f"Operation {operation_id} is not in AUTHORIZED state "
                f"(current: {operation.current_state.value})"
            )

        # Run safety checks before execution
        safety_results = await self.safety_manager.check_all(operation.context)
        operation.safety_check_results = safety_results

        # Log safety check results
        for result in safety_results:
            await self.audit_logger.log_safety_check(
                operation_id=operation_id,
                operation_type=operation.context.operation_type,
                agent_id=operation.context.agent_id,
                checkpoint_id=result.checkpoint_id,
                safe=result.safe,
                reason=result.reason,
            )

        # Check if all safety checks passed
        all_safe = self.safety_manager.is_safe(safety_results)

        if not all_safe:
            # Safety check failed - transition to FAILED
            self.state_machine.transition(
                operation,
                OperationState.FAILED,
                reason="Safety check failed"
            )

            await self.audit_logger.log_state_change(
                operation_id=operation_id,
                operation_type=operation.context.operation_type,
                agent_id=operation.context.agent_id,
                previous_state=OperationState.AUTHORIZED,
                new_state=OperationState.FAILED,
                reason="Safety check failed"
            )

            self.operations_failed += 1

            logger.error(f"❌ Safety check failed for operation: {operation_id}")

            return operation

        # Transition to EXECUTING
        self.state_machine.transition(
            operation,
            OperationState.EXECUTING,
            reason="Starting execution"
        )
        operation.execution_started_at = datetime.utcnow()

        await self.audit_logger.log_state_change(
            operation_id=operation_id,
            operation_type=operation.context.operation_type,
            agent_id=operation.context.agent_id,
            previous_state=OperationState.AUTHORIZED,
            new_state=OperationState.EXECUTING,
            reason="Starting execution"
        )

        # Execute operation
        try:
            result = await self._execute_operation_impl(operation)
            operation.execution_result = result

            # Transition to COMPLETED
            self.state_machine.transition(
                operation,
                OperationState.COMPLETED,
                reason="Execution succeeded"
            )
            operation.execution_completed_at = datetime.utcnow()

            await self.audit_logger.log_state_change(
                operation_id=operation_id,
                operation_type=operation.context.operation_type,
                agent_id=operation.context.agent_id,
                previous_state=OperationState.EXECUTING,
                new_state=OperationState.COMPLETED,
                reason="Execution succeeded"
            )

            self.operations_completed += 1

            logger.info(f"✅ Operation completed: {operation_id}")

        except Exception as e:
            # Execution failed
            operation.execution_error = str(e)

            self.state_machine.transition(
                operation,
                OperationState.FAILED,
                reason=f"Execution failed: {str(e)}"
            )
            operation.execution_completed_at = datetime.utcnow()

            await self.audit_logger.log_error(
                operation_id=operation_id,
                operation_type=operation.context.operation_type,
                agent_id=operation.context.agent_id,
                error_message=str(e),
                error_type="execution_error",
            )

            await self.audit_logger.log_state_change(
                operation_id=operation_id,
                operation_type=operation.context.operation_type,
                agent_id=operation.context.agent_id,
                previous_state=OperationState.EXECUTING,
                new_state=OperationState.FAILED,
                reason=f"Execution failed: {str(e)}"
            )

            self.operations_failed += 1

            logger.error(f"❌ Operation failed: {operation_id} - {str(e)}")

        return operation

    # ========================================================================
    # Helper Methods
    # ========================================================================

    async def _check_authorization_sufficient(
        self,
        operation: RepoOperation
    ) -> bool:
        """
        Check if granted authorization level is sufficient.

        Args:
            operation: Operation to check

        Returns:
            True if authorization is sufficient
        """
        # This is already checked by OperationTypeValidator
        # But we double-check here for defense in depth
        from .validators import OperationTypeValidator

        validator = OperationTypeValidator()
        result = await validator.validate(operation.context)

        return result.valid

    async def _check_policy(self, operation: RepoOperation) -> bool:
        """
        Check operation against policy engine.

        Args:
            operation: Operation to check

        Returns:
            True if policy allows, False otherwise
        """
        if not POLICY_ENGINE_AVAILABLE or not self.policy_engine:
            return True  # No policy engine - allow by default

        # Create policy evaluation context
        context = PolicyEvaluationContext(
            agent_id=operation.context.agent_id,
            agent_role=operation.context.agent_role,
            action=f"repo.{operation.context.operation_type.value}",
            resource=operation.context.repo_path,
            params=operation.context.params,
        )

        # Evaluate policy
        result = await self.policy_engine.evaluate(context)

        return result.allowed

    async def _execute_operation_impl(
        self,
        operation: RepoOperation
    ) -> Dict:
        """
        Execute the actual operation.

        This is a placeholder - actual implementation would use git commands.

        Args:
            operation: Operation to execute

        Returns:
            Execution result
        """
        # TODO: Implement actual git operations
        # For now, just return success

        operation_type = operation.context.operation_type

        logger.info(
            f"🔧 Executing {operation_type.value} "
            f"(operation={operation.operation_id})"
        )

        # Simulate execution
        return {
            "success": True,
            "operation_type": operation_type.value,
            "message": f"Simulated execution of {operation_type.value}",
        }

    # ========================================================================
    # Query Methods
    # ========================================================================

    async def get_operation(self, operation_id: str) -> Optional[RepoOperation]:
        """Get operation by ID"""
        return self.operations.get(operation_id)

    async def list_operations(
        self,
        limit: int = 100,
        state_filter: Optional[OperationState] = None
    ) -> List[RepoOperation]:
        """
        List operations.

        Args:
            limit: Maximum number of operations to return
            state_filter: Filter by state (optional)

        Returns:
            List of operations
        """
        operations = list(self.operations.values())

        # Filter by state
        if state_filter:
            operations = [
                op for op in operations
                if op.current_state == state_filter
            ]

        # Sort by creation time (newest first)
        operations.sort(key=lambda op: op.created_at, reverse=True)

        # Limit
        return operations[:limit]

    async def get_operation_status(
        self,
        operation_id: str
    ) -> OperationStatusResponse:
        """
        Get operation status with execution readiness check.

        Args:
            operation_id: Operation ID

        Returns:
            Operation status response

        Raises:
            ValueError: If operation not found
        """
        operation = self.operations.get(operation_id)
        if not operation:
            raise ValueError(f"Operation not found: {operation_id}")

        # Check if operation can be executed
        can_execute = operation.can_execute()

        # Collect blocking issues
        blocking_issues = []
        if not operation.authorization_granted:
            blocking_issues.append("Operation is not authorized")

        if not self.validator_manager.is_valid(operation.validation_results):
            blocking_issues.append("Validation failed")

        if operation.safety_check_results and not self.safety_manager.is_safe(
            operation.safety_check_results
        ):
            blocking_issues.append("Safety check failed")

        return OperationStatusResponse(
            operation=operation,
            can_execute=can_execute,
            blocking_issues=blocking_issues,
        )

    # ========================================================================
    # Statistics and Health
    # ========================================================================

    async def get_stats(self) -> AROStats:
        """Get ARO system statistics"""
        # Count operations by state
        operations_by_state: Dict[str, int] = {}
        for op in self.operations.values():
            state = op.current_state.value
            operations_by_state[state] = operations_by_state.get(state, 0) + 1

        # Count operations by type
        operations_by_type: Dict[str, int] = {}
        for op in self.operations.values():
            op_type = op.context.operation_type.value
            operations_by_type[op_type] = operations_by_type.get(op_type, 0) + 1

        # Calculate rates
        auth_rate = (
            self.operations_authorized / self.total_operations
            if self.total_operations > 0
            else 0.0
        )

        # Calculate validation pass rate
        total_validations = sum(
            len(op.validation_results) for op in self.operations.values()
        )
        passed_validations = sum(
            sum(1 for v in op.validation_results if v.valid)
            for op in self.operations.values()
        )
        validation_rate = (
            passed_validations / total_validations
            if total_validations > 0
            else 0.0
        )

        # Calculate safety check pass rate
        total_safety_checks = sum(
            len(op.safety_check_results) for op in self.operations.values()
        )
        passed_safety_checks = sum(
            sum(1 for s in op.safety_check_results if s.safe)
            for op in self.operations.values()
        )
        safety_rate = (
            passed_safety_checks / total_safety_checks
            if total_safety_checks > 0
            else 0.0
        )

        return AROStats(
            total_operations=self.total_operations,
            operations_by_state=operations_by_state,
            operations_by_type=operations_by_type,
            total_audit_entries=self.audit_logger.entry_count,
            authorization_grant_rate=auth_rate,
            validation_pass_rate=validation_rate,
            safety_check_pass_rate=safety_rate,
        )

    async def get_health(self) -> AROHealth:
        """Get ARO system health status"""
        # Check audit log integrity
        is_valid, _ = self.audit_logger.verify_chain_integrity()

        return AROHealth(
            status="healthy",
            operational=True,
            audit_log_integrity=is_valid,
            policy_engine_available=POLICY_ENGINE_AVAILABLE,
        )

    async def get_info(self) -> AROInfo:
        """Get ARO system information"""
        return AROInfo()


# ============================================================================
# Singleton Instance
# ============================================================================

_aro_service: Optional[AROService] = None


def get_aro_service() -> AROService:
    """Get the singleton ARO service instance"""
    global _aro_service
    if _aro_service is None:
        _aro_service = AROService()
    return _aro_service
