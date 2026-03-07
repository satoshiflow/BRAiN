"""API router for Genetic Integrity Service."""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.auth_deps import require_auth
from app.core.database import get_db
from app.modules.genetic_integrity.schemas import (
    GeneticAuditEntryList,
    GeneticIntegrityRecord,
    GeneticIntegrityRecordList,
    GeneticMetrics,
    MutationAuditRecord,
    MutationAuditRecordList,
    MutationAuditRequest,
    RegisterSnapshotRequest,
    VerificationResult,
    VerifySnapshotRequest,
)
from app.modules.genetic_integrity.service import get_genetic_integrity_service


router = APIRouter(
    prefix="/api/genetic-integrity",
    tags=["Genetic Integrity"],
    dependencies=[Depends(require_auth)],
)


@router.post("/snapshots/register", response_model=GeneticIntegrityRecord)
async def register_snapshot(
    request: RegisterSnapshotRequest,
    db: AsyncSession = Depends(get_db),
) -> GeneticIntegrityRecord:
    service = get_genetic_integrity_service()
    return await service.register_snapshot(request, db=db)


@router.get("/snapshots", response_model=GeneticIntegrityRecordList)
async def list_snapshots(
    agent_id: str | None = None,
    db: AsyncSession = Depends(get_db),
) -> GeneticIntegrityRecordList:
    service = get_genetic_integrity_service()
    return GeneticIntegrityRecordList(items=await service.list_snapshot_records(agent_id=agent_id, db=db))


@router.get("/snapshots/{agent_id}/{snapshot_version}", response_model=GeneticIntegrityRecord)
async def get_snapshot(
    agent_id: str,
    snapshot_version: int,
    db: AsyncSession = Depends(get_db),
) -> GeneticIntegrityRecord:
    service = get_genetic_integrity_service()
    record = await service.get_snapshot_record(agent_id, snapshot_version, db=db)
    if record is None:
        raise HTTPException(status_code=404, detail="Snapshot record not found")
    return record


@router.post("/snapshots/{agent_id}/{snapshot_version}/verify", response_model=VerificationResult)
async def verify_snapshot(
    agent_id: str,
    snapshot_version: int,
    request: VerifySnapshotRequest,
    db: AsyncSession = Depends(get_db),
) -> VerificationResult:
    service = get_genetic_integrity_service()
    return await service.verify_snapshot(agent_id, snapshot_version, request.dna_payload, db=db)


@router.post("/mutations/record", response_model=MutationAuditRecord)
async def record_mutation(
    request: MutationAuditRequest,
    db: AsyncSession = Depends(get_db),
) -> MutationAuditRecord:
    service = get_genetic_integrity_service()
    return await service.record_mutation(request, db=db)


@router.get("/mutations", response_model=MutationAuditRecordList)
async def list_mutations(db: AsyncSession = Depends(get_db)) -> MutationAuditRecordList:
    service = get_genetic_integrity_service()
    return MutationAuditRecordList(items=await service.list_mutation_audit(db=db))


@router.get("/audit", response_model=GeneticAuditEntryList)
async def list_audit_entries(db: AsyncSession = Depends(get_db)) -> GeneticAuditEntryList:
    service = get_genetic_integrity_service()
    return GeneticAuditEntryList(items=await service.list_audit_entries(db=db))


@router.get("/metrics", response_model=GeneticMetrics)
async def get_metrics(db: AsyncSession = Depends(get_db)) -> GeneticMetrics:
    service = get_genetic_integrity_service()
    return await service.metrics(db=db)
