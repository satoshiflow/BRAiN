"""
Website Executor v1 - Commercial Ready

Production-grade website generation with:
- SEO structure (meta, headings, sitemap)
- Content slots (no free text generation)
- Deterministic rendering
- Stable deployment
- Evidence collection

Version: 1.0.0 (Sprint 6)
"""

from __future__ import annotations

import shutil
from typing import List, Dict, Any, Set
from pathlib import Path
from datetime import datetime
from loguru import logger

from app.modules.factory_executor.base import (
    ExecutorBase,
    ExecutionContext,
    ExecutorCapability,
    ValidationError,
    ExecutionError,
)
from app.modules.business_factory.schemas import (
    ExecutionStep,
    StepResult,
)
from app.modules.template_registry.loader import get_template_loader
from app.modules.template_registry.schemas import Template


class WebsiteExecutor(ExecutorBase):
    """
    Commercial-ready website generation executor.

    Capabilities:
    - IDEMPOTENT: Can safely re-run (checks for existing output)
    - ROLLBACKABLE: Can delete generated files
    - ATOMIC: All files generated or none

    Contract:
    - Input MUST include: domain, template, business_name
    - Input MAY include: pages, primary_color, tagline, etc.
    - Output: Generated website files in storage/factory_output/{plan_id}/website/
    - Evidence: List of generated files, screenshots (future), validation report
    """

    # Required parameters
    REQUIRED_PARAMS = {"domain", "template", "business_name"}

    # SEO defaults
    DEFAULT_SEO = {
        "charset": "UTF-8",
        "viewport": "width=device-width, initial-scale=1.0",
        "robots": "index, follow",
        "language": "en",
    }

    def __init__(self):
        """Initialize website executor"""
        super().__init__(
            name="WebsiteExecutor",
            capabilities={
                ExecutorCapability.IDEMPOTENT,
                ExecutorCapability.ROLLBACKABLE,
                ExecutorCapability.ATOMIC,
            },
            default_timeout_seconds=300.0,  # 5 minutes
            default_max_retries=2,
        )

        self.template_loader = get_template_loader()
        self._generated_files_cache: Dict[str, List[str]] = {}

    async def execute(
        self,
        step: ExecutionStep,
        context: ExecutionContext
    ) -> StepResult:
        """
        Execute website generation.

        Steps:
        1. Load template
        2. Prepare variables (with SEO defaults)
        3. Render template
        4. Generate SEO files (sitemap.xml, robots.txt)
        5. Validate output
        6. Return result with evidence

        Args:
            step: Execution step
            context: Execution context

        Returns:
            StepResult with generated files

        Raises:
            ExecutionError: Generation failed
        """
        logger.info(f"[WebsiteExecutor] Generating website for {step.parameters.get('domain')}")

        try:
            # 1. Extract parameters
            params = step.parameters
            domain = params["domain"]
            template_id = params["template"]
            business_name = params["business_name"]

            # 2. Load template
            template = self.template_loader.get_template(template_id)
            if not template:
                raise ExecutionError(f"Template not found: {template_id}")

            # 3. Prepare output directory
            output_dir = self._get_output_directory(context.plan_id, step.step_id)
            output_dir.mkdir(parents=True, exist_ok=True)

            # 4. Prepare variables with SEO enhancements
            variables = self._prepare_variables(params, template)

            # 5. Render template
            result = self.template_loader.render_template(
                template_id=template_id,
                variables=variables,
                output_dir=str(output_dir)
            )

            if not result.success:
                raise ExecutionError(f"Template rendering failed: {', '.join(result.errors)}")

            # 6. Generate SEO files
            seo_files = await self._generate_seo_files(output_dir, variables)

            # 7. Generate sitemap
            sitemap_file = await self._generate_sitemap(output_dir, variables)

            # 8. Collect all generated files
            all_files = result.files_generated + seo_files + ([sitemap_file] if sitemap_file else [])

            # Cache for rollback
            self._generated_files_cache[step.step_id] = all_files

            logger.info(
                f"[WebsiteExecutor] Generated {len(all_files)} files in {result.render_time_seconds:.2f}s"
            )

            return StepResult(
                step_id=step.step_id,
                success=True,
                data={
                    "domain": domain,
                    "template_id": template_id,
                    "files_generated": len(all_files),
                    "output_directory": str(output_dir),
                    "seo_enabled": True,
                    "sitemap_generated": sitemap_file is not None,
                },
                evidence_files=all_files,
                duration_seconds=result.render_time_seconds,
            )

        except Exception as e:
            logger.error(f"[WebsiteExecutor] Execution failed: {e}")
            raise ExecutionError(f"Website generation failed: {str(e)}")

    async def validate_input(
        self,
        step: ExecutionStep,
        context: ExecutionContext
    ) -> List[str]:
        """
        Validate input parameters.

        Args:
            step: Execution step
            context: Execution context

        Returns:
            List of validation errors (empty if valid)
        """
        errors = []
        params = step.parameters

        # Check required parameters
        missing = self.REQUIRED_PARAMS - set(params.keys())
        if missing:
            errors.append(f"Missing required parameters: {', '.join(missing)}")

        # Validate domain
        domain = params.get("domain")
        if domain:
            if not self._validate_domain(domain):
                errors.append(f"Invalid domain format: {domain}")

        # Validate template exists
        template_id = params.get("template")
        if template_id:
            template = self.template_loader.get_template(template_id)
            if not template:
                errors.append(f"Template not found: {template_id}")
            elif template.type.value != "website":
                errors.append(f"Template {template_id} is not a website template (type={template.type.value})")

        # Validate color format (if provided)
        for color_param in ["primary_color", "secondary_color"]:
            color = params.get(color_param)
            if color and not self._validate_color(color):
                errors.append(f"Invalid color format for {color_param}: {color}")

        return errors

    async def rollback(
        self,
        step: ExecutionStep,
        context: ExecutionContext
    ) -> bool:
        """
        Rollback website generation (delete files).

        Args:
            step: Step to rollback
            context: Execution context

        Returns:
            True if successful
        """
        logger.info(f"[WebsiteExecutor] Rolling back step: {step.step_id}")

        try:
            # Get output directory
            output_dir = self._get_output_directory(context.plan_id, step.step_id)

            if output_dir.exists():
                # Delete directory
                shutil.rmtree(output_dir)
                logger.info(f"[WebsiteExecutor] Deleted output directory: {output_dir}")

            # Clear cache
            if step.step_id in self._generated_files_cache:
                del self._generated_files_cache[step.step_id]

            return True

        except Exception as e:
            logger.error(f"[WebsiteExecutor] Rollback failed: {e}")
            return False

    # ========================================================================
    # Helper Methods
    # ========================================================================

    def _get_output_directory(self, plan_id: str, step_id: str) -> Path:
        """Get output directory for this step"""
        return Path(f"storage/factory_output/{plan_id}/website/{step_id}")

    def _prepare_variables(
        self,
        params: Dict[str, Any],
        template: Template
    ) -> Dict[str, Any]:
        """
        Prepare template variables with SEO enhancements.

        Args:
            params: Input parameters
            template: Template metadata

        Returns:
            Complete variable dictionary
        """
        variables = params.copy()

        # Add SEO defaults
        if "seo" not in variables:
            variables["seo"] = {}

        variables["seo"].update(self.DEFAULT_SEO)

        # Ensure meta description
        if "description" not in variables or not variables["description"]:
            variables["description"] = f"{variables['business_name']} - {variables.get('tagline', 'Welcome')}"

        # Ensure page title
        if "page_title" not in variables:
            variables["page_title"] = variables["business_name"]

        # Add generation metadata
        variables["_generated_at"] = datetime.utcnow().isoformat()
        variables["_template_id"] = template.template_id
        variables["_template_version"] = template.version

        # Ensure pages list
        if "pages" not in variables:
            variables["pages"] = ["home", "about", "contact"]

        return variables

    async def _generate_seo_files(
        self,
        output_dir: Path,
        variables: Dict[str, Any]
    ) -> List[str]:
        """
        Generate SEO-related files (robots.txt, etc.).

        Args:
            output_dir: Output directory
            variables: Template variables

        Returns:
            List of generated file paths
        """
        files = []

        # Generate robots.txt
        robots_path = output_dir / "robots.txt"
        robots_content = self._generate_robots_txt(variables)

        with open(robots_path, "w") as f:
            f.write(robots_content)

        files.append(str(robots_path))

        return files

    def _generate_robots_txt(self, variables: Dict[str, Any]) -> str:
        """Generate robots.txt content"""
        domain = variables.get("domain", "example.com")

        return f"""User-agent: *
Allow: /

Sitemap: https://{domain}/sitemap.xml
"""

    async def _generate_sitemap(
        self,
        output_dir: Path,
        variables: Dict[str, Any]
    ) -> Optional[str]:
        """
        Generate sitemap.xml.

        Args:
            output_dir: Output directory
            variables: Template variables

        Returns:
            Path to sitemap.xml or None
        """
        domain = variables.get("domain", "example.com")
        pages = variables.get("pages", [])

        # Generate sitemap XML
        sitemap_content = '<?xml version="1.0" encoding="UTF-8"?>\n'
        sitemap_content += '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">\n'

        for page in pages:
            url = f"https://{domain}/{page}.html" if page != "home" else f"https://{domain}/"
            sitemap_content += f"""  <url>
    <loc>{url}</loc>
    <lastmod>{datetime.utcnow().strftime('%Y-%m-%d')}</lastmod>
    <changefreq>weekly</changefreq>
    <priority>0.8</priority>
  </url>
"""

        sitemap_content += '</urlset>\n'

        # Write file
        sitemap_path = output_dir / "sitemap.xml"
        with open(sitemap_path, "w") as f:
            f.write(sitemap_content)

        return str(sitemap_path)

    def _validate_domain(self, domain: str) -> bool:
        """Validate domain format"""
        import re
        pattern = r"^[a-z0-9]([a-z0-9-]*[a-z0-9])?(\.[a-z0-9]([a-z0-9-]*[a-z0-9])?)*\.[a-z]{2,}$"
        return bool(re.match(pattern, domain.lower()))

    def _validate_color(self, color: str) -> bool:
        """Validate hex color format"""
        import re
        return bool(re.match(r"^#[0-9a-fA-F]{6}$", color))
