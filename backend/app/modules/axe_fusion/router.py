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
from uuid import UUID, uuid4

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
from app.modules.skill_engine.models import SkillRunModel
from app.modules.skill_engine.schemas import SkillRunCreate, SkillRunState, TriggerType
from app.modules.skill_engine.service import get_skill_engine_service
from app.modules.task_queue.schemas import TaskCreate, TaskPriority
from app.modules.task_queue.service import get_task_queue_service
from app.modules.axe_worker_runs.service import AXEWorkerRunService
from app.modules.axe_worker_runs.schemas import AXEWorkerRunCreateRequest

from .service import (
    get_axe_fusion_service,
    AXEllmUnavailableError,
    AXEllmValidationError,
    AXEllmError
)
from .provider_selector import LLMProvider, SanitizationLevel
from .memory_bridge import get_axe_memory_bridge

# Neural Core Integration (Phase 1)
async def get_neural_context(db: AsyncSession) -> dict:
    """
    Holt Neural Parameter für AXE Chat Requests.
    
    Diese Parameter werden dem Chat als Context hinzugefügt:
    - creativity: Wie kreativ die Antwort sein soll
    - caution: Wie vorsichtig/sicher die Antwort sein soll
    - speed: Bevorzugte Antwortgeschwindigkeit
    - learning_rate: Lernbereitschaft
    """
    try:
        from app.neural.core import get_neural_core
        neural = get_neural_core(db)
        params = await neural.get_all_parameters()
        
        # Filtere nur relevante Parameter
        neural_context = {
            "creativity": params.get("creativity", 0.7),
            "caution": params.get("caution", 0.5),
            "speed": params.get("speed", 0.8),
            "learning_rate": params.get("learning_rate", 0.3),
        }
        
        logger.info(f"🧠 Neural Context geladen: {neural_context}")
        return neural_context
    except Exception as e:
        logger.warning(f"Neural Context nicht verfügbar: {e}")
        try:
            await db.rollback()
        except Exception:
            pass
        return {"creativity": 0.7, "caution": 0.5, "speed": 0.8, "learning_rate": 0.3}


def inject_neural_system_prompt(messages: List[dict], neural_context: dict) -> List[dict]:
    """
    Injiziert Neural Parameter als System Prompt.
    
    Dies beeinflusst das Verhalten von AXELLM basierend auf:
    - creativity: Höher = mehr kreative Antworten
    - caution: Höher = sicherere, validierte Antworten
    - speed: Höher = schnellere Antworten
    """
    system_msg = messages[0] if messages and messages[0].get("role") == "system" else None
    
    neural_instruction = f"""
Du operierst mit folgenden Neural-Parametern:
- Kreativität: {neural_context.get('creativity', 0.7):.0%} (0%=konservativ, 100%=kreativ)
- Vorsicht: {neural_context.get('caution', 0.5):.0%} (0%=risikofreudig, 100%=sicher)
- Geschwindigkeit: {neural_context.get('speed', 0.8):.0%} (0%=langsam, 100%=schnell)
- Lernbereitschaft: {neural_context.get('learning_rate', 0.3):.0%}

Passt eure Antworten entsprechend an!
"""
    
    if system_msg:
        # Append to existing system message
        messages[0]["content"] = system_msg.get("content", "") + "\n\n" + neural_instruction
    else:
        # Prepend new system message
        messages.insert(0, {"role": "system", "content": neural_instruction})
    
    return messages

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
AXE_CHAT_SKILL_KEY = os.getenv("AXE_CHAT_SKILL_KEY", "axe.chat.bridge")
AXE_CHAT_SKILL_VERSION = int(os.getenv("AXE_CHAT_SKILL_VERSION", "1"))
AXE_CHAT_BRIDGE_FALLBACK_DIRECT = os.getenv("AXE_CHAT_BRIDGE_FALLBACK_DIRECT", "false").strip().lower() in {
    "1",
    "true",
    "yes",
}
AXE_CHAT_ALLOW_DIRECT_EXECUTION = os.getenv("AXE_CHAT_ALLOW_DIRECT_EXECUTION", "false").strip().lower() in {
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
        logger.error(f"AXE validation error: {exc}")
        logger.error(f"BRAIN_DMZ_GATEWAY_SECRET in env: {bool(os.environ.get('BRAIN_DMZ_GATEWAY_SECRET'))}")
        logger.error(f"AXE_FUSION_ALLOW_LOCAL_REQUESTS: {os.environ.get('AXE_FUSION_ALLOW_LOCAL_REQUESTS')}")
        logger.error(f"AXE_FUSION_ALLOW_LOCAL_FALLBACK: {os.environ.get('AXE_FUSION_ALLOW_LOCAL_FALLBACK')}")
        allow_local_fallback = (
            os.getenv("AXE_FUSION_ALLOW_LOCAL_FALLBACK", "false").lower() == "true"
        )
        logger.error(f"allow_local_requests={allow_local_requests}, allow_local_fallback={allow_local_fallback}, client_host={client_host}")
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
    stream: Optional[bool] = Field(False, description="Enable Server-Sent Events token streaming")
    session_id: Optional[str] = Field(None, description="Session-ID für Konversationsgedächtnis")
    
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
    run_id: Optional[str] = Field(None, description="Run ID für SSE Event Streaming")
    
    class Config:
        json_schema_extra = {
            "example": {
                "text": "Hallo! Wie kann ich dir helfen?",
                "raw": {
                    "choices": [{"message": {"content": "Hallo! Wie kann ich dir helfen?"}}]
                },
                "run_id": "550e8400-e29b-41d4-a716-446655440000"
            }
        }


class HealthResponse(BaseModel):
    """Health Check Response"""
    status: str
    llm_provider: str
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


async def _emit_run_created(run_id: UUID, skill_key: str) -> None:
    try:
        from app.modules.axe_streams.service import get_axe_stream_service
        stream_service = get_axe_stream_service()
        await stream_service.emit_run_created(run_id, skill_key)
    except Exception as exc:
        logger.warning("Failed to emit RUN_CREATED event: %s", exc)


async def _emit_state_changed(
    run_id: UUID,
    previous_state: Optional[str],
    current_state: str,
    reason: Optional[str] = None,
) -> None:
    try:
        from app.modules.axe_streams.service import get_axe_stream_service
        from app.modules.axe_streams.schemas import AXERunState
        
        stream_service = get_axe_stream_service()
        prev_state = AXERunState(previous_state) if previous_state else None
        await stream_service.emit_state_changed(run_id, prev_state, AXERunState(current_state), reason)
    except Exception as exc:
        logger.warning("Failed to emit state changed event: %s", exc)


async def _emit_run_succeeded(run_id: UUID, output: dict[str, Any]) -> None:
    try:
        from app.modules.axe_streams.service import get_axe_stream_service
        stream_service = get_axe_stream_service()
        await stream_service.emit_run_succeeded(run_id, output)
    except Exception as exc:
        logger.warning("Failed to emit RUN_SUCCEEDED event: %s", exc)


async def _emit_run_failed(run_id: UUID, error_code: str, message: str) -> None:
    try:
        from app.modules.axe_streams.service import get_axe_stream_service
        stream_service = get_axe_stream_service()
        await stream_service.emit_run_failed(run_id, error_code, message)
    except Exception as exc:
        logger.warning("Failed to emit RUN_FAILED event: %s", exc)


async def _emit_token_complete(run_id: UUID, text: str) -> None:
    try:
        from app.modules.axe_streams.service import get_axe_stream_service
        stream_service = get_axe_stream_service()
        await stream_service.emit_token_stream(run_id, text, finish_reason="stop")
    except Exception as exc:
        logger.warning("Failed to emit TOKEN_COMPLETE event: %s", exc)


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
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail={
                "error": "SkillRun bridge misconfigured",
                "message": "AXE_CHAT_SKILL_KEY must be configured for SkillRun bridge mode",
                "code": "SKILLRUN_BRIDGE_MISCONFIGURED",
            },
        )
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
            "prompt": next(
                (
                    message.content
                    for message in reversed(chat_request.messages)
                    if message.role == "user" and message.content.strip()
                ),
                chat_request.messages[-1].content,
            ),
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

    try:
        run = await skill_engine.create_run(db, payload, principal)
        report = await skill_engine.execute_run(db, run.id, principal)
    except Exception as exc:
        if AXE_CHAT_BRIDGE_FALLBACK_DIRECT:
            logger.warning("AXE skillrun bridge unavailable, fallback to direct path: %s", exc)
            return None
        logger.exception("AXE skillrun bridge execution failed")
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail={
                "error": "SkillRun bridge unavailable",
                "message": "SkillRun bridge path failed and fallback is disabled",
                "code": "SKILLRUN_BRIDGE_UNAVAILABLE",
            },
        ) from exc
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
    if not text.strip():
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail={
                "error": "SkillRun output invalid",
                "message": "SkillRun completed without chat text output",
                "code": "SKILLRUN_EMPTY_OUTPUT",
                "skill_run_id": str(report.skill_run.id),
            },
        )
    return ChatResponse(
        text=text or "",
        raw={
            "execution_path": "skillrun_bridge",
            "skill_run_id": str(report.skill_run.id),
            "skill_run_state": state,
            "evaluation_summary": report.skill_run.evaluation_summary,
            "output_payload": report.skill_run.output_payload,
        },
        run_id=str(report.skill_run.id),
    )


WORKER_COMMAND_PATTERN = r"^\s*/(opencode|openclaw)\b"
WorkerCommandType = Literal["opencode", "openclaw"]


async def _try_worker_bridge(
    *,
    db: AsyncSession,
    principal: Optional[Principal],
    chat_request: ChatRequest,
    request_id: str,
) -> ChatResponse | None:
    import re

    last_user_message = next(
        (
            message.content
            for message in reversed(chat_request.messages)
            if message.role == "user" and message.content.strip()
        ),
        None,
    )
    if not last_user_message:
        return None

    match = re.match(WORKER_COMMAND_PATTERN, last_user_message.strip(), re.IGNORECASE)
    if not match:
        return None

    worker_type: WorkerCommandType = match.group(1).lower()  # type: ignore[assignment]
    logger.info("AXE worker bridge triggered: type=%s request_id=%s", worker_type, request_id)

    if principal is None:
        principal = Principal(
            principal_id="axe-worker-bridge",
            principal_type=PrincipalType.SERVICE,
            name="AXE Worker Bridge",
            roles=[SystemRole.OPERATOR.value],
            scopes=["read", "write"],
            tenant_id=None,
        )

    # Extract the prompt from the current message by removing the command prefix
    prompt_text = last_user_message.strip()
    # Remove the /opencode or /openclaw prefix to get just the prompt
    user_prompt = re.sub(WORKER_COMMAND_PATTERN, "", prompt_text, flags=re.IGNORECASE).strip()
    
    # If no prompt after the command, use a default
    if not user_prompt:
        user_prompt = "help"  # Default prompt

    # Create session if it doesn't exist
    from app.modules.axe_sessions.models import AXEChatSessionORM
    from sqlalchemy import select
    
    session_id: UUID = chat_request.session_id or uuid4()  # type: ignore[assignment]
    message_id: UUID = uuid4()
    
    # Check if session exists, if not create it. If the local schema is not aligned,
    # continue in stateless mode so worker dispatch can still proceed.
    try:
        session_query = select(AXEChatSessionORM).where(AXEChatSessionORM.id == session_id)
        existing_session = (await db.execute(session_query)).scalar_one_or_none()

        if existing_session is None:
            new_session = AXEChatSessionORM(
                id=session_id,
                principal_id=principal.principal_id if principal else "anonymous",
                tenant_id=principal.tenant_id if principal else None,
                title=f"{worker_type.title()} worker session",
                status="active",
                message_count=1,
            )
            db.add(new_session)
            await db.commit()

            # Also create the initial message
            from app.modules.axe_sessions.models import AXEChatMessageORM

            new_message = AXEChatMessageORM(
                id=message_id,
                session_id=session_id,
                role="user",
                content=last_user_message,
            )
            db.add(new_message)
            await db.commit()
            logger.info("Created new AXE session and message: %s, %s", session_id, message_id)
    except Exception as exc:
        logger.warning(
            "AXE worker bridge session persistence unavailable; continuing stateless: %s",
            exc,
        )
        try:
            await db.rollback()
        except Exception:
            pass

    if worker_type == "openclaw":
        worker_skill_key = os.getenv("AXE_WORKER_SKILL_KEY", AXE_CHAT_SKILL_KEY)
        skill_payload = SkillRunCreate(
            skill_key=worker_skill_key,
            input_payload={
                "worker_type": worker_type,
                "prompt": user_prompt,
                "mode": "plan",
                "session_id": str(session_id),
                "message_id": str(message_id),
                "request_id": request_id,
            },
            idempotency_key=f"axe-worker-{worker_type}-{session_id}-{message_id}",
            trigger_type=TriggerType.API,
            causation_id=request_id,
            governance_snapshot={
                "source": "axe_worker_bridge",
                "request_id": request_id,
                "worker_type": worker_type,
            },
        )

        try:
            try:
                skill_run = await get_skill_engine_service().create_run(db, skill_payload, principal)
            except ValueError as exc:
                if "No matching definition found" not in str(exc):
                    raise
                logger.warning(
                    "AXE openclaw bridge missing skill definition for %s; creating fallback external SkillRun",
                    worker_skill_key,
                )
                skill_run = await _create_fallback_external_skill_run(
                    db=db,
                    principal=principal,
                    skill_key=worker_skill_key,
                    input_payload=skill_payload.input_payload,
                    request_id=request_id,
                    idempotency_key=skill_payload.idempotency_key,
                    worker_type=worker_type,
                )
            task = await get_task_queue_service().create_task(
                db=db,
                task_data=TaskCreate(
                    name=f"OpenClaw TaskLease {skill_run.id}",
                    description="External OpenClaw worker lease for SkillRun execution",
                    task_type="openclaw_work",
                    category="skill_engine",
                    tags=["tasklease", "skillrun", "openclaw"],
                    priority=TaskPriority.HIGH,
                    payload={
                        "skill_run_id": str(skill_run.id),
                        "skill_key": skill_run.skill_key,
                        "skill_version": skill_run.skill_version,
                        "worker_type": worker_type,
                        "prompt": user_prompt,
                        "mode": "plan",
                        "request_id": request_id,
                    },
                    config={"lease_only": True, "worker_target": "openclaw"},
                    tenant_id=skill_run.tenant_id,
                    mission_id=skill_run.mission_id,
                    skill_run_id=skill_run.id,
                    correlation_id=skill_run.correlation_id,
                    deadline_at=skill_run.deadline_at,
                ),
                created_by=principal.principal_id,
                created_by_type=principal.principal_type.value,
            )
        except Exception as exc:
            logger.exception("AXE openclaw tasklease dispatch failed")
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail={
                    "error": "Worker bridge unavailable",
                    "message": f"Failed to dispatch {worker_type} worker: {exc}",
                    "code": "WORKER_BRIDGE_FAILED",
                },
            ) from exc

        return ChatResponse(
            text=(
                f"[{worker_type.upper()} worker dispatched: {task.task_id}]\n\n"
                f"Status: queued\nTaskLease created for SkillRun {skill_run.id}"
            ),
            raw={
                "execution_path": "worker_bridge_tasklease",
                "worker_type": worker_type,
                "worker_run_id": task.task_id,
                "worker_status": "queued",
                "task_id": task.task_id,
                "skill_run_id": str(skill_run.id),
            },
            run_id=str(skill_run.id),
        )

    worker_service = AXEWorkerRunService(db=db)

    payload = AXEWorkerRunCreateRequest(
        session_id=session_id,
        message_id=message_id,
        prompt=user_prompt,
        mode="plan",
        worker_type=worker_type,
    )

    try:
        worker_response = await worker_service.create_worker_run(
            principal=principal,
            payload=payload,
        )
    except Exception as exc:
        logger.exception("AXE worker bridge failed")
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail={
                "error": "Worker bridge unavailable",
                "message": f"Failed to dispatch {worker_type} worker: {exc}",
                "code": "WORKER_BRIDGE_FAILED",
            },
        ) from exc

    return ChatResponse(
        text=f"[{worker_type.upper()} worker dispatched: {worker_response.worker_run_id}]\n\nStatus: {worker_response.status}\n{worker_response.detail}",
        raw={
            "execution_path": "worker_bridge",
            "worker_type": worker_type,
            "worker_run_id": worker_response.worker_run_id,
            "worker_status": worker_response.status,
        },
        run_id=worker_response.worker_run_id,
    )


async def _create_fallback_external_skill_run(
    *,
    db: AsyncSession,
    principal: Principal,
    skill_key: str,
    input_payload: dict[str, Any],
    request_id: str,
    idempotency_key: str,
    worker_type: str,
) -> SkillRunModel:
    model = SkillRunModel(
        id=uuid4(),
        tenant_id=principal.tenant_id,
        skill_key=skill_key,
        skill_version=1,
        state=SkillRunState.QUEUED.value,
        input_payload=input_payload,
        plan_snapshot={
            "external_worker": worker_type,
            "mode": "fallback_skill_definition_missing",
            "request_id": request_id,
        },
        provider_selection_snapshot={"bindings": []},
        requested_by=principal.principal_id,
        requested_by_type=principal.principal_type.value,
        trigger_type=TriggerType.API.value,
        policy_decision={"allowed": True, "effect": "audit", "reason": "fallback_external_worker"},
        policy_snapshot={"fallback": "missing_skill_definition", "request_id": request_id},
        risk_tier="medium",
        correlation_id=f"fallback-{uuid4().hex}",
        causation_id=request_id,
        idempotency_key=idempotency_key,
        mission_id=None,
        deadline_at=None,
        cost_estimate=0.0,
        state_changed_at=datetime.now(timezone.utc),
    )
    db.add(model)
    await db.commit()
    await db.refresh(model)
    return model


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

        # Phase 1: Neural Core Integration - Parameter holen und injizieren
        neural_context = await get_neural_context(db)
        messages = inject_neural_system_prompt(messages, neural_context)
        logger.info(f"🧠 Neural Context injected: creativity={neural_context['creativity']}, caution={neural_context['caution']}")

        # Phase 1.5: Odoo Bridge - Check for Odoo commands
        last_user_message = next(
            (msg.content for msg in reversed(chat_request.messages) 
             if msg.role == "user" and msg.content.strip()),
            ""
        )
        
        # Import Odoo bridge lazily to avoid startup issues
        try:
            from app.modules.odoo_adapter.chat_bridge import get_odoo_chat_bridge
            odoo_bridge = get_odoo_chat_bridge()
            
            if odoo_bridge.is_odoo_command(last_user_message):
                logger.info(f"🎯 Odoo command detected: {last_user_message[:50]}...")
                odoo_response = await odoo_bridge.handle_message(last_user_message)
                
                if odoo_response:
                    logger.info(f"✅ Odoo command executed successfully")
                    return ChatResponse(
                        id=f"odoo-{uuid4().hex[:8]}",
                        created=int(datetime.now(timezone.utc).timestamp()),
                        model=chat_request.model,
                        choices=[{"index": 0, "message": {"role": "assistant", "content": odoo_response}, "finish_reason": "stop"}],
                        usage={"prompt_tokens": 0, "completion_tokens": len(odoo_response), "total_tokens": len(odoo_response)}
                    )
        except Exception as odoo_error:
            logger.warning(f"⚠️ Odoo bridge error (continuing with LLM): {odoo_error}")

        worker_bridged = await _try_worker_bridge(
            db=db,
            principal=principal,
            chat_request=chat_request,
            request_id=request_id,
        )
        if worker_bridged is not None:
            logger.info("AXE worker bridge handled request_id=%s", request_id)
            return worker_bridged

        bridged = await _try_skillrun_bridge(
            db=db,
            principal=principal,
            chat_request=chat_request,
            request_id=request_id,
        )
        if bridged is not None:
            # Store messages in memory if session_id provided
            if chat_request.session_id:
                memory_bridge = get_axe_memory_bridge(db)
                tenant_id = principal.tenant_id if principal else None
                for msg in chat_request.messages:
                    await memory_bridge.store_message(
                        session_id=chat_request.session_id,
                        role=msg.role,
                        content=msg.content,
                        tenant_id=tenant_id
                    )
                await memory_bridge.store_message(
                    session_id=chat_request.session_id,
                    role="assistant",
                    content=bridged.text,
                    tenant_id=tenant_id
                )
            return bridged

        if AXE_CHAT_EXECUTION_PATH == "skillrun_bridge":
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail={
                    "error": "SkillRun bridge unavailable",
                    "message": "AXE runtime is configured for SkillRun-only execution",
                    "code": "SKILLRUN_BRIDGE_REQUIRED",
                },
            )

        if not AXE_CHAT_ALLOW_DIRECT_EXECUTION:
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail={
                    "error": "Direct execution disabled",
                    "message": "Enable AXE_CHAT_ALLOW_DIRECT_EXECUTION for direct runtime mode",
                    "code": "AXE_DIRECT_DISABLED",
                },
            )
        
        run_id = uuid4()
        tenant_id = principal.tenant_id if principal else None
        
        try:
            from app.core.redis_client import get_redis
            redis_client = await get_redis()
            ownership_key = f"axe:stream:ownership:{run_id}"
            if tenant_id:
                await redis_client.setex(ownership_key, 3600, str(tenant_id))
            else:
                await redis_client.setex(ownership_key, 3600, "system")
        except Exception as exc:
            logger.warning("Failed to store run ownership in Redis: %s", exc)
        
        await _emit_run_created(run_id, "axe.chat.direct")
        await _emit_state_changed(run_id, None, "running", "Starting direct AXE chat execution")
        
        try:
            if chat_request.stream:
                result = await service.stream_chat(
                    model=chat_request.model,
                    messages=messages,
                    temperature=chat_request.temperature or 0.7,
                    request_id=request_id,
                    principal_id=user_id,
                    run_id=str(run_id),
                )
                await _emit_run_succeeded(run_id, {"text": result["text"]})
                
                # Store messages in memory if session_id provided
                if chat_request.session_id:
                    memory_bridge = get_axe_memory_bridge(db)
                    for msg in chat_request.messages:
                        await memory_bridge.store_message(
                            session_id=chat_request.session_id,
                            role=msg.role,
                            content=msg.content,
                            tenant_id=tenant_id
                        )
                
                return ChatResponse(
                    text=result["text"],
                    raw={**result["raw"], "execution_path": "direct", "streamed": True},
                    run_id=str(run_id)
                )
            else:
                result = await service.chat(
                    model=chat_request.model,
                    messages=messages,
                    temperature=chat_request.temperature or 0.7,
                    request_id=request_id,
                    principal_id=user_id,
                )
                
                await _emit_run_succeeded(run_id, {"text": result["text"]})
                await _emit_token_complete(run_id, result["text"])
                
                # Store messages in memory if session_id provided
                if chat_request.session_id:
                    memory_bridge = get_axe_memory_bridge(db)
                    for msg in chat_request.messages:
                        await memory_bridge.store_message(
                            session_id=chat_request.session_id,
                            role=msg.role,
                            content=msg.content,
                            tenant_id=tenant_id
                        )
                    await memory_bridge.store_message(
                        session_id=chat_request.session_id,
                        role="assistant",
                        content=result["text"],
                        tenant_id=tenant_id
                    )
                
                return ChatResponse(
                    text=result["text"],
                    raw={**result["raw"], "execution_path": "direct"},
                    run_id=str(run_id)
                )
            
        except Exception as exc:
            error_message = sanitize_error_for_user(exc)
            error_code = "AXE_CHAT_FAILED"
            
            await _emit_state_changed(run_id, "running", "failed", error_message)
            await _emit_run_failed(run_id, error_code, error_message)
            
            raise
        
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

    except HTTPException:
        raise
        
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
    summary="LLM Provider Health Check",
    description="Prüft ob der LLM Provider erreichbar ist."
)
async def axe_health(
    context: AXERequestContext = Depends(validate_axe_trust),
) -> HealthResponse:
    """
    Health Check für LLM Provider Verbindung.
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
        llm_provider=result.get("llm_provider", "unknown"),
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
        stream=False,
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
    except HTTPException:
        raise
    except Exception as exc:
        logger.exception("Legacy AXE message bridge failed: %s", exc)
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail={
                "error": "SkillRun bridge unavailable",
                "message": "Legacy AXE endpoint requires a healthy SkillRun bridge",
                "code": "AXE_LEGACY_SKILLRUN_UNAVAILABLE",
            },
        ) from exc

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
