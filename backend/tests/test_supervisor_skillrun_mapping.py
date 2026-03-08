from __future__ import annotations

from datetime import datetime, timezone

import pytest

from app.modules.supervisor.service import get_status, list_agents


class FakeScalarResult:
    def __init__(self, value):
        self._value = value

    def scalar(self):
        return self._value


class FakeRowsResult:
    def __init__(self, rows):
        self._rows = rows

    def all(self):
        return self._rows


class FakeAgentScalars:
    def __init__(self, items):
        self._items = items

    def all(self):
        return self._items


class FakeAgentsResult:
    def __init__(self, items):
        self._items = items

    def scalars(self):
        return FakeAgentScalars(self._items)


class FakeDb:
    def __init__(self):
        self.count_values = iter([6, 1, 2, 2, 1, 0])

    async def execute(self, query):
        query_text = str(query)
        if "GROUP BY skill_runs.requested_by" in query_text:
            return FakeRowsResult([("agent-a", 2), ("agent-b", 1)])
        if "FROM agents" in query_text:
            return FakeAgentsResult(
                [
                    type(
                        "Agent",
                        (),
                        {
                            "agent_id": "agent-a",
                            "name": "Alpha",
                            "agent_type": "worker",
                            "status": type("State", (), {"value": "active"})(),
                            "last_heartbeat": datetime.now(timezone.utc),
                            "registered_at": datetime.now(timezone.utc),
                        },
                    )(),
                    type(
                        "Agent",
                        (),
                        {
                            "agent_id": "agent-b",
                            "name": "Beta",
                            "agent_type": "worker",
                            "status": type("State", (), {"value": "offline"})(),
                            "last_heartbeat": None,
                            "registered_at": datetime.now(timezone.utc),
                        },
                    )(),
                ]
            )
        return FakeScalarResult(next(self.count_values))


@pytest.mark.asyncio
async def test_supervisor_status_aggregates_skill_runs() -> None:
    status = await get_status(FakeDb())
    assert status.total_missions == 6
    assert status.running_missions == 1
    assert status.pending_missions == 2
    assert status.completed_missions == 2
    assert status.failed_missions == 1
    assert status.cancelled_missions == 0
    assert len(status.agents) == 2


@pytest.mark.asyncio
async def test_supervisor_agents_include_running_skill_runs() -> None:
    agents = await list_agents(FakeDb())
    assert agents[0].id == "agent-a"
    assert agents[0].missions_running == 2
    assert agents[1].id == "agent-b"
    assert agents[1].missions_running == 1
