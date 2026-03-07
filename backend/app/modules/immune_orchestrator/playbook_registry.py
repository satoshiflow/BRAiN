"""Playbook selection for immune decisions."""

from __future__ import annotations

from app.modules.immune_orchestrator.schemas import DecisionAction, SignalSeverity


class PlaybookRegistry:
    """Maps priority and severity to a mitigation action."""

    def choose_action(self, priority_score: float, severity: SignalSeverity, recurrence: int) -> DecisionAction:
        if severity == SignalSeverity.CRITICAL and (priority_score >= 0.85 or recurrence >= 3):
            return DecisionAction.ESCALATE
        if severity == SignalSeverity.CRITICAL and priority_score >= 0.7:
            return DecisionAction.ISOLATE
        if priority_score >= 0.55:
            return DecisionAction.MITIGATE
        if priority_score >= 0.35:
            return DecisionAction.WARN
        return DecisionAction.OBSERVE
