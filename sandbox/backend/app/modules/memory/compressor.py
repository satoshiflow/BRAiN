"""
Memory Compressor - Summarization and compression of memories.

Strategies:
    - Truncation: Simple truncation for low-importance memories
    - Extractive: Pick key sentences (keyword-based)
    - LLM Summary: Use LLM for high-importance memories (future)

Compression promotes raw memories to summarized/archived status
while preserving key information.
"""

from __future__ import annotations

import re
from datetime import datetime, timedelta
from typing import List, Optional

from loguru import logger

from .schemas import (
    CompressionResult,
    CompressionStatus,
    MemoryEntry,
    MemoryLayer,
    MemoryType,
)
from .store import MemoryStore


# Rough token estimation
CHARS_PER_TOKEN = 4


class MemoryCompressor:
    """
    Compresses memories to reduce storage and improve retrieval.

    Low-importance memories are truncated.
    Medium-importance memories get extractive summaries.
    High-importance memories are preserved (future: LLM summary).
    """

    def __init__(self, store: MemoryStore) -> None:
        self.store = store
        self._total_compressions = 0
        logger.info("🗜️ MemoryCompressor initialized")

    async def compress_old_memories(
        self,
        max_age_hours: float = 24.0,
        target_ratio: float = 0.3,
        agent_id: Optional[str] = None,
    ) -> CompressionResult:
        """
        Compress memories older than max_age_hours.

        Args:
            max_age_hours: Only compress memories older than this.
            target_ratio: Target size as fraction of original (0.3 = 30%).
            agent_id: If set, only compress this agent's memories.

        Returns:
            CompressionResult with stats.
        """
        cutoff = datetime.utcnow() - timedelta(hours=max_age_hours)

        candidates = await self.store.query(
            agent_id=agent_id,
            include_compressed=False,
            limit=500,
        )

        # Filter to old, uncompressed memories
        candidates = [
            m for m in candidates
            if m.created_at <= cutoff and m.compression == CompressionStatus.RAW
        ]

        if not candidates:
            return CompressionResult(
                compressed_count=0,
                original_tokens=0,
                compressed_tokens=0,
                compression_ratio=1.0,
                summaries_created=0,
            )

        original_tokens = 0
        compressed_tokens = 0
        summaries_created = 0

        for memory in candidates:
            orig_tokens = len(memory.content) // CHARS_PER_TOKEN
            original_tokens += orig_tokens

            summary = self._compress_entry(memory, target_ratio)
            memory.summary = summary
            memory.compression = CompressionStatus.SUMMARIZED

            comp_tokens = len(summary) // CHARS_PER_TOKEN
            compressed_tokens += comp_tokens
            summaries_created += 1

        self._total_compressions += summaries_created

        ratio = compressed_tokens / original_tokens if original_tokens > 0 else 1.0

        logger.info(
            "🗜️ Compressed %d memories (%.0f%% reduction)",
            summaries_created, (1 - ratio) * 100,
        )

        return CompressionResult(
            compressed_count=summaries_created,
            original_tokens=original_tokens,
            compressed_tokens=compressed_tokens,
            compression_ratio=ratio,
            summaries_created=summaries_created,
        )

    async def merge_related_memories(
        self,
        agent_id: str,
        memory_type: Optional[MemoryType] = None,
        max_group_size: int = 5,
    ) -> int:
        """
        Merge related episodic memories into semantic summaries.

        Groups memories by tags/mission, creates a merged summary,
        and stores it as a semantic memory.

        Returns count of semantic memories created.
        """
        memories = await self.store.query(
            agent_id=agent_id,
            layer=MemoryLayer.EPISODIC,
            memory_type=memory_type,
            limit=200,
        )

        if len(memories) < 2:
            return 0

        # Group by mission_id (if available) or by tags
        groups: dict[str, List[MemoryEntry]] = {}
        for mem in memories:
            key = mem.mission_id or "general"
            groups.setdefault(key, []).append(mem)

        created = 0
        for group_key, group_mems in groups.items():
            if len(group_mems) < 2:
                continue

            # Take up to max_group_size
            batch = group_mems[:max_group_size]
            merged_content = self._merge_entries(batch)

            # Average importance and karma
            avg_importance = sum(m.importance for m in batch) / len(batch)
            avg_karma = sum(m.karma_score for m in batch) / len(batch)

            # Collect all tags
            all_tags = set()
            for m in batch:
                all_tags.update(m.tags)

            semantic = MemoryEntry(
                layer=MemoryLayer.SEMANTIC,
                memory_type=MemoryType.LEARNED_FACT,
                content=merged_content,
                agent_id=agent_id,
                mission_id=group_key if group_key != "general" else None,
                importance=min(100.0, avg_importance + 10),  # Boost merged memories
                karma_score=avg_karma,
                compression=CompressionStatus.SUMMARIZED,
                tags=list(all_tags) + ["merged"],
                metadata={
                    "source_count": len(batch),
                    "source_ids": [m.memory_id for m in batch],
                },
            )
            await self.store.store(semantic)
            created += 1

        if created:
            logger.info(
                "🔗 Merged %d groups into semantic memories for agent %s",
                created, agent_id,
            )

        return created

    # ------------------------------------------------------------------
    # Compression strategies
    # ------------------------------------------------------------------

    def _compress_entry(self, memory: MemoryEntry, target_ratio: float) -> str:
        """
        Compress a single memory entry.

        Strategy based on importance:
            < 30: Aggressive truncation
            30-70: Extractive (key sentences)
            > 70: Light trimming (preserve most)
        """
        content = memory.content
        target_len = max(50, int(len(content) * target_ratio))

        if memory.importance < 30:
            return self._truncate(content, target_len)
        elif memory.importance < 70:
            return self._extractive(content, target_len)
        else:
            return self._light_trim(content, target_len)

    @staticmethod
    def _truncate(text: str, max_len: int) -> str:
        """Simple truncation with ellipsis."""
        if len(text) <= max_len:
            return text
        return text[:max_len - 3].rstrip() + "..."

    @staticmethod
    def _extractive(text: str, max_len: int) -> str:
        """
        Extract key sentences.

        Picks sentences with important keywords (error, success, result,
        decision, mission, agent, etc.)
        """
        keywords = {
            "error", "success", "fail", "result", "decision", "mission",
            "agent", "important", "critical", "completed", "started",
        }

        sentences = re.split(r'(?<=[.!?])\s+', text)
        if not sentences:
            return text[:max_len]

        # Score sentences
        scored = []
        for i, sent in enumerate(sentences):
            words = set(sent.lower().split())
            score = len(words & keywords)
            # Boost first and last sentences
            if i == 0 or i == len(sentences) - 1:
                score += 2
            scored.append((score, i, sent))

        # Sort by score descending, take top sentences
        scored.sort(key=lambda x: x[0], reverse=True)

        selected = []
        current_len = 0
        for score, idx, sent in scored:
            if current_len + len(sent) > max_len:
                break
            selected.append((idx, sent))
            current_len += len(sent)

        # Re-order by original position
        selected.sort(key=lambda x: x[0])
        return " ".join(s for _, s in selected)

    @staticmethod
    def _light_trim(text: str, max_len: int) -> str:
        """Light trimming - remove whitespace, keep structure."""
        # Collapse multiple whitespace
        trimmed = re.sub(r'\s+', ' ', text).strip()
        if len(trimmed) <= max_len:
            return trimmed
        return trimmed[:max_len - 3].rstrip() + "..."

    @staticmethod
    def _merge_entries(entries: List[MemoryEntry]) -> str:
        """Merge multiple memory entries into a single summary."""
        parts = []
        for entry in entries:
            content = entry.summary or entry.content
            # Take first 200 chars of each
            snippet = content[:200].rstrip()
            if len(content) > 200:
                snippet += "..."
            parts.append(f"- {snippet}")

        return f"Merged from {len(entries)} memories:\n" + "\n".join(parts)
