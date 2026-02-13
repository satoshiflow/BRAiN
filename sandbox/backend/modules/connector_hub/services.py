from __future__ import annotations

from dataclasses import dataclass, asdict
from datetime import datetime
from enum import Enum
from typing import Dict, List, Optional
import os


class ConnectorType(str, Enum):
    LLM = "llm"
    WEBHOOK = "webhook"
    DATA = "data"
    OTHER = "other"


class ConnectorStatus(str, Enum):
    AVAILABLE = "available"
    DISABLED = "disabled"
    ERROR = "error"


@dataclass
class Connector:
    id: str
    name: str
    type: ConnectorType
    description: str = ""
    status: ConnectorStatus = ConnectorStatus.DISABLED
    enabled: bool = False
    last_checked: Optional[datetime] = None
    meta: Dict[str, str] | None = None

    def to_dict(self) -> Dict:
        data = asdict(self)
        if self.last_checked:
            data["last_checked"] = self.last_checked.isoformat()
        return data


class ConnectorRegistry:
    """
    Zentrale Registry für alle externen / internen Connectoren.
    Wird später über das Control Deck konfigurierbar gemacht.
    """

    def __init__(self) -> None:
        self._connectors: Dict[str, Connector] = {}
        self._load_builtin_connectors()

    # --- interne Helper -----------------------------------------------------

    def _load_builtin_connectors(self) -> None:
        """Ein paar sinnvolle Default-Connectoren registrieren."""
        # Lokales Ollama
        ollama_host = os.getenv("OLLAMA_HOST")
        self.register(
            Connector(
                id="ollama_local",
                name="Ollama (local)",
                type=ConnectorType.LLM,
                description="Lokaler LLM über OLLAMA_HOST",
                status=ConnectorStatus.AVAILABLE if ollama_host else ConnectorStatus.DISABLED,
                enabled=bool(ollama_host),
                meta={"env": "OLLAMA_HOST", "host": ollama_host or ""},
            )
        )

        # OpenAI / API-Gateway (später über ENV / Secrets)
        self.register(
            Connector(
                id="openai_gateway",
                name="OpenAI Gateway",
                type=ConnectorType.LLM,
                description="Externer LLM über API-Gateway (z.B. BaaS / FalkLabs Proxy)",
                status=ConnectorStatus.DISABLED,
                enabled=False,
                meta={"env": "OPENAI_API_KEY"},
            )
        )

        # Dummy-Webhook für Tests
        self.register(
            Connector(
                id="dummy_webhook",
                name="Dummy Webhook",
                type=ConnectorType.WEBHOOK,
                description="Interner Test-Webhook für Dev/Tests",
                status=ConnectorStatus.AVAILABLE,
                enabled=True,
                meta={"url": "http://localhost/dummy"},
            )
        )

    # --- öffentliche API ----------------------------------------------------

    def register(self, connector: Connector) -> None:
        self._connectors[connector.id] = connector

    def list_connectors(self) -> Dict[str, Connector]:
        return dict(self._connectors)

    def list_connectors_as_dicts(self) -> List[Dict]:
        return [c.to_dict() for c in self._connectors.values()]

    def get(self, connector_id: str) -> Optional[Connector]:
        return self._connectors.get(connector_id)

    def summary(self) -> Dict:
        total = len(self._connectors)
        enabled = sum(1 for c in self._connectors.values() if c.enabled)
        available = sum(
            1
            for c in self._connectors.values()
            if c.status == ConnectorStatus.AVAILABLE
        )
        return {
            "total": total,
            "enabled": enabled,
            "available": available,
        }


# Globale Registry-Instanz für das Modul
registry = ConnectorRegistry()


def get_gateway() -> Optional[Connector]:
    """
    Legacy-Hilfsfunktion für Module wie axe.py.

    Strategie:
    - wenn ein aktivierter, verfügbarer 'openai_gateway' existiert -> nimm den
    - sonst: wenn ein aktivierter 'ollama_local' existiert -> nimm den
    - sonst: None zurückgeben (Aufrufer muss damit umgehen)
    """
    # 1) bevorzugt externes Gateway
    gw = registry.get("openai_gateway")
    if gw and gw.enabled and gw.status == ConnectorStatus.AVAILABLE:
        return gw

    # 2) fallback: lokales Ollama
    gw = registry.get("ollama_local")
    if gw and gw.enabled and gw.status == ConnectorStatus.AVAILABLE:
        return gw

    # 3) sonst kein Gateway
    return None
