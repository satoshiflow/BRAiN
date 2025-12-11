from fastapi import APIRouter

router = APIRouter(prefix="/api", tags=["core"])

@router.get("/health", summary="Health check")
async def health() -> dict:
    return {"status": "ok"}
