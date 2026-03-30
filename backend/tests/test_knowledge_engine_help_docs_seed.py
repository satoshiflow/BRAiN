from __future__ import annotations

from uuid import uuid4

import pytest

from app.modules.knowledge_engine import help_docs_seed


@pytest.mark.asyncio
async def test_seed_help_documents_creates_missing_entries(monkeypatch: pytest.MonkeyPatch) -> None:
    entries = [
        {
            "help_key": "test.topic",
            "surface": "axe-ui",
            "title": "Test Topic",
            "content": "Test content",
            "tags": ["help", "test"],
        }
    ]
    monkeypatch.setattr(help_docs_seed, "HELP_DOC_SEED_ENTRIES", entries)

    calls = {"create": 0, "update": 0}

    class FakeService:
        async def get_help_doc(self, db, principal, help_key, surface=None):  # noqa: ANN001
            _ = (db, principal, help_key, surface)
            return None

        async def create_knowledge_item(self, db, principal, payload):  # noqa: ANN001
            _ = (db, principal, payload)
            calls["create"] += 1
            return {"id": uuid4()}

        async def update_knowledge_item(self, db, principal, item_id, payload):  # noqa: ANN001
            _ = (db, principal, item_id, payload)
            calls["update"] += 1
            return {"id": item_id}

    monkeypatch.setattr(help_docs_seed, "get_knowledge_engine_service", lambda: FakeService())

    await help_docs_seed.seed_help_documents(db=object())

    assert calls["create"] == 1
    assert calls["update"] == 0


@pytest.mark.asyncio
async def test_seed_help_documents_updates_existing_entries(monkeypatch: pytest.MonkeyPatch) -> None:
    entries = [
        {
            "help_key": "test.topic",
            "surface": "controldeck-v3",
            "title": "Updated Topic",
            "content": "Updated content",
            "tags": ["help", "updated"],
        }
    ]
    monkeypatch.setattr(help_docs_seed, "HELP_DOC_SEED_ENTRIES", entries)

    existing_id = uuid4()
    calls = {"create": 0, "update": 0}

    class FakeService:
        async def get_help_doc(self, db, principal, help_key, surface=None):  # noqa: ANN001
            _ = (db, principal, help_key, surface)
            return {
                "id": existing_id,
                "metadata": {"custom": "keep", "help_key": "old"},
                "visibility": "tenant",
            }

        async def create_knowledge_item(self, db, principal, payload):  # noqa: ANN001
            _ = (db, principal, payload)
            calls["create"] += 1
            return {"id": uuid4()}

        async def update_knowledge_item(self, db, principal, item_id, payload):  # noqa: ANN001
            _ = (db, principal, payload)
            calls["update"] += 1
            assert item_id == existing_id
            assert payload.metadata is not None
            assert payload.metadata["custom"] == "keep"
            assert payload.metadata["help_key"] == "test.topic"
            assert payload.metadata["surface"] == "controldeck-v3"
            return {"id": item_id}

    monkeypatch.setattr(help_docs_seed, "get_knowledge_engine_service", lambda: FakeService())

    await help_docs_seed.seed_help_documents(db=object())

    assert calls["create"] == 0
    assert calls["update"] == 1
