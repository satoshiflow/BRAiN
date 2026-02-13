# backend/brain/agents/repositories.py

"""
repositories.py

Verschiedene Repository-Implementierungen für Agenten:
- InMemoryAgentRepository: nur für Tests / Dev
- JSONFileAgentRepository: persistente Speicherung als JSON-Datei
"""

from __future__ import annotations

import json
import threading
from pathlib import Path
from typing import List, Optional

from .agent_manager import AgentRepository, AgentDefinition


class InMemoryAgentRepository(AgentRepository):
    """
    Sehr einfacher In-Memory Speicher.
    Für Produktion später ersetzen durch:
    - JSONFileAgentRepository
    - SupabaseAgentRepository
    """
    def __init__(self) -> None:
        self._store: dict[str, AgentDefinition] = {}

    def list_agents(self) -> List[AgentDefinition]:
        return list(self._store.values())

    def get_agent(self, agent_id: str) -> Optional[AgentDefinition]:
        return self._store.get(agent_id)

    def save_agent(self, agent: AgentDefinition) -> AgentDefinition:
        self._store[agent["id"]] = agent
        return agent

    def delete_agent(self, agent_id: str) -> bool:
        return self._store.pop(agent_id, None) is not None


class JSONFileAgentRepository(AgentRepository):
    """
    JSON-basiertes Repository für Agenten.

    Speichert alle Agenten in einer Datei, z. B.:

        storage/agents/agents.json

    Struktur in der Datei:
    {
        "agents": {
            "<id>": {
                "id": "...",
                "name": "...",
                "role": "...",
                ...
            },
            ...
        }
    }

    Eigenschaften:
    - Thread-safe via einfachem Lock (für FastAPI-Mehrfachzugriffe ausreichend)
    - Erstellt Verzeichnis + Datei automatisch, falls sie nicht existieren
    """

    def __init__(self, json_path: str | Path) -> None:
        self.path = Path(json_path)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self._lock = threading.Lock()

        # Falls Datei noch nicht existiert → leeres Grundgerüst anlegen
        if not self.path.exists():
            self._write_raw({"agents": {}})

    # ----------------------------- interne Helfer -----------------------------

    def _read_raw(self) -> dict:
        with self._lock:
            if not self.path.exists():
                return {"agents": {}}
            with self.path.open("r", encoding="utf-8") as f:
                try:
                    data = json.load(f)
                except json.JSONDecodeError:
                    # falls Datei korrupt → leeres Gerüst
                    data = {"agents": {}}
            if "agents" not in data or not isinstance(data["agents"], dict):
                data["agents"] = {}
            return data

    def _write_raw(self, data: dict) -> None:
        with self._lock:
            # atomisches Schreiben über temporäre Datei
            tmp_path = self.path.with_suffix(".tmp")
            with tmp_path.open("w", encoding="utf-8") as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
            tmp_path.replace(self.path)

    # --------------------------- Protokoll-Methoden ---------------------------

    def list_agents(self) -> List[AgentDefinition]:
        data = self._read_raw()
        agents_dict: dict[str, AgentDefinition] = data.get("agents", {})  # type: ignore
        return list(agents_dict.values())

    def get_agent(self, agent_id: str) -> Optional[AgentDefinition]:
        data = self._read_raw()
        agents_dict: dict[str, AgentDefinition] = data.get("agents", {})  # type: ignore
        return agents_dict.get(agent_id)

    def save_agent(self, agent: AgentDefinition) -> AgentDefinition:
        if "id" not in agent:
            raise ValueError("AgentDefinition benötigt ein 'id'-Feld.")

        data = self._read_raw()
        agents_dict: dict[str, AgentDefinition] = data.get("agents", {})  # type: ignore
        agents_dict[agent["id"]] = agent
        data["agents"] = agents_dict
        self._write_raw(data)
        return agent

    def delete_agent(self, agent_id: str) -> bool:
        data = self._read_raw()
        agents_dict: dict[str, AgentDefinition] = data.get("agents", {})  # type: ignore

        if agent_id not in agents_dict:
            return False

        del agents_dict[agent_id]
        data["agents"] = agents_dict
        self._write_raw(data)
        return True
# Ende von repositories.py