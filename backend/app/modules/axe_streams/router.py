import json
import logging
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.responses import StreamingResponse
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.auth_deps import Principal, require_auth
from app.core.database import get_db

from .service import get_axe_stream_service

logger = logging.getLogger(__name__)

router = APIRouter(
    prefix="/api/axe",
    tags=["axe-streams"],
)


async def validate_run_ownership(
    run_id: UUID,
    principal: Principal,
    db: AsyncSession,
) -> None:
    """
    Validate that the user has access to the run_id based on tenant_id.
    Checks SkillRunModel for ownership, and Redis for direct execution runs.
    """
    from app.modules.skill_engine.models import SkillRunModel
    
    query = select(SkillRunModel.tenant_id).where(SkillRunModel.id == run_id)
    result = await db.execute(query)
    tenant_id = result.scalar_one_or_none()
    
    if tenant_id is not None:
        if principal.tenant_id is not None and principal.tenant_id != tenant_id:
            logger.warning("User %s attempted to access run %s with mismatched tenant", principal.principal_id, run_id)
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail={
                    "error": "Access denied",
                    "message": "You do not have access to this run",
                    "code": "RUN_ACCESS_DENIED",
                },
            )
        return
    
    try:
        from app.core.redis_client import get_redis
        redis_client = await get_redis()
        ownership_key = f"axe:stream:ownership:{run_id}"
        stored_tenant = await redis_client.get(ownership_key)
        
        if stored_tenant is not None:
            if principal.tenant_id is not None and principal.tenant_id != stored_tenant:
                logger.warning("User %s attempted to access run %s with mismatched tenant (Redis)", principal.principal_id, run_id)
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail={
                        "error": "Access denied",
                        "message": "You do not have access to this run",
                        "code": "RUN_ACCESS_DENIED",
                    },
                )
        return
    except Exception as exc:
        logger.warning("Failed to check Redis ownership: %s", exc)
    
    logger.debug("Run %s not found in SkillRunModel, allowing access (unknown ownership)", run_id)


@router.get("/runs/{run_id}/events")
async def stream_run_events(
    run_id: UUID,
    principal: Principal = Depends(require_auth),
    db: AsyncSession = Depends(get_db),
):
    await validate_run_ownership(run_id, principal, db)
    
    stream_service = get_axe_stream_service()

    async def event_generator():
        queue = await stream_service.subscribe(run_id)
        try:
            while True:
                event = await queue.get()
                if event is None:
                    break
                yield f"event: {event.event_type.value}\ndata: {json.dumps(event.model_dump())}\n\n"
        finally:
            await stream_service.unsubscribe(run_id)

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )
