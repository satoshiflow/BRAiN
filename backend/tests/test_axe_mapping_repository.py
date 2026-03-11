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
