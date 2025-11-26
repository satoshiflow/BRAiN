"""
base_agent.py

Zentrale Basisklasse für alle BRAIN-Agenten.

Idee:
- Jeder spezialisierte Agent (Coder, Ops, Architect, AgentManager, …)
  erbt von `BaseAgent`.
- Die Business-Logik (add/del/edit/test/…) sitzt in Python-Methoden.
- Die "Intelligenz" kommt vom LLM, das über `llm_client` angebunden ist.
- Werkzeuge (Tools) sind normale Python-Funktionen, die der Agent
  kontrolliert aufrufen darf.

Die Klasse ist bewusst generisch gehalten, damit du sie in jedem Projekt
wiederverwenden kannst.
"""

from __future__ import annotations

import uuid
import logging
import datetime as dt
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Callable, Protocol, TypedDict


# ---------------------------------------------------------------------------
# Typen & Protokolle
# ---------------------------------------------------------------------------

class LLMClient(Protocol):
    """
    Abstraktes Protokoll für einen LLM-Client.

    Erwartet wird eine Implementierung mit einer `generate`-Methode,
    z. B. ein Wrapper um Ollama, OpenAI, OpenRouter, etc.

    Du kannst später eine konkrete Klasse schreiben, die dieses Protokoll
    erfüllt, z. B.:

        class OllamaClient:
            async def generate(self, model: str, messages: List[Dict[str, str]], **kwargs) -> str:
                ...

    Für den BaseAgent ist nur wichtig, dass `generate(...) -> str` vorhanden ist.
    """

    async def generate(
        self,
        model: str,
        messages: List[Dict[str, str]],
        **kwargs: Any,
    ) -> str: ...


@dataclass
class AgentConfig:
    """
    Konfiguration / DNA eines Agenten.

    Diese Daten können aus JSON, Datenbank oder einer YAML-Datei
    kommen und werden hier nur typisiert zusammengefasst.
    """

    name: str
    role: str = "GENERIC"                     # z. B. "CODER", "OPS", "SUPERVISOR"
    model: str = "phi3"                       # Standardmodell (Ollama)
    system_prompt: str = ""                   # Instruktionen an das LLM
    temperature: float = 0.2
    max_tokens: int = 1024
    tools: List[str] = field(default_factory=list)         # erlaubte Tools (by name)
    permissions: List[str] = field(default_factory=list)   # abstrakte Rechte, z. B. "AGENT_CREATE"
    metadata: Dict[str, Any] = field(default_factory=dict)


class AgentResult(TypedDict, total=False):
    """
    Standard-Return-Typ für Agenten.

    Keys sind absichtlich optional, damit du flexibel erweitern kannst.
    """

    id: str
    success: bool
    message: str          # Zusammenfassung / Hauptoutput
    raw_response: Any     # Rohantwort des LLM
    used_tools: List[str]
    error: Optional[str]
    meta: Dict[str, Any]


ToolFunc = Callable[..., Any]


# ---------------------------------------------------------------------------
# BaseAgent
# ---------------------------------------------------------------------------

class BaseAgent:
    """
    Basisklasse für alle BRAIN-Agenten.

    WICHTIGES KONZEPT:

    - `BaseAgent` kümmert sich um:
        * Logging
        * Aufruf des LLM (über `llm_client`)
        * Verwaltung von Tools (Python-Funktionen)
        * einfache Permissions
        * standardisierte Rückgabestruktur

    - Abgeleitete Klassen (z. B. `CoderAgent`, `OpsAgent`, `AgentManager`)
      implementieren:
        * Domänenspezifische Methoden (add, del, edit, verify, deploy, ...)
        * eigene Helper-Funktionen
        * ggf. eigene Tools registrieren

    TYPISCHE NUTZUNG:

        class CoderAgent(BaseAgent):
            def __init__(self, llm_client, config):
                super().__init__(llm_client, config)
                self.register_tool("create_file", self.create_file)

            def create_file(self, path: str, content: str) -> None:
                ...

            async def implement_feature(self, spec: str) -> AgentResult:
                # hier LLM + Tools kombinieren
                ...

    """

    def __init__(
        self,
        llm_client: LLMClient,
        config: AgentConfig,
        logger: Optional[logging.Logger] = None,
    ) -> None:
        self.id: str = str(uuid.uuid4())
        self.llm_client = llm_client
        self.config = config

        # zentrale Tool-Registry (name -> callable)
        self._tools: Dict[str, ToolFunc] = {}

        # Logger vorbereiten
        self.logger = logger or logging.getLogger(f"BRAIN.Agent.{config.name}")
        if not self.logger.handlers:
            # einfacher default Handler, falls noch keiner gesetzt ist
            handler = logging.StreamHandler()
            formatter = logging.Formatter(
                "[%(asctime)s] [%(name)s] [%(levelname)s] %(message)s"
            )
            handler.setFormatter(formatter)
            self.logger.addHandler(handler)
            self.logger.setLevel(logging.INFO)

        self.logger.debug(
            "BaseAgent initialisiert | id=%s name=%s role=%s model=%s",
            self.id,
            self.config.name,
            self.config.role,
            self.config.model,
        )

    # ------------------------------------------------------------------
    # Tools & Permissions
    # ------------------------------------------------------------------

    def register_tool(self, name: str, func: ToolFunc) -> None:
        """
        Registriert eine Python-Funktion als Tool, das vom Agenten
        aufgerufen werden kann.

        Hinweise:
        - `name` sollte eindeutig sein.
        - Die Funktion `func` sollte idealerweise "sauber" sein:
          * gut dokumentiert
          * klar definierte Parameter
          * keine Seiteneffekte außerhalb des erlaubten Bereichs.

        Beispiel:

            self.register_tool("create_file", self.create_file)
        """
        self._tools[name] = func
        self.logger.debug("Tool registriert: %s", name)

    def has_permission(self, permission: str) -> bool:
        """
        Prüft, ob der Agent ein bestimmtes Recht besitzt.

        Wird z. B. von AgentManager genutzt, um zu entscheiden, ob
        er neue Agenten anlegen oder löschen darf.
        """
        return permission in self.config.permissions

    def can_use_tool(self, tool_name: str) -> bool:
        """
        Prüft, ob der Agent ein bestimmtes Tool benutzen darf.
        """
        return tool_name in self.config.tools and tool_name in self._tools

    def execute_tool(self, tool_name: str, *args: Any, **kwargs: Any) -> Any:
        """
        Führt ein registriertes Tool aus, sofern es in der Agent-Config
        erlaubt ist.

        Sicherheitsmechanismus:
        - Tool muss registriert sein UND
        - Toolname muss in `config.tools` freigeschaltet sein.

        Andernfalls wird eine Exception geworfen.
        """
        if not self.can_use_tool(tool_name):
            raise PermissionError(
                f"Agent '{self.config.name}' darf Tool '{tool_name}' nicht verwenden."
            )

        self.logger.info("Agent %s verwendet Tool: %s", self.config.name, tool_name)
        func = self._tools[tool_name]
        return func(*args, **kwargs)

    # ------------------------------------------------------------------
    # LLM-Interaktion
    # ------------------------------------------------------------------

    async def call_llm(
        self,
        user_message: str,
        *,
        system_prompt: Optional[str] = None,
        extra_messages: Optional[List[Dict[str, str]]] = None,
        temperature: Optional[float] = None,
        max_tokens: Optional[int] = None,
        **kwargs: Any,
    ) -> str:
        """
        Zentraler Einstieg, um das LLM für diesen Agenten aufzurufen.

        Parameter:
        - user_message: die eigentliche Anfrage des Nutzers / Systems.
        - system_prompt: optionaler Override des Standard-Systemprompts
          aus `self.config.system_prompt`.
        - extra_messages: zusätzliche Messages (z. B. Kontext, Beispiele).
        - temperature / max_tokens: falls gesetzt, überschreiben sie
          die Werte in der AgentConfig.
        - kwargs: wird direkt an den LLM-Client durchgereicht
                 (z. B. "top_p", "stop", ...).

        Rückgabe:
        - reiner Text-Output des LLM als `str`.
        """

        sys_prompt = system_prompt if system_prompt is not None else self.config.system_prompt
        messages: List[Dict[str, str]] = []

        if sys_prompt:
            messages.append({"role": "system", "content": sys_prompt})

        if extra_messages:
            messages.extend(extra_messages)

        messages.append({"role": "user", "content": user_message})

        temp = temperature if temperature is not None else self.config.temperature
        max_toks = max_tokens if max_tokens is not None else self.config.max_tokens

        self.logger.debug(
            "LLM-Aufruf | agent=%s model=%s temp=%.2f max_tokens=%d",
            self.config.name,
            self.config.model,
            temp,
            max_toks,
        )

        response = await self.llm_client.generate(
            model=self.config.model,
            messages=messages,
            temperature=temp,
            max_tokens=max_toks,
            **kwargs,
        )

        return response

    # ------------------------------------------------------------------
    # High-Level API
    # ------------------------------------------------------------------

    async def run(
        self,
        task: str,
        context: Optional[Dict[str, Any]] = None,
    ) -> AgentResult:
        """
        Generische "Fallback"-Methode, um den Agenten mit einer
        freien Aufgabe anzusprechen.

        In vielen Fällen wirst du in abgeleiteten Klassen spezifische
        Methoden definieren (z. B. `implement_feature`, `deploy_service`, …).

        Diese Methode ist dennoch nützlich als:
        - Default-Implementierung
        - Debug / schnelle Experimente
        - einfacher Einstiegspunkt für das Routing

        Standardverhalten:
        - Ruft das LLM mit dem Standard-Systemprompt auf
        - Baut ein einfaches AgentResult
        """

        start = dt.datetime.utcnow()
        self.logger.info("Agent %s startet Task: %s", self.config.name, task)

        try:
            context_msg = ""
            if context:
                # Kontext wird dem LLM als zusätzlicher Text mitgegeben
                context_msg = f"\n\n[Kontext für die Aufgabe]\n{context}"

            llm_output = await self.call_llm(task + context_msg)

            duration = (dt.datetime.utcnow() - start).total_seconds()

            result: AgentResult = {
                "id": str(uuid.uuid4()),
                "success": True,
                "message": llm_output,
                "raw_response": llm_output,
                "used_tools": [],
                "meta": {
                    "agent_id": self.id,
                    "agent_name": self.config.name,
                    "duration_s": duration,
                    "timestamp": start.isoformat() + "Z",
                },
            }

            self.logger.info(
                "Agent %s hat Task erfolgreich beendet (%.2fs)",
                self.config.name,
                duration,
            )
            return result

        except Exception as exc:
            duration = (dt.datetime.utcnow() - start).total_seconds()
            self.logger.exception("Agent %s Fehler bei Task: %s", self.config.name, exc)

            return {
                "id": str(uuid.uuid4()),
                "success": False,
                "message": "Agent konnte die Aufgabe nicht erfolgreich ausführen.",
                "error": str(exc),
                "used_tools": [],
                "meta": {
                    "agent_id": self.id,
                    "agent_name": self.config.name,
                    "duration_s": duration,
                    "timestamp": start.isoformat() + "Z",
                },
            }
# Ende von base_agent.py
