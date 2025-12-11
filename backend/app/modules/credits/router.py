from fastapi import APIRouter, Depends
from app.core.security import Principal, get_current_principal
from .service import get_health, get_info
from .schemas import CreditsHealth, CreditsInfo

router = APIRouter(
    prefix="/api/credits",
    tags=["credits"],
)

@router.get("/health", response_model=CreditsHealth)
async def credits_health(principal: Principal = Depends(get_current_principal)):
    return await get_health()

@router.get("/info", response_model=CreditsInfo)
async def credits_info(principal: Principal = Depends(get_current_principal)):
    return await get_info()
