from __future__ import annotations

from datetime import datetime, timezone
from types import SimpleNamespace

import pytest

from app.modules.config_management.service import ConfigManagementService


def test_vault_definitions_include_core_secret_keys(monkeypatch):
    monkeypatch.setenv("BRAIN_ADMIN_PASSWORD", "admin-password-123456")
    service = ConfigManagementService()

    definitions = service.list_vault_definitions()
    keys = {item.key for item in definitions}

    assert "BRAIN_ADMIN_PASSWORD" in keys
    assert "DATABASE_URL" in keys


def test_validate_vault_candidate_rejects_short_secret():
    service = ConfigManagementService()
    errors = service.validate_vault_candidate("BRAIN_ADMIN_PASSWORD", "short")
    assert any("at least 16" in error for error in errors)


def test_secret_encrypt_decrypt_roundtrip(monkeypatch):
    monkeypatch.setenv("CONFIG_VAULT_ENCRYPTION_KEY", "unit-test-fernet-key")
    service = ConfigManagementService()

    encrypted = service._encrypt_secret_payload("this-is-a-good-secret-value")
    decrypted = service._decrypt_secret_payload(encrypted)

    assert encrypted["alg"] == "fernet"
    assert decrypted == "this-is-a-good-secret-value"


@pytest.mark.asyncio
async def test_generate_jwt_private_key_uses_upsert(monkeypatch):
    service = ConfigManagementService()
    db = object()
    upsert_calls = []

    async def _upsert_stub(db, *, key, value, actor_id, actor_type, reason):  # noqa: ANN001
        upsert_calls.append(
            {
                "db": db,
                "key": key,
                "value": value,
                "actor_id": actor_id,
                "actor_type": actor_type,
                "reason": reason,
            }
        )
        return None

    monkeypatch.setattr(service, "upsert_vault_value", _upsert_stub)

    response = await service.generate_vault_value(
        db,
        key="BRAIN_JWT_PRIVATE_KEY",
        actor_id="admin-user",
        actor_type="human",
        reason="rotation",
        length=None,
    )

    assert response.generated is True
    assert response.revealed_value is not None
    assert "BEGIN PRIVATE KEY" in response.revealed_value
    assert len(upsert_calls) == 1
    assert upsert_calls[0]["key"] == "BRAIN_JWT_PRIVATE_KEY"


@pytest.mark.asyncio
async def test_upsert_vault_value_masks_secret_and_sets_db_override(monkeypatch):
    monkeypatch.setenv("CONFIG_VAULT_ENCRYPTION_KEY", "unit-test-fernet-key")
    service = ConfigManagementService()
    db = object()

    async def _set_config_stub(db, config_data, user_id):  # noqa: ANN001
        _ = config_data
        return SimpleNamespace(updated_at=datetime.now(timezone.utc), updated_by=user_id)

    async def _audit_stub(**kwargs):  # noqa: ANN001
        return None

    monkeypatch.setattr(service, "set_config", _set_config_stub)
    monkeypatch.setattr("app.modules.config_management.service.write_unified_audit", _audit_stub)

    value = await service.upsert_vault_value(
        db,
        key="BRAIN_ADMIN_PASSWORD",
        value="this-is-a-new-admin-password-123",
        actor_id="admin-user",
        actor_type="human",
        reason="manual update",
    )

    assert value.key == "BRAIN_ADMIN_PASSWORD"
    assert value.effective_source == "db_override"
    assert value.masked_value == "********"


@pytest.mark.asyncio
async def test_create_rotation_request_for_secret_masks_candidate(monkeypatch):
    monkeypatch.setenv("CONFIG_VAULT_ENCRYPTION_KEY", "unit-test-fernet-key")
    service = ConfigManagementService()
    db = object()
    set_calls = []

    async def _set_config_stub(db, config_data, user_id):  # noqa: ANN001
        set_calls.append({"key": config_data.key, "value": config_data.value, "user_id": user_id})
        return SimpleNamespace(updated_at=datetime.now(timezone.utc), updated_by=user_id)

    async def _audit_stub(**kwargs):  # noqa: ANN001
        return None

    monkeypatch.setattr(service, "set_config", _set_config_stub)
    monkeypatch.setattr("app.modules.config_management.service.write_unified_audit", _audit_stub)

    response = await service.create_rotation_request(
        db,
        key="BRAIN_VIEWER_PASSWORD",
        value="this-is-a-rotated-viewer-password-123",
        generate=False,
        length=None,
        actor_id="operator-user",
        actor_type="human",
        reason="quarterly rotation",
    )

    assert response.status == "pending"
    assert response.key == "BRAIN_VIEWER_PASSWORD"
    assert response.masked_candidate == "********"
    assert len(set_calls) == 1
    assert set_calls[0]["key"].startswith("__vault_pending__:")


@pytest.mark.asyncio
async def test_approve_rotation_request_activates_value_and_deletes_pending(monkeypatch):
    monkeypatch.setenv("CONFIG_VAULT_ENCRYPTION_KEY", "unit-test-fernet-key")
    service = ConfigManagementService()
    db = object()
    approve_calls = {"upsert": 0, "delete": 0}

    encrypted_candidate = service._encrypt_secret_payload("this-is-a-rotated-admin-password-123")
    pending_payload = {
        "target_key": "BRAIN_ADMIN_PASSWORD",
        "candidate": encrypted_candidate,
        "candidate_encrypted": True,
        "requested_by": "operator-user",
        "requested_at": datetime.now(timezone.utc).isoformat(),
        "requested_reason": "rotation",
    }

    async def _get_config_stub(db, key, environment):  # noqa: ANN001
        _ = environment
        if key.startswith("__vault_pending__:"):
            return SimpleNamespace(value=pending_payload)
        return None

    async def _upsert_stub(db, *, key, value, actor_id, actor_type, reason):  # noqa: ANN001
        approve_calls["upsert"] += 1
        assert key == "BRAIN_ADMIN_PASSWORD"
        assert value == "this-is-a-rotated-admin-password-123"
        return SimpleNamespace(
            key=key,
            classification="secret",
            value_type="string",
            effective_source="db_override",
            is_set=True,
            masked_value="********",
            updated_at=datetime.now(timezone.utc),
            updated_by=actor_id,
        )

    async def _delete_stub(db, key, environment):  # noqa: ANN001
        _ = db
        _ = environment
        assert key.startswith("__vault_pending__:")
        approve_calls["delete"] += 1
        return True

    async def _audit_stub(**kwargs):  # noqa: ANN001
        return None

    monkeypatch.setattr(service, "get_config", _get_config_stub)
    monkeypatch.setattr(service, "upsert_vault_value", _upsert_stub)
    monkeypatch.setattr(service, "delete_config", _delete_stub)
    monkeypatch.setattr("app.modules.config_management.service.write_unified_audit", _audit_stub)

    response = await service.approve_rotation_request(
        db,
        key="BRAIN_ADMIN_PASSWORD",
        actor_id="admin-user",
        actor_type="human",
        reason="approved",
    )

    assert response.key == "BRAIN_ADMIN_PASSWORD"
    assert response.masked_value == "********"
    assert approve_calls["upsert"] == 1
    assert approve_calls["delete"] == 1
