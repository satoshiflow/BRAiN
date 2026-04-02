from __future__ import annotations

import pytest

from main import OpenClawWorker


@pytest.mark.asyncio
async def test_embedded_execution_records_recent_execution() -> None:
    worker = OpenClawWorker()

    response = await worker.perform_embedded_execution(
        {
            "task_id": "task-oc-123",
            "skill_run_id": "run-oc-123",
            "intent": "openclaw.handoff",
            "prompt": "Review external execution",
            "mode": "plan",
            "input": {"prompt": "Review external execution"},
        }
    )

    assert response["status"] == "completed"
    assert response["operational_path"] == "/app/executions/task-oc-123"

    execution = worker.get_execution("task-oc-123")
    assert execution is not None
    assert execution["skill_run_id"] == "run-oc-123"


def test_render_handoff_page_contains_governance_context() -> None:
    worker = OpenClawWorker()

    page = worker.render_handoff_page(
        {
            "target_type": "execution",
            "target_ref": "task-oc-123",
            "permissions": ["view", "request_escalation"],
            "handoff_token": "test-token-value-123456",
            "execution_context": {
                "available_actions": ["request_escalation"],
                "task": {
                    "task_id": "task-oc-123",
                    "status": "failed",
                    "payload": {"prompt": "Review issue"},
                    "config": {"required_worker": "openclaw"},
                    "updated_at": "2026-04-02T00:00:00+00:00",
                    "correlation_id": "corr-1",
                },
                "skill_run": {"id": "run-oc-123", "state": "failed", "provider_selection_snapshot": {}},
            },
        }
    )

    assert "OpenClaw" in page
    assert "Canonical BRAiN context" in page
    assert "/handoff/openclaw/action" in page


def test_render_entity_page_offers_escalation_action() -> None:
    worker = OpenClawWorker()
    page = worker.render_entity_page("issue", "issue-123", handoff_token="test-token-value-123456", permissions=["request_escalation"])

    assert "issue-123" in page
    assert "Request escalation" in page
