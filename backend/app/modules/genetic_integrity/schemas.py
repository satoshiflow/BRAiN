"""Schemas for Genetic Integrity Service."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field


def _utc_now() -> datetime:
    return datetime.now(timezone.utc)


class RegisterSnapshotRequest(BaseModel):
    agent_id: str
    snapshot_version: int = Field(ge=1)
    parent_snapshot: Optional[int] = None
    dna_payload: Dict[str, Any] = Field(default_factory=dict)
    correlation_id: Optional[str] = None
    source: str = "dna"


class GeneticIntegrityRecord(BaseModel):
    record_id: str
    agent_id: str
    snapshot_version: int
    parent_snapshot: Optional[int] = None
    payload_hash: str
    parent_hash: Optional[str] = None
    created_at: datetime = Field(default_factory=_utc_now)
    correlation_id: Optional[str] = None


class VerifySnapshotRequest(BaseModel):
    dna_payload: Dict[str, Any] = Field(default_factory=dict)


class VerificationResult(BaseModel):
    agent_id: str
    snapshot_version: int
    valid: bool
    expected_hash: Optional[str] = None
    computed_hash: Optional[str] = None


class MutationAuditRequest(BaseModel):
    agent_id: str
    from_version: int = Field(ge=1)
    to_version: int = Field(ge=1)
    mutation: Dict[str, Any] = Field(default_factory=dict)
    actor: str = "system"
    reason: str = "mutation_applied"
    correlation_id: Optional[str] = None
    requires_governance_hook: bool = False


class MutationAuditRecord(BaseModel):
    audit_id: str
    agent_id: str
    from_version: int
    to_version: int
    actor: str
    reason: str
    mutation: Dict[str, Any] = Field(default_factory=dict)
    requires_governance_hook: bool = False
    correlation_id: Optional[str] = None
    created_at: datetime = Field(default_factory=_utc_now)


class GeneticAuditEntry(BaseModel):
    audit_id: str
    event_type: str
    action: str
    resource_type: str
    resource_id: str
    details: Dict[str, Any] = Field(default_factory=dict)
    timestamp: datetime = Field(default_factory=_utc_now)


class GeneticMetrics(BaseModel):
    total_snapshots: int = 0
    total_mutations: int = 0
    governance_hooks: int = 0


class GeneticIntegrityRecordList(BaseModel):
    items: List[GeneticIntegrityRecord] = Field(default_factory=list)


class MutationAuditRecordList(BaseModel):
    items: List[MutationAuditRecord] = Field(default_factory=list)


class GeneticAuditEntryList(BaseModel):
    items: List[GeneticAuditEntry] = Field(default_factory=list)
