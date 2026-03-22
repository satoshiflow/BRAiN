"""
AXE Fusion Service - Client für AXEllm Integration

Bietet HTTP-Client zu AXEllm mit Timeout, Error Handling und Response Mapping.
"""

import logging
import os
from typing import Any, Dict, List, Optional, Tuple
import httpx

from .data_sanitizer import DataSanitizer
from .mapping_repository import AXEMappingRepository
from .provider_selector import (
    LLMProvider,
    ProviderConfig,
    ProviderSelector,
    SanitizationLevel,
)
from app.modules.provider_bindings.service import get_provider_binding_service

logger = logging.getLogger(__name__)

AXELLM_TIMEOUT = 60.0  # 60 Sekunden Timeout
MAX_CHARS = 20000  # Max Zeichen Limit für Guardrails

# Erlaubte Rollen für Guardrails
ALLOWED_ROLES = {"system", "user", "assistant"}


class AXEllmError(Exception):
    """Base Exception für AXEllm Fehler"""
    pass


class AXEllmUnavailableError(AXEllmError):
    """AXEllm ist nicht erreichbar (503)"""
    pass


class AXEllmValidationError(AXEllmError):
    """Validierungsfehler im Request"""
    pass


# Security Constants for Image Validation
MAX_IMAGE_SIZE_BYTES = 5 * 1024 * 1024  # 5MB max per image
MAX_IMAGES_PER_REQUEST = 5
ALLOWED_IMAGE_MAGIC_BYTES = {
    b'\xff\xd8\xff': 'jpeg',  # JPEG
    b'\x89PNG\r\n\x1a\n': 'png',  # PNG
    b'GIF87a': 'gif',  # GIF87a
    b'GIF89a': 'gif',  # GIF89a
    b'RIFF': 'webp',  # WebP (starts with RIFF)
    b'BM': 'bmp',  # BMP
}


def _validate_base64_image(content: str) -> bool:
    """
    Validate base64 encoded image to prevent attacks.
    
    Checks:
    - Valid base64 encoding
    - Magic bytes match known image formats
    - Reasonable size estimate
    
    Returns True if valid image.
    """
    if not content:
        return False
    
    try:
        # Check length first (rough estimate)
        if len(content) > MAX_IMAGE_SIZE_BYTES * 2:  # Base64 is ~33% larger
            logger.warning("Image base64 too large: %d bytes", len(content))
            return False
        
        # Decode base64
        import base64
        binary = base64.b64decode(content, validate=True)
        
        # Check magic bytes
        if len(binary) < 12:
            logger.warning("Image too small: %d bytes", len(binary))
            return False
        
        # Check magic bytes
        header = binary[:12]
        is_valid = False
        for magic, fmt in ALLOWED_IMAGE_MAGIC_BYTES.items():
            if header.startswith(magic):
                is_valid = True
                break
        
        if not is_valid:
            logger.warning("Invalid image magic bytes: %s", header[:8].hex())
            return False
        
        # Check size
        if len(binary) > MAX_IMAGE_SIZE_BYTES:
            logger.warning("Image too large after decode: %d bytes", len(binary))
            return False
        
        return True
        
    except Exception as e:
        logger.warning("Image validation failed: %s", e)
        return False


def _sanitize_messages(messages: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """
    Guardrails: Bereinigt Nachrichten
    - Entfernt tool/function_call Felder
    - Filtert nur erlaubte Rollen
    - Prüft Zeichenlimit
    - Validiert Base64-Bildinhalte
    """
    sanitized = []
    total_chars = 0
    image_count = 0
    
    for msg in messages:
        # Nur erlaubte Rollen
        role = msg.get("role", "user")
        if role not in ALLOWED_ROLES:
            logger.warning(f"Ungültige Rolle '{role}' entfernt, verwende 'user'")
            role = "user"
        
        # Inhalt extrahieren
        content = msg.get("content", "")
        if content is None:
            content = ""
        
        # Check for base64 image content markers
        if "[image:" in content.lower() or "data:image/" in content.lower():
            image_count += 1
            # Note: Full base64 validation would require access to the actual image data
            # which is handled separately in multipart uploads
        
        # Tool/Function Felder entfernen
        cleaned_msg = {
            "role": role,
            "content": content
        }
        
        # Zeichen zählen
        total_chars += len(str(content))
        
        sanitized.append(cleaned_msg)
    
    # Zeichenlimit prüfen
    if total_chars > MAX_CHARS:
        raise AXEllmValidationError(
            f"Request too large: {total_chars} chars (limit: {MAX_CHARS})"
        )
    
    # Image count limit
    if image_count > MAX_IMAGES_PER_REQUEST:
        raise AXEllmValidationError(
            f"Too many images: {image_count} (limit: {MAX_IMAGES_PER_REQUEST})"
        )
    
    return sanitized


class AXEllmClient:
    """HTTP Client für AXEllm API"""
    
    def __init__(
        self,
        base_url: str,
        api_key: str = "",
        timeout: float = AXELLM_TIMEOUT,
    ):
        self.base_url = base_url.rstrip("/")
        self.api_key = api_key
        self.timeout = timeout
        self.client = httpx.AsyncClient(timeout=self.timeout)

    def _chat_completion_url(self) -> str:
        if self.base_url.endswith("/chat/completions"):
            return self.base_url
        if self.base_url.endswith("/v1"):
            return f"{self.base_url}/chat/completions"
        return f"{self.base_url}/v1/chat/completions"
    
    async def chat(
        self,
        model: str,
        messages: List[Dict[str, Any]],
        temperature: float = 0.7
    ) -> Dict[str, Any]:
        """
        Sendet Chat-Request an AXEllm
        
        Args:
            model: Modell-Name
            messages: Liste von Nachrichten (OpenAI Format)
            temperature: Sampling Temperatur
            
        Returns:
            Dict mit 'text' und 'raw' Feldern
            
        Raises:
            AXEllmUnavailableError: Wenn AXEllm nicht erreichbar (503)
            AXEllmValidationError: Bei Validierungsfehlern
            AXEllmError: Bei anderen Fehlern
        """
        # Guardrails anwenden
        try:
            sanitized_messages = _sanitize_messages(messages)
        except AXEllmValidationError:
            raise
        
        # Request Payload im OpenAI Format
        payload = {
            "model": model,
            "messages": sanitized_messages,
            "temperature": temperature
        }
        
        # Headers mit API Key falls vorhanden
        headers = {"Content-Type": "application/json"}
        if self.api_key:
            headers["Authorization"] = f"Bearer {self.api_key}"
        
        try:
            response = await self.client.post(
                self._chat_completion_url(),
                json=payload,
                headers=headers
            )
            response.raise_for_status()
            
        except httpx.TimeoutException as e:
            logger.error(f"AXEllm Timeout nach {self.timeout}s: {e}")
            raise AXEllmUnavailableError(
                f"AXEllm Timeout: Keine Antwort innerhalb von {self.timeout} Sekunden"
            )
            
        except httpx.ConnectError as e:
            logger.error(f"AXEllm nicht erreichbar: {e}")
            raise AXEllmUnavailableError(
                f"AXEllm Service nicht erreichbar unter {self.base_url}"
            )
            
        except httpx.HTTPStatusError as e:
            if e.response.status_code == 503:
                logger.error("AXEllm Service unavailable (503)")
                raise AXEllmUnavailableError("AXEllm Service temporär nicht verfügbar (503)")
            else:
                logger.error(f"AXEllm HTTP Fehler: {e.response.status_code}")
                raise AXEllmError(f"AXEllm HTTP Fehler: {e.response.status_code}")
        
        # Response parsen
        try:
            raw_response = response.json()
        except Exception as e:
            logger.error(f"Fehler beim Parsen der AXEllm Response: {e}")
            raise AXEllmError(f"Ungültige Response von AXEllm: {e}")
        
        # Response mapping zu {text, raw}
        # AXEllm gibt OpenAI-kompatibles Format zurück
        text = ""
        if "choices" in raw_response and len(raw_response["choices"]) > 0:
            choice = raw_response["choices"][0]
            if "message" in choice:
                text = choice["message"].get("content", "")
            elif "text" in choice:
                text = choice["text"]
        
        return {
            "text": text,
            "raw": raw_response
        }
    
    async def close(self):
        """Schließt den HTTP Client"""
        await self.client.aclose()


class AXEFusionService:
    """High-Level Service für AXE Fusion"""
    
    def __init__(self, db=None):
        self.db = db
        self.selector = ProviderSelector()
        self.sanitizer = DataSanitizer()
        self.provider_binding_service = get_provider_binding_service()
        self.mapping_repo = AXEMappingRepository()
        self._clients: Dict[Tuple[str, str, str], AXEllmClient] = {}

    def _get_or_create_client(self, config: ProviderConfig) -> AXEllmClient:
        key = (config.provider.value, config.base_url, config.api_key)
        if key not in self._clients:
            self._clients[key] = AXEllmClient(
                base_url=config.base_url,
                api_key=config.api_key,
                timeout=config.timeout_seconds,
            )
        return self._clients[key]

    def _resolve_model(self, model: str, config: ProviderConfig) -> str:
        if model and model.strip():
            return model
        return config.model

    def get_provider_runtime(self) -> Dict[str, Any]:
        config = self.selector.get_active_config()
        active_provider = self.selector.get_active_provider()
        level = self.selector.get_sanitization_level(config.provider)
        return {
            "active": config.to_dict(),
            "mode": active_provider.value,
            "sanitization_level": level.value,
        }

    async def get_provider_runtime_snapshot(self) -> Dict[str, Any]:
        runtime = self.get_provider_runtime()
        if not self.db:
            return runtime
        capability_key = os.getenv("AXE_PROVIDER_CAPABILITY_KEY", "text.generate")
        capability_version = int(os.getenv("AXE_PROVIDER_CAPABILITY_VERSION", "1"))
        try:
            binding = await self.provider_binding_service.find_binding_by_provider(
                self.db,
                capability_key=capability_key,
                capability_version=capability_version,
                provider_key=runtime["active"]["provider"],
                tenant_id=None,
            )
        except Exception as exc:
            logger.warning("Provider binding lookup unavailable for AXE runtime snapshot: %s", exc)
            return runtime
        if binding is None:
            return runtime
        runtime["governed_binding"] = {
            "provider_binding_id": str(binding.id),
            "capability_key": binding.capability_key,
            "capability_version": binding.capability_version,
            "provider_key": binding.provider_key,
            "status": binding.status,
            "adapter_key": binding.adapter_key,
        }
        configured = ProviderConfig(
            provider=LLMProvider(runtime["active"]["provider"]),
            base_url=runtime["active"]["base_url"],
            api_key=os.getenv(f"{runtime['active']['provider'].upper()}_API_KEY", ""),
            model=runtime["active"]["model"],
            timeout_seconds=runtime["active"]["timeout_seconds"],
        )
        provider_ok = await self._probe_provider(configured, require_chat=False)
        try:
            await self.provider_binding_service.update_health_projection(
                binding_id=str(binding.id),
                health_status="healthy" if provider_ok else "degraded",
                circuit_state="closed" if provider_ok else "open",
                ttl_seconds=int(os.getenv("PROVIDER_BINDING_HEALTH_TTL", "300")),
            )
            health = await self.provider_binding_service.get_health_projection(str(binding.id))
        except Exception as exc:
            logger.warning("Provider binding health projection unavailable: %s", exc)
            health = None
        if health:
            runtime["governed_binding"]["health"] = health
        return runtime

    def set_provider_runtime(
        self,
        provider: LLMProvider,
        force_sanitization_level: Optional[SanitizationLevel],
    ) -> Dict[str, Any]:
        self.selector.set_runtime_mode(provider)
        self.selector.set_force_sanitization_level(force_sanitization_level)
        return self.get_provider_runtime()

    async def get_deanonymization_outcomes(
        self,
        *,
        request_id: Optional[str] = None,
        status: Optional[str] = None,
        limit: int = 100,
    ) -> List[Dict[str, Any]]:
        if not self.db:
            return []
        return await self.mapping_repo.list_deanonymization_outcomes(
            self.db,
            request_id=request_id,
            status=status,
            limit=limit,
        )

    async def get_learning_candidates(
        self,
        *,
        provider: Optional[str] = None,
        gate_state: Optional[str] = None,
        limit: int = 100,
    ) -> List[Dict[str, Any]]:
        if not self.db:
            return []
        return await self.mapping_repo.list_learning_candidates(
            self.db,
            provider=provider,
            gate_state=gate_state,
            limit=limit,
        )

    async def update_learning_candidate_state(
        self,
        *,
        candidate_id: str,
        new_state: str,
        approved_by: Optional[str],
    ) -> bool:
        if not self.db:
            return False
        updated = await self.mapping_repo.set_learning_candidate_state(
            self.db,
            candidate_id=candidate_id,
            new_state=new_state,
            approved_by=approved_by,
        )
        await self.db.commit()
        return updated

    async def run_retention_cleanup(self) -> Dict[str, int]:
        if not self.db:
            return {
                "deleted_mapping_sets": 0,
                "deleted_attempts": 0,
                "deleted_candidates": 0,
            }
        result = await self.mapping_repo.run_retention_cleanup(self.db)
        await self.db.commit()
        return result

    async def generate_learning_candidates(
        self,
        *,
        window_days: int = 7,
        min_sample_size: int = 50,
    ) -> Dict[str, int]:
        if not self.db:
            return {"created_candidates": 0}
        created = await self.mapping_repo.generate_learning_candidates(
            self.db,
            window_days=window_days,
            min_sample_size=min_sample_size,
        )
        await self.db.commit()
        return {"created_candidates": created}
    
    async def chat(
        self,
        model: str,
        messages: List[Dict[str, Any]],
        temperature: float = 0.7,
        inject_identity: bool = True,
        request_id: Optional[str] = None,
        principal_id: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Haupt-Chat Methode
        
        Args:
            model: Modell-Name
            messages: Liste von Nachrichten
            temperature: Sampling Temperatur
            inject_identity: Ob System Prompt aus AXE Identity injiziert werden soll
            
        Returns:
            {text: str, raw: object}
        """
        # Inject AXE Identity system prompt
        if inject_identity and self.db:
            from .middleware import SystemPromptMiddleware
            middleware = SystemPromptMiddleware(self.db)
            messages = await middleware.inject_system_prompt(messages)

        provider_config = await self._resolve_runtime_config(require_chat=True)
        client = self._get_or_create_client(provider_config)
        effective_model = self._resolve_model(model, provider_config)

        sanitization_level = self.selector.get_sanitization_level(provider_config.provider)
        if sanitization_level != SanitizationLevel.NONE:
            outbound_messages, mapping = self.sanitizer.sanitize_messages(messages, sanitization_level)
        else:
            outbound_messages, mapping = messages, None

        mapping_set_id: Optional[str] = None
        if self.db and mapping and mapping.replacements and request_id:
            try:
                async with self.db.begin_nested():
                    message_fingerprint = self.mapping_repo.fingerprint_messages(outbound_messages)
                    mapping_set_id = await self.mapping_repo.record_mapping_set(
                        self.db,
                        request_id=request_id,
                        provider=provider_config.provider.value,
                        provider_model=effective_model,
                        sanitization_level=sanitization_level.value,
                        message_fingerprint=message_fingerprint,
                        mapping_count=len(mapping.replacements),
                        principal_id=principal_id,
                    )
                    entries = self.mapping_repo.mapping_entries_from_replacements(mapping.replacements)
                    await self.mapping_repo.record_mapping_entries(
                        self.db,
                        mapping_set_id=mapping_set_id,
                        entries=entries,
                    )
                await self.db.commit()
            except Exception as exc:
                logger.warning("Failed persisting AXE mapping metadata: %s", exc)
                await self.db.rollback()

        try:
            result = await client.chat(effective_model, outbound_messages, temperature)
        except Exception:
            if self.db and mapping_set_id and request_id:
                try:
                    attempt_no = await self.mapping_repo.get_next_attempt_no(
                        self.db,
                        request_id=request_id,
                        mapping_set_id=mapping_set_id,
                    )
                    await self.mapping_repo.record_deanonymization_attempt(
                        self.db,
                        request_id=request_id,
                        mapping_set_id=mapping_set_id,
                        attempt_no=attempt_no,
                        status="failed",
                        reason_code="UPSTREAM_CALL_FAILED",
                        placeholder_count=len(mapping.replacements) if mapping else 0,
                        restored_count=0,
                        unresolved_placeholders=list(mapping.replacements.keys()) if mapping else [],
                        response_fingerprint=self.mapping_repo.fingerprint_text(""),
                    )
                    await self.db.commit()
                except Exception as exc:
                    logger.warning("Failed persisting AXE failure telemetry: %s", exc)
                    await self.db.rollback()
            raise

        restored_count = 0
        unresolved_placeholders: List[str] = []
        if mapping and result.get("text"):
            raw_text = result["text"]
            restored_count = sum(1 for p in mapping.replacements if p in raw_text)
            result["text"] = self.sanitizer.deanonymize_text(result["text"], mapping)
            try:
                choices = result["raw"].get("choices", [])
                if choices and "message" in choices[0]:
                    original_content = choices[0]["message"].get("content", "")
                    choices[0]["message"]["content"] = self.sanitizer.deanonymize_text(
                        original_content,
                        mapping,
                    )
            except Exception:
                logger.debug("Skipping raw response deanonymization")

        if self.db and mapping_set_id and request_id:
            try:
                attempt_no = await self.mapping_repo.get_next_attempt_no(
                    self.db,
                    request_id=request_id,
                    mapping_set_id=mapping_set_id,
                )
                response_text = result.get("text") or ""
                for placeholder in (mapping.replacements.keys() if mapping else []):
                    if placeholder in response_text:
                        unresolved_placeholders.append(placeholder)
                status = "success" if not unresolved_placeholders else "partial"
                await self.mapping_repo.record_deanonymization_attempt(
                    self.db,
                    request_id=request_id,
                    mapping_set_id=mapping_set_id,
                    attempt_no=attempt_no,
                    status=status,
                    reason_code=None if status == "success" else "PLACEHOLDER_UNRESOLVED",
                    placeholder_count=len(mapping.replacements) if mapping else 0,
                    restored_count=restored_count,
                    unresolved_placeholders=unresolved_placeholders,
                    response_fingerprint=self.mapping_repo.fingerprint_text(result.get("text", "")),
                )
                await self.db.commit()
            except Exception as exc:
                logger.warning("Failed persisting AXE deanonymization telemetry: %s", exc)
                await self.db.rollback()

        return result
    
    async def health_check(self) -> Dict[str, Any]:
        """
        Prüft ob AXEllm erreichbar ist
        
        Returns:
            Dict mit Status
        """
        try:
            provider_config = await self._resolve_runtime_config(require_chat=False)
            return {
                "status": "healthy",
                "axellm": "reachable",
                "provider": provider_config.provider.value,
            }
        except AXEllmUnavailableError as e:
            logger.warning(f"AXEllm Health Check degraded: {e}")
            return {"status": "degraded", "axellm": "not_reachable", "error": str(e)}
        except Exception as e:
            logger.warning(f"AXEllm Health Check fehlgeschlagen: {e}")
            return {"status": "unavailable", "axellm": "not_reachable", "error": str(e)}

    async def _resolve_runtime_config(self, *, require_chat: bool) -> ProviderConfig:
        provider = self.selector.get_active_provider()
        enforce_bindings = os.getenv("AXE_ENFORCE_PROVIDER_BINDINGS", "false").strip().lower() in {
            "1",
            "true",
            "yes",
        }

        if provider == LLMProvider.AUTO:
            allow_mock = os.getenv("AXE_ALLOW_MOCK_FALLBACK", "false").strip().lower() in {
                "1",
                "true",
                "yes",
            }
            for candidate in self.selector.get_auto_candidates():
                if await self._probe_provider(candidate, require_chat=require_chat):
                    if enforce_bindings and self.db:
                        binding = await self.provider_binding_service.find_binding_by_provider(
                            self.db,
                            capability_key=os.getenv("AXE_PROVIDER_CAPABILITY_KEY", "text.generate"),
                            capability_version=int(os.getenv("AXE_PROVIDER_CAPABILITY_VERSION", "1")),
                            provider_key=candidate.provider.value,
                            tenant_id=None,
                        )
                        if binding is None:
                            continue
                    return candidate
            if allow_mock:
                logger.warning("AXE runtime auto resolution fell back to mock provider")
                return ProviderConfig(
                    provider=LLMProvider.MOCK,
                    base_url=os.getenv("MOCK_BASE_URL", "http://localhost:8081"),
                    api_key=os.getenv("MOCK_API_KEY", ""),
                    model=os.getenv("MOCK_MODEL", "mock-local"),
                    timeout_seconds=float(os.getenv("AXELLM_TIMEOUT_SECONDS", "60")),
                )
            raise AXEllmUnavailableError("No real LLM provider is reachable in auto mode")

        config = self.selector.get_active_config()
        if provider == LLMProvider.MOCK and not os.getenv("AXE_ALLOW_MOCK_FALLBACK", "").strip():
            raise AXEllmUnavailableError("Mock provider is disabled for this environment")

        if provider != LLMProvider.MOCK and not await self._probe_provider(config, require_chat=require_chat):
            raise AXEllmUnavailableError(
                f"Configured provider '{provider.value}' is not reachable"
            )
        if enforce_bindings and self.db and provider != LLMProvider.MOCK:
            binding = await self.provider_binding_service.find_binding_by_provider(
                self.db,
                capability_key=os.getenv("AXE_PROVIDER_CAPABILITY_KEY", "text.generate"),
                capability_version=int(os.getenv("AXE_PROVIDER_CAPABILITY_VERSION", "1")),
                provider_key=provider.value,
                tenant_id=None,
            )
            if binding is None:
                raise AXEllmUnavailableError(
                    f"Configured provider '{provider.value}' has no enabled governed ProviderBinding"
                )
        return config

    async def _probe_provider(self, config: ProviderConfig, *, require_chat: bool) -> bool:
        if config.provider == LLMProvider.MOCK:
            return False

        if config.provider == LLMProvider.OPENAI and not config.api_key:
            return False
        if config.provider == LLMProvider.GROQ and not config.api_key:
            return False

        client = self._get_or_create_client(config)
        health_url, headers = self._build_health_request(config)
        try:
            response = await client.client.get(health_url, headers=headers, timeout=5.0)
            if response.status_code != 200:
                return False
        except Exception:
            return False

        if not require_chat:
            return True

        if config.provider != LLMProvider.OLLAMA:
            return True

        model_url = f"{self._normalize_ollama_base(config.base_url)}/api/tags"
        try:
            response = await client.client.get(model_url, timeout=5.0)
            if response.status_code != 200:
                return False
            payload = response.json()
            models = payload.get("models", []) if isinstance(payload, dict) else []
            model_names = {
                model.get("name")
                for model in models
                if isinstance(model, dict) and model.get("name")
            }
            return config.model in model_names
        except Exception:
            return False

    def _build_health_request(self, config: ProviderConfig) -> tuple[str, dict[str, str]]:
        headers: dict[str, str] = {}

        if config.provider == LLMProvider.OLLAMA:
            return f"{self._normalize_ollama_base(config.base_url)}/api/tags", headers

        if config.provider in {LLMProvider.GROQ, LLMProvider.OPENAI}:
            if not config.api_key:
                raise AXEllmUnavailableError(f"{config.provider.value} API key is not configured")
            headers["Authorization"] = f"Bearer {config.api_key}"
            base_url = config.base_url.rstrip("/")
            if not base_url.endswith("/v1"):
                base_url = f"{base_url}/v1"
            return f"{base_url}/models", headers

        return f"{config.base_url}/health", headers

    @staticmethod
    def _normalize_ollama_base(base_url: str) -> str:
        normalized = base_url.rstrip("/")
        if normalized.endswith("/v1"):
            return normalized[:-3]
        return normalized


# Singleton Service Instance
_axe_fusion_service: Optional[AXEFusionService] = None


def get_axe_fusion_service(db=None) -> AXEFusionService:
    """Gibt die Singleton Service Instance zurück"""
    global _axe_fusion_service
    if _axe_fusion_service is None or (_axe_fusion_service.db is None and db is not None):
        _axe_fusion_service = AXEFusionService(db=db)
    return _axe_fusion_service
