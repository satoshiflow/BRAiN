"""
FastAPI Router for Cluster System API

Endpoints:
- POST   /api/clusters              Create cluster from blueprint
- GET    /api/clusters              List clusters
- GET    /api/clusters/{id}         Get cluster details
- PUT    /api/clusters/{id}         Update cluster
- DELETE /api/clusters/{id}         Delete cluster
- POST   /api/clusters/{id}/scale   Manual scale
- POST   /api/clusters/{id}/hibernate
- POST   /api/clusters/{id}/reactivate
- GET    /api/clusters/{id}/agents  List agents
- GET    /api/clusters/{id}/hierarchy
- POST   /api/blueprints            Upload blueprint
- GET    /api/blueprints            List blueprints
"""

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession
from typing import Optional, List
from loguru import logger

from app.core.database import get_db
from app.core.security import get_current_principal, require_role, UserRole, Principal
from app.core.rate_limit import limiter

from .service import ClusterService
from .schemas import (
    ClusterCreate,
    ClusterUpdate,
    ClusterScale,
    ClusterResponse,
    ClusterListResponse,
    ClusterAgentResponse,
    ClusterHierarchyResponse,
    ClusterStatus,
    ClusterType,
    BlueprintCreate,
    BlueprintUpdate,
    BlueprintResponse
)
from .models import Cluster

router = APIRouter(prefix="/api/clusters", tags=["Cluster System"])


# ===== CLUSTER ENDPOINTS =====

@router.post(
    "",
    response_model=ClusterResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create cluster from blueprint"
)
@limiter.limit("10/minute")
async def create_cluster(
    data: ClusterCreate,
    db: AsyncSession = Depends(get_db),
    principal: Principal = Depends(require_role(UserRole.OPERATOR))
):
    """
    Create a new cluster from a blueprint.

    Requires OPERATOR or ADMIN role.

    Steps:
    1. Validates blueprint exists
    2. Creates cluster DB entry
    3. Spawns agents according to blueprint
    4. Generates manifest files
    5. Returns cluster details

    Example:
    ```json
    {
      "blueprint_id": "marketing-v1",
      "name": "Marketing Q1 2024",
      "type": "department",
      "target_workers": 5
    }
    ```
    """
    try:
        service = ClusterService(db)
        cluster = await service.create_from_blueprint(data)

        logger.info(f"Cluster created: {cluster.id} by {principal.email}")
        return ClusterResponse.model_validate(cluster)

    except ValueError as e:
        logger.warning(f"Cluster creation failed: {e}")
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"Cluster creation error: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Internal server error")


@router.get(
    "",
    response_model=ClusterListResponse,
    summary="List clusters"
)
@limiter.limit("30/minute")
async def list_clusters(
    status: Optional[ClusterStatus] = Query(None),
    type: Optional[ClusterType] = Query(None),
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
    principal: Principal = Depends(get_current_principal)
):
    """List all clusters with optional filtering"""
    service = ClusterService(db)

    offset = (page - 1) * page_size
    clusters = await service.list_clusters(
        status=status,
        type=type,
        offset=offset,
        limit=page_size
    )

    # TODO: Get total count
    total = len(clusters)  # Placeholder

    return ClusterListResponse(
        clusters=[ClusterResponse.model_validate(c) for c in clusters],
        total=total,
        page=page,
        page_size=page_size
    )


@router.get(
    "/{cluster_id}",
    response_model=ClusterResponse,
    summary="Get cluster details"
)
@limiter.limit("60/minute")
async def get_cluster(
    cluster_id: str,
    db: AsyncSession = Depends(get_db),
    principal: Principal = Depends(get_current_principal)
):
    """Get detailed information about a cluster"""
    service = ClusterService(db)
    cluster = await service.get_cluster(cluster_id)

    if not cluster:
        raise HTTPException(status_code=404, detail="Cluster not found")

    # Add agents count
    agents = await service.get_cluster_agents(cluster_id)
    response = ClusterResponse.model_validate(cluster)
    response.agents_count = len(agents)

    return response


@router.put(
    "/{cluster_id}",
    response_model=ClusterResponse,
    summary="Update cluster configuration"
)
@limiter.limit("20/minute")
async def update_cluster(
    cluster_id: str,
    data: ClusterUpdate,
    db: AsyncSession = Depends(get_db),
    principal: Principal = Depends(require_role(UserRole.OPERATOR))
):
    """Update cluster settings (name, description, scaling limits)"""
    try:
        service = ClusterService(db)
        cluster = await service.update_cluster(cluster_id, data)

        logger.info(f"Cluster {cluster_id} updated by {principal.email}")
        return ClusterResponse.model_validate(cluster)

    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        logger.error(f"Cluster update error: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Internal server error")


@router.delete(
    "/{cluster_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete cluster"
)
@limiter.limit("10/minute")
async def delete_cluster(
    cluster_id: str,
    db: AsyncSession = Depends(get_db),
    principal: Principal = Depends(require_role(UserRole.ADMIN))
):
    """
    Soft delete cluster (sets status to DESTROYED).

    Requires ADMIN role.
    """
    service = ClusterService(db)
    deleted = await service.delete_cluster(cluster_id)

    if not deleted:
        raise HTTPException(status_code=404, detail="Cluster not found")

    logger.warning(f"Cluster {cluster_id} deleted by {principal.email}")


# ===== SCALING ENDPOINTS =====

@router.post(
    "/{cluster_id}/scale",
    response_model=ClusterResponse,
    summary="Manual cluster scaling"
)
@limiter.limit("20/minute")
async def scale_cluster(
    cluster_id: str,
    data: ClusterScale,
    db: AsyncSession = Depends(get_db),
    principal: Principal = Depends(require_role(UserRole.OPERATOR))
):
    """
    Manually scale cluster to target worker count.

    Auto-scaling may override this later based on load.
    """
    try:
        service = ClusterService(db)
        cluster = await service.scale_cluster(cluster_id, data)

        logger.info(f"Cluster {cluster_id} scaled to {data.target_workers} by {principal.email}")
        return ClusterResponse.model_validate(cluster)

    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"Scaling error: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Internal server error")


@router.post(
    "/{cluster_id}/hibernate",
    response_model=ClusterResponse,
    summary="Hibernate cluster"
)
@limiter.limit("10/minute")
async def hibernate_cluster(
    cluster_id: str,
    db: AsyncSession = Depends(get_db),
    principal: Principal = Depends(require_role(UserRole.OPERATOR))
):
    """
    Hibernate cluster (stop all workers, keep configuration).

    Can be reactivated later.
    """
    try:
        service = ClusterService(db)
        cluster = await service.hibernate_cluster(cluster_id)

        logger.info(f"Cluster {cluster_id} hibernated by {principal.email}")
        return ClusterResponse.model_validate(cluster)

    except Exception as e:
        logger.error(f"Hibernation error: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Internal server error")


@router.post(
    "/{cluster_id}/reactivate",
    response_model=ClusterResponse,
    summary="Reactivate hibernated cluster"
)
@limiter.limit("10/minute")
async def reactivate_cluster(
    cluster_id: str,
    db: AsyncSession = Depends(get_db),
    principal: Principal = Depends(require_role(UserRole.OPERATOR))
):
    """Wake up hibernated cluster"""
    try:
        service = ClusterService(db)
        cluster = await service.reactivate_cluster(cluster_id)

        logger.info(f"Cluster {cluster_id} reactivated by {principal.email}")
        return ClusterResponse.model_validate(cluster)

    except Exception as e:
        logger.error(f"Reactivation error: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Internal server error")


# ===== AGENT ENDPOINTS =====

@router.get(
    "/{cluster_id}/agents",
    response_model=List[ClusterAgentResponse],
    summary="List cluster agents"
)
@limiter.limit("60/minute")
async def list_cluster_agents(
    cluster_id: str,
    db: AsyncSession = Depends(get_db),
    principal: Principal = Depends(get_current_principal)
):
    """Get all agents in cluster"""
    service = ClusterService(db)
    agents = await service.get_cluster_agents(cluster_id)

    return [ClusterAgentResponse.model_validate(a) for a in agents]


@router.get(
    "/{cluster_id}/hierarchy",
    response_model=ClusterHierarchyResponse,
    summary="Get cluster agent hierarchy"
)
@limiter.limit("30/minute")
async def get_cluster_hierarchy(
    cluster_id: str,
    db: AsyncSession = Depends(get_db),
    principal: Principal = Depends(get_current_principal)
):
    """Get nested agent hierarchy (Supervisor → Leads → Specialists → Workers)"""
    service = ClusterService(db)
    hierarchy = await service.get_cluster_hierarchy(cluster_id)

    return hierarchy


# ===== BLUEPRINT ENDPOINTS =====

blueprints_router = APIRouter(prefix="/api/blueprints", tags=["Blueprints"])


@blueprints_router.post(
    "",
    response_model=BlueprintResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Upload new blueprint"
)
@limiter.limit("5/minute")
async def create_blueprint(
    data: BlueprintCreate,
    db: AsyncSession = Depends(get_db),
    principal: Principal = Depends(require_role(UserRole.ADMIN))
):
    """
    Upload a new cluster blueprint.

    Requires ADMIN role.

    Blueprint must be valid YAML matching schema.
    """
    # TODO: Implement (Max's Task 3.2)
    raise HTTPException(status_code=501, detail="Not implemented yet")


@blueprints_router.get(
    "",
    response_model=List[BlueprintResponse],
    summary="List blueprints"
)
@limiter.limit("30/minute")
async def list_blueprints(
    active_only: bool = Query(True),
    db: AsyncSession = Depends(get_db),
    principal: Principal = Depends(get_current_principal)
):
    """List all available blueprints"""
    # TODO: Implement (Max's Task 3.2)
    raise HTTPException(status_code=501, detail="Not implemented yet")


@blueprints_router.get(
    "/{blueprint_id}",
    response_model=BlueprintResponse,
    summary="Get blueprint details"
)
@limiter.limit("60/minute")
async def get_blueprint(
    blueprint_id: str,
    include_yaml: bool = Query(False),
    db: AsyncSession = Depends(get_db),
    principal: Principal = Depends(get_current_principal)
):
    """Get blueprint details (optionally with full YAML)"""
    # TODO: Implement (Max's Task 3.2)
    raise HTTPException(status_code=501, detail="Not implemented yet")
