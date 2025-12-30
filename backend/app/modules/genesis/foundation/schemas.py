"""
Foundation Layer Schemas

Ethics and safety validation data structures.
"""

from __future__ import annotations

from datetime import datetime
from enum import Enum
from typing import Any, Callable, Dict, List, Optional

from pydantic import BaseModel, Field


class ValidationSeverity(str, Enum):
    """Severity levels for validation issues."""

    INFO = "info"  # Informational only
    WARNING = "warning"  # Potential issue
    CRITICAL = "critical"  # Blocks action


class ValidationAction(str, Enum):
    """Actions taken on validation failure."""

    ALLOW = "allow"  # Allow action to proceed
    WARN = "warn"  # Allow but log warning
    BLOCK = "block"  # Prevent action


class EthicsRule(BaseModel):
    """
    Ethics rule for agent validation.

    Rules define constraints that agents must satisfy
    for creation, mutation, or specific actions.
    """

    id: str  # Unique rule identifier
    name: str  # Human-readable name
    description: str  # Detailed description
    severity: ValidationSeverity = ValidationSeverity.CRITICAL
    action: ValidationAction = ValidationAction.BLOCK
    enabled: bool = True

    # Validator function signature: (context: Dict[str, Any]) -> bool
    # Returns True if rule is satisfied, False if violated
    # Note: Cannot be serialized, set at runtime
    validator: Optional[Callable[[Dict[str, Any]], bool]] = None

    class Config:
        arbitrary_types_allowed = True  # Allow callable
        json_encoders = {
            Callable: lambda v: None  # Don't serialize callables
        }


class FoundationValidationResult(BaseModel):
    """
    Result of Foundation layer validation.

    Contains outcome and details of all rule evaluations.
    """

    allowed: bool  # Overall result: can action proceed?
    violations: List[str] = Field(default_factory=list)  # Critical violations
    warnings: List[str] = Field(default_factory=list)  # Non-blocking warnings
    info: List[str] = Field(default_factory=list)  # Informational messages
    timestamp: datetime = Field(default_factory=datetime.utcnow)
    context: Dict[str, Any] = Field(default_factory=dict)  # Validation context

    @property
    def has_violations(self) -> bool:
        """Check if any violations exist."""
        return len(self.violations) > 0

    @property
    def has_warnings(self) -> bool:
        """Check if any warnings exist."""
        return len(self.warnings) > 0

    def add_violation(self, message: str):
        """Add critical violation."""
        self.violations.append(message)
        self.allowed = False

    def add_warning(self, message: str):
        """Add warning."""
        self.warnings.append(message)

    def add_info(self, message: str):
        """Add info message."""
        self.info.append(message)


class AgentCreationContext(BaseModel):
    """Context for agent creation validation."""

    blueprint_id: str
    agent_id: str
    traits: Dict[str, Any]  # Trait ID -> value
    config: Dict[str, Any]  # Agent configuration
    tools: List[str] = Field(default_factory=list)
    permissions: List[str] = Field(default_factory=list)


class MutationContext(BaseModel):
    """Context for mutation validation."""

    agent_id: str
    current_traits: Dict[str, Any]
    proposed_traits: Dict[str, Any]
    mutations: List[Dict[str, Any]] = Field(default_factory=list)


class ActionContext(BaseModel):
    """Context for action validation."""

    agent_id: str
    action: str
    parameters: Dict[str, Any] = Field(default_factory=dict)
    environment: Dict[str, Any] = Field(default_factory=dict)
