"""
Event System for Genesis Agent

This module defines all events emitted by the Genesis Agent System including:
- Agent creation lifecycle events
- Validation events
- Error events
- Audit trail integration

All events are emitted to:
1. Redis Pub/Sub (brain.events channel) for real-time monitoring
2. Audit Log (persistent storage) for compliance

Author: Genesis Agent System
Version: 2.0.0
Created: 2026-01-02
"""

from __future__ import annotations

import json
import logging
from datetime import datetime
from typing import Any, Dict, Optional, Protocol

import redis.asyncio as redis


logger = logging.getLogger(__name__)


class AuditLog(Protocol):
    """
    Protocol for audit log persistence.

    This allows different audit storage backends (PostgreSQL, file, etc.)
    while keeping the event system decoupled.
    """
    async def write(self, event: Dict[str, Any]) -> None:
        """Write an event to persistent audit storage."""
        ...


class GenesisEvents:
    """
    Event definitions and emission for Genesis Agent System.

    All events follow a standard structure:
    {
        "event_type": "genesis.agent.create.requested",
        "timestamp": "2026-01-02T12:00:00.000000Z",
        "payload": { ... event-specific data ... }
    }

    Event Types:
    - genesis.agent.create.requested: Agent creation requested
    - genesis.agent.create.validated: DNA validation succeeded
    - genesis.agent.create.registered: Agent registered in system
    - genesis.agent.create.failed: Agent creation failed
    - genesis.agent.template.loaded: Template loaded successfully
    - genesis.agent.customizations.applied: Customizations applied
    - genesis.system.killswitch.triggered: Kill switch activated
    - genesis.system.budget.exceeded: Budget limit exceeded

    Example:
        >>> events = GenesisEvents()
        >>> await events.create_requested(
        ...     request_id="req-123",
        ...     template_name="worker_base",
        ...     customizations={},
        ...     redis=redis_client,
        ...     audit_log=audit_logger
        ... )
    """

    # ========================================================================
    # Core Event Emission
    # ========================================================================

    @staticmethod
    async def emit(
        event_type: str,
        payload: Dict[str, Any],
        redis_client: redis.Redis,
        audit_log: AuditLog
    ) -> None:
        """
        Emit event to both Redis and Audit Log.

        This is the core event emission function that ensures dual-write:
        1. Redis Pub/Sub for real-time monitoring
        2. Audit Log for persistent compliance trail

        Args:
            event_type: Event type identifier (e.g., "genesis.agent.create.requested")
            payload: Event-specific data (will be sanitized)
            redis_client: Redis client for pub/sub
            audit_log: Audit logger for persistence

        Raises:
            Exception: If both Redis AND audit log fail (fail-closed)

        Example:
            >>> await GenesisEvents.emit(
            ...     "genesis.agent.create.requested",
            ...     {"request_id": "req-123"},
            ...     redis_client,
            ...     audit_log
            ... )
        """
        # Build event structure
        event = {
            "event_type": event_type,
            "timestamp": datetime.utcnow().isoformat() + "Z",
            "payload": payload
        }

        redis_success = False
        audit_success = False

        # Try Redis pub/sub
        try:
            await redis_client.publish("brain.events", json.dumps(event))
            redis_success = True
            logger.debug(f"Event published to Redis: {event_type}")
        except Exception as e:
            logger.error(f"Failed to publish event to Redis: {e}")

        # Try Audit Log
        try:
            await audit_log.write(event)
            audit_success = True
            logger.debug(f"Event written to audit log: {event_type}")
        except Exception as e:
            logger.error(f"Failed to write event to audit log: {e}")

        # Fail-closed: at least one must succeed
        if not (redis_success or audit_success):
            raise Exception(
                f"CRITICAL: Failed to emit event '{event_type}' to both "
                f"Redis and Audit Log. Event emission FAILED."
            )

    @staticmethod
    def _sanitize_payload(payload: Dict[str, Any], max_size: int = 1000) -> Dict[str, Any]:
        """
        Sanitize payload to prevent logging sensitive data.

        Args:
            payload: Raw payload
            max_size: Maximum size for string values

        Returns:
            Sanitized payload safe for logging

        Example:
            >>> sanitized = GenesisEvents._sanitize_payload({
            ...     "api_key": "secret123",
            ...     "message": "a" * 2000
            ... })
        """
        sanitized = {}
        for key, value in payload.items():
            # Skip sensitive keys
            if any(sensitive in key.lower() for sensitive in ["password", "secret", "key", "token"]):
                sanitized[key] = "[REDACTED]"
            # Truncate long strings
            elif isinstance(value, str) and len(value) > max_size:
                sanitized[key] = value[:max_size] + "...[TRUNCATED]"
            # Keep safe values
            else:
                sanitized[key] = value

        return sanitized

    # ========================================================================
    # Agent Creation Lifecycle Events
    # ========================================================================

    @staticmethod
    async def create_requested(
        request_id: str,
        template_name: str,
        customizations: Dict[str, Any],
        redis_client: redis.Redis,
        audit_log: AuditLog
    ) -> None:
        """
        Emit event when agent creation is requested.

        Args:
            request_id: Unique request identifier
            template_name: Name of base template
            customizations: Requested customizations (will be sanitized)
            redis_client: Redis client
            audit_log: Audit logger

        Example:
            >>> await GenesisEvents.create_requested(
            ...     request_id="req-123",
            ...     template_name="worker_base",
            ...     customizations={"metadata.name": "worker_01"},
            ...     redis=redis_client,
            ...     audit_log=audit_logger
            ... )
        """
        payload = {
            "request_id": request_id,
            "template_name": template_name,
            "has_customizations": bool(customizations),
            "customization_count": len(customizations),
        }

        await GenesisEvents.emit(
            "genesis.agent.create.requested",
            payload,
            redis_client,
            audit_log
        )

    @staticmethod
    async def create_validated(
        agent_id: str,
        dna_hash: str,
        template_hash: str,
        redis_client: redis.Redis,
        audit_log: AuditLog
    ) -> None:
        """
        Emit event when DNA validation succeeds.

        Args:
            agent_id: Agent identifier
            dna_hash: SHA256 hash of complete DNA
            template_hash: SHA256 hash of source template
            redis_client: Redis client
            audit_log: Audit logger

        Example:
            >>> await GenesisEvents.create_validated(
            ...     agent_id="agent-123",
            ...     dna_hash="abc123...",
            ...     template_hash="sha256:def456...",
            ...     redis=redis_client,
            ...     audit_log=audit_logger
            ... )
        """
        payload = {
            "agent_id": agent_id,
            "dna_hash": dna_hash,
            "template_hash": template_hash,
        }

        await GenesisEvents.emit(
            "genesis.agent.create.validated",
            payload,
            redis_client,
            audit_log
        )

    @staticmethod
    async def create_registered(
        agent_id: str,
        registry_id: str,
        status: str,
        redis_client: redis.Redis,
        audit_log: AuditLog
    ) -> None:
        """
        Emit event when agent is registered in the system.

        Args:
            agent_id: Agent identifier
            registry_id: Registry record identifier
            status: Agent status (e.g., "CREATED")
            redis_client: Redis client
            audit_log: Audit logger

        Example:
            >>> await GenesisEvents.create_registered(
            ...     agent_id="agent-123",
            ...     registry_id="reg-456",
            ...     status="CREATED",
            ...     redis=redis_client,
            ...     audit_log=audit_logger
            ... )
        """
        payload = {
            "agent_id": agent_id,
            "registry_id": registry_id,
            "status": status,
        }

        await GenesisEvents.emit(
            "genesis.agent.create.registered",
            payload,
            redis_client,
            audit_log
        )

    @staticmethod
    async def create_failed(
        error_code: str,
        reason: str,
        request_id: Optional[str],
        redis_client: redis.Redis,
        audit_log: AuditLog
    ) -> None:
        """
        Emit event when agent creation fails.

        Args:
            error_code: Error classification code
            reason: Error message (will be sanitized)
            request_id: Optional request identifier
            redis_client: Redis client
            audit_log: Audit logger

        Example:
            >>> await GenesisEvents.create_failed(
            ...     error_code="VALIDATION_ERROR",
            ...     reason="Invalid DNA schema",
            ...     request_id="req-123",
            ...     redis=redis_client,
            ...     audit_log=audit_logger
            ... )
        """
        # Sanitize reason (truncate, remove sensitive data)
        sanitized_reason = reason[:200]  # Truncate to 200 chars

        payload = {
            "error_code": error_code,
            "reason": sanitized_reason,
        }

        if request_id:
            payload["request_id"] = request_id

        await GenesisEvents.emit(
            "genesis.agent.create.failed",
            payload,
            redis_client,
            audit_log
        )

    # ========================================================================
    # Template Events
    # ========================================================================

    @staticmethod
    async def template_loaded(
        template_name: str,
        template_hash: str,
        redis_client: redis.Redis,
        audit_log: AuditLog
    ) -> None:
        """
        Emit event when template is loaded successfully.

        Args:
            template_name: Name of template
            template_hash: SHA256 hash of template
            redis_client: Redis client
            audit_log: Audit logger

        Example:
            >>> await GenesisEvents.template_loaded(
            ...     template_name="worker_base",
            ...     template_hash="sha256:abc123...",
            ...     redis=redis_client,
            ...     audit_log=audit_logger
            ... )
        """
        payload = {
            "template_name": template_name,
            "template_hash": template_hash,
        }

        await GenesisEvents.emit(
            "genesis.agent.template.loaded",
            payload,
            redis_client,
            audit_log
        )

    @staticmethod
    async def customizations_applied(
        agent_id: str,
        customizations: Dict[str, Any],
        redis_client: redis.Redis,
        audit_log: AuditLog
    ) -> None:
        """
        Emit event when customizations are applied to DNA.

        Args:
            agent_id: Agent identifier
            customizations: Applied customizations (will be sanitized)
            redis_client: Redis client
            audit_log: Audit logger

        Example:
            >>> await GenesisEvents.customizations_applied(
            ...     agent_id="agent-123",
            ...     customizations={"metadata.name": "worker_01"},
            ...     redis=redis_client,
            ...     audit_log=audit_logger
            ... )
        """
        payload = {
            "agent_id": agent_id,
            "customizations": GenesisEvents._sanitize_payload(customizations),
        }

        await GenesisEvents.emit(
            "genesis.agent.customizations.applied",
            payload,
            redis_client,
            audit_log
        )

    # ========================================================================
    # System Events
    # ========================================================================

    @staticmethod
    async def killswitch_triggered(
        reason: str,
        redis_client: redis.Redis,
        audit_log: AuditLog
    ) -> None:
        """
        Emit event when Genesis kill switch is activated.

        Args:
            reason: Reason for activation
            redis_client: Redis client
            audit_log: Audit logger

        Example:
            >>> await GenesisEvents.killswitch_triggered(
            ...     reason="Manual shutdown",
            ...     redis=redis_client,
            ...     audit_log=audit_logger
            ... )
        """
        payload = {
            "reason": reason,
        }

        await GenesisEvents.emit(
            "genesis.system.killswitch.triggered",
            payload,
            redis_client,
            audit_log
        )

    @staticmethod
    async def budget_exceeded(
        available_credits: int,
        required_credits: int,
        redis_client: redis.Redis,
        audit_log: AuditLog
    ) -> None:
        """
        Emit event when budget limit is exceeded.

        Args:
            available_credits: Available credits after reserve
            required_credits: Required credits for operation
            redis_client: Redis client
            audit_log: Audit logger

        Example:
            >>> await GenesisEvents.budget_exceeded(
            ...     available_credits=50,
            ...     required_credits=100,
            ...     redis=redis_client,
            ...     audit_log=audit_logger
            ... )
        """
        payload = {
            "available_credits": available_credits,
            "required_credits": required_credits,
            "shortfall": required_credits - available_credits,
        }

        await GenesisEvents.emit(
            "genesis.system.budget.exceeded",
            payload,
            redis_client,
            audit_log
        )

    @staticmethod
    async def idempotency_hit(
        request_id: str,
        existing_agent_id: str,
        redis_client: redis.Redis,
        audit_log: AuditLog
    ) -> None:
        """
        Emit event when duplicate request_id is detected.

        Args:
            request_id: Duplicate request identifier
            existing_agent_id: ID of existing agent from first request
            redis_client: Redis client
            audit_log: Audit logger

        Example:
            >>> await GenesisEvents.idempotency_hit(
            ...     request_id="req-123",
            ...     existing_agent_id="agent-456",
            ...     redis=redis_client,
            ...     audit_log=audit_logger
            ... )
        """
        payload = {
            "request_id": request_id,
            "existing_agent_id": existing_agent_id,
        }

        await GenesisEvents.emit(
            "genesis.agent.idempotency.hit",
            payload,
            redis_client,
            audit_log
        )


# ============================================================================
# Simple Audit Log Implementation
# ============================================================================

class SimpleAuditLog:
    """
    Simple in-memory audit log for development/testing.

    In production, replace with PostgreSQL or file-based storage.
    """

    def __init__(self):
        """Initialize empty audit log."""
        self.events: list[Dict[str, Any]] = []

    async def write(self, event: Dict[str, Any]) -> None:
        """
        Write event to in-memory storage.

        Args:
            event: Event dictionary to store
        """
        self.events.append(event)
        logger.info(f"Audit event stored: {event['event_type']}")

    def get_events(
        self,
        event_type: Optional[str] = None,
        limit: int = 100
    ) -> list[Dict[str, Any]]:
        """
        Retrieve events from storage.

        Args:
            event_type: Filter by event type (optional)
            limit: Maximum number of events to return

        Returns:
            List of events (newest first)
        """
        events = self.events
        if event_type:
            events = [e for e in events if e["event_type"] == event_type]

        return list(reversed(events[-limit:]))

    def clear(self) -> None:
        """Clear all events (for testing)."""
        self.events.clear()
