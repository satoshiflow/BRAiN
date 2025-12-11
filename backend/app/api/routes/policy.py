from fastapi import APIRouter
from app.modules.policy.router import router as policy_router

router = APIRouter()
router.include_router(policy_router)
