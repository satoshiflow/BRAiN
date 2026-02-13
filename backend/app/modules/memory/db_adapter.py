"""
Database Adapter - Async database operations for Memory module.

Provides async CRUD operations using SQLAlchemy with async PostgreSQL.
"""

from __future__ import annotations

import os
from contextlib import asynccontextmanager
from datetime import datetime
from typing import Any, Dict, List, Optional

from loguru import logger
from sqlalchemy import delete, select, update
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.orm import sessionmaker

from .models import Base, ConversationTurnORM, MemoryEntryORM, SessionContextORM
from .schemas import (
    CompressionStatus,
    ConversationTurn,
    MemoryEntry,
    MemoryLayer,
    MemoryType,
    SessionContext,
)


# Get database URL from environment or default
DATABASE_URL = os.getenv(
    "DATABASE_URL",
    "postgresql+asyncpg://brain:brain@localhost:5432/brain"
)


class DatabaseAdapter:
    """
    Async database adapter for memory operations.
    
    Provides CRUD operations for memory entries and session contexts.
    """
    
    def __init__(self, database_url: Optional[str] = None) -> None:
        self.database_url = database_url or DATABASE_URL
        self.engine = None
        self.async_session = None
        self._initialized = False
    
    async def initialize(self) -> None:
        """Initialize the database engine and session factory."""
        if self._initialized:
            return
            
        self.engine = create_async_engine(
            self.database_url,
            echo=False,
            pool_pre_ping=True,
            pool_size=10,
            max_overflow=20,
        )
        self.async_session = sessionmaker(
            self.engine, 
            class_=AsyncSession, 
            expire_on_commit=False
        )
        self._initialized = True
        logger.info("💾 DatabaseAdapter initialized")
    
    async def close(self) -> None:
        """Close the database engine."""
        if self.engine:
            await self.engine.dispose()
            self._initialized = False
            logger.info("💾 DatabaseAdapter closed")
    
    @asynccontextmanager
    async def session(self):
        """Get a database session context manager."""
        if not self._initialized:
            await self.initialize()
            
        async with self.async_session() as session:
            try:
                yield session
                await session.commit()
            except Exception:
                await session.rollback()
                raise
            finally:
                await session.close()
    
    # ------------------------------------------------------------------
    # Memory Entry Operations
    # ------------------------------------------------------------------
    
    async def store_memory(self, entry: MemoryEntry) -> MemoryEntry:
        """Store a memory entry in the database."""
        async with self.session() as session:
            # Check if entry already exists (update) or new (insert)
            result = await session.execute(
                select(MemoryEntryORM).where(MemoryEntryORM.memory_id == entry.memory_id)
            )
            existing = result.scalar_one_or_none()
            
            orm_data = {
                "memory_id": entry.memory_id,
                "layer": entry.layer.value,
                "memory_type": entry.memory_type.value,
                "content": entry.content,
                "summary": entry.summary,
                "agent_id": entry.agent_id,
                "session_id": entry.session_id,
                "mission_id": entry.mission_id,
                "tags": entry.tags,
                "importance": entry.importance,
                "karma_score": entry.karma_score,
                "access_count": entry.access_count,
                "last_accessed_at": entry.last_accessed_at,
                "compression": entry.compression.value,
                "created_at": entry.created_at,
                "expires_at": entry.expires_at,
                "embedding": entry.embedding,
                "metadata": entry.metadata,
            }
            
            if existing:
                # Update existing
                for key, value in orm_data.items():
                    setattr(existing, key, value)
            else:
                # Insert new
                orm_entry = MemoryEntryORM(**orm_data)
                session.add(orm_entry)
            
            return entry
    
    async def get_memory(self, memory_id: str) -> Optional[MemoryEntry]:
        """Retrieve a memory by ID and update access stats."""
        async with self.session() as session:
            result = await session.execute(
                select(MemoryEntryORM).where(MemoryEntryORM.memory_id == memory_id)
            )
            orm_entry = result.scalar_one_or_none()
            
            if orm_entry:
                # Update access stats
                orm_entry.access_count += 1
                orm_entry.last_accessed_at = datetime.utcnow()
                
                return self._orm_to_memory_entry(orm_entry)
            return None
    
    async def delete_memory(self, memory_id: str) -> bool:
        """Delete a memory entry."""
        async with self.session() as session:
            result = await session.execute(
                delete(MemoryEntryORM).where(MemoryEntryORM.memory_id == memory_id)
            )
            return result.rowcount > 0
    
    async def query_memories(
        self,
        agent_id: Optional[str] = None,
        session_id: Optional[str] = None,
        mission_id: Optional[str] = None,
        layer: Optional[MemoryLayer] = None,
        memory_type: Optional[MemoryType] = None,
        tags: Optional[List[str]] = None,
        min_importance: Optional[float] = None,
        min_karma: Optional[float] = None,
        include_compressed: bool = True,
        limit: int = 50,
    ) -> List[MemoryEntry]:
        """Query memories with filters."""
        async with self.session() as session:
            query = select(MemoryEntryORM)
            
            # Apply filters
            if agent_id:
                query = query.where(MemoryEntryORM.agent_id == agent_id)
            if session_id:
                query = query.where(MemoryEntryORM.session_id == session_id)
            if mission_id:
                query = query.where(MemoryEntryORM.mission_id == mission_id)
            if layer:
                query = query.where(MemoryEntryORM.layer == layer.value)
            if memory_type:
                query = query.where(MemoryEntryORM.memory_type == memory_type.value)
            if tags:
                # Use overlap operator for array overlap
                query = query.where(MemoryEntryORM.tags.overlap(tags))
            if min_importance is not None:
                query = query.where(MemoryEntryORM.importance >= min_importance)
            if min_karma is not None:
                query = query.where(MemoryEntryORM.karma_score >= min_karma)
            if not include_compressed:
                query = query.where(MemoryEntryORM.compression == CompressionStatus.RAW.value)
            
            # Sort by importance descending, then recency
            query = query.order_by(
                MemoryEntryORM.importance.desc(),
                MemoryEntryORM.created_at.desc()
            )
            query = query.limit(limit)
            
            result = await session.execute(query)
            orm_entries = result.scalars().all()
            
            return [self._orm_to_memory_entry(e) for e in orm_entries]
    
    async def keyword_search(
        self, 
        query: str, 
        limit: int = 10,
        **filters
    ) -> List[MemoryEntry]:
        """Simple keyword search across memory content."""
        async with self.session() as session:
            # Use ILIKE for case-insensitive search
            search_pattern = f"%{query.lower()}%"
            
            db_query = select(MemoryEntryORM).where(
                (MemoryEntryORM.content.ilike(search_pattern)) |
                (MemoryEntryORM.summary.ilike(search_pattern))
            )
            
            # Apply additional filters
            if filters.get("agent_id"):
                db_query = db_query.where(MemoryEntryORM.agent_id == filters["agent_id"])
            if filters.get("session_id"):
                db_query = db_query.where(MemoryEntryORM.session_id == filters["session_id"])
            if filters.get("mission_id"):
                db_query = db_query.where(MemoryEntryORM.mission_id == filters["mission_id"])
            if filters.get("layer"):
                db_query = db_query.where(MemoryEntryORM.layer == filters["layer"].value)
            
            db_query = db_query.limit(limit)
            
            result = await session.execute(db_query)
            orm_entries = result.scalars().all()
            
            return [self._orm_to_memory_entry(e) for e in orm_entries]
    
    async def get_memories_by_layer(self, layer: MemoryLayer) -> List[MemoryEntry]:
        """Get all memories for a specific layer."""
        return await self.query_memories(layer=layer, limit=10000)
    
    async def evict_expired(self) -> int:
        """Remove expired memories. Returns count of evicted entries."""
        async with self.session() as session:
            result = await session.execute(
                delete(MemoryEntryORM).where(
                    MemoryEntryORM.expires_at <= datetime.utcnow()
                )
            )
            return result.rowcount
    
    async def update_memory(self, memory_id: str, **updates) -> bool:
        """Update specific fields of a memory entry."""
        async with self.session() as session:
            result = await session.execute(
                update(MemoryEntryORM)
                .where(MemoryEntryORM.memory_id == memory_id)
                .values(**updates)
            )
            return result.rowcount > 0
    
    # ------------------------------------------------------------------
    # Session Context Operations
    # ------------------------------------------------------------------
    
    async def create_session(self, session: SessionContext) -> SessionContext:
        """Create a new session context."""
        async with self.session() as db_session:
            # Check if session exists
            result = await db_session.execute(
                select(SessionContextORM).where(SessionContextORM.session_id == session.session_id)
            )
            existing = result.scalar_one_or_none()
            
            orm_data = {
                "session_id": session.session_id,
                "agent_id": session.agent_id,
                "started_at": session.started_at,
                "last_activity_at": session.last_activity_at,
                "total_tokens": session.total_tokens,
                "max_tokens": session.max_tokens,
                "active_mission_id": session.active_mission_id,
                "context_vars": session.context_vars,
                "compressed_summary": session.compressed_summary,
                "compressed_turn_count": session.compressed_turn_count,
            }
            
            if existing:
                for key, value in orm_data.items():
                    setattr(existing, key, value)
            else:
                orm_session = SessionContextORM(**orm_data)
                db_session.add(orm_session)
            
            return session
    
    async def get_session(self, session_id: str) -> Optional[SessionContext]:
        """Get a session by ID with its turns."""
        async with self.session() as session:
            result = await session.execute(
                select(SessionContextORM).where(SessionContextORM.session_id == session_id)
            )
            orm_session = result.scalar_one_or_none()
            
            if orm_session:
                # Load turns
                turns_result = await session.execute(
                    select(ConversationTurnORM)
                    .where(ConversationTurnORM.session_id == session_id)
                    .order_by(ConversationTurnORM.timestamp)
                )
                orm_turns = turns_result.scalars().all()
                
                # Build SessionContext with turns
                session_ctx = self._orm_to_session_context(orm_session)
                session_ctx.turns = [self._orm_to_conversation_turn(t) for t in orm_turns]
                
                return session_ctx
            return None
    
    async def delete_session(self, session_id: str) -> bool:
        """Delete a session and all its turns."""
        async with self.session() as session:
            result = await session.execute(
                delete(SessionContextORM).where(SessionContextORM.session_id == session_id)
            )
            return result.rowcount > 0
    
    async def list_sessions(self, agent_id: Optional[str] = None) -> List[SessionContext]:
        """List all sessions, optionally filtered by agent."""
        async with self.session() as session:
            query = select(SessionContextORM)
            
            if agent_id:
                query = query.where(SessionContextORM.agent_id == agent_id)
            
            query = query.order_by(SessionContextORM.started_at.desc())
            
            result = await session.execute(query)
            orm_sessions = result.scalars().all()
            
            return [self._orm_to_session_context(s) for s in orm_sessions]
    
    async def add_turn(self, session_id: str, turn: ConversationTurn) -> ConversationTurn:
        """Add a conversation turn to a session."""
        async with self.session() as session:
            orm_turn = ConversationTurnORM(
                turn_id=turn.turn_id,
                session_id=session_id,
                role=turn.role,
                content=turn.content,
                timestamp=turn.timestamp,
                metadata=turn.metadata,
                token_count=turn.token_count,
            )
            session.add(orm_turn)
            
            # Update session last_activity_at
            await session.execute(
                update(SessionContextORM)
                .where(SessionContextORM.session_id == session_id)
                .values(last_activity_at=datetime.utcnow())
            )
            
            return turn
    
    async def update_session(self, session_id: str, **updates) -> bool:
        """Update specific fields of a session."""
        async with self.session() as session:
            result = await session.execute(
                update(SessionContextORM)
                .where(SessionContextORM.session_id == session_id)
                .values(**updates)
            )
            return result.rowcount > 0
    
    # ------------------------------------------------------------------
    # Stats Operations
    # ------------------------------------------------------------------
    
    async def get_stats(self) -> Dict[str, Any]:
        """Get memory system statistics."""
        async with self.session() as session:
            # Total memories
            result = await session.execute(select(MemoryEntryORM))
            total = len(result.scalars().all())
            
            # Count by layer
            result = await session.execute(
                select(MemoryEntryORM.layer, func.count(MemoryEntryORM.id))
                .group_by(MemoryEntryORM.layer)
            )
            layer_counts = {row[0]: row[1] for row in result.all()}
            
            # Active sessions
            result = await session.execute(select(SessionContextORM))
            active_sessions = len(result.scalars().all())
            
            # Avg importance and karma
            result = await session.execute(
                select(func.avg(MemoryEntryORM.importance), func.avg(MemoryEntryORM.karma_score))
            )
            avg_row = result.one_or_none()
            avg_importance = float(avg_row[0]) if avg_row and avg_row[0] else 0.0
            avg_karma = float(avg_row[1]) if avg_row and avg_row[1] else 0.0
            
            return {
                "total_memories": total,
                "working_memories": layer_counts.get("working", 0),
                "episodic_memories": layer_counts.get("episodic", 0),
                "semantic_memories": layer_counts.get("semantic", 0),
                "active_sessions": active_sessions,
                "avg_importance": avg_importance,
                "avg_karma": avg_karma,
            }
    
    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------
    
    @staticmethod
    def _orm_to_memory_entry(orm: MemoryEntryORM) -> MemoryEntry:
        """Convert ORM model to Pydantic MemoryEntry."""
        return MemoryEntry(
            memory_id=orm.memory_id,
            layer=MemoryLayer(orm.layer),
            memory_type=MemoryType(orm.memory_type),
            content=orm.content,
            summary=orm.summary,
            agent_id=orm.agent_id,
            session_id=orm.session_id,
            mission_id=orm.mission_id,
            tags=orm.tags or [],
            importance=orm.importance,
            karma_score=orm.karma_score,
            access_count=orm.access_count,
            last_accessed_at=orm.last_accessed_at,
            compression=CompressionStatus(orm.compression),
            created_at=orm.created_at,
            expires_at=orm.expires_at,
            embedding=orm.embedding,
            metadata=orm.metadata or {},
        )
    
    @staticmethod
    def _orm_to_session_context(orm: SessionContextORM) -> SessionContext:
        """Convert ORM model to Pydantic SessionContext."""
        return SessionContext(
            session_id=orm.session_id,
            agent_id=orm.agent_id,
            started_at=orm.started_at,
            last_activity_at=orm.last_activity_at,
            total_tokens=orm.total_tokens,
            max_tokens=orm.max_tokens,
            active_mission_id=orm.active_mission_id,
            context_vars=orm.context_vars or {},
            compressed_summary=orm.compressed_summary,
            compressed_turn_count=orm.compressed_turn_count,
            turns=[],  # Loaded separately
        )
    
    @staticmethod
    def _orm_to_conversation_turn(orm: ConversationTurnORM) -> ConversationTurn:
        """Convert ORM model to Pydantic ConversationTurn."""
        return ConversationTurn(
            turn_id=orm.turn_id,
            role=orm.role,
            content=orm.content,
            timestamp=orm.timestamp,
            metadata=orm.metadata or {},
            token_count=orm.token_count,
        )


# Singleton instance
_db_adapter: Optional[DatabaseAdapter] = None


async def get_db_adapter(database_url: Optional[str] = None) -> DatabaseAdapter:
    """Get or create the singleton database adapter."""
    global _db_adapter
    if _db_adapter is None:
        _db_adapter = DatabaseAdapter(database_url)
        await _db_adapter.initialize()
    return _db_adapter
