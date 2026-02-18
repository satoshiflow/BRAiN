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
from .blueprints.validator import BlueprintValidator
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
        self.blueprint_validator = BlueprintValidator()
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
        logger.info(f"Creating cluster '{data.name}' from blueprint '{data.blueprint_id}'")

        try:
            # Step 1: Load and validate blueprint
            blueprint_filename = f"{data.blueprint_id}.yaml"
            blueprint = self.blueprint_loader.load_from_file(blueprint_filename)
            self.blueprint_validator.validate(blueprint)

            # Step 2: Create cluster DB entry
            cluster_config = blueprint.get("cluster", {})
            metadata = blueprint.get("metadata", {})

            cluster = Cluster(
                id=str(uuid.uuid4()),
                name=data.name,
                type=data.type or ClusterType(cluster_config.get("type", "department")),
                blueprint_id=data.blueprint_id,
                status=ClusterStatus.SPAWNING,
                description=data.description or metadata.get("description"),
                tags=data.tags or metadata.get("tags", []),
                min_workers=data.min_workers or cluster_config.get("min_workers", 1),
                max_workers=data.max_workers or cluster_config.get("max_workers", 10),
                target_workers=data.target_workers or cluster_config.get("default_workers", 3),
                current_workers=0,
                health_score=1.0,
                config=data.config or cluster_config,
                created_at=datetime.utcnow()
            )

            self.db.add(cluster)
            await self.db.flush()  # Get cluster.id

            logger.info(f"Cluster DB entry created: {cluster.id}")

            # Step 3: Spawn agents from blueprint
            agents = await self.spawner.spawn_from_blueprint(cluster.id, blueprint)
            cluster.current_workers = len([a for a in agents if a.role == AgentRole.WORKER])

            # Step 4: Set status to ACTIVE
            cluster.status = ClusterStatus.ACTIVE
            cluster.started_at = datetime.utcnow()

            await self.db.commit()
            await self.db.refresh(cluster)

            logger.info(f"Cluster {cluster.id} created successfully with {len(agents)} agents")
            return cluster

        except FileNotFoundError as e:
            logger.error(f"Blueprint not found: {e}")
            raise ValueError(f"Blueprint '{data.blueprint_id}' not found")
        except ValueError as e:
            logger.error(f"Blueprint validation failed: {e}")
            raise ValueError(f"Invalid blueprint: {e}")
        except Exception as e:
            logger.error(f"Cluster creation failed: {e}", exc_info=True)
            await self.db.rollback()
            raise RuntimeError(f"Failed to create cluster: {e}")

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
        logger.info(f"Scaling cluster {cluster_id} to {data.target_workers} workers")

        cluster = await self.get_cluster(cluster_id)
        if not cluster:
            raise ValueError(f"Cluster {cluster_id} not found")

        # Validate target
        if data.target_workers < cluster.min_workers:
            raise ValueError(f"Target workers ({data.target_workers}) cannot be less than min_workers ({cluster.min_workers})")

        if data.target_workers > cluster.max_workers:
            raise ValueError(f"Target workers ({data.target_workers}) cannot exceed max_workers ({cluster.max_workers})")

        current = cluster.current_workers
        target = data.target_workers

        if current == target:
            logger.info(f"Cluster {cluster_id} already at target worker count: {target}")
            return cluster

        # Update cluster
        cluster.target_workers = target
        cluster.status = ClusterStatus.SCALING

        await self.db.commit()

        # Determine scaling action
        if target > current:
            # Scale up
            to_spawn = target - current
            logger.info(f"Scaling up cluster {cluster_id}: spawning {to_spawn} workers")

            # Get worker agents from cluster to use as template
            workers = await self.get_cluster_agents(cluster_id, role=AgentRole.WORKER)
            if workers:
                # Use first worker as template
                template = workers[0]
                logger.debug(f"Using worker template: {template.agent_id}")
                # TODO: Spawn additional workers via spawner
                # For now, just update count
                cluster.current_workers = target
            else:
                logger.warning(f"No worker agents found in cluster {cluster_id} to use as template")
                cluster.current_workers = target

        else:
            # Scale down
            to_stop = current - target
            logger.info(f"Scaling down cluster {cluster_id}: stopping {to_stop} workers")

            # Get worker agents to stop
            workers = await self.get_cluster_agents(cluster_id, role=AgentRole.WORKER)
            workers_to_stop = workers[:to_stop]

            # TODO: Stop agents via Genesis
            # For now, just mark as inactive
            for worker in workers_to_stop:
                worker.status = "inactive"
                logger.debug(f"Marked worker {worker.agent_id} as inactive")

            cluster.current_workers = target

        # Set back to ACTIVE
        cluster.status = ClusterStatus.ACTIVE
        await self.db.commit()
        await self.db.refresh(cluster)

        logger.info(f"Cluster {cluster_id} scaled successfully to {target} workers")
        return cluster

    async def hibernate_cluster(self, cluster_id: str) -> Cluster:
        """
        Hibernate cluster (stop all workers, keep supervisor).

        Sets current_workers = 0, status = HIBERNATED.
        Cluster can be reactivated later.
        """
        logger.info(f"Hibernating cluster {cluster_id}")

        cluster = await self.get_cluster(cluster_id)
        if not cluster:
            raise ValueError(f"Cluster {cluster_id} not found")

        if cluster.status == ClusterStatus.HIBERNATED:
            logger.info(f"Cluster {cluster_id} is already hibernated")
            return cluster

        # Get all worker and specialist agents
        agents = await self.get_cluster_agents(cluster_id)
        workers_to_stop = [
            a for a in agents
            if a.role in [AgentRole.WORKER, AgentRole.SPECIALIST]
        ]

        # TODO: Stop agents via Genesis
        # For now, mark as inactive
        for agent in workers_to_stop:
            agent.status = "hibernated"
            logger.debug(f"Hibernated agent {agent.agent_id}")

        # Update cluster
        cluster.status = ClusterStatus.HIBERNATED
        cluster.current_workers = 0
        cluster.hibernated_at = datetime.utcnow()

        await self.db.commit()
        await self.db.refresh(cluster)

        logger.info(f"Cluster {cluster_id} hibernated successfully ({len(workers_to_stop)} agents stopped)")
        return cluster

    async def reactivate_cluster(self, cluster_id: str) -> Cluster:
        """
        Reactivate hibernated cluster.

        Spawns min_workers, sets status = ACTIVE.
        """
        logger.info(f"Reactivating cluster {cluster_id}")

        cluster = await self.get_cluster(cluster_id)
        if not cluster:
            raise ValueError(f"Cluster {cluster_id} not found")

        if cluster.status != ClusterStatus.HIBERNATED:
            logger.warning(f"Cluster {cluster_id} is not hibernated (status: {cluster.status})")
            return cluster

        # Get hibernated agents
        agents = await self.get_cluster_agents(cluster_id)
        hibernated_agents = [a for a in agents if a.status == "hibernated"]

        # TODO: Reactivate agents via Genesis
        # For now, mark as active
        for agent in hibernated_agents:
            agent.status = "active"
            logger.debug(f"Reactivated agent {agent.agent_id}")

        # Update cluster
        cluster.status = ClusterStatus.ACTIVE
        cluster.current_workers = cluster.min_workers
        cluster.started_at = datetime.utcnow()
        cluster.hibernated_at = None

        await self.db.commit()
        await self.db.refresh(cluster)

        logger.info(f"Cluster {cluster_id} reactivated successfully ({len(hibernated_agents)} agents restored)")
        return cluster

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
        logger.info(f"Getting hierarchy for cluster {cluster_id}")

        cluster = await self.get_cluster(cluster_id)
        if not cluster:
            raise ValueError(f"Cluster {cluster_id} not found")

        # Get all agents
        agents = await self.get_cluster_agents(cluster_id)

        if not agents:
            logger.warning(f"No agents found in cluster {cluster_id}")
            return ClusterHierarchyResponse(
                cluster_id=cluster_id,
                cluster_name=cluster.name,
                supervisor=None,
                total_agents=0
            )

        # Build hierarchy map
        agents_by_id = {a.agent_id: a for a in agents}
        agents_by_supervisor = {}

        for agent in agents:
            supervisor_id = agent.supervisor_id
            if supervisor_id:
                if supervisor_id not in agents_by_supervisor:
                    agents_by_supervisor[supervisor_id] = []
                agents_by_supervisor[supervisor_id].append(agent)

        # Find supervisor (no supervisor_id)
        supervisor = next((a for a in agents if a.role == AgentRole.SUPERVISOR), None)

        if not supervisor:
            logger.warning(f"No supervisor found in cluster {cluster_id}")
            return ClusterHierarchyResponse(
                cluster_id=cluster_id,
                cluster_name=cluster.name,
                supervisor=None,
                total_agents=len(agents)
            )

        # Build recursive hierarchy
        def build_node(agent: ClusterAgent) -> Dict[str, Any]:
            subordinates = agents_by_supervisor.get(agent.agent_id, [])
            return {
                "agent_id": agent.agent_id,
                "role": agent.role.value,
                "capabilities": agent.capabilities or [],
                "skills": agent.skills or [],
                "status": agent.status or "active",
                "subordinates": [build_node(sub) for sub in subordinates]
            }

        supervisor_node = build_node(supervisor)

        return ClusterHierarchyResponse(
            cluster_id=cluster_id,
            cluster_name=cluster.name,
            supervisor=supervisor_node,
            total_agents=len(agents)
        )

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

    # ===== BLUEPRINT MANAGEMENT =====

    async def create_blueprint(
        self,
        blueprint_id: str,
        name: str,
        version: str,
        yaml_content: str,
        description: Optional[str] = None,
        tags: Optional[List[str]] = None
    ) -> ClusterBlueprint:
        """Create new blueprint from YAML"""
        # Validate YAML
        try:
            blueprint_dict = self.blueprint_loader.load_from_string(yaml_content)
            self.blueprint_validator.validate(blueprint_dict)
        except Exception as e:
            raise ValueError(f"Invalid blueprint: {e}")

        # Check if blueprint ID already exists
        existing = await self.db.execute(
            select(ClusterBlueprint).where(ClusterBlueprint.id == blueprint_id)
        )
        if existing.scalar_one_or_none():
            raise ValueError(f"Blueprint '{blueprint_id}' already exists")

        # Create blueprint
        blueprint = ClusterBlueprint(
            id=blueprint_id,
            name=name,
            version=version,
            blueprint_yaml=yaml_content,
            description=description,
            tags=tags or [],
            is_active=True
        )

        self.db.add(blueprint)
        await self.db.commit()
        await self.db.refresh(blueprint)

        # Save to file system
        filename = f"{blueprint_id}.yaml"
        self.blueprint_loader.save_to_file(blueprint_dict, filename)

        logger.info(f"Created blueprint: {blueprint_id} v{version}")
        return blueprint

    async def get_blueprint(self, blueprint_id: str) -> Optional[ClusterBlueprint]:
        """Get blueprint by ID"""
        result = await self.db.execute(
            select(ClusterBlueprint).where(ClusterBlueprint.id == blueprint_id)
        )
        return result.scalar_one_or_none()

    async def list_blueprints(
        self,
        active_only: bool = True,
        offset: int = 0,
        limit: int = 50
    ) -> List[ClusterBlueprint]:
        """List blueprints"""
        query = select(ClusterBlueprint)

        if active_only:
            query = query.where(ClusterBlueprint.is_active == True)

        query = query.offset(offset).limit(limit).order_by(ClusterBlueprint.created_at.desc())

        result = await self.db.execute(query)
        return list(result.scalars().all())

    async def update_blueprint(
        self,
        blueprint_id: str,
        yaml_content: Optional[str] = None,
        is_active: Optional[bool] = None
    ) -> ClusterBlueprint:
        """Update blueprint"""
        blueprint = await self.get_blueprint(blueprint_id)
        if not blueprint:
            raise ValueError(f"Blueprint {blueprint_id} not found")

        if yaml_content:
            # Validate
            try:
                blueprint_dict = self.blueprint_loader.load_from_string(yaml_content)
                self.blueprint_validator.validate(blueprint_dict)
            except Exception as e:
                raise ValueError(f"Invalid blueprint: {e}")

            blueprint.blueprint_yaml = yaml_content

        if is_active is not None:
            blueprint.is_active = is_active

        blueprint.updated_at = datetime.utcnow()

        await self.db.commit()
        await self.db.refresh(blueprint)

        logger.info(f"Updated blueprint: {blueprint_id}")
        return blueprint
