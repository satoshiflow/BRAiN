"""Verification helpers for genetic integrity records."""

from __future__ import annotations

from app.modules.genetic_integrity.hashing import snapshot_hash
from app.modules.genetic_integrity.schemas import GeneticIntegrityRecord, VerificationResult


def verify_snapshot_record(record: GeneticIntegrityRecord, dna_payload: dict) -> VerificationResult:
    computed = snapshot_hash(
        agent_id=record.agent_id,
        snapshot_version=record.snapshot_version,
        parent_snapshot=record.parent_snapshot,
        dna_payload=dna_payload,
    )
    return VerificationResult(
        agent_id=record.agent_id,
        snapshot_version=record.snapshot_version,
        valid=(computed == record.payload_hash),
        expected_hash=record.payload_hash,
        computed_hash=computed,
    )
