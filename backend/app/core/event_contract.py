"""Standardized event envelope and publish helper for BRAiN runtime events."""

from __future__ import annotations

import inspect
import time
import uuid
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Optional

from pydantic import BaseModel, Field


class EventSeverity(str, Enum):
    INFO = "info"
    WARNING = "warning"
    CRITICAL = "critical"


def _utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


class RuntimeEventEnvelope(BaseModel):
    event_type: str
    severity: EventSeverity
    source: str
    entity: str
    correlation_id: Optional[str] = None
    occurred_at: str = Field(default_factory=_utc_now_iso)
    data: dict[str, Any] = Field(default_factory=dict)


def build_runtime_event_payload(
    *,
    event_type: str,
    severity: EventSeverity,
    source: str,
    entity: str,
    correlation_id: Optional[str],
    data: dict[str, Any],
) -> dict[str, Any]:
    return RuntimeEventEnvelope(
        event_type=event_type,
        severity=severity,
        source=source,
        entity=entity,
        correlation_id=correlation_id,
        data=data,
    ).model_dump()


def build_event_instance(EventCls, *, event_type: str, source: str, payload: dict[str, Any], correlation_id: Optional[str]):
    """Create Event instance compatible with multiple Event signatures."""
    event_params = inspect.signature(EventCls).parameters

    resolved_type: Any = event_type
    type_param = event_params.get("type")
    if type_param is not None:
        annotation = type_param.annotation
        if inspect.isclass(annotation) and issubclass(annotation, Enum):
            try:
                resolved_type = annotation(event_type)
            except Exception:
                if hasattr(annotation, "SYSTEM_ALERT"):
                    resolved_type = annotation.SYSTEM_ALERT
                else:
                    resolved_type = next(iter(annotation))

    event_kwargs = {
        "type": resolved_type,
        "source": source,
        "target": None,
        "payload": payload,
    }

    if "id" in event_params:
        event_kwargs["id"] = f"evt_{source}_{uuid.uuid4().hex[:12]}"
    if "timestamp" in event_params:
        ts_annotation = event_params["timestamp"].annotation
        if ts_annotation is datetime:
            event_kwargs["timestamp"] = datetime.now(timezone.utc).replace(tzinfo=None)
        else:
            event_kwargs["timestamp"] = time.time()
    if "meta" in event_params:
        event_kwargs["meta"] = {"correlation_id": correlation_id, "version": "1.0"}
    if "correlation_id" in event_params:
        event_kwargs["correlation_id"] = correlation_id
    return EventCls(**event_kwargs)
