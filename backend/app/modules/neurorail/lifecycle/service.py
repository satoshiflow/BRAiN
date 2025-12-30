"""
NeuroRail Lifecycle Service.

Manages entity state transitions with:
- State machine validation (prevent illegal transitions)
- Redis storage for current state (hot data)
- PostgreSQL storage for transition history (audit trail)
- Event emission for observability
"""

from __future__ import annotations
import json
from typing import Optional, List, Dict, Any
from datetime import datetime
from loguru import logger
import redis.asyncio as redis
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.core.redis_client import get_redis
from backend.app.core.database import get_db
from backend.app.modules.neurorail.lifecycle.schemas import (
    MissionState,
    JobState,
    AttemptState,
    StateTransitionEvent,
    TransitionRequest,
    EntityStateResponse,
    StateHistoryResponse,
    is_valid_transition,
    get_allowed_transitions,
)
from backend.app.modules.neurorail.errors import (
    NeuroRailError,
    NeuroRailErrorCode,
)


class LifecycleService:
    """
    Service for managing entity lifecycle and state transitions.

    Responsibilities:
    - Validate state transitions against state machine rules
    - Store current state in Redis (fast access)
    - Persist state history in PostgreSQL (audit trail)
    - Emit transition events for observability
    """

    # Redis key prefixes
    KEY_PREFIX_STATE = "neurorail:state:"

    def __init__(self):
        self.redis: Optional[redis.Redis] = None

    async def _get_redis(self) -> redis.Redis:
        """Get Redis client (lazy initialization)."""
        if self.redis is None:
            self.redis = await get_redis()
        return self.redis

    # ========================================================================
    # Current State Management
    # ========================================================================

    async def get_current_state(
        self,
        entity_type: str,
        entity_id: str
    ) -> Optional[str]:
        """
        Get current state of an entity.

        Args:
            entity_type: Entity type (mission, job, attempt)
            entity_id: Entity identifier

        Returns:
            Current state or None if not found
        """
        redis_client = await self._get_redis()
        key = f"{self.KEY_PREFIX_STATE}{entity_type}:{entity_id}"

        state = await redis_client.get(key)
        return state

    async def _set_current_state(
        self,
        entity_type: str,
        entity_id: str,
        state: str
    ) -> None:
        """Set current state in Redis."""
        redis_client = await self._get_redis()
        key = f"{self.KEY_PREFIX_STATE}{entity_type}:{entity_id}"

        # Store with 24h TTL
        await redis_client.setex(key, 24 * 60 * 60, state)

    # ========================================================================
    # State Transitions
    # ========================================================================

    async def transition(
        self,
        entity_type: str,
        request: TransitionRequest,
        db: AsyncSession
    ) -> StateTransitionEvent:
        """
        Execute a state transition.

        Args:
            entity_type: Entity type (mission, job, attempt)
            request: Transition request
            db: Database session for audit trail

        Returns:
            State transition event

        Raises:
            NeuroRailError: If transition is invalid
        """
        # Get current state
        current_state = await self.get_current_state(entity_type, request.entity_id)

        # Map transition action to target state
        target_state = self._get_target_state(
            entity_type,
            current_state,
            request.transition,
            request.metadata
        )

        # Validate transition
        if not is_valid_transition(entity_type, current_state, target_state):
            allowed = get_allowed_transitions(entity_type, current_state)
            raise NeuroRailError(
                code=NeuroRailErrorCode.INVALID_STATE_TRANSITION,
                message=f"Invalid transition for {entity_type} {request.entity_id}: "
                       f"{current_state} → {target_state}. "
                       f"Allowed next states: {allowed}",
                details={
                    "entity_type": entity_type,
                    "entity_id": request.entity_id,
                    "current_state": current_state,
                    "target_state": target_state,
                    "allowed_states": allowed,
                }
            )

        # Create transition event
        event = StateTransitionEvent(
            entity_type=entity_type,
            entity_id=request.entity_id,
            from_state=current_state,
            to_state=target_state,
            transition=request.transition,
            metadata=request.metadata,
            caused_by=request.caused_by,
        )

        # Update current state in Redis
        await self._set_current_state(entity_type, request.entity_id, target_state)

        # Persist to PostgreSQL
        await self._persist_transition(event, db)

        logger.info(
            f"State transition: {entity_type} {request.entity_id} "
            f"{current_state} → {target_state} (action: {request.transition})"
        )

        return event

    def _get_target_state(
        self,
        entity_type: str,
        current_state: Optional[str],
        transition: str,
        metadata: Dict[str, Any]
    ) -> str:
        """
        Map transition action to target state.

        This implements the business logic for state machine transitions.
        """
        # Creation transitions
        if transition == "create":
            if entity_type == "mission":
                return MissionState.PENDING
            elif entity_type == "job":
                return JobState.PENDING
            elif entity_type == "attempt":
                return AttemptState.CREATED
            else:
                raise ValueError(f"Unknown entity type: {entity_type}")

        # Common transitions
        if transition == "start":
            if entity_type == "mission":
                return MissionState.PLANNING
            elif entity_type == "job":
                return JobState.RUNNING
            elif entity_type == "attempt":
                return AttemptState.RUNNING

        elif transition == "plan_ready":
            return MissionState.PLANNED

        elif transition == "execute":
            return MissionState.EXECUTING

        elif transition == "dependencies_met":
            return JobState.READY

        elif transition == "complete":
            if entity_type == "mission":
                return MissionState.COMPLETED
            elif entity_type == "job":
                return JobState.SUCCEEDED
            elif entity_type == "attempt":
                return AttemptState.SUCCEEDED

        elif transition == "fail":
            # Determine failure type from metadata
            error_category = metadata.get("error_category", "mechanical")

            if entity_type == "mission":
                return MissionState.FAILED
            elif entity_type == "job":
                if error_category == "ethical":
                    return JobState.FAILED_ETHICAL
                else:
                    return JobState.FAILED_MECHANICAL
            elif entity_type == "attempt":
                error_code = metadata.get("error_code", "")
                if "TIMEOUT" in error_code:
                    return AttemptState.FAILED_TIMEOUT
                elif "RESOURCE" in error_code:
                    return AttemptState.FAILED_RESOURCE
                else:
                    return AttemptState.FAILED_ERROR

        elif transition == "timeout":
            if entity_type == "mission":
                return MissionState.TIMEOUT
            elif entity_type == "job":
                return JobState.TIMEOUT
            elif entity_type == "attempt":
                return AttemptState.FAILED_TIMEOUT

        elif transition == "cancel":
            if entity_type == "mission":
                return MissionState.CANCELLED
            elif entity_type == "job":
                return JobState.CANCELLED
            # Attempts cannot be cancelled directly

        elif transition == "retry":
            # Only jobs can be retried (from FAILED_MECHANICAL)
            if entity_type == "job":
                return JobState.RUNNING
            else:
                raise ValueError(f"Retry not supported for {entity_type}")

        raise ValueError(f"Unknown transition: {transition}")

    async def _persist_transition(
        self,
        event: StateTransitionEvent,
        db: AsyncSession
    ) -> None:
        """Persist state transition to PostgreSQL."""
        query = text("""
            INSERT INTO neurorail_state_transitions
                (event_id, entity_type, entity_id, from_state, to_state,
                 transition, timestamp, metadata, caused_by, created_at)
            VALUES
                (:event_id, :entity_type, :entity_id, :from_state, :to_state,
                 :transition, :timestamp, :metadata, :caused_by, NOW())
        """)

        await db.execute(query, {
            "event_id": event.event_id,
            "entity_type": event.entity_type,
            "entity_id": event.entity_id,
            "from_state": event.from_state,
            "to_state": event.to_state,
            "transition": event.transition,
            "timestamp": event.timestamp,
            "metadata": json.dumps(event.metadata),
            "caused_by": event.caused_by,
        })
        await db.commit()

    # ========================================================================
    # State History
    # ========================================================================

    async def get_state_history(
        self,
        entity_type: str,
        entity_id: str,
        db: AsyncSession,
        limit: int = 100
    ) -> StateHistoryResponse:
        """
        Get state transition history for an entity.

        Args:
            entity_type: Entity type
            entity_id: Entity identifier
            db: Database session
            limit: Maximum number of transitions to return

        Returns:
            State history with transitions
        """
        query = text("""
            SELECT
                event_id, entity_type, entity_id, from_state, to_state,
                transition, timestamp, metadata, caused_by
            FROM neurorail_state_transitions
            WHERE entity_type = :entity_type AND entity_id = :entity_id
            ORDER BY timestamp ASC
            LIMIT :limit
        """)

        result = await db.execute(query, {
            "entity_type": entity_type,
            "entity_id": entity_id,
            "limit": limit,
        })

        rows = result.fetchall()

        transitions = [
            StateTransitionEvent(
                event_id=row[0],
                entity_type=row[1],
                entity_id=row[2],
                from_state=row[3],
                to_state=row[4],
                transition=row[5],
                timestamp=row[6],
                metadata=json.loads(row[7]) if row[7] else {},
                caused_by=row[8],
            )
            for row in rows
        ]

        return StateHistoryResponse(
            entity_type=entity_type,
            entity_id=entity_id,
            transitions=transitions,
            total_transitions=len(transitions),
        )


# Singleton instance
_lifecycle_service: Optional[LifecycleService] = None


def get_lifecycle_service() -> LifecycleService:
    """Get singleton lifecycle service instance."""
    global _lifecycle_service
    if _lifecycle_service is None:
        _lifecycle_service = LifecycleService()
    return _lifecycle_service
