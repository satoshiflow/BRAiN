"""
Configuration for Genesis Agent System

This module provides configuration and settings for the Genesis Agent including:
- Kill switch control
- Budget reserve ratio
- Cost estimation
- Template directory location
- Feature flags

Author: Genesis Agent System
Version: 2.0.0
Created: 2026-01-02
"""

from __future__ import annotations

import os
from pathlib import Path
from typing import Dict, Optional

from pydantic import Field
from pydantic_settings import BaseSettings


class GenesisSettings(BaseSettings):
    """
    Genesis Agent configuration settings.

    Settings can be overridden via environment variables with GENESIS_ prefix.

    Attributes:
        enabled: Kill switch (disable all agent creation if False)
        reserve_ratio: Budget reserve percentage (0.2 = 20%)
        templates_dir: Path to DNA templates directory
        max_agents_per_hour: Rate limit for agent creation
        require_admin_auth: Require SYSTEM_ADMIN role (should always be True)
        enable_quarantine: Enable quarantine for new agents (Phase 3)
        enable_governor_approval: Enable Governor approval (Phase 3)

    Example:
        >>> settings = GenesisSettings()
        >>> if not settings.enabled:
        ...     raise HTTPException(503, "Genesis system disabled")
    """

    # Kill Switch (CRITICAL)
    enabled: bool = Field(
        default=True,
        description="Master kill switch for Genesis Agent. Set to False to disable all agent creation."
    )

    # Budget Control
    reserve_ratio: float = Field(
        default=0.2,
        ge=0.0,
        le=1.0,
        description="Budget reserve ratio (0.2 = 20%). System protects this % of available credits."
    )

    # Templates
    templates_dir: Optional[str] = Field(
        default=None,
        description="Path to DNA templates directory. Defaults to ./templates/"
    )

    # Rate Limiting
    max_agents_per_hour: int = Field(
        default=10,
        ge=1,
        description="Maximum number of agents that can be created per hour"
    )

    # Authentication
    require_admin_auth: bool = Field(
        default=True,
        description="Require SYSTEM_ADMIN role for agent creation (should always be True)"
    )

    # Phase 2+ Features (not implemented in Phase 1)
    enable_quarantine: bool = Field(
        default=False,
        description="Enable quarantine for newly created agents (Phase 3)"
    )

    enable_governor_approval: bool = Field(
        default=False,
        description="Enable Governor approval before agent creation (Phase 3)"
    )

    # Cost Estimation
    base_creation_cost: int = Field(
        default=10,
        ge=0,
        description="Base cost in credits for creating an agent"
    )

    # Logging
    log_dna_to_file: bool = Field(
        default=True,
        description="Log complete DNA to file for audit trail"
    )

    dna_log_dir: Optional[str] = Field(
        default=None,
        description="Directory for DNA logs. Defaults to ./storage/dna_logs/"
    )

    class Config:
        """Pydantic configuration."""
        env_prefix = "GENESIS_"
        env_file = ".env"
        env_file_encoding = "utf-8"

    def get_templates_dir(self) -> Path:
        """
        Get templates directory path.

        Returns:
            Path: Absolute path to templates directory

        Example:
            >>> settings = GenesisSettings()
            >>> templates_path = settings.get_templates_dir()
        """
        if self.templates_dir:
            return Path(self.templates_dir).absolute()

        # Default: relative to this file
        module_dir = Path(__file__).parent
        return (module_dir / "templates").absolute()

    def get_dna_log_dir(self) -> Path:
        """
        Get DNA log directory path.

        Returns:
            Path: Absolute path to DNA log directory

        Example:
            >>> settings = GenesisSettings()
            >>> log_path = settings.get_dna_log_dir()
        """
        if self.dna_log_dir:
            return Path(self.dna_log_dir).absolute()

        # Default: project storage directory
        return Path("storage/dna_logs").absolute()

    def check_enabled(self) -> None:
        """
        Check if Genesis system is enabled.

        Raises:
            RuntimeError: If kill switch is disabled

        Example:
            >>> settings = GenesisSettings()
            >>> settings.check_enabled()  # Raises if disabled
        """
        if not self.enabled:
            raise RuntimeError(
                "Genesis Agent system is DISABLED by configuration. "
                "Set GENESIS_ENABLED=true to enable agent creation."
            )

    def estimate_cost(self, template_name: str) -> int:
        """
        Estimate cost for creating an agent from template.

        Args:
            template_name: Name of template

        Returns:
            int: Estimated cost in credits

        Note:
            In Phase 1, this is a simple fixed cost.
            Phase 2+ will implement dynamic cost based on template complexity.

        Example:
            >>> settings = GenesisSettings()
            >>> cost = settings.estimate_cost("worker_base")
            >>> print(cost)
            10
        """
        # Phase 1: Simple fixed cost
        # Phase 2+: Could analyze template to calculate cost
        return self.base_creation_cost


# Singleton settings instance
_settings: Optional[GenesisSettings] = None


def get_genesis_settings() -> GenesisSettings:
    """
    Get Genesis settings singleton.

    Returns:
        GenesisSettings: Global settings instance

    Example:
        >>> settings = get_genesis_settings()
        >>> if settings.enabled:
        ...     # Create agent
        ...     pass
    """
    global _settings
    if _settings is None:
        _settings = GenesisSettings()
    return _settings


def reset_genesis_settings() -> None:
    """
    Reset settings singleton (for testing).

    Example:
        >>> reset_genesis_settings()
        >>> settings = get_genesis_settings()  # Fresh instance
    """
    global _settings
    _settings = None


# ============================================================================
# Cost Constants
# ============================================================================

# Template complexity multipliers (Phase 2+)
TEMPLATE_COST_MULTIPLIERS: Dict[str, float] = {
    "worker_base": 1.0,     # Base cost
    "analyst_base": 1.5,    # More complex
    "builder_base": 2.0,    # Most complex
    "genesis_base": 3.0,    # Highest complexity
}


def get_template_cost(template_name: str, base_cost: int = 10) -> int:
    """
    Calculate cost for specific template.

    Args:
        template_name: Name of template
        base_cost: Base cost in credits

    Returns:
        int: Estimated cost for this template

    Example:
        >>> cost = get_template_cost("builder_base", base_cost=10)
        >>> print(cost)
        20
    """
    multiplier = TEMPLATE_COST_MULTIPLIERS.get(template_name, 1.0)
    return int(base_cost * multiplier)
