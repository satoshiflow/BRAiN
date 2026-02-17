"""
Knowledge Graph API Router

REST API endpoints for knowledge graph operations.
"""

from typing import Optional
from fastapi import APIRouter, HTTPException
from loguru import logger

from .service import CogneeService, AgentMemoryService
from .schemas import (
    KnowledgeGraphInfo,
    AddDataRequest,
    AddDataResponse,
    SearchRequest,
    SearchResponse,
    MissionContextRequest,
    SimilarMissionsResponse,
    CognifyRequest,
    CognifyResponse,
    ListDatasetsResponse,
)


# Create router
router = APIRouter(
    prefix="/api/knowledge-graph",
    tags=["knowledge-graph"],
)

# Initialize services
cognee_service = CogneeService()
memory_service = AgentMemoryService()


@router.get(
    "/info",
    response_model=KnowledgeGraphInfo,
    summary="Get knowledge graph system information",
)
async def get_info():
    """
    Get information about the knowledge graph system

    Returns system status, features, and backend configuration.
    """
    return KnowledgeGraphInfo(
        status="active" if cognee_service.initialized else "unavailable",
    )


@router.post(
    "/add",
    response_model=AddDataResponse,
    summary="Add data to knowledge graph",
)
async def add_data(request: AddDataRequest):
    """
    Add data to the knowledge graph

    Accepts:
    - Text strings
    - Lists of text strings
    - Structured data dictionaries

    The data will be stored in the specified dataset.
    """
    return await cognee_service.add_data(
        data=request.data,
        dataset_name=request.dataset_name,
    )


@router.post(
    "/cognify",
    response_model=CognifyResponse,
    summary="Process data into knowledge graph",
)
async def cognify_data(request: CognifyRequest):
    """
    Process data into knowledge graph (extract entities and relationships)

    This operation:
    1. Analyzes text data
    2. Extracts entities (people, places, concepts)
    3. Identifies relationships (triplets)
    4. Builds knowledge graph structure
    5. Generates embeddings for semantic search

    This is a potentially long-running operation for large datasets.
    """
    return await cognee_service.cognify(
        dataset_name=request.dataset_name,
        temporal=request.temporal,
    )


@router.post(
    "/search",
    response_model=SearchResponse,
    summary="Search knowledge graph",
)
async def search_knowledge_graph(request: SearchRequest):
    """
    Search the knowledge graph using semantic search

    Search types:
    - INSIGHTS: High-level semantic search
    - CHUNKS: Document chunk search
    - HYBRID: Combination of vector + graph search (recommended)

    Returns ranked results with relevance scores.
    """
    return await cognee_service.search(
        query=request.query,
        dataset_name=request.dataset_name,
        search_type=request.search_type,
        limit=request.limit,
    )


@router.get(
    "/datasets",
    response_model=ListDatasetsResponse,
    summary="List all datasets",
)
async def list_datasets():
    """
    List all datasets in the knowledge graph

    Returns information about each dataset including:
    - Name
    - Description
    - Item count
    - Last updated timestamp
    """
    return await cognee_service.list_datasets()


@router.delete(
    "/reset",
    summary="Reset knowledge graph (CAUTION)",
)
async def reset_knowledge_graph():
    """
    **DANGER**: Reset/delete all knowledge graph data

    This operation:
    - Deletes all datasets
    - Removes all knowledge graphs
    - Clears all embeddings
    - Cannot be undone

    Use only for testing or complete system reset.
    """
    try:
        success = await cognee_service.reset()
        if success:
            return {"success": True, "message": "Knowledge graph reset completed"}
        else:
            raise HTTPException(
                status_code=500,
                detail="Failed to reset knowledge graph",
            )
    except Exception as e:
        logger.error(f"Reset failed: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Reset operation failed: {str(e)}",
        )


# Agent Memory Endpoints


@router.post(
    "/missions/record",
    response_model=AddDataResponse,
    summary="Record mission context",
    tags=["agent-memory"],
)
async def record_mission_context(mission: MissionContextRequest):
    """
    Record a mission's context in the knowledge graph

    This creates structured knowledge from mission data including:
    - Mission metadata (ID, type, priority)
    - Agent assignments
    - Execution results
    - Temporal information

    Used by agents to build persistent memory.
    """
    return await memory_service.record_mission_context(mission)


@router.post(
    "/missions/similar",
    response_model=SimilarMissionsResponse,
    summary="Find similar missions",
    tags=["agent-memory"],
)
async def find_similar_missions(
    mission: MissionContextRequest,
    limit: int = 5,
):
    """
    Find missions similar to the given mission

    Uses semantic search to find past missions with:
    - Similar descriptions
    - Same mission type
    - Similar context
    - Comparable priority

    Useful for:
    - Learning from past successes/failures
    - Risk assessment
    - Agent decision support
    """
    return await memory_service.find_similar_missions(
        query_mission=mission,
        limit=limit,
    )


@router.get(
    "/agents/{agent_id}/expertise",
    response_model=SearchResponse,
    summary="Get agent expertise",
    tags=["agent-memory"],
)
async def get_agent_expertise(agent_id: str):
    """
    Extract agent's expertise from decision history

    Analyzes the knowledge graph to find:
    - Successful task completions
    - Decision patterns
    - Specialized knowledge
    - Performance history

    Returns insights about the agent's capabilities and experience.
    """
    return await memory_service.get_agent_expertise(agent_id)


# Health check endpoint


@router.get(
    "/health",
    summary="Knowledge graph health check",
)
async def health_check():
    """
    Check knowledge graph system health

    Returns:
    - Initialization status
    - Backend availability
    - Error states
    """
    return {
        "status": "healthy" if cognee_service.initialized else "unhealthy",
        "initialized": cognee_service.initialized,
        "service": "cognee",
    }
