"""
BRAiN Autonomous Repo Operator (ARO) Module

Phase 1: Strict Governance and Safety for Repository Operations

This module provides a secure, auditable framework for repository operations
with multi-layered validation, safety checks, and policy enforcement.

Components:
- State Machine: Deterministic operation lifecycle
- Validators: Multi-level operation validation
- Safety Checkpoints: Pre-execution safety verification
- Audit Logger: Append-only audit trail
- Policy Engine Integration: Governance rules
- Service Layer: Orchestration of all components
- API Router: REST endpoints

Exports:
- router: FastAPI router for API endpoints
- get_aro_service: Get ARO service instance
- Schemas: All data models
"""

from .router import router
from .service import get_aro_service
from .schemas import (
    RepoOperation,
    RepoOperationContext,
    RepoOperationType,
    OperationState,
    AuthorizationLevel,
    ProposeOperationRequest,
    AuthorizeOperationRequest,
    ExecuteOperationRequest,
    OperationStatusResponse,
    AROStats,
    AROHealth,
    AROInfo,
)

__all__ = [
    # Router
    "router",
    # Service
    "get_aro_service",
    # Schemas
    "RepoOperation",
    "RepoOperationContext",
    "RepoOperationType",
    "OperationState",
    "AuthorizationLevel",
    "ProposeOperationRequest",
    "AuthorizeOperationRequest",
    "ExecuteOperationRequest",
    "OperationStatusResponse",
    "AROStats",
    "AROHealth",
    "AROInfo",
]

__version__ = "1.0.0"
__author__ = "BRAiN Team"
__description__ = "Autonomous Repo Operator - Phase 1"
