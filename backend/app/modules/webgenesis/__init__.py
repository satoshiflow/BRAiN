"""
WebGenesis Module

AI-powered website generation and deployment system.

Sprint I: MVP
- Static HTML + Tailwind template generation
- Docker Compose deployment
- Audit trail integration
- DMZ/Trust tier enforcement

Sprint II: Operational Hardening + DNS Automation
- Lifecycle management (start/stop/restart/remove)
- Health monitoring + auto-rollback
- Release snapshots + retention policy
- Hetzner DNS integration (automatic record creation)

Features:
- Spec-based website generation
- Build artifact hashing
- Safe deployment with Docker Compose
- Release management for rollback capability
- Automatic DNS record creation
- Comprehensive audit logging
- Trust tier access control

Security:
- Path traversal protection
- Subprocess injection prevention
- DMZ/LOCAL only deployment (DNS: LOCAL only)
- Fail-closed policy enforcement
- Audit trail for all operations
- File locking for operation safety
"""

from .schemas import (
    # Enums (Sprint I)
    DeployTarget,
    SiteStatus,
    TemplateType,
    # Enums (Sprint II)
    SiteLifecycleStatus,
    HealthStatus,
    # Core Models (Sprint I)
    WebsiteSpec,
    BuildResult,
    DeployResult,
    SiteManifest,
    # Sub-Models (Sprint I)
    PageSpec,
    PageSection,
    Theme,
    SEOConfig,
    DeployConfig,
    DNSConfig,  # Sprint II
    # API Models (Sprint I)
    SpecSubmitRequest,
    SpecSubmitResponse,
    GenerateResponse,
    BuildResponse,
    DeployResponse,
    SiteStatusResponse,
    # Sprint II Models
    ReleaseMetadata,
    SiteOperationalStatus,
    LifecycleOperationResponse,
    RemoveRequest,
    RemoveResponse,
    RollbackRequest,
    RollbackResponse,
    ReleasesListResponse,
    # Audit
    WebGenesisAuditEvent,
)

from .service import (
    WebGenesisService,
    get_webgenesis_service,
)

from .releases import (
    ReleaseManager,
    get_release_manager,
)

from .router import router

__all__ = [
    # Enums (Sprint I)
    "DeployTarget",
    "SiteStatus",
    "TemplateType",
    # Enums (Sprint II)
    "SiteLifecycleStatus",
    "HealthStatus",
    # Core Models (Sprint I)
    "WebsiteSpec",
    "BuildResult",
    "DeployResult",
    "SiteManifest",
    # Sub-Models (Sprint I)
    "PageSpec",
    "PageSection",
    "Theme",
    "SEOConfig",
    "DeployConfig",
    "DNSConfig",  # Sprint II
    # API Models (Sprint I)
    "SpecSubmitRequest",
    "SpecSubmitResponse",
    "GenerateResponse",
    "BuildResponse",
    "DeployResponse",
    "SiteStatusResponse",
    # Sprint II Models
    "ReleaseMetadata",
    "SiteOperationalStatus",
    "LifecycleOperationResponse",
    "RemoveRequest",
    "RemoveResponse",
    "RollbackRequest",
    "RollbackResponse",
    "ReleasesListResponse",
    # Audit
    "WebGenesisAuditEvent",
    # Service
    "WebGenesisService",
    "get_webgenesis_service",
    # Release Manager (Sprint II)
    "ReleaseManager",
    "get_release_manager",
    # Router
    "router",
]

__version__ = "2.0.0"  # Sprint II
__module_name__ = "brain.webgenesis"
