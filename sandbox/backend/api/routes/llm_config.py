# backend/api/routes/llm_config.py

from __future__ import annotations

from fastapi import APIRouter, HTTPException, status

from modules.llm_config import (
    LLMConfig,
    LLMConfigUpdate,
    get_llm_config,
    update_llm_config,
    reset_llm_config,
)

router = APIRouter(
    prefix="/api/llm",
    tags=["llm"],
)


@router.get("/config", response_model=LLMConfig)
async def get_config() -> LLMConfig:
    """
    Liefert die aktuell aktive LLM-Konfiguration.
    """
    return get_llm_config()


@router.put(
    "/config",
    response_model=LLMConfig,
    status_code=status.HTTP_200_OK,
)
async def put_config(body: LLMConfigUpdate) -> LLMConfig:
    """
    Aktualisiert die LLM-Konfiguration teilweise.
    Nur Felder, die im Body gesetzt sind, werden übernommen.

    Beispiel-Payload (JSON):
    {
      "host": "http://localhost:11434",
      "model": "phi3:latest",
      "temperature": 0.4
    }
    """
    try:
        new_cfg = update_llm_config(body)
        return new_cfg
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(exc),
        ) from exc


@router.post(
    "/config/reset",
    response_model=LLMConfig,
    status_code=status.HTTP_200_OK,
)
async def post_reset_config() -> LLMConfig:
    """
    Setzt die LLM-Konfiguration auf die Default-Werte zurück
    (ENV/Hardcoded) und überschreibt die bestehende JSON-Datei.
    """
    new_cfg = reset_llm_config()
    return new_cfg
# Ende von backend/api/routes/llm_config.py