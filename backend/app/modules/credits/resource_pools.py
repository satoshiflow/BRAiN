"""Shared Resource Pools - Knowledge sharing and collaborative resources.

Implements Myzel-Hybrid-Charta principles:
- Shared knowledge bases (cooperation incentive)
- Code libraries (reuse promotion)
- Resource contribution tracking (credit bonuses)
- Fair access policies (no hoarding)
"""

import logging
from typing import List, Dict, Optional, Set
from datetime import datetime, timezone
from dataclasses import dataclass
from enum import Enum
from uuid import uuid4

logger = logging.getLogger(__name__)


class ResourceType(str, Enum):
    """Type of shared resource."""

    KNOWLEDGE = "knowledge"          # Knowledge base entry
    CODE = "code"                    # Code snippet/library
    DATA = "data"                    # Processed data/results
    TOOL = "tool"                    # Utility/tool
    TEMPLATE = "template"            # Template/boilerplate


class AccessPolicy(str, Enum):
    """Resource access policy."""

    PUBLIC = "public"                # Anyone can access
    RESTRICTED = "restricted"        # Requires permission
    PRIVATE = "private"              # Owner only


@dataclass
class SharedResource:
    """Shared resource in pool."""

    resource_id: str
    resource_type: ResourceType
    title: str
    description: str
    content: Dict  # Actual resource content
    tags: List[str]

    # Ownership
    contributed_by: str  # Agent ID
    contributed_at: datetime

    # Access control
    access_policy: AccessPolicy
    allowed_agents: Set[str]  # For restricted resources

    # Usage tracking
    access_count: int = 0
    reuse_count: int = 0
    last_accessed: Optional[datetime] = None

    # Quality
    quality_score: float = 1.0  # 0.0-1.0
    verified: bool = False


@dataclass
class ResourceContribution:
    """Resource contribution record."""

    contribution_id: str
    resource_id: str
    contributor_id: str
    contribution_type: str  # "create", "update", "improve"
    timestamp: datetime
    credit_bonus: float


@dataclass
class ResourceUsage:
    """Resource usage record."""

    usage_id: str
    resource_id: str
    user_id: str
    usage_type: str  # "view", "copy", "reuse"
    timestamp: datetime
    value_gained: Optional[float] = None  # 0.0-1.0


class SharedResourcePools:
    """Shared resource pool system for cooperation.

    Myzel-Hybrid Principles:
    - Encourage knowledge sharing (credit bonuses)
    - Promote code reuse (contribution tracking)
    - Fair access (no hoarding, no gatekeeping)
    - Quality over quantity (verified resources)

    Features:
    - Knowledge bases (documentation, best practices)
    - Code libraries (reusable components)
    - Data repositories (processed results)
    - Tool collections (utilities)
    - Template libraries (boilerplates)
    """

    # Contribution bonuses
    CONTRIBUTION_BONUS_CREATE = 10.0      # Create new resource
    CONTRIBUTION_BONUS_UPDATE = 5.0       # Update existing resource
    CONTRIBUTION_BONUS_IMPROVE = 3.0      # Improve resource quality

    # Reuse bonuses (for contributor when others use their resource)
    REUSE_BONUS_PER_USE = 0.5             # Per reuse event
    REUSE_BONUS_MAX_PER_RESOURCE = 50.0   # Maximum total per resource

    # Quality thresholds
    VERIFIED_QUALITY_THRESHOLD = 0.8      # Minimum quality for verification
    MIN_REUSES_FOR_VERIFICATION = 3       # Minimum reuses before verification

    def __init__(self):
        self.resources: Dict[str, SharedResource] = {}
        self.contributions: List[ResourceContribution] = []
        self.usages: List[ResourceUsage] = []
        self.usage_counter = 0
        self.contribution_counter = 0

        logger.info("[SharedResourcePools] Initialized")

    def contribute_resource(
        self,
        contributor_id: str,
        resource_type: ResourceType,
        title: str,
        description: str,
        content: Dict,
        tags: List[str],
        access_policy: AccessPolicy = AccessPolicy.PUBLIC,
        allowed_agents: Optional[Set[str]] = None,
    ) -> Dict:
        """Contribute new resource to pool.

        Myzel-Hybrid: Reward contribution with credit bonus.

        Args:
            contributor_id: Agent contributing the resource
            resource_type: Type of resource
            title: Resource title
            description: Resource description
            content: Resource content
            tags: Tags for search
            access_policy: Access policy
            allowed_agents: Allowed agents (for restricted)

        Returns:
            Contribution result with resource_id and credit_bonus
        """
        resource_id = f"{resource_type.value}_{uuid4().hex[:12]}"

        resource = SharedResource(
            resource_id=resource_id,
            resource_type=resource_type,
            title=title,
            description=description,
            content=content,
            tags=tags,
            contributed_by=contributor_id,
            contributed_at=datetime.now(timezone.utc),
            access_policy=access_policy,
            allowed_agents=allowed_agents or set(),
        )

        self.resources[resource_id] = resource

        # Record contribution
        self.contribution_counter += 1
        contribution_id = f"CONTRIB_{self.contribution_counter:06d}"

        contribution = ResourceContribution(
            contribution_id=contribution_id,
            resource_id=resource_id,
            contributor_id=contributor_id,
            contribution_type="create",
            timestamp=datetime.now(timezone.utc),
            credit_bonus=self.CONTRIBUTION_BONUS_CREATE,
        )

        self.contributions.append(contribution)

        logger.info(
            f"[SharedResourcePools] Resource contributed: {resource_id} by {contributor_id} "
            f"({resource_type.value}, bonus: {self.CONTRIBUTION_BONUS_CREATE} credits)"
        )

        return {
            "resource_id": resource_id,
            "credit_bonus": self.CONTRIBUTION_BONUS_CREATE,
            "contribution_id": contribution_id,
        }

    def search_resources(
        self,
        query: Optional[str] = None,
        resource_type: Optional[ResourceType] = None,
        tags: Optional[List[str]] = None,
        min_quality: float = 0.0,
        verified_only: bool = False,
    ) -> List[Dict]:
        """Search shared resources.

        Args:
            query: Search query (title/description)
            resource_type: Filter by resource type
            tags: Filter by tags (any match)
            min_quality: Minimum quality score
            verified_only: Only verified resources

        Returns:
            List of matching resources
        """
        results = []

        for resource in self.resources.values():
            # Filter by type
            if resource_type and resource.resource_type != resource_type:
                continue

            # Filter by verified
            if verified_only and not resource.verified:
                continue

            # Filter by quality
            if resource.quality_score < min_quality:
                continue

            # Filter by tags
            if tags:
                if not any(tag in resource.tags for tag in tags):
                    continue

            # Filter by query
            if query:
                query_lower = query.lower()
                if query_lower not in resource.title.lower() and \
                   query_lower not in resource.description.lower():
                    continue

            results.append({
                "resource_id": resource.resource_id,
                "resource_type": resource.resource_type.value,
                "title": resource.title,
                "description": resource.description,
                "tags": resource.tags,
                "contributed_by": resource.contributed_by,
                "quality_score": resource.quality_score,
                "verified": resource.verified,
                "access_count": resource.access_count,
                "reuse_count": resource.reuse_count,
            })

        # Sort by quality score (descending)
        results.sort(key=lambda r: r["quality_score"], reverse=True)

        logger.info(
            f"[SharedResourcePools] Search: found {len(results)} resources "
            f"(query: {query}, type: {resource_type}, tags: {tags})"
        )

        return results

    def access_resource(
        self,
        resource_id: str,
        user_id: str,
        usage_type: str = "view",
    ) -> Optional[Dict]:
        """Access shared resource.

        Args:
            resource_id: Resource identifier
            user_id: User accessing resource
            usage_type: Type of usage ("view", "copy", "reuse")

        Returns:
            Resource content or None if access denied

        Raises:
            ValueError: If resource not found
        """
        if resource_id not in self.resources:
            raise ValueError(f"Resource {resource_id} not found")

        resource = self.resources[resource_id]

        # Check access policy
        if resource.access_policy == AccessPolicy.PRIVATE:
            if user_id != resource.contributed_by:
                logger.warning(
                    f"[SharedResourcePools] Access denied: {resource_id} is private "
                    f"(user: {user_id})"
                )
                return None

        elif resource.access_policy == AccessPolicy.RESTRICTED:
            if user_id not in resource.allowed_agents and \
               user_id != resource.contributed_by:
                logger.warning(
                    f"[SharedResourcePools] Access denied: {resource_id} is restricted "
                    f"(user: {user_id})"
                )
                return None

        # Record usage
        self.usage_counter += 1
        usage_id = f"USAGE_{self.usage_counter:06d}"

        usage = ResourceUsage(
            usage_id=usage_id,
            resource_id=resource_id,
            user_id=user_id,
            usage_type=usage_type,
            timestamp=datetime.now(timezone.utc),
        )

        self.usages.append(usage)

        # Update resource stats
        resource.access_count += 1
        resource.last_accessed = datetime.now(timezone.utc)

        if usage_type == "reuse":
            resource.reuse_count += 1

            # Check if resource should be verified
            if not resource.verified:
                if resource.reuse_count >= self.MIN_REUSES_FOR_VERIFICATION and \
                   resource.quality_score >= self.VERIFIED_QUALITY_THRESHOLD:
                    resource.verified = True
                    logger.info(
                        f"[SharedResourcePools] Resource {resource_id} auto-verified "
                        f"(reuses: {resource.reuse_count}, quality: {resource.quality_score})"
                    )

        logger.debug(
            f"[SharedResourcePools] Resource accessed: {resource_id} by {user_id} "
            f"({usage_type})"
        )

        return {
            "resource_id": resource.resource_id,
            "resource_type": resource.resource_type.value,
            "title": resource.title,
            "description": resource.description,
            "content": resource.content,
            "tags": resource.tags,
            "contributed_by": resource.contributed_by,
            "quality_score": resource.quality_score,
            "verified": resource.verified,
        }

    def calculate_contribution_rewards(
        self,
        contributor_id: str,
    ) -> Dict:
        """Calculate contribution rewards for agent.

        Myzel-Hybrid: Reward both direct contribution and indirect value (reuse).

        Args:
            contributor_id: Agent identifier

        Returns:
            Reward breakdown
        """
        # Direct contribution bonuses
        contributions = [
            c for c in self.contributions
            if c.contributor_id == contributor_id
        ]

        direct_bonus = sum(c.credit_bonus for c in contributions)

        # Reuse bonuses (when others use your resources)
        contributed_resources = [
            r for r in self.resources.values()
            if r.contributed_by == contributor_id
        ]

        reuse_bonus = 0.0
        for resource in contributed_resources:
            # Cap reuse bonus per resource
            resource_reuse_bonus = min(
                resource.reuse_count * self.REUSE_BONUS_PER_USE,
                self.REUSE_BONUS_MAX_PER_RESOURCE
            )
            reuse_bonus += resource_reuse_bonus

        total_bonus = direct_bonus + reuse_bonus

        logger.info(
            f"[SharedResourcePools] Contribution rewards for {contributor_id}: "
            f"{total_bonus:.2f} credits (direct: {direct_bonus:.2f}, "
            f"reuse: {reuse_bonus:.2f})"
        )

        return {
            "contributor_id": contributor_id,
            "total_bonus": total_bonus,
            "direct_contribution_bonus": direct_bonus,
            "reuse_bonus": reuse_bonus,
            "resources_contributed": len(contributed_resources),
            "total_reuses": sum(r.reuse_count for r in contributed_resources),
        }

    def get_pool_statistics(self) -> Dict:
        """Get shared resource pool statistics.

        Returns:
            Statistics dictionary
        """
        total_resources = len(self.resources)
        verified_resources = len([r for r in self.resources.values() if r.verified])
        total_contributions = len(self.contributions)
        total_usages = len(self.usages)
        total_reuses = sum(r.reuse_count for r in self.resources.values())

        # Resources by type
        by_type = {}
        for resource in self.resources.values():
            resource_type = resource.resource_type.value
            by_type[resource_type] = by_type.get(resource_type, 0) + 1

        # Top contributors
        contributor_counts = {}
        for resource in self.resources.values():
            contributor_id = resource.contributed_by
            contributor_counts[contributor_id] = contributor_counts.get(contributor_id, 0) + 1

        top_contributors = sorted(
            contributor_counts.items(),
            key=lambda x: x[1],
            reverse=True
        )[:5]

        return {
            "total_resources": total_resources,
            "verified_resources": verified_resources,
            "total_contributions": total_contributions,
            "total_usages": total_usages,
            "total_reuses": total_reuses,
            "resources_by_type": by_type,
            "top_contributors": [
                {"contributor_id": c[0], "resources_count": c[1]}
                for c in top_contributors
            ],
        }


# Global shared resource pools instance
_resource_pools: Optional[SharedResourcePools] = None


def get_resource_pools() -> SharedResourcePools:
    """Get global shared resource pools instance.

    Returns:
        SharedResourcePools instance
    """
    global _resource_pools
    if _resource_pools is None:
        _resource_pools = SharedResourcePools()
    return _resource_pools
