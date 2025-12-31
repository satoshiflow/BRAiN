"""
Governor API Endpoints (Phase 2).

Provides REST API for:
- Manifest management (get active, list versions)
- Decision queries
- Shadow reporting
- Statistics
"""

from typing import Optional, List
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from loguru import logger

from backend.app.core.database import get_db
from backend.app.modules.governor.manifest.registry import get_manifest_registry
from backend.app.modules.governor.manifest.schemas import (
    GovernorManifest,
    ShadowReport,
)
from backend.app.modules.governor.decision.store import get_decision_store
from backend.app.modules.governor.decision.models import (
    DecisionQuery,
    DecisionStatistics,
    GovernorDecision,
)
from backend.app.modules.neurorail.errors import ManifestNotFoundError


router = APIRouter(prefix="/api/governor/v2", tags=["governor-v2"])


# ============================================================================
# Manifest Endpoints
# ============================================================================

@router.get("/manifest/active")
async def get_active_manifest(
    db: AsyncSession = Depends(get_db)
) -> Optional[GovernorManifest]:
    """
    Get currently active manifest.

    Returns:
        Active manifest, or null if no manifest is active
    """
    try:
        registry = get_manifest_registry(db)
        manifest = await registry.get_active()
        return manifest
    except Exception as e:
        logger.error(f"Failed to get active manifest: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/manifest/shadow")
async def get_shadow_manifest(
    db: AsyncSession = Depends(get_db)
) -> Optional[GovernorManifest]:
    """
    Get currently shadowed manifest.

    Returns:
        Shadow manifest, or null
    """
    try:
        registry = get_manifest_registry(db)
        manifest = await registry.get_shadow()
        return manifest
    except Exception as e:
        logger.error(f"Failed to get shadow manifest: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/manifest/versions")
async def list_manifest_versions(
    limit: int = 100,
    offset: int = 0,
    db: AsyncSession = Depends(get_db)
) -> List[GovernorManifest]:
    """
    List all manifest versions.

    Args:
        limit: Maximum results (default: 100)
        offset: Result offset (default: 0)

    Returns:
        List of manifests
    """
    try:
        registry = get_manifest_registry(db)
        manifests = await registry.list_all(limit=limit, offset=offset)
        return manifests
    except Exception as e:
        logger.error(f"Failed to list manifests: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/manifest/versions/{version}")
async def get_manifest_version(
    version: str,
    db: AsyncSession = Depends(get_db)
) -> GovernorManifest:
    """
    Get specific manifest version.

    Args:
        version: Manifest version

    Returns:
        Manifest

    Raises:
        HTTPException: 404 if version not found
    """
    try:
        registry = get_manifest_registry(db)
        manifest = await registry.get(version)
        return manifest
    except ManifestNotFoundError as e:
        raise HTTPException(status_code=404, detail=e.message)
    except Exception as e:
        logger.error(f"Failed to get manifest {version}: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# ============================================================================
# Decision Endpoints
# ============================================================================

@router.get("/decisions")
async def query_decisions(
    mission_id: Optional[str] = None,
    job_id: Optional[str] = None,
    job_type: Optional[str] = None,
    mode: Optional[str] = None,
    manifest_version: Optional[str] = None,
    shadow_mode: Optional[bool] = None,
    limit: int = 100,
    offset: int = 0,
    db: AsyncSession = Depends(get_db)
) -> List[GovernorDecision]:
    """
    Query governance decisions.

    Args:
        mission_id: Filter by mission ID
        job_id: Filter by job ID
        job_type: Filter by job type
        mode: Filter by mode (DIRECT/RAIL)
        manifest_version: Filter by manifest version
        shadow_mode: Filter by shadow mode
        limit: Maximum results
        offset: Result offset

    Returns:
        List of decisions
    """
    try:
        store = get_decision_store(db)
        query = DecisionQuery(
            mission_id=mission_id,
            job_id=job_id,
            job_type=job_type,
            mode=mode,
            manifest_version=manifest_version,
            shadow_mode=shadow_mode,
            limit=limit,
            offset=offset,
        )
        decisions = await store.query(query)
        return decisions
    except Exception as e:
        logger.error(f"Failed to query decisions: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/decisions/{decision_id}")
async def get_decision(
    decision_id: str,
    db: AsyncSession = Depends(get_db)
) -> GovernorDecision:
    """
    Get decision by ID.

    Args:
        decision_id: Decision ID

    Returns:
        Decision

    Raises:
        HTTPException: 404 if not found
    """
    try:
        store = get_decision_store(db)
        decision = await store.get(decision_id)

        if not decision:
            raise HTTPException(status_code=404, detail="Decision not found")

        return decision
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get decision {decision_id}: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/decisions/stats")
async def get_decision_statistics(
    db: AsyncSession = Depends(get_db)
) -> DecisionStatistics:
    """
    Get decision statistics.

    Returns:
        Statistics
    """
    try:
        store = get_decision_store(db)
        stats = await store.get_statistics()
        return stats
    except Exception as e:
        logger.error(f"Failed to get decision statistics: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# ============================================================================
# Info Endpoint
# ============================================================================

@router.get("/info")
async def get_governor_info(db: AsyncSession = Depends(get_db)):
    """
    Get governor system information.

    Returns:
        System info including active manifest version
    """
    try:
        registry = get_manifest_registry(db)
        active_manifest = await registry.get_active()
        shadow_manifest = await registry.get_shadow()

        return {
            "name": "Governor v2 (Phase 2)",
            "version": "2.0.0",
            "features": [
                "manifest_versioning",
                "deterministic_decisions",
                "budget_resolution",
                "shadow_evaluation",
                "activation_gate",
            ],
            "active_manifest": (
                active_manifest.version if active_manifest else None
            ),
            "shadow_manifest": (
                shadow_manifest.version if shadow_manifest else None
            ),
            "status": "operational",
        }
    except Exception as e:
        logger.error(f"Failed to get governor info: {e}")
        raise HTTPException(status_code=500, detail=str(e))
