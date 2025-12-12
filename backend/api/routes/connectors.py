# backend/api/routes/connectors.py

from __future__ import annotations

from typing import Any, Dict, List

from fastapi import APIRouter

router = APIRouter(
    prefix="/api/connectors",
    tags=["connectors"],
)


@router.get("/info")
async def connectors_info() -> Dict[str, Any]:
    """
    Basis-Info über den Connector-Hub.
    """
    return {
        "name": "Connector Hub",
        "version": "1.0.0",
        "status": "online",
        "description": "Schnittstelle für externe Systeme (LLMs, Datenquellen, Tools).",
    }


@router.get("/list")
async def connectors_list() -> Dict[str, List[Dict[str, Any]]]:
    """
    Platzhalter-Liste der verfügbaren Connectoren.
    Später aus deiner connector_hub-Registry befüllen.
    """
    connectors = [
        {
            "id": "ollama_local",
            "name": "Ollama (local)",
            "type": "llm",
            "status": "online",
        },
    ]
    return {"connectors": connectors}
