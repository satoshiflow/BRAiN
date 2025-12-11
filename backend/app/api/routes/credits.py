from fastapi import APIRouter
from app.modules.credits.router import router as credits_router

router = APIRouter()
router.include_router(credits_router)
