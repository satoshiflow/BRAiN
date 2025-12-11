from fastapi import APIRouter
from app.modules.missions.router import router as missions_router

router = APIRouter()
router.include_router(missions_router)
# backend/app/modules/missions/__init__.py