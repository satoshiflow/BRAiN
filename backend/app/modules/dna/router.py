from fastapi import APIRouter, HTTPException, status

from app.modules.dna.core.service import DNAService
from app.modules.dna.schemas import (
    CreateDNASnapshotRequest,
    MutateDNARequest,
    AgentDNASnapshot,
    DNAHistoryResponse,
)

router = APIRouter(prefix="/api/dna", tags=["DNA"])

# Einfacher Singleton-Service im Prozess
dna_service = DNAService()


@router.post(
    "/snapshot",
    response_model=AgentDNASnapshot,
    status_code=status.HTTP_201_CREATED,
)
def create_snapshot(payload: CreateDNASnapshotRequest) -> AgentDNASnapshot:
    return dna_service.create_snapshot(payload)


@router.post(
    "/agents/{agent_id}/mutate",
    response_model=AgentDNASnapshot,
)
def mutate_agent_dna(
    agent_id: str,
    payload: MutateDNARequest,
) -> AgentDNASnapshot:
    try:
        return dna_service.mutate(agent_id, payload)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc))


@router.get(
    "/agents/{agent_id}/history",
    response_model=DNAHistoryResponse,
)
def get_history(agent_id: str) -> DNAHistoryResponse:
    return dna_service.history(agent_id)