"""
WebGenesis Module - Data Models

Schemas for website generation, build, and deployment.
Sprint I: MVP for static website generation and Docker Compose deployment.
"""

from __future__ import annotations

from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Literal, Optional

from pydantic import BaseModel, Field, validator


# ============================================================================
# Enums
# ============================================================================


class DeployTarget(str, Enum):
    """Deployment target type"""

    COMPOSE = "compose"  # Docker Compose (MVP)
    COOLIFY = "coolify"  # Coolify (future)
    KUBERNETES = "kubernetes"  # K8s (future)


class SiteStatus(str, Enum):
    """Website deployment status"""

    PENDING = "pending"  # Spec received, not yet generated
    GENERATING = "generating"  # Source code being generated
    GENERATED = "generated"  # Source code ready
    BUILDING = "building"  # Building artifacts
    BUILT = "built"  # Build artifacts ready
    DEPLOYING = "deploying"  # Deploying to target
    DEPLOYED = "deployed"  # Successfully deployed
    FAILED = "failed"  # Deployment failed
    STOPPED = "stopped"  # Deployment stopped


class TemplateType(str, Enum):
    """Website template type"""

    STATIC_HTML = "static_html"  # Static HTML + Tailwind (MVP)
    NEXTJS = "nextjs"  # Next.js static export (future)
    ASTRO = "astro"  # Astro static (future)


# ============================================================================
# Sub-Models
# ============================================================================


class PageSection(BaseModel):
    """Single section within a page"""

    section_id: str = Field(..., description="Unique section identifier")
    type: str = Field(
        ..., description="Section type (hero, features, cta, content, etc.)"
    )
    title: Optional[str] = Field(None, description="Section title")
    content: Optional[str] = Field(None, description="Section content (markdown)")
    data: Dict[str, Any] = Field(
        default_factory=dict, description="Additional section data"
    )
    order: int = Field(0, description="Display order")

    class Config:
        json_schema_extra = {
            "example": {
                "section_id": "hero_1",
                "type": "hero",
                "title": "Welcome to Our Platform",
                "content": "Build amazing things with our tools",
                "data": {"background_image": "/assets/hero.jpg"},
                "order": 0,
            }
        }


class PageSpec(BaseModel):
    """Single page specification"""

    slug: str = Field(..., description="URL slug (e.g., 'about', 'contact')")
    title: str = Field(..., description="Page title")
    description: Optional[str] = Field(None, description="Page meta description")
    sections: List[PageSection] = Field(
        default_factory=list, description="Page sections"
    )
    layout: str = Field("default", description="Page layout template")

    class Config:
        json_schema_extra = {
            "example": {
                "slug": "home",
                "title": "Home",
                "description": "Welcome to our website",
                "sections": [],
                "layout": "default",
            }
        }


class ThemeColors(BaseModel):
    """Theme color palette"""

    primary: str = Field("#3B82F6", description="Primary brand color")
    secondary: str = Field("#8B5CF6", description="Secondary color")
    accent: str = Field("#10B981", description="Accent color")
    background: str = Field("#FFFFFF", description="Background color")
    text: str = Field("#1F2937", description="Text color")

    class Config:
        json_schema_extra = {
            "example": {
                "primary": "#3B82F6",
                "secondary": "#8B5CF6",
                "accent": "#10B981",
                "background": "#FFFFFF",
                "text": "#1F2937",
            }
        }


class ThemeTypography(BaseModel):
    """Theme typography settings"""

    font_family: str = Field(
        "Inter, system-ui, sans-serif", description="Font family"
    )
    heading_font: Optional[str] = Field(None, description="Heading font (optional)")
    base_size: str = Field("16px", description="Base font size")

    class Config:
        json_schema_extra = {
            "example": {
                "font_family": "Inter, system-ui, sans-serif",
                "heading_font": "Montserrat, sans-serif",
                "base_size": "16px",
            }
        }


class Theme(BaseModel):
    """Website theme configuration"""

    colors: ThemeColors = Field(default_factory=ThemeColors, description="Color palette")
    typography: ThemeTypography = Field(
        default_factory=ThemeTypography, description="Typography settings"
    )

    class Config:
        json_schema_extra = {"example": {"colors": {}, "typography": {}}}


class SEOConfig(BaseModel):
    """SEO configuration"""

    title: str = Field(..., description="Default site title")
    description: str = Field(..., description="Default meta description")
    keywords: List[str] = Field(default_factory=list, description="SEO keywords")
    og_image: Optional[str] = Field(None, description="Open Graph image URL")
    twitter_card: Literal["summary", "summary_large_image"] = Field(
        "summary", description="Twitter card type"
    )

    class Config:
        json_schema_extra = {
            "example": {
                "title": "My Awesome Website",
                "description": "Building amazing things",
                "keywords": ["tech", "innovation"],
                "og_image": "/assets/og-image.jpg",
                "twitter_card": "summary_large_image",
            }
        }


class DeployConfig(BaseModel):
    """Deployment configuration"""

    target: DeployTarget = Field(
        DeployTarget.COMPOSE, description="Deployment target"
    )
    base_path: Optional[str] = Field(
        None, description="Base path for deployment (default: storage/webgenesis)"
    )
    ports: List[int] = Field(
        default_factory=list, description="Ports to expose (default: auto-assign 808x)"
    )
    healthcheck_path: str = Field("/", description="Health check endpoint path")
    domain: Optional[str] = Field(None, description="Custom domain (optional)")
    ssl_enabled: bool = Field(False, description="Enable SSL (future)")

    class Config:
        json_schema_extra = {
            "example": {
                "target": "compose",
                "base_path": "/srv/brain/websites",
                "ports": [8080],
                "healthcheck_path": "/",
                "domain": "example.com",
                "ssl_enabled": False,
            }
        }


# ============================================================================
# Main Models
# ============================================================================


class WebsiteSpec(BaseModel):
    """
    Complete website specification.

    This is the input from users to generate a website.
    """

    spec_version: str = Field("1.0.0", description="Spec version (semver)")
    name: str = Field(..., description="Website name/identifier")
    domain: Optional[str] = Field(None, description="Primary domain")
    locale_default: str = Field("en", description="Default locale")
    locales: List[str] = Field(default_factory=lambda: ["en"], description="Supported locales")

    template: TemplateType = Field(
        TemplateType.STATIC_HTML, description="Template type to use"
    )
    pages: List[PageSpec] = Field(..., description="Website pages", min_length=1)
    theme: Theme = Field(default_factory=Theme, description="Theme configuration")
    seo: SEOConfig = Field(..., description="SEO configuration")
    deploy: DeployConfig = Field(
        default_factory=DeployConfig, description="Deployment configuration"
    )

    metadata: Dict[str, Any] = Field(
        default_factory=dict, description="Extra metadata"
    )

    @validator("pages")
    def validate_pages(cls, v):
        """Ensure at least one page and unique slugs"""
        if not v:
            raise ValueError("At least one page is required")

        slugs = [p.slug for p in v]
        if len(slugs) != len(set(slugs)):
            raise ValueError("Page slugs must be unique")

        return v

    @validator("name")
    def validate_name(cls, v):
        """Ensure name is safe for filesystem"""
        import re
        if not re.match(r"^[a-zA-Z0-9_-]+$", v):
            raise ValueError(
                "Name must contain only alphanumeric characters, hyphens, and underscores"
            )
        return v

    class Config:
        json_schema_extra = {
            "example": {
                "spec_version": "1.0.0",
                "name": "my-awesome-site",
                "domain": "example.com",
                "locale_default": "en",
                "locales": ["en", "de"],
                "template": "static_html",
                "pages": [
                    {
                        "slug": "home",
                        "title": "Home",
                        "description": "Welcome page",
                        "sections": [],
                    }
                ],
                "seo": {
                    "title": "My Awesome Site",
                    "description": "Building amazing things",
                },
                "deploy": {"target": "compose"},
            }
        }


class BuildResult(BaseModel):
    """Result of build operation"""

    success: bool = Field(..., description="Build success status")
    site_id: str = Field(..., description="Site identifier")
    artifact_path: Optional[str] = Field(None, description="Path to build artifacts")
    artifact_hash: Optional[str] = Field(
        None, description="SHA-256 hash of build artifacts"
    )
    timestamp: datetime = Field(
        default_factory=datetime.utcnow, description="Build timestamp"
    )
    errors: List[str] = Field(default_factory=list, description="Build errors if any")
    warnings: List[str] = Field(
        default_factory=list, description="Build warnings if any"
    )
    build_log: Optional[str] = Field(None, description="Build log output")

    class Config:
        json_schema_extra = {
            "example": {
                "success": True,
                "site_id": "site_001",
                "artifact_path": "/storage/webgenesis/site_001/build",
                "artifact_hash": "a1b2c3d4...",
                "timestamp": "2025-01-01T12:00:00",
                "errors": [],
                "warnings": [],
            }
        }


class DeployResult(BaseModel):
    """Result of deployment operation"""

    success: bool = Field(..., description="Deployment success status")
    site_id: str = Field(..., description="Site identifier")
    url: Optional[str] = Field(None, description="Deployed website URL")
    container_id: Optional[str] = Field(None, description="Docker container ID")
    container_name: Optional[str] = Field(None, description="Docker container name")
    ports: List[int] = Field(default_factory=list, description="Exposed ports")
    timestamp: datetime = Field(
        default_factory=datetime.utcnow, description="Deployment timestamp"
    )
    errors: List[str] = Field(
        default_factory=list, description="Deployment errors if any"
    )
    warnings: List[str] = Field(
        default_factory=list, description="Deployment warnings if any"
    )
    deploy_log: Optional[str] = Field(None, description="Deployment log output")

    class Config:
        json_schema_extra = {
            "example": {
                "success": True,
                "site_id": "site_001",
                "url": "http://localhost:8080",
                "container_id": "abc123def456",
                "container_name": "webgenesis-site_001",
                "ports": [8080],
                "timestamp": "2025-01-01T12:00:00",
                "errors": [],
                "warnings": [],
            }
        }


class SiteManifest(BaseModel):
    """
    Site manifest - comprehensive metadata for deployed site.

    Stored as manifest.json in site directory.
    """

    site_id: str = Field(..., description="Unique site identifier")
    name: str = Field(..., description="Site name")
    spec_version: str = Field(..., description="Spec version used")
    spec_hash: str = Field(..., description="SHA-256 hash of original spec")
    artifact_hash: Optional[str] = Field(
        None, description="SHA-256 hash of build artifacts"
    )

    status: SiteStatus = Field(SiteStatus.PENDING, description="Current site status")
    template: TemplateType = Field(..., description="Template type used")

    # Timestamps
    created_at: datetime = Field(
        default_factory=datetime.utcnow, description="Creation timestamp"
    )
    updated_at: datetime = Field(
        default_factory=datetime.utcnow, description="Last update timestamp"
    )
    generated_at: Optional[datetime] = Field(
        None, description="Source generation timestamp"
    )
    built_at: Optional[datetime] = Field(None, description="Build timestamp")
    deployed_at: Optional[datetime] = Field(None, description="Deployment timestamp")

    # Deployment info
    deployed_url: Optional[str] = Field(None, description="Deployed URL")
    deployed_ports: List[int] = Field(
        default_factory=list, description="Deployed ports"
    )
    docker_container_id: Optional[str] = Field(None, description="Docker container ID")
    docker_image_tag: Optional[str] = Field(None, description="Docker image tag used")

    # Paths
    source_path: Optional[str] = Field(None, description="Generated source path")
    build_path: Optional[str] = Field(None, description="Build artifacts path")
    deploy_path: Optional[str] = Field(None, description="Deployment path")

    # Error tracking
    last_error: Optional[str] = Field(None, description="Last error message")
    error_count: int = Field(0, description="Total error count")

    metadata: Dict[str, Any] = Field(
        default_factory=dict, description="Extra metadata"
    )

    class Config:
        json_schema_extra = {
            "example": {
                "site_id": "site_001",
                "name": "my-awesome-site",
                "spec_version": "1.0.0",
                "spec_hash": "a1b2c3d4e5f6...",
                "artifact_hash": "f6e5d4c3b2a1...",
                "status": "deployed",
                "template": "static_html",
                "created_at": "2025-01-01T12:00:00",
                "deployed_url": "http://localhost:8080",
                "deployed_ports": [8080],
            }
        }


# ============================================================================
# API Request/Response Models
# ============================================================================


class SpecSubmitRequest(BaseModel):
    """Request to submit a website spec"""

    spec: WebsiteSpec = Field(..., description="Website specification")

    class Config:
        json_schema_extra = {"example": {"spec": {}}}


class SpecSubmitResponse(BaseModel):
    """Response after spec submission"""

    success: bool = Field(..., description="Submission success")
    site_id: str = Field(..., description="Generated site ID")
    spec_hash: str = Field(..., description="Spec hash for verification")
    message: str = Field(..., description="Status message")

    class Config:
        json_schema_extra = {
            "example": {
                "success": True,
                "site_id": "site_001",
                "spec_hash": "a1b2c3d4e5f6...",
                "message": "Spec received and stored successfully",
            }
        }


class GenerateRequest(BaseModel):
    """Request to generate source code (optional override params)"""

    force: bool = Field(False, description="Force regeneration if already exists")

    class Config:
        json_schema_extra = {"example": {"force": False}}


class GenerateResponse(BaseModel):
    """Response after source generation"""

    success: bool = Field(..., description="Generation success")
    site_id: str = Field(..., description="Site ID")
    source_path: str = Field(..., description="Path to generated source")
    files_created: int = Field(..., description="Number of files created")
    message: str = Field(..., description="Status message")
    errors: List[str] = Field(default_factory=list, description="Errors if any")

    class Config:
        json_schema_extra = {
            "example": {
                "success": True,
                "site_id": "site_001",
                "source_path": "storage/webgenesis/site_001/source",
                "files_created": 5,
                "message": "Source generated successfully",
                "errors": [],
            }
        }


class BuildRequest(BaseModel):
    """Request to build artifacts"""

    force: bool = Field(False, description="Force rebuild if already exists")

    class Config:
        json_schema_extra = {"example": {"force": False}}


class BuildResponse(BaseModel):
    """Response after build"""

    result: BuildResult = Field(..., description="Build result details")
    message: str = Field(..., description="Status message")

    class Config:
        json_schema_extra = {
            "example": {
                "result": {},
                "message": "Build completed successfully",
            }
        }


class DeployRequest(BaseModel):
    """Request to deploy site"""

    force: bool = Field(False, description="Force redeploy if already deployed")

    class Config:
        json_schema_extra = {"example": {"force": False}}


class DeployResponse(BaseModel):
    """Response after deployment"""

    result: DeployResult = Field(..., description="Deployment result details")
    message: str = Field(..., description="Status message")

    class Config:
        json_schema_extra = {
            "example": {
                "result": {},
                "message": "Deployment completed successfully",
            }
        }


class SiteStatusResponse(BaseModel):
    """Response for site status query"""

    site_id: str = Field(..., description="Site ID")
    manifest: SiteManifest = Field(..., description="Site manifest")
    is_running: bool = Field(..., description="Whether site container is running")
    health_status: Optional[str] = Field(None, description="Health check status")

    class Config:
        json_schema_extra = {
            "example": {
                "site_id": "site_001",
                "manifest": {},
                "is_running": True,
                "health_status": "healthy",
            }
        }


# ============================================================================
# Audit Event Models
# ============================================================================


class WebGenesisAuditEvent(BaseModel):
    """Audit event for WebGenesis operations"""

    event_type: Literal[
        "spec_received",
        "generate_started",
        "generate_finished",
        "build_started",
        "build_finished",
        "deploy_started",
        "deploy_finished",
        "deploy_failed",
        "site_stopped",
        "site_deleted",
    ]
    site_id: str
    status: str  # success, failure, warning
    details: Dict[str, Any] = Field(default_factory=dict)
    timestamp: datetime = Field(default_factory=datetime.utcnow)
    user_id: Optional[str] = Field(None, description="User who triggered action")
    trust_tier: Optional[str] = Field(None, description="Request trust tier")

    class Config:
        json_schema_extra = {
            "example": {
                "event_type": "deploy_finished",
                "site_id": "site_001",
                "status": "success",
                "details": {"url": "http://localhost:8080"},
                "timestamp": "2025-01-01T12:00:00",
                "trust_tier": "dmz",
            }
        }
