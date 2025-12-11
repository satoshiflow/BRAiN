from fastapi import APIRouter

from app.modules.supervisor.router import router as supervisor_router

router = APIRouter()
router.include_router(supervisor_router)
