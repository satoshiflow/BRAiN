from __future__ import annotations

from dataclasses import dataclass
from types import SimpleNamespace
from uuid import uuid4

import pytest

from app.core.auth_deps import Principal, PrincipalType
from app.modules.axe_miniworker.service import AXEMiniworkerService, get_miniworker_health_snapshot
from app.modules.axe_worker_runs.schemas import AXEWorkerRunCreateRequest


@dataclass
class _FakeDB:
    commit_calls: int = 0

    async def commit(self):
        self.commit_calls += 1


def _principal() -> Principal:
    return Principal(
        principal_id="axe-user",
        principal_type=PrincipalType.HUMAN,
        email="axe@example.com",
        name="AXE User",
        roles=["operator"],
        scopes=["read", "write"],
        tenant_id="tenant-a",
    )


@pytest.mark.asyncio
async def test_miniworker_dispatch_returns_completed_patch(monkeypatch):
    service = AXEMiniworkerService()

    values = {
        "AXE_MINIWORKER_ENABLED": "true",
        "AXE_MINIWORKER_COMMAND": "pi",
        "AXE_MINIWORKER_WORKDIR": "/home/oli/dev/brain-v2",
        "AXE_MINIWORKER_TIMEOUT_SECONDS": "30",
        "AXE_MINIWORKER_MAX_FILES": "3",
        "AXE_MINIWORKER_MAX_LLM_TOKENS": "6000",
        "AXE_MINIWORKER_MAX_COST_CREDITS": "30",
        "AXE_MINIWORKER_ALLOW_BOUNDED_APPLY": "false",
    }

    async def _resolve_effective_value(_db, key, **kwargs):
        return values.get(key, kwargs.get("default"))

    async def _run_command(command, *, cwd, env, timeout_seconds):  # noqa: ANN001
        _ = command, cwd, env, timeout_seconds
        return (
            '{"status":"patch_proposal","summary":"Patch proposal ready","analysis":"Guard nil before access","patch":"-old\\n+new","tests_recommended":["add regression test"],"affected_paths":["backend/app/example.py"],"risks":[],"should_escalate":false}',
            "",
            0,
        )

    consumed: list[float] = []

    async def _consume_credits(*, principal, cost_credits):  # noqa: ANN001
        _ = principal
        consumed.append(cost_credits)

    monkeypatch.setattr(service.config_service, "resolve_effective_value", _resolve_effective_value)
    monkeypatch.setattr(service, "_run_command", _run_command)
    monkeypatch.setattr(service, "_consume_credits", _consume_credits)

    payload = AXEWorkerRunCreateRequest(
        session_id=uuid4(),
        message_id=uuid4(),
        prompt="Replace line 3 with a guarded return",
        worker_type="miniworker",
        file_scope=["backend/app/modules/axe_worker_runs/service.py"],
    )

    result = await service.dispatch(
        db=_FakeDB(),  # type: ignore[arg-type]
        principal=_principal(),
        payload=payload,
        worker_run_id="wr_testmini_1",
    )

    assert result["status"] == "completed"
    assert result["worker_type"] == "miniworker"
    assert result["label"] == "AXE miniworker completed"
    assert result["artifacts"][0]["type"] == "report"
    assert consumed
    health = get_miniworker_health_snapshot()
    assert health["total_runs"] >= 1


@pytest.mark.asyncio
async def test_miniworker_dispatch_creates_repair_ticket_on_failure(monkeypatch):
    service = AXEMiniworkerService()

    values = {
        "AXE_MINIWORKER_ENABLED": "true",
        "AXE_MINIWORKER_COMMAND": "pi",
        "AXE_MINIWORKER_WORKDIR": "/home/oli/dev/brain-v2",
        "AXE_MINIWORKER_TIMEOUT_SECONDS": "30",
        "AXE_MINIWORKER_MAX_FILES": "3",
        "AXE_MINIWORKER_MAX_LLM_TOKENS": "6000",
        "AXE_MINIWORKER_MAX_COST_CREDITS": "30",
        "AXE_MINIWORKER_ALLOW_BOUNDED_APPLY": "false",
    }

    async def _resolve_effective_value(_db, key, **kwargs):
        return values.get(key, kwargs.get("default"))

    async def _run_command(command, *, cwd, env, timeout_seconds):  # noqa: ANN001
        _ = command, cwd, env, timeout_seconds
        return ("", "pi not configured", 1)

    tickets: list[object] = []

    async def _create_ticket(request, db=None):  # noqa: ANN001
        _ = db
        tickets.append(request)
        return SimpleNamespace(ticket_id="rt_123")

    async def _consume_credits(*, principal, cost_credits):  # noqa: ANN001
        _ = principal, cost_credits
        return None

    monkeypatch.setattr(service.config_service, "resolve_effective_value", _resolve_effective_value)
    monkeypatch.setattr(service, "_run_command", _run_command)
    monkeypatch.setattr(service, "_consume_credits", _consume_credits)
    monkeypatch.setattr(service.repair_service, "create_ticket", _create_ticket)

    payload = AXEWorkerRunCreateRequest(
        session_id=uuid4(),
        message_id=uuid4(),
        prompt="Fix failing tests",
        worker_type="miniworker",
    )

    result = await service.dispatch(
        db=_FakeDB(),  # type: ignore[arg-type]
        principal=_principal(),
        payload=payload,
        worker_run_id="wr_testmini_2",
    )

    assert result["status"] == "failed"
    assert result["worker_type"] == "miniworker"
    assert tickets


@pytest.mark.asyncio
async def test_miniworker_bounded_apply_requires_scope_and_concrete_instruction(monkeypatch):
    service = AXEMiniworkerService()

    values = {
        "AXE_MINIWORKER_ENABLED": "true",
        "AXE_MINIWORKER_COMMAND": "pi",
        "AXE_MINIWORKER_WORKDIR": "/home/oli/dev/brain-v2",
        "AXE_MINIWORKER_TIMEOUT_SECONDS": "30",
        "AXE_MINIWORKER_MAX_FILES": "3",
        "AXE_MINIWORKER_MAX_LLM_TOKENS": "6000",
        "AXE_MINIWORKER_MAX_COST_CREDITS": "30",
        "AXE_MINIWORKER_ALLOW_BOUNDED_APPLY": "true",
    }

    async def _resolve_effective_value(_db, key, **kwargs):
        return values.get(key, kwargs.get("default"))

    monkeypatch.setattr(service.config_service, "resolve_effective_value", _resolve_effective_value)

    payload = AXEWorkerRunCreateRequest(
        session_id=uuid4(),
        message_id=uuid4(),
        prompt="Please improve this function",
        worker_type="miniworker",
        execution_mode="bounded_apply",
    )

    with pytest.raises(ValueError, match="requires explicit file_scope"):
        await service.dispatch(
            db=_FakeDB(),  # type: ignore[arg-type]
            principal=_principal(),
            payload=payload,
            worker_run_id="wr_testmini_3",
        )
