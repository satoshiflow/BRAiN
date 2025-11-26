"""
agent_manager.py

AgentManager – verwaltet andere Agenten in BRAIN.

Aufgaben:
- Neue Agenten anlegen (add_agent)
- Bestehende Agenten aktualisieren (update_agent)
- Agenten löschen (delete_agent)
- Agenten-Konfiguration prüfen/validieren (verify_agent)
- Agentenänderungen zur Freigabe an einen Supervisor/Human weitergeben (submit_for_review)

Der AgentManager nutzt:
- BaseAgent (LLM-Aufrufe, Tools, Permissions)
- Ein AgentRepository, das Agenten-Konfigurationen speichert
  (z. B. als JSON-Dateien, in einer DB etc.)

WICHTIG:
Dies ist die "kontrollierte Verwaltungsinstanz" – hier bündeln wir Rechte
und Sicherheitsprüfungen, bevor Agentenstrukturen im System geändert werden.
"""

from __future__ import annotations

import uuid
import datetime as dt
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Protocol, TypedDict

from .base_agent import BaseAgent, AgentConfig, AgentResult


# ---------------------------------------------------------------------------
# Agenten-DNA / Definition
# ---------------------------------------------------------------------------


class AgentDefinition(TypedDict, total=False):
    """
    Minimale DNA eines Agenten, wie sie im Repository gespeichert werden kann.

    Diese Struktur spiegelt zu großen Teilen AgentConfig wider und kann
    später direkt in eine AgentConfig überführt werden.
    """

    id: str
    name: str
    role: str
    model: str
    system_prompt: str
    temperature: float
    max_tokens: int
    tools: List[str]
    permissions: List[str]
    metadata: Dict[str, Any]


# ---------------------------------------------------------------------------
# Repository-Protokoll
# ---------------------------------------------------------------------------


class AgentRepository(Protocol):
    """
    Abstraktes Repository für Agenten-Konfigurationen.

    Du kannst später eine konkrete Implementierung bauen, z. B.:

    - FileSystemAgentRepository (JSON/YAML-Dateien)
    - SupabaseAgentRepository  (Tabelle "agents")
    - InMemoryAgentRepository  (für Tests)

    Der AgentManager kennt nur dieses Protokoll und bleibt dadurch
    unabhängig von der Storage-Technik.
    """

    def list_agents(self) -> List[AgentDefinition]: ...
    def get_agent(self, agent_id: str) -> Optional[AgentDefinition]: ...
    def save_agent(self, agent: AgentDefinition) -> AgentDefinition: ...
    def delete_agent(self, agent_id: str) -> bool: ...


# ---------------------------------------------------------------------------
# AgentManager
# ---------------------------------------------------------------------------


@dataclass
class AgentManagerConfig(AgentConfig):
    """
    Erweiterte Config für den AgentManager selbst.

    Hier könntest du später z. B. zusätzlich festlegen:
    - maximale Anzahl Agenten
    - Naming-Konventionen
    - Standard-Template für neue Agenten
    """

    default_role: str = "GENERIC"
    default_model: str = "phi3"
    default_temperature: float = 0.2
    default_max_tokens: int = 1024
    default_tools: List[str] = field(default_factory=list)
    default_permissions: List[str] = field(default_factory=list)


class AgentManager(BaseAgent):
    """
    Der AgentManager ist ein spezieller BRAIN-Agent, der für die Verwaltung
    anderer Agenten zuständig ist.

    Rechte / Permissions (Vorschlag):
    - "AGENT_CREATE"
    - "AGENT_EDIT"
    - "AGENT_DELETE"
    - "AGENT_VERIFY"

    Diese sollten in der AgentConfig.permissions des AgentManager gesetzt sein.
    """

    def __init__(
        self,
        llm_client,
        config: AgentManagerConfig,
        repository: AgentRepository,
        logger=None,
    ) -> None:
        super().__init__(llm_client=llm_client, config=config, logger=logger)
        self.repository = repository

        # Tools registrieren (optional, wenn du sie aus dem LLM heraus
        # explizit über execute_tool(...) ansprechen möchtest)
        self.register_tool("agent_add", self._tool_add_agent)
        self.register_tool("agent_update", self._tool_update_agent)
        self.register_tool("agent_delete", self._tool_delete_agent)
        self.register_tool("agent_verify", self._tool_verify_agent)

    # ------------------------------------------------------------------
    # High-Level Methoden (für Python-Code / API)
    # ------------------------------------------------------------------

    def _create_agent_id(self) -> str:
        return str(uuid.uuid4())

    def _build_definition(
        self,
        data: Dict[str, Any],
    ) -> AgentDefinition:
        """
        Baut eine vollständige AgentDefinition aus Rohdaten.

        - setzt Defaultwerte aus der AgentManagerConfig
        - generiert bei Bedarf eine ID
        """

        cfg: AgentManagerConfig = self.config  # type: ignore

        agent_id = data.get("id") or self._create_agent_id()

        definition: AgentDefinition = {
            "id": agent_id,
            "name": data.get("name", f"agent-{agent_id[:8]}"),
            "role": data.get("role", cfg.default_role),
            "model": data.get("model", cfg.default_model),
            "system_prompt": data.get("system_prompt", ""),
            "temperature": float(data.get("temperature", cfg.default_temperature)),
            "max_tokens": int(data.get("max_tokens", cfg.default_max_tokens)),
            "tools": list(data.get("tools", cfg.default_tools)),
            "permissions": list(data.get("permissions", cfg.default_permissions)),
            "metadata": dict(data.get("metadata", {})),
        }
        return definition

    def list_all_agents(self) -> List[AgentDefinition]:
        """
        Liefert eine Liste aller bekannten Agenten aus dem Repository.

        Nützlich für:
        - Admin-Übersicht im Control Deck
        - Debugging
        """
        return self.repository.list_agents()

    def add_agent(self, data: Dict[str, Any]) -> AgentResult:
        """
        Legt einen neuen Agenten im Repository an.

        Erwartet ein Dict mit den relevanten Feldern (name, role, model, ...).

        Sicherheitslogik:
        - Prüft Permission "AGENT_CREATE".
        """

        if not self.has_permission("AGENT_CREATE"):
            return {
                "id": str(uuid.uuid4()),
                "success": False,
                "message": "AgentManager hat keine Berechtigung, neue Agenten anzulegen.",
                "error": "MISSING_PERMISSION:AGENT_CREATE",
                "used_tools": [],
                "meta": {},
            }

        definition = self._build_definition(data)
        saved = self.repository.save_agent(definition)

        return {
            "id": saved["id"],
            "success": True,
            "message": f"Agent '{saved['name']}' wurde angelegt.",
            "raw_response": saved,
            "used_tools": ["agent_add"],
            "meta": {"action": "create"},
        }

    def update_agent(self, agent_id: str, patch: Dict[str, Any]) -> AgentResult:
        """
        Aktualisiert die Konfiguration eines bestehenden Agenten.

        - Lädt Agent aus Repository
        - Wendet Patch an
        - Speichert Agent zurück

        Sicherheitslogik:
        - Prüft Permission "AGENT_EDIT".
        """

        if not self.has_permission("AGENT_EDIT"):
            return {
                "id": str(uuid.uuid4()),
                "success": False,
                "message": "AgentManager hat keine Berechtigung, Agenten zu bearbeiten.",
                "error": "MISSING_PERMISSION:AGENT_EDIT",
                "used_tools": [],
                "meta": {},
            }

        existing = self.repository.get_agent(agent_id)
        if not existing:
            return {
                "id": agent_id,
                "success": False,
                "message": f"Agent mit ID '{agent_id}' wurde nicht gefunden.",
                "error": "NOT_FOUND",
                "used_tools": [],
                "meta": {},
            }

        updated: AgentDefinition = {**existing, **patch, "id": agent_id}  # type: ignore
        saved = self.repository.save_agent(updated)

        return {
            "id": saved["id"],
            "success": True,
            "message": f"Agent '{saved['name']}' wurde aktualisiert.",
            "raw_response": saved,
            "used_tools": ["agent_update"],
            "meta": {"action": "update"},
        }

    def delete_agent(self, agent_id: str) -> AgentResult:
        """
        Löscht einen Agenten aus dem Repository.

        Sicherheitslogik:
        - Prüft Permission "AGENT_DELETE".
        """

        if not self.has_permission("AGENT_DELETE"):
            return {
                "id": str(uuid.uuid4()),
                "success": False,
                "message": "AgentManager hat keine Berechtigung, Agenten zu löschen.",
                "error": "MISSING_PERMISSION:AGENT_DELETE",
                "used_tools": [],
                "meta": {},
            }

        ok = self.repository.delete_agent(agent_id)
        if not ok:
            return {
                "id": agent_id,
                "success": False,
                "message": f"Agent mit ID '{agent_id}' wurde nicht gefunden oder konnte nicht gelöscht werden.",
                "error": "NOT_FOUND_OR_DELETE_FAILED",
                "used_tools": ["agent_delete"],
                "meta": {},
            }

        return {
            "id": agent_id,
            "success": True,
            "message": f"Agent mit ID '{agent_id}' wurde gelöscht.",
            "used_tools": ["agent_delete"],
            "meta": {"action": "delete"},
        }

    async def verify_agent(self, agent_id: str) -> AgentResult:
        """
        Prüft einen Agenten mithilfe des LLMs auf:
        - Konsistenz
        - offensichtliche Fehler
        - potenzielle Sicherheitsrisiken (z. B. gefährliche Tools/Permissions)

        Sicherheitslogik:
        - Prüft Permission "AGENT_VERIFY".
        """

        if not self.has_permission("AGENT_VERIFY"):
            return {
                "id": str(uuid.uuid4()),
                "success": False,
                "message": "AgentManager hat keine Berechtigung, Agenten zu verifizieren.",
                "error": "MISSING_PERMISSION:AGENT_VERIFY",
                "used_tools": [],
                "meta": {},
            }

        agent = self.repository.get_agent(agent_id)
        if not agent:
            return {
                "id": agent_id,
                "success": False,
                "message": f"Agent mit ID '{agent_id}' wurde nicht gefunden.",
                "error": "NOT_FOUND",
                "used_tools": [],
                "meta": {},
            }

        # Der AgentManager nutzt hier seine LLM-Fähigkeiten, um die Definition
        # zu beurteilen. Später kannst du hier ein strukturiertes Prüf-Template
        # einbauen (Score, Risiko-Level etc.).
        prompt = (
            "Du bist Sicherheits- und Architekturprüfer für ein Multi-Agenten-System.\n"
            "Analysiere die folgende Agenten-Konfiguration auf Konsistenz und Sicherheit.\n"
            "Liste mögliche Risiken, Verbesserungsvorschläge und eine kurze Bewertung (OK / WARNUNG / KRITISCH) auf.\n\n"
            f"AgentDefinition:\n{agent}\n"
        )

        analysis = await self.call_llm(user_message=prompt)

        return {
            "id": agent_id,
            "success": True,
            "message": "Agent wurde geprüft. Siehe 'raw_response' für Details.",
            "raw_response": analysis,
            "used_tools": ["agent_verify"],
            "meta": {
                "action": "verify",
                "agent_name": agent.get("name"),
                "checked_at": dt.datetime.utcnow().isoformat() + "Z",
            },
        }

    def submit_for_review(
        self,
        agent_id: str,
        reviewer: str = "SUPERVISOR",
    ) -> AgentResult:
        """
        Bereitet eine Agentenänderung zur Freigabe vor.

        Diese Methode selbst verschickt noch nichts – sie erstellt ein
        strukturiertes Payload, das dann vom übergeordneten System
        (z. B. einem Supervisor-Agent oder einer menschlichen UI)
        verarbeitet werden kann.

        Idee:
        - Control Deck zeigt dieses Payload im UI
        - Ein Human oder Supervisor-Agent trifft die finale Entscheidung
        """

        agent = self.repository.get_agent(agent_id)
        if not agent:
            return {
                "id": agent_id,
                "success": False,
                "message": f"Agent mit ID '{agent_id}' wurde nicht gefunden.",
                "error": "NOT_FOUND",
                "used_tools": [],
                "meta": {},
            }

        review_payload = {
            "agent_id": agent_id,
            "agent_name": agent.get("name"),
            "requested_by": self.config.name,
            "reviewer": reviewer,
            "definition": agent,
        }

        return {
            "id": agent_id,
            "success": True,
            "message": "Agent wurde zur Prüfung vorbereitet.",
            "raw_response": review_payload,
            "used_tools": [],
            "meta": {
                "action": "submit_for_review",
                "reviewer": reviewer,
            },
        }

    # ------------------------------------------------------------------
    # Tool-Wrappers (optional für LLM-Tool-Aufrufe)
    # ------------------------------------------------------------------

    # Diese Methoden sind einfache Wrapper um die High-Level-Methoden,
    # damit sie bequem als Tools registriert werden können.

    def _tool_add_agent(self, data: Dict[str, Any]) -> AgentResult:
        return self.add_agent(data)

    def _tool_update_agent(self, agent_id: str, patch: Dict[str, Any]) -> AgentResult:
        return self.update_agent(agent_id, patch)

    def _tool_delete_agent(self, agent_id: str) -> AgentResult:
        return self.delete_agent(agent_id)

    def _tool_verify_agent(self, agent_id: str) -> AgentResult:
        # Achtung: verify_agent ist async → in Tools meist synchron erwartet.
        # Hier könntest du ein Async-Wrapper/Loop nutzen.
        # Fürs Grundgerüst lassen wir einen NotImplementedError stehen,
        # damit du bewusst entscheidest, wie du Async im Tooling behandelst.
        raise NotImplementedError(
            "agent_verify als Tool ist async – bitte über ein Async-Handling im "
            "Agenten-Router oder eine Task-Queue integrieren."
        )


# Ende von agent_manager.py
