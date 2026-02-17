"""
Execution Node Base (Sprint 8.2)

Abstract base class for execution graph nodes.
Each node must implement execute(), rollback(), and dry_run().
"""

from abc import ABC, abstractmethod
from typing import Dict, Any, Optional, List
from datetime import datetime
import time
from loguru import logger

from app.modules.autonomous_pipeline.schemas import (
    ExecutionNodeSpec,
    ExecutionNodeResult,
    ExecutionNodeStatus,
    ExecutionCapability,
)


class ExecutionContext:
    """
    Execution context passed to all nodes.

    Contains shared state and configuration for the execution.
    """

    def __init__(
        self,
        graph_id: str,
        business_intent_id: str,
        dry_run: bool = False,
        audit_enabled: bool = True
    ):
        """
        Initialize execution context.

        Args:
            graph_id: Execution graph identifier
            business_intent_id: Business intent identifier
            dry_run: Execute in dry-run mode
            audit_enabled: Enable audit logging
        """
        self.graph_id = graph_id
        self.business_intent_id = business_intent_id
        self.dry_run = dry_run
        self.audit_enabled = audit_enabled

        # Shared state (for passing data between nodes)
        self.shared_state: Dict[str, Any] = {}

        # Artifacts generated during execution
        self.artifacts: List[str] = []

        # Audit events
        self.audit_events: List[Dict[str, Any]] = []

    def set_state(self, key: str, value: Any):
        """Set shared state value."""
        self.shared_state[key] = value

    def get_state(self, key: str, default: Any = None) -> Any:
        """Get shared state value."""
        return self.shared_state.get(key, default)

    def add_artifact(self, artifact_path: str):
        """Add generated artifact."""
        self.artifacts.append(artifact_path)

    def emit_audit_event(self, event: Dict[str, Any]):
        """Emit audit event."""
        if self.audit_enabled:
            event["timestamp"] = datetime.utcnow().isoformat()
            event["graph_id"] = self.graph_id
            self.audit_events.append(event)


class ExecutionNodeError(Exception):
    """Raised when node execution fails."""
    pass


class RollbackError(Exception):
    """Raised when rollback fails."""
    pass


class ExecutionNode(ABC):
    """
    Abstract base class for execution graph nodes.

    Contract:
    1. MUST implement execute() - main execution logic
    2. MUST implement dry_run() - simulation without side effects
    3. SHOULD implement rollback() - undo changes (if ROLLBACKABLE)
    4. MUST declare capabilities
    5. MUST emit audit events
    6. MUST respect timeouts
    7. MUST handle errors gracefully

    Fail-Closed Principles:
    - Invalid input → ExecutionNodeError → STOP
    - Execution error → ExecutionNodeError → ROLLBACK (if capable)
    - Timeout → ExecutionNodeError → ROLLBACK (if capable)
    """

    def __init__(self, spec: ExecutionNodeSpec):
        """
        Initialize execution node.

        Args:
            spec: Node specification
        """
        self.spec = spec
        self.node_id = spec.node_id
        self.name = spec.name
        self.capabilities = spec.capabilities

        logger.info(f"[{self.node_id}] Node initialized: {self.name}")

    async def execute_node(
        self,
        context: ExecutionContext
    ) -> ExecutionNodeResult:
        """
        Execute node with full lifecycle management.

        Args:
            context: Execution context

        Returns:
            ExecutionNodeResult

        Raises:
            ExecutionNodeError: If execution fails
        """
        logger.info(f"[{self.node_id}] Starting execution: {self.name}")

        start_time = time.time()
        result = ExecutionNodeResult(
            node_id=self.node_id,
            status=ExecutionNodeStatus.RUNNING,
            started_at=datetime.utcnow(),
            success=False,
            was_dry_run=context.dry_run,
        )

        try:
            # Emit start event
            context.emit_audit_event({
                "event_type": "node_execution_started",
                "node_id": self.node_id,
                "node_name": self.name,
                "dry_run": context.dry_run,
            })

            # Validate before execution
            self._validate_before_execution(context)

            # Execute (dry-run or real)
            if context.dry_run:
                if ExecutionCapability.DRY_RUN not in self.capabilities:
                    raise ExecutionNodeError(
                        f"Node {self.node_id} does not support dry-run mode"
                    )

                logger.info(f"[{self.node_id}] Executing in DRY-RUN mode")
                output, artifacts = await self.dry_run(context)
            else:
                logger.info(f"[{self.node_id}] Executing in LIVE mode")
                output, artifacts = await self.execute(context)

            # Success
            result.status = ExecutionNodeStatus.COMPLETED
            result.success = True
            result.output = output
            result.artifacts = artifacts
            result.completed_at = datetime.utcnow()
            result.duration_seconds = time.time() - start_time
            result.rollback_available = ExecutionCapability.ROLLBACKABLE in self.capabilities

            # Add artifacts to context
            for artifact in artifacts:
                context.add_artifact(artifact)

            # Emit success event
            context.emit_audit_event({
                "event_type": "node_execution_completed",
                "node_id": self.node_id,
                "node_name": self.name,
                "success": True,
                "duration_seconds": result.duration_seconds,
                "artifacts_count": len(artifacts),
            })

            logger.info(
                f"[{self.node_id}] Execution completed successfully "
                f"(duration={result.duration_seconds:.2f}s)"
            )

            return result

        except Exception as e:
            # Failure
            result.status = ExecutionNodeStatus.FAILED
            result.success = False
            result.error = str(e)
            result.completed_at = datetime.utcnow()
            result.duration_seconds = time.time() - start_time

            # Emit failure event
            context.emit_audit_event({
                "event_type": "node_execution_failed",
                "node_id": self.node_id,
                "node_name": self.name,
                "success": False,
                "error": str(e),
                "duration_seconds": result.duration_seconds,
            })

            logger.error(f"[{self.node_id}] Execution failed: {e}")

            raise ExecutionNodeError(f"Node {self.node_id} failed: {e}")

    async def rollback_node(
        self,
        context: ExecutionContext
    ) -> bool:
        """
        Rollback node execution.

        Args:
            context: Execution context

        Returns:
            True if rollback successful

        Raises:
            RollbackError: If rollback fails
        """
        if ExecutionCapability.ROLLBACKABLE not in self.capabilities:
            logger.warning(f"[{self.node_id}] Node is not rollbackable")
            return False

        logger.warning(f"[{self.node_id}] Starting rollback: {self.name}")

        try:
            # Emit rollback start event
            context.emit_audit_event({
                "event_type": "node_rollback_started",
                "node_id": self.node_id,
                "node_name": self.name,
            })

            # Execute rollback
            await self.rollback(context)

            # Emit rollback success event
            context.emit_audit_event({
                "event_type": "node_rollback_completed",
                "node_id": self.node_id,
                "node_name": self.name,
                "success": True,
            })

            logger.info(f"[{self.node_id}] Rollback completed successfully")

            return True

        except Exception as e:
            # Emit rollback failure event
            context.emit_audit_event({
                "event_type": "node_rollback_failed",
                "node_id": self.node_id,
                "node_name": self.name,
                "success": False,
                "error": str(e),
            })

            logger.error(f"[{self.node_id}] Rollback failed: {e}")

            raise RollbackError(f"Rollback failed for node {self.node_id}: {e}")

    @abstractmethod
    async def execute(
        self,
        context: ExecutionContext
    ) -> tuple[Dict[str, Any], List[str]]:
        """
        Execute node logic (LIVE mode).

        Args:
            context: Execution context

        Returns:
            Tuple of (output_data, artifact_paths)

        Raises:
            ExecutionNodeError: If execution fails
        """
        pass

    @abstractmethod
    async def dry_run(
        self,
        context: ExecutionContext
    ) -> tuple[Dict[str, Any], List[str]]:
        """
        Simulate node execution without side effects (DRY-RUN mode).

        Args:
            context: Execution context

        Returns:
            Tuple of (simulated_output_data, simulated_artifact_paths)
        """
        pass

    async def rollback(self, context: ExecutionContext):
        """
        Rollback node execution (optional implementation).

        Args:
            context: Execution context

        Raises:
            RollbackError: If rollback fails
        """
        raise NotImplementedError(
            f"Node {self.node_id} does not implement rollback (not ROLLBACKABLE)"
        )

    def _validate_before_execution(self, context: ExecutionContext):
        """
        Validate before execution (fail-closed).

        Args:
            context: Execution context

        Raises:
            ExecutionNodeError: If validation fails
        """
        # Check required dependencies in shared state
        # (Override in subclasses for specific validation)
        pass

    def __repr__(self) -> str:
        """String representation."""
        return f"<ExecutionNode {self.node_id}: {self.name}>"
