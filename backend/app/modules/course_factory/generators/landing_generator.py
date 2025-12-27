"""
Landing Page Generator - Sprint 12

Generates landing page content for course marketing.
"""

from typing import List
from loguru import logger

from app.modules.course_factory.schemas import (
    CourseLandingPage,
    CourseOutline,
    CourseLanguage,
)


class LandingPageGenerator:
    """
    Generate landing page content from course outline.

    Features:
    - Hero section
    - Value proposition
    - Target audience segmentation
    - Course structure preview
    - Feature highlights
    """

    def generate_landing_page(
        self,
        outline: CourseOutline,
        language: CourseLanguage = CourseLanguage.DE
    ) -> CourseLandingPage:
        """
        Generate landing page from course outline.

        Args:
            outline: Course outline
            language: Page language

        Returns:
            CourseLandingPage

        Raises:
            ValueError: If language not supported
        """
        logger.info(
            f"Generating landing page for '{outline.metadata.title}' "
            f"(language={language})"
        )

        if language != CourseLanguage.DE:
            raise ValueError(f"Language {language} not yet supported in MVP")

        # Generate hero section
        hero_title = outline.metadata.title
        hero_subtitle = outline.metadata.description

        # Generate value proposition
        value_prop = self._generate_value_proposition(outline)

        # Generate target audience
        for_whom = self._generate_for_whom(outline)
        not_for_whom = self._generate_not_for_whom(outline)

        # Generate features
        features = self._generate_features(outline)

        landing = CourseLandingPage(
            hero_title=hero_title,
            hero_subtitle=hero_subtitle,
            hero_cta_text="Kurs demnächst verfügbar",
            value_proposition=value_prop,
            for_whom_points=for_whom,
            not_for_whom_points=not_for_whom,
            features=features,
            disclaimer="Dieser Kurs dient ausschließlich Bildungszwecken. Keine Anlageberatung. Kein Produktverkauf.",
        )

        logger.info("Landing page generated successfully")
        return landing

    def _generate_value_proposition(self, outline: CourseOutline) -> str:
        """Generate value proposition based on course."""
        if "Banken" in outline.metadata.title or "Banking" in outline.metadata.title:
            return """Erfahren Sie, warum klassisches Bankwissen heute nicht mehr ausreicht und welche
Alternativen zu Banken und Sparkassen existieren. Dieser Kurs vermittelt praxisnahes Wissen ohne
Ideologie und Produktverkauf – damit Sie informierte Entscheidungen treffen können.

**Was Sie lernen:**
- Moderne Bankalternativen verstehen (Neobanken, FinTechs, Self-Custody)
- Risiken und Chancen objektiv bewerten
- Die richtige Lösung für Ihre Bedürfnisse finden
- Sicherheit und Regulierung durchschauen"""
        else:
            return f"""Dieser Kurs bietet Ihnen fundiertes Wissen zu {outline.metadata.title}.
In {len(outline.modules)} Modulen mit insgesamt {outline.total_lessons} Lektionen
lernen Sie alles Wichtige, um informierte Entscheidungen zu treffen."""

    def _generate_for_whom(self, outline: CourseOutline) -> List[str]:
        """Generate 'for whom' section."""
        if "Banken" in outline.metadata.title:
            return [
                "Privatpersonen, die mehr Kontrolle über ihre Finanzen wollen",
                "Angestellte, die niedrigere Bankgebühren suchen",
                "Berufseinsteiger, die digitale Banklösungen bevorzugen",
                "Alle, die verstehen wollen, wie moderne Finanzdienstleister funktionieren",
                "Menschen, die eine objektive Übersicht ohne Verkaufsabsicht suchen"
            ]
        else:
            return [
                "Personen, die sich mit dem Thema auseinandersetzen möchten",
                "Einsteiger ohne Vorkenntnisse",
                "Alle, die fundiertes Wissen suchen"
            ]

    def _generate_not_for_whom(self, outline: CourseOutline) -> List[str]:
        """Generate 'not for whom' section."""
        if "Banken" in outline.metadata.title:
            return [
                "Sie suchen konkrete Anlageberatung (wir beraten nicht)",
                "Sie wollen ein bestimmtes Produkt verkauft bekommen (wir verkaufen nichts)",
                "Sie erwarten eine ideologische Positionierung (wir bleiben neutral)"
            ]
        else:
            return [
                "Sie suchen individuelle Beratung",
                "Sie benötigen spezialisierte Fachkenntnisse"
            ]

    def _generate_features(self, outline: CourseOutline) -> List[str]:
        """Generate feature highlights."""
        features = [
            f"{len(outline.modules)} praxisnahe Module",
            f"{outline.total_lessons} strukturierte Lektionen",
            f"Ca. {outline.total_estimated_duration_minutes} Minuten Gesamtdauer",
            "Abschlusstest zum Wissensnachweis"
        ]

        if outline.get_full_lessons():
            features.append(f"{len(outline.get_full_lessons())} vollständig ausgearbeitete Lektionen")

        features.append("Kein Produktverkauf, keine Ideologie")

        return features
