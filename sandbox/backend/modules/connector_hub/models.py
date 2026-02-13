from enum import Enum
from typing import Dict, Any


class ConnectorType(str, Enum):
    API = "api"              # klassische HTTP-API
    AXE = "axe"              # unser Axolotl / Axe-Interface
    MCP = "mcp"              # Model Context Protocol
    TCP = "tcp"              # Roh-TCP / Sockets
    WS = "websocket"         # WebSockets
    CLI = "cli"              # Kommandozeilen-Input
    INTERNAL_AGENT = "agent" # interne Agenten-Kommunikation
    UNKNOWN = "unknown"


class ConnectorConfig(Dict[str, Any]):
    """Platzhalter für zukünftige Konfiguration (Rate Limits, Policies etc.)."""
    pass
