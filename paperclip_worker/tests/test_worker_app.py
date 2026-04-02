from __future__ import annotations

import pytest

from main import PaperclipWorker


@pytest.mark.asyncio
async def test_embedded_execution_records_recent_execution() -> None:
    worker = PaperclipWorker()

    response = await worker.perform_embedded_execution(
        {
            "task_id": "task-123",
            "skill_run_id": "run-123",
            "intent": "paperclip.handoff",
            "prompt": "Review external execution",
            "mode": "plan",
            "input": {"prompt": "Review external execution"},
        }
    )

    assert response["status"] == "completed"
    assert response["operational_path"] == "/app/executions/task-123"

    execution = worker.get_execution("task-123")
    assert execution is not None
    assert execution["skill_run_id"] == "run-123"
    assert execution["prompt"] == "Review external execution"


def test_render_handoff_page_contains_governance_context() -> None:
    worker = PaperclipWorker()
    worker._record_execution(  # noqa: SLF001
        {
            "execution_id": "task-123",
            "task_id": "task-123",
            "skill_run_id": "run-123",
            "status": "completed",
            "summary": "Execution recorded",
        }
    )

    page = worker.render_handoff_page(
        {
            "jti": "handoff_123",
            "principal_id": "operator-1",
            "tenant_id": "tenant-a",
            "skill_run_id": "run-123",
            "mission_id": "mission-1",
            "decision_id": "rdec-1",
            "correlation_id": "corr-1",
            "target_type": "execution",
            "target_ref": "task-123",
            "permissions": ["view", "request_approval"],
            "suggested_path": "/app/executions/task-123",
            "governance_banner": "Governed by BRAiN. Sensitive actions require BRAiN approval.",
            "expires_at": "2026-04-02T00:00:00+00:00",
            "handoff_token": "test-token-value-123456",
            "execution_context": {
                "available_actions": ["request_approval"],
                "task": {"task_id": "task-123", "status": "completed", "payload": {}, "config": {}, "updated_at": "2026-04-02T00:00:00+00:00", "correlation_id": "corr-1"},
                "skill_run": {"id": "run-123", "state": "waiting_approval", "provider_selection_snapshot": {}},
            },
        }
    )

    assert "Governed by BRAiN" in page
    assert "/app/executions/task-123" in page
    assert "request_approval" in page
    assert "run-123" in page
    assert "/handoff/paperclip/action" in page


def test_render_execution_page_prefers_canonical_context() -> None:
    worker = PaperclipWorker()

    page = worker.render_execution_page(
        "task-123",
        execution_context={
            "target_type": "execution",
            "target_ref": "task-123",
            "task": {
                "task_id": "task-123",
                "name": "Paperclip TaskLease",
                "description": "External execution",
                "status": "completed",
                "updated_at": "2026-04-02T00:00:00+00:00",
                "correlation_id": "corr-1",
                "payload": {"prompt": "Review issue"},
                "config": {"required_worker": "paperclip"},
                "skill_run_id": "run-123",
                "error_message": None,
            },
            "skill_run": {
                "id": "run-123",
                "state": "succeeded",
                "failure_reason_sanitized": None,
                "provider_selection_snapshot": {
                    "runtime_decision": {
                        "decision_id": "rdec-1",
                        "selected_route": "external_executor.paperclip",
                        "selected_worker": "paperclip",
                    }
                },
            },
            "available_actions": ["request_retry", "request_escalation"],
        },
        handoff_token="test-token-value-123456",
    )

    assert "Canonical BRAiN context" in page
    assert "rdec-1" in page
    assert "external_executor.paperclip" in page
    assert "Request retry" in page


def test_render_action_result_page_shows_request_summary() -> None:
    worker = PaperclipWorker()
    page = worker.render_action_result_page(
        {
            "request_id": "actreq_123",
            "action": "request_retry",
            "target_ref": "task-123",
            "message": "Retry request recorded for operator review.",
        }
    )

    assert "actreq_123" in page
    assert "request_retry" in page
    assert "task-123" in page
