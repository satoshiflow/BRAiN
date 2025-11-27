# backend/modules/llm_client.py
"""
Zentraler LLM-Client für BRAiN
------------------------------

Aktuell: Ollama-kompatibler Client mit einfacher generate()- und
simple_chat()-API.

Die Host/Model/Parameter kommen aus backend.modules.llm_config.
Dadurch können sie zur Laufzeit über /api/llm/config geändert werden.
"""

from __future__ import annotations

import logging
from typing import Any, Dict, List, Tuple

import httpx

from backend.modules.llm_config import get_llm_config

logger = logging.getLogger(__name__)


class LLMClient:
    """
    Thin Wrapper um einen Ollama-kompatiblen HTTP-Endpoint.
    """

    def __init__(self) -> None:
        self._logger = logger

    # ------------------------------------------------------------------
    # Eigenschaften basierend auf aktueller Config
    # ------------------------------------------------------------------
    @property
    def host(self) -> str:
        return get_llm_config().host

    @property
    def model(self) -> str:
        return get_llm_config().model

    @property
    def temperature(self) -> float:
        return get_llm_config().temperature

    @property
    def max_tokens(self) -> int:
        return get_llm_config().max_tokens

    # ------------------------------------------------------------------
    # Low-Level generate()
    # ------------------------------------------------------------------
    async def generate(
        self,
        prompt: str,
        extra_params: Dict[str, Any] | None = None,
    ) -> Dict[str, Any]:
        """
        Ruft den LLM-Endpoint im 'generate'-Stil auf.
        Für Ollama: POST {host}/api/generate
        """
        cfg = get_llm_config()
        if not cfg.enabled:
            raise RuntimeError("LLM usage is disabled via configuration.")

        payload: Dict[str, Any] = {
            "model": cfg.model,
            "prompt": prompt,
            "stream": False,
            "temperature": cfg.temperature,
        }
        if extra_params:
            payload.update(extra_params)

        url = f"{cfg.host}/api/generate"
        self._logger.info("LLM generate call: host=%s model=%s", cfg.host, cfg.model)

        async with httpx.AsyncClient(timeout=60.0) as client:
            resp = await client.post(url, json=payload)
            resp.raise_for_status()
            data = resp.json()

        return data

    # ------------------------------------------------------------------
    # High-Level simple_chat()
    # ------------------------------------------------------------------
    async def simple_chat(
        self,
        messages: List[Dict[str, str]],
        extra_params: Dict[str, Any] | None = None,
    ) -> Tuple[str, Dict[str, Any]]:
        """
        Einfache Chat-API:

        messages: [
          {"role": "system", "content": "..."},
          {"role": "user", "content": "..."},
          ...
        ]

        Aktuell werden die Nachrichten zu einem Prompt zusammengefasst und
        über /api/generate geschickt. Später kann das auf /api/chat
        umgestellt werden.
        """
        parts: List[str] = []
        for msg in messages:
            role = msg.get("role", "user").upper()
            content = msg.get("content", "")
            parts.append(f"{role}: {content}")
        prompt = "\n".join(parts)

        raw = await self.generate(prompt, extra_params=extra_params)
        reply_text = raw.get("response") or raw.get("message") or ""
        return reply_text, raw


# ----------------------------------------------------------------------
# Singleton-Fabrik
# ----------------------------------------------------------------------

_client: LLMClient | None = None


def get_llm_client() -> LLMClient:
    global _client
    if _client is None:
        _client = LLMClient()
    return _client


# ----------------------------------------------------------------------
# API-Routen für LLM-Konfiguration
# ----------------------------------------------------------------------
