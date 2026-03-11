"""
AXE Fusion Service - Client für AXEllm Integration

Bietet HTTP-Client zu AXEllm mit Timeout, Error Handling und Response Mapping.
"""

import logging
from typing import Any, Dict, List, Optional, Tuple
import httpx

from .data_sanitizer import DataSanitizer
from .provider_selector import (
    LLMProvider,
    ProviderConfig,
    ProviderSelector,
    SanitizationLevel,
)

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
                f"{self.base_url}/v1/chat/completions",
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
        level = self.selector.get_sanitization_level(config.provider)
        return {
            "active": config.to_dict(),
            "sanitization_level": level.value,
        }

    def set_provider_runtime(
        self,
        provider: LLMProvider,
        force_sanitization_level: Optional[SanitizationLevel],
    ) -> Dict[str, Any]:
        self.selector.set_runtime_mode(provider)
        self.selector.set_force_sanitization_level(force_sanitization_level)
        return self.get_provider_runtime()
    
    async def chat(
        self,
        model: str,
        messages: List[Dict[str, Any]],
        temperature: float = 0.7,
        inject_identity: bool = True
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

        provider_config = self.selector.get_active_config()
        client = self._get_or_create_client(provider_config)
        effective_model = self._resolve_model(model, provider_config)

        sanitization_level = self.selector.get_sanitization_level(provider_config.provider)
        if sanitization_level != SanitizationLevel.NONE:
            outbound_messages, mapping = self.sanitizer.sanitize_messages(messages, sanitization_level)
        else:
            outbound_messages, mapping = messages, None

        result = await client.chat(effective_model, outbound_messages, temperature)

        if mapping and result.get("text"):
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

        return result
    
    async def health_check(self) -> Dict[str, Any]:
        """
        Prüft ob AXEllm erreichbar ist
        
        Returns:
            Dict mit Status
        """
        try:
            provider_config = self.selector.get_active_config()
            client = self._get_or_create_client(provider_config)
            response = await client.client.get(
                f"{client.base_url}/health",
                timeout=5.0
            )
            if response.status_code == 200:
                return {
                    "status": "healthy",
                    "axellm": "reachable",
                    "provider": provider_config.provider.value,
                }
            else:
                return {
                    "status": "degraded",
                    "axellm": f"status_{response.status_code}",
                    "provider": provider_config.provider.value,
                }
        except Exception as e:
            logger.warning(f"AXEllm Health Check fehlgeschlagen: {e}")
            return {"status": "unavailable", "axellm": "not_reachable", "error": str(e)}


# Singleton Service Instance
_axe_fusion_service: Optional[AXEFusionService] = None


def get_axe_fusion_service(db=None) -> AXEFusionService:
    """Gibt die Singleton Service Instance zurück"""
    global _axe_fusion_service
    if _axe_fusion_service is None or (_axe_fusion_service.db is None and db is not None):
        _axe_fusion_service = AXEFusionService(db=db)
    return _axe_fusion_service
