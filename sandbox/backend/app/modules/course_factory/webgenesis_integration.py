"""
WebGenesis Integration - Sprint 13

Integrates CourseFactory with WebGenesis for theme binding, section building, SEO, and previews.
"""

from typing import List, Dict, Any, Optional
from pathlib import Path
import json
from loguru import logger

from app.modules.course_factory.schemas import CourseOutline, CourseLesson
from app.modules.course_factory.enhanced_schemas import (
    WebGenesisTheme,
    WebGenesisSection,
    SEOPack,
    i18nPlaceholders,
)


class WebGenesisIntegrationError(Exception):
    """Raised when WebGenesis integration fails."""
    pass


class ThemeRegistry:
    """
    Registry of trusted WebGenesis themes.

    For MVP: Hardcoded themes
    Future: Load from database/config
    """

    TRUSTED_THEMES = {
        "course-minimal": WebGenesisTheme(
            theme_id="course-minimal",
            theme_name="Course Minimal",
            primary_color="#0066cc",
            secondary_color="#6c757d",
            font_family="system-ui, -apple-system, sans-serif",
            supports_dark_mode=True,
            supports_i18n=True,
            supports_seo=True,
            template_path="templates/course-minimal",
        ),
        "course-professional": WebGenesisTheme(
            theme_id="course-professional",
            theme_name="Course Professional",
            primary_color="#1a237e",
            secondary_color="#455a64",
            font_family="'Inter', system-ui, sans-serif",
            supports_dark_mode=True,
            supports_i18n=True,
            supports_seo=True,
            template_path="templates/course-professional",
        ),
        "course-modern": WebGenesisTheme(
            theme_id="course-modern",
            theme_name="Course Modern",
            primary_color="#6200ea",
            secondary_color="#03dac6",
            font_family="'Poppins', system-ui, sans-serif",
            supports_dark_mode=True,
            supports_i18n=True,
            supports_seo=True,
            template_path="templates/course-modern",
        ),
    }

    def get_theme(self, theme_id: str) -> WebGenesisTheme:
        """
        Get theme by ID.

        Args:
            theme_id: Theme identifier

        Returns:
            WebGenesisTheme

        Raises:
            WebGenesisIntegrationError: If theme not found
        """
        if theme_id not in self.TRUSTED_THEMES:
            raise WebGenesisIntegrationError(
                f"Theme '{theme_id}' not found. "
                f"Available: {list(self.TRUSTED_THEMES.keys())}"
            )
        return self.TRUSTED_THEMES[theme_id]

    def list_themes(self) -> List[WebGenesisTheme]:
        """List all available themes."""
        return list(self.TRUSTED_THEMES.values())


class SectionBuilder:
    """
    Builds WebGenesis sections from course data.

    Converts course outline → website sections (Hero, Syllabus, Lesson Preview, etc.)
    """

    def build_sections(
        self,
        outline: CourseOutline,
        theme: WebGenesisTheme,
    ) -> List[WebGenesisSection]:
        """
        Build website sections from course outline.

        Args:
            outline: Course outline
            theme: WebGenesis theme

        Returns:
            List of WebGenesisSection
        """
        logger.info(f"Building sections for course '{outline.metadata.title}' with theme '{theme.theme_id}'")

        sections = []

        # 1. Hero Section
        sections.append(self._build_hero_section(outline, theme))

        # 2. Syllabus Section
        sections.append(self._build_syllabus_section(outline, theme))

        # 3. Lesson Preview Sections (first 3 lessons)
        preview_sections = self._build_lesson_preview_sections(outline, theme, max_previews=3)
        sections.extend(preview_sections)

        # 4. FAQ Section (placeholder)
        sections.append(self._build_faq_section(outline, theme))

        # 5. CTA Section
        sections.append(self._build_cta_section(outline, theme))

        # 6. Footer Section
        sections.append(self._build_footer_section(outline, theme))

        logger.info(f"Built {len(sections)} sections")
        return sections

    def _build_hero_section(self, outline: CourseOutline, theme: WebGenesisTheme) -> WebGenesisSection:
        """Build hero section."""
        return WebGenesisSection(
            section_type="hero",
            title=outline.metadata.title,
            content=outline.metadata.description,
            background_color=theme.primary_color,
            text_color="#ffffff",
            order_index=0,
        )

    def _build_syllabus_section(self, outline: CourseOutline, theme: WebGenesisTheme) -> WebGenesisSection:
        """Build syllabus/course structure section."""
        # Generate HTML list of modules and lessons
        content = "<ul class='syllabus'>\n"
        for module in outline.modules:
            content += f"  <li><strong>{module.title}</strong>\n"
            content += "    <ul>\n"
            for lesson in module.lessons:
                content += f"      <li>{lesson.title} ({lesson.estimated_duration_minutes} min)</li>\n"
            content += "    </ul>\n"
            content += "  </li>\n"
        content += "</ul>"

        return WebGenesisSection(
            section_type="syllabus",
            title="Kursstruktur",
            content=content,
            order_index=1,
        )

    def _build_lesson_preview_sections(
        self, outline: CourseOutline, theme: WebGenesisTheme, max_previews: int = 3
    ) -> List[WebGenesisSection]:
        """Build lesson preview sections."""
        sections = []
        full_lessons = outline.get_full_lessons()[:max_previews]

        for idx, lesson in enumerate(full_lessons):
            # Get preview (first 300 chars of content)
            preview_content = lesson.content_markdown[:300] + "..." if lesson.content_markdown else lesson.description

            section = WebGenesisSection(
                section_type="lesson_preview",
                title=f"Lektion: {lesson.title}",
                content=preview_content,
                order_index=2 + idx,
            )
            sections.append(section)

        return sections

    def _build_faq_section(self, outline: CourseOutline, theme: WebGenesisTheme) -> WebGenesisSection:
        """Build FAQ section (placeholder)."""
        faq_content = """
        <div class="faq">
            <h3>Häufig gestellte Fragen</h3>
            <p><strong>Wie lange habe ich Zugriff auf den Kurs?</strong><br>
            Unbegrenzt! Einmal gekauft, immer verfügbar.</p>

            <p><strong>Gibt es Voraussetzungen?</strong><br>
            Nein, der Kurs ist für Einsteiger konzipiert.</p>

            <p><strong>Erhalte ich ein Zertifikat?</strong><br>
            Ja, nach erfolgreichem Abschluss des Quiz.</p>
        </div>
        """
        return WebGenesisSection(
            section_type="faq",
            title="FAQ",
            content=faq_content,
            order_index=100,
        )

    def _build_cta_section(self, outline: CourseOutline, theme: WebGenesisTheme) -> WebGenesisSection:
        """Build call-to-action section."""
        return WebGenesisSection(
            section_type="cta",
            title="Kurs demnächst verfügbar",
            content=f"<p>{outline.total_lessons} Lektionen · {outline.total_estimated_duration_minutes} Minuten</p>",
            background_color=theme.secondary_color,
            text_color="#ffffff",
            order_index=200,
        )

    def _build_footer_section(self, outline: CourseOutline, theme: WebGenesisTheme) -> WebGenesisSection:
        """Build footer section."""
        from datetime import datetime
        footer_content = f"""
        <footer>
            <p>&copy; {datetime.utcnow().year} · {outline.metadata.title}</p>
            <p>Erstellt mit BRAiN CourseFactory</p>
        </footer>
        """
        return WebGenesisSection(
            section_type="footer",
            title="",
            content=footer_content,
            order_index=999,
        )


class SEOGenerator:
    """
    Generates SEO metadata pack for course websites.

    Creates meta tags, OG tags, Twitter cards, and JSON-LD structured data.
    """

    def generate_seo_pack(
        self,
        outline: CourseOutline,
        canonical_url: Optional[str] = None,
    ) -> SEOPack:
        """
        Generate SEO pack from course outline.

        Args:
            outline: Course outline
            canonical_url: Optional canonical URL

        Returns:
            SEOPack with complete SEO metadata
        """
        logger.info(f"Generating SEO pack for '{outline.metadata.title}'")

        # Extract keywords from course
        keywords = self._extract_keywords(outline)

        # Generate JSON-LD
        json_ld = self._generate_course_json_ld(outline, canonical_url)

        seo_pack = SEOPack(
            # Meta tags
            meta_title=outline.metadata.title[:70],
            meta_description=outline.metadata.description[:160],
            meta_keywords=keywords,

            # Open Graph
            og_title=outline.metadata.title[:70],
            og_description=outline.metadata.description[:200],
            og_type="website",  # Could be "course" with schema.org extension

            # Twitter Card
            twitter_card="summary_large_image",
            twitter_title=outline.metadata.title[:70],
            twitter_description=outline.metadata.description[:200],

            # Additional
            canonical_url=canonical_url,
            robots="index, follow",
            json_ld=json_ld,
        )

        logger.info("SEO pack generated successfully")
        return seo_pack

    def _extract_keywords(self, outline: CourseOutline) -> List[str]:
        """Extract keywords from course for SEO."""
        keywords = set()

        # Add keywords from lessons
        for module in outline.modules:
            for lesson in module.lessons:
                if lesson.keywords:
                    keywords.update(lesson.keywords)

        # Add language
        keywords.add(outline.metadata.language.value)

        # Add target audiences
        for audience in outline.metadata.target_audiences:
            keywords.add(audience.value)

        return list(keywords)[:10]  # Max 10

    def _generate_course_json_ld(
        self, outline: CourseOutline, canonical_url: Optional[str]
    ) -> Dict[str, Any]:
        """Generate JSON-LD structured data for Course schema."""
        json_ld = {
            "@context": "https://schema.org",
            "@type": "Course",
            "name": outline.metadata.title,
            "description": outline.metadata.description,
            "provider": {
                "@type": "Organization",
                "name": "BRAiN CourseFactory",
            },
            "hasCourseInstance": {
                "@type": "CourseInstance",
                "courseMode": "online",
                "inLanguage": outline.metadata.language.value,
            },
            "numberOfCredits": len(outline.modules),
            "timeRequired": f"PT{outline.total_estimated_duration_minutes}M",
        }

        if canonical_url:
            json_ld["url"] = canonical_url

        return json_ld


class PreviewURLGenerator:
    """
    Generates versioned preview URLs for course websites.

    Format: https://{domain}/previews/{course_id}/{version}/
    """

    def generate_preview_url(
        self,
        course_id: str,
        version: int,
        base_domain: str = "brain.staging",
    ) -> str:
        """
        Generate preview URL.

        Args:
            course_id: Course identifier
            version: Version number
            base_domain: Base domain for previews

        Returns:
            Preview URL
        """
        # Sanitize course_id for URL
        safe_course_id = course_id.replace("_", "-")[:50]

        url = f"https://{base_domain}/previews/{safe_course_id}/v{version}/"

        logger.info(f"Generated preview URL: {url}")
        return url


# Singletons
_theme_registry: Optional[ThemeRegistry] = None
_section_builder: Optional[SectionBuilder] = None
_seo_generator: Optional[SEOGenerator] = None
_preview_url_generator: Optional[PreviewURLGenerator] = None


def get_theme_registry() -> ThemeRegistry:
    """Get theme registry singleton."""
    global _theme_registry
    if _theme_registry is None:
        _theme_registry = ThemeRegistry()
    return _theme_registry


def get_section_builder() -> SectionBuilder:
    """Get section builder singleton."""
    global _section_builder
    if _section_builder is None:
        _section_builder = SectionBuilder()
    return _section_builder


def get_seo_generator() -> SEOGenerator:
    """Get SEO generator singleton."""
    global _seo_generator
    if _seo_generator is None:
        _seo_generator = SEOGenerator()
    return _seo_generator


def get_preview_url_generator() -> PreviewURLGenerator:
    """Get preview URL generator singleton."""
    global _preview_url_generator
    if _preview_url_generator is None:
        _preview_url_generator = PreviewURLGenerator()
    return _preview_url_generator
