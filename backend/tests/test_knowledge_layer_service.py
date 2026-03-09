from __future__ import annotations

from types import SimpleNamespace
from uuid import uuid4

import pytest

from app.core.auth_deps import Principal, PrincipalType
from app.modules.knowledge_layer.service import KnowledgeLayerService


class FakeDb:
    def __init__(self) -> None:
        self._added = []

    def add(self, item) -> None:
        self._added.append(item)

    async def commit(self) -> None:
        return None

    async def refresh(self, item) -> None:
        return None


def _principal() -> Principal:
    return Principal(
        principal_id="operator-1",
        principal_type=PrincipalType.HUMAN,
        email="operator@example.com",
        name="Operator",
        roles=["operator"],
        scopes=["read", "write"],
        tenant_id="tenant-a",
    )


@pytest.mark.asyncio
async def test_ingest_run_lesson_uses_experience_layer(monkeypatch) -> None:
    service = KnowledgeLayerService()
    db = FakeDb()
    run_id = uuid4()
    exp_id = uuid4()

    class FakeExperienceService:
        async def ingest_skill_run(self, db_param, skill_run_id, principal):
            assert db_param is db
            assert skill_run_id == run_id
            assert principal.tenant_id == "tenant-a"
            return SimpleNamespace(
                id=exp_id,
                skill_run_id=run_id,
                state="succeeded",
                summary="SkillRun completed successfully",
                evaluation_summary={"score": 0.9},
                signals={"skill_key": "builder.webgenesis.generate"},
            )

    module = __import__("app.modules.knowledge_layer.service", fromlist=["get_experience_layer_service"])
    monkeypatch.setattr(module, "get_experience_layer_service", lambda: FakeExperienceService())

    item = await service.ingest_run_lesson(db, run_id, _principal())

    assert item.source == "experience_record"
    assert item.module == "experience_layer"
    assert item.title == "Run lesson: builder.webgenesis.generate"
    assert item.provenance_refs[0]["type"] == "skill_run"
    assert item.provenance_refs[1] == {"type": "experience_record", "id": str(exp_id)}


@pytest.mark.asyncio
async def test_ingest_run_lesson_requires_tenant() -> None:
    service = KnowledgeLayerService()
    db = FakeDb()
    principal = Principal(
        principal_id="system-admin-1",
        principal_type=PrincipalType.HUMAN,
        email="sysadmin@example.com",
        name="System Admin",
        roles=["SYSTEM_ADMIN"],
        scopes=["read", "write"],
        tenant_id=None,
    )

    with pytest.raises(PermissionError, match="Tenant context required"):
        await service.ingest_run_lesson(db, uuid4(), principal)
