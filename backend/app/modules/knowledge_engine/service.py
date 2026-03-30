from __future__ import annotations

import json
import math
import os
from datetime import datetime, timezone
from typing import Any
from uuid import UUID

from loguru import logger
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.auth_deps import Principal

from .ingest_service import chunk_content, extract_text_from_input, generate_embeddings
from .schemas import KnowledgeIngestRequest, KnowledgeItemCreate, KnowledgeItemUpdate

try:
    from qdrant_client import QdrantClient
    from qdrant_client.models import Distance, PointStruct, VectorParams

    QDRANT_AVAILABLE = True
except ImportError:
    QDRANT_AVAILABLE = False


QDRANT_COLLECTION = "brain_knowledge_chunks"
QDRANT_VECTOR_SIZE = 256


class KnowledgeEngineService:
    def __init__(self) -> None:
        self._qdrant_client: QdrantClient | None = None

    async def _get_qdrant_client(self) -> QdrantClient | None:
        if not QDRANT_AVAILABLE:
            return None

        if self._qdrant_client is None:
            qdrant_url = os.getenv("QDRANT_URL", "http://localhost:6333")
            try:
                self._qdrant_client = QdrantClient(url=qdrant_url)
                await self._ensure_qdrant_collection()
                logger.info("KnowledgeEngine connected to Qdrant at {}", qdrant_url)
            except Exception as exc:
                logger.warning("KnowledgeEngine Qdrant unavailable, using JSON fallback: {}", exc)
                self._qdrant_client = None

        return self._qdrant_client

    async def _ensure_qdrant_collection(self) -> None:
        if not self._qdrant_client:
            return

        collections = self._qdrant_client.get_collections().collections
        existing = {item.name for item in collections}
        if QDRANT_COLLECTION in existing:
            return

        self._qdrant_client.create_collection(
            collection_name=QDRANT_COLLECTION,
            vectors_config=VectorParams(size=QDRANT_VECTOR_SIZE, distance=Distance.COSINE),
        )

    async def create_knowledge_item(self, db: AsyncSession, principal: Principal, payload: KnowledgeItemCreate) -> dict[str, Any]:
        stmt = text(
            """
            INSERT INTO knowledge_items (tenant_id, title, content, type, tags, visibility, metadata)
            VALUES (:tenant_id, :title, :content, :type, CAST(:tags AS jsonb), :visibility, CAST(:metadata AS jsonb))
            RETURNING id, tenant_id, title, content, type, tags, visibility, metadata, created_at, updated_at
            """
        )
        result = await db.execute(
            stmt,
            {
                "tenant_id": principal.tenant_id,
                "title": payload.title,
                "content": payload.content,
                "type": payload.type,
                "tags": json.dumps(payload.tags),
                "visibility": payload.visibility,
                "metadata": json.dumps(payload.metadata),
            },
        )
        row = result.mappings().one()
        await db.execute(
            text(
                """
                INSERT INTO knowledge_scores (item_id, usage_count, relevance_score, last_used)
                VALUES (:item_id, 0, 0.0, NULL)
                ON CONFLICT (item_id) DO NOTHING
                """
            ),
            {"item_id": row["id"]},
        )
        await db.commit()
        return dict(row)

    async def update_knowledge_item(self, db: AsyncSession, principal: Principal, item_id: UUID, payload: KnowledgeItemUpdate) -> dict[str, Any] | None:
        current = await self.get_item(db, principal, item_id)
        if current is None:
            return None

        updated = {
            "title": payload.title if payload.title is not None else current["title"],
            "content": payload.content if payload.content is not None else current["content"],
            "type": payload.type if payload.type is not None else current["type"],
            "tags": payload.tags if payload.tags is not None else current["tags"],
            "visibility": payload.visibility if payload.visibility is not None else current["visibility"],
            "metadata": payload.metadata if payload.metadata is not None else current["metadata"],
        }

        await self.version_knowledge_item(
            db,
            principal,
            item_id,
            {
                "before": {
                    "title": current["title"],
                    "content": current["content"],
                    "type": current["type"],
                    "tags": current["tags"],
                    "visibility": current["visibility"],
                    "metadata": current["metadata"],
                },
                "after": updated,
            },
            commit=False,
        )

        result = await db.execute(
            text(
                """
                UPDATE knowledge_items
                SET title = :title,
                    content = :content,
                    type = :type,
                    tags = CAST(:tags AS jsonb),
                    visibility = :visibility,
                    metadata = CAST(:metadata AS jsonb),
                    updated_at = NOW()
                WHERE id = :item_id
                  AND (CAST(:tenant_id AS text) IS NULL OR tenant_id = :tenant_id)
                RETURNING id, tenant_id, title, content, type, tags, visibility, metadata, created_at, updated_at
                """
            ),
            {
                "item_id": str(item_id),
                "tenant_id": principal.tenant_id,
                "title": updated["title"],
                "content": updated["content"],
                "type": updated["type"],
                "tags": json.dumps(updated["tags"]),
                "visibility": updated["visibility"],
                "metadata": json.dumps(updated["metadata"]),
            },
        )
        row = result.mappings().one_or_none()
        await db.commit()
        return dict(row) if row else None

    async def get_item(self, db: AsyncSession, principal: Principal, item_id: UUID) -> dict[str, Any] | None:
        result = await db.execute(
            text(
                """
                SELECT id, tenant_id, title, content, type, tags, visibility, metadata, created_at, updated_at
                FROM knowledge_items
                WHERE id = :item_id
                  AND (CAST(:tenant_id AS text) IS NULL OR tenant_id = :tenant_id)
                """
            ),
            {"item_id": str(item_id), "tenant_id": principal.tenant_id},
        )
        row = result.mappings().one_or_none()
        return dict(row) if row else None

    async def _get_item_by_id(self, db: AsyncSession, tenant_id: str | None, item_id: str) -> dict[str, Any] | None:
        result = await db.execute(
            text(
                """
                SELECT id, tenant_id, title, content, type, tags, visibility, metadata, created_at, updated_at
                FROM knowledge_items
                WHERE id = CAST(:item_id AS uuid)
                  AND (CAST(:tenant_id AS text) IS NULL OR tenant_id = :tenant_id)
                """
            ),
            {"item_id": item_id, "tenant_id": tenant_id},
        )
        row = result.mappings().one_or_none()
        return dict(row) if row else None

    async def list_items(
        self,
        db: AsyncSession,
        principal: Principal,
        query: str | None = None,
        type_filter: str | None = None,
        tag: str | None = None,
        limit: int = 50,
    ) -> list[dict[str, Any]]:
        where = ["(CAST(:tenant_id AS text) IS NULL OR tenant_id = :tenant_id)"]
        params: dict[str, Any] = {"tenant_id": principal.tenant_id, "limit": limit}

        if query:
            where.append("(title ILIKE :q OR content ILIKE :q)")
            params["q"] = f"%{query}%"
        if type_filter:
            where.append("type = :type_filter")
            params["type_filter"] = type_filter
        if tag:
            where.append("tags @> CAST(:tag AS jsonb)")
            params["tag"] = json.dumps([tag])

        sql = f"""
            SELECT id, tenant_id, title, content, type, tags, visibility, metadata, created_at, updated_at
            FROM knowledge_items
            WHERE {' AND '.join(where)}
            ORDER BY updated_at DESC
            LIMIT :limit
        """
        result = await db.execute(text(sql), params)
        return [dict(row) for row in result.mappings().all()]

    async def link_knowledge_items(self, db: AsyncSession, principal: Principal, source_id: UUID, target_id: UUID, relation_type: str) -> dict[str, Any]:
        result = await db.execute(
            text(
                """
                INSERT INTO knowledge_links (source_id, target_id, relation_type)
                VALUES (:source_id, :target_id, :relation_type)
                RETURNING id, source_id, target_id, relation_type, created_at
                """
            ),
            {
                "source_id": str(source_id),
                "target_id": str(target_id),
                "relation_type": relation_type,
            },
        )
        row = result.mappings().one()
        await db.commit()
        return dict(row)

    async def get_related_items(self, db: AsyncSession, principal: Principal, item_id: UUID) -> list[dict[str, Any]]:
        result = await db.execute(
            text(
                """
                SELECT DISTINCT ki.id, ki.tenant_id, ki.title, ki.content, ki.type, ki.tags, ki.visibility, ki.metadata, ki.created_at, ki.updated_at
                FROM knowledge_links kl
                JOIN knowledge_items ki ON (ki.id = kl.target_id OR ki.id = kl.source_id)
                WHERE (kl.source_id = :item_id OR kl.target_id = :item_id)
                  AND ki.id <> :item_id
                  AND (CAST(:tenant_id AS text) IS NULL OR ki.tenant_id = :tenant_id)
                ORDER BY ki.updated_at DESC
                """
            ),
            {"item_id": str(item_id), "tenant_id": principal.tenant_id},
        )
        return [dict(row) for row in result.mappings().all()]

    async def version_knowledge_item(
        self,
        db: AsyncSession,
        principal: Principal,
        item_id: UUID,
        diff: dict[str, Any],
        *,
        commit: bool = True,
    ) -> dict[str, Any]:
        version_result = await db.execute(
            text("SELECT COALESCE(MAX(version), 0) + 1 FROM knowledge_versions WHERE item_id = :item_id"),
            {"item_id": str(item_id)},
        )
        next_version = int(version_result.scalar_one())

        result = await db.execute(
            text(
                """
                INSERT INTO knowledge_versions (item_id, version, diff)
                VALUES (:item_id, :version, CAST(:diff AS jsonb))
                RETURNING id, item_id, version, diff, created_at
                """
            ),
            {"item_id": str(item_id), "version": next_version, "diff": json.dumps(diff)},
        )
        row = result.mappings().one()
        if commit:
            await db.commit()
        return dict(row)

    async def list_versions(self, db: AsyncSession, principal: Principal, item_id: UUID) -> list[dict[str, Any]]:
        result = await db.execute(
            text(
                """
                SELECT id, item_id, version, diff, created_at
                FROM knowledge_versions
                WHERE item_id = :item_id
                ORDER BY version DESC
                """
            ),
            {"item_id": str(item_id)},
        )
        return [dict(row) for row in result.mappings().all()]

    async def ingest(self, db: AsyncSession, principal: Principal, payload: KnowledgeIngestRequest) -> tuple[dict[str, Any], int]:
        content = extract_text_from_input(payload.raw_text, payload.url, payload.code, payload.document_text)
        title = payload.title or content[:80]

        item = await self.create_knowledge_item(
            db,
            principal,
            KnowledgeItemCreate(
                title=title,
                content=content,
                type=payload.type,
                tags=payload.tags,
                visibility=payload.visibility,
                metadata=payload.metadata,
            ),
        )

        qdrant = await self._get_qdrant_client()
        chunks = chunk_content(content)
        for idx, chunk in enumerate(chunks):
            embedding = generate_embeddings(chunk)
            chunk_result = await db.execute(
                text(
                    """
                    INSERT INTO knowledge_chunks (item_id, content, embedding_json, chunk_index)
                    VALUES (:item_id, :content, CAST(:embedding_json AS jsonb), :chunk_index)
                    RETURNING id
                    """
                ),
                {
                    "item_id": str(item["id"]),
                    "content": chunk,
                    "embedding_json": json.dumps(embedding),
                    "chunk_index": idx,
                },
            )
            chunk_row = chunk_result.mappings().one()

            if qdrant is not None:
                try:
                    qdrant.upsert(
                        collection_name=QDRANT_COLLECTION,
                        points=[
                            PointStruct(
                                id=str(chunk_row["id"]),
                                vector=embedding,
                                payload={
                                    "item_id": str(item["id"]),
                                    "tenant_id": principal.tenant_id,
                                    "chunk_index": idx,
                                },
                            )
                        ],
                    )
                except Exception as exc:
                    logger.warning("KnowledgeEngine Qdrant upsert failed for chunk {}: {}", chunk_row["id"], exc)

        await db.commit()
        return item, len(chunks)

    async def semantic_search(self, db: AsyncSession, principal: Principal, query: str, limit: int = 20) -> list[dict[str, Any]]:
        query_vec = generate_embeddings(query)

        qdrant_results = await self._semantic_search_qdrant(db, principal, query_vec, limit)
        if qdrant_results:
            await self._update_scores(db, qdrant_results)
            await db.commit()
            return [item for _, item in qdrant_results]

        fallback = await self._semantic_search_fallback(db, principal, query_vec, limit)
        if fallback:
            await self._update_scores(db, fallback)
            await db.commit()
        return [item for _, item in fallback]

    async def _semantic_search_qdrant(
        self,
        db: AsyncSession,
        principal: Principal,
        query_vec: list[float],
        limit: int,
    ) -> list[tuple[float, dict[str, Any]]]:
        qdrant = await self._get_qdrant_client()
        if qdrant is None:
            return []

        try:
            points = qdrant.search(
                collection_name=QDRANT_COLLECTION,
                query_vector=query_vec,
                limit=max(limit * 3, 10),
                with_payload=True,
            )
        except Exception as exc:
            logger.warning("KnowledgeEngine Qdrant search failed, falling back to JSON embeddings: {}", exc)
            return []

        seen_item_ids: set[str] = set()
        ordered: list[tuple[float, dict[str, Any]]] = []

        for point in points:
            payload = point.payload or {}
            item_id = payload.get("item_id")
            if not isinstance(item_id, str):
                continue
            if item_id in seen_item_ids:
                continue

            tenant_id = payload.get("tenant_id")
            if principal.tenant_id and tenant_id not in {principal.tenant_id, None, ""}:
                continue

            item = await self._get_item_by_id(db, principal.tenant_id, item_id)
            if item is None:
                continue

            score = float(getattr(point, "score", 0.0) or 0.0)
            ordered.append((score, item))
            seen_item_ids.add(item_id)
            if len(ordered) >= limit:
                break

        return ordered

    async def _semantic_search_fallback(
        self,
        db: AsyncSession,
        principal: Principal,
        query_vec: list[float],
        limit: int,
    ) -> list[tuple[float, dict[str, Any]]]:
        result = await db.execute(
            text(
                """
                SELECT kc.item_id, kc.embedding_json, ki.id, ki.tenant_id, ki.title, ki.content, ki.type, ki.tags, ki.visibility, ki.metadata, ki.created_at, ki.updated_at
                FROM knowledge_chunks kc
                JOIN knowledge_items ki ON ki.id = kc.item_id
                WHERE (CAST(:tenant_id AS text) IS NULL OR ki.tenant_id = :tenant_id)
                """
            ),
            {"tenant_id": principal.tenant_id},
        )

        best: dict[str, tuple[float, dict[str, Any]]] = {}
        for row in result.mappings().all():
            embedding = row.get("embedding_json") or []
            if not isinstance(embedding, list):
                continue
            score = _cosine(query_vec, [float(v) for v in embedding])
            item_id = str(row["item_id"])
            item = {
                "id": row["id"],
                "tenant_id": row["tenant_id"],
                "title": row["title"],
                "content": row["content"],
                "type": row["type"],
                "tags": row["tags"],
                "visibility": row["visibility"],
                "metadata": row["metadata"],
                "created_at": row["created_at"],
                "updated_at": row["updated_at"],
            }
            if item_id not in best or score > best[item_id][0]:
                best[item_id] = (score, item)

        return sorted(best.values(), key=lambda x: x[0], reverse=True)[:limit]

    async def list_help_docs(self, db: AsyncSession, principal: Principal, surface: str | None = None, limit: int = 50) -> list[dict[str, Any]]:
        where = ["(CAST(:tenant_id AS text) IS NULL OR tenant_id = :tenant_id)", "type = 'help_doc'"]
        params: dict[str, Any] = {"tenant_id": principal.tenant_id, "limit": limit}
        if surface:
            where.append("metadata ->> 'surface' = :surface")
            params["surface"] = surface

        sql = f"""
            SELECT id, tenant_id, title, content, type, tags, visibility, metadata, created_at, updated_at
            FROM knowledge_items
            WHERE {' AND '.join(where)}
            ORDER BY updated_at DESC
            LIMIT :limit
        """
        result = await db.execute(text(sql), params)
        return [dict(row) for row in result.mappings().all()]

    async def get_help_doc(self, db: AsyncSession, principal: Principal, help_key: str, surface: str | None = None) -> dict[str, Any] | None:
        where = ["(CAST(:tenant_id AS text) IS NULL OR tenant_id = :tenant_id)", "type = 'help_doc'", "metadata ->> 'help_key' = :help_key"]
        params: dict[str, Any] = {"tenant_id": principal.tenant_id, "help_key": help_key}
        if surface:
            where.append("metadata ->> 'surface' = :surface")
            params["surface"] = surface

        sql = f"""
            SELECT id, tenant_id, title, content, type, tags, visibility, metadata, created_at, updated_at
            FROM knowledge_items
            WHERE {' AND '.join(where)}
            ORDER BY updated_at DESC
            LIMIT 1
        """
        result = await db.execute(text(sql), params)
        row = result.mappings().one_or_none()
        return dict(row) if row else None

    async def _update_scores(self, db: AsyncSession, scored_items: list[tuple[float, dict[str, Any]]]) -> None:
        now = datetime.now(timezone.utc)
        for score, item in scored_items:
            await db.execute(
                text(
                    """
                    INSERT INTO knowledge_scores (item_id, usage_count, relevance_score, last_used)
                    VALUES (CAST(:item_id AS uuid), 1, :score, :last_used)
                    ON CONFLICT (item_id)
                    DO UPDATE SET
                        usage_count = knowledge_scores.usage_count + 1,
                        relevance_score = GREATEST(knowledge_scores.relevance_score, EXCLUDED.relevance_score),
                        last_used = EXCLUDED.last_used,
                        updated_at = NOW()
                    """
                ),
                {
                    "item_id": str(item["id"]),
                    "score": float(score),
                    "last_used": now,
                },
            )


_service: KnowledgeEngineService | None = None


def get_knowledge_engine_service() -> KnowledgeEngineService:
    global _service
    if _service is None:
        _service = KnowledgeEngineService()
    return _service


def _cosine(a: list[float], b: list[float]) -> float:
    if not a or not b:
        return 0.0
    length = min(len(a), len(b))
    if length == 0:
        return 0.0
    dot = sum(a[i] * b[i] for i in range(length))
    na = math.sqrt(sum(a[i] * a[i] for i in range(length)))
    nb = math.sqrt(sum(b[i] * b[i] for i in range(length)))
    if na == 0 or nb == 0:
        return 0.0
    return dot / (na * nb)
