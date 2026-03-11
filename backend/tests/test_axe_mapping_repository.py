from __future__ import annotations

from app.modules.axe_fusion.mapping_repository import AXEMappingRepository


def test_mapping_entries_redacts_and_hashes_without_raw_values() -> None:
    repo = AXEMappingRepository()
    replacements = {
        "[EMAIL_1]": "user@example.com",
        "[SECRET_1]": "api-665752525625265296252526",
    }

    entries = repo.mapping_entries_from_replacements(replacements)

    assert len(entries) == 2
    assert all(entry.original_hash for entry in entries)
    assert all("@example.com" not in entry.preview_redacted for entry in entries)
    assert all("665752525" not in entry.preview_redacted for entry in entries)


def test_fingerprint_messages_is_deterministic() -> None:
    repo = AXEMappingRepository()
    messages = [{"role": "user", "content": "hello"}]
    assert repo.fingerprint_messages(messages) == repo.fingerprint_messages(messages)


def test_unknown_entity_type_is_sanitized() -> None:
    repo = AXEMappingRepository()
    entries = repo.mapping_entries_from_replacements({"[../../BAD_1]": "value"})

    assert len(entries) == 1
    assert entries[0].entity_type == "unknown"


def test_hash_key_registry_uses_specific_version(monkeypatch) -> None:  # noqa: ANN001
    monkeypatch.setenv("AXE_MAPPING_HASH_KEY", "fallback")
    monkeypatch.setenv("AXE_MAPPING_HASH_KEY_VERSION", "2")
    monkeypatch.setenv("AXE_MAPPING_HASH_KEYS", "1:key-one,2:key-two")
    repo = AXEMappingRepository()

    hash_v2 = repo.hash_value("abc", key_version=2)
    hash_v1 = repo.hash_value("abc", key_version=1)

    assert hash_v2 != hash_v1
