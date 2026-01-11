# backend/api/routes/agent_manager.py

from __future__ import annotations

from typing import Any, Dict, Optional

from fastapi import APIRouter
from pydantic import BaseModel, Field

from modules.llm_client import get_llm_client

router = APIRouter(
    prefix="/api/agents",
    tags=["agents"],
)


class ChatRequest(BaseModel):
    message: str = Field(
        default="Sag kurz Hallo. Du bist BRAiN im Dev-Modus.",
        description="Nutzereingabe / Prompt",
        examples=["Bau mir eine Landingpage für FeWoHeroes."],
    )
    agent_id: Optional[str] = Field(
        default=None,
        description="Optional: spezifischer Agent (Name oder ID).",
    )
    metadata: Dict[str, Any] = Field(
        default_factory=dict,
        description="Kontextinfos (Quelle, Session, User-ID, usw.).",
    )


class ChatResponse(BaseModel):
    agent_id: str
    reply: str
    raw_llm: Dict[str, Any]
    metadata: Dict[str, Any]


@router.get("/info")
async def agents_info() -> Dict[str, Any]:
    client = get_llm_client()
    return {
        "name": "Agent Manager",
        "version": "1.0",
        "status": "online",
        "description": "Zentrale Schnittstelle für Agenten-Chats und Routing.",
        "default_model": client.model,
    }


@router.post("/chat", response_model=ChatResponse)
async def agent_chat(body: ChatRequest) -> ChatResponse:
    """
    Einfacher Agenten-Chat über den zentralen LLMClient.

    Wichtig:
    - Exceptions des LLM-Clients werden hier gefangen,
      damit der Endpoint nie mit 500 antwortet.
    """
    agent_id = body.agent_id or "brain.default"
    metadata = body.metadata or {}

    client = get_llm_client()

    system_prompt = (
        "Du bist BRAiN, ein hilfreicher KI-Assistent im Dev-Modus. "
        "Antworte präzise, freundlich und auf Deutsch. "
        f"Agent-ID: {agent_id}."
    )

    try:
        reply_text, raw = await client.simple_chat(
            user_message=body.message,
            system_prompt=system_prompt,
            extra_params=None,
        )
    except Exception as e:
        # Fange alle LLM-/Netz-Fehler ab → keine 500er für den Client
        reply_text = f"[LLM-Fehler] {e}"
        raw = {"error": str(e)}

    return ChatResponse(
        agent_id=agent_id,
        reply=reply_text,
        raw_llm=raw,
        metadata=metadata,
    )
# End of file
