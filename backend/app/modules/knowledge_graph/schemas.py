"""
Pydantic schemas for Knowledge Graph module
"""

from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field
from datetime import datetime


class KnowledgeGraphInfo(BaseModel):
    """Knowledge Graph system information"""

    name: str = "BRAiN Knowledge Graph"
    version: str = "0.1.0"
    description: str = "Semantic memory and knowledge graph using Cognee"
    status: str = "active"
    features: List[str] = [
        "semantic_search",
        "knowledge_graphs",
        "agent_memory",
        "mission_context",
        "audit_trail",
    ]
    backend: str = "cognee"
    vector_db: str = "qdrant"  # or pgvector
    graph_db: str = "networkx"  # or falkordb, kuzu


class AddDataRequest(BaseModel):
    """Request to add data to knowledge graph"""

    data: str | List[str] | Dict[str, Any] = Field(
        ...,
        description="Data to add (text, list of texts, or structured data)",
    )
    dataset_name: Optional[str] = Field(
        None,
        description="Dataset name for organization (e.g., 'missions', 'policies')",
    )
    metadata: Optional[Dict[str, Any]] = Field(
        None,
        description="Additional metadata for the data",
    )


class AddDataResponse(BaseModel):
    """Response after adding data"""

    success: bool
    message: str
    dataset_name: Optional[str] = None
    items_added: int = 0


class SearchRequest(BaseModel):
    """Request to search knowledge graph"""

    query: str = Field(
        ...,
        description="Search query (natural language or structured)",
    )
    dataset_name: Optional[str] = Field(
        None,
        description="Limit search to specific dataset",
    )
    search_type: str = Field(
        "HYBRID",
        description="Search type: INSIGHTS, CHUNKS, or HYBRID",
    )
    limit: int = Field(
        5,
        ge=1,
        le=100,
        description="Maximum number of results",
    )


class SearchResult(BaseModel):
    """Single search result"""

    content: str
    score: float = Field(
        description="Relevance score (0-1)",
    )
    metadata: Optional[Dict[str, Any]] = None
    source: Optional[str] = None


class SearchResponse(BaseModel):
    """Response from search operation"""

    query: str
    results: List[SearchResult]
    total_results: int
    search_type: str
    dataset_name: Optional[str] = None


class MissionContextRequest(BaseModel):
    """Request to add mission context to knowledge graph"""

    mission_id: str
    name: str
    description: str
    status: str
    priority: str
    mission_type: Optional[str] = None
    assigned_agent: Optional[str] = None
    context: Optional[Dict[str, Any]] = None
    created_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    result: Optional[Dict[str, Any]] = None


class SimilarMission(BaseModel):
    """Similar mission result"""

    mission_id: str
    name: str
    description: str
    status: str
    similarity_score: float
    reasoning: Optional[str] = None


class SimilarMissionsResponse(BaseModel):
    """Response with similar missions"""

    query_mission_id: str
    similar_missions: List[SimilarMission]
    total_found: int


class CognifyRequest(BaseModel):
    """Request to cognify (process) data into knowledge graph"""

    dataset_name: str = Field(
        ...,
        description="Dataset to cognify",
    )
    temporal: bool = Field(
        False,
        description="Enable temporal awareness (time-indexed facts)",
    )


class CognifyResponse(BaseModel):
    """Response from cognify operation"""

    success: bool
    message: str
    dataset_name: str
    triplets_extracted: Optional[int] = None
    processing_time_seconds: Optional[float] = None


class DatasetInfo(BaseModel):
    """Information about a dataset"""

    name: str
    description: Optional[str] = None
    item_count: int = 0
    created_at: Optional[datetime] = None
    last_updated: Optional[datetime] = None


class ListDatasetsResponse(BaseModel):
    """Response listing all datasets"""

    datasets: List[DatasetInfo]
    total_datasets: int
