from fastapi import APIRouter
from app.modules.dna.router import router as dna_router

router = APIRouter()
router.include_router(dna_router)
