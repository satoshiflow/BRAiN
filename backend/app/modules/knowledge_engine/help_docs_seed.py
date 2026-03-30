from __future__ import annotations

from typing import Any

from loguru import logger
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.auth_deps import Principal, PrincipalType

from .schemas import KnowledgeItemCreate, KnowledgeItemUpdate
from .service import get_knowledge_engine_service


HELP_DOC_SEED_ENTRIES: list[dict[str, Any]] = [
    {
        "help_key": "skills.catalog",
        "surface": "controldeck-v3",
        "title": "Skills-Katalog: Governance und Ausfuehrung",
        "content": (
            "Der Skills-Katalog ist die zentrale Steuerflaeche fuer registrierte Skills.\n\n"
            "Praktische Nutzung:\n"
            "- Filtere nach Risiko und Status, bevor du produktive Runs startest.\n"
            "- Pruefe Parameter und Version in den Skill-Details.\n"
            "- Nutze den Katalog als Startpunkt fuer kontrollierte Run-Ausfuehrung.\n\n"
            "Empfehlung:\n"
            "Nutze zuerst low-risk Skills in neuen Workflows und erweitere schrittweise."
        ),
        "tags": ["help", "skills", "governance", "controldeck-v3"],
    },
    {
        "help_key": "knowledge.explorer",
        "surface": "controldeck-v3",
        "title": "Knowledge Explorer: Hybrid-Suche und Kontext",
        "content": (
            "Der Knowledge Explorer kombiniert klassische Suche und semantische Suche.\n\n"
            "Praktische Nutzung:\n"
            "- Nutze Textsuche fuer exakte Begriffe oder IDs.\n"
            "- Nutze Semantic Search fuer aehnliche Konzepte und Runbook-Naehe.\n"
            "- Verknuepfe Eintraege, um Ursache-Wirkung und Abhaengigkeiten sichtbar zu machen.\n\n"
            "Empfehlung:\n"
            "Pflege tags und metadata sauber, damit Skills spaeter besseren Kontext erhalten."
        ),
        "tags": ["help", "knowledge", "semantic-search", "controldeck-v3"],
    },
    {
        "help_key": "healing.actions",
        "surface": "controldeck-v3",
        "title": "Self-Healing Aktionen: Reevaluate und Escalate",
        "content": (
            "Self-Healing Aktionen steuern kontrollierte Recovery-Entscheidungen.\n\n"
            "Praktische Nutzung:\n"
            "- Reevaluate bei transienten Fehlern oder geaendertem Kontext.\n"
            "- Escalate bei wiederkehrenden kritischen Vorfaellen.\n"
            "- Dokumentiere den Grund jeder Aktion fuer Governance und Audit.\n\n"
            "Empfehlung:\n"
            "Nutze Eskalation nur bei anhaltendem Risiko oder wenn automatische Recovery mehrfach scheitert."
        ),
        "tags": ["help", "healing", "incident", "controldeck-v3"],
    },
    {
        "help_key": "settings.appearance",
        "surface": "controldeck-v3",
        "title": "Settings: Appearance und Runtime-Verhalten",
        "content": (
            "In den Settings steuerst du Theme, Live-Updates und Runtime-nahe Optionen.\n\n"
            "Praktische Nutzung:\n"
            "- Verwende system theme fuer konsistente Darstellung.\n"
            "- Deaktiviere Live-Updates bei gezieltem UI-Debugging.\n"
            "- Halte Team-Defaults stabil, um Bedienfehler zu reduzieren.\n\n"
            "Empfehlung:\n"
            "Aendere Runtime-relevante Einstellungen bewusst und dokumentiere Abweichungen im Team."
        ),
        "tags": ["help", "settings", "operator", "controldeck-v3"],
    },
    {
        "help_key": "axe.chat.intent",
        "surface": "axe-ui",
        "title": "AXE Intent Surface: Praezise Operator-Intents",
        "content": (
            "Die Intent Surface ist der Einstieg fuer ausfuehrbare Arbeitsauftraege in AXE.\n\n"
            "Praktische Nutzung:\n"
            "- Formuliere Ziel, Grenzen und erwartete Artefakte klar.\n"
            "- Trenne Analyse-, Implementierungs- und Verifikationsschritte.\n"
            "- Nutze Follow-up Prompts fuer iterative Verfeinerung statt unscharfer Sammelanfragen.\n\n"
            "Empfehlung:\n"
            "Gib immer den gewuenschten Endzustand an (z. B. Build gruen, Testbericht, PR-Delta)."
        ),
        "tags": ["help", "axe", "intent", "orchestration"],
    },
    {
        "help_key": "axe.health.indicator",
        "surface": "axe-ui",
        "title": "AXE API Health Indicator: Fruehwarnsignal",
        "content": (
            "Der API Health Indicator zeigt den aktuellen Verbindungszustand zum Backend.\n\n"
            "Praktische Nutzung:\n"
            "- Bei API error zuerst Token, Backend-Status und Netzwerk pruefen.\n"
            "- Nutze die Tooltips fuer konkrete Fehlermeldungen.\n"
            "- Stabilisiere zuerst Health, bevor du komplexe Runs startest.\n\n"
            "Empfehlung:\n"
            "Betrachte den Indikator als Start-Check vor laengeren Operator-Sessions."
        ),
        "tags": ["help", "axe", "health", "diagnostics"],
    },
    {
        "help_key": "axe.navigation",
        "surface": "axe-ui",
        "title": "AXE Navigation: Mission Surface und Handover",
        "content": (
            "Die AXE Navigation verbindet operative Arbeit mit Governance-Flaechen.\n\n"
            "Praktische Nutzung:\n"
            "- Wechsel zwischen Chat, Dashboard und Settings je nach Workflow-Phase.\n"
            "- Nutze den ControlDeck-Link fuer Governance- oder Policy-Anpassungen.\n"
            "- Halte Chat fuer Ausfuehrung und ControlDeck fuer Steuerung getrennt.\n\n"
            "Empfehlung:\n"
            "Fuehre operative Entscheidungen in AXE aus, dokumentiere Governance-Entscheidungen in ControlDeck."
        ),
        "tags": ["help", "axe", "navigation", "handover"],
    },
]


def _seed_principal() -> Principal:
    return Principal(
        principal_id="system-help-seed",
        principal_type=PrincipalType.SERVICE,
        name="Knowledge Help Seeder",
        roles=["SYSTEM_ADMIN"],
        scopes=["read", "write"],
        tenant_id=None,
    )


async def seed_help_documents(db: AsyncSession) -> None:
    service = get_knowledge_engine_service()
    principal = _seed_principal()

    created = 0
    updated = 0

    for entry in HELP_DOC_SEED_ENTRIES:
        help_key = str(entry["help_key"])
        surface = str(entry["surface"])
        metadata = {
            "help_key": help_key,
            "surface": surface,
            "seed_version": 1,
            "seeded_by": "knowledge_engine.help_docs_seed",
        }

        existing = await service.get_help_doc(db, principal, help_key=help_key, surface=surface)
        if existing is None:
            await service.create_knowledge_item(
                db,
                principal,
                KnowledgeItemCreate(
                    title=str(entry["title"]),
                    content=str(entry["content"]),
                    type="help_doc",
                    tags=[str(tag) for tag in entry.get("tags", [])],
                    visibility="tenant",
                    metadata=metadata,
                ),
            )
            created += 1
            continue

        merged_metadata = dict(existing.get("metadata") or {})
        merged_metadata.update(metadata)
        await service.update_knowledge_item(
            db,
            principal,
            existing["id"],
            KnowledgeItemUpdate(
                title=str(entry["title"]),
                content=str(entry["content"]),
                type="help_doc",
                tags=[str(tag) for tag in entry.get("tags", [])],
                visibility=str(existing.get("visibility") or "tenant"),
                metadata=merged_metadata,
            ),
        )
        updated += 1

    logger.info(
        "Knowledge help docs seeding complete: created={} updated={} total={}",
        created,
        updated,
        len(HELP_DOC_SEED_ENTRIES),
    )
