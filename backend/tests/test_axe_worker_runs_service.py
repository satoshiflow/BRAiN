from __future__ import annotations

from dataclasses import dataclass
from types import SimpleNamespace
from uuid import uuid4

import pytest
from pydantic import ValidationError

from app.core.auth_deps import Principal, PrincipalType
from app.modules.axe_worker_runs.schemas import AXEWorkerRunCreateRequest
from app.modules.axe_worker_runs.service import AXEWorkerRunService, WorkerAdapterRegistry


@dataclass
class _FakeDB:
    added: object | None = None
    commit_calls: int = 0
    refresh_calls: int = 0

    def add(self, row):  # noqa: ANN001
        self.added = row

    async def commit(self):
        self.commit_calls += 1

    async def refresh(self, _row):
        self.refresh_calls += 1


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
async def test_create_worker_run_dispatches_opencode_and_persists_backend_job_id(monkeypatch):
    db = _FakeDB()
    service = AXEWorkerRunService(db=db)  # type: ignore[arg-type]

    async def _owned_session(**kwargs):
        _ = kwargs
        return SimpleNamespace(tenant_id="tenant-a")

    async def _owned_message(**kwargs):
        _ = kwargs
        return SimpleNamespace(id=uuid4())

    class _OpenCodeStub:
        async def dispatch(self, *, principal, payload, worker_run_id):  # noqa: ANN001
            _ = principal
            _ = payload
            return SimpleNamespace(
                worker_run_id=worker_run_id,
                session_id=payload.session_id,
                message_id=payload.message_id,
                status="queued",
                label="OpenCode worker queued",
                detail="Job dispatched: job_123",
                updated_at=None,
                artifacts=[],
            )

    monkeypatch.setattr(service, "_get_owned_session", _owned_session)
    monkeypatch.setattr(service, "_get_owned_message", _owned_message)
    WorkerAdapterRegistry._adapters = {"opencode": _OpenCodeStub()}  # type: ignore[assignment]
    WorkerAdapterRegistry._initialized = True

    payload = AXEWorkerRunCreateRequest(
        session_id=uuid4(),
        message_id=uuid4(),
        prompt="Please repair test failures",
    )

    response = await service.create_worker_run(principal=_principal(), payload=payload)

    assert response.status == "queued"
    assert db.added is not None
    assert db.added.backend_run_id == "job_123"
    assert db.commit_calls == 1


@pytest.mark.asyncio
async def test_sync_backend_status_maps_to_completed(monkeypatch):
    db = _FakeDB()
    service = AXEWorkerRunService(db=db)  # type: ignore[arg-type]

    row = SimpleNamespace(
        backend_run_type="opencode_job",
        backend_run_id="job_done",
        status="running",
        label="OpenCode worker active",
        detail="Running",
    )

    class _OpenCodeStub:
        async def get_job_contract(self, _job_id):
            return SimpleNamespace(status=SimpleNamespace(value="completed"))

    service.opencode = _OpenCodeStub()  # type: ignore[assignment]

    await service._sync_backend_status(row)  # noqa: SLF001

    assert row.status == "completed"
    assert db.commit_calls == 1


@pytest.mark.asyncio
async def test_create_worker_run_rejects_openclaw_parallel_path():
    db = _FakeDB()
    service = AXEWorkerRunService(db=db)  # type: ignore[arg-type]

    with pytest.raises(ValidationError):
        AXEWorkerRunCreateRequest(
            session_id=uuid4(),
            message_id=uuid4(),
            prompt="run openclaw task",
            worker_type="openclaw",
        )

    payload = AXEWorkerRunCreateRequest.model_construct(
        session_id=uuid4(),
        message_id=uuid4(),
        prompt="run openclaw task",
        mode="plan",
        worker_type="openclaw",
        module=None,
        entity_id=None,
    )

    with pytest.raises(ValueError, match="SkillRun/TaskLease runtime path"):
        await service.create_worker_run(principal=_principal(), payload=payload)

    assert db.commit_calls == 0
