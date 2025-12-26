"""
Lesson Content Generator - Sprint 12

Generates full lesson content in Markdown format.

For MVP: Template-based content with placeholders.
Future: LLM-enhanced content generation.
"""

from typing import List, Dict, Any
from loguru import logger

from app.modules.course_factory.schemas import (
    CourseLesson,
    CourseLessonContent,
    CourseLanguage,
)


class LessonGenerator:
    """
    Generate full lesson content in Markdown.

    Features:
    - Template-based Markdown generation
    - Structured content (intro, main, examples, summary)
    - Deterministic for dry-run parity
    - Supports multiple languages (DE, EN, FR, ES)
    """

    # Lesson content templates (German)
    LESSON_TEMPLATES_DE = {
        "default": """# {title}

## Überblick

{description}

**Lernziele:**
{objectives}

**Geschätzte Dauer:** {duration} Minuten

---

## Einführung

{intro_content}

## Hauptinhalt

{main_content}

## Praktische Beispiele

{examples_content}

## Zusammenfassung

{summary_content}

## Weiterführende Ressourcen

{resources_content}

---

*Hinweis: Dieser Inhalt wurde automatisch generiert und dient ausschließlich Bildungszwecken. Keine Anlageberatung.*
"""
    }

    # Predefined lesson content for banking alternatives course (DE)
    BANKING_LESSONS_DE = {
        "Die Entwicklung des Bankwesens seit 2000": {
            "intro": """Das Bankwesen hat sich in den letzten zwei Jahrzehnten grundlegend verändert.
Während traditionelle Banken lange Zeit das Monopol auf Finanzdienstleistungen hatten,
haben technologische Innovationen und veränderte Kundenerwartungen zu einem Umbruch geführt.

In dieser Lektion betrachten wir die wichtigsten Entwicklungen und verstehen, warum
klassisches Bankwissen heute nicht mehr ausreicht.""",
            "main": """### Die drei Phasen der Bankenentwicklung

**Phase 1 (2000-2008): Digitalisierung der klassischen Bank**
- Online-Banking wird Standard
- Filialen bleiben wichtig
- Geschäftsmodell bleibt unverändert

**Phase 2 (2008-2015): Vertrauenskrise und erste Alternativen**
- Finanzkrise erschüttert Vertrauen in Banken
- Erste FinTechs entstehen (z.B. PayPal wird massentauglich)
- Regulierung verschärft sich (Basel III)

**Phase 3 (2015-heute): Disruption und Diversifizierung**
- Neobanken erhalten Banklizenz (N26, bunq)
- Payment-Dienste expandieren (Apple Pay, Google Pay)
- Dezentrale Systeme entstehen
- Hybride Modelle entwickeln sich

### Veränderte Kundenerwartungen

Moderne Kunden erwarten:
- **Sofortige Verfügbarkeit:** 24/7 Zugang zu allen Services
- **Transparenz:** Klare Gebührenstrukturen, keine versteckten Kosten
- **Einfachheit:** Intuitive Apps, schnelle Kontoeröffnung
- **Mobilität:** Alle Funktionen auf dem Smartphone
- **Fairness:** Nachvollziehbare Konditionen

### Technologische Treiber

Folgende Technologien ermöglichen die Transformation:
- Cloud-Computing (skalierbare Infrastruktur)
- APIs (Schnittstellen für Drittanbieter)
- KI und Machine Learning (Betrugsschutz, Personalisierung)
- Biometrie (sichere Authentifizierung)
- Blockchain (dezentrale Systeme)""",
            "examples": """**Beispiel 1: Kontoeröffnung**
- **Klassische Bank:** Termin vereinbaren, persönlich erscheinen, Formulare ausfüllen, 1-2 Wochen Wartezeit
- **Neobank:** App herunterladen, Video-Ident, 15 Minuten später Konto aktiv

**Beispiel 2: Auslandsüberweisung**
- **Klassische Bank:** 25€ Gebühren, 3-5 Tage Bearbeitungszeit, intransparenter Wechselkurs
- **FinTech-Dienst:** 1-2€ Gebühren, Echtzeit-Überweisung, Echtzeitkurs

**Beispiel 3: Kundenservice**
- **Klassische Bank:** Hotline Mo-Fr 9-17 Uhr, lange Warteschleifen
- **Neobank:** 24/7 Chat-Support, durchschnittliche Antwortzeit <5 Minuten""",
            "summary": """Die Bankenlandschaft hat sich seit 2000 radikal verändert:

**Wichtigste Erkenntnisse:**
1. Technologie hat Markteintrittsbarrieren gesenkt
2. Kundenerwartungen haben sich fundamental gewandelt
3. Neue Anbieter bieten oft bessere Konditionen und Services
4. Regulierung schützt Kunden auch bei neuen Anbietern
5. Hybride Strategien (mehrere Anbieter nutzen) werden zur Norm

**Konsequenz für Privatpersonen:**
Klassisches Bankwissen (eine Hausbank für alles) ist nicht mehr zeitgemäß.
Informierte Entscheidungen erfordern Verständnis der Alternativen.""",
            "resources": """- BaFin: Offizielle Liste zugelassener Finanzdienstleister
- Verbraucherzentrale: Unabhängige Beratung zu Bankprodukten
- Fachblogs: finanz-szene.de, paymentandbanking.com
- Vergleichsportale: Check24, Verivox (mit kritischer Distanz nutzen)"""
        },
        "Was sind Neobanken und FinTechs?": {
            "intro": """In den letzten Jahren sind neue Begriffe wie "Neobank", "FinTech" oder "Challenger Bank"
aufgetaucht. Für viele ist unklar, was diese Anbieter von klassischen Banken unterscheidet und ob
sie wirklich sicher sind.

In dieser Lektion klären wir Definitionen, Unterschiede und rechtliche Rahmenbedingungen.""",
            "main": """### Definition: FinTech

**FinTech** = Financial Technology
- Oberbegriff für technologiegetriebene Finanzdienstleister
- Umfasst Payment, Lending, Investment, Insurance, etc.
- Nicht alle FinTechs sind Banken

**Beispiele:**
- PayPal (Payment)
- Auxmoney (Lending)
- Trade Republic (Investment)
- Clark (Insurance)

### Definition: Neobank

**Neobank** = Digitale Bank ohne eigenes Filialnetz
- Hat echte Banklizenz (BaFin-reguliert)
- Bietet Girokonten und grundlegende Bankdienstleistungen
- Ausschließlich über App/Web nutzbar

**Beispiele:**
- N26 (Deutschland)
- bunq (Niederlande)
- Revolut (UK, seit 2024 auch EU-Lizenz)
- vivid (Deutschland)

### Unterschied zu klassischen Banken

| Merkmal | Klassische Bank | Neobank |
|---------|----------------|---------|
| Filialnetz | Ja (oft hunderte) | Nein (rein digital) |
| Kostenstruktur | Höher (Immobilien, Personal) | Niedriger (Cloud, Automatisierung) |
| Kontoeröffnung | Persönlich, 1-2 Wochen | Digital, <15 Minuten |
| Gebühren | Oft Kontoführungsgebühren | Meist kostenlose Basiskonten |
| Produkt-Range | Breit (Kredit, Depot, Versicherung) | Fokussiert (primär Girokonto) |
| Zielgruppe | Alle Altersgruppen | Vorrangig Digital Natives |

### Rechtsrahmen und Sicherheit

**Banklizenz:**
- Neobanken mit BaFin-Lizenz unterliegen denselben Regeln wie klassische Banken
- Einlagensicherung bis 100.000€ pro Kunde
- Regelmäßige Prüfungen durch Aufsichtsbehörden

**Vorsicht bei "Banking-as-a-Service":**
- Manche Anbieter arbeiten mit Partner-Banken
- Kunde hat Konto bei Partner, nicht bei der App
- Rechtslage kann komplexer sein

### Geschäftsmodelle

Wie verdienen Neobanken Geld?
1. **Interchange Fees:** Gebühren von Händlern bei Kartenzahlungen
2. **Premium-Abos:** Kostenpflichtige Zusatzfunktionen
3. **Cross-Selling:** Vermittlung von Krediten, Versicherungen
4. **Zinsmarge:** (bei einigen) Geld verleihen
5. **Datenbasierte Services:** Anonymisierte Insights (DSGVO-konform)""",
            "examples": """**Beispiel 1: N26**
- Deutsche BaFin-Lizenz
- Kostenloses Basiskonto
- Premium-Abo (4,90€/Monat) mit Versicherungen
- Zielgruppe: Mobile-First Kunden

**Beispiel 2: bunq**
- Niederländische Lizenz (EU-weit gültig)
- Fokus auf Nachhaltigkeit und Transparenz
- Kostenpflichtig ab 2,99€/Monat
- Zielgruppe: Bewusste Konsumenten

**Beispiel 3: Trade Republic**
- Primär Investment-App, aber mit Girokonto
- Kostenlose Kontoführung
- Zinsen auf Guthaben
- Zielgruppe: Junge Anleger""",
            "summary": """**Kernpunkte:**
1. FinTech = Oberbegriff, Neobank = digitale Bank mit Lizenz
2. Neobanken sind genauso sicher wie klassische Banken (Einlagensicherung)
3. Kostenvorteile durch fehlende Filialen und Automatisierung
4. Nicht alle Funktionen klassischer Banken verfügbar
5. Ideal als Zweit- oder Hauptkonto für digital-affine Nutzer

**Wann macht eine Neobank Sinn?**
✓ Wenn Sie primär digital bezahlen
✓ Wenn Sie keine Bargeldgeschäfte haben
✓ Wenn Sie niedrige Gebühren schätzen
✓ Wenn Sie mobilen Zugang bevorzugen

**Wann eher nicht?**
✗ Wenn Sie viel Bargeld einzahlen müssen
✗ Wenn Sie Beratung vor Ort benötigen
✗ Wenn Sie komplexe Finanzprodukte nutzen (Immobilienkredit, etc.)""",
            "resources": """- BaFin: Liste lizenzierter Neobanken in Deutschland
- Finanztest: Vergleichstests von Girokonten (inkl. Neobanken)
- Eigene Anbieter-Websites für aktuelle Konditionen
- Verbraucherzentralen: Beratung bei Unsicherheiten"""
        },
        "Regulierung und Einlagensicherung": {
            "intro": """Eine der häufigsten Fragen bei neuen Bankalternativen ist: "Ist mein Geld sicher?"

Diese Lektion erklärt, wie Regulierung in Deutschland und der EU funktioniert und welche
Schutzmechanismen für Ihre Einlagen existieren.""",
            "main": """### Regulierung in Deutschland (BaFin)

**BaFin = Bundesanstalt für Finanzdienstleistungsaufsicht**

Aufgaben:
- Erteilung und Überwachung von Banklizenzen
- Prüfung der Solvenz (Zahlungsfähigkeit)
- Durchsetzung von Vorschriften (z.B. Geldwäsche-Prävention)
- Verbraucherschutz

**Lizenzpflicht:**
- Jede Bank in Deutschland benötigt BaFin-Lizenz
- Auch Neobanken mit deutscher Lizenz (z.B. N26, vivid)
- EU-Banken können per "Passporting" in Deutschland tätig sein

### EU-Regulierung

**PSD2 (Payment Services Directive 2):**
- EU-weite Regulierung für Zahlungsdienste
- Open Banking (APIs für Drittanbieter)
- Starke Kundenauthentifizierung (2FA)

**DSGVO:**
- Schutz persönlicher Daten
- Strenge Regeln für Datennutzung
- Hohe Strafen bei Verstößen

### Einlagensicherung

**Gesetzliche Einlagensicherung (EU-weit):**
- **100.000€ pro Kunde pro Bank**
- Gilt für Girokonten, Sparkonten, Festgeld
- Auszahlung innerhalb 7 Tagen im Krisenfall

**Zusätzliche freiwillige Sicherung (nur klassische Banken):**
- Private Banken: Einlagensicherungsfonds
- Sparkassen: Sparkassen-Finanzgruppe
- Volksbanken: BVR-Sicherungssystem
- **Neobanken haben meist KEINE zusätzliche Sicherung**

### Wie funktioniert Einlagensicherung?

1. Bank gerät in Schieflage
2. BaFin entzieht Lizenz
3. Einlagensicherungsfonds übernimmt
4. Kunden erhalten Geld zurück (bis 100.000€)

**Wichtig:**
- Gilt pro Person, pro Bank
- Gemeinschaftskonten: 200.000€ Schutz
- Wertpapier-Depots sind Sondervermögen (immer geschützt)

### Unterschiede Neobank vs. Klassische Bank

| Aspekt | Neobank | Klassische Bank |
|--------|---------|----------------|
| BaFin-Regulierung | Ja | Ja |
| Gesetzliche Einlagensicherung | Ja (100.000€) | Ja (100.000€) |
| Zusätzliche Sicherung | Meist nein | Ja (oft mehrere Mio.) |
| Krisenhistorie | Noch keine Insolvenzen | Teilweise Insolvenzen (aber selten) |

### Risikobewertung

**Sehr sicher:**
- Beträge bis 100.000€ bei lizenzierten Banken
- Wertpapier-Depots (Sondervermögen)

**Potenzielles Risiko:**
- Beträge >100.000€ bei einer Bank ohne Zusatzsicherung
- "Banking-as-a-Service" Modelle (unklare Rechtslage)
- Nicht-lizenzierte Anbieter

### Wie prüfe ich die Sicherheit?

1. **BaFin-Lizenz prüfen:** bafin.de → Unternehmensdatenbank
2. **Einlagensicherung bestätigen:** Website der Bank, oft im Footer
3. **Kritische Masse vermeiden:** Nicht mehr als 100.000€ bei einer Bank
4. **Diversifikation:** Mehrere Banken nutzen (Risikominimierung)""",
            "examples": """**Beispiel 1: N26**
- BaFin-Lizenz: Ja (seit 2016)
- Einlagensicherung: 100.000€ (EdB - Einlagensicherungsfonds deutscher Banken)
- Zusatzsicherung: Nein
- Bewertung: Sicher für Beträge bis 100.000€

**Beispiel 2: Sparkasse**
- BaFin-Lizenz: Ja
- Einlagensicherung: 100.000€ (gesetzlich)
- Zusatzsicherung: Ja (über Sparkassen-Finanzgruppe, faktisch unbegrenzt)
- Bewertung: Sehr sicher, auch für Großbeträge

**Beispiel 3: Revolut (vor 2024)**
- Lizenz: Nur UK (nach Brexit problematisch)
- Einlagensicherung: Kompliziert (UK-System)
- Status 2024: EU-Lizenz erhalten, jetzt klar geregelt
- Lehrpunkt: Regulierungsstatus kann sich ändern""",
            "summary": """**Wichtigste Erkenntnisse:**

1. **BaFin-Lizenz = Grundvoraussetzung** (für Deutschland)
2. **100.000€ Einlagensicherung** gilt für alle lizenzierten Banken
3. **Neobanken sind NICHT unsicherer** (bei Beträgen bis 100.000€)
4. **Zusatzsicherung gibt es nur bei klassischen Banken**
5. **Diversifikation schützt** bei Beträgen >100.000€

**Faustregeln:**
- Bis 100.000€: Jede BaFin-lizenzierte Bank ist gleich sicher
- Darüber: Entweder mehrere Banken oder klassische Bank mit Zusatzsicherung
- Wertpapiere: Immer geschützt (Sondervermögen)
- Im Zweifel: BaFin-Datenbank prüfen""",
            "resources": """- BaFin Unternehmensdatenbank: bafin.de
- Einlagensicherungsfonds: einlagensicherung.de
- EU-Richtlinie: ec.europa.eu (Deposit Guarantee Schemes)
- Verbraucherzentrale: Merkblätter zur Einlagensicherung"""
        }
    }

    def generate_lesson_content(
        self, lesson: CourseLesson, language: CourseLanguage = CourseLanguage.DE
    ) -> CourseLessonContent:
        """
        Generate full lesson content in Markdown.

        Args:
            lesson: Lesson metadata
            language: Content language

        Returns:
            CourseLessonContent with full Markdown

        Raises:
            ValueError: If language not supported
        """
        logger.info(
            f"Generating lesson content: '{lesson.title}' (language={language})"
        )

        if language != CourseLanguage.DE:
            raise ValueError(f"Language {language} not yet supported in MVP")

        # Check if we have predefined content
        if lesson.title in self.BANKING_LESSONS_DE:
            content_md = self._generate_from_predefined(lesson, language)
        else:
            content_md = self._generate_from_template(lesson, language)

        # Count words (approximation)
        word_count = len(content_md.split())

        return CourseLessonContent(
            lesson_id=lesson.lesson_id,
            content_markdown=content_md,
            word_count=word_count,
        )

    def _generate_from_predefined(
        self, lesson: CourseLesson, language: CourseLanguage
    ) -> str:
        """Generate content from predefined lesson data."""
        lesson_data = self.BANKING_LESSONS_DE[lesson.title]

        # Format objectives as Markdown list
        objectives_md = "\n".join(
            f"- {obj}" for obj in lesson.learning_objectives
        )

        # Use template
        template = self.LESSON_TEMPLATES_DE["default"]
        content = template.format(
            title=lesson.title,
            description=lesson.description,
            objectives=objectives_md,
            duration=lesson.estimated_duration_minutes,
            intro_content=lesson_data["intro"],
            main_content=lesson_data["main"],
            examples_content=lesson_data["examples"],
            summary_content=lesson_data["summary"],
            resources_content=lesson_data["resources"],
        )

        return content

    def _generate_from_template(
        self, lesson: CourseLesson, language: CourseLanguage
    ) -> str:
        """Generate generic content from template."""
        logger.warning(
            f"No predefined content for lesson '{lesson.title}', using generic template"
        )

        objectives_md = "\n".join(
            f"- {obj}" for obj in lesson.learning_objectives
        )

        template = self.LESSON_TEMPLATES_DE["default"]
        content = template.format(
            title=lesson.title,
            description=lesson.description,
            objectives=objectives_md,
            duration=lesson.estimated_duration_minutes,
            intro_content=f"Einführung in das Thema {lesson.title}.",
            main_content=f"Hauptinhalt zu {lesson.title}.\n\n(Dieser Inhalt wird in einer zukünftigen Version automatisch generiert.)",
            examples_content="Praktische Beispiele folgen in einer zukünftigen Version.",
            summary_content=f"Zusammenfassung der wichtigsten Punkte zu {lesson.title}.",
            resources_content="Weiterführende Ressourcen werden ergänzt.",
        )

        return content
