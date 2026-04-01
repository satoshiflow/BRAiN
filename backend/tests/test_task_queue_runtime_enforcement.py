from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from types import SimpleNamespace
from uuid import uuid4

import pytest

from app.modules.task_queue.models import TaskStatus
from app.modules.task_queue.service import TaskQueueService


@pytest.mark.asyncio
async def test_create_task_lease_includes_runtime_selected_worker(monkeypatch: pytest.MonkeyPatch) -> None:
    service = TaskQueueService()
    captured = {}

    async def _fake_create_task(db, task_data, created_by=None, created_by_type=None):  # noqa: ANN001
        _ = (db, created_by, created_by_type)
        captured["task_data"] = task_data
        return SimpleNamespace(task_id="task-lease-1", config=task_data.config)

    monkeypatch.setattr(service, "create_task", _fake_create_task)

    run = SimpleNamespace(
        id=uuid4(),
        skill_key="demo.skill",
        skill_version=1,
        tenant_id="tenant-a",
        mission_id="mission-1",
        correlation_id="corr-1",
        deadline_at=None,
        provider_selection_snapshot={
            "runtime_decision": {
                "decision_id": "rdec_1",
                "selected_worker": "openclaw",
            }
        },
    )
    principal = SimpleNamespace(principal_id="svc-worker", principal_type=SimpleNamespace(value="service"))

    task = await service.create_task_lease_for_skill_run(db=None, run=run, principal=principal)

    assert task.config["required_worker"] == "openclaw"
    assert captured["task_data"].config["runtime_decision_id"] == "rdec_1"
    assert captured["task_data"].config["enforced_by"] == "runtime_control"


@dataclass
class _ScalarResult:
    task: object

    def scalar_one_or_none(self):
        return self.task


@dataclass
class _DepsResult:
    rows: list

    def all(self):
        return self.rows


class _FakeDB:
    def __init__(self, task):
        self.task = task
        self.commit_calls = 0
        self.refresh_calls = 0
        self.execute_calls = 0

    async def execute(self, _query):  # noqa: ANN001
        self.execute_calls += 1
        if self.execute_calls == 1:
            return _ScalarResult(self.task)
        return _DepsResult([])

    async def commit(self):
        self.commit_calls += 1

    async def refresh(self, _task):  # noqa: ANN001
        self.refresh_calls += 1


@pytest.mark.asyncio
async def test_claim_next_task_enforces_required_worker_lane() -> None:
    service = TaskQueueService()
    task = SimpleNamespace(
        task_id="task-1",
        status=TaskStatus.PENDING,
        scheduled_at=None,
        created_at=datetime.now(timezone.utc).replace(tzinfo=None),
        depends_on=[],
        priority=75,
        config={"required_worker": "openclaw"},
        claimed_by=None,
        claimed_at=None,
        wait_time_ms=None,
    )
    db = _FakeDB(task)

    claimed = await service.claim_next_task(db=db, agent_id="miniworker-agent-1")

    assert claimed is None
    assert db.commit_calls == 0
    assert task.status == TaskStatus.PENDING


@pytest.mark.asyncio
async def test_claim_next_task_allows_matching_required_worker_lane() -> None:
    service = TaskQueueService()
    task = SimpleNamespace(
        task_id="task-2",
        status=TaskStatus.PENDING,
        scheduled_at=None,
        created_at=datetime.now(timezone.utc).replace(tzinfo=None),
        depends_on=[],
        priority=75,
        config={"required_worker": "openclaw"},
        claimed_by=None,
        claimed_at=None,
        wait_time_ms=None,
    )
    db = _FakeDB(task)

    claimed = await service.claim_next_task(db=db, agent_id="openclaw-agent-1")

    assert claimed is task
    assert db.commit_calls == 1
    assert task.status == TaskStatus.CLAIMED
    assert task.claimed_by == "openclaw-agent-1"
