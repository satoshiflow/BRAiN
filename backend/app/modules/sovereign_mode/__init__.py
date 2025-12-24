"""
Sovereign Mode Module

Provides secure offline operation with model bundle management,
network isolation, and strict validation.

Components:
- ModeDetector: Network connectivity detection
- BundleManager: Offline model bundle management
- HashValidator: SHA256 integrity validation
- NetworkGuard: HTTP request interception and blocking
- Service: Core orchestration and policy integration
"""

from backend.app.modules.sovereign_mode.service import (
    SovereignModeService,
    get_sovereign_service,
)
from backend.app.modules.sovereign_mode.schemas import (
    SovereignMode,
    OperationMode,
    Bundle,
    BundleStatus,
    ValidationResult,
    ModeConfig,
    AuditEntry,
    AuditSeverity,
    AuditEventType,
)

__all__ = [
    "SovereignModeService",
    "get_sovereign_service",
    "SovereignMode",
    "OperationMode",
    "Bundle",
    "BundleStatus",
    "ValidationResult",
    "ModeConfig",
    "AuditEntry",
    "AuditSeverity",
    "AuditEventType",
]
