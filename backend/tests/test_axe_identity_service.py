from __future__ import annotations

from datetime import datetime
from types import SimpleNamespace
from uuid import uuid4

import pytest
from sqlalchemy.exc import ProgrammingError

from app.modules.axe_identity.service import AXEIdentityService


class _FailingSession:
    def __init__(self) -> None:
        self.rollback_calls = 0

    async def execute(self, *_args, **_kwargs):
        raise ProgrammingError("SELECT ...", {}, Exception("relation axe_identities does not exist"))

    async def rollback(self):
        self.rollback_calls += 1


@pytest.mark.asyncio
async def test_axe_identity_get_active_falls_back_when_table_missing() -> None:
    session = _FailingSession()
    service = AXEIdentityService(session)  # type: ignore[arg-type]

    identity = await service.get_active()

    assert identity is None
    assert session.rollback_calls == 1


@pytest.mark.asyncio
async def test_axe_identity_default_is_timezone_aware() -> None:
    session = _FailingSession()
    service = AXEIdentityService(session)  # type: ignore[arg-type]

    identity = await service.get_default()

    assert identity.created_at.tzinfo is not None
    assert identity.updated_at.tzinfo is not None


class _ScalarResult:
    def __init__(self, value):
        self._value = value

    def scalar_one_or_none(self):
        return self._value


class _IdentitySession:
    def __init__(self, identity):
        self._identity = identity

    async def execute(self, *_args, **_kwargs):
        return _ScalarResult(self._identity)


@pytest.mark.asyncio
async def test_axe_identity_get_active_handles_missing_timestamps() -> None:
    identity = SimpleNamespace(
        id=uuid4(),
        name="AXE NullTs",
        description="test",
        system_prompt="This is a valid prompt text",
        personality=None,
        capabilities=None,
        is_active=True,
        version=None,
        created_at=None,
        updated_at=None,
        created_by="system",
    )
    service = AXEIdentityService(_IdentitySession(identity))  # type: ignore[arg-type]

    response = await service.get_active()

    assert response is not None
    assert response.name == "AXE NullTs"
    assert response.created_at is not None
    assert response.updated_at is not None
    assert isinstance(response.created_at, datetime)
    assert isinstance(response.updated_at, datetime)
    assert response.updated_at >= response.created_at.replace(tzinfo=response.updated_at.tzinfo)
