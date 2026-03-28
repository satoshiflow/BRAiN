"""
AXE Memory Bridge Service

Verbindet AXE Chat mit dem MemoryService und Qdrant für Konversationsgedächtnis.
"""

from __future__ import annotations

import json
import os
from typing import Any, Dict, List, Optional
from datetime import datetime
from loguru import logger
import redis.asyncio as redis
from sqlalchemy.ext.asyncio import AsyncSession

try:
    from qdrant_client import QdrantClient
    from qdrant_client.models import Distance, VectorParams, PointStruct
    QDRANT_AVAILABLE = True
except ImportError:
    QDRANT_AVAILABLE = False
    logger.warning("Qdrant client not available, falling back to memory-only")

from app.modules.memory.service import get_memory_service
from app.modules.memory.schemas import MemoryStoreRequest, MemoryLayer, MemoryType


# Qdrant Collection Names
CONVERSATIONS_COLLECTION = "axe_conversations"
PREFERENCES_COLLECTION = "axe_preferences"

# Redis Keys
REDIS_SESSION_PREFIX = "brain:axe:session"
REDIS_SESSION_TTL = 3600 * 24 * 7  # 7 days


class AXEMemoryBridge:
    """
    Memory Bridge für AXE Chat - verbindet Chat mit MemoryService und Qdrant.
    """

    def __init__(self, db: Optional[AsyncSession] = None):
        self.db = db
        self._redis: Optional[redis.Redis] = None
        self._qdrant_client: Optional[QdrantClient] = None
        self._memory_service = None

    async def _get_redis(self) -> redis.Redis:
        if self._redis is None:
            redis_url = os.getenv("REDIS_URL", "redis://localhost:6379/0")
            self._redis = redis.from_url(redis_url, decode_responses=True)
        return self._redis

    async def _get_memory_service(self):
        if self._memory_service is None:
            self._memory_service = get_memory_service()
        return self._memory_service

    async def _get_qdrant_client(self) -> Optional[QdrantClient]:
        if not QDRANT_AVAILABLE:
            return None
        if self._qdrant_client is None:
            qdrant_url = os.getenv("QDRANT_URL", "http://localhost:6334")
            try:
                self._qdrant_client = QdrantClient(url=qdrant_url)
                # Ensure collections exist
                await self._ensure_qdrant_collections()
            except Exception as e:
                logger.warning(f"Qdrant connection failed: {e}, falling back to memory-only")
                self._qdrant_client = None
        return self._qdrant_client

    async def _ensure_qdrant_collections(self):
        """Ensure Qdrant collections exist."""
        if not self._qdrant_client:
            return
        
        try:
            # Create conversations collection if not exists
            collections = self._qdrant_client.get_collections().collections
            collection_names = [c.name for c in collections]
            
            if CONVERSATIONS_COLLECTION not in collection_names:
                self._qdrant_client.create_collection(
                    collection_name=CONVERSATIONS_COLLECTION,
                    vectors_config=VectorParams(
                        size=1536,  # text-embedding-3-small
                        distance=Distance.COSINE
                    )
                )
                logger.info(f"Created Qdrant collection: {CONVERSATIONS_COLLECTION}")
            
            if PREFERENCES_COLLECTION not in collection_names:
                self._qdrant_client.create_collection(
                    collection_name=PREFERENCES_COLLECTION,
                    vectors_config=VectorParams(
                        size=1536,
                        distance=Distance.COSINE
                    )
                )
                logger.info(f"Created Qdrant collection: {PREFERENCES_COLLECTION}")
        except Exception as e:
            logger.warning(f"Failed to ensure Qdrant collections: {e}")

    # =========================================================================
    # Core Methods
    # =========================================================================

    async def store_message(
        self,
        session_id: str,
        role: str,
        content: str,
        metadata: Dict[str, Any] = None,
        tenant_id: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Speichert eine Chat-Nachricht im Memory und Qdrant.
        
        Args:
            session_id: Session-ID
            role: "user" oder "assistant"
            content: Nachrichteninhalt
            metadata: Optionale Metadaten
            tenant_id: Tenant-ID
            
        Returns:
            Dict mit gespeicherten Daten
        """
        timestamp = datetime.utcnow()
        
        # 1. Store in Redis (fast access)
        redis = await self._get_redis()
        redis_key = f"{REDIS_SESSION_PREFIX}:{session_id}:messages"
        
        message_data = {
            "role": role,
            "content": content,
            "timestamp": timestamp.isoformat(),
            "metadata": metadata or {}
        }
        
        await redis.rpush(redis_key, json.dumps(message_data))
        await redis.expire(redis_key, REDIS_SESSION_TTL)
        
        # 2. Store in MemoryService (long-term)
        memory_service = await self._get_memory_service()
        if memory_service:
            try:
                memory_request = MemoryStoreRequest(
                    content=f"[{role.upper()}] {content}",
                    tenant_id=tenant_id,
                    memory_type=MemoryType.CONVERSATION,
                    layer=MemoryLayer.EPISODIC,
                    session_id=session_id,
                    importance=50.0,
                    tags=[role, "axe_chat"],
                    metadata={
                        "role": role,
                        "session_id": session_id,
                        **(metadata or {})
                    }
                )
                memory_entry = await memory_service.store_memory(memory_request)
                logger.debug(f"Stored message in MemoryService: {memory_entry.memory_id}")
            except Exception as e:
                logger.warning(f"Failed to store in MemoryService: {e}")
        
        # 3. Store in Qdrant (semantic search)
        qdrant = await self._get_qdrant_client()
        if qdrant and role == "user":
            try:
                # For now, use content as-is for embedding
                # In production, would call embedding API
                embedding = await self._get_embedding(content)
                if embedding:
                    point = PointStruct(
                        id=f"{session_id}:{timestamp.timestamp()}",
                        vector=embedding,
                        payload={
                            "session_id": session_id,
                            "role": role,
                            "content": content,
                            "timestamp": timestamp.isoformat()
                        }
                    )
                    qdrant.upsert(
                        collection_name=CONVERSATIONS_COLLECTION,
                        points=[point]
                    )
            except Exception as e:
                logger.warning(f"Failed to store in Qdrant: {e}")
        
        # 4. Check for preferences in user messages
        if role == "user" and tenant_id:
            preferences = await self._extract_preferences_from_message(content)
            if preferences:
                await self._store_preferences(session_id, preferences, tenant_id)
        
        return {
            "session_id": session_id,
            "role": role,
            "content": content,
            "timestamp": timestamp.isoformat()
        }

    async def get_session_context(
        self,
        session_id: str,
        max_turns: int = 10
    ) -> List[Dict[str, Any]]:
        """
        Lädt den Session-Context aus Redis (schnellster Zugriff).
        
        Args:
            session_id: Session-ID
            max_turns: Maximale Anzahl Nachrichten
            
        Returns:
            Liste von Nachrichten
        """
        redis = await self._get_redis()
        redis_key = f"{REDIS_SESSION_PREFIX}:{session_id}:messages"
        
        messages = await redis.lrange(redis_key, -max_turns * 2, -1)
        
        result = []
        for msg in messages:
            try:
                result.append(json.loads(msg))
            except json.JSONDecodeError:
                continue
        
        return result[-max_turns:]

    async def get_session_context_full(
        self,
        session_id: str,
        max_turns: int = 20
    ) -> List[Dict[str, Any]]:
        """
        Lädt den vollständigen Session-Context aus MemoryService.
        
        Args:
            session_id: Session-ID
            max_turns: Maximale Anzahl
            
        Returns:
            Liste von MemoryEntries
        """
        memory_service = await self._get_memory_service()
        if not memory_service:
            return await self.get_session_context(session_id, max_turns)
        
        try:
            recall_result = await memory_service.recall.from_session(
                session_id=session_id,
                limit=max_turns
            )
            return [
                {
                    "role": m.metadata.get("role", "unknown"),
                    "content": m.content,
                    "timestamp": m.created_at.isoformat() if m.created_at else None
                }
                for m in recall_result.memories
            ]
        except Exception as e:
            logger.warning(f"Failed to get context from MemoryService: {e}")
            return await self.get_session_context(session_id, max_turns)

    async def _extract_preferences_from_message(self, content: str) -> Optional[Dict[str, Any]]:
        """
        Extrahiert Präferenzen aus einer Nachricht (LLM-basiert).
        
        Args:
            content: Nachrichteninhalt
            
        Returns:
            Dict mit extrahierten Präferenzen oder None
        """
        # Use LLM to extract preferences
        prompt = f"""
Extract any user preferences or identity information from this message.
Look for:
- Name preferences: "call me X", "my name is X", "I'm X"
- Tone preferences: "be formal", "be casual", "short answers"
- Topic interests: "I like X", "interested in X"
- Communication style: "use emojis", "no jargon"

Message: {content}

Return a JSON with keys: name, tone_topics. Set to null if not mentioned.
Example: {{"name": "AXE", "tone": "casual", "topics": ["tech", "coding"]}}
"""
        try:
            from app.modules.axe_fusion.service import AXEFusionService
            from sqlalchemy.ext.asyncio import AsyncSession
            
            # Create a minimal session for extraction
            # This is a lightweight call - no need for full session context
            extraction_result = await self._llm_extract_preferences(prompt)
            return extraction_result
        except Exception as e:
            logger.debug(f"Preference extraction failed: {e}")
            return None

    async def _llm_extract_preferences(self, prompt: str) -> Optional[Dict[str, Any]]:
        """
        LLM-basierte Präferenz-Extraktion.
        """
        try:
            # Use the configured LLM client
            from app.modules.axe_fusion.service import AXEFusionService
            from app.modules.axe_fusion.client import AXEllmClient
            
            client = AXEllmClient()
            response = await client.chat(
                model="gpt-4o-mini",
                messages=[{"role": "user", "content": prompt}],
                temperature=0.3
            )
            
            # Parse JSON from response
            content = response.get("content", "")
            # Extract JSON from response
            import re
            json_match = re.search(r'\{[^}]+\}', content)
            if json_match:
                return json.loads(json_match.group())
        except Exception as e:
            logger.debug(f"LLM extraction failed: {e}")
        
        return None

    async def _store_preferences(
        self,
        session_id: str,
        preferences: Dict[str, Any],
        tenant_id: str
    ):
        """Speichert extrahierte Präferenzen."""
        redis = await self._get_redis()
        redis_key = f"{REDIS_SESSION_PREFIX}:{session_id}:preferences"
        
        await redis.set(
            redis_key,
            json.dumps(preferences),
            ex=REDIS_SESSION_TTL
        )
        
        # Also store in Qdrant for semantic search
        qdrant = await self._get_qdrant_client()
        if qdrant and preferences.get("name"):
            try:
                embedding = await self._get_embedding(preferences["name"])
                if embedding:
                    point = PointStruct(
                        id=f"{session_id}:preference:name",
                        vector=embedding,
                        payload={
                            "session_id": session_id,
                            "preference_type": "name",
                            "value": preferences["name"],
                            "confidence": 0.8
                        }
                    )
                    qdrant.upsert(
                        collection_name=PREFERENCES_COLLECTION,
                        points=[point]
                    )
            except Exception as e:
                logger.warning(f"Failed to store preference in Qdrant: {e}")

    async def get_preferences(self, session_id: str) -> Dict[str, Any]:
        """Lädt gespeicherte Präferenzen für eine Session."""
        redis = await self._get_redis()
        redis_key = f"{REDIS_SESSION_PREFIX}:{session_id}:preferences"
        
        prefs = await redis.get(redis_key)
        if prefs:
            return json.loads(prefs)
        return {}

    async def _get_embedding(self, text: str) -> Optional[List[float]]:
        """
        Generiert Embedding für Text (using OpenAI).
        
        In production, this would call the embedding API.
        For now, returns a mock vector for testing.
        """
        try:
            import httpx
            api_key = os.getenv("OPENAI_API_KEY")
            if not api_key:
                return None
            
            async with httpx.AsyncClient() as client:
                response = await client.post(
                    "https://api.openai.com/v1/embeddings",
                    headers={
                        "Authorization": f"Bearer {api_key}",
                        "Content-Type": "application/json"
                    },
                    json={
                        "model": "text-embedding-3-small",
                        "input": text
                    },
                    timeout=10.0
                )
                
                if response.status_code == 200:
                    data = response.json()
                    return data["data"][0]["embedding"]
        except Exception as e:
            logger.debug(f"Embedding generation failed: {e}")
        
        return None

    async def semantic_search(
        self,
        query: str,
        session_id: Optional[str] = None,
        limit: int = 5
    ) -> List[Dict[str, Any]]:
        """
        Semantische Suche in Konversationen.
        
        Args:
            query: Suchquery
            session_id: Optional nur diese Session
            limit: Anzahl Ergebnisse
            
        Returns:
            Liste von relevanten Nachrichten
        """
        qdrant = await self._get_qdrant_client()
        if not qdrant:
            return []
        
        try:
            query_embedding = await self._get_embedding(query)
            if not query_embedding:
                return []
            
            filter_conditions = {}
            if session_id:
                filter_conditions["session_id"] = session_id
            
            results = qdrant.search(
                collection_name=CONVERSATIONS_COLLECTION,
                query_vector=query_embedding,
                limit=limit,
                query_filter=filter_conditions if filter_conditions else None
            )
            
            return [
                {
                    "content": r.payload.get("content"),
                    "session_id": r.payload.get("session_id"),
                    "role": r.payload.get("role"),
                    "score": r.score
                }
                for r in results
            ]
        except Exception as e:
            logger.warning(f"Semantic search failed: {e}")
            return []

    async def close(self):
        """Cleanup resources."""
        if self._redis:
            await self._redis.close()
        if self._qdrant_client:
            self._qdrant_client.close()


# Singleton instance
_memory_bridge: Optional[AXEMemoryBridge] = None


def get_axe_memory_bridge(db: Optional[AsyncSession] = None) -> AXEMemoryBridge:
    """Get singleton AXE Memory Bridge."""
    global _memory_bridge
    if _memory_bridge is None:
        _memory_bridge = AXEMemoryBridge(db)
    return _memory_bridge