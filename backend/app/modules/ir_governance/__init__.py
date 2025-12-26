"""
IR Governance Module - Sprint 9 (P0)

Deterministic policy enforcement kernel for autonomous business pipelines.

Components:
- schemas: IR, IRStep, validation models
- canonicalization: Deterministic hashing
- validator: Policy-as-code enforcement
- approvals: HITL approval workflow
- diff_audit: IR ↔ DAG integrity gate
- router: FastAPI endpoints
"""

from backend.app.modules.ir_governance.schemas import (
    IR,
    IRStep,
    IRAction,
    IRProvider,
    RiskTier,
    IRValidationStatus,
    IRValidationResult,
    IRViolation,
    ApprovalStatus,
    ApprovalRequest,
    ApprovalConsumeRequest,
    ApprovalConsumeResult,
    DiffAuditResult,
)
from backend.app.modules.ir_governance.canonicalization import (
    canonical_json,
    sha256_hex,
    ir_hash,
    step_hash,
    compute_dag_hash,
)
from backend.app.modules.ir_governance.validator import (
    IRValidator,
    get_validator,
)
from backend.app.modules.ir_governance.approvals import (
    ApprovalsService,
    get_approvals_service,
)
from backend.app.modules.ir_governance.diff_audit import (
    DiffAuditGate,
    get_diff_audit_gate,
)
from backend.app.modules.ir_governance.router import router

__all__ = [
    # Schemas
    "IR",
    "IRStep",
    "IRAction",
    "IRProvider",
    "RiskTier",
    "IRValidationStatus",
    "IRValidationResult",
    "IRViolation",
    "ApprovalStatus",
    "ApprovalRequest",
    "ApprovalConsumeRequest",
    "ApprovalConsumeResult",
    "DiffAuditResult",
    # Canonicalization
    "canonical_json",
    "sha256_hex",
    "ir_hash",
    "step_hash",
    "compute_dag_hash",
    # Validator
    "IRValidator",
    "get_validator",
    # Approvals
    "ApprovalsService",
    "get_approvals_service",
    # Diff-Audit
    "DiffAuditGate",
    "get_diff_audit_gate",
    # Router
    "router",
]
