"""
Workspace Isolation Service (Sprint 9-C)

Hard isolation for multi-tenant deployments.
Each workspace gets isolated storage for secrets, evidence, and contracts.
"""

from typing import Dict, List, Optional
from pathlib import Path
import json
import time
from loguru import logger

from app.modules.autonomous_pipeline.workspace_schemas import (
    Workspace,
    Project,
    WorkspaceStatus,
    ProjectStatus,
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


class WorkspaceService:
    """
    Workspace isolation and management service.

    Features:
    - Hard workspace isolation (storage, secrets)
    - Project management within workspaces
    - Quota enforcement
    - Default workspace for backward compatibility
    """

    # Storage directories
    WORKSPACES_DIR = Path("storage/workspaces")
    DEFAULT_WORKSPACE_ID = "default"

    def __init__(self):
        """Initialize workspace service."""
        self.WORKSPACES_DIR.mkdir(parents=True, exist_ok=True)

        # In-memory cache (for demo; use database in production)
        self.workspaces: Dict[str, Workspace] = {}
        self.projects: Dict[str, Project] = {}

        # Ensure default workspace exists
        self._ensure_default_workspace()

    def _ensure_default_workspace(self):
        """Create default workspace if it doesn't exist."""
        if self.DEFAULT_WORKSPACE_ID in self.workspaces:
            return

        default_workspace = Workspace(
            workspace_id=self.DEFAULT_WORKSPACE_ID,
            name="Default Workspace",
            slug="default",
            description="Default workspace for backward compatibility",
            status=WorkspaceStatus.ACTIVE,
            storage_path=str(self.WORKSPACES_DIR / self.DEFAULT_WORKSPACE_ID),
        )

        self.workspaces[self.DEFAULT_WORKSPACE_ID] = default_workspace
        self._save_workspace(default_workspace)

        logger.info(f"[Workspace] Default workspace created: {self.DEFAULT_WORKSPACE_ID}")

    def create_workspace(self, request: WorkspaceCreateRequest) -> Workspace:
        """
        Create new workspace.

        Args:
            request: Workspace creation request

        Returns:
            Created workspace

        Raises:
            ValueError: If slug already exists
        """
        # Check slug uniqueness
        for workspace in self.workspaces.values():
            if workspace.slug == request.slug:
                raise ValueError(f"Workspace slug already exists: {request.slug}")

        # Generate workspace ID
        timestamp_ms = int(time.time() * 1000)
        workspace_id = f"ws_{timestamp_ms}_{request.slug}"

        # Create storage path
        storage_path = self.WORKSPACES_DIR / workspace_id
        storage_path.mkdir(parents=True, exist_ok=True)

        # Create subdirectories for isolation
        (storage_path / "secrets").mkdir(exist_ok=True)
        (storage_path / "evidence").mkdir(exist_ok=True)
        (storage_path / "contracts").mkdir(exist_ok=True)
        (storage_path / "projects").mkdir(exist_ok=True)

        # Create workspace
        workspace = Workspace(
            workspace_id=workspace_id,
            name=request.name,
            slug=request.slug,
            description=request.description,
            status=WorkspaceStatus.ACTIVE,
            owner_id=request.owner_id,
            storage_path=str(storage_path),
            max_projects=request.max_projects,
            max_runs_per_day=request.max_runs_per_day,
            max_storage_gb=request.max_storage_gb,
            settings=request.settings,
            tags=request.tags,
        )

        # Store workspace
        self.workspaces[workspace_id] = workspace
        self._save_workspace(workspace)

        logger.info(f"[Workspace] Created: {workspace_id} (slug={request.slug})")

        return workspace

    def get_workspace(self, workspace_id: str) -> Workspace:
        """
        Get workspace by ID.

        Args:
            workspace_id: Workspace ID

        Returns:
            Workspace

        Raises:
            WorkspaceNotFoundError: If workspace not found
        """
        workspace = self.workspaces.get(workspace_id)
        if not workspace:
            raise WorkspaceNotFoundError(f"Workspace not found: {workspace_id}")
        return workspace

    def get_workspace_by_slug(self, slug: str) -> Optional[Workspace]:
        """
        Get workspace by slug.

        Args:
            slug: Workspace slug

        Returns:
            Workspace or None if not found
        """
        for workspace in self.workspaces.values():
            if workspace.slug == slug:
                return workspace
        return None

    def list_workspaces(
        self,
        status: Optional[WorkspaceStatus] = None,
        owner_id: Optional[str] = None,
    ) -> List[Workspace]:
        """
        List workspaces with optional filters.

        Args:
            status: Filter by status
            owner_id: Filter by owner

        Returns:
            List of workspaces
        """
        result = list(self.workspaces.values())

        if status:
            result = [ws for ws in result if ws.status == status]

        if owner_id:
            result = [ws for ws in result if ws.owner_id == owner_id]

        return result

    def update_workspace(
        self,
        workspace_id: str,
        request: WorkspaceUpdateRequest,
    ) -> Workspace:
        """
        Update workspace.

        Args:
            workspace_id: Workspace ID
            request: Update request

        Returns:
            Updated workspace

        Raises:
            WorkspaceNotFoundError: If workspace not found
        """
        workspace = self.get_workspace(workspace_id)

        # Update fields
        if request.name is not None:
            workspace.name = request.name
        if request.description is not None:
            workspace.description = request.description
        if request.status is not None:
            workspace.status = request.status
        if request.max_projects is not None:
            workspace.max_projects = request.max_projects
        if request.max_runs_per_day is not None:
            workspace.max_runs_per_day = request.max_runs_per_day
        if request.max_storage_gb is not None:
            workspace.max_storage_gb = request.max_storage_gb
        if request.settings is not None:
            workspace.settings = request.settings
        if request.tags is not None:
            workspace.tags = request.tags

        workspace.updated_at = time.time()

        # Save
        self._save_workspace(workspace)

        logger.info(f"[Workspace] Updated: {workspace_id}")

        return workspace

    def delete_workspace(self, workspace_id: str) -> bool:
        """
        Delete workspace (soft delete - archive).

        Args:
            workspace_id: Workspace ID

        Returns:
            True if deleted

        Raises:
            WorkspaceNotFoundError: If workspace not found
            ValueError: If trying to delete default workspace
        """
        if workspace_id == self.DEFAULT_WORKSPACE_ID:
            raise ValueError("Cannot delete default workspace")

        workspace = self.get_workspace(workspace_id)
        workspace.status = WorkspaceStatus.ARCHIVED
        workspace.updated_at = time.time()

        self._save_workspace(workspace)

        logger.info(f"[Workspace] Archived: {workspace_id}")

        return True

    def create_project(
        self,
        workspace_id: str,
        request: ProjectCreateRequest,
    ) -> Project:
        """
        Create project in workspace.

        Args:
            workspace_id: Parent workspace ID
            request: Project creation request

        Returns:
            Created project

        Raises:
            WorkspaceNotFoundError: If workspace not found
            QuotaExceededError: If max projects exceeded
            ValueError: If slug already exists in workspace
        """
        workspace = self.get_workspace(workspace_id)

        # Check quota
        workspace_projects = [
            p for p in self.projects.values()
            if p.workspace_id == workspace_id and p.status != ProjectStatus.ARCHIVED
        ]
        if len(workspace_projects) >= workspace.max_projects:
            raise QuotaExceededError(
                f"Workspace {workspace_id} has reached max projects limit: {workspace.max_projects}"
            )

        # Check slug uniqueness within workspace
        for project in workspace_projects:
            if project.slug == request.slug:
                raise ValueError(
                    f"Project slug already exists in workspace: {request.slug}"
                )

        # Generate project ID
        timestamp_ms = int(time.time() * 1000)
        project_id = f"proj_{timestamp_ms}_{request.slug}"

        # Create project
        project = Project(
            project_id=project_id,
            workspace_id=workspace_id,
            name=request.name,
            slug=request.slug,
            description=request.description,
            status=ProjectStatus.ACTIVE,
            default_budget=request.default_budget,
            default_policy=request.default_policy,
            tags=request.tags,
        )

        # Store project
        self.projects[project_id] = project
        self._save_project(project)

        logger.info(
            f"[Workspace] Project created: {project_id} (workspace={workspace_id}, slug={request.slug})"
        )

        return project

    def get_project(self, project_id: str) -> Project:
        """
        Get project by ID.

        Args:
            project_id: Project ID

        Returns:
            Project

        Raises:
            ProjectNotFoundError: If project not found
        """
        project = self.projects.get(project_id)
        if not project:
            raise ProjectNotFoundError(f"Project not found: {project_id}")
        return project

    def list_projects(
        self,
        workspace_id: Optional[str] = None,
        status: Optional[ProjectStatus] = None,
    ) -> List[Project]:
        """
        List projects with optional filters.

        Args:
            workspace_id: Filter by workspace
            status: Filter by status

        Returns:
            List of projects
        """
        result = list(self.projects.values())

        if workspace_id:
            result = [p for p in result if p.workspace_id == workspace_id]

        if status:
            result = [p for p in result if p.status == status]

        return result

    def update_project(
        self,
        project_id: str,
        request: ProjectUpdateRequest,
    ) -> Project:
        """
        Update project.

        Args:
            project_id: Project ID
            request: Update request

        Returns:
            Updated project

        Raises:
            ProjectNotFoundError: If project not found
        """
        project = self.get_project(project_id)

        # Update fields
        if request.name is not None:
            project.name = request.name
        if request.description is not None:
            project.description = request.description
        if request.status is not None:
            project.status = request.status
        if request.default_budget is not None:
            project.default_budget = request.default_budget
        if request.default_policy is not None:
            project.default_policy = request.default_policy
        if request.tags is not None:
            project.tags = request.tags

        project.updated_at = time.time()

        # Save
        self._save_project(project)

        logger.info(f"[Workspace] Project updated: {project_id}")

        return project

    def delete_project(self, project_id: str) -> bool:
        """
        Delete project (soft delete - archive).

        Args:
            project_id: Project ID

        Returns:
            True if deleted

        Raises:
            ProjectNotFoundError: If project not found
        """
        project = self.get_project(project_id)
        project.status = ProjectStatus.ARCHIVED
        project.updated_at = time.time()

        self._save_project(project)

        logger.info(f"[Workspace] Project archived: {project_id}")

        return True

    def get_isolated_storage_path(
        self,
        workspace_id: str,
        subdirectory: str = "",
    ) -> Path:
        """
        Get isolated storage path for workspace.

        Args:
            workspace_id: Workspace ID
            subdirectory: Optional subdirectory (e.g., "secrets", "evidence")

        Returns:
            Isolated storage path

        Raises:
            WorkspaceNotFoundError: If workspace not found
        """
        workspace = self.get_workspace(workspace_id)

        base_path = Path(workspace.storage_path)

        if subdirectory:
            path = base_path / subdirectory
            path.mkdir(parents=True, exist_ok=True)
            return path

        return base_path

    def get_workspace_stats(self, workspace_id: str) -> WorkspaceStats:
        """
        Get workspace statistics.

        Args:
            workspace_id: Workspace ID

        Returns:
            Workspace statistics

        Raises:
            WorkspaceNotFoundError: If workspace not found
        """
        workspace = self.get_workspace(workspace_id)

        # Get projects
        projects = self.list_projects(workspace_id=workspace_id)
        active_projects = [p for p in projects if p.status == ProjectStatus.ACTIVE]

        # Calculate totals
        total_runs = sum(p.total_runs for p in projects)

        # Estimate storage usage (simplified)
        storage_used_gb = 0.0
        try:
            storage_path = Path(workspace.storage_path)
            if storage_path.exists():
                total_bytes = sum(
                    f.stat().st_size
                    for f in storage_path.rglob("*")
                    if f.is_file()
                )
                storage_used_gb = total_bytes / (1024 ** 3)
        except Exception as e:
            logger.warning(f"Failed to calculate storage usage: {e}")

        # Calculate quota usage
        quota_usage_percent = (storage_used_gb / workspace.max_storage_gb) * 100.0

        return WorkspaceStats(
            workspace_id=workspace_id,
            total_projects=len(projects),
            active_projects=len(active_projects),
            total_runs=total_runs,
            runs_today=0,  # TODO: Track daily runs
            storage_used_gb=storage_used_gb,
            storage_limit_gb=workspace.max_storage_gb,
            quota_usage_percent=quota_usage_percent,
        )

    def get_project_stats(self, project_id: str) -> ProjectStats:
        """
        Get project statistics.

        Args:
            project_id: Project ID

        Returns:
            Project statistics

        Raises:
            ProjectNotFoundError: If project not found
        """
        project = self.get_project(project_id)

        # Calculate success rate
        success_rate_percent = 0.0
        if project.total_runs > 0:
            success_rate_percent = (project.successful_runs / project.total_runs) * 100.0

        return ProjectStats(
            project_id=project_id,
            workspace_id=project.workspace_id,
            total_runs=project.total_runs,
            successful_runs=project.successful_runs,
            failed_runs=project.failed_runs,
            success_rate_percent=success_rate_percent,
            avg_duration_seconds=0.0,  # TODO: Track avg duration
            last_run_at=None,  # TODO: Track last run
        )

    def _save_workspace(self, workspace: Workspace):
        """Save workspace to disk."""
        file_path = self.WORKSPACES_DIR / f"{workspace.workspace_id}.json"
        with open(file_path, "w") as f:
            json.dump(workspace.model_dump(), f, indent=2, default=str)

    def _save_project(self, project: Project):
        """Save project to disk."""
        workspace_path = self.WORKSPACES_DIR / project.workspace_id / "projects"
        workspace_path.mkdir(parents=True, exist_ok=True)
        file_path = workspace_path / f"{project.project_id}.json"
        with open(file_path, "w") as f:
            json.dump(project.model_dump(), f, indent=2, default=str)


# Singleton
_workspace_service: Optional[WorkspaceService] = None


def get_workspace_service() -> WorkspaceService:
    """Get singleton workspace service."""
    global _workspace_service
    if _workspace_service is None:
        _workspace_service = WorkspaceService()
    return _workspace_service
