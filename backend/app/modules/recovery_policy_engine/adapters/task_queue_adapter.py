"""Adapter for task queue retry/failure signals."""

from __future__ import annotations

from app.modules.recovery_policy_engine.schemas import RecoveryRequest, RecoverySeverity


def from_payload(payload: dict) -> RecoveryRequest:
    severity = payload.get("severity", "medium").lower()
    if severity not in {"low", "medium", "high", "critical"}:
        severity = "medium"

    return RecoveryRequest(
        id=payload.get("id", "task-request"),
        source="task_queue",
        entity_id=payload.get("entity_id", payload.get("task_id", "unknown-task")),
        failure_type=payload.get("failure_type", "task_execution_failure"),
        severity=RecoverySeverity(severity),
        retry_count=int(payload.get("retry_count", 0)),
        recurrence=int(payload.get("recurrence", 0)),
        context=payload,
        correlation_id=payload.get("correlation_id"),
    )
