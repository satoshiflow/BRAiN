"""
Governor v1 Event System (Phase 2a + 2b)

Events emitted by Governor v1 for agent creation governance decisions.

All events follow dual-write pattern:
1. Redis Pub/Sub (brain.events channel) for real-time monitoring
2. Audit Log (persistent storage) for compliance

Events are fail-closed: at least one write must succeed.

Event Types (Phase 2a):
- governor.decision.requested: Decision request received
- governor.decision.evaluated: Decision evaluation complete
- governor.decision.approved: Decision approved
- governor.decision.rejected: Decision rejected
- governor.constraints.applied: Constraints applied to agent

Event Types (Phase 2b):
- governor.constraints.reduced: Constraints reduced by manifest rules
- governor.manifest.applied: Governance manifest applied

Author: Governor v1 System
Version: 2b.1
Created: 2026-01-02
Updated: 2026-01-02 (Phase 2b)
"""

from __future__ import annotations

import json
import logging
from datetime import datetime
from typing import Any, Dict, Optional

import redis.asyncio as redis

# Re-use Genesis AuditLog protocol
from backend.brain.agents.genesis_agent.events import AuditLog


logger = logging.getLogger(__name__)


# ============================================================================
# Governor Events
# ============================================================================

class GovernorEvents:
    """
    Event definitions and emission for Governor v1 System.

    All events follow standard structure:
    {
        "event_type": "governor.decision.requested",
        "timestamp": "2026-01-02T12:00:00.000000Z",
        "payload": { ... event-specific data ... }
    }

    Example:
        >>> await GovernorEvents.decision_requested(
        ...     decision_id="dec_abc123",
        ...     request_id="req-xyz789",
        ...     template_name="worker_base",
        ...     actor_role="SYSTEM_ADMIN",
        ...     redis_client=redis,
        ...     audit_log=audit
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
        Emit event to both Redis and Audit Log (dual-write).

        Args:
            event_type: Event type identifier
            payload: Event-specific data (will be sanitized)
            redis_client: Redis client for pub/sub
            audit_log: Audit logger for persistence

        Raises:
            Exception: If both Redis AND audit log fail (fail-closed)

        Example:
            >>> await GovernorEvents.emit(
            ...     "governor.decision.requested",
            ...     {"decision_id": "dec_abc123"},
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

    # ========================================================================
    # Decision Lifecycle Events
    # ========================================================================

    @staticmethod
    async def decision_requested(
        decision_id: str,
        request_id: str,
        template_name: str,
        actor_role: str,
        has_customizations: bool,
        redis_client: redis.Redis,
        audit_log: AuditLog
    ) -> None:
        """
        Emit event when Governor decision is requested.

        Args:
            decision_id: Decision identifier
            request_id: Original request identifier
            template_name: Template name
            actor_role: Actor role
            has_customizations: Whether request has customizations
            redis_client: Redis client
            audit_log: Audit logger

        Example:
            >>> await GovernorEvents.decision_requested(
            ...     decision_id="dec_abc123",
            ...     request_id="req-xyz789",
            ...     template_name="worker_base",
            ...     actor_role="SYSTEM_ADMIN",
            ...     has_customizations=True,
            ...     redis_client=redis,
            ...     audit_log=audit
            ... )
        """
        payload = {
            "decision_id": decision_id,
            "request_id": request_id,
            "template_name": template_name,
            "actor_role": actor_role,
            "has_customizations": has_customizations,
        }

        await GovernorEvents.emit(
            "governor.decision.requested",
            payload,
            redis_client,
            audit_log
        )

    @staticmethod
    async def decision_evaluated(
        decision_id: str,
        evaluation_duration_ms: float,
        evaluated_rules: list[str],
        triggered_rules: list[str],
        redis_client: redis.Redis,
        audit_log: AuditLog
    ) -> None:
        """
        Emit event when decision evaluation completes.

        Args:
            decision_id: Decision identifier
            evaluation_duration_ms: Evaluation duration in milliseconds
            evaluated_rules: List of rule IDs that were evaluated
            triggered_rules: List of rule IDs that triggered
            redis_client: Redis client
            audit_log: Audit logger

        Example:
            >>> await GovernorEvents.decision_evaluated(
            ...     decision_id="dec_abc123",
            ...     evaluation_duration_ms=12.5,
            ...     evaluated_rules=["A1", "B1", "C1"],
            ...     triggered_rules=["C2"],
            ...     redis_client=redis,
            ...     audit_log=audit
            ... )
        """
        payload = {
            "decision_id": decision_id,
            "evaluation_duration_ms": evaluation_duration_ms,
            "evaluated_rules": evaluated_rules,
            "triggered_rules": triggered_rules,
        }

        await GovernorEvents.emit(
            "governor.decision.evaluated",
            payload,
            redis_client,
            audit_log
        )

    @staticmethod
    async def decision_approved(
        decision_id: str,
        decision_type: str,
        reason_code: str,
        risk_tier: str,
        quarantine: bool,
        redis_client: redis.Redis,
        audit_log: AuditLog
    ) -> None:
        """
        Emit event when decision is approved.

        Args:
            decision_id: Decision identifier
            decision_type: Decision type (approve/approve_with_constraints)
            reason_code: Reason code
            risk_tier: Risk tier (LOW/MEDIUM/HIGH/CRITICAL)
            quarantine: Whether agent is quarantined
            redis_client: Redis client
            audit_log: Audit logger

        Example:
            >>> await GovernorEvents.decision_approved(
            ...     decision_id="dec_abc123",
            ...     decision_type="approve_with_constraints",
            ...     reason_code="APPROVED_WITH_CONSTRAINTS",
            ...     risk_tier="MEDIUM",
            ...     quarantine=False,
            ...     redis_client=redis,
            ...     audit_log=audit
            ... )
        """
        payload = {
            "decision_id": decision_id,
            "decision_type": decision_type,
            "reason_code": reason_code,
            "risk_tier": risk_tier,
            "quarantine": quarantine,
        }

        await GovernorEvents.emit(
            "governor.decision.approved",
            payload,
            redis_client,
            audit_log
        )

    @staticmethod
    async def decision_rejected(
        decision_id: str,
        reason_code: str,
        reason_detail: str,
        triggered_rules: list[str],
        redis_client: redis.Redis,
        audit_log: AuditLog
    ) -> None:
        """
        Emit event when decision is rejected.

        Args:
            decision_id: Decision identifier
            reason_code: Reason code
            reason_detail: Human-readable reason (sanitized to 200 chars)
            triggered_rules: List of rule IDs that caused rejection
            redis_client: Redis client
            audit_log: Audit logger

        Example:
            >>> await GovernorEvents.decision_rejected(
            ...     decision_id="dec_abc123",
            ...     reason_code="UNAUTHORIZED_ROLE",
            ...     reason_detail="Agent creation requires SYSTEM_ADMIN role",
            ...     triggered_rules=["A1"],
            ...     redis_client=redis,
            ...     audit_log=audit
            ... )
        """
        # Sanitize reason_detail (truncate to 200 chars)
        sanitized_detail = reason_detail[:200]

        payload = {
            "decision_id": decision_id,
            "reason_code": reason_code,
            "reason_detail": sanitized_detail,
            "triggered_rules": triggered_rules,
        }

        await GovernorEvents.emit(
            "governor.decision.rejected",
            payload,
            redis_client,
            audit_log
        )

    @staticmethod
    async def constraints_applied(
        decision_id: str,
        agent_id: str,
        constraints_summary: Dict[str, Any],
        redis_client: redis.Redis,
        audit_log: AuditLog
    ) -> None:
        """
        Emit event when constraints are applied to agent.

        Args:
            decision_id: Decision identifier
            agent_id: Agent identifier
            constraints_summary: Summary of applied constraints (sanitized)
            redis_client: Redis client
            audit_log: Audit logger

        Example:
            >>> await GovernorEvents.constraints_applied(
            ...     decision_id="dec_abc123",
            ...     agent_id="agent-456",
            ...     constraints_summary={
            ...         "max_credits_per_mission": 50,
            ...         "network_access": "restricted"
            ...     },
            ...     redis_client=redis,
            ...     audit_log=audit
            ... )
        """
        payload = {
            "decision_id": decision_id,
            "agent_id": agent_id,
            "constraints_summary": constraints_summary,
        }

        await GovernorEvents.emit(
            "governor.constraints.applied",
            payload,
            redis_client,
            audit_log
        )

    # ========================================================================
    # Phase 2b: Reduction & Manifest Events
    # ========================================================================

    @staticmethod
    async def constraints_reduced(
        decision_id: str,
        applied_reductions: list[str],
        reduction_summary: Dict[str, Any],
        base_constraints_hash: str,
        reduced_constraints_hash: str,
        redis_client: redis.Redis,
        audit_log: AuditLog
    ) -> None:
        """
        Emit event when constraints are reduced by manifest rules.

        Args:
            decision_id: Decision identifier
            applied_reductions: List of reduction section names applied
            reduction_summary: Summary of reductions (before/after values)
            base_constraints_hash: Hash of base constraints
            reduced_constraints_hash: Hash of reduced constraints
            redis_client: Redis client
            audit_log: Audit logger

        Example:
            >>> await GovernorEvents.constraints_reduced(
            ...     decision_id="dec_abc123",
            ...     applied_reductions=["on_customization", "on_high_risk"],
            ...     reduction_summary={
            ...         "max_llm_calls_per_day": {"before": 1000, "after": 700},
            ...         "network_access": {"before": "restricted", "after": "none"}
            ...     },
            ...     base_constraints_hash="sha256:abc123",
            ...     reduced_constraints_hash="sha256:def456",
            ...     redis_client=redis,
            ...     audit_log=audit
            ... )
        """
        payload = {
            "decision_id": decision_id,
            "applied_reductions": applied_reductions,
            "reduction_summary": reduction_summary,
            "base_constraints_hash": base_constraints_hash,
            "reduced_constraints_hash": reduced_constraints_hash,
        }

        await GovernorEvents.emit(
            "governor.constraints.reduced",
            payload,
            redis_client,
            audit_log
        )

    @staticmethod
    async def manifest_applied(
        decision_id: str,
        manifest_name: str,
        manifest_version: str,
        policy_version: str,
        applicable_sections: list[str],
        risk_overrides: Dict[str, str],
        locked_fields: list[str],
        redis_client: redis.Redis,
        audit_log: AuditLog
    ) -> None:
        """
        Emit event when a governance manifest is applied.

        Args:
            decision_id: Decision identifier
            manifest_name: Manifest name
            manifest_version: Manifest version
            policy_version: Policy version
            applicable_sections: Reduction sections that were applicable
            risk_overrides: Risk tier overrides applied
            locked_fields: Fields locked by manifest
            redis_client: Redis client
            audit_log: Audit logger

        Example:
            >>> await GovernorEvents.manifest_applied(
            ...     decision_id="dec_abc123",
            ...     manifest_name="default",
            ...     manifest_version="1",
            ...     policy_version="2b.1",
            ...     applicable_sections=["on_customization"],
            ...     risk_overrides={"if_customizations": "MEDIUM"},
            ...     locked_fields=["ethics_flags.human_override"],
            ...     redis_client=redis,
            ...     audit_log=audit
            ... )
        """
        payload = {
            "decision_id": decision_id,
            "manifest_name": manifest_name,
            "manifest_version": str(manifest_version),
            "policy_version": policy_version,
            "applicable_sections": applicable_sections,
            "risk_overrides": risk_overrides,
            "locked_fields": locked_fields,
        }

        await GovernorEvents.emit(
            "governor.manifest.applied",
            payload,
            redis_client,
            audit_log
        )
