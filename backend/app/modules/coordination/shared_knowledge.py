"""
Shared Knowledge Base - Cross-agent knowledge sharing.

Agents contribute knowledge entries with confidence scores.
Other agents can query, subscribe to updates, and build on
shared understanding.

KARMA integration:
    - High-confidence entries boost contributor's KARMA
    - Frequently accessed entries increase in importance
    - Stale entries decay over time
"""

from __future__ import annotations

import fnmatch
import time
from datetime import datetime
from typing import Any, Dict, List, Optional

from loguru import logger

from .schemas import KnowledgeEntry, KnowledgeQuery


class SharedKnowledgeBase:
    """
    In-memory shared knowledge base for cross-agent collaboration.

    Agents contribute facts, observations, and learned patterns.
    Other agents query the knowledge base for context.
    """

    def __init__(self) -> None:
        self._entries: Dict[str, KnowledgeEntry] = {}
        # Index: key → entry_id
        self._key_index: Dict[str, str] = {}
        # Index: tag → set of entry_ids
        self._tag_index: Dict[str, set] = {}
        # Index: contributor → set of entry_ids
        self._contributor_index: Dict[str, set] = {}

        # Metrics
        self._total_contributed = 0
        self._total_queries = 0

        logger.info("📚 SharedKnowledgeBase initialized")

    # ------------------------------------------------------------------
    # Write operations
    # ------------------------------------------------------------------

    def contribute(self, entry: KnowledgeEntry) -> KnowledgeEntry:
        """
        Add or update a knowledge entry.

        If key already exists, update value and bump confidence
        if the new confidence is higher.
        """
        existing_id = self._key_index.get(entry.key)

        if existing_id and existing_id in self._entries:
            existing = self._entries[existing_id]
            existing.value = entry.value
            existing.confidence = max(existing.confidence, entry.confidence)
            existing.updated_at = datetime.utcnow()
            if entry.tags:
                for tag in entry.tags:
                    if tag not in existing.tags:
                        existing.tags.append(tag)
                        self._tag_index.setdefault(tag, set()).add(existing_id)
            logger.debug("Updated knowledge '%s' by %s", entry.key, entry.contributed_by)
            return existing

        # New entry
        self._entries[entry.entry_id] = entry
        self._key_index[entry.key] = entry.entry_id

        for tag in entry.tags:
            self._tag_index.setdefault(tag, set()).add(entry.entry_id)

        self._contributor_index.setdefault(entry.contributed_by, set()).add(entry.entry_id)
        self._total_contributed += 1

        logger.info("📚 Knowledge contributed: '%s' by %s (conf=%.2f)", entry.key, entry.contributed_by, entry.confidence)
        return entry

    def remove(self, entry_id: str) -> bool:
        """Remove a knowledge entry."""
        entry = self._entries.pop(entry_id, None)
        if not entry:
            return False

        self._key_index.pop(entry.key, None)
        for tag in entry.tags:
            if tag in self._tag_index:
                self._tag_index[tag].discard(entry_id)
        if entry.contributed_by in self._contributor_index:
            self._contributor_index[entry.contributed_by].discard(entry_id)
        return True

    # ------------------------------------------------------------------
    # Read operations
    # ------------------------------------------------------------------

    def get_by_key(self, key: str) -> Optional[KnowledgeEntry]:
        """Get a knowledge entry by exact key."""
        entry_id = self._key_index.get(key)
        if entry_id and entry_id in self._entries:
            entry = self._entries[entry_id]
            entry.access_count += 1
            return entry
        return None

    def query(self, q: KnowledgeQuery) -> List[KnowledgeEntry]:
        """Query the knowledge base with filters."""
        self._total_queries += 1
        candidates: Optional[set] = None

        # Filter by contributor
        if q.contributed_by:
            ids = self._contributor_index.get(q.contributed_by, set())
            candidates = set(ids)

        # Filter by tags (intersection)
        if q.tags:
            for tag in q.tags:
                tag_ids = self._tag_index.get(tag, set())
                if candidates is None:
                    candidates = set(tag_ids)
                else:
                    candidates &= tag_ids

        # Start from all if no filters narrowed it
        if candidates is None:
            candidates = set(self._entries.keys())

        results = []
        for eid in candidates:
            entry = self._entries.get(eid)
            if not entry:
                continue

            # Key pattern (glob)
            if q.key_pattern and not fnmatch.fnmatch(entry.key, q.key_pattern):
                continue

            # Min confidence
            if q.min_confidence is not None and entry.confidence < q.min_confidence:
                continue

            results.append(entry)

        # Sort by confidence descending
        results.sort(key=lambda e: e.confidence, reverse=True)
        return results[: q.limit]

    def list_keys(self, pattern: Optional[str] = None) -> List[str]:
        """List all knowledge keys, optionally filtered by glob pattern."""
        keys = list(self._key_index.keys())
        if pattern:
            keys = [k for k in keys if fnmatch.fnmatch(k, pattern)]
        return sorted(keys)

    # ------------------------------------------------------------------
    # Stats
    # ------------------------------------------------------------------

    @property
    def stats(self) -> Dict:
        return {
            "total_entries": len(self._entries),
            "total_contributed": self._total_contributed,
            "total_queries": self._total_queries,
            "unique_contributors": len(self._contributor_index),
            "unique_tags": len(self._tag_index),
        }
