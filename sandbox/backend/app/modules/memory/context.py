"""
Context Manager - Session and cross-session context management.

Manages:
    - Active session working memory (conversation turns)
    - Token budget tracking and auto-compression triggers
    - Cross-session context persistence (episodic memory)
    - Context variable accumulation within sessions
"""

from __future__ import annotations

from datetime import datetime
from typing import Any, Dict, List, Optional

from loguru import logger

from .schemas import (
    ConversationTurn,
    MemoryEntry,
    MemoryLayer,
    MemoryType,
    SessionContext,
)
from .store import MemoryStore


# Rough token estimation: 1 token ≈ 4 chars
CHARS_PER_TOKEN = 4


def _estimate_tokens(text: str) -> int:
    return max(1, len(text) // CHARS_PER_TOKEN)


class ContextManager:
    """
    Manages working memory (sessions) and cross-session persistence.

    Each agent can have one active session. When a session ends,
    its important memories are promoted to episodic storage.
    """

    def __init__(self, store: MemoryStore) -> None:
        self.store = store
        # Track which agent has which active session
        self._agent_sessions: Dict[str, str] = {}  # agent_id → session_id
        logger.info("🧠 ContextManager initialized")

    # ------------------------------------------------------------------
    # Session lifecycle
    # ------------------------------------------------------------------

    async def start_session(
        self,
        agent_id: str,
        max_tokens: int = 8000,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> SessionContext:
        """
        Start a new session for an agent.

        If the agent already has an active session, it is ended first
        (important context promoted to episodic memory).
        """
        # End existing session if any
        existing_sid = self._agent_sessions.get(agent_id)
        if existing_sid:
            await self.end_session(existing_sid)

        session = SessionContext(
            agent_id=agent_id,
            max_tokens=max_tokens,
        )
        if metadata:
            session.context_vars.update(metadata)

        await self.store.create_session(session)
        self._agent_sessions[agent_id] = session.session_id

        logger.info("▶️ Session started: %s (agent=%s)", session.session_id, agent_id)
        return session

    async def end_session(self, session_id: str) -> Optional[Dict]:
        """
        End a session and promote important context to episodic memory.

        Returns summary of what was promoted.
        """
        session = await self.store.get_session(session_id)
        if not session:
            return None

        promoted = 0

        # Promote conversation summary to episodic
        if session.turns:
            summary = self._build_session_summary(session)
            entry = MemoryEntry(
                layer=MemoryLayer.EPISODIC,
                memory_type=MemoryType.CONVERSATION,
                content=summary,
                agent_id=session.agent_id,
                session_id=session.session_id,
                mission_id=session.active_mission_id,
                importance=60.0,
                tags=["session_summary"],
                metadata={
                    "turn_count": len(session.turns),
                    "total_tokens": session.total_tokens,
                },
            )
            await self.store.store(entry)
            promoted += 1

        # Promote context variables that look important
        if session.context_vars:
            entry = MemoryEntry(
                layer=MemoryLayer.EPISODIC,
                memory_type=MemoryType.OBSERVATION,
                content=str(session.context_vars),
                agent_id=session.agent_id,
                session_id=session.session_id,
                importance=40.0,
                tags=["session_context_vars"],
            )
            await self.store.store(entry)
            promoted += 1

        # Clean up
        self._agent_sessions.pop(session.agent_id, None)
        await self.store.delete_session(session_id)

        logger.info("⏹️ Session ended: %s (promoted %d memories)", session_id, promoted)
        return {"session_id": session_id, "promoted": promoted}

    # ------------------------------------------------------------------
    # Conversation turns
    # ------------------------------------------------------------------

    async def add_turn(
        self,
        session_id: str,
        role: str,
        content: str,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> Optional[ConversationTurn]:
        """
        Add a conversation turn to the session.

        If total tokens exceed the budget, triggers compression
        of oldest turns.

        Returns the created turn, or None if session not found.
        """
        session = await self.store.get_session(session_id)
        if not session:
            return None

        token_count = _estimate_tokens(content)
        turn = ConversationTurn(
            role=role,
            content=content,
            token_count=token_count,
            metadata=metadata or {},
        )

        session.turns.append(turn)
        session.total_tokens += token_count
        session.last_activity_at = datetime.utcnow()

        # Check token budget
        if session.total_tokens > session.max_tokens * 0.85:
            await self._compress_oldest_turns(session)

        return turn

    async def get_context_window(self, session_id: str) -> Optional[Dict]:
        """
        Get the current context window for an agent session.

        Returns the compressed summary (if any) plus recent turns,
        suitable for passing to an LLM.
        """
        session = await self.store.get_session(session_id)
        if not session:
            return None

        context_parts = []

        if session.compressed_summary:
            context_parts.append({
                "role": "system",
                "content": f"[Previous context summary]\n{session.compressed_summary}",
            })

        for turn in session.turns:
            context_parts.append({
                "role": turn.role,
                "content": turn.content,
            })

        return {
            "session_id": session.session_id,
            "agent_id": session.agent_id,
            "messages": context_parts,
            "total_tokens": session.total_tokens,
            "max_tokens": session.max_tokens,
            "compressed_turns": session.compressed_turn_count,
            "active_turns": len(session.turns),
        }

    # ------------------------------------------------------------------
    # Context variables
    # ------------------------------------------------------------------

    async def set_context_var(self, session_id: str, key: str, value: Any) -> bool:
        session = await self.store.get_session(session_id)
        if not session:
            return False
        session.context_vars[key] = value
        return True

    async def get_context_var(self, session_id: str, key: str) -> Optional[Any]:
        session = await self.store.get_session(session_id)
        if not session:
            return None
        return session.context_vars.get(key)

    # ------------------------------------------------------------------
    # Cross-session recall
    # ------------------------------------------------------------------

    async def get_agent_history(
        self,
        agent_id: str,
        limit: int = 20,
        min_importance: float = 30.0,
    ) -> List[MemoryEntry]:
        """
        Get an agent's cross-session history from episodic memory.

        Useful for providing historical context to an agent at session start.
        """
        return await self.store.query(
            agent_id=agent_id,
            layer=MemoryLayer.EPISODIC,
            min_importance=min_importance,
            limit=limit,
        )

    async def get_mission_context(self, mission_id: str) -> List[MemoryEntry]:
        """Get all memories associated with a mission."""
        return await self.store.query(mission_id=mission_id, limit=100)

    # ------------------------------------------------------------------
    # Compression
    # ------------------------------------------------------------------

    async def _compress_oldest_turns(self, session: SessionContext) -> None:
        """
        Compress oldest turns into a summary to free token budget.

        Compresses the first half of turns into a text summary.
        """
        if len(session.turns) < 4:
            return  # Not enough turns to compress

        # Take first half for compression
        split = len(session.turns) // 2
        old_turns = session.turns[:split]
        remaining = session.turns[split:]

        # Build summary from old turns
        summary_parts = []
        compressed_tokens = 0
        for turn in old_turns:
            # Truncate each turn to key info
            snippet = turn.content[:200]
            summary_parts.append(f"[{turn.role}]: {snippet}")
            compressed_tokens += turn.token_count

        new_summary = "\n".join(summary_parts)

        # Merge with existing compressed summary
        if session.compressed_summary:
            new_summary = f"{session.compressed_summary}\n---\n{new_summary}"

        session.compressed_summary = new_summary
        session.compressed_turn_count += len(old_turns)
        session.turns = remaining
        session.total_tokens -= compressed_tokens
        # Add summary token estimate
        session.total_tokens += _estimate_tokens(new_summary)

        logger.info(
            "🗜️ Compressed %d turns in session %s (freed ~%d tokens)",
            len(old_turns), session.session_id, compressed_tokens,
        )

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _build_session_summary(session: SessionContext) -> str:
        """Build a text summary of a session for episodic storage."""
        parts = [f"Session {session.session_id} (agent: {session.agent_id})"]

        if session.compressed_summary:
            parts.append(f"[Compressed history]: {session.compressed_summary[:500]}")

        for turn in session.turns[-5:]:  # Last 5 turns
            snippet = turn.content[:150]
            parts.append(f"[{turn.role}]: {snippet}")

        return "\n".join(parts)
