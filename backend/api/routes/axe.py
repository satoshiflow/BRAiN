# backend/api/routes/axe.py

from __future__ import annotations

import inspect
import logging
from typing import Any, Dict, Optional

from fastapi import APIRouter
from pydantic import BaseModel

from backend.modules.connector_hub.services import get_gateway
from backend.modules.llm_client import get_llm_client

logger = logging.getLogger(__name__)

router = APIRouter(
    prefix="/api/axe",
    tags=["axe"],
)


class AxeMessage(BaseModel):
    message: str
    metadata: Dict[str, Any] | None = None


async def _call_gateway_send_message(
    gateway: Any,
    *,
    message: str,
    metadata: Dict[str, Any],
) -> Optional[Dict[str, Any]]:
    """
    Versucht, gateway.send_message(message=..., metadata=...) aufzurufen.
    Gibt None zurück, wenn keine passende Implementierung existiert.
    Erwartet, dass das Gateway ein Dict-artiges Ergebnis zurückgibt.
    """
    send = getattr(gateway, "send_message", None)
    if send is None or not callable(send):
        return None

    if inspect.iscoroutinefunction(send):
        result = await send(message=message, metadata=metadata)
    else:
        result = send(message=message, metadata=metadata)
        if inspect.isawaitable(result):
            result = await result

    if isinstance(result, dict):
        return result
    # Notfalls in Dict wrappen
    return {"result": result}


@router.get("/info")
async def axe_info() -> Dict[str, Any]:
    gateway = get_gateway()
    gateway_name = getattr(gateway, "name", None) if gateway is not None else None

    return {
        "name": "AXE",
        "version": "1.0",
        "status": "online" if gateway is not None else "degraded",
        "description": "Auxiliary Execution Engine über Connector Hub / LLM.",
        "gateway": gateway_name or "none",
    }


@router.post("/message")
async def axe_message(payload: AxeMessage) -> Dict[str, Any]:
    """
    AXE-Endpoint:

    1. Versucht, über den Connector Hub ein Gateway zu nutzen.
    2. Wenn das nicht klappt oder kein passender Handler existiert,
       verwendet er den zentralen LLMClient als Fallback.
    """
    metadata: Dict[str, Any] = payload.metadata or {}

    # ---------------------------------------------------------------------
    # 1) Versuch: Gateway über Connector Hub
    # ---------------------------------------------------------------------
    gateway = get_gateway()
    if gateway is not None:
        try:
            gw_result = await _call_gateway_send_message(
                gateway,
                message=payload.message,
                metadata=metadata,
            )
        except Exception as exc:  # pragma: no cover – defensiver Catch
            logger.error("AXE gateway send_message failed: %s", exc)
            gw_result = None

        if gw_result is not None:
            # Versuchen, einen "reply"-Text aus dem Gateway-Result zu extrahieren
            reply_text = (
                gw_result.get("reply")
                or gw_result.get("message")
                or gw_result.get("text")
                or ""
            )
            return {
                "mode": "gateway",
                "gateway": getattr(gateway, "name", "unknown"),
                "input_message": payload.message,
                "reply": reply_text,
                "metadata": metadata,
                "result": gw_result,
            }

    # ---------------------------------------------------------------------
    # 2) Fallback: direkter LLM-Call über zentralen LLMClient
    # ---------------------------------------------------------------------
    client = get_llm_client()
    system_prompt = (
        "Du bist AXE, die Execution-Engine von BRAiN. "
        "Beantworte oder kommentiere die Nachricht kurz und präzise."
    )

    messages = [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": payload.message},
    ]

    try:
        reply_text, raw = await client.simple_chat(
            messages=messages,
            extra_params=None,
        )
    except Exception as exc:
        logger.error("AXE LLM fallback failed: %s", exc)
        # Immer noch eine strukturierte Antwort liefern
        return {
            "mode": "llm-fallback-error",
            "gateway": getattr(gateway, "name", "none") if gateway else "none",
            "input_message": payload.message,
            "reply": "",
            "metadata": metadata,
            "error": str(exc),
        }

    return {
        "mode": "llm-fallback",
        "gateway": getattr(gateway, "name", "none") if gateway else "none",
        "input_message": payload.message,
        "reply": reply_text,
        "metadata": metadata,
        "result": {
            "raw_llm": raw,
        },
    }

# End of file
# backend/modules/llm_client.py