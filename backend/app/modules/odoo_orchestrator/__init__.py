"""
Odoo Orchestrator Module

Coordinates module generation, storage, and deployment.
Sprint IV: AXE × Odoo Integration
"""

from .schemas import (
    ModuleGenerateRequest,
    ModuleInstallRequest,
    ModuleRollbackRequest,
    ModuleUpgradeRequest,
    OdooOrchestrationResult,
    OdooOrchestrationStatus,
)
from .service import OdooOrchestrator, get_odoo_orchestrator

__all__ = [
    "ModuleGenerateRequest",
    "ModuleInstallRequest",
    "ModuleRollbackRequest",
    "ModuleUpgradeRequest",
    "OdooOrchestrationResult",
    "OdooOrchestrationStatus",
    "OdooOrchestrator",
    "get_odoo_orchestrator",
]
