from typing import List

from fastapi import APIRouter, Depends, status

from .schemas import (
    SupervisorStatus,
    AgentStatus,
    AgentControlRequest,
    AgentControlResponse,
)
from .service import get_supervisor_service, SupervisorService

router = APIRouter(prefix="/supervisor", tags=["supervisor"])


def _get_service() -> SupervisorService:
    return get_supervisor_service()


@router.get(
    "/status",
    response_model=SupervisorStatus,
    status_code=status.HTTP_200_OK,
)
def get_supervisor_status(service: SupervisorService = Depends(_get_service)) -> SupervisorStatus:
    return service.get_status()


@router.get(
    "/agents",
    response_model=List[AgentStatus],
    status_code=status.HTTP_200_OK,
)
def list_agents(service: SupervisorService = Depends(_get_service)) -> List[AgentStatus]:
    return service.list_agents()


@router.post(
    "/control",
    response_model=AgentControlResponse,
    status_code=status.HTTP_200_OK,
)
def control_agent(
    payload: AgentControlRequest,
    service: SupervisorService = Depends(_get_service),
) -> AgentControlResponse:
    return service.control_agent(payload)
