"""
Tool System - Pydantic Models

Data models for tool registration, versioning, execution, and accumulation.
"""

from __future__ import annotations

import time
from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field


# ============================================================================
# Enums
# ============================================================================


class ToolSourceType(str, Enum):
    """How a tool is loaded."""
    PYTHON_MODULE = "python_module"      # Local Python callable
    PYTHON_ENTRYPOINT = "python_entrypoint"  # pkg entry point
    HTTP_API = "http_api"                # External REST endpoint
    MCP = "mcp"                          # Model Context Protocol server
    BUILTIN = "builtin"                  # Shipped with BRAIN


class ToolStatus(str, Enum):
    """Lifecycle status of a tool."""
    PENDING = "pending"          # Registered but not yet validated
    VALIDATED = "validated"      # Passed security + policy checks
    ACTIVE = "active"            # Available for use
    SUSPENDED = "suspended"      # Temporarily disabled (immune/policy)
    DEPRECATED = "deprecated"    # Scheduled for removal
    REJECTED = "rejected"        # Failed validation


class ToolSecurityLevel(str, Enum):
    """Security classification for sandbox isolation depth."""
    TRUSTED = "trusted"          # Runs in-process (builtins only)
    STANDARD = "standard"        # Runs in subprocess with timeout
    RESTRICTED = "restricted"    # Runs in subprocess, no network, limited FS
    UNTRUSTED = "untrusted"      # Runs in container (future)


# ============================================================================
# Core Models
# ============================================================================


class ToolCapability(BaseModel):
    """Describes what a tool can do."""
    name: str = Field(..., description="Capability name (e.g. 'web_search', 'file_read')")
    description: str = Field("", description="Human-readable description")
    input_schema: Dict[str, Any] = Field(
        default_factory=dict,
        description="JSON Schema for tool input parameters"
    )
    output_schema: Dict[str, Any] = Field(
        default_factory=dict,
        description="JSON Schema for tool output"
    )


class ToolVersion(BaseModel):
    """Semantic version with changelog."""
    version: str = Field(..., description="Semver string (e.g. '1.2.0')")
    released_at: datetime = Field(default_factory=datetime.utcnow)
    changelog: str = Field("", description="What changed in this version")
    checksum: Optional[str] = Field(None, description="SHA-256 of source artifact")


class ToolSource(BaseModel):
    """Where and how to load a tool."""
    source_type: ToolSourceType
    location: str = Field(
        ...,
        description="Module path, URL, or MCP server address"
    )
    entrypoint: Optional[str] = Field(
        None,
        description="Function/class name within module (for python_module)"
    )
    auth_required: bool = Field(False, description="Whether source needs auth")
    auth_config: Dict[str, Any] = Field(
        default_factory=dict,
        description="Auth configuration (header names, not secrets)"
    )


class ToolDefinition(BaseModel):
    """Complete definition of a registered tool."""
    tool_id: str = Field(..., description="Unique tool identifier")
    name: str = Field(..., description="Human-readable name")
    description: str = Field("", description="What this tool does")
    author: Optional[str] = Field(None, description="Tool author/provider")

    # Classification
    capabilities: List[ToolCapability] = Field(default_factory=list)
    tags: List[str] = Field(default_factory=list, description="Search tags")
    security_level: ToolSecurityLevel = Field(ToolSecurityLevel.STANDARD)

    # Source & Version
    source: ToolSource
    versions: List[ToolVersion] = Field(default_factory=list)
    current_version: str = Field("0.1.0")

    # Status
    status: ToolStatus = Field(ToolStatus.PENDING)
    registered_at: datetime = Field(default_factory=datetime.utcnow)
    last_used_at: Optional[datetime] = None
    use_count: int = Field(0, ge=0)

    # KARMA & Policy integration
    karma_score: float = Field(
        50.0, ge=0.0, le=100.0,
        description="Ethical score from KARMA evaluation (0-100)"
    )
    policy_approved: bool = Field(False, description="Passed Policy Engine check")

    # Metadata
    metadata: Dict[str, Any] = Field(default_factory=dict)

    class Config:
        json_schema_extra = {
            "example": {
                "tool_id": "web_search_v1",
                "name": "Web Search",
                "description": "Search the web for information",
                "security_level": "standard",
                "source": {
                    "source_type": "python_module",
                    "location": "app.modules.tool_system.builtins.web_search",
                    "entrypoint": "search",
                },
                "current_version": "1.0.0",
                "status": "active",
                "karma_score": 85.0,
            }
        }


# ============================================================================
# Execution Models
# ============================================================================


class ToolExecutionRequest(BaseModel):
    """Request to execute a tool."""
    tool_id: str
    parameters: Dict[str, Any] = Field(default_factory=dict)
    timeout_ms: int = Field(30000, ge=1000, le=300000, description="Timeout in ms")
    agent_id: Optional[str] = Field(None, description="Requesting agent")
    mission_id: Optional[str] = Field(None, description="Associated mission")


class ToolExecutionResult(BaseModel):
    """Result of a tool execution."""
    tool_id: str
    success: bool
    output: Any = None
    error: Optional[str] = None
    duration_ms: float = Field(0.0, ge=0.0)
    sandbox_used: bool = False
    timestamp: float = Field(default_factory=time.time)

    # Trace context (NeuroRail integration)
    attempt_id: Optional[str] = None
    mission_id: Optional[str] = None


# ============================================================================
# Accumulation Models
# ============================================================================


class ToolAccumulationRecord(BaseModel):
    """
    Tracks a tool's accumulation history within BRAIN.

    Unlike simple tool-use, accumulation means BRAIN *learns* from tool usage:
    - Success patterns are remembered
    - Failure modes are catalogued
    - Optimal parameter ranges are discovered
    - Cross-tool synergies are identified
    """
    tool_id: str
    total_executions: int = Field(0, ge=0)
    successful_executions: int = Field(0, ge=0)
    failed_executions: int = Field(0, ge=0)
    avg_duration_ms: float = Field(0.0, ge=0.0)

    # Learning
    learned_defaults: Dict[str, Any] = Field(
        default_factory=dict,
        description="Optimal default parameters discovered through usage"
    )
    failure_patterns: List[str] = Field(
        default_factory=list,
        description="Known failure modes"
    )
    synergies: List[str] = Field(
        default_factory=list,
        description="Tool IDs that work well together with this tool"
    )

    # Retention
    karma_trend: List[float] = Field(
        default_factory=list,
        description="Recent KARMA scores (rolling window)"
    )
    retention_score: float = Field(
        50.0, ge=0.0, le=100.0,
        description="Should BRAIN keep accumulating this tool? (0=drop, 100=essential)"
    )
    last_evaluated_at: Optional[datetime] = None


# ============================================================================
# API Request/Response Models
# ============================================================================


class ToolRegisterRequest(BaseModel):
    """Request to register a new tool."""
    name: str
    description: str = ""
    source: ToolSource
    capabilities: List[ToolCapability] = Field(default_factory=list)
    tags: List[str] = Field(default_factory=list)
    security_level: ToolSecurityLevel = Field(ToolSecurityLevel.STANDARD)
    version: str = "0.1.0"
    author: Optional[str] = None
    metadata: Dict[str, Any] = Field(default_factory=dict)


class ToolUpdateRequest(BaseModel):
    """Request to update a tool."""
    description: Optional[str] = None
    tags: Optional[List[str]] = None
    security_level: Optional[ToolSecurityLevel] = None
    status: Optional[ToolStatus] = None
    metadata: Optional[Dict[str, Any]] = None


class ToolListResponse(BaseModel):
    """Response for listing tools."""
    total: int
    tools: List[ToolDefinition]


class ToolSearchRequest(BaseModel):
    """Search tools by capability or tag."""
    query: Optional[str] = None
    tags: Optional[List[str]] = None
    capability: Optional[str] = None
    status: Optional[ToolStatus] = None
    min_karma: Optional[float] = None


class ToolSystemStats(BaseModel):
    """Tool system statistics."""
    total_tools: int = 0
    active_tools: int = 0
    pending_tools: int = 0
    suspended_tools: int = 0
    rejected_tools: int = 0
    total_executions: int = 0
    total_accumulated: int = 0
    avg_karma_score: float = 0.0


class ToolSystemInfo(BaseModel):
    """Tool system module information."""
    name: str = "brain.tool_system"
    version: str = "1.0.0"
    description: str = "Tool Accumulation System - Sprint 6A"
    features: List[str] = Field(default_factory=lambda: [
        "dynamic_loading",
        "versioning",
        "security_sandbox",
        "karma_scoring",
        "policy_integration",
        "accumulation_learning",
        "event_stream_integration",
    ])
