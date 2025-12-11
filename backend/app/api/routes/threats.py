from fastapi import APIRouter

from app.modules.threats.router import router as threats_router

router = APIRouter()
router.include_router(threats_router)