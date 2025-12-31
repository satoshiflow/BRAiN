"""
Course Outline Generator - Sprint 12

Generates course structure (modules and lessons) based on course topic.

For MVP: Template-based generation with deterministic structure.
Future: LLM-enhanced generation for custom topics.
"""

from typing import List, Dict, Any
from loguru import logger

from app.modules.course_factory.schemas import (
    CourseOutline,
    CourseModule,
    CourseLesson,
    CourseMetadata,
    CourseLanguage,
    CourseTargetAudience,
    LessonStatus,
)


class OutlineGenerator:
    """
    Generate course outline from course metadata.

    Features:
    - Template-based structure generation
    - Configurable module/lesson count
    - Deterministic for given inputs (dry-run parity)
    - Supports micro-niche parameterization
    """

    # Predefined course templates
    COURSE_TEMPLATES = {
        "banking-alternatives-de": {
            "language": "de",
            "title": "Alternativen zu Banken & Sparkassen – Was du heute wissen musst",
            "description": "Ein praxisnaher Grundlagenkurs für Privatpersonen, Angestellte und Berufseinsteiger über moderne Bankalternativen.",
            "modules": [
                {
                    "title": "Warum klassisches Bankwissen nicht mehr ausreicht",
                    "description": "Verstehen Sie die Veränderungen im Bankensektor und warum traditionelle Ansätze überdacht werden müssen.",
                    "lessons": [
                        {
                            "title": "Die Entwicklung des Bankwesens seit 2000",
                            "description": "Von der klassischen Filialbank zur digitalen Revolution",
                            "duration": 15,
                            "objectives": [
                                "Verständnis der Digitalisierung im Bankwesen",
                                "Erkennen von Veränderungen im Kundenverhalten",
                                "Identifikation neuer Marktteilnehmer"
                            ]
                        },
                        {
                            "title": "Was sind Neobanken und FinTechs?",
                            "description": "Definition und Unterscheidung moderner Finanzdienstleister",
                            "duration": 20,
                            "objectives": [
                                "Definition von Neobanken",
                                "Unterschied zu klassischen Banken",
                                "Vorteile und Einschränkungen"
                            ]
                        },
                        {
                            "title": "Regulierung und Einlagensicherung",
                            "description": "Wie sicher sind moderne Bankalternativen?",
                            "duration": 25,
                            "objectives": [
                                "Verständnis der BaFin-Regulierung",
                                "Einlagensicherung in Deutschland und EU",
                                "Sicherheitsstandards verschiedener Anbieter"
                            ]
                        }
                    ]
                },
                {
                    "title": "Übersicht der Alternativen",
                    "description": "Ein Überblick über die verschiedenen Kategorien von Bankalternativen",
                    "lessons": [
                        {
                            "title": "Neobanken in Deutschland",
                            "description": "N26, bunq, vivid und weitere Anbieter im Überblick",
                            "duration": 30,
                            "objectives": [
                                "Kenntnis der wichtigsten deutschen Neobanken",
                                "Vergleich der Geschäftsmodelle",
                                "Zielgruppen und Anwendungsfälle"
                            ]
                        },
                        {
                            "title": "Payment-Dienste und E-Wallets",
                            "description": "PayPal, Apple Pay, Google Pay und deren Rolle",
                            "duration": 20,
                            "objectives": [
                                "Unterschied zwischen E-Wallet und Bank",
                                "Einsatzbereiche und Grenzen",
                                "Sicherheitsaspekte"
                            ]
                        },
                        {
                            "title": "Self-Custody und dezentrale Systeme",
                            "description": "Einführung in selbstverwaltete Finanzlösungen",
                            "duration": 25,
                            "objectives": [
                                "Was bedeutet Self-Custody?",
                                "Vor- und Nachteile dezentraler Systeme",
                                "Verantwortung und Risiken"
                            ]
                        },
                        {
                            "title": "Hybride Lösungen",
                            "description": "Kombination klassischer und moderner Ansätze",
                            "duration": 15,
                            "objectives": [
                                "Multi-Banking-Strategien",
                                "Risikodiversifikation",
                                "Praktische Beispiele"
                            ]
                        }
                    ]
                },
                {
                    "title": "Risiken & Chancen",
                    "description": "Objektive Bewertung der Vor- und Nachteile verschiedener Ansätze",
                    "lessons": [
                        {
                            "title": "Technische Risiken",
                            "description": "IT-Sicherheit, Ausfälle und technische Abhängigkeiten",
                            "duration": 20,
                            "objectives": [
                                "Verständnis technischer Risiken",
                                "Schutzmaßnahmen",
                                "Notfallpläne"
                            ]
                        },
                        {
                            "title": "Regulatorische Risiken",
                            "description": "Gesetzesänderungen und deren Auswirkungen",
                            "duration": 15,
                            "objectives": [
                                "Aktuelle Regulierungstrends",
                                "Auswirkungen auf Privatpersonen",
                                "Zukunftsszenarien"
                            ]
                        },
                        {
                            "title": "Wirtschaftliche Risiken",
                            "description": "Gebühren, Wechselkurse und versteckte Kosten",
                            "duration": 20,
                            "objectives": [
                                "Kostenstrukturen verstehen",
                                "Gebührenvergleich",
                                "Langfristige Kostenplanung"
                            ]
                        },
                        {
                            "title": "Chancen und Mehrwerte",
                            "description": "Was moderne Alternativen besser machen können",
                            "duration": 15,
                            "objectives": [
                                "Effizienzgewinne",
                                "Neue Funktionen und Services",
                                "Kosteneinsparungen"
                            ]
                        }
                    ]
                },
                {
                    "title": "Informierte Entscheidungen treffen",
                    "description": "Werkzeuge und Methoden für die Auswahl der richtigen Lösung",
                    "lessons": [
                        {
                            "title": "Bedarfsanalyse",
                            "description": "Was brauche ich wirklich?",
                            "duration": 25,
                            "objectives": [
                                "Eigene Anforderungen identifizieren",
                                "Prioritäten setzen",
                                "Checkliste erstellen"
                            ]
                        },
                        {
                            "title": "Vergleichskriterien",
                            "description": "Worauf kommt es bei der Auswahl an?",
                            "duration": 20,
                            "objectives": [
                                "Objektive Vergleichskriterien",
                                "Bewertungsmatrix",
                                "Fallstricke vermeiden"
                            ]
                        },
                        {
                            "title": "Migration und Umstellung",
                            "description": "Wie wechsle ich sicher zu einer Alternative?",
                            "duration": 30,
                            "objectives": [
                                "Migrationsplanung",
                                "Parallelbetrieb",
                                "Häufige Probleme und Lösungen"
                            ]
                        },
                        {
                            "title": "Kontinuierliche Bewertung",
                            "description": "Langfristig die richtige Lösung behalten",
                            "duration": 15,
                            "objectives": [
                                "Regelmäßige Überprüfung",
                                "Anpassung an veränderte Bedürfnisse",
                                "Aktuell bleiben"
                            ]
                        }
                    ]
                }
            ]
        }
    }

    def generate_outline(
        self,
        metadata: CourseMetadata,
        template_id: str | None = None,
        dry_run: bool = False
    ) -> CourseOutline:
        """
        Generate course outline from metadata.

        Args:
            metadata: Course metadata
            template_id: Optional template ID (e.g., "banking-alternatives-de")
            dry_run: Dry-run mode (deterministic output)

        Returns:
            CourseOutline

        Raises:
            ValueError: If template not found or invalid configuration
        """
        logger.info(
            f"Generating course outline: title='{metadata.title}', "
            f"language={metadata.language}, dry_run={dry_run}"
        )

        # Use template if provided, otherwise generate generic outline
        if template_id and template_id in self.COURSE_TEMPLATES:
            outline = self._generate_from_template(metadata, template_id)
        else:
            outline = self._generate_generic_outline(metadata)

        # Mark lessons as full or placeholder based on full_lessons_count
        self._mark_lesson_statuses(outline, metadata.full_lessons_count)

        # Compute summary statistics
        outline.total_lessons = sum(len(module.lessons) for module in outline.modules)
        outline.total_estimated_duration_minutes = sum(
            module.estimated_total_duration_minutes for module in outline.modules
        )

        logger.info(
            f"Outline generated: {len(outline.modules)} modules, "
            f"{outline.total_lessons} lessons, "
            f"{outline.total_estimated_duration_minutes} minutes"
        )

        return outline

    def _generate_from_template(
        self, metadata: CourseMetadata, template_id: str
    ) -> CourseOutline:
        """Generate outline from predefined template."""
        template = self.COURSE_TEMPLATES[template_id]

        modules = []
        for idx, module_data in enumerate(template["modules"]):
            lessons = []
            total_duration = 0

            for lesson_idx, lesson_data in enumerate(module_data["lessons"]):
                lesson = CourseLesson(
                    title=lesson_data["title"],
                    description=lesson_data["description"],
                    learning_objectives=lesson_data["objectives"],
                    estimated_duration_minutes=lesson_data["duration"],
                    status=LessonStatus.TODO,  # Will be updated later
                    order_index=lesson_idx,
                )
                lessons.append(lesson)
                total_duration += lesson_data["duration"]

            module = CourseModule(
                title=module_data["title"],
                description=module_data["description"],
                learning_objectives=[],  # Can be derived from lessons
                lessons=lessons,
                order_index=idx,
                estimated_total_duration_minutes=total_duration,
            )
            modules.append(module)

        return CourseOutline(
            metadata=metadata,
            modules=modules,
            total_lessons=0,  # Will be computed
            total_estimated_duration_minutes=0,  # Will be computed
        )

    def _generate_generic_outline(self, metadata: CourseMetadata) -> CourseOutline:
        """
        Generate generic outline when no template is available.

        Creates a basic 4-module structure with 3-4 lessons each.
        """
        logger.warning("No template provided, generating generic outline")

        modules = []
        for i in range(4):
            lessons = []
            for j in range(3):
                lesson = CourseLesson(
                    title=f"Lektion {j+1}: {metadata.title} - Teil {i+1}.{j+1}",
                    description=f"Lerninhalt für Lektion {j+1} in Modul {i+1}",
                    learning_objectives=[
                        f"Lernziel {k+1}" for k in range(3)
                    ],
                    estimated_duration_minutes=20,
                    status=LessonStatus.TODO,
                    order_index=j,
                )
                lessons.append(lesson)

            module = CourseModule(
                title=f"Modul {i+1}: {metadata.title}",
                description=f"Beschreibung für Modul {i+1}",
                learning_objectives=[f"Modulziel {k+1}" for k in range(3)],
                lessons=lessons,
                order_index=i,
                estimated_total_duration_minutes=60,
            )
            modules.append(module)

        return CourseOutline(
            metadata=metadata,
            modules=modules,
            total_lessons=0,
            total_estimated_duration_minutes=0,
        )

    def _mark_lesson_statuses(
        self, outline: CourseOutline, full_lessons_count: int
    ):
        """
        Mark lessons as FULL or PLACEHOLDER based on configuration.

        First N lessons (up to full_lessons_count) are marked as FULL,
        rest as PLACEHOLDER.

        Args:
            outline: Course outline (modified in-place)
            full_lessons_count: Number of lessons to mark as FULL
        """
        marked_full = 0

        for module in outline.modules:
            for lesson in module.lessons:
                if marked_full < full_lessons_count:
                    lesson.status = LessonStatus.FULL
                    marked_full += 1
                else:
                    lesson.status = LessonStatus.PLACEHOLDER
                    # Generate placeholder outline
                    lesson.content_outline = [
                        f"Einführung in {lesson.title}",
                        f"Hauptkonzepte und Definitionen",
                        f"Praktische Beispiele",
                        f"Zusammenfassung und Ausblick",
                    ]

        logger.info(
            f"Marked {marked_full} lessons as FULL, "
            f"{outline.total_lessons - marked_full} as PLACEHOLDER"
        )
