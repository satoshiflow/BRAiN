# backend/api/routes/debug_llm.py

from __future__ import annotations

from typing import Any, Dict

from fastapi import APIRouter
from pydantic import BaseModel

from modules.llm_client import get_llm_client

router = APIRouter(
    prefix="/api/debug",
    tags=["debug"],
)


class LLMTestRequest(BaseModel):
    prompt: str | None = "Sag kurz Hallo. Du bist BRAiN im Dev-Modus."


class LLMTestResponse(BaseModel):
    ok: bool
    model: str
    prompt: str
    raw_response: Dict[str, Any]


@router.post("/llm-ping", response_model=LLMTestResponse)
async def llm_ping(body: LLMTestRequest) -> LLMTestResponse:
    """
    Debug-Endpoint:
    Backend → zentraler LLMClient → Ollama → Modell.
    """
    client = get_llm_client()
    prompt = body.prompt or ""

    try:
        raw = await client.generate(prompt)
        return LLMTestResponse(
            ok=True,
            model=client.model,
            prompt=prompt,
            raw_response=raw,
        )
    except Exception as e:
        return LLMTestResponse(
            ok=False,
            model=client.model,
            prompt=prompt,
            raw_response={"error": str(e)},
        )
# End of file
