"""
Odoo Connector Service

High-level service layer for Odoo integration.
Sprint IV: AXE × Odoo Integration
"""

from __future__ import annotations

import os
from typing import Dict, List, Optional

from loguru import logger

from .client import OdooXMLRPCClient
from .schemas import (
    OdooConnectionInfo,
    OdooModuleInfo,
    OdooModuleState,
    OdooOperationResult,
    OdooStatusResponse,
)


class OdooConnectorService:
    """
    Service layer for Odoo integration.

    Manages connection lifecycle, caching, and high-level operations.
    """

    def __init__(self):
        """Initialize Odoo connector service."""
        self._client: Optional[OdooXMLRPCClient] = None
        self._connection_info: Optional[OdooConnectionInfo] = None

    def _get_connection_info_from_env(self) -> OdooConnectionInfo:
        """
        Load Odoo connection info from environment variables.

        Returns:
            OdooConnectionInfo from ENV

        Raises:
            ValueError: If required ENV vars are missing
        """
        base_url = os.getenv("ODOO_BASE_URL")
        database = os.getenv("ODOO_DB_NAME")
        username = os.getenv("ODOO_ADMIN_USER")
        password = os.getenv("ODOO_ADMIN_PASSWORD")

        if not all([base_url, database, username, password]):
            missing = []
            if not base_url:
                missing.append("ODOO_BASE_URL")
            if not database:
                missing.append("ODOO_DB_NAME")
            if not username:
                missing.append("ODOO_ADMIN_USER")
            if not password:
                missing.append("ODOO_ADMIN_PASSWORD")

            raise ValueError(
                f"Missing required Odoo ENV variables: {', '.join(missing)}"
            )

        return OdooConnectionInfo(
            base_url=base_url,
            database=database,
            username=username,
            password=password,
        )

    def _get_client(self) -> OdooXMLRPCClient:
        """
        Get or create Odoo XML-RPC client.

        Returns:
            Initialized OdooXMLRPCClient

        Raises:
            ValueError: If connection info not configured
        """
        if self._client is None:
            connection_info = self._get_connection_info_from_env()
            self._client = OdooXMLRPCClient(connection_info)
            self._connection_info = connection_info

        return self._client

    async def test_connection(self) -> OdooStatusResponse:
        """
        Test connection to Odoo instance.

        Returns:
            OdooStatusResponse with connection status
        """
        try:
            client = self._get_client()
            status = await client.test_connection()
            return status

        except ValueError as e:
            # Configuration error
            logger.error(f"Odoo configuration error: {e}")
            return OdooStatusResponse(
                connected=False,
                status="error",
                error=f"Configuration error: {e}",
            )

        except Exception as e:
            # Connection error
            logger.error(f"Odoo connection test failed: {e}")
            return OdooStatusResponse(
                connected=False,
                status="error",
                error=str(e),
            )

    async def list_modules(
        self,
        state: Optional[OdooModuleState] = None,
        name_filter: Optional[str] = None,
    ) -> List[OdooModuleInfo]:
        """
        List Odoo modules with optional filters.

        Args:
            state: Filter by module state
            name_filter: Filter by module name (partial match)

        Returns:
            List of OdooModuleInfo
        """
        try:
            client = self._get_client()
            modules = await client.list_modules(
                state_filter=state, name_filter=name_filter
            )
            return modules

        except Exception as e:
            logger.error(f"Failed to list modules: {e}")
            return []

    async def get_module_info(self, module_name: str) -> Optional[OdooModuleInfo]:
        """
        Get detailed information about a specific module.

        Args:
            module_name: Technical module name

        Returns:
            OdooModuleInfo if found, None otherwise
        """
        try:
            client = self._get_client()
            return await client.get_module_info(module_name)

        except Exception as e:
            logger.error(f"Failed to get module info: {e}")
            return None

    async def install_module(self, module_name: str) -> OdooOperationResult:
        """
        Install an Odoo module.

        Args:
            module_name: Technical module name

        Returns:
            OdooOperationResult with operation details
        """
        try:
            client = self._get_client()

            # Get current state
            module_info = await client.get_module_info(module_name)
            if not module_info:
                return OdooOperationResult(
                    success=False,
                    module_name=module_name,
                    operation="install",
                    message=f"Module '{module_name}' not found in Odoo",
                    error="Module not found",
                )

            previous_state = module_info.state

            # Check if already installed
            if previous_state == OdooModuleState.INSTALLED:
                return OdooOperationResult(
                    success=False,
                    module_name=module_name,
                    operation="install",
                    message=f"Module '{module_name}' is already installed",
                    previous_state=previous_state,
                    warnings=["Module already installed"],
                )

            # Trigger installation
            await client.install_module(module_name)

            # Get new state
            updated_info = await client.get_module_info(module_name)
            new_state = updated_info.state if updated_info else OdooModuleState.UNKNOWN

            return OdooOperationResult(
                success=True,
                module_name=module_name,
                operation="install",
                message=f"Module '{module_name}' installation initiated",
                previous_state=previous_state,
                new_state=new_state,
            )

        except Exception as e:
            logger.error(f"Failed to install module '{module_name}': {e}")
            return OdooOperationResult(
                success=False,
                module_name=module_name,
                operation="install",
                message=f"Installation failed: {e}",
                error=str(e),
            )

    async def upgrade_module(self, module_name: str) -> OdooOperationResult:
        """
        Upgrade an Odoo module.

        Args:
            module_name: Technical module name

        Returns:
            OdooOperationResult with operation details
        """
        try:
            client = self._get_client()

            # Get current state
            module_info = await client.get_module_info(module_name)
            if not module_info:
                return OdooOperationResult(
                    success=False,
                    module_name=module_name,
                    operation="upgrade",
                    message=f"Module '{module_name}' not found in Odoo",
                    error="Module not found",
                )

            previous_state = module_info.state

            # Check if installed
            if previous_state != OdooModuleState.INSTALLED:
                return OdooOperationResult(
                    success=False,
                    module_name=module_name,
                    operation="upgrade",
                    message=f"Module '{module_name}' is not installed (state: {previous_state.value})",
                    previous_state=previous_state,
                    warnings=["Module must be installed before upgrade"],
                )

            # Trigger upgrade
            await client.upgrade_module(module_name)

            # Get new state
            updated_info = await client.get_module_info(module_name)
            new_state = updated_info.state if updated_info else OdooModuleState.UNKNOWN

            return OdooOperationResult(
                success=True,
                module_name=module_name,
                operation="upgrade",
                message=f"Module '{module_name}' upgrade initiated",
                previous_state=previous_state,
                new_state=new_state,
            )

        except Exception as e:
            logger.error(f"Failed to upgrade module '{module_name}': {e}")
            return OdooOperationResult(
                success=False,
                module_name=module_name,
                operation="upgrade",
                message=f"Upgrade failed: {e}",
                error=str(e),
            )

    async def uninstall_module(
        self, module_name: str, remove_dependencies: bool = False
    ) -> OdooOperationResult:
        """
        Uninstall an Odoo module.

        Args:
            module_name: Technical module name
            remove_dependencies: Also uninstall dependent modules (conservative default: False)

        Returns:
            OdooOperationResult with operation details
        """
        try:
            client = self._get_client()

            # Get current state
            module_info = await client.get_module_info(module_name)
            if not module_info:
                return OdooOperationResult(
                    success=False,
                    module_name=module_name,
                    operation="uninstall",
                    message=f"Module '{module_name}' not found in Odoo",
                    error="Module not found",
                )

            previous_state = module_info.state

            # Check if installed
            if previous_state != OdooModuleState.INSTALLED:
                return OdooOperationResult(
                    success=False,
                    module_name=module_name,
                    operation="uninstall",
                    message=f"Module '{module_name}' is not installed (state: {previous_state.value})",
                    previous_state=previous_state,
                    warnings=["Module is not installed"],
                )

            # Warn if dependencies exist and not removing them
            if module_info.depends and not remove_dependencies:
                logger.warning(
                    f"Module '{module_name}' has dependencies: {module_info.depends}. "
                    "Use remove_dependencies=True to also remove them."
                )

            # Trigger uninstall
            await client.uninstall_module(module_name)

            # Get new state
            updated_info = await client.get_module_info(module_name)
            new_state = updated_info.state if updated_info else OdooModuleState.UNKNOWN

            return OdooOperationResult(
                success=True,
                module_name=module_name,
                operation="uninstall",
                message=f"Module '{module_name}' uninstallation initiated",
                previous_state=previous_state,
                new_state=new_state,
            )

        except Exception as e:
            logger.error(f"Failed to uninstall module '{module_name}': {e}")
            return OdooOperationResult(
                success=False,
                module_name=module_name,
                operation="uninstall",
                message=f"Uninstallation failed: {e}",
                error=str(e),
            )


# Singleton instance
_service: Optional[OdooConnectorService] = None


def get_odoo_service() -> OdooConnectorService:
    """
    Get singleton Odoo connector service.

    Returns:
        OdooConnectorService instance
    """
    global _service
    if _service is None:
        _service = OdooConnectorService()
    return _service
