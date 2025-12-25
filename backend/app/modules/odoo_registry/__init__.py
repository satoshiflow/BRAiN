"""
Odoo Module Registry

Version management and storage for generated Odoo modules.
Sprint IV: AXE × Odoo Integration
"""

from .schemas import (
    ModuleRegistryInfo,
    ModuleReleaseRecord,
    ModuleVersion,
    RegistryListResponse,
)
from .service import OdooModuleRegistry, get_odoo_registry

__all__ = [
    "ModuleRegistryInfo",
    "ModuleReleaseRecord",
    "ModuleVersion",
    "RegistryListResponse",
    "OdooModuleRegistry",
    "get_odoo_registry",
]
