from __future__ import annotations

from contextlib import asynccontextmanager

import pytest

import app.modules.supervisor.service as supervisor_service


class _FakeConn:
    def __init__(self) -> None:
        self.sync_calls = 0

    async def run_sync(self, func):  # noqa: ANN001
        self.sync_calls += 1
        _ = func
        return None


class _FakeBind:
    def __init__(self) -> None:
        self.conn = _FakeConn()
        self.begin_calls = 0

    @asynccontextmanager
    async def begin(self):
        self.begin_calls += 1
        yield self.conn


class _FakeSession:
    def __init__(self) -> None:
        self.bind = _FakeBind()


@pytest.mark.asyncio
async def test_ensure_domain_escalation_table_runs_create_all_once(monkeypatch) -> None:
    session = _FakeSession()
    monkeypatch.setattr(supervisor_service, "_domain_escalation_table_ready", False)

    await supervisor_service._ensure_domain_escalation_table(session)  # noqa: SLF001
    await supervisor_service._ensure_domain_escalation_table(session)  # noqa: SLF001

    assert session.bind.begin_calls == 1
    assert session.bind.conn.sync_calls == 1
