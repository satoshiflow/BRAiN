"""
WebGenesis Module

AI-powered website generation and deployment system.

Sprint I: MVP
- Static HTML + Tailwind template generation
- Docker Compose deployment
- Audit trail integration
- DMZ/Trust tier enforcement

Features:
- Spec-based website generation
- Build artifact hashing
- Safe deployment with Docker Compose
- Comprehensive audit logging
- Trust tier access control

Security:
- Path traversal protection
- Subprocess injection prevention
- DMZ/LOCAL only deployment
- Fail-closed policy enforcement
- Audit trail for all operations
"""

from .schemas import (
    # Enums
    DeployTarget,
    SiteStatus,
    TemplateType,
    # Core Models
    WebsiteSpec,
    BuildResult,
    DeployResult,
    SiteManifest,
    # Sub-Models
    PageSpec,
    PageSection,
    Theme,
    SEOConfig,
    DeployConfig,
    # API Models
    SpecSubmitRequest,
    SpecSubmitResponse,
    GenerateResponse,
    BuildResponse,
    DeployResponse,
    SiteStatusResponse,
    # Audit
    WebGenesisAuditEvent,
)

__all__ = [
    # Enums
    "DeployTarget",
    "SiteStatus",
    "TemplateType",
    # Core Models
    "WebsiteSpec",
    "BuildResult",
    "DeployResult",
    "SiteManifest",
    # Sub-Models
    "PageSpec",
    "PageSection",
    "Theme",
    "SEOConfig",
    "DeployConfig",
    # API Models
    "SpecSubmitRequest",
    "SpecSubmitResponse",
    "GenerateResponse",
    "BuildResponse",
    "DeployResponse",
    "SiteStatusResponse",
    # Audit
    "WebGenesisAuditEvent",
]

__version__ = "1.0.0"
__module_name__ = "brain.webgenesis"
