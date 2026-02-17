"""
Cluster System Business Logic

Handles:
- Cluster creation from blueprints
- Agent spawning and hierarchy management
- Scaling operations (up/down/hibernate)
- Lifecycle management
- Metrics collection
"""

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_, or_, func
from typing import Optional, List, Dict, Any
from datetime import datetime, timedelta
from loguru import logger
import uuid

from .models import (
    Cluster,
    ClusterAgent,
    ClusterBlueprint,
    ClusterMetrics,
    ClusterStatus,
    ClusterType,
    AgentRole
)
from .schemas import (
    ClusterCreate,
    ClusterUpdate,
    ClusterScale,
    ClusterResponse,
    ClusterAgentCreate,
    ClusterAgentResponse,
    ClusterHierarchyResponse
)
from .blueprints.loader import BlueprintLoader
from .creator.spawner import ClusterSpawner


class ClusterService:
    """
    Main service for cluster operations.

    Usage:
        service = ClusterService(db_session)
        cluster = await service.create_from_blueprint(...)
    """

    def __init__(self, db: AsyncSession):
        self.db = db
        self.blueprint_loader = BlueprintLoader()
        self.spawner = ClusterSpawner(db)

    # ===== CLUSTER CRUD =====

    async def create_from_blueprint(
        self,
        data: ClusterCreate
    ) -> Cluster:
        """
        Create cluster from blueprint.

        Steps:
        1. Load and validate blueprint
        2. Create cluster DB entry
        3. Spawn supervisor agent
        4. Spawn initial workers
        5. Generate manifest files
        6. Set status to ACTIVE

        Args:
            data: ClusterCreate schema with blueprint_id and overrides

        Returns:
            Cluster: Created cluster instance

        Raises:
            ValueError: If blueprint not found or invalid
            RuntimeError: If agent spawning fails
        """
        # TODO: Implement (Max's Task 3.3)
        logger.info(f"Creating cluster '{data.name}' from blueprint '{data.blueprint_id}'")
        raise NotImplementedError("ClusterService.create_from_blueprint - To be implemented by Max")

    async def get_cluster(self, cluster_id: str) -> Optional[Cluster]:
        """Get cluster by ID"""
        result = await self.db.execute(
            select(Cluster).where(Cluster.id == cluster_id)
        )
        return result.scalar_one_or_none()

    async def list_clusters(
        self,
        status: Optional[ClusterStatus] = None,
        type: Optional[ClusterType] = None,
        offset: int = 0,
        limit: int = 50
    ) -> List[Cluster]:
        """List clusters with optional filters"""
        query = select(Cluster)

        if status:
            query = query.where(Cluster.status == status)
        if type:
            query = query.where(Cluster.type == type)

        query = query.offset(offset).limit(limit).order_by(Cluster.created_at.desc())

        result = await self.db.execute(query)
        return list(result.scalars().all())

    async def update_cluster(
        self,
        cluster_id: str,
        data: ClusterUpdate
    ) -> Cluster:
        """Update cluster configuration"""
        cluster = await self.get_cluster(cluster_id)
        if not cluster:
            raise ValueError(f"Cluster {cluster_id} not found")

        # Update fields if provided
        if data.name is not None:
            cluster.name = data.name
        if data.description is not None:
            cluster.description = data.description
        if data.tags is not None:
            cluster.tags = data.tags
        if data.min_workers is not None:
            cluster.min_workers = data.min_workers
        if data.max_workers is not None:
            cluster.max_workers = data.max_workers
        if data.config is not None:
            cluster.config = data.config

        await self.db.commit()
        await self.db.refresh(cluster)

        logger.info(f"Updated cluster {cluster_id}")
        return cluster

    async def delete_cluster(self, cluster_id: str) -> bool:
        """
        Soft delete cluster (set status to DESTROYED).

        For hard delete, use destroy_cluster().
        """
        cluster = await self.get_cluster(cluster_id)
        if not cluster:
            return False

        cluster.status = ClusterStatus.DESTROYED
        cluster.destroyed_at = datetime.utcnow()
        await self.db.commit()

        logger.info(f"Soft deleted cluster {cluster_id}")
        return True

    # ===== SCALING OPERATIONS =====

    async def scale_cluster(
        self,
        cluster_id: str,
        data: ClusterScale
    ) -> Cluster:
        """
        Scale cluster to target worker count.

        If target > current: spawn workers
        If target < current: stop workers

        Args:
            cluster_id: Cluster ID
            data: ClusterScale with target_workers

        Returns:
            Cluster: Updated cluster

        Raises:
            ValueError: If target exceeds max_workers
        """
        # TODO: Implement (Max's Task 3.3)
        logger.info(f"Scaling cluster {cluster_id} to {data.target_workers} workers")
        raise NotImplementedError("ClusterService.scale_cluster - To be implemented by Max")

    async def hibernate_cluster(self, cluster_id: str) -> Cluster:
        """
        Hibernate cluster (stop all workers, keep supervisor).

        Sets current_workers = 0, status = HIBERNATED.
        Cluster can be reactivated later.
        """
        # TODO: Implement (Max's Task 3.3)
        logger.info(f"Hibernating cluster {cluster_id}")
        raise NotImplementedError("ClusterService.hibernate_cluster - To be implemented by Max")

    async def reactivate_cluster(self, cluster_id: str) -> Cluster:
        """
        Reactivate hibernated cluster.

        Spawns min_workers, sets status = ACTIVE.
        """
        # TODO: Implement (Max's Task 3.3)
        logger.info(f"Reactivating cluster {cluster_id}")
        raise NotImplementedError("ClusterService.reactivate_cluster - To be implemented by Max")

    # ===== AGENT MANAGEMENT =====

    async def add_agent(
        self,
        cluster_id: str,
        data: ClusterAgentCreate
    ) -> ClusterAgent:
        """
        Add existing agent to cluster.

        For creating new agents, use spawner.
        """
        cluster = await self.get_cluster(cluster_id)
        if not cluster:
            raise ValueError(f"Cluster {cluster_id} not found")

        agent = ClusterAgent(
            id=str(uuid.uuid4()),
            cluster_id=cluster_id,
            agent_id=data.agent_id,
            role=data.role,
            supervisor_id=data.supervisor_id,
            capabilities=data.capabilities,
            skills=data.skills
        )

        self.db.add(agent)
        await self.db.commit()
        await self.db.refresh(agent)

        logger.info(f"Added agent {data.agent_id} to cluster {cluster_id}")
        return agent

    async def get_cluster_agents(
        self,
        cluster_id: str,
        role: Optional[AgentRole] = None
    ) -> List[ClusterAgent]:
        """Get all agents in cluster, optionally filtered by role"""
        query = select(ClusterAgent).where(ClusterAgent.cluster_id == cluster_id)

        if role:
            query = query.where(ClusterAgent.role == role)

        result = await self.db.execute(query)
        return list(result.scalars().all())

    async def get_cluster_hierarchy(self, cluster_id: str) -> ClusterHierarchyResponse:
        """
        Get agent hierarchy as nested structure.

        Returns:
            Supervisor at root with recursive subordinates
        """
        # TODO: Implement (Max's Task 3.3)
        logger.info(f"Getting hierarchy for cluster {cluster_id}")
        raise NotImplementedError("ClusterService.get_cluster_hierarchy - To be implemented by Max")

    # ===== METRICS =====

    async def record_metrics(
        self,
        cluster_id: str,
        metrics_data: Dict[str, Any]
    ) -> ClusterMetrics:
        """Record cluster metrics snapshot"""
        metrics = ClusterMetrics(
            id=str(uuid.uuid4()),
            cluster_id=cluster_id,
            **metrics_data
        )

        self.db.add(metrics)
        await self.db.commit()
        await self.db.refresh(metrics)

        return metrics

    async def get_metrics(
        self,
        cluster_id: str,
        start_time: Optional[datetime] = None,
        end_time: Optional[datetime] = None,
        limit: int = 100
    ) -> List[ClusterMetrics]:
        """Get metrics time series"""
        query = select(ClusterMetrics).where(
            ClusterMetrics.cluster_id == cluster_id
        )

        if start_time:
            query = query.where(ClusterMetrics.timestamp >= start_time)
        if end_time:
            query = query.where(ClusterMetrics.timestamp <= end_time)

        query = query.order_by(ClusterMetrics.timestamp.desc()).limit(limit)

        result = await self.db.execute(query)
        return list(result.scalars().all())

    # ===== AUTO-SCALING LOGIC =====

    async def check_scaling_needed(self, cluster_id: str) -> Optional[int]:
        """
        Check if cluster needs scaling based on metrics.

        Returns:
            int: New target_workers if scaling needed, None otherwise
        """
        # TODO: Implement (Max's Task 3.3)
        # Logic:
        # - Get latest metrics
        # - Check load_percentage, queue_length
        # - Compare against blueprint scaling rules
        # - Return new target if scale up/down needed
        raise NotImplementedError("ClusterService.check_scaling_needed - To be implemented by Max")
