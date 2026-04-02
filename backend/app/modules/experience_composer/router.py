from __future__ import annotations

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.auth_deps import Principal, require_auth
from app.core.database import get_db

from .schemas import ExperienceRenderRequest, ExperienceRenderResponse
from .service import get_experience_composer_service


router = APIRouter(prefix="/api/experiences", tags=["experience-composer"])


@router.post("/render", response_model=ExperienceRenderResponse)
async def render_experience(
    payload: ExperienceRenderRequest,
    db: AsyncSession = Depends(get_db),
    principal: Principal = Depends(require_auth),
):
    output = await get_experience_composer_service().render(db, principal, payload)
    return ExperienceRenderResponse(output=output)
