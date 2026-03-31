from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from types import SimpleNamespace
from uuid import uuid4

import pytest

from app.modules.task_queue.schemas import TaskComplete, TaskFail
from app.modules.task_queue.service import TaskQueueService


@dataclass
class _ScalarResult:
    task: object

    def scalar_one_or_none(self):
        return self.task


@dataclass
class _FakeDB:
    task: object
    commit_calls: int = 0
    refresh_calls: int = 0

    async def execute(self, _query):
        return _ScalarResult(self.task)

    async def commit(self):
        self.commit_calls += 1

    async def refresh(self, _row):
        self.refresh_calls += 1

    async def rollback(self):
        return None


@pytest.mark.asyncio
async def test_complete_task_finalizes_linked_skill_run(monkeypatch):
    task = SimpleNamespace(
        task_id="task-1",
        claimed_by="openclaw-agent",
        status="running",
        started_at=datetime.now(timezone.utc).replace(tzinfo=None),
        completed_at=None,
        result=None,
        execution_time_ms=None,
        wait_time_ms=None,
        skill_run_id=uuid4(),
        created_by="svc-openclaw",
        created_by_type="service",
        tenant_id="tenant-a",
    )
    db = _FakeDB(task=task)
    service = TaskQueueService()
    calls: list[dict] = []

    class _SkillEngineStub:
        async def finalize_external_run(self, db, run_id, principal, **kwargs):
            calls.append(
                {
                    "db": db,
                    "run_id": run_id,
                    "principal_id": principal.principal_id,
                    "kwargs": kwargs,
                }
            )

    monkeypatch.setattr(
        "app.modules.task_queue.service.get_skill_engine_service",
        lambda: _SkillEngineStub(),
    )

    result = await service.complete_task(
        db,
        task_id="task-1",
        agent_id="openclaw-agent",
        complete_data=TaskComplete(result={"text": "done"}),
    )

    assert result is task
    assert len(calls) == 1
    assert calls[0]["run_id"] == task.skill_run_id
    assert calls[0]["principal_id"] == "svc-openclaw"
    assert calls[0]["kwargs"]["success"] is True
    assert calls[0]["kwargs"]["output_payload"] == {"text": "done"}


@pytest.mark.asyncio
async def test_fail_task_finalizes_linked_skill_run_on_terminal_failure(monkeypatch):
    task = SimpleNamespace(
        task_id="task-2",
        claimed_by="openclaw-agent",
        status="running",
        started_at=datetime.now(timezone.utc).replace(tzinfo=None),
        completed_at=None,
        error_message=None,
        error_details=None,
        retry_count=0,
        max_retries=1,
        retry_delay_seconds=30,
        scheduled_at=None,
        skill_run_id=uuid4(),
        created_by="svc-openclaw",
        created_by_type="service",
        tenant_id="tenant-a",
    )
    db = _FakeDB(task=task)
    service = TaskQueueService()
    calls: list[dict] = []

    class _SkillEngineStub:
        async def finalize_external_run(self, db, run_id, principal, **kwargs):
            calls.append(
                {
                    "db": db,
                    "run_id": run_id,
                    "principal_id": principal.principal_id,
                    "kwargs": kwargs,
                }
            )

    monkeypatch.setattr(
        "app.modules.task_queue.service.get_skill_engine_service",
        lambda: _SkillEngineStub(),
    )

    result = await service.fail_task(
        db,
        task_id="task-2",
        agent_id="openclaw-agent",
        fail_data=TaskFail(error_message="worker crashed", retry=False),
    )

    assert result is task
    assert len(calls) == 1
    assert calls[0]["run_id"] == task.skill_run_id
    assert calls[0]["kwargs"]["success"] is False
    assert calls[0]["kwargs"]["failure_code"] == "EXTERNAL-FAIL"
    assert calls[0]["kwargs"]["failure_reason_sanitized"] == "worker crashed"


@pytest.mark.asyncio
async def test_complete_task_uses_fallback_when_finalize_external_run_raises(monkeypatch):
    task = SimpleNamespace(
        task_id="task-3",
        claimed_by="openclaw-agent",
        status="running",
        started_at=datetime.now(timezone.utc).replace(tzinfo=None),
        completed_at=None,
        result=None,
        execution_time_ms=None,
        wait_time_ms=None,
        skill_run_id=uuid4(),
        created_by="svc-openclaw",
        created_by_type="service",
        tenant_id="tenant-a",
    )
    db = _FakeDB(task=task)
    service = TaskQueueService()
    fallback_calls: list[dict] = []

    class _SkillEngineStub:
        async def finalize_external_run(self, db, run_id, principal, **kwargs):
            raise RuntimeError("missing control_plane_events")

    async def _fallback_stub(**kwargs):
        fallback_calls.append(kwargs)

    monkeypatch.setattr(
        "app.modules.task_queue.service.get_skill_engine_service",
        lambda: _SkillEngineStub(),
    )
    monkeypatch.setattr(service, "_fallback_finalize_linked_skill_run", _fallback_stub)

    result = await service.complete_task(
        db,
        task_id="task-3",
        agent_id="openclaw-agent",
        complete_data=TaskComplete(result={"text": "done"}),
    )

    assert result is task
    assert len(fallback_calls) == 1
    assert fallback_calls[0]["task_id"] == "task-3"
    assert fallback_calls[0]["skill_run_id"] == task.skill_run_id
    assert fallback_calls[0]["success"] is True
