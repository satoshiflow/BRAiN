# backend/modules/llm_client.py

from __future__ import annotations

import logging
import os
from typing import Any, Dict, List, Optional

import httpx

logger = logging.getLogger(__name__)


class LLMClient:
    """
    Zentraler LLM-Client für BRAIN.

    Aktuell: HTTP-Client für Ollama-kompatible /api/generate-Endpoint.
    """

    def __init__(
        self,
        host: Optional[str] = None,
        model: Optional[str] = None,
        timeout_seconds: Optional[float] = None,
    ) -> None:
        self.host = host or os.getenv("OLLAMA_HOST", "http://host.docker.internal:11434")
        self.model = model or os.getenv("OLLAMA_MODEL", "phi3")
        self.timeout_seconds = timeout_seconds or float(
            os.getenv("LLM_HTTP_TIMEOUT", "60")
        )

    async def generate(
        self,
        prompt: str,
        extra_params: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """
        Low-level Aufruf an /api/generate (non-streaming).
        """
        payload: Dict[str, Any] = {
            "model": self.model,
            "prompt": prompt,
            "stream": False,
        }
        if extra_params:
            payload.update(extra_params)

        async with httpx.AsyncClient(timeout=self.timeout_seconds) as client:
            try:
                resp = await client.post(f"{self.host}/api/generate", json=payload)
                resp.raise_for_status()
                return resp.json()
            except httpx.ReadTimeout as exc:
                logger.error(
                    "LLM generate() timed out after %.1fs (host=%s, model=%s)",
                    self.timeout_seconds,
                    self.host,
                    self.model,
                )
                raise exc
            except httpx.HTTPError as exc:
                logger.error(
                    "LLM generate() HTTP error: %s (host=%s, model=%s)",
                    exc,
                    self.host,
                    self.model,
                )
                raise

    async def simple_chat(
        self,
        messages: List[Dict[str, str]],
        extra_params: Optional[Dict[str, Any]] = None,
    ) -> tuple[str, Dict[str, Any]]:
        """
        Sehr einfacher Chat-Wrapper:
        - messages: [{"role": "user" | "system" | "assistant", "content": "..."}]
        - gibt (text_reply, raw_response) zurück
        """
        # Für V1: wir flatten die Messages in einen Prompt
        prompt_parts: List[str] = []
        for msg in messages:
            role = msg.get("role", "user")
            content = msg.get("content", "")
            prompt_parts.append(f"{role.upper()}: {content}\n")

        raw = await self.generate("".join(prompt_parts), extra_params=extra_params)

        # Ollama-Response vereinfachen
        reply_text = raw.get("response") or raw.get("text") or ""
        return reply_text, raw


# Singleton-Instanz für das Backend
_llm_client: Optional[LLMClient] = None


def get_llm_client() -> LLMClient:
    global _llm_client
    if _llm_client is None:
        _llm_client = LLMClient()
    return _llm_client
