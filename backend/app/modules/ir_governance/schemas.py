"""
IR Governance Schemas - Sprint 9 (P0)

Canonical Intermediate Representation (IR) as Single Source of Truth.
Strict typing, deterministic, fail-closed by default.
"""

from typing import Dict, List, Optional, Any
from datetime import datetime
from pydantic import BaseModel, Field, field_validator
from enum import Enum
import uuid


class IRAction(str, Enum):
    """Fixed vocabulary of allowed actions (fail-closed)."""

    # Deployment actions
    DEPLOY_WEBSITE = "deploy.website"
    DEPLOY_API = "deploy.api"
    DEPLOY_DATABASE = "deploy.database"

    # DNS actions
    DNS_UPDATE_RECORDS = "dns.update_records"
    DNS_CREATE_ZONE = "dns.create_zone"
    DNS_DELETE_ZONE = "dns.delete_zone"

    # Odoo/ERP actions
    ODOO_INSTALL_MODULE = "odoo.install_module"
    ODOO_UNINSTALL_MODULE = "odoo.uninstall_module"
    ODOO_UPDATE_MODULE = "odoo.update_module"
    ODOO_CREATE_RECORD = "odoo.create_record"
    ODOO_UPDATE_RECORD = "odoo.update_record"
    ODOO_DELETE_RECORD = "odoo.delete_record"

    # WebGenesis actions (Sprint 8)
    WEBGEN_GENERATE_SITE = "webgen.generate_site"
    WEBGEN_UPDATE_CONTENT = "webgen.update_content"

    # WebGenesis actions (Sprint 10 - opt-in IR integration)
    WEBGENESIS_SITE_CREATE = "webgenesis.site.create"
    WEBGENESIS_SITE_UPDATE = "webgenesis.site.update"
    WEBGENESIS_DEPLOY_TRIGGER = "webgenesis.deploy.trigger"

    # CourseFactory actions (Sprint 12)
    COURSE_CREATE = "course.create"
    COURSE_GENERATE_OUTLINE = "course.generate_outline"
    COURSE_GENERATE_LESSONS = "course.generate_lessons"
    COURSE_GENERATE_QUIZ = "course.generate_quiz"
    COURSE_GENERATE_LANDING = "course.generate_landing"
    COURSE_DEPLOY_STAGING = "course.deploy_staging"

    # CourseFactory enhancement actions (Sprint 13)
    COURSE_ENHANCE_EXAMPLES = "course.enhance_examples"
    COURSE_ENHANCE_SUMMARIES = "course.enhance_summaries"
    COURSE_GENERATE_FLASHCARDS = "course.generate_flashcards"
    COURSE_WORKFLOW_TRANSITION = "course.workflow_transition"

    # WebGenesis integration actions (Sprint 13)
    WEBGENESIS_BIND_THEME = "webgenesis.bind_theme"
    WEBGENESIS_BUILD_SECTIONS = "webgenesis.build_sections"
    WEBGENESIS_APPLY_SEO = "webgenesis.apply_seo"
    WEBGENESIS_PREVIEW = "webgenesis.preview"

    # Infrastructure actions
    INFRA_PROVISION = "infra.provision"
    INFRA_DESTROY = "infra.destroy"
    INFRA_SCALE = "infra.scale"


class IRProvider(str, Enum):
    """Fixed vocabulary of allowed providers (fail-closed)."""

    # Deployment providers
    DEPLOY_PROVIDER_V1 = "deploy.provider_v1"
    DEPLOY_DOCKER = "deploy.docker"
    DEPLOY_KUBERNETES = "deploy.kubernetes"

    # DNS providers
    DNS_HETZNER = "dns.hetzner"
    DNS_CLOUDFLARE = "dns.cloudflare"
    DNS_ROUTE53 = "dns.route53"

    # Odoo provider
    ODOO_V16 = "odoo.v16"
    ODOO_V17 = "odoo.v17"

    # WebGenesis providers
    WEBGEN_V1 = "webgen.v1"  # Sprint 8
    WEBGENESIS_V1 = "webgenesis.v1"  # Sprint 10

    # CourseFactory providers
    COURSE_FACTORY_V1 = "course_factory.v1"  # Sprint 12

    # Infrastructure providers
    INFRA_TERRAFORM = "infra.terraform"
    INFRA_ANSIBLE = "infra.ansible"


class RiskTier(int, Enum):
    """Risk tier computed by validator (not trusted from IR input)."""

    TIER_0 = 0  # Safe, read-only, no side effects
    TIER_1 = 1  # Low risk, dev/staging only
    TIER_2 = 2  # Medium risk, requires approval
    TIER_3 = 3  # High risk, critical operations


class IRStep(BaseModel):
    """
    Atomic step in IR.

    Strictly typed, fail-closed, deterministic.
    """

    # Required fields
    action: IRAction = Field(..., description="Action to perform (fixed vocabulary)")
    provider: IRProvider = Field(..., description="Provider to use (fixed vocabulary)")
    resource: str = Field(..., description="Resource identifier", min_length=1, max_length=500)
    params: Dict[str, Any] = Field(default_factory=dict, description="Action parameters")
    idempotency_key: str = Field(..., description="Idempotency key (required, non-empty)", min_length=1, max_length=200)

    # Optional fields
    constraints: Dict[str, Any] = Field(default_factory=dict, description="Step constraints")
    budget_cents: Optional[int] = Field(None, description="Budget in cents (integer only, no floats)", ge=0)

    # Computed by validator (not trusted from input)
    risk_tier: Optional[RiskTier] = Field(None, description="Risk tier (computed by validator)")
    requires_approval: bool = Field(default=False, description="Requires approval (computed)")

    # Optional metadata
    step_id: Optional[str] = Field(None, description="Optional stable step ID (UUID)")
    description: Optional[str] = Field(None, description="Human-readable description", max_length=1000)

    class Config:
        extra = "forbid"  # Reject unknown fields (fail-closed)
        use_enum_values = False  # Keep enum objects for validation

    @field_validator("idempotency_key")
    @classmethod
    def validate_idempotency_key(cls, v):
        """Ensure idempotency key is non-empty."""
        if not v or not v.strip():
            raise ValueError("idempotency_key must be non-empty")
        return v.strip()

    @field_validator("resource")
    @classmethod
    def validate_resource(cls, v):
        """Ensure resource identifier is valid."""
        if not v or not v.strip():
            raise ValueError("resource must be non-empty")
        # Basic sanitation: no control characters
        if any(ord(c) < 32 for c in v):
            raise ValueError("resource contains invalid control characters")
        return v.strip()


class IR(BaseModel):
    """
    Canonical Intermediate Representation.

    Single Source of Truth for pipeline execution.
    Fail-closed, deterministic, tenant-bound.
    """

    # Required fields
    tenant_id: str = Field(..., description="Tenant ID (required, hard isolation)", min_length=1, max_length=100)
    steps: List[IRStep] = Field(..., description="Atomic steps to execute", min_items=1)

    # Optional metadata
    request_id: str = Field(default_factory=lambda: str(uuid.uuid4()), description="Request ID (UUID)")
    created_at: datetime = Field(default_factory=datetime.utcnow, description="Creation timestamp")
    intent_summary: Optional[str] = Field(None, description="Intent summary", max_length=2000)
    labels: Dict[str, str] = Field(default_factory=dict, description="Labels/tags")

    class Config:
        extra = "forbid"  # Reject unknown fields (fail-closed)

    @field_validator("tenant_id")
    @classmethod
    def validate_tenant_id(cls, v):
        """Ensure tenant_id is non-empty and sanitized."""
        if not v or not v.strip():
            raise ValueError("tenant_id must be non-empty")
        # Basic sanitation: no control characters
        if any(ord(c) < 32 for c in v):
            raise ValueError("tenant_id contains invalid control characters")
        return v.strip()

    @field_validator("steps")
    @classmethod
    def validate_steps(cls, v):
        """Ensure steps list is non-empty."""
        if not v:
            raise ValueError("steps must contain at least one step")
        return v


class IRValidationStatus(str, Enum):
    """Validation result status."""

    PASS = "PASS"  # Safe to execute
    ESCALATE = "ESCALATE"  # Requires approval
    REJECT = "REJECT"  # Cannot execute


class IRViolation(BaseModel):
    """Validation violation."""

    step_index: Optional[int] = Field(None, description="Step index (if step-specific)")
    code: str = Field(..., description="Violation code")
    message: str = Field(..., description="Human-readable message")
    severity: str = Field(..., description="Severity: ERROR, WARNING")


class IRValidationResult(BaseModel):
    """Result of IR validation."""

    status: IRValidationStatus = Field(..., description="Validation status")
    violations: List[IRViolation] = Field(default_factory=list, description="Violations found")
    risk_tier: RiskTier = Field(..., description="Effective risk tier (max across steps)")
    requires_approval: bool = Field(default=False, description="Requires HITL approval")
    ir_hash: str = Field(..., description="Canonical IR hash (SHA256)")

    # Audit correlation
    tenant_id: str = Field(..., description="Tenant ID")
    request_id: str = Field(..., description="Request ID")
    validated_at: datetime = Field(default_factory=datetime.utcnow)


class ApprovalStatus(str, Enum):
    """Approval request status."""

    PENDING = "pending"
    CONSUMED = "consumed"
    EXPIRED = "expired"
    INVALID = "invalid"


class ApprovalRequest(BaseModel):
    """HITL approval request."""

    approval_id: str = Field(default_factory=lambda: str(uuid.uuid4()), description="Approval ID")
    tenant_id: str = Field(..., description="Tenant ID")
    ir_hash: str = Field(..., description="IR hash being approved")
    status: ApprovalStatus = Field(default=ApprovalStatus.PENDING)

    # Token (single-use, TTL, not logged in raw form)
    token_hash: str = Field(..., description="Token hash (SHA256, not raw token)")

    # Timestamps
    created_at: datetime = Field(default_factory=datetime.utcnow)
    expires_at: datetime = Field(..., description="Expiration timestamp")
    consumed_at: Optional[datetime] = Field(None, description="Consumption timestamp")

    # Metadata
    created_by: Optional[str] = Field(None, description="User/role who created")
    consumed_by: Optional[str] = Field(None, description="User/role who consumed")

    class Config:
        extra = "forbid"


class ApprovalConsumeRequest(BaseModel):
    """Request to consume an approval."""

    tenant_id: str = Field(..., description="Tenant ID")
    ir_hash: str = Field(..., description="IR hash")
    token: str = Field(..., description="Approval token (raw)")

    class Config:
        extra = "forbid"


class ApprovalConsumeResult(BaseModel):
    """Result of approval consumption."""

    success: bool = Field(..., description="Consumption successful")
    status: ApprovalStatus = Field(..., description="Approval status")
    message: str = Field(..., description="Result message")
    approval_id: Optional[str] = Field(None, description="Approval ID if successful")


class DiffAuditResult(BaseModel):
    """Result of IR ↔ DAG diff audit."""

    success: bool = Field(..., description="Diff audit passed")
    ir_hash: str = Field(..., description="IR hash")
    dag_hash: str = Field(..., description="DAG hash (computed from nodes)")

    # Violations
    missing_ir_steps: List[str] = Field(default_factory=list, description="IR steps missing from DAG")
    extra_dag_nodes: List[str] = Field(default_factory=list, description="DAG nodes without IR step")
    hash_mismatches: List[Dict[str, str]] = Field(default_factory=list, description="Hash mismatches")

    # Audit correlation
    tenant_id: str = Field(..., description="Tenant ID")
    request_id: str = Field(..., description="Request ID")
    audited_at: datetime = Field(default_factory=datetime.utcnow)
