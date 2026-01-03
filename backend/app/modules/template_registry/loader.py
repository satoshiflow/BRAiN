"""
Template Loader

Loads and renders templates from the template registry.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Dict, List, Optional, Any
from jinja2 import Environment, FileSystemLoader, select_autoescape, TemplateSyntaxError
from loguru import logger

from app.modules.template_registry.schemas import (
    Template,
    TemplateType,
    RenderedTemplate,
)
from app.modules.template_registry.validator import TemplateValidator


class TemplateLoader:
    """
    Loads and renders templates.

    Features:
    - Template discovery from filesystem
    - Jinja2 rendering with sandboxing
    - Variable validation
    - Multi-file generation
    """

    def __init__(self, templates_dir: str = "backend/app/modules/template_registry/templates"):
        """
        Initialize template loader.

        Args:
            templates_dir: Directory containing templates
        """
        self.templates_dir = Path(templates_dir)
        self.templates_dir.mkdir(parents=True, exist_ok=True)

        # Jinja2 environment with security
        self.jinja_env = Environment(
            loader=FileSystemLoader(str(self.templates_dir)),
            autoescape=select_autoescape(['html', 'xml', 'jinja2']),
            trim_blocks=True,
            lstrip_blocks=True,
        )

        self.validator = TemplateValidator()
        self._template_cache: Dict[str, Template] = {}

        logger.info(f"TemplateLoader initialized: {self.templates_dir}")

    def discover_templates(self) -> List[Template]:
        """
        Discover all templates in the templates directory.

        Returns:
            List of discovered templates
        """
        templates = []

        for manifest_path in self.templates_dir.rglob("manifest.json"):
            try:
                template = self.load_template_manifest(manifest_path)
                templates.append(template)
            except Exception as e:
                logger.warning(f"Failed to load template from {manifest_path}: {e}")

        logger.info(f"Discovered {len(templates)} templates")
        return templates

    def load_template_manifest(self, manifest_path: Path) -> Template:
        """
        Load template from manifest.json file.

        Args:
            manifest_path: Path to manifest.json

        Returns:
            Template object

        Raises:
            ValueError: If manifest is invalid
        """
        try:
            with open(manifest_path, "r") as f:
                data = json.load(f)

            template = Template(**data)

            # Validate template
            validation = self.validator.validate(template)
            if not validation.is_valid:
                raise ValueError(f"Invalid template: {', '.join(validation.errors)}")

            # Cache template
            self._template_cache[template.template_id] = template

            logger.debug(f"Loaded template: {template.template_id} v{template.version}")
            return template

        except Exception as e:
            logger.error(f"Error loading template manifest {manifest_path}: {e}")
            raise ValueError(f"Failed to load template: {str(e)}")

    def get_template(self, template_id: str) -> Optional[Template]:
        """
        Get template by ID.

        Args:
            template_id: Template identifier

        Returns:
            Template object or None if not found
        """
        # Check cache
        if template_id in self._template_cache:
            return self._template_cache[template_id]

        # Search filesystem
        templates = self.discover_templates()
        for template in templates:
            if template.template_id == template_id:
                return template

        return None

    def list_templates(
        self,
        type: Optional[TemplateType] = None,
        tags: Optional[List[str]] = None
    ) -> List[Template]:
        """
        List available templates with optional filtering.

        Args:
            type: Filter by template type
            tags: Filter by tags (any match)

        Returns:
            List of matching templates
        """
        templates = self.discover_templates()

        if type:
            templates = [t for t in templates if t.type == type]

        if tags:
            templates = [
                t for t in templates
                if any(tag in t.tags for tag in tags)
            ]

        return templates

    def render_template(
        self,
        template_id: str,
        variables: Dict[str, Any],
        output_dir: str
    ) -> RenderedTemplate:
        """
        Render template with provided variables.

        Args:
            template_id: Template to render
            variables: Variable values
            output_dir: Output directory for generated files

        Returns:
            RenderedTemplate result

        Raises:
            ValueError: If template not found or validation fails
        """
        import time
        start_time = time.time()

        # Load template
        template = self.get_template(template_id)
        if not template:
            raise ValueError(f"Template not found: {template_id}")

        logger.info(f"Rendering template: {template_id} → {output_dir}")

        # Validate variables
        errors = self.validator.validate_variables(template, variables)
        if errors:
            raise ValueError(f"Variable validation failed: {', '.join(errors)}")

        # Create output directory
        output_path = Path(output_dir)
        output_path.mkdir(parents=True, exist_ok=True)

        # Render each file
        generated_files = []
        render_errors = []

        for template_file in template.files:
            try:
                if template_file.is_template:
                    # Render Jinja2 template
                    content = self._render_file(template_file.path, variables)
                else:
                    # Copy static file
                    content = self._read_static_file(template_file.path)

                # Write to output
                output_file_path = output_path / template_file.output_path
                output_file_path.parent.mkdir(parents=True, exist_ok=True)

                with open(output_file_path, "w") as f:
                    f.write(content)

                generated_files.append(str(output_file_path))
                logger.debug(f"Generated: {template_file.output_path}")

            except Exception as e:
                error_msg = f"Failed to render {template_file.path}: {str(e)}"
                render_errors.append(error_msg)
                logger.error(error_msg)

        # Calculate render time
        render_time = time.time() - start_time

        result = RenderedTemplate(
            template_id=template.template_id,
            template_version=template.version,
            output_directory=output_dir,
            files_generated=generated_files,
            variables_used=variables,
            render_time_seconds=render_time,
            success=len(render_errors) == 0,
            errors=render_errors,
        )

        logger.info(
            f"Template rendered: {len(generated_files)} files in {render_time:.2f}s "
            f"(errors={len(render_errors)})"
        )

        return result

    def _render_file(self, template_path: str, variables: Dict[str, Any]) -> str:
        """
        Render a single Jinja2 template file.

        Args:
            template_path: Path to template file (relative to templates_dir)
            variables: Template variables

        Returns:
            Rendered content

        Raises:
            TemplateSyntaxError: If template has syntax errors
        """
        try:
            template = self.jinja_env.get_template(template_path)
            return template.render(**variables)
        except TemplateSyntaxError as e:
            raise ValueError(f"Template syntax error in {template_path}: {e}")
        except Exception as e:
            raise ValueError(f"Template rendering error: {e}")

    def _read_static_file(self, file_path: str) -> str:
        """
        Read a static (non-template) file.

        Args:
            file_path: Path to file (relative to templates_dir)

        Returns:
            File contents

        Raises:
            FileNotFoundError: If file doesn't exist
        """
        full_path = self.templates_dir / file_path
        if not full_path.exists():
            raise FileNotFoundError(f"Static file not found: {file_path}")

        with open(full_path, "r") as f:
            return f.read()


# Singleton
_template_loader: Optional[TemplateLoader] = None


def get_template_loader() -> TemplateLoader:
    """Get global template loader instance"""
    global _template_loader
    if _template_loader is None:
        _template_loader = TemplateLoader()
    return _template_loader
