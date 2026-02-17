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
        # TODO: Implement (Max's Task 3.2)
        logger.info("Validating blueprint")

        self.validate_metadata(blueprint.get("metadata", {}))
        self.validate_cluster_config(blueprint.get("cluster", {}))
        self.validate_agents(blueprint.get("agents", []))

        logger.info("Blueprint validation passed")
        return True

    def validate_metadata(self, metadata: Dict[str, Any]) -> bool:
        """Validate metadata section"""
        # TODO: Implement (Max's Task 3.2)
        required = ["id", "name", "version"]
        for field in required:
            if field not in metadata:
                raise ValueError(f"Missing required metadata field: {field}")
        return True

    def validate_cluster_config(self, cluster: Dict[str, Any]) -> bool:
        """Validate cluster configuration"""
        # TODO: Implement (Max's Task 3.2)
        if cluster.get("min_workers", 0) > cluster.get("max_workers", 10):
            raise ValueError("min_workers cannot exceed max_workers")
        return True

    def validate_agents(self, agents: List[Dict[str, Any]]) -> bool:
        """Validate agent definitions"""
        # TODO: Implement (Max's Task 3.2)
        if not agents:
            raise ValueError("Blueprint must define at least one agent")

        # Must have exactly one supervisor
        supervisors = [a for a in agents if a.get("role") == "supervisor"]
        if len(supervisors) != 1:
            raise ValueError("Blueprint must have exactly one supervisor agent")

        return True
