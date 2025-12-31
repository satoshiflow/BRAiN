"""
NeuroRail Lifecycle API Router.

Provides REST endpoints for:
- Executing state transitions
- Querying current state
- Viewing state history
"""

from fastapi import APIRouter, HTTPException, status, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.core.database import get_db
from backend.app.modules.neurorail.lifecycle.service import (
    LifecycleService,
    get_lifecycle_service,
)
from backend.app.modules.neurorail.lifecycle.schemas import (
    StateTransitionEvent,
    TransitionRequest,
    EntityStateResponse,
    StateHistoryResponse,
    get_allowed_transitions,
)
from backend.app.modules.neurorail.errors import NeuroRailError

router = APIRouter(prefix="/api/neurorail/v1/lifecycle", tags=["NeuroRail Lifecycle"])


# ============================================================================
# State Transition Endpoints
# ============================================================================

@router.post("/{entity_type}/{entity_id}/transition", response_model=StateTransitionEvent)
async def execute_transition(
    entity_type: str,
    entity_id: str,
    request: TransitionRequest,
    db: AsyncSession = Depends(get_db),
    service: LifecycleService = Depends(get_lifecycle_service)
) -> StateTransitionEvent:
    """
    Execute a state transition for an entity.

    Args:
        entity_type: Entity type (mission, job, attempt)
        entity_id: Entity identifier
        request: Transition request with action and metadata

    Returns:
        State transition event

    Raises:
        400: Invalid transition (state machine rules violated)
        500: Server error
    """
    valid_types = ["mission", "job", "attempt"]
    if entity_type not in valid_types:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid entity type. Must be one of: {', '.join(valid_types)}"
        )

    # Override entity_id in request to match URL parameter
    request.entity_id = entity_id

    try:
        return await service.transition(entity_type, request, db)
    except NeuroRailError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=e.to_dict()
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to execute transition: {str(e)}"
        )


# ============================================================================
# State Query Endpoints
# ============================================================================

@router.get("/{entity_type}/{entity_id}/state", response_model=EntityStateResponse)
async def get_current_state(
    entity_type: str,
    entity_id: str,
    service: LifecycleService = Depends(get_lifecycle_service)
) -> EntityStateResponse:
    """
    Get current state of an entity.

    Args:
        entity_type: Entity type (mission, job, attempt)
        entity_id: Entity identifier

    Returns:
        Current state and metadata

    Raises:
        404: Entity not found
    """
    valid_types = ["mission", "job", "attempt"]
    if entity_type not in valid_types:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid entity type. Must be one of: {', '.join(valid_types)}"
        )

    current_state = await service.get_current_state(entity_type, entity_id)

    if not current_state:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"{entity_type.capitalize()} {entity_id} not found"
        )

    # Get allowed next states
    allowed = get_allowed_transitions(entity_type, current_state)

    return EntityStateResponse(
        entity_type=entity_type,
        entity_id=entity_id,
        current_state=current_state,
        updated_at=datetime.utcnow(),
        metadata={"allowed_transitions": allowed}
    )


@router.get("/{entity_type}/{entity_id}/history", response_model=StateHistoryResponse)
async def get_state_history(
    entity_type: str,
    entity_id: str,
    limit: int = 100,
    db: AsyncSession = Depends(get_db),
    service: LifecycleService = Depends(get_lifecycle_service)
) -> StateHistoryResponse:
    """
    Get state transition history for an entity.

    Args:
        entity_type: Entity type (mission, job, attempt)
        entity_id: Entity identifier
        limit: Maximum number of transitions to return (default 100)

    Returns:
        State history with all transitions

    Raises:
        400: Invalid entity type
    """
    valid_types = ["mission", "job", "attempt"]
    if entity_type not in valid_types:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid entity type. Must be one of: {', '.join(valid_types)}"
        )

    try:
        return await service.get_state_history(entity_type, entity_id, db, limit)
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get state history: {str(e)}"
        )


# Need to import datetime for current_state response
from datetime import datetime
