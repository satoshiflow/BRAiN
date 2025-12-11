from fastapi import APIRouter
from app.modules.karma.router import router as karma_router

router = APIRouter()
router.include_router(karma_router)
