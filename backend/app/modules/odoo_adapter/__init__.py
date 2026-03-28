"""
Odoo 19 Adapter Module
======================

Integration Layer für Odoo 19 ERP System.

Bietet:
- Connection Pooling für PostgreSQL
- Company Resolution (Multi-Company)
- Domain Adapter (Accounting, Sales, etc.)
- Neural Core Integration

Usage:
    from app.modules.odoo_adapter import get_odoo_adapter
    adapter = get_odoo_adapter()
"""

from .service import OdooAdapter, get_odoo_adapter
from .connection import OdooConnectionPool
from .config import OdooAdapterConfig

__all__ = [
    "OdooAdapter",
    "get_odoo_adapter",
    "OdooConnectionPool",
    "OdooAdapterConfig",
]
