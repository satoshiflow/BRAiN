from __future__ import annotations

from dataclasses import dataclass
import importlib
from types import SimpleNamespace
from uuid import uuid4

import pytest

from app.core.auth_deps import Principal, PrincipalType
from app.modules.axe_fusion.router import ChatMessage, ChatRequest, _try_worker_bridge


@dataclass
class _ScalarResult:
    value: object

    def scalar_one_or_none(self):
        return self.value


@dataclass
class _FakeDB:
    commit_calls: int = 0
    added_rows: list[object] | None = None
    fail_execute: bool = False
    rollback_calls: int = 0

    def __post_init__(self) -> None:
        if self.added_rows is None:
            self.added_rows = []

    async def execute(self, _query):
        if self.fail_execute:
            raise RuntimeError("session table unavailable")
        return _ScalarResult(None)

    def add(self, row):
        self.added_rows.append(row)

    async def commit(self):
        self.commit_calls += 1

    async def rollback(self):
        self.rollback_calls += 1

    async def refresh(self, _row):
        return None


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
async def test_openclaw_command_creates_skillrun_and_tasklease(monkeypatch):
    db = _FakeDB()
    router_module = importlib.import_module("app.modules.axe_fusion.router")

    class _SkillServiceStub:
        async def create_run(self, db, payload, principal):
            assert payload.input_payload["worker_type"] == "openclaw"
            assert payload.input_payload["prompt"] == "build feature"
            return SimpleNamespace(
                id=uuid4(),
                skill_key=payload.skill_key,
                skill_version=1,
                tenant_id=principal.tenant_id,
                mission_id=None,
                correlation_id="corr-openclaw",
                deadline_at=None,
            )

    class _TaskQueueStub:
        async def create_task(self, db, task_data, created_by, created_by_type):
            assert task_data.task_type == "openclaw_work"
            assert task_data.config["worker_target"] == "openclaw"
            assert created_by == "axe-user"
            assert created_by_type == "human"
            return SimpleNamespace(task_id="task-openclaw-1")

    monkeypatch.setattr(router_module, "get_skill_engine_service", lambda: _SkillServiceStub())
    monkeypatch.setattr(router_module, "get_task_queue_service", lambda: _TaskQueueStub())

    request = ChatRequest(
        model="gpt-4",
        messages=[ChatMessage(role="user", content="/openclaw build feature")],
    )

    response = await _try_worker_bridge(
        db=db,  # type: ignore[arg-type]
        principal=_principal(),
        chat_request=request,
        request_id="req-openclaw-1",
    )

    assert response is not None
    assert response.raw["execution_path"] == "worker_bridge_tasklease"
    assert response.raw["worker_type"] == "openclaw"
    assert response.raw["task_id"] == "task-openclaw-1"


@pytest.mark.asyncio
async def test_openclaw_command_continues_if_session_persistence_fails(monkeypatch):
    db = _FakeDB(fail_execute=True)
    router_module = importlib.import_module("app.modules.axe_fusion.router")

    class _SkillServiceStub:
        async def create_run(self, db, payload, principal):
            assert payload.input_payload["worker_type"] == "openclaw"
            assert payload.input_payload["prompt"] == "build feature"
            return SimpleNamespace(
                id=uuid4(),
                skill_key=payload.skill_key,
                skill_version=1,
                tenant_id=principal.tenant_id,
                mission_id=None,
                correlation_id="corr-openclaw",
                deadline_at=None,
            )

    class _TaskQueueStub:
        async def create_task(self, db, task_data, created_by, created_by_type):
            assert task_data.task_type == "openclaw_work"
            assert task_data.config["worker_target"] == "openclaw"
            assert created_by == "axe-user"
            assert created_by_type == "human"
            return SimpleNamespace(task_id="task-openclaw-2")

    monkeypatch.setattr(router_module, "get_skill_engine_service", lambda: _SkillServiceStub())
    monkeypatch.setattr(router_module, "get_task_queue_service", lambda: _TaskQueueStub())

    request = ChatRequest(
        model="gpt-4",
        messages=[ChatMessage(role="user", content="/openclaw build feature")],
    )

    response = await _try_worker_bridge(
        db=db,  # type: ignore[arg-type]
        principal=_principal(),
        chat_request=request,
        request_id="req-openclaw-2",
    )

    assert response is not None
    assert response.raw["execution_path"] == "worker_bridge_tasklease"
    assert response.raw["worker_type"] == "openclaw"
    assert response.raw["task_id"] == "task-openclaw-2"
    assert db.rollback_calls == 1


@pytest.mark.asyncio
async def test_openclaw_command_uses_fallback_skillrun_when_definition_missing(monkeypatch):
    db = _FakeDB()
    router_module = importlib.import_module("app.modules.axe_fusion.router")

    class _SkillServiceStub:
        async def create_run(self, db, payload, principal):
            raise ValueError("No matching definition found for 'axe.chat.bridge'")

    class _TaskQueueStub:
        async def create_task(self, db, task_data, created_by, created_by_type):
            assert task_data.task_type == "openclaw_work"
            assert task_data.config["worker_target"] == "openclaw"
            assert task_data.skill_run_id is not None
            assert created_by == "axe-user"
            assert created_by_type == "human"
            return SimpleNamespace(task_id="task-openclaw-3")

    monkeypatch.setattr(router_module, "get_skill_engine_service", lambda: _SkillServiceStub())
    monkeypatch.setattr(router_module, "get_task_queue_service", lambda: _TaskQueueStub())

    request = ChatRequest(
        model="gpt-4",
        messages=[ChatMessage(role="user", content="/openclaw build feature")],
    )

    response = await _try_worker_bridge(
        db=db,  # type: ignore[arg-type]
        principal=_principal(),
        chat_request=request,
        request_id="req-openclaw-3",
    )

    assert response is not None
    assert response.raw["execution_path"] == "worker_bridge_tasklease"
    assert response.raw["worker_type"] == "openclaw"
    assert response.raw["task_id"] == "task-openclaw-3"
    assert response.raw["skill_run_id"]


@pytest.mark.asyncio
async def test_miniworker_command_dispatches_session_scoped_worker(monkeypatch):
    db = _FakeDB()
    router_module = importlib.import_module("app.modules.axe_fusion.router")

    class _WorkerServiceStub:
        def __init__(self, db):  # noqa: ANN001
            _ = db

        async def create_worker_run(self, *, principal, payload):  # noqa: ANN001
            assert principal.principal_id == "axe-user"
            assert payload.worker_type == "miniworker"
            assert payload.execution_mode == "proposal"
            assert payload.prompt == "replace line 3"
            return SimpleNamespace(
                worker_run_id="wr-mini-1",
                status="completed",
                detail="Patch proposal ready",
            )

    monkeypatch.setattr(router_module, "AXEWorkerRunService", _WorkerServiceStub)

    request = ChatRequest(
        model="gpt-4",
        messages=[ChatMessage(role="user", content="/miniworker replace line 3")],
    )

    response = await _try_worker_bridge(
        db=db,  # type: ignore[arg-type]
        principal=_principal(),
        chat_request=request,
        request_id="req-miniworker-1",
    )

    assert response is not None
    assert response.raw["worker_type"] == "miniworker"
    assert response.raw["worker_run_id"] == "wr-mini-1"
