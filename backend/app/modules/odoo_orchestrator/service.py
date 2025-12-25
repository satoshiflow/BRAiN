"""
Odoo Orchestrator Service

Coordinates module generation, storage, and Odoo deployment.
Sprint IV: AXE × Odoo Integration
"""

from __future__ import annotations

import os
import shutil
from pathlib import Path
from typing import Optional

from loguru import logger

from backend.app.modules.axe_odoo_generator import (
    ModuleSpecParser,
    OdooModuleGenerator,
)
from backend.app.modules.odoo_connector import (
    OdooModuleState,
    get_odoo_service,
)
from backend.app.modules.odoo_registry import get_odoo_registry

from .schemas import (
    ModuleGenerateRequest,
    ModuleInstallRequest,
    ModuleRollbackRequest,
    ModuleUpgradeRequest,
    OdooOrchestrationResult,
    OdooOrchestrationStatus,
)


class OdooOrchestrator:
    """
    Orchestrates Odoo module lifecycle operations.

    Coordinates:
    - Text spec parsing (ModuleSpecParser)
    - Module generation (OdooModuleGenerator)
    - Version storage (OdooModuleRegistry)
    - Odoo deployment (OdooConnectorService)
    """

    def __init__(self):
        """Initialize orchestrator with required services."""
        self.parser = ModuleSpecParser()
        self.generator = OdooModuleGenerator()
        self.registry = get_odoo_registry()
        self.odoo_service = get_odoo_service()

        # Get Odoo addons path from ENV
        self.odoo_addons_path = os.getenv("ODOO_ADDONS_PATH")

    async def generate_and_install(
        self, request: ModuleGenerateRequest
    ) -> OdooOrchestrationResult:
        """
        Full workflow: Parse → Generate → Store → Copy → Install.

        Args:
            request: Module generation request

        Returns:
            OdooOrchestrationResult with operation details
        """
        module_name = "unknown"
        version = "0.0.0"

        try:
            # Step 1: Parse spec
            logger.info("Parsing module specification...")
            module_ast = self.parser.parse(request.spec_text)
            module_name = module_ast.name
            version = module_ast.version

            # Step 2: Generate module
            logger.info(f"Generating module {module_name} v{version}...")
            generation_result = self.generator.generate(module_ast)

            if not generation_result.success:
                return OdooOrchestrationResult(
                    success=False,
                    status=OdooOrchestrationStatus.FAILED,
                    module_name=module_name,
                    version=version,
                    operation="generate_and_install",
                    generation_success=False,
                    message=f"Generation failed: {generation_result.errors}",
                    errors=generation_result.errors,
                    warnings=generation_result.warnings,
                )

            # Step 3: Store in registry
            logger.info(f"Storing module {module_name} v{version} in registry...")
            version_record = self.registry.store_module(generation_result)

            # Step 4: Copy to Odoo addons path (if configured and auto_install=True)
            copied = False
            if request.auto_install and self.odoo_addons_path:
                logger.info(
                    f"Copying module to Odoo addons path: {self.odoo_addons_path}"
                )
                copied = self._copy_to_odoo_addons(module_name, version)

            # Step 5: Install in Odoo (if auto_install and copied)
            installation_result = None
            release_id = None

            if request.auto_install and copied:
                logger.info(f"Installing module {module_name} in Odoo...")
                installation_result = await self.odoo_service.install_module(
                    module_name
                )

                if installation_result.success:
                    # Create release record
                    release = self.registry.create_release_record(
                        module_name=module_name,
                        version=version,
                        odoo_status=installation_result.new_state.value
                        if installation_result.new_state
                        else "unknown",
                    )
                    release_id = release.release_id

            # Build result
            return OdooOrchestrationResult(
                success=installation_result.success
                if installation_result
                else generation_result.success,
                status=OdooOrchestrationStatus.COMPLETED
                if (installation_result and installation_result.success)
                or not request.auto_install
                else OdooOrchestrationStatus.FAILED,
                module_name=module_name,
                version=version,
                operation="generate_and_install",
                generation_success=True,
                module_hash=version_record.module_hash,
                file_count=version_record.file_count,
                installation_success=installation_result.success
                if installation_result
                else False,
                odoo_status=installation_result.new_state.value
                if installation_result and installation_result.new_state
                else None,
                release_id=release_id,
                message=f"Module {module_name} v{version} "
                + (
                    "generated and installed successfully"
                    if installation_result and installation_result.success
                    else "generated successfully (installation skipped)"
                    if not request.auto_install
                    else "generated but installation failed"
                ),
                warnings=generation_result.warnings
                + (installation_result.warnings if installation_result else []),
                errors=installation_result.errors if installation_result else [],
            )

        except Exception as e:
            logger.error(f"Orchestration failed: {e}")
            return OdooOrchestrationResult(
                success=False,
                status=OdooOrchestrationStatus.FAILED,
                module_name=module_name,
                version=version,
                operation="generate_and_install",
                message=f"Orchestration failed: {e}",
                errors=[str(e)],
            )

    async def install_existing(
        self, request: ModuleInstallRequest
    ) -> OdooOrchestrationResult:
        """
        Install a previously generated module.

        Args:
            request: Module install request

        Returns:
            OdooOrchestrationResult
        """
        try:
            # Get version from registry
            version_record = self.registry.get_module_version(
                request.module_name, request.version
            )

            if not version_record:
                return OdooOrchestrationResult(
                    success=False,
                    status=OdooOrchestrationStatus.FAILED,
                    module_name=request.module_name,
                    version=request.version,
                    operation="install",
                    message=f"Module {request.module_name} v{request.version} not found in registry",
                    errors=["Module version not found"],
                )

            # Copy to Odoo addons
            if self.odoo_addons_path:
                logger.info(
                    f"Copying module {request.module_name} v{request.version} to Odoo..."
                )
                copied = self._copy_to_odoo_addons(
                    request.module_name, request.version
                )

                if not copied:
                    return OdooOrchestrationResult(
                        success=False,
                        status=OdooOrchestrationStatus.FAILED,
                        module_name=request.module_name,
                        version=request.version,
                        operation="install",
                        message="Failed to copy module to Odoo addons path",
                        errors=["Copy failed"],
                    )

            # Install in Odoo
            logger.info(f"Installing module {request.module_name} in Odoo...")
            installation_result = await self.odoo_service.install_module(
                request.module_name
            )

            if installation_result.success:
                # Create release record
                release = self.registry.create_release_record(
                    module_name=request.module_name,
                    version=request.version,
                    odoo_status=installation_result.new_state.value
                    if installation_result.new_state
                    else "unknown",
                )

                return OdooOrchestrationResult(
                    success=True,
                    status=OdooOrchestrationStatus.COMPLETED,
                    module_name=request.module_name,
                    version=request.version,
                    operation="install",
                    installation_success=True,
                    odoo_status=installation_result.new_state.value
                    if installation_result.new_state
                    else None,
                    release_id=release.release_id,
                    message=f"Module {request.module_name} v{request.version} installed successfully",
                )

            else:
                return OdooOrchestrationResult(
                    success=False,
                    status=OdooOrchestrationStatus.FAILED,
                    module_name=request.module_name,
                    version=request.version,
                    operation="install",
                    message=installation_result.message,
                    errors=installation_result.errors,
                    warnings=installation_result.warnings,
                )

        except Exception as e:
            logger.error(f"Install failed: {e}")
            return OdooOrchestrationResult(
                success=False,
                status=OdooOrchestrationStatus.FAILED,
                module_name=request.module_name,
                version=request.version,
                operation="install",
                message=f"Install failed: {e}",
                errors=[str(e)],
            )

    async def upgrade_module(
        self, request: ModuleUpgradeRequest
    ) -> OdooOrchestrationResult:
        """
        Upgrade module with new version.

        Args:
            request: Module upgrade request

        Returns:
            OdooOrchestrationResult
        """
        try:
            # If spec_text provided, generate new version
            if request.spec_text:
                # Parse new spec
                module_ast = self.parser.parse(request.spec_text)

                # Override version if specified
                if request.new_version:
                    module_ast.version = request.new_version

                # Generate
                generation_result = self.generator.generate(module_ast)

                if not generation_result.success:
                    return OdooOrchestrationResult(
                        success=False,
                        status=OdooOrchestrationStatus.FAILED,
                        module_name=request.module_name,
                        version=module_ast.version,
                        operation="upgrade",
                        message=f"Generation failed: {generation_result.errors}",
                        errors=generation_result.errors,
                    )

                # Store new version
                version_record = self.registry.store_module(generation_result)
                new_version = version_record.version

                # Copy to Odoo
                if self.odoo_addons_path:
                    self._copy_to_odoo_addons(request.module_name, new_version)

            else:
                # Use existing latest version
                latest = self.registry.get_latest_version(request.module_name)
                if not latest:
                    return OdooOrchestrationResult(
                        success=False,
                        status=OdooOrchestrationStatus.FAILED,
                        module_name=request.module_name,
                        version="unknown",
                        operation="upgrade",
                        message="No versions found in registry",
                        errors=["Module not found"],
                    )

                new_version = latest.version

                # Copy to Odoo
                if self.odoo_addons_path:
                    self._copy_to_odoo_addons(request.module_name, new_version)

            # Upgrade in Odoo
            logger.info(f"Upgrading module {request.module_name} in Odoo...")
            upgrade_result = await self.odoo_service.upgrade_module(request.module_name)

            if upgrade_result.success:
                # Update release record
                release = self.registry.create_release_record(
                    module_name=request.module_name,
                    version=new_version,
                    odoo_status=upgrade_result.new_state.value
                    if upgrade_result.new_state
                    else "unknown",
                )

                return OdooOrchestrationResult(
                    success=True,
                    status=OdooOrchestrationStatus.COMPLETED,
                    module_name=request.module_name,
                    version=new_version,
                    operation="upgrade",
                    installation_success=True,
                    odoo_status=upgrade_result.new_state.value
                    if upgrade_result.new_state
                    else None,
                    release_id=release.release_id,
                    message=f"Module {request.module_name} upgraded to v{new_version}",
                )

            else:
                return OdooOrchestrationResult(
                    success=False,
                    status=OdooOrchestrationStatus.FAILED,
                    module_name=request.module_name,
                    version=new_version,
                    operation="upgrade",
                    message=upgrade_result.message,
                    errors=upgrade_result.errors,
                )

        except Exception as e:
            logger.error(f"Upgrade failed: {e}")
            return OdooOrchestrationResult(
                success=False,
                status=OdooOrchestrationStatus.FAILED,
                module_name=request.module_name,
                version="unknown",
                operation="upgrade",
                message=f"Upgrade failed: {e}",
                errors=[str(e)],
            )

    async def rollback_module(
        self, request: ModuleRollbackRequest
    ) -> OdooOrchestrationResult:
        """
        Rollback module to previous version.

        Args:
            request: Module rollback request

        Returns:
            OdooOrchestrationResult
        """
        try:
            # Determine target version
            if request.target_version:
                target_version = request.target_version
            else:
                # Get previous release
                releases = self.registry.get_release_history(request.module_name)
                if len(releases) < 2:
                    return OdooOrchestrationResult(
                        success=False,
                        status=OdooOrchestrationStatus.FAILED,
                        module_name=request.module_name,
                        version="unknown",
                        operation="rollback",
                        message="No previous version to rollback to",
                        errors=["Insufficient release history"],
                    )

                target_version = releases[1].version  # Second most recent

            # Verify version exists
            version_record = self.registry.get_module_version(
                request.module_name, target_version
            )

            if not version_record:
                return OdooOrchestrationResult(
                    success=False,
                    status=OdooOrchestrationStatus.FAILED,
                    module_name=request.module_name,
                    version=target_version,
                    operation="rollback",
                    message=f"Target version {target_version} not found",
                    errors=["Version not found"],
                )

            # Copy target version to Odoo
            if self.odoo_addons_path:
                logger.info(
                    f"Copying version {target_version} to Odoo addons path..."
                )
                copied = self._copy_to_odoo_addons(request.module_name, target_version)

                if not copied:
                    return OdooOrchestrationResult(
                        success=False,
                        status=OdooOrchestrationStatus.FAILED,
                        module_name=request.module_name,
                        version=target_version,
                        operation="rollback",
                        message="Failed to copy module to Odoo",
                        errors=["Copy failed"],
                    )

            # Upgrade in Odoo (will pick up the older version)
            logger.info(
                f"Rolling back {request.module_name} to version {target_version}..."
            )
            upgrade_result = await self.odoo_service.upgrade_module(request.module_name)

            if upgrade_result.success:
                # Create new release record
                release = self.registry.create_release_record(
                    module_name=request.module_name,
                    version=target_version,
                    odoo_status=upgrade_result.new_state.value
                    if upgrade_result.new_state
                    else "unknown",
                )

                return OdooOrchestrationResult(
                    success=True,
                    status=OdooOrchestrationStatus.COMPLETED,
                    module_name=request.module_name,
                    version=target_version,
                    operation="rollback",
                    installation_success=True,
                    odoo_status=upgrade_result.new_state.value
                    if upgrade_result.new_state
                    else None,
                    release_id=release.release_id,
                    message=f"Module {request.module_name} rolled back to v{target_version}",
                )

            else:
                return OdooOrchestrationResult(
                    success=False,
                    status=OdooOrchestrationStatus.FAILED,
                    module_name=request.module_name,
                    version=target_version,
                    operation="rollback",
                    message=upgrade_result.message,
                    errors=upgrade_result.errors,
                )

        except Exception as e:
            logger.error(f"Rollback failed: {e}")
            return OdooOrchestrationResult(
                success=False,
                status=OdooOrchestrationStatus.FAILED,
                module_name=request.module_name,
                version="unknown",
                operation="rollback",
                message=f"Rollback failed: {e}",
                errors=[str(e)],
            )

    def _copy_to_odoo_addons(self, module_name: str, version: str) -> bool:
        """
        Copy module to Odoo addons path.

        Args:
            module_name: Module technical name
            version: Version to copy

        Returns:
            True if successful
        """
        if not self.odoo_addons_path:
            logger.warning("ODOO_ADDONS_PATH not configured - skipping copy")
            return False

        # Source path (from registry)
        source_path = self.registry.get_module_path(module_name, version)

        if not source_path or not source_path.exists():
            logger.error(f"Source path not found: {source_path}")
            return False

        # Destination path
        dest_path = Path(self.odoo_addons_path) / module_name

        try:
            # Remove existing if present
            if dest_path.exists():
                shutil.rmtree(dest_path)

            # Copy
            shutil.copytree(source_path, dest_path)

            logger.info(f"Copied {module_name} v{version} to {dest_path}")
            return True

        except Exception as e:
            logger.error(f"Failed to copy module to Odoo: {e}")
            return False


# Singleton instance
_orchestrator: Optional[OdooOrchestrator] = None


def get_odoo_orchestrator() -> OdooOrchestrator:
    """
    Get singleton Odoo orchestrator.

    Returns:
        OdooOrchestrator instance
    """
    global _orchestrator
    if _orchestrator is None:
        _orchestrator = OdooOrchestrator()
    return _orchestrator
