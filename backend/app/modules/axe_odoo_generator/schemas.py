"""
AXE Odoo Generator Schemas

AST models for Odoo module generation.
Sprint IV: AXE × Odoo Integration
"""

from __future__ import annotations

from enum import Enum
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field


# ============================================================================
# Field Types & Enums
# ============================================================================


class OdooFieldType(str, Enum):
    """Odoo field types."""

    CHAR = "char"
    TEXT = "text"
    INTEGER = "integer"
    FLOAT = "float"
    BOOLEAN = "boolean"
    DATE = "date"
    DATETIME = "datetime"
    SELECTION = "selection"
    MANY2ONE = "many2one"
    ONE2MANY = "one2many"
    MANY2MANY = "many2many"
    BINARY = "binary"
    HTML = "html"


class OdooViewType(str, Enum):
    """Odoo view types."""

    TREE = "tree"
    FORM = "form"
    KANBAN = "kanban"
    SEARCH = "search"
    CALENDAR = "calendar"
    GRAPH = "graph"


# ============================================================================
# Module AST Models
# ============================================================================


class OdooFieldAST(BaseModel):
    """AST representation of an Odoo model field."""

    name: str = Field(..., description="Field name (snake_case)")
    field_type: OdooFieldType = Field(..., description="Field type")
    required: bool = Field(False, description="Field is required")
    readonly: bool = Field(False, description="Field is readonly")
    default: Optional[Any] = Field(None, description="Default value")
    string: Optional[str] = Field(None, description="Field label")
    help: Optional[str] = Field(None, description="Field help text")

    # Relational fields
    comodel_name: Optional[str] = Field(None, description="Related model (for Many2one, etc.)")
    relation: Optional[str] = Field(None, description="Relation table (for Many2many)")
    domain: Optional[str] = Field(None, description="Domain filter")

    # Selection field
    selection: Optional[List[tuple]] = Field(None, description="Selection options")

    # Constraints
    size: Optional[int] = Field(None, description="Max size (for Char)")
    digits: Optional[tuple] = Field(None, description="Precision (for Float)")

    # Metadata
    metadata: Dict[str, Any] = Field(default_factory=dict, description="Additional field attributes")


class OdooModelAST(BaseModel):
    """AST representation of an Odoo model."""

    name: str = Field(..., description="Model name (e.g., 'custom.lead.stage')")
    description: Optional[str] = Field(None, description="Model description")
    inherits: Optional[str] = Field(None, description="Model inheritance (_inherit)")
    fields: List[OdooFieldAST] = Field(default_factory=list, description="Model fields")

    # Model attributes
    order: Optional[str] = Field(None, description="Default order")
    rec_name: Optional[str] = Field(None, description="Record name field")

    # Metadata
    metadata: Dict[str, Any] = Field(default_factory=dict, description="Additional model attributes")


class OdooViewAST(BaseModel):
    """AST representation of an Odoo view."""

    name: str = Field(..., description="View name")
    model: str = Field(..., description="Model this view belongs to")
    view_type: OdooViewType = Field(..., description="View type (tree, form, etc.)")
    arch: Optional[str] = Field(None, description="View XML architecture (if custom)")
    priority: int = Field(16, description="View priority")

    # Auto-generated views can specify fields to include
    fields: List[str] = Field(default_factory=list, description="Fields to include (for auto-gen)")

    # Metadata
    metadata: Dict[str, Any] = Field(default_factory=dict, description="Additional view attributes")


class OdooMenuItemAST(BaseModel):
    """AST representation of an Odoo menu item."""

    name: str = Field(..., description="Menu item name")
    parent: Optional[str] = Field(None, description="Parent menu ID")
    action: Optional[str] = Field(None, description="Action ID")
    sequence: int = Field(10, description="Menu sequence")
    groups: List[str] = Field(default_factory=list, description="Security groups")


class OdooAccessRightAST(BaseModel):
    """AST representation of Odoo access rights."""

    model: str = Field(..., description="Model name")
    group: str = Field("base.group_user", description="Security group")
    perm_read: bool = Field(True, description="Read permission")
    perm_write: bool = Field(False, description="Write permission")
    perm_create: bool = Field(False, description="Create permission")
    perm_unlink: bool = Field(False, description="Delete permission")


class ModuleAST(BaseModel):
    """
    Abstract Syntax Tree for Odoo module.

    This is the intermediate representation between text spec and generated files.
    """

    # Module metadata
    name: str = Field(..., description="Technical module name (snake_case)")
    version: str = Field("1.0.0", description="Module version")
    display_name: Optional[str] = Field(None, description="Human-readable name")
    summary: Optional[str] = Field(None, description="Short description")
    description: Optional[str] = Field(None, description="Long description")
    author: str = Field("BRAiN AXE Generator", description="Module author")
    website: str = Field("https://brain.falklabs.de", description="Author website")
    category: str = Field("Uncategorized", description="Module category")
    license: str = Field("LGPL-3", description="License")

    # Dependencies
    depends: List[str] = Field(default_factory=lambda: ["base"], description="Module dependencies")

    # Module components
    models: List[OdooModelAST] = Field(default_factory=list, description="Models to generate")
    views: List[OdooViewAST] = Field(default_factory=list, description="Views to generate")
    menus: List[OdooMenuItemAST] = Field(default_factory=list, description="Menu items")
    access_rights: List[OdooAccessRightAST] = Field(default_factory=list, description="Access rights")

    # Data files
    demo_data: bool = Field(False, description="Include demo data")

    # Installation
    installable: bool = Field(True, description="Module is installable")
    application: bool = Field(False, description="Module is an application")
    auto_install: bool = Field(False, description="Auto-install with dependencies")

    # Metadata
    metadata: Dict[str, Any] = Field(default_factory=dict, description="Additional module metadata")

    class Config:
        json_schema_extra = {
            "example": {
                "name": "my_custom_crm",
                "version": "1.0.0",
                "display_name": "My Custom CRM",
                "summary": "Custom CRM extension",
                "depends": ["base", "crm"],
                "models": [
                    {
                        "name": "custom.lead.stage",
                        "description": "Custom Lead Stage",
                        "fields": [
                            {
                                "name": "name",
                                "field_type": "char",
                                "required": True,
                                "string": "Stage Name",
                            },
                            {
                                "name": "sequence",
                                "field_type": "integer",
                                "default": 10,
                                "string": "Sequence",
                            },
                        ],
                    }
                ],
                "views": [
                    {
                        "name": "custom_lead_stage_tree",
                        "model": "custom.lead.stage",
                        "view_type": "tree",
                        "fields": ["name", "sequence"],
                    },
                    {
                        "name": "custom_lead_stage_form",
                        "model": "custom.lead.stage",
                        "view_type": "form",
                        "fields": ["name", "sequence"],
                    },
                ],
            }
        }


# ============================================================================
# Generation Result Models
# ============================================================================


class GeneratedFile(BaseModel):
    """Represents a generated file."""

    path: str = Field(..., description="Relative path within module")
    content: str = Field(..., description="File content")
    file_type: str = Field(..., description="File type (python, xml, csv, etc.)")


class OdooModuleGenerationResult(BaseModel):
    """Result of Odoo module generation."""

    success: bool = Field(..., description="Generation succeeded")
    module_name: str = Field(..., description="Generated module name")
    version: str = Field(..., description="Module version")
    files: List[GeneratedFile] = Field(default_factory=list, description="Generated files")
    module_hash: Optional[str] = Field(None, description="SHA256 hash of module")
    warnings: List[str] = Field(default_factory=list, description="Warning messages")
    errors: List[str] = Field(default_factory=list, description="Error messages")
    metadata: Dict[str, Any] = Field(default_factory=dict, description="Additional metadata")

    class Config:
        json_schema_extra = {
            "example": {
                "success": True,
                "module_name": "my_custom_crm",
                "version": "1.0.0",
                "files": [
                    {
                        "path": "__manifest__.py",
                        "content": "...",
                        "file_type": "python",
                    },
                    {
                        "path": "models/custom_lead_stage.py",
                        "content": "...",
                        "file_type": "python",
                    },
                ],
                "module_hash": "abc123...",
                "warnings": [],
                "errors": [],
            }
        }
