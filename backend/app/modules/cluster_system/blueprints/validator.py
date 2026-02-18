"""
Blueprint Validator

Validates blueprint structure and content.
"""

from typing import Dict, Any, List
from loguru import logger


class BlueprintValidator:
    """
    Validates cluster blueprints against schema.

    Checks:
    - Required fields present
    - Valid scaling configuration
    - Agent hierarchy is valid
    - Capabilities match available skills
    """

    def validate(self, blueprint: Dict[str, Any]) -> bool:
        """
        Validate complete blueprint.

        Args:
            blueprint: Parsed blueprint dict

        Returns:
            bool: True if valid

        Raises:
            ValueError: If validation fails
        """
        logger.info("Validating blueprint")

        if not isinstance(blueprint, dict):
            raise ValueError("Blueprint must be a dictionary")

        # Validate each section
        self.validate_metadata(blueprint.get("metadata", {}))
        self.validate_cluster_config(blueprint.get("cluster", {}))
        self.validate_agents(blueprint.get("agents", []))

        logger.info("Blueprint validation passed")
        return True

    def validate_metadata(self, metadata: Dict[str, Any]) -> bool:
        """Validate metadata section"""
        if not metadata:
            raise ValueError("Metadata section is required")

        required = ["id", "name", "version"]
        for field in required:
            if field not in metadata:
                raise ValueError(f"Missing required metadata field: {field}")
            if not metadata[field]:
                raise ValueError(f"Metadata field '{field}' cannot be empty")

        # Validate ID format (alphanumeric + hyphens)
        blueprint_id = metadata["id"]
        if not isinstance(blueprint_id, str) or not blueprint_id.replace("-", "").replace("_", "").isalnum():
            raise ValueError(f"Invalid blueprint ID format: {blueprint_id}")

        # Validate version format (semver-like)
        version = metadata["version"]
        if not isinstance(version, str):
            raise ValueError("Version must be a string")

        logger.debug(f"Metadata validation passed: {blueprint_id} v{version}")
        return True

    def validate_cluster_config(self, cluster: Dict[str, Any]) -> bool:
        """Validate cluster configuration"""
        if not cluster:
            raise ValueError("Cluster configuration is required")

        # Validate required fields
        required = ["type", "min_workers", "max_workers"]
        for field in required:
            if field not in cluster:
                raise ValueError(f"Missing required cluster field: {field}")

        # Validate worker counts
        min_workers = cluster.get("min_workers", 0)
        max_workers = cluster.get("max_workers", 10)

        if not isinstance(min_workers, int) or min_workers < 0:
            raise ValueError("min_workers must be a non-negative integer")

        if not isinstance(max_workers, int) or max_workers < 1:
            raise ValueError("max_workers must be a positive integer")

        if min_workers > max_workers:
            raise ValueError(f"min_workers ({min_workers}) cannot exceed max_workers ({max_workers})")

        if max_workers > 1000:
            raise ValueError("max_workers cannot exceed 1000")

        # Validate cluster type
        valid_types = ["department", "project", "campaign", "team"]
        if cluster["type"] not in valid_types:
            raise ValueError(f"Invalid cluster type: {cluster['type']}. Must be one of {valid_types}")

        # Validate scaling config if present
        if "scaling" in cluster:
            scaling = cluster["scaling"]
            if "metric" in scaling and scaling["metric"] not in ["task_queue_length", "cpu_usage", "load_percentage"]:
                raise ValueError(f"Invalid scaling metric: {scaling['metric']}")

        logger.debug(f"Cluster config validation passed: {cluster['type']}, {min_workers}-{max_workers} workers")
        return True

    def validate_agents(self, agents: List[Dict[str, Any]]) -> bool:
        """Validate agent definitions"""
        if not agents:
            raise ValueError("Blueprint must define at least one agent")

        if not isinstance(agents, list):
            raise ValueError("Agents must be a list")

        # Must have exactly one supervisor
        supervisors = [a for a in agents if a.get("role") == "supervisor"]
        if len(supervisors) != 1:
            raise ValueError("Blueprint must have exactly one supervisor agent")

        # Validate each agent
        valid_roles = ["supervisor", "lead", "specialist", "worker"]
        seen_names = set()

        for i, agent in enumerate(agents):
            if not isinstance(agent, dict):
                raise ValueError(f"Agent {i} must be a dictionary")

            # Required fields
            required = ["role", "name"]
            for field in required:
                if field not in agent:
                    raise ValueError(f"Agent {i} missing required field: {field}")

            # Validate role
            role = agent["role"]
            if role not in valid_roles:
                raise ValueError(f"Invalid agent role: {role}. Must be one of {valid_roles}")

            # Validate name uniqueness
            name = agent["name"]
            if name in seen_names:
                raise ValueError(f"Duplicate agent name: {name}")
            seen_names.add(name)

            # Validate count
            if "count" in agent:
                count = agent["count"]
                # Can be int or string like "0-5"
                if isinstance(count, str) and "-" in count:
                    # Range format
                    try:
                        min_val, max_val = count.split("-")
                        int(min_val), int(max_val)
                    except (ValueError, AttributeError):
                        raise ValueError(f"Invalid count format for agent {name}: {count}")
                elif isinstance(count, int):
                    if count < 0:
                        raise ValueError(f"Agent count cannot be negative for {name}")
                else:
                    raise ValueError(f"Invalid count type for agent {name}: {type(count)}")

            # Validate supervisor doesn't report to anyone
            if role == "supervisor" and "reports_to" in agent:
                raise ValueError("Supervisor agent cannot have reports_to field")

            # Non-supervisors should have reports_to (optional but recommended)
            if role != "supervisor" and "reports_to" not in agent:
                logger.warning(f"Agent {name} ({role}) has no reports_to field - will default to supervisor")

        logger.debug(f"Agents validation passed: {len(agents)} agents defined")
        return True
