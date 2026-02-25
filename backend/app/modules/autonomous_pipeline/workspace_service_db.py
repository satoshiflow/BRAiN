"""
Database-backed Workspace Service (Sprint 9-C)

Uses SQLAlchemy AsyncSession for persistent multi-tenant workspace management.
Replaces in-memory storage with PostgreSQL backend.
"""

from typing import List, Optional
from datetime import datetime
from pathlib import Path
from loguru import logger
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from sqlalchemy.orm import joinedload

from app.core.database import Base
from app.models.autonomous_pipeline import (
    Workspace as WorkspaceModel,
    Project as ProjectModel,
    RunContract as RunContractModel,
    WorkspaceStatus,
    ProjectStatus,
)
from app.modules.autonomous_pipeline.workspace_schemas import (
    Workspace,
    Project,
    WorkspaceCreateRequest,
    WorkspaceUpdateRequest,
    ProjectCreateRequest,
    ProjectUpdateRequest,
    WorkspaceStats,
    ProjectStats,
)


class WorkspaceNotFoundError(Exception):
    """Raised when workspace is not found."""
    pass


class ProjectNotFoundError(Exception):
    """Raised when project is not found."""
    pass


class QuotaExceededError(Exception):
    """Raised when workspace quota is exceeded."""
    pass


class DatabaseWorkspaceService:
    """
    Database-backed workspace isolation and management service.

    Uses PostgreSQL with SQLAlchemy AsyncSession for:
    - Hard workspace isolation
    - Project management
    - Quota enforcement
    - Audit trails
    """

    # Storage directories for evidence/contracts
    WORKSPACES_DIR = Path("storage/workspaces")
    DEFAULT_WORKSPACE_ID = "default"

    async def create_workspace(
        self,
        db: AsyncSession,
        request: WorkspaceCreateRequest,
    ) -> Workspace:
        """
        Create new workspace in database.

        Args:
            db: AsyncSession for database operations
            request: Workspace creation request

        Returns:
            Created workspace

        Raises:
            ValueError: If slug already exists
        """
        # Check slug uniqueness
        stmt = select(WorkspaceModel).where(WorkspaceModel.slug == request.slug)
        result = await db.execute(stmt)
        if result.scalars().first():
            raise ValueError(f"Workspace slug already exists: {request.slug}")

        # Generate workspace ID
        timestamp_ms = int(datetime.utcnow().timestamp() * 1000)
        workspace_id = f"ws_{timestamp_ms}_{request.slug}"

        # Create storage path
        storage_path = self.WORKSPACES_DIR / workspace_id
        storage_path.mkdir(parents=True, exist_ok=True)

        # Create subdirectories
        (storage_path / "secrets").mkdir(exist_ok=True)
        (storage_path / "evidence").mkdir(exist_ok=True)
        (storage_path / "contracts").mkdir(exist_ok=True)
        (storage_path / "projects").mkdir(exist_ok=True)

        # Create workspace model
        workspace_model = WorkspaceModel(
            workspace_id=workspace_id,
            name=request.name,
            slug=request.slug,
            description=request.description,
            status=WorkspaceStatus.ACTIVE.value,
            owner_id=request.owner_id,
            created_by=request.owner_id,
            storage_path=str(storage_path),
            max_projects=request.max_projects,
            max_runs_per_day=request.max_runs_per_day,
            max_storage_gb=request.max_storage_gb,
            settings=request.settings or {},
            tags=request.tags or [],
        )

        db.add(workspace_model)
        await db.commit()
        await db.refresh(workspace_model)

        logger.info(f"[Workspace] Created in DB: {workspace_id} (slug={request.slug})")

        return self._model_to_schema(workspace_model)

    async def get_workspace(
        self,
        db: AsyncSession,
        workspace_id: str,
    ) -> Workspace:
        """
        Get workspace by ID from database.

        Args:
            db: AsyncSession
            workspace_id: Workspace ID

        Returns:
            Workspace

        Raises:
            WorkspaceNotFoundError: If not found
        """
        stmt = select(WorkspaceModel).where(
            WorkspaceModel.workspace_id == workspace_id
        )
        result = await db.execute(stmt)
        workspace_model = result.scalars().first()

        if not workspace_model:
            raise WorkspaceNotFoundError(f"Workspace not found: {workspace_id}")

        return self._model_to_schema(workspace_model)

    async def get_workspace_by_slug(
        self,
        db: AsyncSession,
        slug: str,
    ) -> Optional[Workspace]:
        """
        Get workspace by slug from database.

        Args:
            db: AsyncSession
            slug: Workspace slug

        Returns:
            Workspace or None
        """
        stmt = select(WorkspaceModel).where(WorkspaceModel.slug == slug)
        result = await db.execute(stmt)
        workspace_model = result.scalars().first()

        return self._model_to_schema(workspace_model) if workspace_model else None

    async def list_workspaces(
        self,
        db: AsyncSession,
        status: Optional[str] = None,
        owner_id: Optional[str] = None,
    ) -> List[Workspace]:
        """
        List workspaces with optional filters.

        Args:
            db: AsyncSession
            status: Filter by status
            owner_id: Filter by owner ID

        Returns:
            List of workspaces
        """
        stmt = select(WorkspaceModel)

        if status:
            stmt = stmt.where(WorkspaceModel.status == status)

        if owner_id:
            stmt = stmt.where(WorkspaceModel.owner_id == owner_id)

        result = await db.execute(stmt)
        workspaces = result.scalars().all()

        return [self._model_to_schema(ws) for ws in workspaces]

    async def update_workspace(
        self,
        db: AsyncSession,
        workspace_id: str,
        request: WorkspaceUpdateRequest,
    ) -> Workspace:
        """
        Update workspace in database.

        Args:
            db: AsyncSession
            workspace_id: Workspace ID
            request: Update request

        Returns:
            Updated workspace

        Raises:
            WorkspaceNotFoundError: If not found
        """
        workspace_model = await self._get_workspace_model(db, workspace_id)

        # Update fields
        if request.name is not None:
            workspace_model.name = request.name
        if request.description is not None:
            workspace_model.description = request.description
        if request.status is not None:
            workspace_model.status = request.status.value
        if request.max_projects is not None:
            workspace_model.max_projects = request.max_projects
        if request.max_runs_per_day is not None:
            workspace_model.max_runs_per_day = request.max_runs_per_day
        if request.max_storage_gb is not None:
            workspace_model.max_storage_gb = request.max_storage_gb
        if request.settings is not None:
            workspace_model.settings = request.settings
        if request.tags is not None:
            workspace_model.tags = request.tags

        workspace_model.updated_at = datetime.utcnow()

        await db.commit()
        await db.refresh(workspace_model)

        logger.info(f"[Workspace] Updated in DB: {workspace_id}")

        return self._model_to_schema(workspace_model)

    async def delete_workspace(
        self,
        db: AsyncSession,
        workspace_id: str,
    ) -> bool:
        """
        Delete workspace (soft delete - archive).

        Args:
            db: AsyncSession
            workspace_id: Workspace ID

        Returns:
            True if deleted

        Raises:
            WorkspaceNotFoundError: If not found
            ValueError: If trying to delete default workspace
        """
        if workspace_id == self.DEFAULT_WORKSPACE_ID:
            raise ValueError("Cannot delete default workspace")

        workspace_model = await self._get_workspace_model(db, workspace_id)
        workspace_model.status = WorkspaceStatus.ARCHIVED.value
        workspace_model.updated_at = datetime.utcnow()

        await db.commit()

        logger.info(f"[Workspace] Archived in DB: {workspace_id}")

        return True

    async def create_project(
        self,
        db: AsyncSession,
        workspace_id: str,
        request: ProjectCreateRequest,
    ) -> Project:
        """
        Create project in workspace.

        Args:
            db: AsyncSession
            workspace_id: Parent workspace ID
            request: Project creation request

        Returns:
            Created project

        Raises:
            WorkspaceNotFoundError: If workspace not found
            QuotaExceededError: If max projects exceeded
            ValueError: If slug already exists
        """
        # Verify workspace exists
        workspace_model = await self._get_workspace_model(db, workspace_id)

        # Check quota
        stmt = select(ProjectModel).where(
            ProjectModel.workspace_id == workspace_id,
            ProjectModel.status != ProjectStatus.ARCHIVED.value,
        )
        result = await db.execute(stmt)
        active_projects = result.scalars().all()

        if len(active_projects) >= workspace_model.max_projects:
            raise QuotaExceededError(
                f"Workspace {workspace_id} has reached max projects limit: {workspace_model.max_projects}"
            )

        # Check slug uniqueness within workspace
        for project in active_projects:
            if project.slug == request.slug:
                raise ValueError(
                    f"Project slug already exists in workspace: {request.slug}"
                )

        # Generate project ID
        timestamp_ms = int(datetime.utcnow().timestamp() * 1000)
        project_id = f"proj_{timestamp_ms}_{request.slug}"

        # Create project model
        project_model = ProjectModel(
            project_id=project_id,
            workspace_id=workspace_id,
            name=request.name,
            slug=request.slug,
            description=request.description,
            status=ProjectStatus.ACTIVE.value,
            created_by=request.created_by,
            default_budget=request.default_budget,
            default_policy=request.default_policy,
            tags=request.tags or [],
        )

        db.add(project_model)
        await db.commit()
        await db.refresh(project_model)

        logger.info(
            f"[Workspace] Project created in DB: {project_id} "
            f"(workspace={workspace_id}, slug={request.slug})"
        )

        return self._project_model_to_schema(project_model)

    async def get_project(
        self,
        db: AsyncSession,
        project_id: str,
    ) -> Project:
        """
        Get project by ID.

        Args:
            db: AsyncSession
            project_id: Project ID

        Returns:
            Project

        Raises:
            ProjectNotFoundError: If not found
        """
        stmt = select(ProjectModel).where(ProjectModel.project_id == project_id)
        result = await db.execute(stmt)
        project_model = result.scalars().first()

        if not project_model:
            raise ProjectNotFoundError(f"Project not found: {project_id}")

        return self._project_model_to_schema(project_model)

    async def list_projects(
        self,
        db: AsyncSession,
        workspace_id: Optional[str] = None,
        status: Optional[str] = None,
    ) -> List[Project]:
        """
        List projects with optional filters.

        Args:
            db: AsyncSession
            workspace_id: Filter by workspace
            status: Filter by status

        Returns:
            List of projects
        """
        stmt = select(ProjectModel)

        if workspace_id:
            stmt = stmt.where(ProjectModel.workspace_id == workspace_id)

        if status:
            stmt = stmt.where(ProjectModel.status == status)

        result = await db.execute(stmt)
        projects = result.scalars().all()

        return [self._project_model_to_schema(p) for p in projects]

    async def update_project(
        self,
        db: AsyncSession,
        project_id: str,
        request: ProjectUpdateRequest,
    ) -> Project:
        """
        Update project.

        Args:
            db: AsyncSession
            project_id: Project ID
            request: Update request

        Returns:
            Updated project

        Raises:
            ProjectNotFoundError: If not found
        """
        project_model = await self._get_project_model(db, project_id)

        # Update fields
        if request.name is not None:
            project_model.name = request.name
        if request.description is not None:
            project_model.description = request.description
        if request.status is not None:
            project_model.status = request.status.value
        if request.default_budget is not None:
            project_model.default_budget = request.default_budget
        if request.default_policy is not None:
            project_model.default_policy = request.default_policy
        if request.tags is not None:
            project_model.tags = request.tags

        project_model.updated_at = datetime.utcnow()

        await db.commit()
        await db.refresh(project_model)

        logger.info(f"[Workspace] Project updated in DB: {project_id}")

        return self._project_model_to_schema(project_model)

    async def delete_project(
        self,
        db: AsyncSession,
        project_id: str,
    ) -> bool:
        """
        Delete project (soft delete - archive).

        Args:
            db: AsyncSession
            project_id: Project ID

        Returns:
            True if deleted

        Raises:
            ProjectNotFoundError: If not found
        """
        project_model = await self._get_project_model(db, project_id)
        project_model.status = ProjectStatus.ARCHIVED.value
        project_model.updated_at = datetime.utcnow()

        await db.commit()

        logger.info(f"[Workspace] Project archived in DB: {project_id}")

        return True

    async def get_workspace_stats(
        self,
        db: AsyncSession,
        workspace_id: str,
    ) -> WorkspaceStats:
        """
        Get workspace statistics.

        Args:
            db: AsyncSession
            workspace_id: Workspace ID

        Returns:
            Workspace statistics

        Raises:
            WorkspaceNotFoundError: If not found
        """
        workspace_model = await self._get_workspace_model(db, workspace_id)

        # Get projects
        stmt = select(ProjectModel).where(ProjectModel.workspace_id == workspace_id)
        result = await db.execute(stmt)
        projects = result.scalars().all()

        active_projects = [
            p for p in projects
            if p.status == ProjectStatus.ACTIVE.value
        ]

        # Calculate totals
        total_runs = sum(p.total_runs for p in projects)

        # Estimate storage usage (simplified)
        storage_used_gb = 0.0
        try:
            storage_path = Path(workspace_model.storage_path) if workspace_model.storage_path else None
            if storage_path and storage_path.exists():
                total_bytes = sum(
                    f.stat().st_size
                    for f in storage_path.rglob("*")
                    if f.is_file()
                )
                storage_used_gb = total_bytes / (1024 ** 3)
        except Exception as e:
            logger.warning(f"Failed to calculate storage usage: {e}")

        # Calculate quota usage
        quota_usage_percent = (storage_used_gb / workspace_model.max_storage_gb) * 100.0

        return WorkspaceStats(
            workspace_id=workspace_id,
            total_projects=len(projects),
            active_projects=len(active_projects),
            total_runs=total_runs,
            runs_today=0,  # TODO: Track daily runs with timestamps
            storage_used_gb=storage_used_gb,
            storage_limit_gb=workspace_model.max_storage_gb,
            quota_usage_percent=quota_usage_percent,
        )

    async def get_project_stats(
        self,
        db: AsyncSession,
        project_id: str,
    ) -> ProjectStats:
        """
        Get project statistics.

        Args:
            db: AsyncSession
            project_id: Project ID

        Returns:
            Project statistics

        Raises:
            ProjectNotFoundError: If not found
        """
        project_model = await self._get_project_model(db, project_id)

        # Calculate success rate
        success_rate_percent = 0.0
        if project_model.total_runs > 0:
            success_rate_percent = (
                project_model.successful_runs / project_model.total_runs
            ) * 100.0

        return ProjectStats(
            project_id=project_id,
            workspace_id=project_model.workspace_id,
            total_runs=project_model.total_runs,
            successful_runs=project_model.successful_runs,
            failed_runs=project_model.failed_runs,
            success_rate_percent=success_rate_percent,
            avg_duration_seconds=0.0,  # TODO: Track avg duration
            last_run_at=None,  # TODO: Track last run timestamp
        )

    async def get_workspace_run_count_today(
        self,
        db: AsyncSession,
        workspace_id: str,
    ) -> int:
        """
        Get count of pipeline runs executed today in workspace.

        Args:
            db: AsyncSession
            workspace_id: Workspace ID

        Returns:
            Count of runs today
        """
        today = datetime.utcnow().date()

        stmt = select(RunContractModel).where(
            RunContractModel.workspace_id == workspace_id,
            RunContractModel.created_at >= datetime.combine(today, datetime.min.time()),
        )
        result = await db.execute(stmt)
        runs = result.scalars().all()

        return len(runs)

    # ========================================================================
    # Private Helper Methods
    # ========================================================================

    async def _get_workspace_model(
        self,
        db: AsyncSession,
        workspace_id: str,
    ) -> WorkspaceModel:
        """Get workspace model from DB or raise error."""
        stmt = select(WorkspaceModel).where(
            WorkspaceModel.workspace_id == workspace_id
        )
        result = await db.execute(stmt)
        workspace_model = result.scalars().first()

        if not workspace_model:
            raise WorkspaceNotFoundError(f"Workspace not found: {workspace_id}")

        return workspace_model

    async def _get_project_model(
        self,
        db: AsyncSession,
        project_id: str,
    ) -> ProjectModel:
        """Get project model from DB or raise error."""
        stmt = select(ProjectModel).where(ProjectModel.project_id == project_id)
        result = await db.execute(stmt)
        project_model = result.scalars().first()

        if not project_model:
            raise ProjectNotFoundError(f"Project not found: {project_id}")

        return project_model

    @staticmethod
    def _model_to_schema(workspace_model: WorkspaceModel) -> Workspace:
        """Convert SQLAlchemy model to Pydantic schema."""
        return Workspace(
            workspace_id=workspace_model.workspace_id,
            name=workspace_model.name,
            slug=workspace_model.slug,
            description=workspace_model.description,
            status=workspace_model.status,
            owner_id=workspace_model.owner_id,
            created_by=workspace_model.created_by,
            created_at=workspace_model.created_at,
            updated_at=workspace_model.updated_at,
            storage_path=workspace_model.storage_path,
            max_projects=workspace_model.max_projects,
            max_runs_per_day=workspace_model.max_runs_per_day,
            max_storage_gb=workspace_model.max_storage_gb,
            settings=workspace_model.settings,
            tags=workspace_model.tags,
        )

    @staticmethod
    def _project_model_to_schema(project_model: ProjectModel) -> Project:
        """Convert SQLAlchemy model to Pydantic schema."""
        return Project(
            project_id=project_model.project_id,
            workspace_id=project_model.workspace_id,
            name=project_model.name,
            slug=project_model.slug,
            description=project_model.description,
            status=project_model.status,
            created_by=project_model.created_by,
            created_at=project_model.created_at,
            updated_at=project_model.updated_at,
            default_budget=project_model.default_budget,
            default_policy=project_model.default_policy,
            total_runs=project_model.total_runs,
            successful_runs=project_model.successful_runs,
            failed_runs=project_model.failed_runs,
            tags=project_model.tags,
        )
