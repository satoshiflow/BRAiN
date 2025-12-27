"""
Template Renderer for Course Distribution

Sprint 15: Course Distribution & Growth Layer
Renders course pages using Jinja2 templates.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any, Dict

from jinja2 import Environment, FileSystemLoader, select_autoescape

from .distribution_models import PublicCourseDetail, PublicCourseOutline


TEMPLATES_DIR = Path(__file__).parent / "templates"


class TemplateRenderer:
    """
    Renders course pages using Jinja2 templates.

    Features:
    - SEO-optimized HTML
    - OpenGraph / Twitter Cards
    - Structured data (JSON-LD)
    - Responsive design
    """

    def __init__(self, templates_dir: Path = TEMPLATES_DIR):
        self.templates_dir = templates_dir
        self.env = Environment(
            loader=FileSystemLoader(str(templates_dir)),
            autoescape=select_autoescape(['html', 'xml']),
        )

    def render_course_page(
        self,
        course_detail: PublicCourseDetail,
        course_outline: PublicCourseOutline,
    ) -> str:
        """
        Render complete course landing page.

        Args:
            course_detail: Course details
            course_outline: Course outline

        Returns:
            Rendered HTML string
        """
        template = self.env.get_template("course_page.html")

        context = {
            # Course info
            "slug": course_detail.slug,
            "language": course_detail.language,
            "title": course_detail.title,
            "description": course_detail.description,
            "target_group": course_detail.target_group,
            "version": course_detail.version,
            "derived_from_slug": course_detail.derived_from_slug,

            # SEO
            "seo": course_detail.seo,

            # CTA
            "cta": course_detail.cta,

            # Metrics
            "view_count": course_detail.view_count,
            "enrollment_count": course_detail.enrollment_count,

            # Outline
            "modules": course_outline.modules,
            "total_chapters": course_outline.total_chapters,
            "total_duration_minutes": course_outline.total_duration_minutes,
            "prerequisites": course_outline.prerequisites,
            "learning_outcomes": course_outline.learning_outcomes,
        }

        return template.render(**context)

    def render_custom(self, template_name: str, context: Dict[str, Any]) -> str:
        """
        Render custom template with context.

        Args:
            template_name: Template filename
            context: Template context

        Returns:
            Rendered HTML string
        """
        template = self.env.get_template(template_name)
        return template.render(**context)
