"""
Odoo Connector Module

XML-RPC-based Odoo integration layer.
Sprint IV: AXE × Odoo Integration
"""

from .client import OdooXMLRPCClient
from .schemas import (
    OdooConnectionInfo,
    OdooConnectionStatus,
    OdooModuleInfo,
    OdooModuleListResponse,
    OdooModuleState,
    OdooOperationResult,
    OdooStatusResponse,
)
from .service import OdooConnectorService, get_odoo_service

__all__ = [
    "OdooXMLRPCClient",
    "OdooConnectionInfo",
    "OdooConnectionStatus",
    "OdooModuleInfo",
    "OdooModuleListResponse",
    "OdooModuleState",
    "OdooOperationResult",
    "OdooStatusResponse",
    "OdooConnectorService",
    "get_odoo_service",
]
