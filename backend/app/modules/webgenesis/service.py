"""
WebGenesis Service - Website generation, build, and deployment

Business logic for:
- Static website generation from specs
- Build artifact creation
- Docker Compose deployment
- Lifecycle management

Sprint I: MVP
- Template A: Static HTML + Tailwind
- Path safety enforcement
- Docker Compose deployment
- Audit trail integration
"""

from __future__ import annotations

import hashlib
import json
import os
import re
import shutil
import subprocess
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

from loguru import logger

from .schemas import (
    WebsiteSpec,
    BuildResult,
    DeployResult,
    SiteManifest,
    SiteStatus,
    TemplateType,
    PageSpec,
    PageSection,
)


# ============================================================================
# Constants
# ============================================================================

# Storage base path (allowlist - only this path is allowed)
STORAGE_BASE = Path("storage/webgenesis")

# Allowed site ID pattern (prevent path traversal)
SITE_ID_PATTERN = re.compile(r"^[a-zA-Z0-9_-]+$")

# Template directory
TEMPLATES_DIR = Path(__file__).parent / "templates"

# Docker Compose base port
COMPOSE_BASE_PORT = 8080


# ============================================================================
# Helper Functions
# ============================================================================


def validate_site_id(site_id: str) -> bool:
    """
    Validate site ID for safety.

    Args:
        site_id: Site identifier to validate

    Returns:
        True if valid, False otherwise
    """
    return bool(SITE_ID_PATTERN.match(site_id))


def compute_hash(data: str) -> str:
    """
    Compute SHA-256 hash of data.

    Args:
        data: Data to hash

    Returns:
        Hex-encoded SHA-256 hash
    """
    return hashlib.sha256(data.encode("utf-8")).hexdigest()


def compute_file_hash(file_path: Path) -> str:
    """
    Compute SHA-256 hash of file.

    Args:
        file_path: Path to file

    Returns:
        Hex-encoded SHA-256 hash
    """
    sha256 = hashlib.sha256()
    with open(file_path, "rb") as f:
        for chunk in iter(lambda: f.read(4096), b""):
            sha256.update(chunk)
    return sha256.hexdigest()


def compute_directory_hash(directory: Path) -> str:
    """
    Compute hash of all files in directory (recursive).

    Args:
        directory: Directory to hash

    Returns:
        Combined SHA-256 hash
    """
    hashes = []

    for file_path in sorted(directory.rglob("*")):
        if file_path.is_file():
            file_hash = compute_file_hash(file_path)
            # Include relative path in hash to detect renames
            rel_path = file_path.relative_to(directory)
            combined = f"{rel_path}:{file_hash}"
            hashes.append(combined)

    # Hash all file hashes together
    combined_data = "\n".join(hashes)
    return compute_hash(combined_data)


def safe_path_join(base: Path, *parts: str) -> Path:
    """
    Safely join path parts, preventing traversal.

    Args:
        base: Base directory
        parts: Path parts to join

    Returns:
        Resolved absolute path

    Raises:
        ValueError: If resulting path is outside base
    """
    # Resolve to absolute path
    result = (base / Path(*parts)).resolve()

    # Ensure result is within base
    try:
        result.relative_to(base.resolve())
    except ValueError:
        raise ValueError(f"Path traversal detected: {result} is outside {base}")

    return result


# ============================================================================
# WebGenesis Service
# ============================================================================


class WebGenesisService:
    """
    WebGenesis Service for website generation and deployment.

    Features:
    - Static HTML + Tailwind generation
    - Build artifact creation
    - Docker Compose deployment
    - Path safety enforcement
    - Audit trail integration
    """

    def __init__(self, storage_base: Optional[Path] = None):
        """
        Initialize WebGenesis service.

        Args:
            storage_base: Storage base path (default: storage/webgenesis)
        """
        self.storage_base = storage_base or STORAGE_BASE
        self.storage_base.mkdir(parents=True, exist_ok=True)

        # Templates
        self.templates_dir = TEMPLATES_DIR

        # Metrics
        self.total_sites = 0
        self.total_generated = 0
        self.total_built = 0
        self.total_deployed = 0
        self.total_errors = 0

        logger.info(f"🌐 WebGenesis Service initialized (storage: {self.storage_base})")

    # ========================================================================
    # Site ID Generation
    # ========================================================================

    def generate_site_id(self, spec: WebsiteSpec) -> str:
        """
        Generate unique site ID from spec.

        Args:
            spec: Website specification

        Returns:
            Unique site ID
        """
        # Use spec name + timestamp for uniqueness
        timestamp = datetime.utcnow().strftime("%Y%m%d%H%M%S")
        site_id = f"{spec.name}_{timestamp}"

        # Ensure valid format
        site_id = re.sub(r"[^a-zA-Z0-9_-]", "_", site_id)

        return site_id

    # ========================================================================
    # Spec Storage
    # ========================================================================

    def store_spec(self, spec: WebsiteSpec) -> Tuple[str, str, SiteManifest]:
        """
        Store website spec and create manifest.

        Args:
            spec: Website specification

        Returns:
            Tuple of (site_id, spec_hash, manifest)

        Raises:
            ValueError: If spec is invalid
        """
        # Generate site ID
        site_id = self.generate_site_id(spec)

        if not validate_site_id(site_id):
            raise ValueError(f"Invalid site ID generated: {site_id}")

        # Create site directory
        site_dir = safe_path_join(self.storage_base, site_id)
        site_dir.mkdir(parents=True, exist_ok=True)

        # Compute spec hash
        spec_json = spec.model_dump_json(indent=2)
        spec_hash = compute_hash(spec_json)

        # Store spec
        spec_file = site_dir / "spec.json"
        with open(spec_file, "w") as f:
            f.write(spec_json)

        # Create manifest
        manifest = SiteManifest(
            site_id=site_id,
            name=spec.name,
            spec_version=spec.spec_version,
            spec_hash=spec_hash,
            status=SiteStatus.PENDING,
            template=spec.template,
            created_at=datetime.utcnow(),
            updated_at=datetime.utcnow(),
        )

        # Store manifest
        self._save_manifest(site_id, manifest)

        self.total_sites += 1

        logger.info(f"✅ Stored spec for site: {site_id} (hash: {spec_hash[:8]}...)")

        return site_id, spec_hash, manifest

    def _save_manifest(self, site_id: str, manifest: SiteManifest):
        """Save manifest to disk."""
        site_dir = safe_path_join(self.storage_base, site_id)
        manifest_file = site_dir / "manifest.json"

        manifest.updated_at = datetime.utcnow()

        with open(manifest_file, "w") as f:
            f.write(manifest.model_dump_json(indent=2))

    def _load_manifest(self, site_id: str) -> SiteManifest:
        """Load manifest from disk."""
        site_dir = safe_path_join(self.storage_base, site_id)
        manifest_file = site_dir / "manifest.json"

        if not manifest_file.exists():
            raise FileNotFoundError(f"Manifest not found for site: {site_id}")

        with open(manifest_file, "r") as f:
            data = json.load(f)

        return SiteManifest(**data)

    def _load_spec(self, site_id: str) -> WebsiteSpec:
        """Load spec from disk."""
        site_dir = safe_path_join(self.storage_base, site_id)
        spec_file = site_dir / "spec.json"

        if not spec_file.exists():
            raise FileNotFoundError(f"Spec not found for site: {site_id}")

        with open(spec_file, "r") as f:
            data = json.load(f)

        return WebsiteSpec(**data)

    # ========================================================================
    # Source Generation
    # ========================================================================

    def generate_project(
        self, site_id: str, force: bool = False
    ) -> Tuple[str, int, List[str]]:
        """
        Generate website source code from spec.

        Args:
            site_id: Site identifier
            force: Force regeneration if already exists

        Returns:
            Tuple of (source_path, files_created, errors)

        Raises:
            ValueError: If site_id is invalid
            FileNotFoundError: If site not found
        """
        if not validate_site_id(site_id):
            raise ValueError(f"Invalid site ID: {site_id}")

        # Load spec and manifest
        spec = self._load_spec(site_id)
        manifest = self._load_manifest(site_id)

        # Update status
        manifest.status = SiteStatus.GENERATING
        self._save_manifest(site_id, manifest)

        try:
            # Create source directory
            site_dir = safe_path_join(self.storage_base, site_id)
            source_dir = site_dir / "source"

            if source_dir.exists() and not force:
                raise ValueError(
                    f"Source already exists for site: {site_id}. Use force=True to regenerate."
                )

            # Remove existing source if force
            if source_dir.exists():
                shutil.rmtree(source_dir)

            source_dir.mkdir(parents=True, exist_ok=True)

            # Generate based on template type
            if spec.template == TemplateType.STATIC_HTML:
                files_created, errors = self._generate_static_html(spec, source_dir)
            else:
                raise ValueError(f"Unsupported template type: {spec.template}")

            # Update manifest
            manifest.status = SiteStatus.GENERATED
            manifest.generated_at = datetime.utcnow()
            manifest.source_path = str(source_dir.relative_to(self.storage_base))
            self._save_manifest(site_id, manifest)

            self.total_generated += 1

            logger.info(
                f"✅ Generated source for site: {site_id} ({files_created} files)"
            )

            return str(source_dir), files_created, errors

        except Exception as e:
            # Update manifest with error
            manifest.status = SiteStatus.FAILED
            manifest.last_error = str(e)
            manifest.error_count += 1
            self._save_manifest(site_id, manifest)

            self.total_errors += 1
            logger.error(f"❌ Failed to generate source for site {site_id}: {e}")

            raise

    def _generate_static_html(
        self, spec: WebsiteSpec, output_dir: Path
    ) -> Tuple[int, List[str]]:
        """
        Generate static HTML site.

        Args:
            spec: Website specification
            output_dir: Output directory

        Returns:
            Tuple of (files_created, errors)
        """
        files_created = 0
        errors = []

        # Load base template
        base_template_path = self.templates_dir / "base.html"
        with open(base_template_path, "r") as f:
            base_template = f.read()

        # Load sections template
        sections_template_path = self.templates_dir / "sections.html"
        with open(sections_template_path, "r") as f:
            sections_template = f.read()

        # Create assets directory
        assets_dir = output_dir / "assets"
        assets_dir.mkdir(parents=True, exist_ok=True)

        # Generate CSS
        css_content = self._generate_css(spec)
        css_file = assets_dir / "styles.css"
        with open(css_file, "w") as f:
            f.write(css_content)
        files_created += 1

        # Generate pages
        for page in spec.pages:
            try:
                html_content = self._render_page(
                    spec, page, base_template, sections_template
                )

                # Determine filename
                if page.slug == "home" or page.slug == "index":
                    filename = "index.html"
                else:
                    filename = f"{page.slug}.html"

                page_file = output_dir / filename
                with open(page_file, "w") as f:
                    f.write(html_content)

                files_created += 1

            except Exception as e:
                errors.append(f"Failed to render page '{page.slug}': {e}")
                logger.warning(f"⚠️ Failed to render page '{page.slug}': {e}")

        return files_created, errors

    def _generate_css(self, spec: WebsiteSpec) -> str:
        """Generate custom CSS from theme."""
        return f"""/* WebGenesis Generated Styles */

:root {{
    --color-primary: {spec.theme.colors.primary};
    --color-secondary: {spec.theme.colors.secondary};
    --color-accent: {spec.theme.colors.accent};
    --color-background: {spec.theme.colors.background};
    --color-text: {spec.theme.colors.text};
}}

/* Custom utilities */
.btn {{
    @apply px-6 py-3 rounded-lg font-semibold transition-all duration-200;
}}

.btn-primary {{
    @apply bg-primary text-white hover:opacity-90;
}}

.btn-secondary {{
    @apply bg-secondary text-white hover:opacity-90;
}}

.btn-accent {{
    @apply bg-accent text-white hover:opacity-90;
}}

/* Feature card */
.feature-card {{
    @apply bg-white p-6 rounded-lg shadow-md hover:shadow-lg transition-shadow;
}}

/* Prose enhancements */
.prose {{
    color: {spec.theme.colors.text};
}}
"""

    def _render_page(
        self,
        spec: WebsiteSpec,
        page: PageSpec,
        base_template: str,
        sections_template: str,
    ) -> str:
        """
        Render a single page.

        Args:
            spec: Website spec
            page: Page spec
            base_template: Base HTML template
            sections_template: Sections template

        Returns:
            Rendered HTML
        """
        import datetime

        # Prepare navigation links
        nav_links = []
        for nav_page in spec.pages:
            slug = "index" if nav_page.slug in ["home", "index"] else nav_page.slug
            current_slug = "index" if page.slug in ["home", "index"] else page.slug
            active_class = " bg-primary/10 text-primary" if slug == current_slug else ""

            nav_links.append(
                f'<a href="/{slug}.html" '
                f'class="text-gray-700 hover:text-primary transition-colors px-3 py-2 rounded-md text-sm font-medium{active_class}">'
                f"{nav_page.title}</a>"
            )

        navigation_html = "\n".join(nav_links)

        # Render sections
        page_content_html = self._render_sections(page.sections, sections_template)

        # Prepare template variables
        template_vars = {
            # Meta
            "locale": spec.locale_default,
            "page_title": page.title,
            "page_description": page.description or spec.seo.description,
            "site_name": spec.name,
            "current_year": datetime.datetime.utcnow().year,
            # SEO
            "seo_keywords_meta": (
                f'<meta name="keywords" content="{", ".join(spec.seo.keywords)}">'
                if spec.seo.keywords
                else ""
            ),
            "og_image_meta": (
                f'<meta property="og:image" content="{spec.seo.og_image}">'
                if spec.seo.og_image
                else ""
            ),
            "twitter_card": spec.seo.twitter_card,
            # Theme
            "theme_primary": spec.theme.colors.primary,
            "theme_secondary": spec.theme.colors.secondary,
            "theme_accent": spec.theme.colors.accent,
            "theme_background": spec.theme.colors.background,
            "theme_text": spec.theme.colors.text,
            "theme_font_family": spec.theme.typography.font_family,
            "theme_base_size": spec.theme.typography.base_size,
            "heading_font_style": (
                f"font-family: {spec.theme.typography.heading_font};"
                if spec.theme.typography.heading_font
                else ""
            ),
            # Content
            "navigation_links": navigation_html,
            "page_content": page_content_html,
        }

        # Render template
        html = base_template.format(**template_vars)

        return html

    def _render_sections(
        self, sections: List[PageSection], sections_template: str
    ) -> str:
        """
        Render page sections.

        Args:
            sections: List of page sections
            sections_template: Sections template

        Returns:
            Rendered sections HTML
        """
        # Sort sections by order
        sorted_sections = sorted(sections, key=lambda s: s.order)

        rendered_sections = []

        for section in sorted_sections:
            section_html = self._render_section(section)
            rendered_sections.append(section_html)

        return "\n\n".join(rendered_sections)

    def _render_section(self, section: PageSection) -> str:
        """
        Render a single section.

        Args:
            section: Section spec

        Returns:
            Rendered section HTML
        """
        section_type = section.type.lower()

        if section_type == "hero":
            return self._render_hero_section(section)
        elif section_type == "features":
            return self._render_features_section(section)
        elif section_type == "content":
            return self._render_content_section(section)
        elif section_type == "cta":
            return self._render_cta_section(section)
        elif section_type == "contact":
            return self._render_contact_section(section)
        else:
            # Default: content section
            return self._render_content_section(section)

    def _render_hero_section(self, section: PageSection) -> str:
        """Render hero section."""
        cta_html = ""
        if section.data.get("cta_text") and section.data.get("cta_link"):
            cta_html = f"""
        <a href="{section.data['cta_link']}" class="btn btn-accent inline-block">
            {section.data['cta_text']}
        </a>
            """

        return f"""
<section class="hero bg-gradient-to-r from-primary to-secondary text-white py-20">
    <div class="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 text-center">
        <h1 class="text-4xl sm:text-5xl md:text-6xl font-bold mb-6">
            {section.title or ""}
        </h1>
        <p class="text-xl sm:text-2xl mb-8 text-white/90">
            {section.content or ""}
        </p>
        {cta_html}
    </div>
</section>
        """

    def _render_features_section(self, section: PageSection) -> str:
        """Render features section."""
        items = section.data.get("items", [])
        items_html = []

        for item in items:
            title = item.get("title", "")
            description = item.get("description", "")

            items_html.append(
                f"""
            <div class="feature-card">
                <h3 class="text-xl font-bold mb-2">{title}</h3>
                <p class="text-gray-600">{description}</p>
            </div>
                """
            )

        features_grid = "\n".join(items_html)

        return f"""
<section class="features py-16 bg-gray-50">
    <div class="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
        <h2 class="text-3xl font-bold text-center mb-12 text-gray-900">
            {section.title or "Features"}
        </h2>
        <div class="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-8">
            {features_grid}
        </div>
    </div>
</section>
        """

    def _render_content_section(self, section: PageSection) -> str:
        """Render content section."""
        # Simple markdown-like conversion
        content = section.content or ""
        content_html = content.replace("\n\n", "</p><p>")
        content_html = f"<p>{content_html}</p>"

        return f"""
<section class="content py-16">
    <div class="max-w-4xl mx-auto px-4 sm:px-6 lg:px-8">
        <h2 class="text-3xl font-bold mb-6 text-gray-900">
            {section.title or ""}
        </h2>
        <div class="prose prose-lg max-w-none">
            {content_html}
        </div>
    </div>
</section>
        """

    def _render_cta_section(self, section: PageSection) -> str:
        """Render CTA section."""
        buttons_html = ""
        if section.data.get("button_text") and section.data.get("button_link"):
            buttons_html = f"""
        <a href="{section.data['button_link']}" class="btn btn-accent inline-block">
            {section.data['button_text']}
        </a>
            """

        return f"""
<section class="cta bg-primary text-white py-16">
    <div class="max-w-4xl mx-auto px-4 sm:px-6 lg:px-8 text-center">
        <h2 class="text-3xl font-bold mb-4">
            {section.title or ""}
        </h2>
        <p class="text-xl mb-8 text-white/90">
            {section.content or ""}
        </p>
        {buttons_html}
    </div>
</section>
        """

    def _render_contact_section(self, section: PageSection) -> str:
        """Render contact section."""
        return f"""
<section class="contact py-16">
    <div class="max-w-2xl mx-auto px-4 sm:px-6 lg:px-8">
        <h2 class="text-3xl font-bold text-center mb-12 text-gray-900">
            {section.title or "Contact"}
        </h2>
        <div class="bg-white shadow-md rounded-lg p-8">
            <p class="text-gray-700">
                {section.content or "Get in touch with us."}
            </p>
        </div>
    </div>
</section>
        """


# ============================================================================
# Singleton
# ============================================================================

_webgenesis_service: Optional[WebGenesisService] = None


def get_webgenesis_service() -> WebGenesisService:
    """Get singleton WebGenesis service instance."""
    global _webgenesis_service
    if _webgenesis_service is None:
        _webgenesis_service = WebGenesisService()
    return _webgenesis_service
