"""
NeuroRail Audit Module.

Provides immutable audit logging with:
- Append-only PostgreSQL storage
- EventStream integration for real-time observability
- Query API for audit trail analysis
"""

from app.modules.neurorail.audit.schemas import (
    AuditEvent,
    AuditQuery,
    AuditQueryResponse,
    AuditStats,
    StateTransitionAudit,
    ResourceAllocationAudit,
    BudgetCheckAudit,
    ErrorAudit,
    GovernanceDecisionAudit,
)
from app.modules.neurorail.audit.service import (
    AuditService,
    get_audit_service,
)
from app.modules.neurorail.audit.router import router

__all__ = [
    # Schemas
    "AuditEvent",
    "AuditQuery",
    "AuditQueryResponse",
    "AuditStats",
    "StateTransitionAudit",
    "ResourceAllocationAudit",
    "BudgetCheckAudit",
    "ErrorAudit",
    "GovernanceDecisionAudit",
    # Service
    "AuditService",
    "get_audit_service",
    # Router
    "router",
]
