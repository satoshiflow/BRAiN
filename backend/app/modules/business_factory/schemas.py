"""
Business Factory Schemas

Pydantic models for business setup automation.
All data structures for briefings, plans, steps, and results.
"""

from __future__ import annotations

from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field, field_validator, EmailStr
import uuid


# ============================================================================
# Enums
# ============================================================================

class BusinessType(str, Enum):
    """Supported business types with specific template sets"""
    ECOMMERCE = "ecommerce"
    SAAS = "saas"
    CONSULTING = "consulting"
    MANUFACTURING = "manufacturing"
    RETAIL = "retail"
    SERVICE = "service"


class PlanStatus(str, Enum):
    """Business plan lifecycle status"""
    DRAFT = "draft"              # Plan generated, not validated
    VALIDATED = "validated"      # Preflight checks passed
    APPROVED = "approved"        # User confirmed execution
    EXECUTING = "executing"      # Currently running
    COMPLETED = "completed"      # Successfully finished
    FAILED = "failed"            # Execution failed
    ROLLED_BACK = "rolled_back"  # Rollback completed


class StepStatus(str, Enum):
    """Individual step status"""
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    SKIPPED = "skipped"
    ROLLED_BACK = "rolled_back"


class RiskLevel(str, Enum):
    """Risk severity levels"""
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class ExecutorType(str, Enum):
    """Available executor types"""
    WEBGEN = "webgen"            # Website generation
    ODOO = "odoo"                # Odoo ERP operations
    INTEGRATION = "integration"  # Integration configuration
    VALIDATION = "validation"    # Testing/validation
    DNS = "dns"                  # DNS configuration


# ============================================================================
# Configuration Schemas
# ============================================================================

class WebsiteConfig(BaseModel):
    """Website setup configuration"""
    domain: str = Field(..., max_length=255, description="Desired domain (e.g., 'example.com')")
    template: str = Field(
        default="modern_landing",
        max_length=100,
        description="Website template ID from template registry"
    )
    pages: List[str] = Field(
        default_factory=lambda: ["home", "about", "contact"],
        description="Pages to generate"
    )
    features: List[str] = Field(
        default_factory=list,
        description="Features to enable (e.g., 'blog', 'shop', 'booking')"
    )
    primary_color: str = Field(
        default="#2563eb",
        max_length=7,
        description="Brand primary color (hex)"
    )
    secondary_color: str = Field(
        default="#64748b",
        max_length=7,
        description="Brand secondary color (hex)"
    )
    logo_url: Optional[str] = Field(
        None,
        max_length=2048,
        description="Logo URL or base64 data URI"
    )
    tagline: str = Field(
        default="Welcome to our business",
        max_length=255,
        description="Hero section tagline"
    )
    description: str = Field(
        default="",
        max_length=1000,
        description="Meta description for SEO"
    )

    @field_validator("domain")
    @classmethod
    def validate_domain(cls, v: str) -> str:
        """Validate domain name format"""
        if not v or "." not in v:
            raise ValueError("Invalid domain format")
        # Remove protocol if present
        v = v.replace("http://", "").replace("https://", "")
        # Remove trailing slash
        v = v.rstrip("/")
        return v.lower()

    @field_validator("primary_color", "secondary_color")
    @classmethod
    def validate_color(cls, v: str) -> str:
        """Validate hex color format"""
        if not v.startswith("#") or len(v) != 7:
            raise ValueError("Color must be in #RRGGBB format")
        return v.lower()


class ERPConfig(BaseModel):
    """Odoo ERP configuration"""
    modules: List[str] = Field(
        default_factory=lambda: ["crm", "sales", "accounting"],
        description="Odoo modules to install (e.g., 'crm', 'sales', 'inventory')"
    )
    users: List[Dict[str, str]] = Field(
        default_factory=list,
        description="Initial users [{name, email, role}]"
    )
    currency: str = Field(
        default="EUR",
        max_length=3,
        description="Default currency (ISO code)"
    )
    fiscal_year_start: str = Field(
        default="01-01",
        max_length=5,
        description="Fiscal year start (MM-DD)"
    )
    language: str = Field(
        default="en_US",
        max_length=10,
        description="Default language (e.g., 'en_US', 'de_DE')"
    )
    timezone: str = Field(
        default="UTC",
        max_length=63,
        description="Default timezone (IANA format)"
    )
    company_name: Optional[str] = Field(
        None,
        max_length=255,
        description="Company name in Odoo (defaults to business_name)"
    )
    custom_fields: Dict[str, Any] = Field(
        default_factory=dict,
        description="Custom field definitions"
    )

    @field_validator("fiscal_year_start")
    @classmethod
    def validate_fiscal_year(cls, v: str) -> str:
        """Validate fiscal year format"""
        if not v or len(v) != 5 or v[2] != "-":
            raise ValueError("Fiscal year must be in MM-DD format")
        month, day = v.split("-")
        if not (1 <= int(month) <= 12 and 1 <= int(day) <= 31):
            raise ValueError("Invalid month or day in fiscal year")
        return v


class IntegrationRequirement(BaseModel):
    """Integration between components"""
    name: str = Field(..., min_length=1, max_length=255, description="Integration name")
    source: str = Field(..., max_length=100, description="Source system (e.g., 'website')")
    target: str = Field(..., max_length=100, description="Target system (e.g., 'odoo')")
    type: str = Field(
        ...,
        max_length=100,
        description="Integration type (e.g., 'contact_form', 'product_sync')"
    )
    enabled: bool = Field(default=True, description="Enable this integration")
    config: Dict[str, Any] = Field(
        default_factory=dict,
        description="Integration-specific configuration"
    )


# ============================================================================
# Input Schema
# ============================================================================

class BusinessBriefing(BaseModel):
    """
    User input for business setup.
    Single source of truth for the entire factory process.
    """
    # Identity
    briefing_id: str = Field(
        default_factory=lambda: f"brief_{uuid.uuid4().hex[:12]}",
        description="Unique briefing identifier"
    )

    # Basic Info
    business_name: str = Field(..., min_length=1, max_length=255, description="Legal business name")
    business_type: BusinessType = Field(..., description="Type of business")
    industry: str = Field(..., min_length=1, max_length=100, description="Industry sector (e.g., 'IT Services')")
    country: str = Field(default="DE", max_length=2, description="Primary country (ISO code)")

    # Contact
    contact_email: EmailStr = Field(..., description="Primary contact email")
    contact_phone: Optional[str] = Field(None, max_length=20, description="Contact phone")

    # Website Requirements
    website_config: WebsiteConfig = Field(...)

    # ERP Requirements
    erp_config: ERPConfig = Field(...)

    # Integration Requirements
    integrations: List[IntegrationRequirement] = Field(
        default_factory=list,
        description="Integrations to configure"
    )

    # Execution Options
    auto_execute: bool = Field(
        default=False,
        description="Execute plan immediately after generation (use with caution)"
    )
    dry_run: bool = Field(
        default=False,
        description="Generate plan only, no execution"
    )
    auto_rollback: bool = Field(
        default=True,
        description="Automatically rollback on failure"
    )

    # Metadata
    created_at: datetime = Field(default_factory=datetime.utcnow)
    created_by: str = Field(default="system", max_length=255, description="User/system that created briefing")
    priority: int = Field(default=10, ge=1, le=100, description="Execution priority (1-100)")
    deadline: Optional[datetime] = Field(None, description="Optional deadline")
    notes: str = Field(default="", max_length=10000, description="Additional notes or requirements")

    class Config:
        json_schema_extra = {
            "example": {
                "business_name": "Acme Consulting GmbH",
                "business_type": "consulting",
                "industry": "IT Consulting",
                "country": "DE",
                "contact_email": "info@acme.example",
                "contact_phone": "+49 30 12345678",
                "website_config": {
                    "domain": "acme.example",
                    "template": "corporate_site_v1",
                    "pages": ["home", "services", "team", "contact"],
                    "primary_color": "#1e40af",
                    "tagline": "Expert IT Consulting",
                    "features": ["blog", "contact_form"]
                },
                "erp_config": {
                    "modules": ["crm", "projects", "timesheets", "invoicing"],
                    "users": [
                        {"name": "Admin User", "email": "admin@acme.example", "role": "admin"}
                    ],
                    "currency": "EUR"
                },
                "integrations": [
                    {
                        "name": "Contact Form to CRM",
                        "source": "website",
                        "target": "odoo",
                        "type": "contact_form",
                        "config": {"create_lead": True}
                    }
                ]
            }
        }


# ============================================================================
# Plan Schemas
# ============================================================================

class ExecutionStep(BaseModel):
    """Single execution step in the business plan"""
    # Identity
    step_id: str = Field(
        default_factory=lambda: f"step_{uuid.uuid4().hex[:8]}",
        description="Unique step identifier"
    )
    sequence: int = Field(..., description="Step sequence number (1-based)")
    name: str = Field(..., max_length=255, description="Human-readable step name")
    description: str = Field(..., max_length=2000, description="What this step does")

    # Execution
    executor: ExecutorType = Field(..., description="Which executor handles this step")
    template_id: Optional[str] = Field(None, max_length=100, description="Template to use (if applicable)")
    parameters: Dict[str, Any] = Field(
        default_factory=dict,
        description="Execution parameters"
    )

    # Dependencies
    depends_on: List[str] = Field(
        default_factory=list,
        description="Step IDs that must complete first"
    )

    # Status
    status: StepStatus = Field(default=StepStatus.PENDING)
    started_at: Optional[datetime] = Field(None)
    completed_at: Optional[datetime] = Field(None)
    duration_seconds: Optional[float] = Field(None)

    # Results
    result: Optional[Dict[str, Any]] = Field(
        None,
        description="Execution result data"
    )
    error: Optional[str] = Field(None, max_length=2000, description="Error message if failed")
    error_details: Optional[Dict[str, Any]] = Field(
        None,
        description="Detailed error information"
    )
    evidence_path: Optional[str] = Field(
        None, max_length=1000,
        description="Path to evidence files"
    )

    # Rollback
    rollback_possible: bool = Field(
        default=True,
        description="Can this step be rolled back?"
    )
    rollback_steps: List[Dict[str, Any]] = Field(
        default_factory=list,
        description="Actions to perform during rollback"
    )
    rollback_at: Optional[datetime] = Field(None, description="When rollback occurred")

    def mark_started(self):
        """Mark step as started"""
        self.status = StepStatus.RUNNING
        self.started_at = datetime.utcnow()

    def mark_completed(self, result: Optional[Dict[str, Any]] = None):
        """Mark step as completed"""
        self.status = StepStatus.COMPLETED
        self.completed_at = datetime.utcnow()
        if self.started_at:
            self.duration_seconds = (self.completed_at - self.started_at).total_seconds()
        if result:
            self.result = result

    def mark_failed(self, error: str, details: Optional[Dict[str, Any]] = None):
        """Mark step as failed"""
        self.status = StepStatus.FAILED
        self.completed_at = datetime.utcnow()
        if self.started_at:
            self.duration_seconds = (self.completed_at - self.started_at).total_seconds()
        self.error = error
        if details:
            self.error_details = details


class Risk(BaseModel):
    """Individual risk item"""
    risk_id: str = Field(
        default_factory=lambda: f"risk_{uuid.uuid4().hex[:8]}",
        description="Unique risk identifier"
    )
    description: str = Field(..., max_length=2000, description="Risk description")
    severity: RiskLevel = Field(..., description="Risk severity")
    probability: RiskLevel = Field(..., description="Likelihood of occurrence")
    impact: str = Field(..., max_length=2000, description="Potential impact if risk occurs")
    mitigation: str = Field(..., max_length=2000, description="Mitigation strategy")
    related_steps: List[str] = Field(
        default_factory=list,
        description="Step IDs affected by this risk"
    )


class RiskAssessment(BaseModel):
    """Risk analysis for the business plan"""
    # Overall
    overall_risk_level: RiskLevel = Field(..., description="Overall risk level")
    risks: List[Risk] = Field(default_factory=list, description="Identified risks")

    # Resource estimates
    estimated_duration_minutes: int = Field(
        ...,
        description="Total estimated execution time in minutes"
    )
    estimated_cost_euros: float = Field(
        default=0.0,
        description="Estimated cost in EUR"
    )
    resource_requirements: Dict[str, Any] = Field(
        default_factory=dict,
        description="Required resources (disk, memory, network, etc.)"
    )

    # Recommendations
    recommendations: List[str] = Field(
        default_factory=list,
        description="Recommended actions before execution (max 50 items, each max 500 chars)"
    )
    warnings: List[str] = Field(
        default_factory=list,
        description="Warnings to user (max 50 items, each max 500 chars)"
    )


class BusinessPlan(BaseModel):
    """Complete execution plan for business setup"""
    # Identity
    plan_id: str = Field(
        default_factory=lambda: f"plan_{uuid.uuid4().hex[:12]}",
        description="Unique plan identifier"
    )
    briefing_id: str = Field(..., description="Original briefing ID")
    version: int = Field(default=1, description="Plan version number")

    # Business Info (copied from briefing for reference)
    business_name: str = Field(..., description="Business name")
    business_type: BusinessType = Field(..., description="Business type")

    # Metadata
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)
    created_by: str = Field(default="business_factory")
    status: PlanStatus = Field(default=PlanStatus.DRAFT)

    # Content
    steps: List[ExecutionStep] = Field(
        default_factory=list,
        description="Ordered execution steps"
    )
    risk_assessment: Optional[RiskAssessment] = Field(
        None,
        description="Risk analysis"
    )

    # Execution tracking
    execution_started_at: Optional[datetime] = Field(None)
    execution_completed_at: Optional[datetime] = Field(None)
    current_step_index: int = Field(
        default=0,
        description="Index of currently executing step"
    )

    # Results
    evidence_pack_path: Optional[str] = Field(
        None,
        description="Path to evidence pack ZIP file"
    )
    final_urls: Dict[str, str] = Field(
        default_factory=dict,
        description="Generated URLs (website, odoo admin, etc.)"
    )

    # Statistics
    steps_total: int = Field(default=0)
    steps_completed: int = Field(default=0)
    steps_failed: int = Field(default=0)
    steps_skipped: int = Field(default=0)

    def get_next_step(self) -> Optional[ExecutionStep]:
        """
        Get next pending step that has all dependencies met.

        Returns:
            Next executable step or None if all done/blocked
        """
        completed_step_ids = {
            step.step_id for step in self.steps
            if step.status == StepStatus.COMPLETED
        }

        for step in self.steps:
            if step.status != StepStatus.PENDING:
                continue

            # Check if all dependencies are completed
            deps_met = all(dep_id in completed_step_ids for dep_id in step.depends_on)

            if deps_met:
                return step

        return None

    def update_statistics(self):
        """Recalculate plan statistics"""
        self.steps_total = len(self.steps)
        self.steps_completed = sum(1 for s in self.steps if s.status == StepStatus.COMPLETED)
        self.steps_failed = sum(1 for s in self.steps if s.status == StepStatus.FAILED)
        self.steps_skipped = sum(1 for s in self.steps if s.status == StepStatus.SKIPPED)
        self.updated_at = datetime.utcnow()

    def get_progress_percentage(self) -> float:
        """Calculate execution progress as percentage"""
        if self.steps_total == 0:
            return 0.0
        return (self.steps_completed / self.steps_total) * 100.0

    class Config:
        json_schema_extra = {
            "example": {
                "plan_id": "plan_abc123def456",
                "briefing_id": "brief_xyz789",
                "business_name": "Acme Consulting GmbH",
                "business_type": "consulting",
                "version": 1,
                "status": "draft",
                "steps_total": 7,
                "steps_completed": 0
            }
        }


# ============================================================================
# Result Schemas
# ============================================================================

class PreflightResult(BaseModel):
    """Result of preflight checks"""
    passed: bool = Field(..., description="All checks passed")
    checks: List[Dict[str, Any]] = Field(
        default_factory=list,
        description="Individual check results"
    )
    errors: List[str] = Field(default_factory=list, description="Preflight errors (max 100 items, each max 1000 chars)")
    warnings: List[str] = Field(default_factory=list, description="Preflight warnings (max 100 items, each max 1000 chars)")
    timestamp: datetime = Field(default_factory=datetime.utcnow)


class StepResult(BaseModel):
    """Result of a single step execution"""
    step_id: str
    success: bool
    data: Optional[Dict[str, Any]] = None
    error: Optional[str] = Field(None, max_length=2000)
    evidence_files: List[str] = Field(default_factory=list)
    duration_seconds: float


class ExecutionResult(BaseModel):
    """Result of complete plan execution"""
    plan_id: str
    status: PlanStatus
    success: bool
    message: str = Field(..., max_length=2000)
    steps_executed: int
    steps_succeeded: int
    steps_failed: int
    evidence_pack_url: Optional[str] = Field(None, max_length=2048)
    final_urls: Dict[str, str] = Field(default_factory=dict)
    execution_time_seconds: float
    timestamp: datetime = Field(default_factory=datetime.utcnow)


class RollbackResult(BaseModel):
    """Result of rollback operation"""
    plan_id: str
    success: bool
    steps_rolled_back: int
    errors: List[str] = Field(default_factory=list, description="Rollback errors (max 100 items, each max 1000 chars)")
    timestamp: datetime = Field(default_factory=datetime.utcnow)
