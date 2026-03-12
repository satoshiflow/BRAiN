from __future__ import annotations

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
