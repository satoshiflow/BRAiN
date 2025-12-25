"""
AXE Odoo Module Generator

Text spec → ModuleAST → Odoo module files
Sprint IV: AXE × Odoo Integration
"""

from .generator import OdooModuleGenerator
from .parser import ModuleSpecParser
from .schemas import (
    GeneratedFile,
    ModuleAST,
    OdooAccessRightAST,
    OdooFieldAST,
    OdooFieldType,
    OdooMenuItemAST,
    OdooModelAST,
    OdooModuleGenerationResult,
    OdooViewAST,
    OdooViewType,
)

__all__ = [
    "OdooModuleGenerator",
    "ModuleSpecParser",
    "GeneratedFile",
    "ModuleAST",
    "OdooAccessRightAST",
    "OdooFieldAST",
    "OdooFieldType",
    "OdooMenuItemAST",
    "OdooModelAST",
    "OdooModuleGenerationResult",
    "OdooViewAST",
    "OdooViewType",
]
