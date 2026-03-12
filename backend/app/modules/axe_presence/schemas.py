"""Schemas for AXE presence surface endpoints."""

from __future__ import annotations

from typing import List

from pydantic import BaseModel, Field


class AXEPresenceResponse(BaseModel):
    status: str = Field(...)
    label: str = Field(...)
    signal: str = Field(...)
    capabilities: List[str] = Field(default_factory=list)
    last_seen: str = Field(...)
    action_hint: str = Field(...)


class AXERelayResponse(BaseModel):
    status: str = Field(...)
    label: str = Field(...)
    signal: str = Field(...)
    capabilities: List[str] = Field(default_factory=list)
    last_seen: str = Field(...)
    action_hint: str = Field(...)


class AXERelaysListResponse(BaseModel):
    relays: List[AXERelayResponse] = Field(default_factory=list)


class AXERuntimeSurfaceResponse(BaseModel):
    status: str = Field(...)
    label: str = Field(...)
    signal: str = Field(...)
    capabilities: List[str] = Field(default_factory=list)
    last_seen: str = Field(...)
    action_hint: str = Field(...)
    active_agents: int = Field(default=0, ge=0)
    pending_missions: int = Field(default=0, ge=0)
    uptime: str = Field(...)
