"""
API Schemas for Genesis Agent

This module defines request and response models for the Genesis API.

Author: Genesis Agent System
Version: 2.0.0
Created: 2026-01-02
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field


class AgentCreationRequest(BaseModel):
    """
    Request model for creating a new agent.

    Attributes:
        request_id: Unique request identifier (for idempotency)
        template_name: Name of base template (worker_base, analyst_base, etc.)
        customizations: Optional DNA modifications (whitelist-enforced)

    Example:
        {
            "request_id": "req-abc123def456",
            "template_name": "worker_base",
            "customizations": {
                "metadata.name": "worker_api_specialist",
                "skills[].domains": ["rest_api", "graphql"]
            }
        }
    """
    request_id: str = Field(
        ...,
        description="Unique request identifier (UUID recommended) for idempotency",
        min_length=1,
        max_length=100
    )
    template_name: str = Field(
        ...,
        description="Name of base template (worker_base, analyst_base, builder_base, genesis_base)",
        pattern=r"^[a-z0-9_]+$"
    )
    customizations: Dict[str, Any] = Field(
        default_factory=dict,
        description="Optional DNA customizations (only whitelisted fields allowed)"
    )

    class Config:
        """Pydantic configuration."""
        json_schema_extra = {
            "example": {
                "request_id": "req-abc123def456",
                "template_name": "worker_base",
                "customizations": {
                    "metadata.name": "worker_api_specialist",
                    "skills[].domains": ["rest_api", "graphql"]
                }
            }
        }


class AgentCreationResponse(BaseModel):
    """
    Response model for agent creation.

    Attributes:
        success: Whether creation succeeded
        agent_id: Created agent identifier
        status: Agent status (e.g., "CREATED")
        message: Human-readable message
        cost: Cost in credits
        dna_hash: SHA256 hash of complete DNA (for verification)
        template_hash: SHA256 hash of source template

    Example:
        {
            "success": true,
            "agent_id": "agent-xyz789",
            "status": "CREATED",
            "message": "Agent created successfully",
            "cost": 10,
            "dna_hash": "abc123...",
            "template_hash": "sha256:def456..."
        }
    """
    success: bool
    agent_id: str
    status: str
    message: str
    cost: int
    dna_hash: Optional[str] = None
    template_hash: Optional[str] = None

    class Config:
        """Pydantic configuration."""
        json_schema_extra = {
            "example": {
                "success": True,
                "agent_id": "agent-xyz789abc012",
                "status": "CREATED",
                "message": "Agent created successfully",
                "cost": 10,
                "dna_hash": "abc123def456...",
                "template_hash": "sha256:def456ghi789..."
            }
        }


class GenesisInfoResponse(BaseModel):
    """
    Response model for Genesis system information.

    Attributes:
        name: System name
        version: Genesis version
        enabled: Whether system is enabled (kill switch status)
        templates_available: List of available templates
        reserve_ratio: Budget reserve ratio

    Example:
        {
            "name": "Genesis Agent System",
            "version": "2.0.0",
            "enabled": true,
            "templates_available": ["worker_base", "analyst_base"],
            "reserve_ratio": 0.2
        }
    """
    name: str = "Genesis Agent System"
    version: str = "2.0.0"
    enabled: bool
    templates_available: List[str]
    reserve_ratio: float

    class Config:
        """Pydantic configuration."""
        json_schema_extra = {
            "example": {
                "name": "Genesis Agent System",
                "version": "2.0.0",
                "enabled": True,
                "templates_available": [
                    "worker_base",
                    "analyst_base",
                    "builder_base",
                    "genesis_base"
                ],
                "reserve_ratio": 0.2
            }
        }


class TemplateInfoResponse(BaseModel):
    """
    Response model for template information.

    Attributes:
        template_name: Name of template
        template_hash: SHA256 hash of template
        agent_type: Agent type (Worker, Analyst, etc.)
        description: Template description

    Example:
        {
            "template_name": "worker_base",
            "template_hash": "sha256:abc123...",
            "agent_type": "Worker",
            "description": "Generic worker agent for task execution"
        }
    """
    template_name: str
    template_hash: str
    agent_type: str
    description: Optional[str] = None

    class Config:
        """Pydantic configuration."""
        json_schema_extra = {
            "example": {
                "template_name": "worker_base",
                "template_hash": "sha256:abc123def456...",
                "agent_type": "Worker",
                "description": "Generic worker agent for task execution and integration"
            }
        }


class CustomizationHelpResponse(BaseModel):
    """
    Response model for customization help.

    Attributes:
        allowed_customizations: Dictionary of allowed customizations with schemas

    Example:
        {
            "allowed_customizations": {
                "metadata.name": {
                    "type": "string",
                    "max_length": 100,
                    "pattern": "^[a-z0-9_]+$",
                    "description": "Agent name"
                }
            }
        }
    """
    allowed_customizations: Dict[str, Dict[str, Any]]

    class Config:
        """Pydantic configuration."""
        json_schema_extra = {
            "example": {
                "allowed_customizations": {
                    "metadata.name": {
                        "type": "string",
                        "max_length": 100,
                        "pattern": "^[a-z0-9_]+$",
                        "description": "Agent name (lowercase, alphanumeric + underscore)"
                    },
                    "skills[].domains": {
                        "type": "array",
                        "action": "append",
                        "max_items": 10,
                        "description": "Add skill domains (append-only)"
                    }
                }
            }
        }


class ErrorResponse(BaseModel):
    """
    Standard error response model.

    Attributes:
        error: Error type/code
        message: Error message
        details: Optional additional details

    Example:
        {
            "error": "VALIDATION_ERROR",
            "message": "Invalid DNA schema",
            "details": {"field": "metadata.name", "issue": "too long"}
        }
    """
    error: str
    message: str
    details: Optional[Dict[str, Any]] = None

    class Config:
        """Pydantic configuration."""
        json_schema_extra = {
            "example": {
                "error": "VALIDATION_ERROR",
                "message": "Customization 'ethics_flags' is FORBIDDEN",
                "details": {
                    "field": "ethics_flags",
                    "reason": "Immutable for security/compliance"
                }
            }
        }


class BudgetCheckResponse(BaseModel):
    """
    Response model for budget check.

    Attributes:
        available_credits: Available credits after reserve
        required_credits: Required credits for operation
        has_sufficient_budget: Whether operation can proceed
        reserve_amount: Reserved credits (not available)

    Example:
        {
            "available_credits": 800,
            "required_credits": 10,
            "has_sufficient_budget": true,
            "reserve_amount": 200
        }
    """
    available_credits: int
    required_credits: int
    has_sufficient_budget: bool
    reserve_amount: int

    class Config:
        """Pydantic configuration."""
        json_schema_extra = {
            "example": {
                "available_credits": 800,
                "required_credits": 10,
                "has_sufficient_budget": True,
                "reserve_amount": 200
            }
        }
