"""
NeuroRail Identity Service.

Manages the creation and retrieval of trace chain entities:
- Mission, Plan, Job, Attempt, Resource identities
- Hierarchical trace chain lookup
- Redis storage for fast access (24h retention)
"""

from __future__ import annotations
import json
from typing import Optional, Dict, Any, List
from datetime import datetime, timedelta
from loguru import logger
import redis.asyncio as redis

from app.core.redis_client import get_redis
from app.modules.neurorail.identity.schemas import (
    MissionIdentity,
    PlanIdentity,
    JobIdentity,
    AttemptIdentity,
    ResourceIdentity,
    TraceChain,
    CreateMissionRequest,
    CreatePlanRequest,
    CreateJobRequest,
    CreateAttemptRequest,
    CreateResourceRequest,
)


class IdentityService:
    """
    Service for managing NeuroRail entity identities.

    Provides:
    - UUID generation with prefixes (m_, p_, j_, a_, r_)
    - Redis storage with 24h TTL
    - Hierarchical trace chain reconstruction
    """

    # Redis key prefixes
    KEY_PREFIX_MISSION = "neurorail:mission:"
    KEY_PREFIX_PLAN = "neurorail:plan:"
    KEY_PREFIX_JOB = "neurorail:job:"
    KEY_PREFIX_ATTEMPT = "neurorail:attempt:"
    KEY_PREFIX_RESOURCE = "neurorail:resource:"

    # Redis TTL (24 hours in seconds)
    REDIS_TTL = 24 * 60 * 60

    def __init__(self):
        self.redis: Optional[redis.Redis] = None

    async def _get_redis(self) -> redis.Redis:
        """Get Redis client (lazy initialization)."""
        if self.redis is None:
            self.redis = await get_redis()
        return self.redis

    # ========================================================================
    # Mission Identity
    # ========================================================================

    async def create_mission(
        self,
        request: CreateMissionRequest
    ) -> MissionIdentity:
        """
        Create a new mission identity.

        Args:
            request: Mission creation request

        Returns:
            Created mission identity
        """
        mission = MissionIdentity(
            parent_mission_id=request.parent_mission_id,
            tags=request.tags
        )

        # Store in Redis
        redis_client = await self._get_redis()
        key = f"{self.KEY_PREFIX_MISSION}{mission.mission_id}"

        await redis_client.hset(
            key,
            mapping={
                "mission_id": mission.mission_id,
                "created_at": mission.created_at.isoformat(),
                "parent_mission_id": mission.parent_mission_id or "",
                "tags": json.dumps(mission.tags),
            }
        )
        await redis_client.expire(key, self.REDIS_TTL)

        logger.info(f"Created mission identity: {mission.mission_id}")
        return mission

    async def get_mission(self, mission_id: str) -> Optional[MissionIdentity]:
        """Get mission identity by ID."""
        redis_client = await self._get_redis()
        key = f"{self.KEY_PREFIX_MISSION}{mission_id}"

        data = await redis_client.hgetall(key)
        if not data:
            return None

        return MissionIdentity(
            mission_id=data["mission_id"],
            created_at=datetime.fromisoformat(data["created_at"]),
            parent_mission_id=data["parent_mission_id"] or None,
            tags=json.loads(data["tags"]) if data.get("tags") else {},
        )

    # ========================================================================
    # Plan Identity
    # ========================================================================

    async def create_plan(
        self,
        request: CreatePlanRequest
    ) -> PlanIdentity:
        """
        Create a new plan identity.

        Args:
            request: Plan creation request

        Returns:
            Created plan identity
        """
        # Verify mission exists
        mission = await self.get_mission(request.mission_id)
        if not mission:
            raise ValueError(f"Mission {request.mission_id} not found")

        plan = PlanIdentity(
            mission_id=request.mission_id,
            plan_type=request.plan_type,
            metadata=request.metadata
        )

        # Store in Redis
        redis_client = await self._get_redis()
        key = f"{self.KEY_PREFIX_PLAN}{plan.plan_id}"

        await redis_client.hset(
            key,
            mapping={
                "plan_id": plan.plan_id,
                "mission_id": plan.mission_id,
                "created_at": plan.created_at.isoformat(),
                "plan_type": plan.plan_type,
                "metadata": json.dumps(plan.metadata),
            }
        )
        await redis_client.expire(key, self.REDIS_TTL)

        logger.info(f"Created plan identity: {plan.plan_id} for mission {plan.mission_id}")
        return plan

    async def get_plan(self, plan_id: str) -> Optional[PlanIdentity]:
        """Get plan identity by ID."""
        redis_client = await self._get_redis()
        key = f"{self.KEY_PREFIX_PLAN}{plan_id}"

        data = await redis_client.hgetall(key)
        if not data:
            return None

        return PlanIdentity(
            plan_id=data["plan_id"],
            mission_id=data["mission_id"],
            created_at=datetime.fromisoformat(data["created_at"]),
            plan_type=data["plan_type"],
            metadata=json.loads(data["metadata"]) if data.get("metadata") else {},
        )

    # ========================================================================
    # Job Identity
    # ========================================================================

    async def create_job(
        self,
        request: CreateJobRequest
    ) -> JobIdentity:
        """
        Create a new job identity.

        Args:
            request: Job creation request

        Returns:
            Created job identity
        """
        # Verify plan exists
        plan = await self.get_plan(request.plan_id)
        if not plan:
            raise ValueError(f"Plan {request.plan_id} not found")

        job = JobIdentity(
            plan_id=request.plan_id,
            job_type=request.job_type,
            dependencies=request.dependencies,
            metadata=request.metadata
        )

        # Store in Redis
        redis_client = await self._get_redis()
        key = f"{self.KEY_PREFIX_JOB}{job.job_id}"

        await redis_client.hset(
            key,
            mapping={
                "job_id": job.job_id,
                "plan_id": job.plan_id,
                "created_at": job.created_at.isoformat(),
                "job_type": job.job_type,
                "dependencies": json.dumps(job.dependencies),
                "metadata": json.dumps(job.metadata),
            }
        )
        await redis_client.expire(key, self.REDIS_TTL)

        logger.info(f"Created job identity: {job.job_id} of type {job.job_type}")
        return job

    async def get_job(self, job_id: str) -> Optional[JobIdentity]:
        """Get job identity by ID."""
        redis_client = await self._get_redis()
        key = f"{self.KEY_PREFIX_JOB}{job_id}"

        data = await redis_client.hgetall(key)
        if not data:
            return None

        return JobIdentity(
            job_id=data["job_id"],
            plan_id=data["plan_id"],
            created_at=datetime.fromisoformat(data["created_at"]),
            job_type=data["job_type"],
            dependencies=json.loads(data["dependencies"]) if data.get("dependencies") else [],
            metadata=json.loads(data["metadata"]) if data.get("metadata") else {},
        )

    # ========================================================================
    # Attempt Identity
    # ========================================================================

    async def create_attempt(
        self,
        request: CreateAttemptRequest
    ) -> AttemptIdentity:
        """
        Create a new attempt identity.

        Args:
            request: Attempt creation request

        Returns:
            Created attempt identity
        """
        # Verify job exists
        job = await self.get_job(request.job_id)
        if not job:
            raise ValueError(f"Job {request.job_id} not found")

        attempt = AttemptIdentity(
            job_id=request.job_id,
            attempt_number=request.attempt_number,
            metadata=request.metadata
        )

        # Store in Redis
        redis_client = await self._get_redis()
        key = f"{self.KEY_PREFIX_ATTEMPT}{attempt.attempt_id}"

        await redis_client.hset(
            key,
            mapping={
                "attempt_id": attempt.attempt_id,
                "job_id": attempt.job_id,
                "attempt_number": str(attempt.attempt_number),
                "created_at": attempt.created_at.isoformat(),
                "metadata": json.dumps(attempt.metadata),
            }
        )
        await redis_client.expire(key, self.REDIS_TTL)

        logger.info(f"Created attempt identity: {attempt.attempt_id} (attempt #{attempt.attempt_number})")
        return attempt

    async def get_attempt(self, attempt_id: str) -> Optional[AttemptIdentity]:
        """Get attempt identity by ID."""
        redis_client = await self._get_redis()
        key = f"{self.KEY_PREFIX_ATTEMPT}{attempt_id}"

        data = await redis_client.hgetall(key)
        if not data:
            return None

        return AttemptIdentity(
            attempt_id=data["attempt_id"],
            job_id=data["job_id"],
            attempt_number=int(data["attempt_number"]),
            created_at=datetime.fromisoformat(data["created_at"]),
            metadata=json.loads(data["metadata"]) if data.get("metadata") else {},
        )

    # ========================================================================
    # Resource Identity
    # ========================================================================

    async def create_resource(
        self,
        request: CreateResourceRequest
    ) -> ResourceIdentity:
        """
        Create a new resource identity.

        Args:
            request: Resource creation request

        Returns:
            Created resource identity
        """
        # Verify attempt exists
        attempt = await self.get_attempt(request.attempt_id)
        if not attempt:
            raise ValueError(f"Attempt {request.attempt_id} not found")

        resource = ResourceIdentity(
            attempt_id=request.attempt_id,
            resource_type=request.resource_type,
            metadata=request.metadata
        )

        # Store in Redis
        redis_client = await self._get_redis()
        key = f"{self.KEY_PREFIX_RESOURCE}{resource.resource_uuid}"

        await redis_client.hset(
            key,
            mapping={
                "resource_uuid": resource.resource_uuid,
                "attempt_id": resource.attempt_id,
                "resource_type": resource.resource_type,
                "created_at": resource.created_at.isoformat(),
                "metadata": json.dumps(resource.metadata),
            }
        )
        await redis_client.expire(key, self.REDIS_TTL)

        logger.info(f"Created resource identity: {resource.resource_uuid} of type {resource.resource_type}")
        return resource

    async def get_resource(self, resource_uuid: str) -> Optional[ResourceIdentity]:
        """Get resource identity by UUID."""
        redis_client = await self._get_redis()
        key = f"{self.KEY_PREFIX_RESOURCE}{resource_uuid}"

        data = await redis_client.hgetall(key)
        if not data:
            return None

        return ResourceIdentity(
            resource_uuid=data["resource_uuid"],
            attempt_id=data["attempt_id"],
            resource_type=data["resource_type"],
            created_at=datetime.fromisoformat(data["created_at"]),
            metadata=json.loads(data["metadata"]) if data.get("metadata") else {},
        )

    # ========================================================================
    # Trace Chain Reconstruction
    # ========================================================================

    async def get_trace_chain(
        self,
        entity_type: str,
        entity_id: str
    ) -> Optional[TraceChain]:
        """
        Reconstruct complete trace chain from any entity.

        Args:
            entity_type: Entity type (mission, plan, job, attempt, resource)
            entity_id: Entity ID

        Returns:
            Complete trace chain or None if entity not found
        """
        trace = TraceChain()

        # Start from the given entity and walk up the hierarchy
        if entity_type == "mission":
            mission = await self.get_mission(entity_id)
            if not mission:
                return None
            trace.mission = mission

        elif entity_type == "plan":
            plan = await self.get_plan(entity_id)
            if not plan:
                return None
            trace.plan = plan
            trace.mission = await self.get_mission(plan.mission_id)

        elif entity_type == "job":
            job = await self.get_job(entity_id)
            if not job:
                return None
            trace.job = job
            trace.plan = await self.get_plan(job.plan_id)
            if trace.plan:
                trace.mission = await self.get_mission(trace.plan.mission_id)

        elif entity_type == "attempt":
            attempt = await self.get_attempt(entity_id)
            if not attempt:
                return None
            trace.attempt = attempt
            trace.job = await self.get_job(attempt.job_id)
            if trace.job:
                trace.plan = await self.get_plan(trace.job.plan_id)
                if trace.plan:
                    trace.mission = await self.get_mission(trace.plan.mission_id)

        elif entity_type == "resource":
            resource = await self.get_resource(entity_id)
            if not resource:
                return None
            trace.resource = resource
            trace.attempt = await self.get_attempt(resource.attempt_id)
            if trace.attempt:
                trace.job = await self.get_job(trace.attempt.job_id)
                if trace.job:
                    trace.plan = await self.get_plan(trace.job.plan_id)
                    if trace.plan:
                        trace.mission = await self.get_mission(trace.plan.mission_id)

        else:
            raise ValueError(f"Unknown entity type: {entity_type}")

        return trace


# Singleton instance
_identity_service: Optional[IdentityService] = None


def get_identity_service() -> IdentityService:
    """Get singleton identity service instance."""
    global _identity_service
    if _identity_service is None:
        _identity_service = IdentityService()
    return _identity_service
