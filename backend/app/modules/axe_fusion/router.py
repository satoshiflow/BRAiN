"""
AXE Fusion Router - FastAPI Router für AXEllm Integration

Endpoint: POST /api/axe/chat
"""

import logging
import os
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import List, Optional
from uuid import uuid4

from fastapi import APIRouter, Depends, File, Header, HTTPException, Request, UploadFile, status
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession
from app.core.database import get_db
from app.modules.axe_governance import (
    AXERequestContext,
    TrustTier,
    get_axe_trust_validator,
)

from .service import (
    get_axe_fusion_service,
    AXEllmUnavailableError,
    AXEllmValidationError,
    AXEllmError
)

logger = logging.getLogger(__name__)

UPLOAD_BASE_DIR = Path(os.getenv("AXE_UPLOAD_DIR", "/tmp/axe_uploads"))
UPLOAD_MAX_BYTES = int(os.getenv("AXE_UPLOAD_MAX_BYTES", str(10 * 1024 * 1024)))
UPLOAD_ALLOWED_MIME_TYPES = {
    "image/jpeg",
    "image/png",
    "image/webp",
    "application/pdf",
    "text/plain",
}

router = APIRouter(
    prefix="/axe",
    tags=["axe-fusion"],
)


async def validate_axe_trust(
    request: Request,
    x_dmz_gateway_id: Optional[str] = Header(None),
    x_dmz_gateway_token: Optional[str] = Header(None),
) -> AXERequestContext:
    """Allow only LOCAL/DMZ traffic for AXE chat endpoints (fail-closed)."""
    allow_local_requests = (
        os.getenv("AXE_FUSION_ALLOW_LOCAL_REQUESTS", "false").lower() == "true"
    )
    request_id = request.headers.get("x-request-id", "axe-fusion-request")
    client_host = request.client.host if request.client else None
    headers = dict(request.headers)

    if x_dmz_gateway_id:
        headers["x-dmz-gateway-id"] = x_dmz_gateway_id
    if x_dmz_gateway_token:
        headers["x-dmz-gateway-token"] = x_dmz_gateway_token

    try:
        validator = get_axe_trust_validator()
        context = await validator.validate_request(
            headers=headers,
            client_host=client_host,
            request_id=request_id,
        )
        if context.trust_tier == TrustTier.LOCAL and not allow_local_requests:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail={
                    "error": "Forbidden",
                    "message": "Local AXE access is disabled for this environment",
                    "trust_tier": context.trust_tier.value,
                    "request_id": context.request_id,
                },
            )
        if not validator.is_request_allowed(context):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail={
                    "error": "Forbidden",
                    "message": "AXE endpoint is only accessible via DMZ gateways",
                    "trust_tier": context.trust_tier.value,
                    "request_id": context.request_id,
                },
            )
        return context
    except ValueError as exc:
        allow_local_fallback = (
            os.getenv("AXE_FUSION_ALLOW_LOCAL_FALLBACK", "false").lower() == "true"
        )
        if (
            allow_local_requests
            and allow_local_fallback
            and client_host in {"127.0.0.1", "::1", "localhost"}
        ):
            logger.warning(
                "BRAIN_DMZ_GATEWAY_SECRET not set; allowing localhost-only AXE chat traffic"
            )
            return AXERequestContext(
                trust_tier=TrustTier.LOCAL,
                source_service="localhost",
                source_ip=client_host,
                authenticated=True,
                request_id=request_id,
                user_agent=request.headers.get("user-agent"),
                rate_limit_key=f"local:{client_host}",
            )
        logger.error("AXE governance unavailable: %s", exc)
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail={
                "error": "AXE governance unavailable",
                "message": "AXE trust-tier validation is not configured",
                "code": "AXE_GOVERNANCE_UNAVAILABLE",
            },
        )


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
    attachments: Optional[List[str]] = Field(None, description="Optionale Attachment-Referenzen")
    
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


class UploadResponse(BaseModel):
    attachment_id: str
    filename: str
    mime_type: str
    size_bytes: int
    expires_at: str


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
    db: AsyncSession = Depends(get_db),
    context: AXERequestContext = Depends(validate_axe_trust),
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
        logger.info(
            "AXE chat request accepted (trust_tier=%s source=%s)",
            context.trust_tier.value,
            context.source_service,
        )
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
async def axe_health(
    context: AXERequestContext = Depends(validate_axe_trust),
) -> HealthResponse:
    """
    Health Check für AXEllm Verbindung.
    """
    logger.debug(
        "AXE health request accepted (trust_tier=%s source=%s)",
        context.trust_tier.value,
        context.source_service,
    )
    service = get_axe_fusion_service()
    result = await service.health_check()
    
    return HealthResponse(
        status=result["status"],
        axellm=result["axellm"],
        error=result.get("error")
    )


@router.post(
    "/upload",
    response_model=UploadResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Upload AXE Attachment",
    description="Speichert ein erlaubtes Attachment und gibt eine Referenz-ID für Chat Requests zurück.",
)
async def axe_upload(
    file: UploadFile = File(...),
    context: AXERequestContext = Depends(validate_axe_trust),
) -> UploadResponse:
    if file.content_type not in UPLOAD_ALLOWED_MIME_TYPES:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={
                "error": "Unsupported file type",
                "message": f"Unsupported content type: {file.content_type}",
                "code": "UNSUPPORTED_ATTACHMENT_TYPE",
            },
        )

    payload = await file.read()
    size_bytes = len(payload)

    if size_bytes == 0:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={
                "error": "Empty file",
                "message": "Attachment must not be empty",
                "code": "EMPTY_ATTACHMENT",
            },
        )

    if size_bytes > UPLOAD_MAX_BYTES:
        raise HTTPException(
            status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
            detail={
                "error": "File too large",
                "message": f"Attachment exceeds max size of {UPLOAD_MAX_BYTES} bytes",
                "code": "ATTACHMENT_TOO_LARGE",
            },
        )

    attachment_id = f"att_{uuid4().hex}"
    UPLOAD_BASE_DIR.mkdir(parents=True, exist_ok=True)

    suffix = Path(file.filename or "upload").suffix
    target_path = UPLOAD_BASE_DIR / f"{attachment_id}{suffix}"
    target_path.write_bytes(payload)

    logger.info(
        "AXE attachment uploaded (id=%s, trust_tier=%s, source=%s, size=%s)",
        attachment_id,
        context.trust_tier.value,
        context.source_service,
        size_bytes,
    )

    expires_at = (datetime.now(timezone.utc) + timedelta(hours=24)).isoformat()
    return UploadResponse(
        attachment_id=attachment_id,
        filename=file.filename or "upload",
        mime_type=file.content_type or "application/octet-stream",
        size_bytes=size_bytes,
        expires_at=expires_at,
    )
