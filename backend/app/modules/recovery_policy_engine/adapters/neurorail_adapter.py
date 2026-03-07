"""Adapter for neurorail enforcement/reflex signals."""

from __future__ import annotations

from app.modules.recovery_policy_engine.schemas import RecoveryRequest, RecoverySeverity


def from_payload(payload: dict) -> RecoveryRequest:
    severity = payload.get("severity", "high").lower()
    if severity not in {"low", "medium", "high", "critical"}:
        severity = "high"

    return RecoveryRequest(
        id=payload.get("id", "neurorail-request"),
        source="neurorail",
        entity_id=payload.get("entity_id", payload.get("job_id", "unknown-job")),
        failure_type=payload.get("failure_type", payload.get("error_type", "neurorail_failure")),
        severity=RecoverySeverity(severity),
        retry_count=int(payload.get("retry_count", 0)),
        recurrence=int(payload.get("recurrence", 0)),
        context=payload,
        correlation_id=payload.get("correlation_id"),
    )
