"""
Template Registry Module

Manages templates for website generation, Odoo configurations, and integrations.
Provides template loading, validation, versioning, and rendering capabilities.

Version: 1.0.0
"""

from backend.app.modules.template_registry.loader import TemplateLoader
from backend.app.modules.template_registry.validator import TemplateValidator
from backend.app.modules.template_registry.schemas import (
    Template,
    TemplateType,
    TemplateVariable,
    RenderedTemplate,
)

__all__ = [
    "TemplateLoader",
    "TemplateValidator",
    "Template",
    "TemplateType",
    "TemplateVariable",
    "RenderedTemplate",
]
