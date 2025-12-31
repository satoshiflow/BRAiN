"""
Knowledge Graph Service - Cognee Integration

Provides semantic memory and knowledge graph capabilities for BRAiN.
"""

import time
from typing import Any, Dict, List, Optional
from datetime import datetime
from loguru import logger

try:
    import cognee
    from cognee.api.v1.search import SearchType
    COGNEE_AVAILABLE = True
except ImportError:
    logger.warning("Cognee not available - knowledge graph features disabled")
    COGNEE_AVAILABLE = False

from .schemas import (
    AddDataResponse,
    SearchResult,
    SearchResponse,
    MissionContextRequest,
    SimilarMission,
    SimilarMissionsResponse,
    CognifyResponse,
    DatasetInfo,
    ListDatasetsResponse,
)


class CogneeService:
    """
    Base wrapper around Cognee SDK for knowledge graph operations

    Provides:
    - Data ingestion (add)
    - Cognification (extract entities/relationships)
    - Semantic search (vector + graph hybrid)
    - Dataset management
    """

    def __init__(self):
        """Initialize Cognee service"""
        self.initialized = False

        if not COGNEE_AVAILABLE:
            logger.error("Cognee not installed - install with: pip install cognee[postgres]")
            return

        try:
            # Initialize cognee with default settings
            # This will use environment variables for configuration
            logger.info("Initializing Cognee knowledge graph service")
            self.initialized = True
            logger.success("Cognee service initialized successfully")
        except Exception as e:
            logger.error(f"Failed to initialize Cognee: {e}")
            self.initialized = False

    async def add_data(
        self,
        data: str | List[str] | Dict[str, Any],
        dataset_name: Optional[str] = None,
    ) -> AddDataResponse:
        """
        Add data to knowledge graph

        Args:
            data: Text, list of texts, or structured data
            dataset_name: Optional dataset identifier

        Returns:
            AddDataResponse with success status
        """
        if not self.initialized:
            return AddDataResponse(
                success=False,
                message="Cognee service not initialized",
                items_added=0,
            )

        try:
            # Add data to cognee
            await cognee.add(data, dataset_name=dataset_name)

            # Count items
            items_count = 1
            if isinstance(data, list):
                items_count = len(data)

            logger.info(
                f"Added {items_count} items to knowledge graph"
                + (f" (dataset: {dataset_name})" if dataset_name else "")
            )

            return AddDataResponse(
                success=True,
                message=f"Successfully added {items_count} items",
                dataset_name=dataset_name,
                items_added=items_count,
            )

        except Exception as e:
            logger.error(f"Failed to add data to knowledge graph: {e}")
            return AddDataResponse(
                success=False,
                message=f"Error: {str(e)}",
                items_added=0,
            )

    async def cognify(
        self,
        dataset_name: Optional[str] = None,
        temporal: bool = False,
    ) -> CognifyResponse:
        """
        Process data into knowledge graph (extract entities/relationships)

        Args:
            dataset_name: Optional dataset to cognify
            temporal: Enable temporal awareness

        Returns:
            CognifyResponse with processing results
        """
        if not self.initialized:
            return CognifyResponse(
                success=False,
                message="Cognee service not initialized",
                dataset_name=dataset_name or "unknown",
            )

        try:
            start_time = time.time()

            # Run cognify pipeline
            logger.info(f"Starting cognify process for dataset: {dataset_name}")
            await cognee.cognify(temporal=temporal)

            processing_time = time.time() - start_time

            logger.success(
                f"Cognify completed in {processing_time:.2f}s"
                + (f" (dataset: {dataset_name})" if dataset_name else "")
            )

            return CognifyResponse(
                success=True,
                message="Cognify process completed successfully",
                dataset_name=dataset_name or "default",
                processing_time_seconds=processing_time,
            )

        except Exception as e:
            logger.error(f"Cognify process failed: {e}")
            return CognifyResponse(
                success=False,
                message=f"Error: {str(e)}",
                dataset_name=dataset_name or "unknown",
            )

    async def search(
        self,
        query: str,
        dataset_name: Optional[str] = None,
        search_type: str = "HYBRID",
        limit: int = 5,
    ) -> SearchResponse:
        """
        Search knowledge graph

        Args:
            query: Search query (natural language)
            dataset_name: Optional dataset to search
            search_type: INSIGHTS, CHUNKS, or HYBRID
            limit: Maximum results

        Returns:
            SearchResponse with results
        """
        if not self.initialized:
            return SearchResponse(
                query=query,
                results=[],
                total_results=0,
                search_type=search_type,
            )

        try:
            # Map search type string to enum
            if hasattr(SearchType, search_type):
                search_type_enum = getattr(SearchType, search_type)
            else:
                search_type_enum = SearchType.INSIGHTS

            # Execute search
            logger.info(f"Searching knowledge graph: '{query}' (type: {search_type})")
            raw_results = await cognee.search(
                search_type_enum,
                query_text=query,
            )

            # Parse results
            results = []
            for item in raw_results[:limit]:
                # Handle different result formats
                if isinstance(item, dict):
                    results.append(SearchResult(
                        content=str(item.get("text", item.get("content", str(item)))),
                        score=float(item.get("score", 0.0)),
                        metadata=item.get("metadata"),
                        source=item.get("source"),
                    ))
                else:
                    # If result is not a dict, convert to string
                    results.append(SearchResult(
                        content=str(item),
                        score=1.0,  # Default score
                        metadata=None,
                        source=None,
                    ))

            logger.info(f"Found {len(results)} results for query: '{query}'")

            return SearchResponse(
                query=query,
                results=results,
                total_results=len(results),
                search_type=search_type,
                dataset_name=dataset_name,
            )

        except Exception as e:
            logger.error(f"Search failed: {e}")
            return SearchResponse(
                query=query,
                results=[],
                total_results=0,
                search_type=search_type,
            )

    async def list_datasets(self) -> ListDatasetsResponse:
        """
        List all datasets in knowledge graph

        Returns:
            ListDatasetsResponse with dataset information
        """
        if not self.initialized:
            return ListDatasetsResponse(
                datasets=[],
                total_datasets=0,
            )

        try:
            # Get datasets from cognee
            datasets_data = await cognee.datasets.list()

            datasets = []
            for ds in datasets_data:
                if isinstance(ds, dict):
                    datasets.append(DatasetInfo(
                        name=ds.get("name", "unknown"),
                        description=ds.get("description"),
                        item_count=ds.get("item_count", 0),
                    ))
                else:
                    # Handle string dataset names
                    datasets.append(DatasetInfo(
                        name=str(ds),
                        item_count=0,
                    ))

            return ListDatasetsResponse(
                datasets=datasets,
                total_datasets=len(datasets),
            )

        except Exception as e:
            logger.error(f"Failed to list datasets: {e}")
            return ListDatasetsResponse(
                datasets=[],
                total_datasets=0,
            )

    async def reset(self) -> bool:
        """
        Reset/prune all data (USE WITH CAUTION)

        Returns:
            True if successful
        """
        if not self.initialized:
            return False

        try:
            logger.warning("Resetting all knowledge graph data")
            await cognee.prune.prune_data()
            logger.success("Knowledge graph data reset completed")
            return True
        except Exception as e:
            logger.error(f"Failed to reset knowledge graph: {e}")
            return False


class AgentMemoryService:
    """
    Agent memory management using knowledge graphs

    Provides:
    - Mission context storage
    - Similar mission retrieval
    - Agent expertise tracking
    """

    def __init__(self):
        """Initialize agent memory service"""
        self.cognee = CogneeService()

    async def record_mission_context(
        self,
        mission: MissionContextRequest,
    ) -> AddDataResponse:
        """
        Store mission execution as knowledge graph

        Args:
            mission: Mission context data

        Returns:
            AddDataResponse
        """
        try:
            # Format mission as structured text for better entity extraction
            mission_text = f"""
Mission: {mission.name}
ID: {mission.mission_id}
Type: {mission.mission_type or 'general'}
Status: {mission.status}
Priority: {mission.priority}
Assigned Agent: {mission.assigned_agent or 'unassigned'}
Description: {mission.description}
Created: {mission.created_at or 'unknown'}
Completed: {mission.completed_at or 'ongoing'}
Result: {mission.result or 'pending'}
Additional Context: {mission.context or {}}
"""

            # Add to missions dataset
            response = await self.cognee.add_data(
                data=mission_text,
                dataset_name="missions",
            )

            logger.info(f"Recorded mission context: {mission.mission_id}")
            return response

        except Exception as e:
            logger.error(f"Failed to record mission context: {e}")
            return AddDataResponse(
                success=False,
                message=f"Error: {str(e)}",
                items_added=0,
            )

    async def find_similar_missions(
        self,
        query_mission: MissionContextRequest,
        limit: int = 5,
    ) -> SimilarMissionsResponse:
        """
        Find missions similar to the given mission

        Args:
            query_mission: Mission to compare against
            limit: Maximum results

        Returns:
            SimilarMissionsResponse
        """
        try:
            # Build search query
            query = f"""
Find missions similar to:
Type: {query_mission.mission_type}
Priority: {query_mission.priority}
Description: {query_mission.description}
"""

            # Search knowledge graph
            search_response = await self.cognee.search(
                query=query,
                dataset_name="missions",
                search_type="HYBRID",
                limit=limit,
            )

            # Parse results into similar missions
            similar = []
            for result in search_response.results:
                # Extract mission info from content
                # This is simplified - in production, use structured extraction
                similar.append(SimilarMission(
                    mission_id=f"mission_{hash(result.content) % 10000}",
                    name="Extracted from knowledge graph",
                    description=result.content[:200],
                    status="unknown",
                    similarity_score=result.score,
                    reasoning=f"Score: {result.score:.2f}",
                ))

            logger.info(
                f"Found {len(similar)} similar missions for: {query_mission.mission_id}"
            )

            return SimilarMissionsResponse(
                query_mission_id=query_mission.mission_id,
                similar_missions=similar,
                total_found=len(similar),
            )

        except Exception as e:
            logger.error(f"Failed to find similar missions: {e}")
            return SimilarMissionsResponse(
                query_mission_id=query_mission.mission_id,
                similar_missions=[],
                total_found=0,
            )

    async def get_agent_expertise(
        self,
        agent_id: str,
    ) -> SearchResponse:
        """
        Extract agent's decision history from knowledge graph

        Args:
            agent_id: Agent identifier

        Returns:
            SearchResponse with agent expertise data
        """
        query = f"What decisions and tasks has {agent_id} completed successfully?"

        return await self.cognee.search(
            query=query,
            dataset_name="missions",
            search_type="INSIGHTS",
            limit=10,
        )
