"""
AXE Fusion Service - Client für AXEllm Integration

Bietet HTTP-Client zu AXEllm mit Timeout, Error Handling und Response Mapping.
"""

import os
import logging
from typing import Any, Dict, List, Optional
import httpx

logger = logging.getLogger(__name__)

# Konfiguration
AXELLM_BASE_URL = os.getenv("AXELLM_BASE_URL", "http://axellm:8000")
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


def _sanitize_messages(messages: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """
    Guardrails: Bereinigt Nachrichten
    - Entfernt tool/function_call Felder
    - Filtert nur erlaubte Rollen
    - Prüft Zeichenlimit
    """
    sanitized = []
    total_chars = 0
    
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
            f"Request zu groß: {total_chars} Zeichen (Limit: {MAX_CHARS})"
        )
    
    return sanitized


class AXEllmClient:
    """HTTP Client für AXEllm API"""
    
    def __init__(self, base_url: Optional[str] = None):
        self.base_url = base_url or AXELLM_BASE_URL
        self.timeout = AXELLM_TIMEOUT
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
        
        try:
            response = await self.client.post(
                f"{self.base_url}/v1/chat/completions",
                json=payload,
                headers={"Content-Type": "application/json"}
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
        self.client = AXEllmClient()
        self.db = db
    
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
        
        return await self.client.chat(model, messages, temperature)
    
    async def health_check(self) -> Dict[str, Any]:
        """
        Prüft ob AXEllm erreichbar ist
        
        Returns:
            Dict mit Status
        """
        try:
            response = await self.client.client.get(
                f"{self.client.base_url}/health",
                timeout=5.0
            )
            if response.status_code == 200:
                return {"status": "healthy", "axellm": "reachable"}
            else:
                return {"status": "degraded", "axellm": f"status_{response.status_code}"}
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
