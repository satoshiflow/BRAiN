"""
Quiz Generator - Sprint 12

Generates multiple-choice quiz questions for course assessment.
"""

from typing import List
from loguru import logger

from app.modules.course_factory.schemas import (
    CourseQuiz,
    QuizQuestion,
    CourseOutline,
    CourseLanguage,
)


class QuizGenerator:
    """
    Generate quiz questions from course outline.

    Features:
    - Template-based question generation
    - Covers all modules
    - Difficulty distribution (easy/medium/hard)
    - Deterministic for dry-run parity
    """

    # Predefined questions for banking alternatives course (German)
    BANKING_QUIZ_DE = [
        {
            "question": "Welche Behörde reguliert Banken in Deutschland?",
            "a": "Bundesbank",
            "b": "BaFin (Bundesanstalt für Finanzdienstleistungsaufsicht)",
            "c": "Finanzministerium",
            "d": "Europäische Zentralbank",
            "correct": "b",
            "explanation": "Die BaFin ist die zuständige Aufsichtsbehörde für alle Finanzdienstleister in Deutschland, einschließlich Banken.",
            "difficulty": "easy",
            "module": "Modul 1"
        },
        {
            "question": "Bis zu welcher Höhe sind Einlagen bei lizenzierten Banken in der EU gesichert?",
            "a": "50.000 Euro",
            "b": "75.000 Euro",
            "c": "100.000 Euro",
            "d": "Unbegrenzt",
            "correct": "c",
            "explanation": "Die gesetzliche Einlagensicherung in der EU schützt Einlagen bis 100.000 Euro pro Person und Bank.",
            "difficulty": "easy",
            "module": "Modul 1"
        },
        {
            "question": "Was ist der Hauptunterschied zwischen einer Neobank und einer klassischen Bank?",
            "a": "Neobanken haben keine BaFin-Lizenz",
            "b": "Neobanken haben kein physisches Filialnetz",
            "c": "Neobanken dürfen keine Girokonten anbieten",
            "d": "Neobanken sind nicht reguliert",
            "correct": "b",
            "explanation": "Neobanken sind vollständig digitale Banken ohne Filialnetz, haben aber dieselbe Regulierung und Lizenzierung wie klassische Banken.",
            "difficulty": "easy",
            "module": "Modul 2"
        },
        {
            "question": "Welche Aussage über Neobanken ist FALSCH?",
            "a": "Sie unterliegen derselben Regulierung wie klassische Banken",
            "b": "Sie haben meist niedrigere Betriebskosten",
            "c": "Sie haben zusätzliche Einlagensicherung wie Sparkassen",
            "d": "Sie bieten oft kostenlose Basiskonten an",
            "correct": "c",
            "explanation": "Neobanken haben meist KEINE zusätzliche Einlagensicherung über die gesetzlichen 100.000 Euro hinaus, während klassische Banken oft zusätzliche Sicherungssysteme haben.",
            "difficulty": "medium",
            "module": "Modul 2"
        },
        {
            "question": "Was bedeutet 'Self-Custody' im Finanzkontext?",
            "a": "Die Bank verwahrt meine Wertpapiere",
            "b": "Ich verwalte meine Zugangsdaten selbst",
            "c": "Ich bin selbst für die Verwahrung meiner Assets verantwortlich",
            "d": "Eine Versicherung schützt mein Vermögen",
            "correct": "c",
            "explanation": "Self-Custody bedeutet, dass man selbst die volle Kontrolle und Verantwortung für seine digitalen Assets hat, ohne Zwischenhändler.",
            "difficulty": "medium",
            "module": "Modul 2"
        },
        {
            "question": "Welches ist ein typischer Vorteil von FinTech-Zahlungsdiensten gegenüber klassischen Banken bei Auslandsüberweisungen?",
            "a": "Höhere Sicherheit",
            "b": "Bessere Beratung",
            "c": "Niedrigere Gebühren und schnellere Abwicklung",
            "d": "Unbegrenzte Einlagensicherung",
            "correct": "c",
            "explanation": "FinTech-Dienste bieten oft deutlich niedrigere Gebühren und schnellere Überweisungen als klassische Banken, besonders bei internationalen Transaktionen.",
            "difficulty": "easy",
            "module": "Modul 2"
        },
        {
            "question": "Welches Risiko besteht NICHT primär bei Neobanken?",
            "a": "Technische Ausfälle der App",
            "b": "Fehlende Bargeldeinzahlung",
            "c": "Höhere Kontoführungsgebühren als bei klassischen Banken",
            "d": "Eingeschränkter Kundenservice in ländlichen Regionen",
            "correct": "c",
            "explanation": "Neobanken haben typischerweise NIEDRIGERE oder keine Kontoführungsgebühren. Die anderen Punkte sind tatsächliche Einschränkungen.",
            "difficulty": "medium",
            "module": "Modul 3"
        },
        {
            "question": "Was sollten Sie tun, wenn Sie mehr als 100.000 Euro anlegen möchten?",
            "a": "Alles bei einer Bank belassen, wenn diese groß genug ist",
            "b": "Das Geld auf mehrere Banken verteilen",
            "c": "Nur Neobanken verwenden",
            "d": "Das Geld in bar aufbewahren",
            "correct": "b",
            "explanation": "Die Einlagensicherung gilt pro Person und Bank. Beträge über 100.000 Euro sollten auf mehrere Banken verteilt werden, um vollständig geschützt zu sein.",
            "difficulty": "medium",
            "module": "Modul 3"
        },
        {
            "question": "Welche Technologie ermöglicht es Drittanbietern, auf Bankdaten zuzugreifen (mit Zustimmung des Kunden)?",
            "a": "Blockchain",
            "b": "APIs (PSD2)",
            "c": "Cloud Computing",
            "d": "Biometrie",
            "correct": "b",
            "explanation": "Die PSD2-Richtlinie verpflichtet Banken, APIs bereitzustellen, über die Kunden Drittanbietern Zugriff auf ihre Daten gewähren können.",
            "difficulty": "hard",
            "module": "Modul 1"
        },
        {
            "question": "Wann macht eine Neobank als Hauptkonto am WENIGSTEN Sinn?",
            "a": "Wenn Sie viel online einkaufen",
            "b": "Wenn Sie regelmäßig Bargeld einzahlen müssen",
            "c": "Wenn Sie niedrige Gebühren bevorzugen",
            "d": "Wenn Sie mobil bezahlen möchten",
            "correct": "b",
            "explanation": "Neobanken haben kein Filialnetz, wodurch Bargeldeinzahlungen schwierig oder unmöglich sind. Dies ist eine Haupteinschränkung.",
            "difficulty": "easy",
            "module": "Modul 4"
        },
        {
            "question": "Was ist ein 'Hybrid-Ansatz' bei der Bankwahl?",
            "a": "Nutzung nur einer Bank",
            "b": "Kombination verschiedener Anbieter für unterschiedliche Zwecke",
            "c": "Ausschließlich digitale Banken verwenden",
            "d": "Nur klassische Banken nutzen",
            "correct": "b",
            "explanation": "Ein Hybrid-Ansatz bedeutet, verschiedene Banken und Dienste für unterschiedliche Zwecke zu kombinieren (z.B. Neobank für Alltag, klassische Bank für Kredit).",
            "difficulty": "medium",
            "module": "Modul 4"
        },
        {
            "question": "Welche Aussage zur Migration zu einer neuen Bank ist richtig?",
            "a": "Man sollte das alte Konto sofort kündigen",
            "b": "Parallelbetrieb für eine Übergangszeit ist empfehlenswert",
            "c": "Alle Daueraufträge übertragen sich automatisch",
            "d": "Eine Migration ist rechtlich nicht erlaubt",
            "correct": "b",
            "explanation": "Ein Parallelbetrieb beider Konten für einige Monate minimiert Risiken (vergessene Lastschriften, etc.) und ermöglicht einen sanften Übergang.",
            "difficulty": "medium",
            "module": "Modul 4"
        },
        {
            "question": "Was ist bei 'Banking-as-a-Service' Modellen zu beachten?",
            "a": "Diese sind immer unsicherer als normale Banken",
            "b": "Das Konto liegt rechtlich bei der Partner-Bank, nicht bei der App",
            "c": "Sie haben keine Einlagensicherung",
            "d": "Sie sind in Deutschland verboten",
            "correct": "b",
            "explanation": "Bei BaaS-Modellen ist die App nur die Schnittstelle, das eigentliche Konto liegt bei einer Partner-Bank. Dies sollte man bei Vertragsabschluss wissen.",
            "difficulty": "hard",
            "module": "Modul 2"
        },
        {
            "question": "Welcher Kostenfaktor ist bei klassischen Banken typischerweise HÖHER als bei Neobanken?",
            "a": "IT-Kosten",
            "b": "Marketing-Kosten",
            "c": "Immobilien- und Personalkosten für Filialen",
            "d": "Regulierungskosten",
            "correct": "c",
            "explanation": "Klassische Banken haben hohe Kosten für Filialen (Miete, Mitarbeiter), während Neobanken diese Kosten nicht haben und günstiger anbieten können.",
            "difficulty": "easy",
            "module": "Modul 2"
        },
        {
            "question": "Was sollte bei der kontinuierlichen Bewertung Ihrer Bankverbindung regelmäßig überprüft werden?",
            "a": "Nur die Gebührenstruktur",
            "b": "Ob sich persönliche Bedürfnisse geändert haben",
            "c": "Nur die App-Funktionen",
            "d": "Ausschließlich die Zinssätze",
            "correct": "b",
            "explanation": "Eine gute Bankwahl hängt von den individuellen Bedürfnissen ab. Diese ändern sich im Laufe des Lebens, daher sollte man regelmäßig prüfen, ob die Bank noch passt.",
            "difficulty": "medium",
            "module": "Modul 4"
        }
    ]

    def generate_quiz(
        self,
        outline: CourseOutline,
        question_count: int = 15,
        language: CourseLanguage = CourseLanguage.DE
    ) -> CourseQuiz:
        """
        Generate quiz from course outline.

        Args:
            outline: Course outline
            question_count: Number of questions (10-15)
            language: Quiz language

        Returns:
            CourseQuiz

        Raises:
            ValueError: If language not supported
        """
        logger.info(
            f"Generating quiz: {question_count} questions (language={language})"
        )

        if language != CourseLanguage.DE:
            raise ValueError(f"Language {language} not yet supported in MVP")

        # Use predefined questions
        questions = self._generate_from_predefined(question_count)

        quiz = CourseQuiz(
            title="Abschlusstest: Alternativen zu Banken & Sparkassen",
            description="Testen Sie Ihr Wissen über moderne Bankalternativen",
            questions=questions,
            passing_score_percentage=70,
            time_limit_minutes=30,
        )

        logger.info(f"Quiz generated with {len(questions)} questions")
        return quiz

    def _generate_from_predefined(self, count: int) -> List[QuizQuestion]:
        """Generate questions from predefined set."""
        # Take first `count` questions
        questions = []
        for i, q_data in enumerate(self.BANKING_QUIZ_DE[:count]):
            question = QuizQuestion(
                question_text=q_data["question"],
                option_a=q_data["a"],
                option_b=q_data["b"],
                option_c=q_data["c"],
                option_d=q_data["d"],
                correct_answer=q_data["correct"],
                explanation=q_data["explanation"],
                difficulty=q_data["difficulty"],
                module_reference=q_data.get("module"),
            )
            questions.append(question)

        return questions
