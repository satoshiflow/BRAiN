"""
AXE Fusion Router - FastAPI Router für AXEllm Integration

Endpoint: POST /api/axe/chat
"""

import logging
from typing import List, Optional
from fastapi import APIRouter, HTTPException, status, Depends
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession
from app.core.database import get_db

from .service import (
    get_axe_fusion_service,
    AXEllmUnavailableError,
    AXEllmValidationError,
    AXEllmError
)

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/axe", tags=["axe-fusion"])


# === Schemas ===

class ChatMessage(BaseModel):
    """Einzelne Chat-Nachricht im OpenAI Format"""
    role: str = Field(..., description="Rolle: system, user, oder assistant")
    content: str = Field(..., description="Nachrichteninhalt")
    
    class Config:
        json_schema_extra = {
            "example": {
                "role": "user",
                "content": "Hallo, wer bist du?"
            }
        }


class ChatRequest(BaseModel):
    """Chat Request im OpenAI Format"""
    model: str = Field(..., description="Modell-Name (z.B. 'gpt-4', 'claude-3')")
    messages: List[ChatMessage] = Field(..., description="Liste der Chat-Nachrichten")
    temperature: Optional[float] = Field(0.7, ge=0.0, le=2.0, description="Sampling Temperatur")
    
    class Config:
        json_schema_extra = {
            "example": {
                "model": "gpt-4",
                "messages": [
                    {"role": "system", "content": "Du bist ein hilfreicher Assistent."},
                    {"role": "user", "content": "Hallo!"}
                ],
                "temperature": 0.7
            }
        }


class ChatResponse(BaseModel):
    """Chat Response Format"""
    text: str = Field(..., description="Generierter Text")
    raw: dict = Field(..., description="Rohdaten von AXEllm")
    
    class Config:
        json_schema_extra = {
            "example": {
                "text": "Hallo! Wie kann ich dir helfen?",
                "raw": {
                    "choices": [{"message": {"content": "Hallo! Wie kann ich dir helfen?"}}]
                }
            }
        }


class HealthResponse(BaseModel):
    """Health Check Response"""
    status: str
    axellm: str
    error: Optional[str] = None


# === Endpoints ===

@router.post(
    "/chat",
    response_model=ChatResponse,
    status_code=status.HTTP_200_OK,
    summary="Chat mit AXEllm",
    description="Sendet einen Chat-Request an AXEllm und gibt die Antwort zurück."
)
async def axe_chat(
    request: ChatRequest,
    db: AsyncSession = Depends(get_db)
) -> ChatResponse:
    """
    Chat Endpoint für AXEllm Integration.
    
    Akzeptiert OpenAI-kompatible Requests und leitet sie an AXEllm weiter.
    
    **Guardrails:**
    - Max 20.000 Zeichen pro Request
    - Nur Rollen: system, user, assistant
    - Tool/Function Felder werden entfernt
    
    **Features:**
    - Automatische AXE Identity System Prompt Injection
    
    **Fehlercodes:**
    - 503: AXEllm nicht erreichbar
    - 400: Validierungsfehler (z.B. Zeichenlimit überschritten)
    - 500: Interner Fehler
    """
    service = get_axe_fusion_service(db=db)
    
    try:
        # Konvertiere Pydantic Model zu Dict für Service
        messages = [msg.model_dump() for msg in request.messages]
        
        result = await service.chat(
            model=request.model,
            messages=messages,
            temperature=request.temperature or 0.7
        )
        
        return ChatResponse(
            text=result["text"],
            raw=result["raw"]
        )
        
    except AXEllmUnavailableError as e:
        logger.error(f"AXEllm nicht verfügbar: {e}")
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail={
                "error": "AXEllm Service nicht verfügbar",
                "message": str(e),
                "code": "AXELLM_UNAVAILABLE"
            }
        )
        
    except AXEllmValidationError as e:
        logger.warning(f"AXEllm Validierungsfehler: {e}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={
                "error": "Validierungsfehler",
                "message": str(e),
                "code": "VALIDATION_ERROR"
            }
        )
        
    except AXEllmError as e:
        logger.error(f"AXEllm Fehler: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={
                "error": "AXEllm Fehler",
                "message": str(e),
                "code": "AXELLM_ERROR"
            }
        )
        
    except Exception as e:
        logger.exception(f"Unerwarteter Fehler in axe_chat: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={
                "error": "Interner Server Fehler",
                "message": "Ein unerwarteter Fehler ist aufgetreten",
                "code": "INTERNAL_ERROR"
            }
        )


@router.get(
    "/health",
    response_model=HealthResponse,
    summary="AXEllm Health Check",
    description="Prüft ob AXEllm erreichbar ist."
)
async def axe_health() -> HealthResponse:
    """
    Health Check für AXEllm Verbindung.
    """
    service = get_axe_fusion_service()
    result = await service.health_check()
    
    return HealthResponse(
        status=result["status"],
        axellm=result["axellm"],
        error=result.get("error")
    )
