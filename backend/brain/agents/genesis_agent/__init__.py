"""
Genesis Agent System for BRAiN

This package implements the Genesis Agent System Phase 1, which enables
controlled agent creation from DNA templates with comprehensive security,
validation, and auditability.

Main Components:
- dna_schema: Pydantic models for Agent DNA v2.0
- dna_validator: Schema and security validation
- events: Event emission (Redis + Audit)
- config: Configuration and kill switch
- genesis_agent: Core agent creation logic

Usage:
    >>> from brain.agents.genesis_agent import GenesisAgent
    >>> from brain.agents.genesis_agent.config import get_genesis_settings
    >>>
    >>> settings = get_genesis_settings()
    >>> genesis = GenesisAgent(...)
    >>>
    >>> dna = await genesis.create_agent(
    ...     request_id="req-123",
    ...     template_name="worker_base",
    ...     customizations={"metadata.name": "worker_01"}
    ... )

Author: Genesis Agent System
Version: 2.0.0
Created: 2026-01-02
"""

from .config import GenesisSettings, get_genesis_settings, reset_genesis_settings
from .dna_schema import (
    AgentDNA,
    AgentStatus,
    AgentTraits,
    AgentType,
    BehaviorModules,
    Capabilities,
    DNAMetadata,
    EthicsFlags,
    MissionAffinity,
    ResourceLimits,
    RuntimeConfig,
    Skill,
)
from .dna_validator import DNAValidator, ValidationError
from .events import GenesisEvents, SimpleAuditLog
from .genesis_agent import GenesisAgent, InMemoryRegistry, InMemoryBudget

__all__ = [
    # Core classes
    "GenesisAgent",
    # DNA Schema
    "AgentDNA",
    "DNAMetadata",
    "AgentType",
    "AgentStatus",
    "Skill",
    "AgentTraits",
    "BehaviorModules",
    "EthicsFlags",
    "Capabilities",
    "RuntimeConfig",
    "ResourceLimits",
    "MissionAffinity",
    # Validation
    "DNAValidator",
    "ValidationError",
    # Events
    "GenesisEvents",
    "SimpleAuditLog",
    # Configuration
    "GenesisSettings",
    "get_genesis_settings",
    "reset_genesis_settings",
]

__version__ = "2.0.0"
