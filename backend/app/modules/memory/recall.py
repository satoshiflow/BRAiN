"""
Selective Recall - KARMA-scored memory retrieval.

Retrieval strategies:
    - Keyword:   Simple text match (fast, always available)
    - Importance: Filter by importance + KARMA score
    - Recency:   Bias toward recent memories
    - Hybrid:    Combine keyword, importance, and recency

KARMA integration:
    - Memories with higher KARMA scores rank higher
    - Frequent recalls boost importance (reinforcement)
    - Unused memories decay over time
"""

from __future__ import annotations

import time
from datetime import datetime, timedelta
from typing import List, Optional

from loguru import logger

from .schemas import (
    MemoryEntry,
    MemoryLayer,
    MemoryQuery,
    MemoryRecallResult,
    MemoryType,
)
from .store import MemoryStore


# Decay: importance drops 1 point per day of inactivity
IMPORTANCE_DECAY_PER_DAY = 1.0
# Reinforcement: each recall boosts importance by this much
RECALL_BOOST = 0.5
# Max importance (cap to prevent runaway)
MAX_IMPORTANCE = 100.0


class SelectiveRecall:
    """
    Retrieves memories using KARMA-weighted scoring.

    Combines relevance, importance, and recency to find
    the most useful memories for a given context.
    """

    def __init__(self, store: MemoryStore) -> None:
        self.store = store
        logger.info("🔍 SelectiveRecall initialized")

    async def recall(self, query: MemoryQuery) -> MemoryRecallResult:
        """
        Execute a memory recall using the best available strategy.

        Falls back from semantic → keyword → importance-based.
        """
        start = time.monotonic()

        # Get base candidates
        candidates = await self.store.query(
            agent_id=query.agent_id,
            session_id=query.session_id,
            mission_id=query.mission_id,
            layer=query.layer,
            memory_type=query.memory_type,
            tags=query.tags,
            min_importance=query.min_importance,
            min_karma=query.min_karma,
            include_compressed=query.include_compressed,
            limit=query.limit * 5,  # Over-fetch for re-ranking
        )

        # Apply keyword filter if query text provided
        strategy = "importance"
        if query.query:
            candidates = self._keyword_filter(candidates, query.query)
            strategy = "keyword"

        # Score and rank
        scored = self._score_memories(candidates)

        # Take top N
        scored.sort(key=lambda x: x[1], reverse=True)
        top = [m for m, _ in scored[:query.limit]]

        # Reinforce recalled memories (boost importance)
        for mem in top:
            await self._reinforce(mem)

        duration = (time.monotonic() - start) * 1000

        return MemoryRecallResult(
            memories=top,
            total_found=len(candidates),
            query_time_ms=duration,
            recall_strategy=strategy,
        )

    async def apply_decay(self, agent_id: Optional[str] = None) -> int:
        """
        Apply importance decay to old memories.

        Memories that haven't been accessed decay in importance.
        Called periodically (e.g., once per day).

        Returns count of memories that decayed.
        """
        now = datetime.utcnow()
        memories = await self.store.query(
            agent_id=agent_id,
            limit=1000,
        )

        decayed = 0
        for mem in memories:
            last_access = mem.last_accessed_at or mem.created_at
            days_idle = (now - last_access).total_seconds() / 86400

            if days_idle > 1:
                decay = IMPORTANCE_DECAY_PER_DAY * days_idle
                new_importance = max(0.0, mem.importance - decay)
                if new_importance != mem.importance:
                    mem.importance = new_importance
                    decayed += 1

        if decayed:
            logger.info("📉 Applied decay to %d memories", decayed)

        return decayed

    # ------------------------------------------------------------------
    # Scoring
    # ------------------------------------------------------------------

    def _score_memories(self, memories: List[MemoryEntry]) -> List[tuple]:
        """
        Score memories using a composite score.

        Score = (importance * 0.35) + (karma * 0.30) + (recency * 0.20) + (access * 0.15)
        """
        now = datetime.utcnow()
        scored = []

        for mem in memories:
            # Importance component (0-100)
            imp = mem.importance

            # KARMA component (0-100)
            karma = mem.karma_score

            # Recency component (0-100): decays over 30 days
            age_days = (now - mem.created_at).total_seconds() / 86400
            recency = max(0.0, 100.0 - (age_days * 100.0 / 30.0))

            # Access frequency component (0-100): log scale
            import math
            access = min(100.0, math.log2(mem.access_count + 1) * 20)

            # Composite score
            score = (imp * 0.35) + (karma * 0.30) + (recency * 0.20) + (access * 0.15)

            scored.append((mem, score))

        return scored

    # ------------------------------------------------------------------
    # Keyword filtering
    # ------------------------------------------------------------------

    @staticmethod
    def _keyword_filter(memories: List[MemoryEntry], query: str) -> List[MemoryEntry]:
        """Filter memories by keyword match in content/summary."""
        q = query.lower()
        tokens = q.split()

        results = []
        for mem in memories:
            text = f"{mem.content} {mem.summary or ''}".lower()
            # Match if any token appears
            if any(t in text for t in tokens):
                results.append(mem)

        return results

    # ------------------------------------------------------------------
    # Reinforcement
    # ------------------------------------------------------------------

    async def _reinforce(self, memory: MemoryEntry) -> None:
        """Boost importance of recalled memories (reinforcement learning)."""
        memory.access_count += 1
        memory.last_accessed_at = datetime.utcnow()
        memory.importance = min(MAX_IMPORTANCE, memory.importance + RECALL_BOOST)
