"""
Event Sourcing Events for BRAiN Credit System.

Implements Event Sourcing Standard with:
- Immutable event envelopes
- Causality tracking (correlation_id, causation_id)
- Idempotency keys for duplicate prevention
- Schema versioning for forward compatibility

Event Contract v1:
- All events are immutable (frozen=True)
- All events have UTC timestamps
- All events track actor_id (who caused the event)
- All events have correlation_id (groups related events)
- All events have idempotency_key (prevents duplicates)
"""

from __future__ import annotations

from datetime import datetime, timezone
from enum import Enum
from typing import Any, Dict, Optional
from uuid import uuid4

from pydantic import BaseModel, Field


class EventType(str, Enum):
    """
    Event types in the BRAiN Credit System.

    Naming Convention: <domain>.<action>_<object>
    Examples: credit.allocated, approval.approved
    """

    # === Ledger Events ===
    CREDIT_ALLOCATED = "credit.allocated"
    """Initial credit allocation to entity (agent, mission, pool)."""

    CREDIT_CONSUMED = "credit.consumed"
    """Credits consumed for mission execution."""

    CREDIT_REFUNDED = "credit.refunded"
    """Credits refunded after failed/cancelled mission."""

    CREDIT_WITHDRAWN = "credit.withdrawn"
    """Credits withdrawn from entity (e.g., agent decommissioned)."""

    CREDIT_REGENERATED = "credit.regenerated"
    """Credits regenerated over time (Phase 8 feature)."""

    # === Approval Events ===
    APPROVAL_REQUESTED = "approval.requested"
    """Human approval requested for high-risk action."""

    APPROVAL_APPROVED = "approval.approved"
    """Human approver approved the request."""

    APPROVAL_REJECTED = "approval.rejected"
    """Human approver rejected the request."""

    APPROVAL_EXPIRED = "approval.expired"
    """Approval request expired without decision."""

    # === Synergie Events ===
    COLLABORATION_RECORDED = "synergie.collaboration_recorded"
    """Agent collaboration recorded for synergie bonus."""

    REUSE_DETECTED = "synergie.reuse_detected"
    """Solution reuse detected (e.g., code reuse, knowledge transfer)."""

    # === EoC Events ===
    EOC_REGULATED = "eoc.regulated"
    """Energy of Consciousness regulation applied."""

    # === Mission Events ===
    MISSION_RATED = "mission.rated"
    """Mission performance rating recorded."""


class EventEnvelope(BaseModel):
    """
    Immutable event envelope following Event Sourcing Standard.

    Properties:
    - Immutability: frozen=True prevents mutation after creation
    - Causality: correlation_id groups related events, causation_id tracks cause
    - Idempotency: idempotency_key prevents duplicate processing
    - Versioning: schema_version enables forward compatibility

    Examples:
        >>> event = EventEnvelope(
        ...     event_id=str(uuid4()),
        ...     event_type=EventType.CREDIT_ALLOCATED,
        ...     timestamp=datetime.now(timezone.utc),
        ...     actor_id="system",
        ...     correlation_id="agent_123",
        ...     causation_id=None,
        ...     payload={"entity_id": "agent_123", "amount": 100.0},
        ...     schema_version=1,
        ...     idempotency_key="agent_123:allocation:2025-12-30T15:30:00Z"
        ... )
    """

    # === Identity ===
    event_id: str = Field(
        ...,
        description="Unique event identifier (UUID v4)",
    )

    event_type: EventType = Field(
        ...,
        description="Type of event (from EventType enum)",
    )

    # === Causality ===
    timestamp: datetime = Field(
        ...,
        description="UTC timestamp when event occurred",
    )

    actor_id: str = Field(
        ...,
        description="Who caused this event (agent_id, user_id, or 'system')",
    )

    correlation_id: str = Field(
        ...,
        description="Groups related events (e.g., mission_id, agent_id)",
    )

    causation_id: Optional[str] = Field(
        None,
        description="event_id that caused this event (for event chains)",
    )

    # === Payload ===
    payload: Dict[str, Any] = Field(
        ...,
        description="Event-specific data (validated by event handlers)",
    )

    # === Versioning ===
    schema_version: int = Field(
        1,
        description="Event schema version (for forward compatibility)",
    )

    # === Idempotency ===
    idempotency_key: str = Field(
        ...,
        description="Prevents duplicate processing (retry safety)",
    )

    class Config:
        frozen = True  # Immutable
        json_encoders = {
            datetime: lambda v: v.isoformat(),
        }


# ============================================================================
# Event Creation Helpers
# ============================================================================
# These functions provide type-safe event construction with sensible defaults.


def _now_utc() -> datetime:
    """Get current UTC timestamp."""
    return datetime.now(timezone.utc)


def _generate_event_id() -> str:
    """Generate unique event ID (UUID v4)."""
    return str(uuid4())


# === Ledger Event Creators ===


def create_credit_allocated_event(
    entity_id: str,
    entity_type: str,
    amount: float,
    reason: str,
    balance_after: float,
    actor_id: str = "system",
    causation_id: Optional[str] = None,
) -> EventEnvelope:
    """
    Create CREDIT_ALLOCATED event.

    Args:
        entity_id: Entity receiving credits (agent_id, mission_id, pool_id)
        entity_type: Type of entity ("agent", "mission", "pool")
        amount: Credits allocated (must be > 0)
        reason: Why credits were allocated
        balance_after: Entity balance after allocation
        actor_id: Who allocated credits (default: "system")
        causation_id: Event that caused this allocation (optional)

    Returns:
        EventEnvelope with CREDIT_ALLOCATED event
    """
    timestamp = _now_utc()
    return EventEnvelope(
        event_id=_generate_event_id(),
        event_type=EventType.CREDIT_ALLOCATED,
        timestamp=timestamp,
        actor_id=actor_id,
        correlation_id=entity_id,
        causation_id=causation_id,
        payload={
            "entity_id": entity_id,
            "entity_type": entity_type,
            "amount": amount,
            "reason": reason,
            "balance_after": balance_after,
        },
        schema_version=1,
        idempotency_key=f"{entity_id}:allocation:{timestamp.isoformat()}",
    )


def create_credit_consumed_event(
    entity_id: str,
    entity_type: str,
    amount: float,
    reason: str,
    balance_after: float,
    mission_id: Optional[str] = None,
    actor_id: str = "system",
    causation_id: Optional[str] = None,
) -> EventEnvelope:
    """
    Create CREDIT_CONSUMED event.

    Args:
        entity_id: Entity consuming credits
        entity_type: Type of entity
        amount: Credits consumed (must be > 0)
        reason: Why credits were consumed
        balance_after: Entity balance after consumption
        mission_id: Related mission (if applicable)
        actor_id: Who initiated consumption
        causation_id: Event that caused this consumption

    Returns:
        EventEnvelope with CREDIT_CONSUMED event
    """
    timestamp = _now_utc()
    payload = {
        "entity_id": entity_id,
        "entity_type": entity_type,
        "amount": amount,
        "reason": reason,
        "balance_after": balance_after,
    }
    if mission_id:
        payload["mission_id"] = mission_id

    return EventEnvelope(
        event_id=_generate_event_id(),
        event_type=EventType.CREDIT_CONSUMED,
        timestamp=timestamp,
        actor_id=actor_id,
        correlation_id=mission_id or entity_id,
        causation_id=causation_id,
        payload=payload,
        schema_version=1,
        idempotency_key=f"{entity_id}:consumption:{timestamp.isoformat()}",
    )


def create_credit_refunded_event(
    entity_id: str,
    entity_type: str,
    amount: float,
    reason: str,
    balance_after: float,
    mission_id: Optional[str] = None,
    actor_id: str = "system",
    causation_id: Optional[str] = None,
) -> EventEnvelope:
    """
    Create CREDIT_REFUNDED event.

    Args:
        entity_id: Entity receiving refund
        entity_type: Type of entity
        amount: Credits refunded (must be > 0)
        reason: Why credits were refunded
        balance_after: Entity balance after refund
        mission_id: Related mission (if applicable)
        actor_id: Who initiated refund
        causation_id: Event that caused this refund

    Returns:
        EventEnvelope with CREDIT_REFUNDED event
    """
    timestamp = _now_utc()
    payload = {
        "entity_id": entity_id,
        "entity_type": entity_type,
        "amount": amount,
        "reason": reason,
        "balance_after": balance_after,
    }
    if mission_id:
        payload["mission_id"] = mission_id

    return EventEnvelope(
        event_id=_generate_event_id(),
        event_type=EventType.CREDIT_REFUNDED,
        timestamp=timestamp,
        actor_id=actor_id,
        correlation_id=mission_id or entity_id,
        causation_id=causation_id,
        payload=payload,
        schema_version=1,
        idempotency_key=f"{entity_id}:refund:{timestamp.isoformat()}",
    )


def create_credit_withdrawn_event(
    entity_id: str,
    entity_type: str,
    amount: float,
    reason: str,
    balance_after: float,
    actor_id: str = "system",
    causation_id: Optional[str] = None,
) -> EventEnvelope:
    """
    Create CREDIT_WITHDRAWN event.

    Args:
        entity_id: Entity losing credits
        entity_type: Type of entity
        amount: Credits withdrawn (can result in negative balance)
        reason: Why credits were withdrawn
        balance_after: Entity balance after withdrawal
        actor_id: Who initiated withdrawal
        causation_id: Event that caused this withdrawal

    Returns:
        EventEnvelope with CREDIT_WITHDRAWN event
    """
    timestamp = _now_utc()
    return EventEnvelope(
        event_id=_generate_event_id(),
        event_type=EventType.CREDIT_WITHDRAWN,
        timestamp=timestamp,
        actor_id=actor_id,
        correlation_id=entity_id,
        causation_id=causation_id,
        payload={
            "entity_id": entity_id,
            "entity_type": entity_type,
            "amount": amount,
            "reason": reason,
            "balance_after": balance_after,
        },
        schema_version=1,
        idempotency_key=f"{entity_id}:withdrawal:{timestamp.isoformat()}",
    )


def create_credit_regenerated_event(
    entity_id: str,
    entity_type: str,
    amount: float,
    balance_after: float,
    actor_id: str = "system",
    causation_id: Optional[str] = None,
) -> EventEnvelope:
    """
    Create CREDIT_REGENERATED event (Phase 8 feature).

    Args:
        entity_id: Entity regenerating credits
        entity_type: Type of entity
        amount: Credits regenerated
        balance_after: Entity balance after regeneration
        actor_id: Who triggered regeneration
        causation_id: Event that caused this regeneration

    Returns:
        EventEnvelope with CREDIT_REGENERATED event
    """
    timestamp = _now_utc()
    return EventEnvelope(
        event_id=_generate_event_id(),
        event_type=EventType.CREDIT_REGENERATED,
        timestamp=timestamp,
        actor_id=actor_id,
        correlation_id=entity_id,
        causation_id=causation_id,
        payload={
            "entity_id": entity_id,
            "entity_type": entity_type,
            "amount": amount,
            "balance_after": balance_after,
        },
        schema_version=1,
        idempotency_key=f"{entity_id}:regeneration:{timestamp.isoformat()}",
    )


# === Approval Event Creators ===


def create_approval_requested_event(
    request_id: str,
    action_type: str,
    action_context: Dict[str, Any],
    requester_id: str,
    risk_level: str,
    actor_id: str,
    causation_id: Optional[str] = None,
) -> EventEnvelope:
    """
    Create APPROVAL_REQUESTED event.

    Args:
        request_id: Unique approval request ID
        action_type: Type of action requiring approval
        action_context: Context data for approval decision
        requester_id: Entity requesting approval
        risk_level: Risk level (LOW, MEDIUM, HIGH, CRITICAL)
        actor_id: Who initiated the request
        causation_id: Event that caused this request

    Returns:
        EventEnvelope with APPROVAL_REQUESTED event
    """
    timestamp = _now_utc()
    return EventEnvelope(
        event_id=_generate_event_id(),
        event_type=EventType.APPROVAL_REQUESTED,
        timestamp=timestamp,
        actor_id=actor_id,
        correlation_id=request_id,
        causation_id=causation_id,
        payload={
            "request_id": request_id,
            "action_type": action_type,
            "action_context": action_context,
            "requester_id": requester_id,
            "risk_level": risk_level,
        },
        schema_version=1,
        idempotency_key=f"{request_id}:requested:{requester_id}",
    )


def create_approval_approved_event(
    request_id: str,
    approver_id: str,
    justification: str,
    action_type: str,
    actor_id: str,
    causation_id: Optional[str] = None,
) -> EventEnvelope:
    """
    Create APPROVAL_APPROVED event.

    Args:
        request_id: Approval request ID
        approver_id: Who approved the request
        justification: Why it was approved
        action_type: Type of action approved
        actor_id: System actor (usually same as approver_id)
        causation_id: APPROVAL_REQUESTED event_id

    Returns:
        EventEnvelope with APPROVAL_APPROVED event
    """
    timestamp = _now_utc()
    return EventEnvelope(
        event_id=_generate_event_id(),
        event_type=EventType.APPROVAL_APPROVED,
        timestamp=timestamp,
        actor_id=actor_id,
        correlation_id=request_id,
        causation_id=causation_id,
        payload={
            "request_id": request_id,
            "approver_id": approver_id,
            "justification": justification,
            "action_type": action_type,
        },
        schema_version=1,
        idempotency_key=f"{request_id}:approved:{approver_id}",
    )


def create_approval_rejected_event(
    request_id: str,
    approver_id: str,
    justification: str,
    action_type: str,
    actor_id: str,
    causation_id: Optional[str] = None,
) -> EventEnvelope:
    """
    Create APPROVAL_REJECTED event.

    Args:
        request_id: Approval request ID
        approver_id: Who rejected the request
        justification: Why it was rejected
        action_type: Type of action rejected
        actor_id: System actor (usually same as approver_id)
        causation_id: APPROVAL_REQUESTED event_id

    Returns:
        EventEnvelope with APPROVAL_REJECTED event
    """
    timestamp = _now_utc()
    return EventEnvelope(
        event_id=_generate_event_id(),
        event_type=EventType.APPROVAL_REJECTED,
        timestamp=timestamp,
        actor_id=actor_id,
        correlation_id=request_id,
        causation_id=causation_id,
        payload={
            "request_id": request_id,
            "approver_id": approver_id,
            "justification": justification,
            "action_type": action_type,
        },
        schema_version=1,
        idempotency_key=f"{request_id}:rejected:{approver_id}",
    )


def create_approval_expired_event(
    request_id: str,
    action_type: str,
    actor_id: str = "system",
    causation_id: Optional[str] = None,
) -> EventEnvelope:
    """
    Create APPROVAL_EXPIRED event.

    Args:
        request_id: Approval request ID
        action_type: Type of action that expired
        actor_id: System actor (default: "system")
        causation_id: APPROVAL_REQUESTED event_id

    Returns:
        EventEnvelope with APPROVAL_EXPIRED event
    """
    timestamp = _now_utc()
    return EventEnvelope(
        event_id=_generate_event_id(),
        event_type=EventType.APPROVAL_EXPIRED,
        timestamp=timestamp,
        actor_id=actor_id,
        correlation_id=request_id,
        causation_id=causation_id,
        payload={
            "request_id": request_id,
            "action_type": action_type,
        },
        schema_version=1,
        idempotency_key=f"{request_id}:expired",
    )


# === Synergie Event Creators ===


def create_collaboration_recorded_event(
    collaboration_id: str,
    agent_ids: list[str],
    mission_id: str,
    contribution_scores: Dict[str, float],
    actor_id: str = "system",
    causation_id: Optional[str] = None,
) -> EventEnvelope:
    """
    Create COLLABORATION_RECORDED event.

    Args:
        collaboration_id: Unique collaboration ID
        agent_ids: Agents involved in collaboration
        mission_id: Related mission
        contribution_scores: Contribution score per agent
        actor_id: Who recorded collaboration
        causation_id: Event that caused this recording

    Returns:
        EventEnvelope with COLLABORATION_RECORDED event
    """
    timestamp = _now_utc()
    return EventEnvelope(
        event_id=_generate_event_id(),
        event_type=EventType.COLLABORATION_RECORDED,
        timestamp=timestamp,
        actor_id=actor_id,
        correlation_id=mission_id,
        causation_id=causation_id,
        payload={
            "collaboration_id": collaboration_id,
            "agent_ids": agent_ids,
            "mission_id": mission_id,
            "contribution_scores": contribution_scores,
        },
        schema_version=1,
        idempotency_key=f"{collaboration_id}:recorded",
    )


def create_reuse_detected_event(
    reuse_id: str,
    source_agent_id: str,
    reusing_agent_id: str,
    artifact_type: str,
    artifact_id: str,
    similarity_score: float,
    actor_id: str = "system",
    causation_id: Optional[str] = None,
) -> EventEnvelope:
    """
    Create REUSE_DETECTED event.

    Args:
        reuse_id: Unique reuse detection ID
        source_agent_id: Agent who created original artifact
        reusing_agent_id: Agent reusing the artifact
        artifact_type: Type of artifact (code, knowledge, solution)
        artifact_id: Unique artifact identifier
        similarity_score: Similarity score (0.0 - 1.0)
        actor_id: Who detected reuse
        causation_id: Event that caused this detection

    Returns:
        EventEnvelope with REUSE_DETECTED event
    """
    timestamp = _now_utc()
    return EventEnvelope(
        event_id=_generate_event_id(),
        event_type=EventType.REUSE_DETECTED,
        timestamp=timestamp,
        actor_id=actor_id,
        correlation_id=artifact_id,
        causation_id=causation_id,
        payload={
            "reuse_id": reuse_id,
            "source_agent_id": source_agent_id,
            "reusing_agent_id": reusing_agent_id,
            "artifact_type": artifact_type,
            "artifact_id": artifact_id,
            "similarity_score": similarity_score,
        },
        schema_version=1,
        idempotency_key=f"{reuse_id}:detected",
    )


# === EoC Event Creators ===


def create_eoc_regulated_event(
    entity_id: str,
    regulation_type: str,
    adjustment_amount: float,
    reason: str,
    actor_id: str = "system",
    causation_id: Optional[str] = None,
) -> EventEnvelope:
    """
    Create EOC_REGULATED event.

    Args:
        entity_id: Entity being regulated
        regulation_type: Type of regulation (increase, decrease, reset)
        adjustment_amount: EoC adjustment amount
        reason: Why regulation occurred
        actor_id: Who triggered regulation
        causation_id: Event that caused this regulation

    Returns:
        EventEnvelope with EOC_REGULATED event
    """
    timestamp = _now_utc()
    return EventEnvelope(
        event_id=_generate_event_id(),
        event_type=EventType.EOC_REGULATED,
        timestamp=timestamp,
        actor_id=actor_id,
        correlation_id=entity_id,
        causation_id=causation_id,
        payload={
            "entity_id": entity_id,
            "regulation_type": regulation_type,
            "adjustment_amount": adjustment_amount,
            "reason": reason,
        },
        schema_version=1,
        idempotency_key=f"{entity_id}:eoc_regulation:{timestamp.isoformat()}",
    )


# === Mission Event Creators ===


def create_mission_rated_event(
    mission_id: str,
    agent_id: str,
    rating_score: float,
    rating_category: str,
    rater_id: str,
    actor_id: str,
    causation_id: Optional[str] = None,
) -> EventEnvelope:
    """
    Create MISSION_RATED event.

    Args:
        mission_id: Mission being rated
        agent_id: Agent who executed mission
        rating_score: Rating score (0.0 - 1.0)
        rating_category: Category of rating (quality, speed, efficiency)
        rater_id: Who provided the rating
        actor_id: System actor
        causation_id: Event that caused this rating

    Returns:
        EventEnvelope with MISSION_RATED event
    """
    timestamp = _now_utc()
    return EventEnvelope(
        event_id=_generate_event_id(),
        event_type=EventType.MISSION_RATED,
        timestamp=timestamp,
        actor_id=actor_id,
        correlation_id=mission_id,
        causation_id=causation_id,
        payload={
            "mission_id": mission_id,
            "agent_id": agent_id,
            "rating_score": rating_score,
            "rating_category": rating_category,
            "rater_id": rater_id,
        },
        schema_version=1,
        idempotency_key=f"{mission_id}:rated:{rater_id}:{rating_category}",
    )
