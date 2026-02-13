"""
Knowledge Graph Module for BRAiN

Provides semantic memory and knowledge graph capabilities using Cognee.
This module enables:
- Persistent agent memory across sessions
- Semantic search over mission history
- Knowledge graph-based reasoning
- Audit trail with relationship tracking

Phase: PoC (Proof of Concept)
Version: 0.1.0
"""

from .service import CogneeService, AgentMemoryService
from .schemas import (
    KnowledgeGraphInfo,
    AddDataRequest,
    AddDataResponse,
    SearchRequest,
    SearchResponse,
    MissionContextRequest,
    SimilarMissionsResponse,
)

__all__ = [
    "CogneeService",
    "AgentMemoryService",
    "KnowledgeGraphInfo",
    "AddDataRequest",
    "AddDataResponse",
    "SearchRequest",
    "SearchResponse",
    "MissionContextRequest",
    "SimilarMissionsResponse",
]
