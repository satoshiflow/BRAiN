"""
Workspace API Router (Sprint 9-C)

Multi-tenant workspace and project management endpoints.
Workspace-scoped pipeline execution for tenant isolation.
"""

from fastapi import APIRouter, HTTPException, Depends
from typing import Dict, Any, List, Optional
from loguru import logger
from sqlalchemy.ext.asyncio import AsyncSession
import json
import aiofiles
import aiofiles.os
from pathlib import Path

from app.core.auth_deps import require_auth, get_current_principal, Principal
from app.core.database import get_db
from app.modules.autonomous_pipeline.workspace_schemas import (
    Workspace,
    Project,
    WorkspaceCreateRequest,
    WorkspaceUpdateRequest,
    ProjectCreateRequest,
    ProjectUpdateRequest,
    WorkspaceStats,
    ProjectStats,
    WorkspaceStatus,
    ProjectStatus,
)
from app.modules.autonomous_pipeline.workspace_service import (
    WorkspaceNotFoundError,
    ProjectNotFoundError,
    QuotaExceededError,
)
from app.modules.autonomous_pipeline.workspace_service_db import DatabaseWorkspaceService
from app.modules.autonomous_pipeline.rate_limiting import (
    workspace_limiter as limiter,
    PIPELINE_EXECUTE_LIMIT,
)

# Sprint 9-C: Workspace-scoped execution
from app.modules.autonomous_pipeline.schemas import ExecutionGraphSpec
from app.modules.autonomous_pipeline.execution_graph import create_execution_graph
from app.modules.autonomous_pipeline.run_contract import get_run_contract_service


router = APIRouter(
    prefix="/api/workspaces",
    tags=["workspaces"],
    dependencies=[Depends(require_auth)]
)


# ============================================================================
# Helper Functions
# ============================================================================

async def _get_directory_size(directory: Path) -> int:
    """
    Asynchronously calculate total size of directory in bytes.

    Args:
        directory: Path to directory

    Returns:
        Total size in bytes
    """
    total_size = 0
    try:
        for root, dirs, files in await aiofiles.os.walk(directory):
            for filename in files:
                filepath = Path(root) / filename
                try:
                    size = (await aiofiles.os.stat(filepath)).st_size
                    total_size += size
                except (OSError, FileNotFoundError):
                    # Skip files that can't be accessed
                    logger.debug(f"Could not stat file: {filepath}")
    except (OSError, FileNotFoundError):
        # Skip if directory doesn't exist
        logger.debug(f"Could not walk directory: {directory}")

    return total_size


def _verify_workspace_ownership(workspace: Workspace, principal: Principal, allow_admin: bool = True) -> None:
    """
    Verify that principal owns the workspace.

    Raises HTTPException(403) if not authorized.
    Admin users can always access if allow_admin=True.
    """
    # Allow admins to access any workspace (unless explicitly disabled)
    if allow_admin and principal.role and "admin" in str(principal.role).lower():
        return

    # Check ownership: principal must be the owner
    if principal.principal_id != workspace.owner_id:
        raise HTTPException(
            status_code=403,
            detail="You are not authorized to access this workspace"
        )


# ============================================================================
# Workspace Management
# ============================================================================

@router.get("/info")
async def get_workspaces_info():
    """
    Get workspace system information.

    Returns basic information about the multi-tenancy system.
    """
    return {
        "name": "BRAiN Workspace Management",
        "version": "1.0.0",
        "description": "Multi-tenant workspace and project isolation",
        "sprint": "Sprint 9-C",
        "features": [
            "Hard workspace isolation",
            "Project management",
            "Quota enforcement",
            "Workspace-scoped pipeline execution",
            "Default workspace for backward compatibility",
        ],
        "endpoints": [
            "GET /api/workspaces - List workspaces",
            "POST /api/workspaces - Create workspace",
            "GET /api/workspaces/{workspace_id} - Get workspace",
            "PUT /api/workspaces/{workspace_id} - Update workspace",
            "DELETE /api/workspaces/{workspace_id} - Delete workspace",
            "GET /api/workspaces/{workspace_id}/stats - Workspace statistics",
            "GET /api/workspaces/{workspace_id}/projects - List projects",
            "POST /api/workspaces/{workspace_id}/projects - Create project",
            "POST /api/workspaces/{workspace_id}/pipeline/run - Execute pipeline (workspace-scoped)",
        ],
    }


@router.get("")
async def list_workspaces(
    principal: Principal = Depends(get_current_principal),
    status: Optional[WorkspaceStatus] = None,
    owner_id: Optional[str] = None,
) -> List[Workspace]:
    """
    List workspaces that you own.

    **Query Parameters:**
    - status: Filter by status (active, suspended, archived)
    - owner_id: Filter by owner ID (admins only)

    **Example:**
    ```bash
    GET /api/workspaces?status=active
    ```

    **Note:** Non-admin users can only see their own workspaces.
    """
    try:
        service = get_workspace_service()

        # Non-admin users can only see their own workspaces
        effective_owner_id = owner_id
        if not principal.role or "admin" not in str(principal.role).lower():
            effective_owner_id = principal.principal_id

        workspaces = service.list_workspaces(status=status, owner_id=effective_owner_id)
        return workspaces

    except Exception as e:
        logger.error(f"Failed to list workspaces: {e}")
        raise HTTPException(status_code=500, detail="Failed to list workspaces")


@router.post("")
async def create_workspace(
    request: WorkspaceCreateRequest,
    principal: Principal = Depends(get_current_principal),
) -> Workspace:
    """
    Create new workspace.

    **Example Request:**
    ```json
    {
      "name": "Acme Corp",
      "slug": "acme-corp",
      "description": "Production workspace for Acme Corporation",
      "max_projects": 50,
      "max_runs_per_day": 500,
      "max_storage_gb": 50.0
    }
    ```

    **Note:** The created workspace will be owned by the authenticated user.
    """
    try:
        service = get_workspace_service()

        # Set owner_id from principal if not explicitly provided
        if not request.owner_id:
            request.owner_id = principal.principal_id

        workspace = service.create_workspace(request)

        logger.info(
            f"[Workspace] Created by {principal.principal_id}: {workspace.workspace_id} "
            f"(name={workspace.name})"
        )

        return workspace

    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

    except Exception as e:
        logger.error(f"Failed to create workspace: {e}")
        raise HTTPException(status_code=500, detail="Failed to create workspace")


@router.get("/{workspace_id}")
async def get_workspace(
    workspace_id: str,
    principal: Principal = Depends(get_current_principal),
) -> Workspace:
    """
    Get workspace by ID.

    **Example:**
    ```bash
    GET /api/workspaces/ws_01j12k34m56n78p90qrs
    ```

    **Note:** You must own the workspace or be an admin.
    """
    try:
        service = get_workspace_service()
        workspace = service.get_workspace(workspace_id)

        # Verify ownership
        _verify_workspace_ownership(workspace, principal)

        return workspace

    except WorkspaceNotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e))

    except HTTPException:
        raise

    except Exception as e:
        logger.error(f"Failed to get workspace: {e}")
        raise HTTPException(status_code=500, detail="Failed to get workspace")


@router.put("/{workspace_id}")
async def update_workspace(
    workspace_id: str,
    request: WorkspaceUpdateRequest,
    principal: Principal = Depends(get_current_principal),
) -> Workspace:
    """
    Update workspace.

    **Example Request:**
    ```json
    {
      "name": "Acme Corporation (Updated)",
      "max_runs_per_day": 1000
    }
    ```

    **Note:** You must own the workspace or be an admin.
    """
    try:
        service = get_workspace_service()
        workspace = service.get_workspace(workspace_id)

        # Verify ownership
        _verify_workspace_ownership(workspace, principal)

        workspace = service.update_workspace(workspace_id, request)

        logger.info(f"[Workspace] Updated by {principal.principal_id}: {workspace_id}")

        return workspace

    except WorkspaceNotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e))

    except HTTPException:
        raise

    except Exception as e:
        logger.error(f"Failed to update workspace: {e}")
        raise HTTPException(status_code=500, detail="Failed to update workspace")


@router.delete("/{workspace_id}")
async def delete_workspace(
    workspace_id: str,
    principal: Principal = Depends(get_current_principal),
) -> Dict[str, Any]:
    """
    Delete workspace (soft delete - archive).

    **Example:**
    ```bash
    DELETE /api/workspaces/ws_01j12k34m56n78p90qrs
    ```

    **Note:** You must own the workspace or be an admin.
    """
    try:
        service = get_workspace_service()
        workspace = service.get_workspace(workspace_id)

        # Verify ownership
        _verify_workspace_ownership(workspace, principal)

        success = service.delete_workspace(workspace_id)

        logger.info(f"[Workspace] Archived by {principal.principal_id}: {workspace_id}")

        return {"success": success, "workspace_id": workspace_id, "message": "Workspace archived"}

    except WorkspaceNotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e))

    except HTTPException:
        raise

    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

    except Exception as e:
        logger.error(f"Failed to delete workspace: {e}")
        raise HTTPException(status_code=500, detail="Failed to delete workspace")


@router.get("/{workspace_id}/stats")
async def get_workspace_stats(
    workspace_id: str,
    principal: Principal = Depends(get_current_principal),
) -> WorkspaceStats:
    """
    Get workspace statistics.

    **Returns:**
    - Total projects
    - Active projects
    - Total runs
    - Runs today
    - Storage usage
    - Quota usage percentage

    **Example:**
    ```bash
    GET /api/workspaces/ws_01j12k34m56n78p90qrs/stats
    ```

    **Note:** You must own the workspace or be an admin.
    """
    try:
        service = get_workspace_service()

        # Verify workspace exists and you own it
        workspace = service.get_workspace(workspace_id)
        _verify_workspace_ownership(workspace, principal)

        stats = service.get_workspace_stats(workspace_id)
        return stats

    except WorkspaceNotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e))

    except HTTPException:
        raise

    except Exception as e:
        logger.error(f"Failed to get workspace stats: {e}")
        raise HTTPException(status_code=500, detail="Failed to get workspace stats")


# ============================================================================
# Project Management
# ============================================================================

@router.get("/{workspace_id}/projects")
async def list_projects(
    workspace_id: str,
    principal: Principal = Depends(get_current_principal),
    status: Optional[ProjectStatus] = None,
) -> List[Project]:
    """
    List projects in workspace.

    **Query Parameters:**
    - status: Filter by status (active, paused, completed, archived)

    **Example:**
    ```bash
    GET /api/workspaces/ws_01j12k34m56n78p90qrs/projects?status=active
    ```

    **Note:** You must own the workspace or be an admin.
    """
    try:
        service = get_workspace_service()

        # Verify workspace exists and you own it
        workspace = service.get_workspace(workspace_id)
        _verify_workspace_ownership(workspace, principal)

        # List projects
        projects = service.list_projects(workspace_id=workspace_id, status=status)
        return projects

    except WorkspaceNotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e))

    except HTTPException:
        raise

    except Exception as e:
        logger.error(f"Failed to list projects: {e}")
        raise HTTPException(status_code=500, detail="Failed to list projects")


@router.post("/{workspace_id}/projects")
async def create_project(
    workspace_id: str,
    request: ProjectCreateRequest,
    principal: Principal = Depends(get_current_principal),
) -> Project:
    """
    Create project in workspace.

    **Example Request:**
    ```json
    {
      "name": "E-Commerce Platform",
      "slug": "ecommerce-platform",
      "description": "Main e-commerce business automation project",
      "default_budget": {
        "max_steps": 50,
        "max_duration_seconds": 300
      }
    }
    ```

    **Note:** You must own the workspace or be an admin.
    """
    try:
        service = get_workspace_service()

        # Verify workspace exists and you own it
        workspace = service.get_workspace(workspace_id)
        _verify_workspace_ownership(workspace, principal)

        project = service.create_project(workspace_id, request)

        logger.info(
            f"[Workspace] Project created by {principal.principal_id}: {project.project_id} "
            f"(workspace={workspace_id}, name={project.name})"
        )

        return project

    except WorkspaceNotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e))

    except HTTPException:
        raise

    except QuotaExceededError as e:
        raise HTTPException(status_code=429, detail=str(e))

    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

    except Exception as e:
        logger.error(f"Failed to create project: {e}")
        raise HTTPException(status_code=500, detail="Failed to create project")


@router.get("/{workspace_id}/projects/{project_id}")
async def get_project(
    workspace_id: str,
    project_id: str,
    principal: Principal = Depends(get_current_principal),
) -> Project:
    """
    Get project by ID.

    **Example:**
    ```bash
    GET /api/workspaces/ws_xxx/projects/proj_yyy
    ```

    **Note:** You must own the workspace or be an admin.
    """
    try:
        service = get_workspace_service()

        # Verify workspace exists and you own it
        workspace = service.get_workspace(workspace_id)
        _verify_workspace_ownership(workspace, principal)

        project = service.get_project(project_id)

        # Verify project belongs to workspace
        if project.workspace_id != workspace_id:
            raise HTTPException(
                status_code=404,
                detail=f"Project {project_id} not found in workspace {workspace_id}"
            )

        return project

    except ProjectNotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e))

    except HTTPException:
        raise

    except Exception as e:
        logger.error(f"Failed to get project: {e}")
        raise HTTPException(status_code=500, detail="Failed to get project")


@router.put("/{workspace_id}/projects/{project_id}")
async def update_project(
    workspace_id: str,
    project_id: str,
    request: ProjectUpdateRequest,
    principal: Principal = Depends(get_current_principal),
) -> Project:
    """
    Update project.

    **Example Request:**
    ```json
    {
      "name": "E-Commerce Platform (Updated)",
      "status": "paused"
    }
    ```

    **Note:** You must own the workspace or be an admin.
    """
    try:
        service = get_workspace_service()

        # Verify workspace exists and you own it
        workspace = service.get_workspace(workspace_id)
        _verify_workspace_ownership(workspace, principal)

        project = service.get_project(project_id)

        # Verify project belongs to workspace
        if project.workspace_id != workspace_id:
            raise HTTPException(
                status_code=404,
                detail=f"Project {project_id} not found in workspace {workspace_id}"
            )

        project = service.update_project(project_id, request)

        logger.info(f"[Workspace] Project updated by {principal.principal_id}: {project_id}")

        return project

    except ProjectNotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e))

    except HTTPException:
        raise

    except Exception as e:
        logger.error(f"Failed to update project: {e}")
        raise HTTPException(status_code=500, detail="Failed to update project")


@router.delete("/{workspace_id}/projects/{project_id}")
async def delete_project(
    workspace_id: str,
    project_id: str,
    principal: Principal = Depends(get_current_principal),
) -> Dict[str, Any]:
    """
    Delete project (soft delete - archive).

    **Example:**
    ```bash
    DELETE /api/workspaces/ws_xxx/projects/proj_yyy
    ```

    **Note:** You must own the workspace or be an admin.
    """
    try:
        service = get_workspace_service()

        # Verify workspace exists and you own it
        workspace = service.get_workspace(workspace_id)
        _verify_workspace_ownership(workspace, principal)

        project = service.get_project(project_id)

        # Verify project belongs to workspace
        if project.workspace_id != workspace_id:
            raise HTTPException(
                status_code=404,
                detail=f"Project {project_id} not found in workspace {workspace_id}"
            )

        success = service.delete_project(project_id)

        logger.info(f"[Workspace] Project archived by {principal.principal_id}: {project_id}")

        return {"success": success, "project_id": project_id, "message": "Project archived"}

    except ProjectNotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e))

    except HTTPException:
        raise

    except Exception as e:
        logger.error(f"Failed to delete project: {e}")
        raise HTTPException(status_code=500, detail="Failed to delete project")


@router.get("/{workspace_id}/projects/{project_id}/stats")
async def get_project_stats(
    workspace_id: str,
    project_id: str,
    principal: Principal = Depends(get_current_principal),
) -> ProjectStats:
    """
    Get project statistics.

    **Returns:**
    - Total runs
    - Successful/failed runs
    - Success rate
    - Average duration
    - Last run timestamp

    **Example:**
    ```bash
    GET /api/workspaces/ws_xxx/projects/proj_yyy/stats
    ```

    **Note:** You must own the workspace or be an admin.
    """
    try:
        service = get_workspace_service()

        # Verify workspace exists and you own it
        workspace = service.get_workspace(workspace_id)
        _verify_workspace_ownership(workspace, principal)

        project = service.get_project(project_id)

        # Verify project belongs to workspace
        if project.workspace_id != workspace_id:
            raise HTTPException(
                status_code=404,
                detail=f"Project {project_id} not found in workspace {workspace_id}"
            )

        stats = service.get_project_stats(project_id)
        return stats

    except ProjectNotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e))

    except HTTPException:
        raise

    except Exception as e:
        logger.error(f"Failed to get project stats: {e}")
        raise HTTPException(status_code=500, detail="Failed to get project stats")


# ============================================================================
# Workspace-Scoped Pipeline Execution
# ============================================================================

@router.post("/{workspace_id}/pipeline/run")
@limiter.limit(PIPELINE_EXECUTE_LIMIT)
async def execute_workspace_pipeline(
    workspace_id: str,
    graph_spec: ExecutionGraphSpec,
    principal: Principal = Depends(get_current_principal),
    db: AsyncSession = Depends(get_db),
    project_id: Optional[str] = None,
) -> Dict[str, Any]:
    """
    Execute pipeline in workspace context (workspace-scoped).

    **Rate Limiting:**
    - 10 requests per minute per IP address
    - Returns 429 (Too Many Requests) if exceeded

    **Quota Enforcement:**
    - Enforces max_runs_per_day limit per workspace
    - Returns 429 if daily quota exceeded
    - Enforces max_storage_gb limit for evidence/contracts

    **Isolation:**
    - Secrets scoped to workspace
    - Evidence packs saved in workspace storage
    - Run contracts saved in workspace storage
    - Persisted to PostgreSQL database

    **Example Request:**
    ```json
    {
      "graph_id": "graph_123",
      "business_intent_id": "intent_abc",
      "nodes": [...],
      "dry_run": true
    }
    ```

    **Query Parameters:**
    - project_id: Optional project ID for grouping

    **Example:**
    ```bash
    POST /api/workspaces/ws_xxx/pipeline/run?project_id=proj_yyy
    ```

    **Note:** You must own the workspace or be an admin.
    """
    try:
        db_service = DatabaseWorkspaceService()

        # Verify workspace exists and you own it
        workspace = await db_service.get_workspace(db, workspace_id)
        _verify_workspace_ownership(workspace, principal)

        # Verify workspace is active
        if workspace.status != WorkspaceStatus.ACTIVE.value:
            raise HTTPException(
                status_code=403,
                detail=f"Workspace {workspace_id} is not active (status={workspace.status})"
            )

        # ====================================================================
        # QUOTA ENFORCEMENT: Check daily run limit
        # ====================================================================
        runs_today = await db_service.get_workspace_run_count_today(db, workspace_id)
        if runs_today >= workspace.max_runs_per_day:
            logger.warning(
                f"[Workspace] Daily quota exceeded for {workspace_id}: "
                f"{runs_today}/{workspace.max_runs_per_day} runs"
            )
            raise HTTPException(
                status_code=429,
                detail=f"Daily pipeline execution quota exceeded ({runs_today}/{workspace.max_runs_per_day}). "
                       f"Please try again tomorrow."
            )

        # Verify project if specified
        if project_id:
            project = await db_service.get_project(db, project_id)
            if project.workspace_id != workspace_id:
                raise HTTPException(
                    status_code=400,
                    detail=f"Project {project_id} does not belong to workspace {workspace_id}"
                )
            if project.status != ProjectStatus.ACTIVE.value:
                raise HTTPException(
                    status_code=403,
                    detail=f"Project {project_id} is not active (status={project.status})"
                )

        # Get workspace-isolated storage paths
        from pathlib import Path
        storage_path = Path(workspace.storage_path) if workspace.storage_path else Path("storage/workspaces") / workspace_id
        contracts_path = storage_path / "contracts"
        evidence_path = storage_path / "evidence"
        contracts_path.mkdir(parents=True, exist_ok=True)
        evidence_path.mkdir(parents=True, exist_ok=True)

        logger.info(
            f"[Workspace] Executing pipeline in workspace {workspace_id} "
            f"(project={project_id}, dry_run={graph_spec.dry_run}, runs_today={runs_today})"
        )

        # Create run contract (workspace-scoped)
        run_contract_service = get_run_contract_service()
        run_contract = run_contract_service.create_contract(
            graph_spec=graph_spec,
            dry_run=graph_spec.dry_run,
        )

        # Execute graph
        graph = create_execution_graph(graph_spec)
        result = await graph.execute()

        # Finalize contract
        run_contract = run_contract_service.finalize_contract(run_contract, result)

        # ====================================================================
        # QUOTA ENFORCEMENT: Check storage limit (ASYNC)
        # ====================================================================
        contract_data = json.dumps(run_contract.model_dump(), default=str)
        contract_size_mb = len(contract_data.encode('utf-8')) / (1024 * 1024)

        # Calculate current storage (async)
        total_size = await _get_directory_size(storage_path)
        total_size_gb = total_size / (1024 ** 3)
        new_total_size_gb = total_size_gb + contract_size_mb / 1024

        if new_total_size_gb > workspace.max_storage_gb:
            logger.warning(
                f"[Workspace] Storage quota exceeded for {workspace_id}: "
                f"{new_total_size_gb:.2f}GB / {workspace.max_storage_gb}GB"
            )
            raise HTTPException(
                status_code=429,
                detail=f"Storage quota exceeded ({new_total_size_gb:.2f}GB / {workspace.max_storage_gb}GB). "
                       f"Please clean up old evidence and contracts."
            )

        # Save contract in workspace storage (ASYNC)
        contract_file_path = contracts_path / f"{run_contract.contract_id}.json"
        async with aiofiles.open(contract_file_path, "w") as f:
            await f.write(contract_data)

        logger.info(
            f"[Workspace] Pipeline execution completed: {result.graph_id} "
            f"(workspace={workspace_id}, success={result.success}, contract={run_contract.contract_id}, "
            f"storage={new_total_size_gb:.2f}GB)"
        )

        return {
            "execution_result": result.model_dump(),
            "run_contract": run_contract.model_dump(),
            "workspace_id": workspace_id,
            "project_id": project_id,
            "contract_path": str(contract_file_path),
            "quota_status": {
                "runs_today": runs_today + 1,
                "max_runs_per_day": workspace.max_runs_per_day,
                "storage_used_gb": new_total_size_gb,
                "max_storage_gb": workspace.max_storage_gb,
            },
            "isolated_storage": {
                "contracts": str(contracts_path),
                "evidence": str(evidence_path),
            },
        }

    except WorkspaceNotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e))

    except ProjectNotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e))

    except HTTPException:
        raise  # Re-raise HTTP exceptions

    except Exception as e:
        logger.error(f"Workspace pipeline execution failed: {e}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail="Workspace pipeline execution failed"
        )
