"""Policy decision engine for recovery actions."""

from __future__ import annotations

from app.modules.recovery_policy_engine.schemas import (
    RecoveryPolicyConfig,
    RecoveryRequest,
    RecoverySeverity,
    RecoveryStrategy,
)


class RecoveryPolicyEngine:
    """Selects an action based on request context and configured policy."""

    def decide(self, request: RecoveryRequest, config: RecoveryPolicyConfig) -> RecoveryStrategy:
        allowed = set(config.allowed_actions)

        if request.severity == RecoverySeverity.CRITICAL:
            if request.recurrence >= config.escalation_threshold and RecoveryStrategy.ESCALATE in allowed:
                return RecoveryStrategy.ESCALATE
            if RecoveryStrategy.ISOLATE in allowed:
                return RecoveryStrategy.ISOLATE

        if "timeout" in request.failure_type.lower() and RecoveryStrategy.CIRCUIT_BREAK in allowed:
            return RecoveryStrategy.CIRCUIT_BREAK

        if request.retry_count < config.max_retries and RecoveryStrategy.RETRY in allowed:
            return RecoveryStrategy.RETRY

        if request.severity in {RecoverySeverity.HIGH, RecoverySeverity.CRITICAL}:
            if RecoveryStrategy.BACKPRESSURE in allowed:
                return RecoveryStrategy.BACKPRESSURE
            if RecoveryStrategy.ROLLBACK in allowed:
                return RecoveryStrategy.ROLLBACK

        if RecoveryStrategy.DETOX in allowed:
            return RecoveryStrategy.DETOX

        if RecoveryStrategy.ESCALATE in allowed:
            return RecoveryStrategy.ESCALATE

        # Guaranteed fallback based on enum ordering expectation.
        return next(iter(allowed))
