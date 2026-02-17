"""
Template Registry Schemas

Data models for template management.
"""

from __future__ import annotations

from enum import Enum
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field
from datetime import datetime


class TemplateType(str, Enum):
    """Template categories"""
    WEBSITE = "website"
    ODOO_CONFIG = "odoo_config"
    INTEGRATION = "integration"


class VariableType(str, Enum):
    """Variable data types"""
    STRING = "string"
    INTEGER = "integer"
    FLOAT = "float"
    BOOLEAN = "boolean"
    COLOR = "color"
    EMAIL = "email"
    URL = "url"
    LIST = "list"
    DICT = "dict"


class TemplateVariable(BaseModel):
    """Template variable definition"""
    name: str = Field(..., description="Variable name (used in templates)")
    type: VariableType = Field(..., description="Variable data type")
    required: bool = Field(default=True, description="Is this variable required?")
    default: Optional[Any] = Field(None, description="Default value if not provided")
    description: str = Field(default="", description="Variable description")
    validation: Optional[Dict[str, Any]] = Field(
        None,
        description="Validation rules (e.g., {'min_length': 3, 'max_length': 100})"
    )


class TemplateFile(BaseModel):
    """File to generate from template"""
    path: str = Field(..., description="Relative path in template directory")
    output_path: str = Field(..., description="Output path in generated project")
    is_template: bool = Field(
        default=True,
        description="Is this a Jinja2 template or a static file?"
    )


class Template(BaseModel):
    """Template metadata and configuration"""
    # Identity
    template_id: str = Field(..., description="Unique template identifier")
    version: str = Field(..., description="Semantic version (e.g., '1.0.0')")
    type: TemplateType = Field(..., description="Template type")

    # Metadata
    name: str = Field(..., description="Human-readable name")
    description: str = Field(..., description="Template description")
    author: str = Field(default="BRAiN Factory", description="Template author")
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)

    # Configuration
    variables: List[TemplateVariable] = Field(
        default_factory=list,
        description="Template variables"
    )
    files: List[TemplateFile] = Field(
        default_factory=list,
        description="Files to generate"
    )

    # Dependencies
    dependencies: List[str] = Field(
        default_factory=list,
        description="System dependencies (e.g., 'nodejs>=18', 'nginx')"
    )

    # Tags for searching
    tags: List[str] = Field(default_factory=list, description="Search tags")

    # Preview
    preview_url: Optional[str] = Field(
        None,
        description="URL to template preview/screenshot"
    )

    class Config:
        json_schema_extra = {
            "example": {
                "template_id": "modern_landing_v1",
                "version": "1.0.0",
                "type": "website",
                "name": "Modern Landing Page",
                "description": "Responsive landing page with hero, features, contact form",
                "variables": [
                    {
                        "name": "business_name",
                        "type": "string",
                        "required": True,
                        "description": "Business name for title and branding"
                    },
                    {
                        "name": "primary_color",
                        "type": "color",
                        "required": False,
                        "default": "#2563eb",
                        "description": "Primary brand color"
                    }
                ],
                "files": [
                    {
                        "path": "index.html.jinja2",
                        "output_path": "public/index.html",
                        "is_template": True
                    }
                ],
                "tags": ["landing", "modern", "responsive"]
            }
        }


class RenderedTemplate(BaseModel):
    """Result of template rendering"""
    template_id: str
    template_version: str
    output_directory: str
    files_generated: List[str] = Field(default_factory=list)
    variables_used: Dict[str, Any] = Field(default_factory=dict)
    render_time_seconds: float
    timestamp: datetime = Field(default_factory=datetime.utcnow)
    success: bool = True
    errors: List[str] = Field(default_factory=list)


class ValidationResult(BaseModel):
    """Template validation result"""
    is_valid: bool
    errors: List[str] = Field(default_factory=list)
    warnings: List[str] = Field(default_factory=list)
    validated_at: datetime = Field(default_factory=datetime.utcnow)
