"""
BRAIN Mission System V1 - LLM Client Abstraction Layer
=======================================================

Dieses Modul definiert die Abstraktionsschicht für LLM-Calls.
Aktuell nutzen wir einen Mock-Client (Dummy), später kann hier
ein lokaler LLM oder API-basierter Client eingebunden werden.

Architektur:
- LLMClient (Abstract Base Class)
- MockLLMClient (Dummy für V1)
- Später: LocalLLMClient, AnthropicClient, etc.

Author: Claude (Chief Developer)
Created: 2025-11-11
"""

from abc import ABC, abstractmethod
from typing import Dict, List, Optional, Any
from dataclasses import dataclass
import json
import time


@dataclass
class LLMMessage:
    """Einzelne Nachricht im LLM-Kontext"""
    role: str  # "system", "user", "assistant"
    content: str


@dataclass
class LLMResponse:
    """Response von LLM Call"""
    content: str
    model: str
    tokens_used: int
    latency_ms: float
    metadata: Dict[str, Any]


class LLMClient(ABC):
    """
    Abstract Base Class für alle LLM-Clients.
    
    Diese Klasse definiert die Schnittstelle für LLM-Interaktionen.
    Alle konkreten Implementierungen (Mock, Local, API) müssen
    diese Methoden implementieren.
    """
    
    @abstractmethod
    def call(
        self,
        messages: List[LLMMessage],
        temperature: float = 0.7,
        max_tokens: int = 1024,
        **kwargs
    ) -> LLMResponse:
        """
        Führt einen LLM-Call durch.
        
        Args:
            messages: Liste von LLMMessage Objekten
            temperature: Kreativität (0.0 = deterministisch, 1.0 = kreativ)
            max_tokens: Maximale Anzahl Tokens in Response
            **kwargs: Weitere modell-spezifische Parameter
            
        Returns:
            LLMResponse mit Ergebnis
        """
        pass
    
    @abstractmethod
    def stream(
        self,
        messages: List[LLMMessage],
        temperature: float = 0.7,
        max_tokens: int = 1024,
        **kwargs
    ):
        """
        Streamt LLM-Response (Generator).
        
        Für V1 optional, später für UI-Feedback wichtig.
        """
        pass
    
    @abstractmethod
    def get_model_info(self) -> Dict[str, Any]:
        """
        Gibt Informationen über das verwendete Modell zurück.
        
        Returns:
            Dict mit model_name, context_window, etc.
        """
        pass


class MockLLMClient(LLMClient):
    """
    Mock-Implementation für Development/Testing.
    
    Dieser Client simuliert LLM-Antworten ohne echte API-Calls.
    Nützlich für:
    - Testing ohne API-Keys
    - Lokale Entwicklung
    - CI/CD Pipelines
    """
    
    def __init__(self, model_name: str = "mock-llm-v1"):
        self.model_name = model_name
        self.call_count = 0
        
    def call(
        self,
        messages: List[LLMMessage],
        temperature: float = 0.7,
        max_tokens: int = 1024,
        **kwargs
    ) -> LLMResponse:
        """
        Simuliert einen LLM-Call mit deterministischen Antworten.
        
        Generiert Antworten basierend auf dem letzten User-Message.
        """
        start_time = time.time()
        self.call_count += 1
        
        # Extrahiere letztes User-Message
        user_messages = [m for m in messages if m.role == "user"]
        last_user_msg = user_messages[-1].content if user_messages else ""
        
        # Generiere Mock-Response basierend auf Keywords
        content = self._generate_mock_response(last_user_msg, temperature)
        
        # Simuliere Token-Nutzung
        tokens_used = len(content.split()) * 1.3  # Rough estimate
        
        latency_ms = (time.time() - start_time) * 1000
        
        return LLMResponse(
            content=content,
            model=self.model_name,
            tokens_used=int(tokens_used),
            latency_ms=latency_ms,
            metadata={
                "call_count": self.call_count,
                "temperature": temperature,
                "max_tokens": max_tokens,
                "mock": True
            }
        )
    
    def _generate_mock_response(self, user_message: str, temperature: float) -> str:
        """
        Generiert deterministische Mock-Antworten.
        
        Basiert auf Keywords im User-Message für realistische Antworten.
        """
        user_lower = user_message.lower()
        
        # Keyword-basierte Responses
        if "late" in user_lower and "check" in user_lower:
            return json.dumps({
                "analysis": "Late check-in detected",
                "required_actions": [
                    "Retrieve door code from booking system",
                    "Send SMS with access instructions",
                    "Log interaction in CRM"
                ],
                "priority": "high",
                "estimated_duration": "5 minutes"
            })
        
        elif "price" in user_lower or "pricing" in user_lower:
            return json.dumps({
                "analysis": "Pricing optimization request",
                "suggested_price": 120.50,
                "factors": ["season", "demand", "competitor_rates"],
                "confidence": 0.85
            })
        
        elif "maintenance" in user_lower or "repair" in user_lower:
            return json.dumps({
                "analysis": "Maintenance request detected",
                "urgency": "medium",
                "suggested_actions": [
                    "Schedule technician visit",
                    "Notify property manager",
                    "Update maintenance log"
                ]
            })
        
        else:
            # Generic response
            return json.dumps({
                "status": "processed",
                "message": "Mock LLM response generated successfully",
                "input_length": len(user_message),
                "timestamp": time.time()
            })
    
    def stream(
        self,
        messages: List[LLMMessage],
        temperature: float = 0.7,
        max_tokens: int = 1024,
        **kwargs
    ):
        """
        Mock-Stream: Gibt Response in Chunks zurück.
        
        Für V1 nicht implementiert, gibt gesamte Response zurück.
        """
        response = self.call(messages, temperature, max_tokens, **kwargs)
        yield response.content
    
    def get_model_info(self) -> Dict[str, Any]:
        """Gibt Mock-Modellinformationen zurück."""
        return {
            "model_name": self.model_name,
            "type": "mock",
            "context_window": 8192,
            "max_tokens": 4096,
            "capabilities": ["text", "json"],
            "cost_per_1k_tokens": 0.0,  # Mock ist kostenlos
            "call_count": self.call_count
        }


# Factory Function für einfache Client-Erstellung
def get_llm_client(client_type: str = "mock", **config) -> LLMClient:
    """
    Factory Function für LLM-Client Erstellung.
    
    Args:
        client_type: "mock", "local", "anthropic", etc.
        **config: Client-spezifische Konfiguration
        
    Returns:
        Konfigurierter LLMClient
        
    Example:
        >>> client = get_llm_client("mock")
        >>> response = client.call([LLMMessage("user", "Hello")])
    """
    if client_type == "mock":
        return MockLLMClient(**config)
    
    # Später weitere Clients:
    # elif client_type == "local":
    #     return LocalLLMClient(**config)
    # elif client_type == "anthropic":
    #     return AnthropicClient(**config)
    
    else:
        raise ValueError(f"Unknown LLM client type: {client_type}")


# Convenience Functions
def create_message(role: str, content: str) -> LLMMessage:
    """Helper zum Erstellen von LLMMessage."""
    return LLMMessage(role=role, content=content)


def create_system_message(content: str) -> LLMMessage:
    """Helper für System-Prompts."""
    return LLMMessage(role="system", content=content)


def create_user_message(content: str) -> LLMMessage:
    """Helper für User-Messages."""
    return LLMMessage(role="user", content=content)
