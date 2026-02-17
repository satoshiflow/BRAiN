# backend/brain/agents/repositories_supabase.py

from typing import List, Optional
from supabase import create_client, Client
from .agent_manager import AgentRepository, AgentDefinition


class SupabaseAgentRepository(AgentRepository):
    """
    Persistente Speicherung der Agenten in einer Supabase-Tabelle:

        brain_agents

    Vorteil:
    - Multi-User tauglich
    - Control Deck synchron über mehrere Instanzen
    - Revisionsfähig durch Row-Level-History (optional)
    """

    def __init__(self, supabase_url: str, supabase_key: str):
        self.client: Client = create_client(supabase_url, supabase_key)
        self.table = "brain_agents"

    # -------------------------------------------------------------

    def list_agents(self) -> List[AgentDefinition]:
        res = (
            self.client.table(self.table)
            .select("*")
            .execute()
        )
        return res.data or []

    def get_agent(self, agent_id: str) -> Optional[AgentDefinition]:
        res = (
            self.client.table(self.table)
            .select("*")
            .eq("id", agent_id)
            .single()
            .execute()
        )
        return res.data

    def save_agent(self, agent: AgentDefinition) -> AgentDefinition:
        # upsert = update OR insert
        res = (
            self.client.table(self.table)
            .upsert(agent)
            .execute()
        )
        return res.data[0]

    def delete_agent(self, agent_id: str) -> bool:
        res = (
            self.client.table(self.table)
            .delete()
            .eq("id", agent_id)
            .execute()
        )
        return bool(res.data)
