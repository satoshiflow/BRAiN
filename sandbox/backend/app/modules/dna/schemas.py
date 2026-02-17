from datetime import datetime
from typing import Any, Dict, Optional, List
from pydantic import BaseModel, Field


class DNAMetadata(BaseModel):
    reason: Optional[str] = None
    source: str = Field(default="manual", description="manual|system|mutation")
    parent_snapshot_id: Optional[int] = None


class AgentDNASnapshot(BaseModel):
    id: int
    agent_id: str
    version: int
    dna: Dict[str, Any]
    traits: Dict[str, Any]
    karma_score: Optional[float] = None
    created_at: datetime
    meta: DNAMetadata


class CreateDNASnapshotRequest(BaseModel):
    agent_id: str
    dna: Dict[str, Any]
    traits: Dict[str, Any] = {}
    reason: Optional[str] = None


class MutateDNARequest(BaseModel):
    mutation: Dict[str, Any]
    traits_delta: Dict[str, Any] = {}
    reason: Optional[str] = None


class DNAHistoryResponse(BaseModel):
    agent_id: str
    snapshots: List[AgentDNASnapshot]