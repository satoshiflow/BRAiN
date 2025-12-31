"""
Projections - In-Memory Read Models.

Implements CQRS Query Side:
- BalanceProjection: Current balance per entity
- LedgerProjection: Transaction history
- ApprovalProjection: Approval request states
- SynergieProjection: Collaboration statistics

Design:
- Projections subscribe to EventBus
- Rebuild from events on startup (replay)
- In-memory for low-latency reads
- Eventually consistent with event log

Invariants:
- Balance = Sum(all credit deltas)
- No NaN, Inf, or None balances
- Transaction history ordered by timestamp
"""

from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass, field
from datetime import datetime
from typing import Dict, List, Optional

from loguru import logger

from backend.app.modules.credits.event_sourcing.events import (
    EventEnvelope,
    EventType,
)


@dataclass
class LedgerEntry:
    """Single ledger entry (transaction)."""

    event_id: str
    timestamp: datetime
    entity_id: str
    entity_type: str
    amount: float  # Positive for credits added, negative for consumed
    balance_after: float
    reason: str
    mission_id: Optional[str] = None


@dataclass
class ApprovalRequest:
    """Approval request state."""

    request_id: str
    action_type: str
    requester_id: str
    risk_level: str
    status: str  # "pending", "approved", "rejected", "expired"
    requested_at: datetime
    resolved_at: Optional[datetime] = None
    resolved_by: Optional[str] = None
    justification: Optional[str] = None
    action_context: Dict = field(default_factory=dict)


@dataclass
class CollaborationRecord:
    """Collaboration event record."""

    collaboration_id: str
    agent_ids: List[str]
    mission_id: str
    contribution_scores: Dict[str, float]
    timestamp: datetime


# ============================================================================
# Balance Projection
# ============================================================================


class BalanceProjection:
    """
    Tracks current balance for each entity.

    Subscribes to:
    - CREDIT_ALLOCATED
    - CREDIT_CONSUMED
    - CREDIT_REFUNDED
    - CREDIT_WITHDRAWN
    - CREDIT_REGENERATED

    State:
    - entity_id → current_balance (float)

    Query Methods:
    - get_balance(entity_id) → float
    - get_all_balances() → Dict[str, float]
    """

    def __init__(self):
        self._balances: Dict[str, float] = defaultdict(float)

    async def handle_event(self, event: EventEnvelope) -> None:
        """
        Update balance from event.

        Args:
            event: Credit event (allocated, consumed, refunded, withdrawn, regenerated)
        """
        if event.event_type not in [
            EventType.CREDIT_ALLOCATED,
            EventType.CREDIT_CONSUMED,
            EventType.CREDIT_REFUNDED,
            EventType.CREDIT_WITHDRAWN,
            EventType.CREDIT_REGENERATED,
        ]:
            return

        entity_id = event.payload.get("entity_id")
        balance_after = event.payload.get("balance_after")

        if entity_id is None or balance_after is None:
            logger.warning(
                "Invalid credit event payload (missing entity_id or balance_after)",
                event_id=event.event_id,
                event_type=event.event_type,
                payload=event.payload,
            )
            return

        # Update balance (use balance_after from event for consistency)
        self._balances[entity_id] = balance_after

        logger.debug(
            f"Balance updated: {entity_id} → {balance_after}",
            entity_id=entity_id,
            balance=balance_after,
            event_type=event.event_type,
        )

    def get_balance(self, entity_id: str) -> float:
        """
        Get current balance for entity.

        Args:
            entity_id: Entity ID

        Returns:
            Current balance (0.0 if entity not found)
        """
        return self._balances.get(entity_id, 0.0)

    def get_all_balances(self) -> Dict[str, float]:
        """
        Get all balances.

        Returns:
            Dict of entity_id → balance
        """
        return dict(self._balances)

    def clear(self) -> None:
        """Clear all balances (for testing)."""
        self._balances.clear()


# ============================================================================
# Ledger Projection
# ============================================================================


class LedgerProjection:
    """
    Tracks transaction history for each entity.

    Subscribes to:
    - CREDIT_ALLOCATED
    - CREDIT_CONSUMED
    - CREDIT_REFUNDED
    - CREDIT_WITHDRAWN
    - CREDIT_REGENERATED

    State:
    - entity_id → List[LedgerEntry]

    Query Methods:
    - get_history(entity_id, limit) → List[LedgerEntry]
    - get_all_entries() → List[LedgerEntry]
    """

    def __init__(self, max_entries_per_entity: int = 1000):
        """
        Initialize LedgerProjection.

        Args:
            max_entries_per_entity: Max entries to keep per entity (FIFO)
        """
        self._history: Dict[str, List[LedgerEntry]] = defaultdict(list)
        self._max_entries_per_entity = max_entries_per_entity

    async def handle_event(self, event: EventEnvelope) -> None:
        """
        Add entry to ledger from event.

        Args:
            event: Credit event
        """
        if event.event_type not in [
            EventType.CREDIT_ALLOCATED,
            EventType.CREDIT_CONSUMED,
            EventType.CREDIT_REFUNDED,
            EventType.CREDIT_WITHDRAWN,
            EventType.CREDIT_REGENERATED,
        ]:
            return

        payload = event.payload
        entity_id = payload.get("entity_id")

        if entity_id is None:
            logger.warning(
                "Invalid credit event payload (missing entity_id)",
                event_id=event.event_id,
                event_type=event.event_type,
            )
            return

        # Determine amount sign based on event type
        amount = payload.get("amount", 0.0)
        if event.event_type == EventType.CREDIT_CONSUMED:
            amount = -amount  # Consumed is negative delta
        elif event.event_type == EventType.CREDIT_WITHDRAWN:
            amount = -amount  # Withdrawn is negative delta

        entry = LedgerEntry(
            event_id=event.event_id,
            timestamp=event.timestamp,
            entity_id=entity_id,
            entity_type=payload.get("entity_type", "unknown"),
            amount=amount,
            balance_after=payload.get("balance_after", 0.0),
            reason=payload.get("reason", ""),
            mission_id=payload.get("mission_id"),
        )

        # Add entry to history
        self._history[entity_id].append(entry)

        # Enforce max entries (FIFO)
        if len(self._history[entity_id]) > self._max_entries_per_entity:
            self._history[entity_id].pop(0)

        logger.debug(
            f"Ledger entry added: {entity_id}",
            entity_id=entity_id,
            event_type=event.event_type,
            amount=amount,
            total_entries=len(self._history[entity_id]),
        )

    def get_history(
        self,
        entity_id: str,
        limit: Optional[int] = None,
    ) -> List[LedgerEntry]:
        """
        Get transaction history for entity.

        Args:
            entity_id: Entity ID
            limit: Max number of entries (most recent first)

        Returns:
            List of LedgerEntry (ordered by timestamp, newest first)
        """
        entries = self._history.get(entity_id, [])

        # Sort by timestamp (newest first)
        sorted_entries = sorted(entries, key=lambda e: e.timestamp, reverse=True)

        if limit:
            return sorted_entries[:limit]

        return sorted_entries

    def get_all_entries(self) -> List[LedgerEntry]:
        """
        Get all ledger entries across all entities.

        Returns:
            List of all LedgerEntry (ordered by timestamp, newest first)
        """
        all_entries = []
        for entries in self._history.values():
            all_entries.extend(entries)

        return sorted(all_entries, key=lambda e: e.timestamp, reverse=True)

    def clear(self) -> None:
        """Clear all ledger entries (for testing)."""
        self._history.clear()


# ============================================================================
# Approval Projection
# ============================================================================


class ApprovalProjection:
    """
    Tracks approval request states.

    Subscribes to:
    - APPROVAL_REQUESTED
    - APPROVAL_APPROVED
    - APPROVAL_REJECTED
    - APPROVAL_EXPIRED

    State:
    - request_id → ApprovalRequest

    Query Methods:
    - get_request(request_id) → ApprovalRequest
    - get_pending_approvals() → List[ApprovalRequest]
    - get_resolved_approvals() → List[ApprovalRequest]
    """

    def __init__(self):
        self._requests: Dict[str, ApprovalRequest] = {}

    async def handle_event(self, event: EventEnvelope) -> None:
        """
        Update approval state from event.

        Args:
            event: Approval event
        """
        if event.event_type == EventType.APPROVAL_REQUESTED:
            request_id = event.payload.get("request_id")
            if not request_id:
                return

            self._requests[request_id] = ApprovalRequest(
                request_id=request_id,
                action_type=event.payload.get("action_type", ""),
                requester_id=event.payload.get("requester_id", ""),
                risk_level=event.payload.get("risk_level", ""),
                status="pending",
                requested_at=event.timestamp,
                action_context=event.payload.get("action_context", {}),
            )

        elif event.event_type in [
            EventType.APPROVAL_APPROVED,
            EventType.APPROVAL_REJECTED,
            EventType.APPROVAL_EXPIRED,
        ]:
            request_id = event.payload.get("request_id")
            if not request_id or request_id not in self._requests:
                logger.warning(
                    f"Approval resolution for unknown request: {request_id}",
                    event_id=event.event_id,
                    event_type=event.event_type,
                )
                return

            request = self._requests[request_id]

            # Update status
            if event.event_type == EventType.APPROVAL_APPROVED:
                request.status = "approved"
            elif event.event_type == EventType.APPROVAL_REJECTED:
                request.status = "rejected"
            elif event.event_type == EventType.APPROVAL_EXPIRED:
                request.status = "expired"

            # Update resolution metadata
            request.resolved_at = event.timestamp
            request.resolved_by = event.payload.get("approver_id", event.actor_id)
            request.justification = event.payload.get("justification", "")

    def get_request(self, request_id: str) -> Optional[ApprovalRequest]:
        """
        Get approval request by ID.

        Args:
            request_id: Request ID

        Returns:
            ApprovalRequest or None if not found
        """
        return self._requests.get(request_id)

    def get_pending_approvals(self) -> List[ApprovalRequest]:
        """
        Get all pending approval requests.

        Returns:
            List of pending ApprovalRequest (ordered by requested_at)
        """
        pending = [
            req for req in self._requests.values() if req.status == "pending"
        ]
        return sorted(pending, key=lambda r: r.requested_at)

    def get_resolved_approvals(
        self,
        status: Optional[str] = None,
    ) -> List[ApprovalRequest]:
        """
        Get resolved approval requests.

        Args:
            status: Filter by status ("approved", "rejected", "expired")

        Returns:
            List of resolved ApprovalRequest (ordered by resolved_at)
        """
        resolved = [
            req for req in self._requests.values() if req.status != "pending"
        ]

        if status:
            resolved = [req for req in resolved if req.status == status]

        return sorted(
            resolved,
            key=lambda r: r.resolved_at or r.requested_at,
            reverse=True,
        )

    def clear(self) -> None:
        """Clear all approval requests (for testing)."""
        self._requests.clear()


# ============================================================================
# Synergie Projection
# ============================================================================


class SynergieProjection:
    """
    Tracks collaboration and reuse statistics.

    Subscribes to:
    - COLLABORATION_RECORDED
    - REUSE_DETECTED

    State:
    - collaboration_records: List[CollaborationRecord]
    - reuse_stats: Dict (source_agent → reuse_count)

    Query Methods:
    - get_collaboration_history(agent_id) → List[CollaborationRecord]
    - get_reuse_stats(agent_id) → Dict
    """

    def __init__(self):
        self._collaborations: List[CollaborationRecord] = []
        self._reuse_stats: Dict[str, int] = defaultdict(int)

    async def handle_event(self, event: EventEnvelope) -> None:
        """
        Update synergie data from event.

        Args:
            event: Synergie event
        """
        if event.event_type == EventType.COLLABORATION_RECORDED:
            collab = CollaborationRecord(
                collaboration_id=event.payload.get("collaboration_id", ""),
                agent_ids=event.payload.get("agent_ids", []),
                mission_id=event.payload.get("mission_id", ""),
                contribution_scores=event.payload.get("contribution_scores", {}),
                timestamp=event.timestamp,
            )
            self._collaborations.append(collab)

        elif event.event_type == EventType.REUSE_DETECTED:
            source_agent_id = event.payload.get("source_agent_id")
            if source_agent_id:
                self._reuse_stats[source_agent_id] += 1

    def get_collaboration_history(
        self,
        agent_id: Optional[str] = None,
    ) -> List[CollaborationRecord]:
        """
        Get collaboration history.

        Args:
            agent_id: Filter by agent (if None, return all)

        Returns:
            List of CollaborationRecord (ordered by timestamp, newest first)
        """
        if agent_id:
            filtered = [
                c for c in self._collaborations if agent_id in c.agent_ids
            ]
        else:
            filtered = self._collaborations

        return sorted(filtered, key=lambda c: c.timestamp, reverse=True)

    def get_reuse_stats(self, agent_id: Optional[str] = None) -> Dict[str, int]:
        """
        Get reuse statistics.

        Args:
            agent_id: Filter by source agent (if None, return all)

        Returns:
            Dict of source_agent_id → reuse_count
        """
        if agent_id:
            return {agent_id: self._reuse_stats.get(agent_id, 0)}

        return dict(self._reuse_stats)

    def clear(self) -> None:
        """Clear all synergie data (for testing)."""
        self._collaborations.clear()
        self._reuse_stats.clear()


# ============================================================================
# Projection Manager
# ============================================================================


class ProjectionManager:
    """
    Manages all projections and subscribes them to EventBus.

    Projections:
    - BalanceProjection: Current balances
    - LedgerProjection: Transaction history
    - ApprovalProjection: Approval states
    - SynergieProjection: Collaboration stats
    """

    def __init__(self):
        self.balance = BalanceProjection()
        self.ledger = LedgerProjection()
        self.approval = ApprovalProjection()
        self.synergie = SynergieProjection()

    async def subscribe_all(self, event_bus) -> None:
        """
        Subscribe all projections to EventBus.

        Args:
            event_bus: EventBus instance
        """
        # Balance projection
        for event_type in [
            EventType.CREDIT_ALLOCATED,
            EventType.CREDIT_CONSUMED,
            EventType.CREDIT_REFUNDED,
            EventType.CREDIT_WITHDRAWN,
            EventType.CREDIT_REGENERATED,
        ]:
            event_bus.subscribe(event_type, self.balance.handle_event)

        # Ledger projection
        for event_type in [
            EventType.CREDIT_ALLOCATED,
            EventType.CREDIT_CONSUMED,
            EventType.CREDIT_REFUNDED,
            EventType.CREDIT_WITHDRAWN,
            EventType.CREDIT_REGENERATED,
        ]:
            event_bus.subscribe(event_type, self.ledger.handle_event)

        # Approval projection
        for event_type in [
            EventType.APPROVAL_REQUESTED,
            EventType.APPROVAL_APPROVED,
            EventType.APPROVAL_REJECTED,
            EventType.APPROVAL_EXPIRED,
        ]:
            event_bus.subscribe(event_type, self.approval.handle_event)

        # Synergie projection
        for event_type in [
            EventType.COLLABORATION_RECORDED,
            EventType.REUSE_DETECTED,
        ]:
            event_bus.subscribe(event_type, self.synergie.handle_event)

        logger.info("All projections subscribed to EventBus")

    def clear_all(self) -> None:
        """Clear all projections (for testing)."""
        self.balance.clear()
        self.ledger.clear()
        self.approval.clear()
        self.synergie.clear()


# === Singleton Pattern ===

_projection_manager_instance: Optional[ProjectionManager] = None


def get_projection_manager() -> ProjectionManager:
    """
    Get singleton ProjectionManager instance.

    Returns:
        ProjectionManager instance
    """
    global _projection_manager_instance

    if _projection_manager_instance is None:
        _projection_manager_instance = ProjectionManager()

    return _projection_manager_instance
