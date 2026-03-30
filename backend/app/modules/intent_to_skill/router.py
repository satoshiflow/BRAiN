from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.auth_deps import Principal, SystemRole, get_current_principal, require_auth
from app.core.database import get_db

from .schemas import IntentExecuteRequest, IntentExecuteResponse
from .service import get_intent_to_skill_service


router = APIRouter(prefix="/api/intent", tags=["intent-to-skill"], dependencies=[Depends(require_auth)])


@router.post("/execute", response_model=IntentExecuteResponse)
async def execute_intent(
    payload: IntentExecuteRequest,
    db: AsyncSession = Depends(get_db),
    principal: Principal = Depends(get_current_principal),
):
    if payload.auto_execute and not principal.has_any_role(
        [
            SystemRole.OPERATOR,
            SystemRole.ADMIN,
            SystemRole.SERVICE,
            SystemRole.SYSTEM_ADMIN,
        ]
    ):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Insufficient role for auto_execute",
        )

    try:
        return await get_intent_to_skill_service().execute_intent(db, payload, principal)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc
    except PermissionError as exc:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(exc)) from exc
