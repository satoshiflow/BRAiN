from fastapi import APIRouter, Depends
from app.core.security import Principal, get_current_principal
from .service import get_health, get_info
from .schemas import PolicyHealth, PolicyInfo

router = APIRouter(
    prefix="/api/policy",
    tags=["policy"],
)

@router.get("/health", response_model=PolicyHealth)
async def policy_health(principal: Principal = Depends(get_current_principal)):
    return await get_health()

@router.get("/info", response_model=PolicyInfo)
async def policy_info(principal: Principal = Depends(get_current_principal)):
    return await get_info()
