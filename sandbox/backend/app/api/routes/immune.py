from fastapi import APIRouter
from app.modules.immune.router import router as immune_router

router = APIRouter()
router.include_router(immune_router)
