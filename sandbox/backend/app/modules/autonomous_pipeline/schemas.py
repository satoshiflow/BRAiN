"""
Autonomous Business Pipeline Schemas (Sprint 8)

Structured data models for end-to-end business creation pipeline.
"""

from enum import Enum
from typing import Dict, List, Optional, Any
from pydantic import BaseModel, Field
from datetime import datetime


# ============================================================================
# S8.1 - Business Intent Resolution
# ============================================================================


class BusinessType(str, Enum):
    """Type of business model."""
    SERVICE = "service"        # Service-based business (consulting, agency)
    PRODUCT = "product"        # Product-based business (e-commerce, retail)
    PLATFORM = "platform"      # Platform business (marketplace, SaaS)
    HYBRID = "hybrid"          # Combination of above


class MonetizationType(str, Enum):
    """Revenue model."""
    SUBSCRIPTION = "subscription"    # Recurring revenue
    ONE_TIME = "one_time"           # One-time purchases
    FREEMIUM = "freemium"           # Free + premium tiers
    COMMISSION = "commission"       # Marketplace commission
    ADVERTISING = "advertising"     # Ad-supported
    HYBRID = "hybrid"               # Multiple revenue streams


class ComplianceSensitivity(str, Enum):
    """Compliance requirements level."""
    LOW = "low"          # Minimal compliance (blog, portfolio)
    MEDIUM = "medium"    # Standard compliance (e-commerce, services)
    HIGH = "high"        # High compliance (finance, healthcare, legal)


class RiskLevel(str, Enum):
    """Business execution risk level."""
    LOW = "low"          # Simple execution, low complexity
    MEDIUM = "medium"    # Moderate complexity, some custom requirements
    HIGH = "high"        # Complex execution, high customization
    CRITICAL = "critical"  # Very complex, regulatory requirements


class BusinessIntentInput(BaseModel):
    """
    Input for business intent resolution.

    User provides natural language description of business idea.
    """

    # Core Business Description
    vision: str = Field(
        ...,
        description="Business vision/idea in natural language",
        min_length=10
    )
    target_audience: str = Field(
        ...,
        description="Target audience description",
        min_length=5
    )
    region: str = Field(
        default="global",
        description="Primary region (e.g., 'Germany', 'EU', 'global')"
    )

    # Optional Details
    monetization_type: Optional[MonetizationType] = Field(
        None,
        description="Revenue model (if known)"
    )
    compliance_sensitivity: ComplianceSensitivity = Field(
        default=ComplianceSensitivity.MEDIUM,
        description="Compliance requirements level"
    )

    # Technical Preferences
    preferred_language: str = Field(default="en", description="Primary language")
    budget_tier: str = Field(default="standard", description="Budget tier (basic/standard/premium)")

    class Config:
        json_schema_extra = {
            "example": {
                "vision": "A consulting platform connecting sustainability experts with manufacturing companies",
                "target_audience": "Manufacturing companies in EU seeking sustainability consulting",
                "region": "EU",
                "monetization_type": "commission",
                "compliance_sensitivity": "medium",
                "preferred_language": "de",
                "budget_tier": "standard"
            }
        }


class ResolvedBusinessIntent(BaseModel):
    """
    Resolved structured business intent.

    Output of BusinessIntentResolver - deterministic business configuration.
    """

    # Resolution Metadata
    intent_id: str = Field(..., description="Unique intent identifier")
    resolved_at: datetime = Field(default_factory=datetime.utcnow)

    # Business Classification
    business_type: BusinessType = Field(..., description="Classified business type")
    monetization_type: MonetizationType = Field(..., description="Revenue model")
    risk_level: RiskLevel = Field(..., description="Execution risk level")
    compliance_sensitivity: ComplianceSensitivity = Field(..., description="Compliance level")

    # Technical Requirements
    needs_website: bool = Field(..., description="Requires website")
    needs_erp: bool = Field(..., description="Requires ERP system")
    needs_custom_modules: bool = Field(..., description="Requires custom Odoo modules")

    # Website Configuration
    website_template: Optional[str] = Field(None, description="Website template ID")
    website_pages: List[str] = Field(default_factory=list, description="Required pages")

    # Odoo Configuration
    odoo_modules_required: List[str] = Field(
        default_factory=list,
        description="Required Odoo modules"
    )
    custom_modules_spec: List[Dict[str, Any]] = Field(
        default_factory=list,
        description="Custom module specifications"
    )

    # Domain Configuration
    suggested_domain_pattern: str = Field(
        ...,
        description="Suggested domain pattern (e.g., '{business-name}.com')"
    )

    # Business Context
    industry: str = Field(..., description="Industry classification")
    primary_language: str = Field(..., description="Primary language code")
    target_region: str = Field(..., description="Target region")

    # Governance & Risk
    governance_checks_required: List[str] = Field(
        default_factory=list,
        description="Required governance checks"
    )
    estimated_complexity_score: int = Field(
        ...,
        ge=1,
        le=100,
        description="Complexity score (1-100)"
    )

    # Original Input
    original_vision: str = Field(..., description="Original vision text")

    class Config:
        json_schema_extra = {
            "example": {
                "intent_id": "intent_20251225_abc123",
                "business_type": "platform",
                "monetization_type": "commission",
                "risk_level": "medium",
                "compliance_sensitivity": "medium",
                "needs_website": True,
                "needs_erp": True,
                "needs_custom_modules": True,
                "website_template": "professional_services_v1",
                "website_pages": ["home", "services", "experts", "about", "contact"],
                "odoo_modules_required": ["crm", "project", "website", "contacts"],
                "custom_modules_spec": [
                    {
                        "name": "expert_matching",
                        "description": "Match experts with companies based on expertise",
                        "models": ["expert_profile", "matching_request"],
                        "views": ["expert_list", "match_kanban"]
                    }
                ],
                "suggested_domain_pattern": "{business-name}.consulting",
                "industry": "consulting",
                "primary_language": "de",
                "target_region": "EU",
                "governance_checks_required": ["policy_check", "data_privacy_check"],
                "estimated_complexity_score": 65,
                "original_vision": "A consulting platform..."
            }
        }


# ============================================================================
# S8.2 - Execution Graph
# ============================================================================


class ExecutionNodeType(str, Enum):
    """Type of execution node."""
    VALIDATION = "validation"      # Pre-flight validation
    GENERATION = "generation"      # Content/code generation
    DEPLOYMENT = "deployment"      # Deployment operation
    CONFIGURATION = "configuration"  # Configuration change
    VERIFICATION = "verification"  # Post-deployment verification


class ExecutionNodeStatus(str, Enum):
    """Status of execution node."""
    PENDING = "pending"          # Not yet executed
    RUNNING = "running"          # Currently executing
    COMPLETED = "completed"      # Successfully completed
    FAILED = "failed"            # Failed with error
    SKIPPED = "skipped"          # Skipped due to conditions
    ROLLED_BACK = "rolled_back"  # Successfully rolled back


class ExecutionCapability(str, Enum):
    """Execution node capabilities."""
    DRY_RUN = "dry_run"            # Supports dry-run mode
    ROLLBACKABLE = "rollbackable"  # Can be rolled back
    IDEMPOTENT = "idempotent"      # Safe to re-run
    RESUMABLE = "resumable"        # Can resume after failure


class ExecutionNodeSpec(BaseModel):
    """Specification for an execution node in the graph."""

    node_id: str = Field(..., description="Unique node identifier")
    node_type: ExecutionNodeType = Field(..., description="Node type")
    name: str = Field(..., description="Human-readable name")
    description: str = Field(..., description="Node description")

    # Dependencies
    depends_on: List[str] = Field(
        default_factory=list,
        description="Node IDs this depends on"
    )

    # Capabilities
    capabilities: List[ExecutionCapability] = Field(
        default_factory=list,
        description="Node capabilities"
    )

    # Execution Config
    executor_class: str = Field(..., description="Executor class name")
    executor_params: Dict[str, Any] = Field(
        default_factory=dict,
        description="Executor parameters"
    )

    # Timeouts & Retries
    timeout_seconds: int = Field(default=300, description="Execution timeout")
    max_retries: int = Field(default=0, description="Max retry attempts")

    # Governance
    requires_governance_approval: bool = Field(
        default=False,
        description="Requires governance approval before execution"
    )
    critical: bool = Field(
        default=False,
        description="Critical node - failure aborts pipeline"
    )


class ExecutionNodeResult(BaseModel):
    """Result of executing a node."""

    node_id: str = Field(..., description="Node identifier")
    status: ExecutionNodeStatus = Field(..., description="Execution status")

    # Timing
    started_at: Optional[datetime] = Field(None, description="Start timestamp")
    completed_at: Optional[datetime] = Field(None, description="Completion timestamp")
    duration_seconds: Optional[float] = Field(None, description="Execution duration")

    # Result Data
    success: bool = Field(..., description="Execution succeeded")
    output: Dict[str, Any] = Field(
        default_factory=dict,
        description="Execution output data"
    )
    artifacts: List[str] = Field(
        default_factory=list,
        description="Generated artifacts (file paths, URLs)"
    )

    # Error Handling
    error: Optional[str] = Field(None, description="Error message if failed")
    error_traceback: Optional[str] = Field(None, description="Error traceback")

    # Rollback
    rollback_available: bool = Field(default=False, description="Can be rolled back")
    rollback_executed: bool = Field(default=False, description="Rollback was executed")

    # Dry Run
    was_dry_run: bool = Field(default=False, description="Was executed in dry-run mode")


class ExecutionGraphSpec(BaseModel):
    """Specification for complete execution graph."""

    graph_id: str = Field(..., description="Unique graph identifier")
    business_intent_id: str = Field(..., description="Associated business intent")

    # Nodes
    nodes: List[ExecutionNodeSpec] = Field(
        ...,
        description="Execution nodes"
    )

    # Execution Config
    dry_run: bool = Field(default=False, description="Execute in dry-run mode")
    auto_rollback: bool = Field(default=True, description="Auto-rollback on failure")
    stop_on_first_error: bool = Field(default=True, description="Stop on first critical error")

    # Metadata
    created_at: datetime = Field(default_factory=datetime.utcnow)
    created_by: str = Field(default="system", description="Creator identifier")


class ExecutionGraphResult(BaseModel):
    """Result of executing a complete graph."""

    graph_id: str = Field(..., description="Graph identifier")

    # Status
    status: str = Field(..., description="Overall status (completed/failed/partial)")
    started_at: datetime = Field(..., description="Execution start")
    completed_at: Optional[datetime] = Field(None, description="Execution completion")
    total_duration_seconds: Optional[float] = Field(None, description="Total duration")

    # Node Results
    node_results: List[ExecutionNodeResult] = Field(
        default_factory=list,
        description="Results for each node"
    )

    # Statistics
    nodes_total: int = Field(..., description="Total nodes")
    nodes_completed: int = Field(default=0, description="Completed nodes")
    nodes_failed: int = Field(default=0, description="Failed nodes")
    nodes_skipped: int = Field(default=0, description="Skipped nodes")

    # Artifacts
    artifacts_generated: List[str] = Field(
        default_factory=list,
        description="All generated artifacts"
    )

    # Rollback
    rollback_executed: bool = Field(default=False, description="Rollback was performed")
    rolled_back_nodes: List[str] = Field(
        default_factory=list,
        description="Nodes that were rolled back"
    )

    # Evidence
    audit_trail: List[Dict[str, Any]] = Field(
        default_factory=list,
        description="Complete audit trail"
    )
    evidence_pack_path: Optional[str] = Field(
        None,
        description="Path to evidence pack"
    )
