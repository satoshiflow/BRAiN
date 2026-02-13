"""
Fred Bridge Schemas (Simplified for OpenAPI compatibility)

Ticket and Patch Artifact schemas for the Fred Bridge system.
"""

from __future__ import annotations

from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional
from uuid import UUID

from pydantic import BaseModel, Field


# =============================================================================
# Enums
# =============================================================================

class TicketType(str, Enum):
    INCIDENT = "incident"
    FEATURE = "feature"
    REFACTOR = "refactor"
    SECURITY = "security"


class TicketSeverity(str, Enum):
    S1 = "S1"
    S2 = "S2"
    S3 = "S3"
    S4 = "S4"


class TicketStatus(str, Enum):
    OPEN = "open"
    TRIAGED = "triaged"
    IN_ANALYSIS = "in_analysis"
    PATCH_SUBMITTED = "patch_submitted"
    ACCEPTED = "accepted"
    CLOSED = "closed"


class PatchStatus(str, Enum):
    PROPOSED = "proposed"
    IN_REVIEW = "in_review"
    APPROVED = "approved"
    STAGING = "staging"
    CANARY = "canary"
    PRODUCTION = "production"
    ROLLED_BACK = "rolled_back"
    REJECTED = "rejected"


# =============================================================================
# Simplified Sub-Schemas (no nested ForwardRefs)
# =============================================================================

class ConstraintConfig(BaseModel):
    model_config = {"extra": "allow"}
    time_limit_hours: int = 24
    freeze_deployments: bool = False


class Symptoms(BaseModel):
    model_config = {"extra": "allow"}
    error_rate: str = ""
    latency_ms: str = ""
    user_reports: int = 0


class Links(BaseModel):
    model_config = {"extra": "allow"}
    logs: str = ""
    traces: str = ""
    metrics_dashboard: str = ""


class TestsConfig(BaseModel):
    model_config = {"extra": "allow"}
    added_or_updated: List[str] = Field(default_factory=list)
    evidence: str = ""


class RiskAssessment(BaseModel):
    model_config = {"extra": "allow"}
    risk_level: str = "medium"
    blast_radius: str = "single module"
    rollback_plan: str = ""


class SecurityImpact(BaseModel):
    model_config = {"extra": "allow"}
    summary: str = ""
    secrets_touched: bool = False


class ApprovalsConfig(BaseModel):
    model_config = {"extra": "allow"}
    governor_required: bool = True
    human_required: bool = False


class DeploymentPlan(BaseModel):
    model_config = {"extra": "allow"}
    staging: Dict[str, Any] = Field(default_factory=dict)
    canary: Dict[str, Any] = Field(default_factory=dict)
    production: Dict[str, Any] = Field(default_factory=dict)


# =============================================================================
# Ticket Schemas
# =============================================================================

class FredTicketCreate(BaseModel):
    """Create a new ticket"""
    type: str = "incident"  # incident|feature|refactor|security
    severity: str = "S4"    # S1|S2|S3|S4
    component: str
    summary: str
    environment: str = "staging"
    constraints: Dict[str, Any] = Field(default_factory=dict)
    observed_symptoms: Dict[str, Any] = Field(default_factory=dict)
    expected_outcome: str = ""
    links: Dict[str, Any] = Field(default_factory=dict)
    metadata: Dict[str, Any] = Field(default_factory=dict)


class FredTicketUpdate(BaseModel):
    """Update ticket fields"""
    status: Optional[str] = None
    severity: Optional[str] = None
    summary: Optional[str] = None
    expected_outcome: Optional[str] = None
    metadata: Optional[Dict[str, Any]] = None


class FredTicket(BaseModel):
    """Complete ticket response"""
    id: UUID
    ticket_id: str
    type: str
    severity: str
    component: str
    summary: str
    status: str
    environment: str
    reporter: str
    constraints: Dict[str, Any]
    observed_symptoms: Dict[str, Any]
    expected_outcome: str
    links: Dict[str, Any]
    metadata: Dict[str, Any]
    created_at: datetime
    updated_at: datetime


# =============================================================================
# Patch Artifact Schemas
# =============================================================================

class PatchArtifactCreate(BaseModel):
    """Submit a new patch"""
    ticket_id: str
    target_repo: str = "BRAiN"
    target_paths: List[str] = Field(default_factory=list)
    git_diff_excerpt: str = ""
    tests: Dict[str, Any] = Field(default_factory=dict)
    risk_assessment: Dict[str, Any] = Field(default_factory=dict)
    security_impact: Dict[str, Any] = Field(default_factory=dict)
    deployment_plan: Dict[str, Any] = Field(default_factory=dict)
    release_notes: str = ""
    metadata: Dict[str, Any] = Field(default_factory=dict)


class PatchArtifactUpdate(BaseModel):
    """Update patch fields"""
    status: Optional[str] = None
    release_notes: Optional[str] = None
    metadata: Optional[Dict[str, Any]] = None


class PatchArtifact(BaseModel):
    """Complete patch response"""
    id: UUID
    patch_id: str
    ticket_id: str
    status: str
    author: str
    target_repo: str
    target_paths: List[str]
    git_diff_excerpt: str
    tests: Dict[str, Any]
    risk_assessment: Dict[str, Any]
    security_impact: Dict[str, Any]
    approvals: Dict[str, Any]
    deployment_plan: Dict[str, Any]
    release_notes: str
    metadata: Dict[str, Any]
    created_at: datetime
    updated_at: datetime


# =============================================================================
# List Responses
# =============================================================================

class TicketListResponse(BaseModel):
    tickets: List[FredTicket]
    total: int
    page: int
    page_size: int


class PatchListResponse(BaseModel):
    patches: List[PatchArtifact]
    total: int
    page: int
    page_size: int


# =============================================================================
# Mock Config
# =============================================================================

class MockPatchConfig(BaseModel):
    ticket_id: str
    auto_generate: bool = True
    delay_seconds: int = 5
    risk_level: str = "low"
