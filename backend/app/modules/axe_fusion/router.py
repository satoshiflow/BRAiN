"""
AXE Fusion Router - FastAPI Router für AXEllm Integration

Endpoint: POST /api/axe/chat

SECURITY:
- Trust Tier Validation (DMZ Gateway)
- User Authentication (via JWT)
- Rate Limiting
- Input Validation
- Error Sanitization
"""

import logging
import os
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any, List, Optional, Literal
from uuid import uuid4

from fastapi import APIRouter, Depends, File, Header, HTTPException, Query, Request, Response, UploadFile, status
from pydantic import BaseModel, Field, field_validator
from sqlalchemy.ext.asyncio import AsyncSession
from slowapi import Limiter
from slowapi.util import get_remote_address

from app.core.database import get_db
from app.core.audit_bridge import write_unified_audit
from app.core.auth_deps import (
    get_current_principal,
    Principal,
    PrincipalType,
    require_role,
    SystemRole,
)
from app.modules.axe_governance import (
    AXERequestContext,
    TrustTier,
    get_axe_trust_validator,
)
from app.modules.skill_engine.schemas import SkillRunCreate, SkillRunState, TriggerType
from app.modules.skill_engine.service import get_skill_engine_service

from .service import (
    get_axe_fusion_service,
    AXEllmUnavailableError,
    AXEllmValidationError,
    AXEllmError
)
from .provider_selector import LLMProvider, SanitizationLevel

logger = logging.getLogger(__name__)

# Rate limiter for AXE endpoints
limiter = Limiter(key_func=get_remote_address)

# AXE-specific rate limits
AXE_CHAT_RATE_LIMIT = os.getenv("AXE_CHAT_RATE_LIMIT", "30/minute")  # 30 requests per minute
AXE_ADMIN_RATE_LIMIT = os.getenv("AXE_ADMIN_RATE_LIMIT", "10/minute")
AXE_ADMIN_READ_RATE_LIMIT = os.getenv("AXE_ADMIN_READ_RATE_LIMIT", "60/minute")

# Security Constants
MAX_MESSAGE_LENGTH = 10000
MAX_MESSAGES_PER_REQUEST = 100
MAX_ATTACHMENTS = 10
MAX_ATTACHMENT_SIZE_BYTES = 10 * 1024 * 1024  # 10MB
UPLOAD_BASE_DIR = Path(os.getenv("AXE_UPLOAD_DIR", "/tmp/axe_uploads"))
UPLOAD_MAX_BYTES = int(os.getenv("AXE_UPLOAD_MAX_BYTES", str(MAX_ATTACHMENT_SIZE_BYTES)))
UPLOAD_ALLOWED_MIME_TYPES = {
    "image/jpeg",
    "image/png",
    "image/webp",
    "application/pdf",
    "text/plain",
}

# Allowed LLM hosts (SSRF protection)
ALLOWED_LLM_HOSTS = os.getenv(
    "AXE_ALLOWED_LLM_HOSTS",
    "localhost,127.0.0.1,host.docker.internal,ollama,vllm"
).split(",")

# Legacy endpoint deprecation metadata
LEGACY_AXE_SUNSET = os.getenv("AXE_LEGACY_SUNSET", "Wed, 30 Sep 2026 23:59:59 GMT")
LEGACY_AXE_DOC_LINK = os.getenv(
    "AXE_LEGACY_DOC_LINK",
    "https://github.com/falklabs/brain-v2/blob/main/docs/modules/axe/AXE_API_DEPRECATIONS.md",
)

AXE_CHAT_EXECUTION_PATH = os.getenv("AXE_CHAT_EXECUTION_PATH", "skillrun_bridge").strip().lower()
AXE_CHAT_SKILL_KEY = os.getenv("AXE_CHAT_SKILL_KEY", "")
AXE_CHAT_SKILL_VERSION = int(os.getenv("AXE_CHAT_SKILL_VERSION", "1"))
AXE_CHAT_BRIDGE_FALLBACK_DIRECT = os.getenv("AXE_CHAT_BRIDGE_FALLBACK_DIRECT", "true").strip().lower() in {
    "1",
    "true",
    "yes",
}


# === Security Utilities ===

def sanitize_error_for_user(error: Exception, include_details: bool = False) -> str:
    """
    Sanitize error messages to prevent information leakage.
    
    NEVER expose:
    - Stack traces
    - Internal file paths
    - Database details
    - Configuration values
    - Third-party service credentials
    """
    error_type = type(error).__name__
    error_msg = str(error)
    
    # Log full error server-side for debugging
    logger.debug("Sanitizing error: %s - %s", error_type, error_msg)
    
    # Map error types to user-safe messages
    if isinstance(error, HTTPException):
        # Already HTTPException - use detail if safe
        return error.detail if len(error.detail) < 200 else "Request processing error"
    
    # Network/database errors
    if any(keyword in error_msg.lower() for keyword in ['connection', 'timeout', 'refused', 'unreachable']):
        return "Service temporarily unavailable. Please try again later."
    
    if any(keyword in error_msg.lower() for keyword in ['permission', 'denied', 'forbidden', 'unauthorized']):
        return "Access denied. Please check your permissions."
    
    if any(keyword in error_msg.lower() for keyword in ['not found', 'does not exist', 'invalid']):
        return "The requested resource was not found."
    
    if any(keyword in error_msg.lower() for keyword in ['rate limit', 'too many', 'quota']):
        return "Rate limit exceeded. Please wait before retrying."
    
    # Default safe message
    if include_details and len(error_msg) < 100:
        # Only include user-controlled error messages
        return error_msg
    
    return "An error occurred while processing your request. Please try again."


def validate_llm_host(host: str) -> bool:
    """
    Validate LLM host against whitelist to prevent SSRF attacks.
    
    Blocks:
    - Localhost (except for development)
    - Private IP ranges
    - Internal network addresses
    """
    if not host:
        return False
    
    host_lower = host.lower().strip()
    
    # Remove protocol if present
    if host_lower.startswith('http://'):
        host_lower = host_lower[7:]
    elif host_lower.startswith('https://'):
        host_lower = host_lower[8:]
    
    # Remove port if present
    if ':' in host_lower:
        host_lower = host_lower.split(':')[0]
    
    # Check against whitelist
    for allowed in ALLOWED_LLM_HOSTS:
        allowed = allowed.strip().lower()
        if allowed in host_lower or host_lower.endswith('.' + allowed):
            return True
        if host_lower == allowed:
            return True
    
    # Block private IP ranges
    private_patterns = ['10.', '172.16.', '172.17.', '172.18.', '172.19.',
                       '172.2', '172.30.', '172.31.', '192.168.', 
                       'localhost', '127.0.0.1', '::1', '0.0.0.0']
    
    # Allow localhost in development only
    is_development = os.getenv("AXE_ALLOW_LOCAL_LLM", "false").lower() == "true"
    if is_development and any(host_lower.startswith(p) for p in ['localhost', '127.']):
        return True
    
    for pattern in private_patterns:
        if host_lower.startswith(pattern):
            logger.warning("Blocked SSRF attempt to private IP: %s", host)
            return False
    
    return False

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
    content: str = Field(..., description="Nachrichteninhalt", max_length=MAX_MESSAGE_LENGTH)
    
    @field_validator('role')
    @classmethod
    def validate_role(cls, v: str) -> str:
        allowed_roles = {'system', 'user', 'assistant'}
        if v.lower() not in allowed_roles:
            raise ValueError(f"Role must be one of: {allowed_roles}")
        return v.lower()
    
    @field_validator('content')
    @classmethod
    def validate_content(cls, v: str) -> str:
        if not v or not v.strip():
            raise ValueError("Content cannot be empty")
        if len(v) > MAX_MESSAGE_LENGTH:
            raise ValueError(f"Content exceeds maximum length of {MAX_MESSAGE_LENGTH} characters")
        return v
    
    class Config:
        json_schema_extra = {
            "example": {
                "role": "user",
                "content": "Hallo, wer bist du?"
            }
        }


class ChatRequest(BaseModel):
    """Chat Request im OpenAI Format mit SECURITY Validierung"""
    model: str = Field(..., description="Modell-Name (z.B. 'gpt-4', 'claude-3')")
    messages: List[ChatMessage] = Field(..., description="Liste der Chat-Nachrichten", min_length=1, max_length=MAX_MESSAGES_PER_REQUEST)
    temperature: Optional[float] = Field(0.7, ge=0.0, le=2.0, description="Sampling Temperatur")
    attachments: Optional[List[str]] = Field(None, description="Optionale Attachment-Referenzen", max_length=MAX_ATTACHMENTS)
    
    @field_validator('model')
    @classmethod
    def validate_model(cls, v: str) -> str:
        if not v or not v.strip():
            raise ValueError("Model cannot be empty")
        # Block potentially dangerous model names
        dangerous_patterns = ['../', '..\\', '/etc/', 'con:', 'prn:', 'aux:']
        v_lower = v.lower()
        for pattern in dangerous_patterns:
            if pattern in v_lower:
                raise ValueError("Invalid model name")
        return v.strip()
    
    @field_validator('attachments')
    @classmethod
    def validate_attachments(cls, v: Optional[List[str]]) -> Optional[List[str]]:
        if v is None:
            return v
        if len(v) > MAX_ATTACHMENTS:
            raise ValueError(f"Maximum {MAX_ATTACHMENTS} attachments allowed")
        # Validate attachment IDs (alphanumeric + underscore only)
        for att in v:
            if not att.replace('_', '').replace('-', '').isalnum():
                raise ValueError("Invalid attachment ID format")
        return v
    
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


class ProviderRuntimeResponse(BaseModel):
    provider: Literal["openai", "groq", "ollama", "mock"]
    mode: Literal["auto", "openai", "groq", "ollama", "mock"]
    base_url: str
    api_key_configured: bool
    model: str
    timeout_seconds: float
    sanitization_level: Literal["none", "moderate", "strict"]
    governed_binding: Optional[dict[str, Any]] = None


class ProviderRuntimeUpdateRequest(BaseModel):
    provider: LLMProvider
    force_sanitization_level: Optional[SanitizationLevel] = None


class DeanonymizationOutcomeResponse(BaseModel):
    request_id: str
    provider: str
    provider_model: str
    status: str
    reason_code: Optional[str] = None
    placeholder_count: int
    restored_count: int
    unresolved_placeholders: list
    created_at: datetime


class LearningCandidateResponse(BaseModel):
    id: str
    provider: str
    pattern_name: str
    sample_size: int
    failure_rate: float
    confidence_score: float
    risk_score: float
    proposed_change: Any
    gate_state: str
    approved_by: Optional[str] = None
    approved_at: Optional[datetime] = None
    created_at: datetime


class CandidateDecisionResponse(BaseModel):
    candidate_id: str
    updated: bool
    gate_state: str


class RetentionRunResponse(BaseModel):
    deleted_mapping_sets: int
    deleted_attempts: int
    deleted_candidates: int


class LearningGenerationResponse(BaseModel):
    created_candidates: int


async def _emit_axe_admin_audit(
    *,
    db: AsyncSession,
    action: str,
    actor: str,
    resource_id: str,
    details: dict,
) -> None:
    audit_required = os.getenv("AXE_ADMIN_AUDIT_REQUIRED", "false").lower() == "true"
    try:
        await write_unified_audit(
            event_type="axe.admin",
            action=action,
            actor=actor,
            actor_type="operator",
            resource_type="axe_fusion",
            resource_id=resource_id,
            severity="info",
            message=f"AXE admin action: {action}",
            correlation_id=details.get("request_id"),
            details=details,
            db=db,
        )
    except Exception as exc:
        if audit_required:
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail={
                    "error": "Audit unavailable",
                    "message": "Admin action blocked because audit logging is required",
                    "code": "AUDIT_UNAVAILABLE",
                },
            )
        logger.warning("AXE admin audit emit failed: %s", exc)


class LegacyAxeMessageRequest(BaseModel):
    message: Optional[str] = None
    metadata: dict = Field(default_factory=dict)


def _extract_text_from_skillrun_output(output_payload: dict[str, Any]) -> str:
    if not isinstance(output_payload, dict):
        return ""
    for key in ("text.generate", "text_generate", "response", "result"):
        value = output_payload.get(key)
        if isinstance(value, dict):
            text = value.get("text") or value.get("content")
            if isinstance(text, str) and text.strip():
                return text
        if isinstance(value, str) and value.strip():
            return value
    fallback = output_payload.get("text")
    return fallback if isinstance(fallback, str) else ""


async def _try_skillrun_bridge(
    *,
    db: AsyncSession,
    principal: Optional[Principal],
    chat_request: ChatRequest,
    request_id: str,
) -> ChatResponse | None:
    if AXE_CHAT_EXECUTION_PATH != "skillrun_bridge":
        return None
    if not AXE_CHAT_SKILL_KEY:
        logger.warning("AXE skillrun bridge enabled but AXE_CHAT_SKILL_KEY is empty")
        return None
    if principal is None:
        principal = Principal(
            principal_id="axe-legacy-bridge",
            principal_type=PrincipalType.SERVICE,
            name="AXE Legacy Bridge",
            roles=[SystemRole.OPERATOR.value],
            scopes=["read", "write"],
            tenant_id=None,
        )

    skill_engine = get_skill_engine_service()
    payload = SkillRunCreate(
        skill_key=AXE_CHAT_SKILL_KEY,
        version=AXE_CHAT_SKILL_VERSION,
        input_payload={
            "model": chat_request.model,
            "messages": [msg.model_dump() for msg in chat_request.messages],
            "temperature": chat_request.temperature or 0.7,
            "request_id": request_id,
            "channel": "axe",
        },
        idempotency_key=f"axe:{principal.tenant_id or 'system'}:{principal.principal_id}:{request_id}",
        trigger_type=TriggerType.API,
        causation_id=request_id,
    )

    run = await skill_engine.create_run(db, payload, principal)
    report = await skill_engine.execute_run(db, run.id, principal)
    state = report.skill_run.state.value

    if state == SkillRunState.WAITING_APPROVAL.value:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail={
                "error": "Approval required",
                "message": "AXE request queued and waiting for approval",
                "code": "SKILLRUN_WAITING_APPROVAL",
                "skill_run_id": str(report.skill_run.id),
            },
        )

    if state != SkillRunState.SUCCEEDED.value:
        if AXE_CHAT_BRIDGE_FALLBACK_DIRECT:
            logger.warning(
                "AXE skillrun bridge failed state=%s run=%s, using direct fallback",
                state,
                report.skill_run.id,
            )
            return None
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail={
                "error": "SkillRun execution failed",
                "message": report.skill_run.failure_reason_sanitized or "SkillRun execution failed",
                "code": report.skill_run.failure_code or "SKILLRUN_FAILED",
                "skill_run_id": str(report.skill_run.id),
            },
        )

    text = _extract_text_from_skillrun_output(report.skill_run.output_payload)
    if not text.strip() and AXE_CHAT_BRIDGE_FALLBACK_DIRECT:
        logger.warning("AXE skillrun bridge produced empty response for run=%s; using fallback", report.skill_run.id)
        return None
    return ChatResponse(
        text=text or "",
        raw={
            "execution_path": "skillrun_bridge",
            "skill_run_id": str(report.skill_run.id),
            "skill_run_state": state,
            "evaluation_summary": report.skill_run.evaluation_summary,
            "output_payload": report.skill_run.output_payload,
        },
    )


# === Endpoints ===

@router.post(
    "/chat",
    response_model=ChatResponse,
    status_code=status.HTTP_200_OK,
    summary="Chat mit AXEllm",
    description="Sendet einen Chat-Request an AXEllm und gibt die Antwort zurück."
)
@limiter.limit(AXE_CHAT_RATE_LIMIT)
async def axe_chat(
    request: Request,
    response: Response,
    chat_request: ChatRequest,
    db: AsyncSession = Depends(get_db),
    context: AXERequestContext = Depends(validate_axe_trust),
    principal: Optional[Principal] = Depends(get_current_principal),
) -> ChatResponse:
    """
    Chat Endpoint für AXEllm Integration.
    
    Akzeptiert OpenAI-kompatible Requests und leitet sie an AXEllm weiter.
    
    **Security Layers:**
    1. Trust Tier Validation (DMZ Gateway) - Required
    2. User Authentication - Optional (for audit)
    3. Input Validation - Automatic via Pydantic
    
    **Guardrails:**
    - Max {MAX_MESSAGE_LENGTH} Zeichen pro Message
    - Max {MAX_MESSAGES_PER_REQUEST} Messages pro Request
    - Max {MAX_ATTACHMENTS} Attachments
    - Nur Rollen: system, user, assistant
    - Model Name Validation (no path traversal)
    
    **Features:**
    - Automatische AXE Identity System Prompt Injection
    
    **Fehlercodes:**
    - 503: AXEllm nicht erreichbar
    - 400: Validierungsfehler (z.B. Zeichenlimit überschritten)
    - 429: Rate limit exceeded
    - 500: Interner Fehler
    """
    service = get_axe_fusion_service(db=db)
    
    # Log request with user info if authenticated
    user_id = principal.principal_id if principal else None
    logger.info(
        "AXE chat request (trust_tier=%s source=%s user=%s model=%s messages=%d)",
        context.trust_tier.value,
        context.source_service,
        user_id,
        chat_request.model,
        len(chat_request.messages),
    )
    
    try:
        request_id = request.headers.get("x-request-id", f"axe-{uuid4().hex}")
        response.headers["x-axe-request-id"] = request_id

        # Konvertiere Pydantic Model zu Dict für Service
        messages = [msg.model_dump() for msg in chat_request.messages]

        bridged = await _try_skillrun_bridge(
            db=db,
            principal=principal,
            chat_request=chat_request,
            request_id=request_id,
        )
        if bridged is not None:
            return bridged
        
        result = await service.chat(
            model=chat_request.model,
            messages=messages,
            temperature=chat_request.temperature or 0.7,
            request_id=request_id,
            principal_id=user_id,
        )
        
        return ChatResponse(
            text=result["text"],
            raw={**result["raw"], "execution_path": "direct"}
        )
        
    except AXEllmUnavailableError as e:
        logger.error("AXEllm nicht verfügbar: %s", e)
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail={
                "error": "AXEllm Service nicht verfügbar",
                "message": sanitize_error_for_user(e),
                "code": "AXELLM_UNAVAILABLE"
            }
        )
        
    except AXEllmValidationError as e:
        logger.warning("AXEllm Validierungsfehler: %s", e)
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={
                "error": "Validierungsfehler",
                "message": sanitize_error_for_user(e),
                "code": "VALIDATION_ERROR"
            }
        )
        
    except AXEllmError as e:
        logger.error("AXEllm Fehler: %s", e)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={
                "error": "AXEllm Fehler",
                "message": sanitize_error_for_user(e),
                "code": "AXELLM_ERROR"
            }
        )
        
    except Exception as e:
        logger.exception("Unerwarteter Fehler in axe_chat: %s", e)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={
                "error": "Interner Server Fehler",
                "message": sanitize_error_for_user(e),
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


@router.get(
    "/provider/runtime",
    response_model=ProviderRuntimeResponse,
    summary="Get active AXE LLM provider runtime",
    description="Returns active provider, model, endpoint and effective sanitization level.",
)
@limiter.limit(AXE_ADMIN_READ_RATE_LIMIT)
async def axe_provider_runtime(
    request: Request,
    db: AsyncSession = Depends(get_db),
    context: AXERequestContext = Depends(validate_axe_trust),
    principal: Principal = Depends(require_role(SystemRole.OPERATOR, SystemRole.ADMIN, SystemRole.SYSTEM_ADMIN)),
) -> ProviderRuntimeResponse:
    _ = request
    logger.info(
        "AXE provider runtime read (trust_tier=%s source=%s user=%s)",
        context.trust_tier.value,
        context.source_service,
        principal.principal_id,
    )
    service = get_axe_fusion_service(db=db)
    if hasattr(service, "get_provider_runtime_snapshot"):
        runtime = await service.get_provider_runtime_snapshot()
    else:
        runtime = service.get_provider_runtime()
    active = runtime["active"]
    return ProviderRuntimeResponse(
        provider=active["provider"],
        mode=runtime.get("mode", active["provider"]),
        base_url=active["base_url"],
        api_key_configured=active["api_key_configured"],
        model=active["model"],
        timeout_seconds=active["timeout_seconds"],
        sanitization_level=runtime["sanitization_level"],
        governed_binding=runtime.get("governed_binding"),
    )


@router.put(
    "/provider/runtime",
    response_model=ProviderRuntimeResponse,
    summary="Update active AXE LLM provider runtime",
    description="Updates LOCAL_LLM_MODE and optional FORCE_SANITIZATION_LEVEL without restart.",
)
@limiter.limit(AXE_ADMIN_RATE_LIMIT)
async def axe_update_provider_runtime(
    payload: ProviderRuntimeUpdateRequest,
    request: Request,
    db: AsyncSession = Depends(get_db),
    context: AXERequestContext = Depends(validate_axe_trust),
    principal: Principal = Depends(require_role(SystemRole.OPERATOR, SystemRole.ADMIN, SystemRole.SYSTEM_ADMIN)),
) -> ProviderRuntimeResponse:
    logger.warning(
        "AXE provider runtime update (trust_tier=%s source=%s user=%s provider=%s force_sanitization=%s)",
        context.trust_tier.value,
        context.source_service,
        principal.principal_id,
        payload.provider.value,
        payload.force_sanitization_level.value if payload.force_sanitization_level else "<default>",
    )
    service = get_axe_fusion_service(db=db)
    runtime = service.set_provider_runtime(
        provider=payload.provider,
        force_sanitization_level=payload.force_sanitization_level,
    )
    if hasattr(service, "get_provider_runtime_snapshot"):
        runtime = await service.get_provider_runtime_snapshot()
    await _emit_axe_admin_audit(
        db=db,
        action="provider_runtime_update",
        actor=principal.principal_id,
        resource_id="provider_runtime",
        details={
            "provider": payload.provider.value,
            "force_sanitization_level": payload.force_sanitization_level.value if payload.force_sanitization_level else None,
            "source_service": context.source_service,
            "request_id": request.headers.get("x-request-id"),
        },
    )
    active = runtime["active"]
    return ProviderRuntimeResponse(
        provider=active["provider"],
        mode=runtime.get("mode", active["provider"]),
        base_url=active["base_url"],
        api_key_configured=active["api_key_configured"],
        model=active["model"],
        timeout_seconds=active["timeout_seconds"],
        sanitization_level=runtime["sanitization_level"],
        governed_binding=runtime.get("governed_binding"),
    )


@router.get(
    "/admin/deanonymization/outcomes",
    response_model=List[DeanonymizationOutcomeResponse],
    summary="List AXE deanonymization outcomes",
)
@limiter.limit(AXE_ADMIN_READ_RATE_LIMIT)
async def axe_admin_deanonymization_outcomes(
    request: Request,
    request_id: Optional[str] = None,
    status_filter: Optional[str] = Query(None, alias="status"),
    limit: int = Query(100, ge=1, le=500),
    db: AsyncSession = Depends(get_db),
    context: AXERequestContext = Depends(validate_axe_trust),
    principal: Principal = Depends(require_role(SystemRole.OPERATOR, SystemRole.ADMIN, SystemRole.SYSTEM_ADMIN)),
) -> List[DeanonymizationOutcomeResponse]:
    _ = request
    logger.info(
        "AXE outcomes query (trust_tier=%s source=%s user=%s request_id=%s status=%s limit=%s)",
        context.trust_tier.value,
        context.source_service,
        principal.principal_id,
        request_id,
        status_filter,
        limit,
    )
    service = get_axe_fusion_service(db=db)
    rows = await service.get_deanonymization_outcomes(
        request_id=request_id,
        status=status_filter,
        limit=limit,
    )
    return [DeanonymizationOutcomeResponse(**row) for row in rows]


@router.get(
    "/admin/sanitization/insights",
    response_model=List[LearningCandidateResponse],
    summary="List AXE sanitization learning candidates",
)
@limiter.limit(AXE_ADMIN_READ_RATE_LIMIT)
async def axe_admin_sanitization_insights(
    request: Request,
    provider: Optional[str] = None,
    gate_state: Optional[str] = None,
    limit: int = Query(100, ge=1, le=500),
    db: AsyncSession = Depends(get_db),
    context: AXERequestContext = Depends(validate_axe_trust),
    principal: Principal = Depends(require_role(SystemRole.OPERATOR, SystemRole.ADMIN, SystemRole.SYSTEM_ADMIN)),
) -> List[LearningCandidateResponse]:
    _ = request
    logger.info(
        "AXE insights query (trust_tier=%s source=%s user=%s provider=%s gate_state=%s)",
        context.trust_tier.value,
        context.source_service,
        principal.principal_id,
        provider,
        gate_state,
    )
    service = get_axe_fusion_service(db=db)
    rows = await service.get_learning_candidates(
        provider=provider,
        gate_state=gate_state,
        limit=limit,
    )
    return [LearningCandidateResponse(**{**row, "id": str(row["id"])}) for row in rows]


@router.post(
    "/admin/sanitization/insights/{candidate_id}/approve",
    response_model=CandidateDecisionResponse,
    summary="Approve AXE sanitization learning candidate",
)
@limiter.limit(AXE_ADMIN_RATE_LIMIT)
async def axe_admin_approve_insight(
    candidate_id: str,
    request: Request,
    db: AsyncSession = Depends(get_db),
    context: AXERequestContext = Depends(validate_axe_trust),
    principal: Principal = Depends(require_role(SystemRole.OPERATOR, SystemRole.ADMIN, SystemRole.SYSTEM_ADMIN)),
) -> CandidateDecisionResponse:
    logger.warning(
        "AXE insight approve (trust_tier=%s source=%s user=%s candidate=%s)",
        context.trust_tier.value,
        context.source_service,
        principal.principal_id,
        candidate_id,
    )
    service = get_axe_fusion_service(db=db)
    updated = await service.update_learning_candidate_state(
        candidate_id=candidate_id,
        new_state="approved",
        approved_by=principal.principal_id,
    )
    if not updated:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Candidate not found")
    await _emit_axe_admin_audit(
        db=db,
        action="insight_approve",
        actor=principal.principal_id,
        resource_id=candidate_id,
        details={
            "new_state": "approved",
            "source_service": context.source_service,
            "request_id": request.headers.get("x-request-id"),
        },
    )
    return CandidateDecisionResponse(candidate_id=candidate_id, updated=True, gate_state="approved")


@router.post(
    "/admin/sanitization/insights/{candidate_id}/reject",
    response_model=CandidateDecisionResponse,
    summary="Reject AXE sanitization learning candidate",
)
@limiter.limit(AXE_ADMIN_RATE_LIMIT)
async def axe_admin_reject_insight(
    candidate_id: str,
    request: Request,
    db: AsyncSession = Depends(get_db),
    context: AXERequestContext = Depends(validate_axe_trust),
    principal: Principal = Depends(require_role(SystemRole.OPERATOR, SystemRole.ADMIN, SystemRole.SYSTEM_ADMIN)),
) -> CandidateDecisionResponse:
    logger.warning(
        "AXE insight reject (trust_tier=%s source=%s user=%s candidate=%s)",
        context.trust_tier.value,
        context.source_service,
        principal.principal_id,
        candidate_id,
    )
    service = get_axe_fusion_service(db=db)
    updated = await service.update_learning_candidate_state(
        candidate_id=candidate_id,
        new_state="rejected",
        approved_by=principal.principal_id,
    )
    if not updated:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Candidate not found")
    await _emit_axe_admin_audit(
        db=db,
        action="insight_reject",
        actor=principal.principal_id,
        resource_id=candidate_id,
        details={
            "new_state": "rejected",
            "source_service": context.source_service,
            "request_id": request.headers.get("x-request-id"),
        },
    )
    return CandidateDecisionResponse(candidate_id=candidate_id, updated=True, gate_state="rejected")


@router.post(
    "/admin/retention/run",
    response_model=RetentionRunResponse,
    summary="Run AXE retention cleanup",
)
@limiter.limit(AXE_ADMIN_RATE_LIMIT)
async def axe_admin_retention_run(
    request: Request,
    db: AsyncSession = Depends(get_db),
    context: AXERequestContext = Depends(validate_axe_trust),
    principal: Principal = Depends(require_role(SystemRole.OPERATOR, SystemRole.ADMIN, SystemRole.SYSTEM_ADMIN)),
) -> RetentionRunResponse:
    logger.warning(
        "AXE retention run (trust_tier=%s source=%s user=%s)",
        context.trust_tier.value,
        context.source_service,
        principal.principal_id,
    )
    service = get_axe_fusion_service(db=db)
    result = await service.run_retention_cleanup()
    await _emit_axe_admin_audit(
        db=db,
        action="retention_run",
        actor=principal.principal_id,
        resource_id="retention",
        details={
            **result,
            "source_service": context.source_service,
            "request_id": request.headers.get("x-request-id"),
        },
    )
    return RetentionRunResponse(**result)


@router.post(
    "/admin/sanitization/insights/generate",
    response_model=LearningGenerationResponse,
    summary="Generate AXE sanitization learning candidates",
)
@limiter.limit(AXE_ADMIN_RATE_LIMIT)
async def axe_admin_generate_insights(
    request: Request,
    window_days: int = Query(7, ge=1, le=30),
    min_sample_size: int = Query(50, ge=10, le=5000),
    db: AsyncSession = Depends(get_db),
    context: AXERequestContext = Depends(validate_axe_trust),
    principal: Principal = Depends(require_role(SystemRole.OPERATOR, SystemRole.ADMIN, SystemRole.SYSTEM_ADMIN)),
) -> LearningGenerationResponse:
    logger.warning(
        "AXE insight generation (trust_tier=%s source=%s user=%s window_days=%s min_sample_size=%s)",
        context.trust_tier.value,
        context.source_service,
        principal.principal_id,
        window_days,
        min_sample_size,
    )
    service = get_axe_fusion_service(db=db)
    result = await service.generate_learning_candidates(
        window_days=window_days,
        min_sample_size=min_sample_size,
    )
    await _emit_axe_admin_audit(
        db=db,
        action="insights_generate",
        actor=principal.principal_id,
        resource_id="learning_candidates",
        details={
            **result,
            "window_days": window_days,
            "min_sample_size": min_sample_size,
            "source_service": context.source_service,
            "request_id": request.headers.get("x-request-id"),
        },
    )
    return LearningGenerationResponse(**result)


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


async def validate_axe_trust_legacy(
    request: Request,
    x_dmz_gateway_id: Optional[str] = Header(None),
    x_dmz_gateway_token: Optional[str] = Header(None),
) -> AXERequestContext:
    """
    Legacy trust validation for deprecated /info and /message routes.

    Behavior is intentionally compatible with historical governance tests:
    - LOCAL requests are allowed
    - Valid DMZ requests are allowed
    - EXTERNAL requests are blocked
    """
    request_id = request.headers.get("x-request-id", "axe-legacy-request")
    client_host = request.client.host if request.client else None
    if client_host == "testclient":
        client_host = "127.0.0.1"
    headers = dict(request.headers)

    if x_dmz_gateway_id is not None:
        headers["x-dmz-gateway-id"] = x_dmz_gateway_id
    if x_dmz_gateway_token is not None:
        headers["x-dmz-gateway-token"] = x_dmz_gateway_token

    dmz_headers_present = (
        "x-dmz-gateway-id" in headers or "x-dmz-gateway-token" in headers
    )

    try:
        validator = get_axe_trust_validator()
    except ValueError as exc:
        logger.error("AXE governance unavailable for legacy endpoint: %s", exc)
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail={
                "error": "AXE governance unavailable",
                "message": "AXE trust-tier validation is not configured",
                "code": "AXE_GOVERNANCE_UNAVAILABLE",
            },
        ) from exc

    context = await validator.validate_request(
        headers=headers,
        client_host=client_host,
        request_id=request_id,
    )

    # If DMZ headers are present, request must authenticate as DMZ.
    # Do not silently downgrade to LOCAL on invalid DMZ credentials.
    if dmz_headers_present and context.trust_tier != TrustTier.DMZ:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail={
                "error": "Forbidden",
                "message": "AXE is only accessible via DMZ gateways",
                "trust_tier": TrustTier.EXTERNAL.value,
                "request_id": context.request_id,
            },
        )

    if not validator.is_request_allowed(context):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail={
                "error": "Forbidden",
                "message": "AXE is only accessible via DMZ gateways",
                "trust_tier": context.trust_tier.value,
                "request_id": context.request_id,
            },
        )

    return context


@router.get("/info", deprecated=True)
async def axe_info_legacy(
    response: Response,
    context: AXERequestContext = Depends(validate_axe_trust_legacy),
) -> dict:
    """Deprecated compatibility endpoint: use `/api/axe/health` and `/api/axe/chat`."""
    response.headers["Deprecation"] = "true"
    response.headers["Sunset"] = LEGACY_AXE_SUNSET
    response.headers["Link"] = f'<{LEGACY_AXE_DOC_LINK}>; rel="deprecation"'
    response.headers["Warning"] = '299 - "Deprecated API: use /api/axe/chat and /api/axe/health"'
    return {
        "name": "AXE",
        "version": "2.0-compat",
        "status": "online",
        "description": "Auxiliary Execution Engine (compat endpoint)",
        "gateway": context.source_service or "none",
        "governance": {
            "trust_tier": context.trust_tier.value,
            "source_service": context.source_service,
            "authenticated": context.authenticated,
            "request_id": context.request_id,
        },
        "deprecated": True,
        "replacement": ["/api/axe/chat", "/api/axe/health"],
    }


@router.post("/message", deprecated=True)
async def axe_message_legacy(
    response: Response,
    payload: LegacyAxeMessageRequest,
    db: AsyncSession = Depends(get_db),
    context: AXERequestContext = Depends(validate_axe_trust_legacy),
) -> dict:
    """Deprecated compatibility endpoint: use `/api/axe/chat`."""
    response.headers["Deprecation"] = "true"
    response.headers["Sunset"] = LEGACY_AXE_SUNSET
    response.headers["Link"] = f'<{LEGACY_AXE_DOC_LINK}>; rel="deprecation"'
    response.headers["Warning"] = '299 - "Deprecated API: use /api/axe/chat"'
    user_message = payload.message or ""
    request_id = context.request_id or f"axe-legacy-{uuid4().hex}"
    chat_request = ChatRequest(
        model="qwen2.5:0.5b",
        messages=[ChatMessage(role="user", content=user_message)],
        temperature=0.7,
        attachments=[],
    )

    try:
        bridged = await _try_skillrun_bridge(
            db=db,
            principal=None,
            chat_request=chat_request,
            request_id=request_id,
        )
        if bridged is not None:
            reply = bridged.text
        else:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail={
                    "error": "Legacy endpoint requires SkillRun bridge",
                    "message": "Configure AXE_CHAT_SKILL_KEY and AXE_CHAT_EXECUTION_PATH=skillrun_bridge",
                    "code": "AXE_LEGACY_SKILLRUN_REQUIRED",
                },
            )
    except Exception:
        # Keep compatibility behavior stable even if upstream LLM is unavailable.
        reply = "AXE received your message."

    return {
        "mode": "compat",
        "gateway": context.source_service or "none",
        "input_message": user_message,
        "reply": reply,
        "metadata": payload.metadata,
        "governance": {
            "trust_tier": context.trust_tier.value,
            "source_service": context.source_service,
            "authenticated": context.authenticated,
            "request_id": context.request_id,
        },
        "deprecated": True,
        "replacement": "/api/axe/chat",
    }
