from __future__ import annotations

from types import SimpleNamespace

import pytest

import app.modules.skills.axe_chat_skill_seeder as seeder


@pytest.mark.asyncio
async def test_seed_axe_chat_skill_contract_creates_and_activates(monkeypatch: pytest.MonkeyPatch) -> None:
    calls = {
        "cap_create": 0,
        "cap_transition": 0,
        "skill_create": 0,
        "skill_transition": 0,
    }

    class FakeCapabilityService:
        async def resolve_definition(self, db, tenant_id, owner_scope, capability_key):  # noqa: ANN001
            return None

        async def create_definition(self, db, payload, principal):  # noqa: ANN001
            calls["cap_create"] += 1
            return SimpleNamespace(id="cap-1", status="draft")

        async def transition_status(self, db, capability_id, target_status, principal):  # noqa: ANN001
            calls["cap_transition"] += 1
            return SimpleNamespace(id=capability_id, status=target_status.value)

    class FakeSkillService:
        async def resolve_definition(self, db, tenant_id, owner_scope, skill_key, version_value):  # noqa: ANN001
            return None

        async def create_definition(self, db, payload, principal):  # noqa: ANN001
            calls["skill_create"] += 1
            return SimpleNamespace(id="skill-1", status="draft")

        async def transition_status(self, db, skill_id, target_status, principal):  # noqa: ANN001
            calls["skill_transition"] += 1
            return SimpleNamespace(id=skill_id, status=target_status.value)

    monkeypatch.setattr(seeder, "get_capability_registry_service", lambda: FakeCapabilityService())
    monkeypatch.setattr(seeder, "get_skill_registry_service", lambda: FakeSkillService())
    monkeypatch.setenv("AXE_CHAT_SKILL_KEY", "axe.chat.bridge")
    monkeypatch.setenv("AXE_CHAT_SKILL_VERSION", "1")
    monkeypatch.setenv("AXE_PROVIDER_CAPABILITY_KEY", "text.generate")

    await seeder.seed_axe_chat_skill_contract(db=object())

    assert calls["cap_create"] == 1
    assert calls["cap_transition"] == 1
    assert calls["skill_create"] == 1
    assert calls["skill_transition"] == 3
