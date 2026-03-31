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


def _viewer_principal() -> Principal:
    return Principal(
        principal_id="axe-viewer",
        principal_type=PrincipalType.HUMAN,
        email="viewer@example.com",
        name="AXE Viewer",
        roles=["viewer"],
        scopes=["read"],
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
        async def dispatch(self, *, db, principal, payload, worker_run_id):  # noqa: ANN001
            _ = db
            _ = principal
            _ = payload
            return SimpleNamespace(
                worker_run_id=worker_run_id,
                session_id=payload.session_id,
                message_id=payload.message_id,
                worker_type="opencode",
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
        worker_type="opencode",
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


@pytest.mark.asyncio
async def test_create_worker_run_persists_miniworker_completed_payload(monkeypatch):
    db = _FakeDB()
    service = AXEWorkerRunService(db=db)  # type: ignore[arg-type]

    async def _owned_session(**kwargs):
        _ = kwargs
        return SimpleNamespace(tenant_id="tenant-a")

    async def _owned_message(**kwargs):
        _ = kwargs
        return SimpleNamespace(id=uuid4())

    class _MiniworkerStub:
        async def dispatch(self, *, db, principal, payload, worker_run_id):  # noqa: ANN001
            _ = db
            _ = principal
            return SimpleNamespace(
                worker_run_id=worker_run_id,
                session_id=payload.session_id,
                message_id=payload.message_id,
                worker_type="miniworker",
                status="completed",
                label="AXE miniworker completed",
                detail="Patch proposal ready",
                updated_at=None,
                artifacts=[],
            )

    monkeypatch.setattr(service, "_get_owned_session", _owned_session)
    monkeypatch.setattr(service, "_get_owned_message", _owned_message)
    WorkerAdapterRegistry._adapters = {"miniworker": _MiniworkerStub()}  # type: ignore[assignment]
    WorkerAdapterRegistry._initialized = True

    payload = AXEWorkerRunCreateRequest(
        session_id=uuid4(),
        message_id=uuid4(),
        prompt="Replace line 3 with a guarded return",
        worker_type="miniworker",
    )

    response = await service.create_worker_run(principal=_principal(), payload=payload)

    assert response.status == "completed"
    assert db.added is not None
    assert db.added.label == "AXE miniworker completed"
    assert db.added.detail == "Patch proposal ready"


@pytest.mark.asyncio
async def test_create_worker_run_auto_routes_small_scope_to_miniworker(monkeypatch):
    db = _FakeDB()
    service = AXEWorkerRunService(db=db)  # type: ignore[arg-type]

    async def _owned_session(**kwargs):
        _ = kwargs
        return SimpleNamespace(tenant_id="tenant-a")

    async def _owned_message(**kwargs):
        _ = kwargs
        return SimpleNamespace(id=uuid4())

    class _MiniworkerStub:
        async def dispatch(self, *, db, principal, payload, worker_run_id):  # noqa: ANN001
            _ = db, principal, worker_run_id
            assert payload.worker_type == "miniworker"
            return SimpleNamespace(
                worker_run_id=worker_run_id,
                session_id=payload.session_id,
                message_id=payload.message_id,
                worker_type="miniworker",
                status="completed",
                label="AXE miniworker completed",
                detail="Patch proposal ready",
                updated_at=None,
                artifacts=[],
            )

    monkeypatch.setattr(service, "_get_owned_session", _owned_session)
    monkeypatch.setattr(service, "_get_owned_message", _owned_message)
    async def _resolve_routing_decision(*, principal, payload):  # noqa: ANN001
        _ = principal, payload
        return SimpleNamespace(id="route-1", selected_worker="miniworker", strategy="single_worker")

    monkeypatch.setattr(service, "_resolve_routing_decision", _resolve_routing_decision)
    WorkerAdapterRegistry._adapters = {"miniworker": _MiniworkerStub()}  # type: ignore[assignment]
    WorkerAdapterRegistry._initialized = True

    payload = AXEWorkerRunCreateRequest(
        session_id=uuid4(),
        message_id=uuid4(),
        prompt="Delete line 3 and replace it with a guarded return",
        worker_type="auto",
        file_scope=["backend/app/modules/axe_worker_runs/service.py"],
    )

    response = await service.create_worker_run(principal=_principal(), payload=payload)

    assert response.worker_type == "miniworker"
    assert response.artifacts[0].metadata["selected_worker"] == "miniworker"


@pytest.mark.asyncio
async def test_create_worker_run_auto_routes_broad_scope_to_opencode(monkeypatch):
    db = _FakeDB()
    service = AXEWorkerRunService(db=db)  # type: ignore[arg-type]

    async def _owned_session(**kwargs):
        _ = kwargs
        return SimpleNamespace(tenant_id="tenant-a")

    async def _owned_message(**kwargs):
        _ = kwargs
        return SimpleNamespace(id=uuid4())

    class _OpenCodeStub:
        async def dispatch(self, *, db, principal, payload, worker_run_id):  # noqa: ANN001
            _ = db, principal, worker_run_id
            assert payload.worker_type == "opencode"
            return SimpleNamespace(
                worker_run_id=worker_run_id,
                session_id=payload.session_id,
                message_id=payload.message_id,
                worker_type="opencode",
                status="queued",
                label="OpenCode worker queued",
                detail="Job dispatched: job_456",
                updated_at=None,
                artifacts=[],
            )

    monkeypatch.setattr(service, "_get_owned_session", _owned_session)
    monkeypatch.setattr(service, "_get_owned_message", _owned_message)
    async def _resolve_routing_decision(*, principal, payload):  # noqa: ANN001
        _ = principal, payload
        return SimpleNamespace(id="route-2", selected_worker="opencode", strategy="single_worker")

    monkeypatch.setattr(service, "_resolve_routing_decision", _resolve_routing_decision)
    WorkerAdapterRegistry._adapters = {"opencode": _OpenCodeStub()}  # type: ignore[assignment]
    WorkerAdapterRegistry._initialized = True

    payload = AXEWorkerRunCreateRequest(
        session_id=uuid4(),
        message_id=uuid4(),
        prompt="Run a security review across auth, secrets, infra and deployment paths",
        worker_type="auto",
    )

    response = await service.create_worker_run(principal=_principal(), payload=payload)

    assert response.worker_type == "opencode"


@pytest.mark.asyncio
async def test_create_worker_run_bounded_apply_waits_for_approval(monkeypatch):
    db = _FakeDB()
    service = AXEWorkerRunService(db=db)  # type: ignore[arg-type]

    async def _owned_session(**kwargs):
        _ = kwargs
        return SimpleNamespace(tenant_id="tenant-a")

    async def _owned_message(**kwargs):
        _ = kwargs
        return SimpleNamespace(id=uuid4())

    events: list[str] = []

    async def _record_event(**kwargs):  # noqa: ANN001
        events.append(kwargs["event_type"])
        return None

    monkeypatch.setattr(service, "_get_owned_session", _owned_session)
    monkeypatch.setattr(service, "_get_owned_message", _owned_message)
    monkeypatch.setattr("app.modules.axe_worker_runs.service.record_control_plane_event", _record_event)

    payload = AXEWorkerRunCreateRequest(
        session_id=uuid4(),
        message_id=uuid4(),
        prompt="Replace line 3 with a guarded return",
        worker_type="miniworker",
        execution_mode="bounded_apply",
        file_scope=["backend/app/modules/axe_worker_runs/service.py"],
    )

    response = await service.create_worker_run(principal=_principal(), payload=payload)

    assert response.status == "waiting_input"
    assert response.label == "AXE miniworker waiting for approval"
    assert any(artifact.metadata.get("approval_required") is True for artifact in response.artifacts)
    assert events == ["axe.miniworker.bounded_apply.approval_required.v1"]


@pytest.mark.asyncio
async def test_create_worker_run_bounded_apply_requires_operator_role(monkeypatch):
    db = _FakeDB()
    service = AXEWorkerRunService(db=db)  # type: ignore[arg-type]

    async def _owned_session(**kwargs):
        _ = kwargs
        return SimpleNamespace(tenant_id="tenant-a")

    async def _owned_message(**kwargs):
        _ = kwargs
        return SimpleNamespace(id=uuid4())

    monkeypatch.setattr(service, "_get_owned_session", _owned_session)
    monkeypatch.setattr(service, "_get_owned_message", _owned_message)

    payload = AXEWorkerRunCreateRequest(
        session_id=uuid4(),
        message_id=uuid4(),
        prompt="Replace line 3 with a guarded return",
        worker_type="miniworker",
        execution_mode="bounded_apply",
        file_scope=["backend/app/modules/axe_worker_runs/service.py"],
    )

    with pytest.raises(ValueError, match="requires operator/admin role"):
        await service.create_worker_run(principal=_viewer_principal(), payload=payload)


@pytest.mark.asyncio
async def test_create_worker_run_bounded_apply_records_approval_before_dispatch(monkeypatch):
    db = _FakeDB()
    service = AXEWorkerRunService(db=db)  # type: ignore[arg-type]

    async def _owned_session(**kwargs):
        _ = kwargs
        return SimpleNamespace(tenant_id="tenant-a")

    async def _owned_message(**kwargs):
        _ = kwargs
        return SimpleNamespace(id=uuid4())

    events: list[str] = []

    async def _record_event(**kwargs):  # noqa: ANN001
        events.append(kwargs["event_type"])
        return None

    class _MiniworkerStub:
        async def dispatch(self, *, db, principal, payload, worker_run_id):  # noqa: ANN001
            _ = db, principal
            assert payload.approval_confirmed is True
            return SimpleNamespace(
                worker_run_id=worker_run_id,
                session_id=payload.session_id,
                message_id=payload.message_id,
                worker_type="miniworker",
                status="completed",
                label="AXE miniworker completed",
                detail="Patch applied within bounded scope",
                updated_at=None,
                artifacts=[],
            )

    monkeypatch.setattr(service, "_get_owned_session", _owned_session)
    monkeypatch.setattr(service, "_get_owned_message", _owned_message)
    monkeypatch.setattr("app.modules.axe_worker_runs.service.record_control_plane_event", _record_event)
    WorkerAdapterRegistry._adapters = {"miniworker": _MiniworkerStub()}  # type: ignore[assignment]
    WorkerAdapterRegistry._initialized = True

    payload = AXEWorkerRunCreateRequest(
        session_id=uuid4(),
        message_id=uuid4(),
        prompt="Replace line 3 with a guarded return",
        worker_type="miniworker",
        execution_mode="bounded_apply",
        approval_confirmed=True,
        approval_reason="Operator approved exact scoped edit",
        file_scope=["backend/app/modules/axe_worker_runs/service.py"],
    )

    response = await service.create_worker_run(principal=_principal(), payload=payload)

    assert response.status == "completed"
    assert events == ["axe.miniworker.bounded_apply.approved.v1"]


@pytest.mark.asyncio
async def test_create_worker_run_bounded_apply_requires_reason_when_preapproved(monkeypatch):
    db = _FakeDB()
    service = AXEWorkerRunService(db=db)  # type: ignore[arg-type]

    async def _owned_session(**kwargs):
        _ = kwargs
        return SimpleNamespace(tenant_id="tenant-a")

    async def _owned_message(**kwargs):
        _ = kwargs
        return SimpleNamespace(id=uuid4())

    monkeypatch.setattr(service, "_get_owned_session", _owned_session)
    monkeypatch.setattr(service, "_get_owned_message", _owned_message)

    payload = AXEWorkerRunCreateRequest(
        session_id=uuid4(),
        message_id=uuid4(),
        prompt="Replace line 3 with a guarded return",
        worker_type="miniworker",
        execution_mode="bounded_apply",
        approval_confirmed=True,
        approval_reason=None,
        file_scope=["backend/app/modules/axe_worker_runs/service.py"],
    )

    with pytest.raises(ValueError, match="requires non-empty approval_reason"):
        await service.create_worker_run(principal=_principal(), payload=payload)


@pytest.mark.asyncio
async def test_approve_worker_run_dispatches_pending_bounded_apply(monkeypatch):
    db = _FakeDB()
    service = AXEWorkerRunService(db=db)  # type: ignore[arg-type]
    pending_payload = AXEWorkerRunCreateRequest(
        session_id=uuid4(),
        message_id=uuid4(),
        prompt="Replace line 3 with a guarded return",
        worker_type="miniworker",
        execution_mode="bounded_apply",
        file_scope=["backend/app/modules/axe_worker_runs/service.py"],
    ).model_dump(mode="json")
    row = SimpleNamespace(
        worker_run_id="wr-approve-1",
        session_id=uuid4(),
        message_id=uuid4(),
        backend_run_id=None,
        backend_run_type="miniworker_job",
        status="waiting_input",
        label="AXE miniworker waiting for approval",
        detail="Needs approval",
        artifacts_json=[
            {"type": "routing_decision", "metadata": {"routing_decision_id": "route-1", "purpose_evaluation_id": "purpose-1"}},
            {"type": "pending_request", "metadata": pending_payload},
        ],
        updated_at=None,
    )

    async def _get_owned_worker_run(**kwargs):
        _ = kwargs
        return row

    events: list[str] = []

    async def _record_event(**kwargs):  # noqa: ANN001
        events.append(kwargs["event_type"])
        return None

    class _MiniworkerStub:
        async def dispatch(self, *, db, principal, payload, worker_run_id):  # noqa: ANN001
            _ = db, principal
            assert payload.approval_confirmed is True
            assert payload.approval_reason == "approved"
            return SimpleNamespace(
                worker_run_id=worker_run_id,
                session_id=payload.session_id,
                message_id=payload.message_id,
                worker_type="miniworker",
                status="completed",
                label="AXE miniworker completed",
                detail="Patch applied within bounded scope",
                updated_at=None,
                artifacts=[],
            )

    monkeypatch.setattr(service, "_get_owned_worker_run", _get_owned_worker_run)
    monkeypatch.setattr("app.modules.axe_worker_runs.service.record_control_plane_event", _record_event)
    WorkerAdapterRegistry._adapters = {"miniworker": _MiniworkerStub()}  # type: ignore[assignment]
    WorkerAdapterRegistry._initialized = True

    response = await service.approve_worker_run(
        principal=_principal(),
        worker_run_id="wr-approve-1",
        approval_reason="approved",
    )

    assert response.status == "completed"
    assert row.detail == "Patch applied within bounded scope"
    assert events == ["axe.miniworker.bounded_apply.approved.v1"]
    approval_history = next((artifact for artifact in row.artifacts_json if artifact.get("type") == "approval_history"), None)
    assert approval_history is not None
    assert approval_history["metadata"]["decided_by"] == "axe-user"
    assert isinstance(approval_history["metadata"]["decided_at"], str)
    assert approval_history["metadata"]["routing_decision_id"] == "route-1"
    assert approval_history["metadata"]["purpose_evaluation_id"] == "purpose-1"


@pytest.mark.asyncio
async def test_approve_worker_run_requires_operator_role(monkeypatch):
    db = _FakeDB()
    service = AXEWorkerRunService(db=db)  # type: ignore[arg-type]
    row = SimpleNamespace(
        worker_run_id="wr-approve-2",
        session_id=uuid4(),
        message_id=uuid4(),
        backend_run_id=None,
        backend_run_type="miniworker_job",
        status="waiting_input",
        label="AXE miniworker waiting for approval",
        detail="Needs approval",
        artifacts_json=[{"type": "pending_request", "metadata": AXEWorkerRunCreateRequest(
            session_id=uuid4(),
            message_id=uuid4(),
            prompt="Replace line 3",
            worker_type="miniworker",
            execution_mode="bounded_apply",
            file_scope=["backend/app/modules/axe_worker_runs/service.py"],
        ).model_dump(mode="json")}],
        updated_at=None,
    )

    async def _get_owned_worker_run(**kwargs):
        _ = kwargs
        return row

    monkeypatch.setattr(service, "_get_owned_worker_run", _get_owned_worker_run)

    with pytest.raises(ValueError, match="requires operator/admin role"):
        await service.approve_worker_run(
            principal=_viewer_principal(),
            worker_run_id="wr-approve-2",
            approval_reason="approved",
        )


@pytest.mark.asyncio
async def test_reject_worker_run_marks_failed(monkeypatch):
    db = _FakeDB()
    service = AXEWorkerRunService(db=db)  # type: ignore[arg-type]
    row = SimpleNamespace(
        worker_run_id="wr-reject-1",
        session_id=uuid4(),
        message_id=uuid4(),
        backend_run_id=None,
        backend_run_type="miniworker_job",
        status="waiting_input",
        label="AXE miniworker waiting for approval",
        detail="Needs approval",
        artifacts_json=[],
        updated_at=None,
    )

    async def _get_owned_worker_run(**kwargs):
        _ = kwargs
        return row

    events: list[str] = []

    async def _record_event(**kwargs):  # noqa: ANN001
        events.append(kwargs["event_type"])
        return None

    monkeypatch.setattr(service, "_get_owned_worker_run", _get_owned_worker_run)
    monkeypatch.setattr("app.modules.axe_worker_runs.service.record_control_plane_event", _record_event)

    response = await service.reject_worker_run(
        principal=_principal(),
        worker_run_id="wr-reject-1",
        rejection_reason="not approved",
    )

    assert response.status == "failed"
    assert row.detail == "not approved"
    assert events == ["axe.miniworker.bounded_apply.rejected.v1"]
    assert row.artifacts_json[0]["type"] == "approval_history"
    assert row.artifacts_json[0]["metadata"]["decided_by"] == "axe-user"
    assert isinstance(row.artifacts_json[0]["metadata"]["decided_at"], str)
