"""
Fred Bridge Module

Provides safe integration between BRAiN Runtime and Fred Development Intelligence.

Architecture:
    BRAiN Core (Runtime Authority) ←→ Fred Bridge (Controlled Interface) ←→ Fred/OpenClaw

Responsibilities:
    - Ticket ingestion from BRAiN
    - Patch artifact storage and lifecycle
    - Approval workflow coordination
    - Audit logging

Safety:
    - No direct production runtime modification
    - All changes are auditable artifacts
    - Governor decides, Bridge only coordinates
"""

from app.modules.fred_bridge.schemas import (
    FredTicket,
    FredTicketCreate,
    FredTicketUpdate,
    PatchArtifact,
    PatchArtifactCreate,
    PatchArtifactUpdate,
    TicketListResponse,
    PatchListResponse,
    MockPatchConfig,
)

from app.modules.fred_bridge.service import FredBridgeService, get_bridge_service

__all__ = [
    "FredTicket",
    "FredTicketCreate",
    "FredTicketUpdate",
    "PatchArtifact",
    "PatchArtifactCreate",
    "PatchArtifactUpdate",
    "TicketListResponse",
    "PatchListResponse",
    "MockPatchConfig",
    "FredBridgeService",
    "get_bridge_service",
]
