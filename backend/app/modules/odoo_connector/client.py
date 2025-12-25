"""
Odoo XML-RPC Client

Handles XML-RPC communication with Odoo instance.
Sprint IV: AXE × Odoo Integration
"""

from __future__ import annotations

import xmlrpc.client
from typing import Any, Dict, List, Optional

from loguru import logger

from .schemas import (
    OdooConnectionInfo,
    OdooModuleInfo,
    OdooModuleState,
    OdooStatusResponse,
    OdooConnectionStatus,
)


class OdooXMLRPCClient:
    """
    XML-RPC client for Odoo integration.

    Handles authentication, module queries, and module operations
    via Odoo's XML-RPC API.
    """

    def __init__(self, connection_info: OdooConnectionInfo):
        """
        Initialize Odoo XML-RPC client.

        Args:
            connection_info: Odoo connection configuration
        """
        self.base_url = connection_info.base_url.rstrip("/")
        self.database = connection_info.database
        self.username = connection_info.username
        self.password = connection_info.password

        # XML-RPC endpoints
        self.common_url = f"{self.base_url}/xmlrpc/2/common"
        self.object_url = f"{self.base_url}/xmlrpc/2/object"

        # Session state
        self.uid: Optional[int] = None
        self._common_proxy: Optional[xmlrpc.client.ServerProxy] = None
        self._object_proxy: Optional[xmlrpc.client.ServerProxy] = None

    def _get_common_proxy(self) -> xmlrpc.client.ServerProxy:
        """Get or create common endpoint proxy."""
        if self._common_proxy is None:
            self._common_proxy = xmlrpc.client.ServerProxy(self.common_url)
        return self._common_proxy

    def _get_object_proxy(self) -> xmlrpc.client.ServerProxy:
        """Get or create object endpoint proxy."""
        if self._object_proxy is None:
            self._object_proxy = xmlrpc.client.ServerProxy(self.object_url)
        return self._object_proxy

    async def authenticate(self) -> int:
        """
        Authenticate with Odoo and get user ID.

        Returns:
            User ID (uid) if successful

        Raises:
            ConnectionError: If authentication fails
        """
        try:
            common = self._get_common_proxy()
            uid = common.authenticate(
                self.database, self.username, self.password, {}
            )

            if not uid:
                raise ConnectionError("Authentication failed - invalid credentials")

            self.uid = uid
            logger.info(f"Authenticated with Odoo as user {self.username} (uid={uid})")
            return uid

        except Exception as e:
            logger.error(f"Odoo authentication error: {e}")
            raise ConnectionError(f"Failed to authenticate: {e}")

    async def test_connection(self) -> OdooStatusResponse:
        """
        Test connection to Odoo and retrieve server info.

        Returns:
            OdooStatusResponse with connection status and server details
        """
        try:
            common = self._get_common_proxy()

            # Get server version
            version_info = common.version()

            # Try to authenticate
            uid = await self.authenticate()

            return OdooStatusResponse(
                connected=True,
                status=OdooConnectionStatus.CONNECTED,
                odoo_version=version_info.get("server_version_info", [None])[0],
                server_version=version_info.get("server_version"),
                database=self.database,
                protocol_version=version_info.get("protocol_version"),
                uid=uid,
                error=None,
            )

        except Exception as e:
            logger.error(f"Odoo connection test failed: {e}")
            return OdooStatusResponse(
                connected=False,
                status=OdooConnectionStatus.ERROR,
                odoo_version=None,
                server_version=None,
                database=self.database,
                protocol_version=None,
                uid=None,
                error=str(e),
            )

    async def _execute_kw(
        self,
        model: str,
        method: str,
        args: List[Any],
        kwargs: Optional[Dict[str, Any]] = None,
    ) -> Any:
        """
        Execute Odoo model method via XML-RPC.

        Args:
            model: Odoo model name (e.g., 'ir.module.module')
            method: Method name (e.g., 'search_read')
            args: Positional arguments
            kwargs: Keyword arguments

        Returns:
            Method result

        Raises:
            ConnectionError: If not authenticated or call fails
        """
        if self.uid is None:
            await self.authenticate()

        try:
            obj = self._get_object_proxy()
            result = obj.execute_kw(
                self.database,
                self.uid,
                self.password,
                model,
                method,
                args,
                kwargs or {},
            )
            return result

        except Exception as e:
            logger.error(f"Odoo execute_kw error ({model}.{method}): {e}")
            raise ConnectionError(f"Failed to execute {model}.{method}: {e}")

    async def list_modules(
        self,
        state_filter: Optional[OdooModuleState] = None,
        name_filter: Optional[str] = None,
    ) -> List[OdooModuleInfo]:
        """
        List Odoo modules with optional filters.

        Args:
            state_filter: Filter by module state
            name_filter: Filter by module name (partial match)

        Returns:
            List of OdooModuleInfo objects
        """
        try:
            # Build domain filter
            domain = []
            if state_filter:
                domain.append(("state", "=", state_filter.value))
            if name_filter:
                domain.append(("name", "ilike", name_filter))

            # Query modules
            modules = await self._execute_kw(
                "ir.module.module",
                "search_read",
                [domain],
                {
                    "fields": [
                        "name",
                        "shortdesc",
                        "state",
                        "latest_version",
                        "installed_version",
                        "summary",
                        "author",
                        "website",
                    ]
                },
            )

            # Convert to OdooModuleInfo
            result = []
            for mod in modules:
                # Get dependencies
                deps = await self._get_module_dependencies(mod["name"])

                result.append(
                    OdooModuleInfo(
                        name=mod["name"],
                        display_name=mod.get("shortdesc"),
                        state=self._parse_module_state(mod["state"]),
                        version=mod.get("latest_version"),
                        summary=mod.get("summary"),
                        author=mod.get("author"),
                        website=mod.get("website"),
                        depends=deps,
                        installed_version=mod.get("installed_version"),
                        latest_version=mod.get("latest_version"),
                    )
                )

            logger.info(f"Listed {len(result)} Odoo modules")
            return result

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
            modules = await self._execute_kw(
                "ir.module.module",
                "search_read",
                [[("name", "=", module_name)]],
                {
                    "fields": [
                        "name",
                        "shortdesc",
                        "state",
                        "latest_version",
                        "installed_version",
                        "summary",
                        "author",
                        "website",
                    ],
                    "limit": 1,
                },
            )

            if not modules:
                logger.warning(f"Module '{module_name}' not found in Odoo")
                return None

            mod = modules[0]
            deps = await self._get_module_dependencies(module_name)

            return OdooModuleInfo(
                name=mod["name"],
                display_name=mod.get("shortdesc"),
                state=self._parse_module_state(mod["state"]),
                version=mod.get("latest_version"),
                summary=mod.get("summary"),
                author=mod.get("author"),
                website=mod.get("website"),
                depends=deps,
                installed_version=mod.get("installed_version"),
                latest_version=mod.get("latest_version"),
            )

        except Exception as e:
            logger.error(f"Failed to get module info for '{module_name}': {e}")
            return None

    async def install_module(self, module_name: str) -> bool:
        """
        Install an Odoo module.

        Args:
            module_name: Technical module name

        Returns:
            True if installation initiated successfully

        Raises:
            ConnectionError: If installation fails
        """
        try:
            # Find module ID
            module_ids = await self._execute_kw(
                "ir.module.module",
                "search",
                [[("name", "=", module_name)]],
            )

            if not module_ids:
                raise ConnectionError(f"Module '{module_name}' not found")

            # Trigger installation
            await self._execute_kw(
                "ir.module.module",
                "button_immediate_install",
                [module_ids],
            )

            logger.info(f"Odoo module '{module_name}' installation initiated")
            return True

        except Exception as e:
            logger.error(f"Failed to install module '{module_name}': {e}")
            raise ConnectionError(f"Installation failed: {e}")

    async def upgrade_module(self, module_name: str) -> bool:
        """
        Upgrade an Odoo module.

        Args:
            module_name: Technical module name

        Returns:
            True if upgrade initiated successfully

        Raises:
            ConnectionError: If upgrade fails
        """
        try:
            # Find module ID
            module_ids = await self._execute_kw(
                "ir.module.module",
                "search",
                [[("name", "=", module_name)]],
            )

            if not module_ids:
                raise ConnectionError(f"Module '{module_name}' not found")

            # Trigger upgrade
            await self._execute_kw(
                "ir.module.module",
                "button_immediate_upgrade",
                [module_ids],
            )

            logger.info(f"Odoo module '{module_name}' upgrade initiated")
            return True

        except Exception as e:
            logger.error(f"Failed to upgrade module '{module_name}': {e}")
            raise ConnectionError(f"Upgrade failed: {e}")

    async def uninstall_module(self, module_name: str) -> bool:
        """
        Uninstall an Odoo module.

        Args:
            module_name: Technical module name

        Returns:
            True if uninstallation initiated successfully

        Raises:
            ConnectionError: If uninstallation fails
        """
        try:
            # Find module ID
            module_ids = await self._execute_kw(
                "ir.module.module",
                "search",
                [[("name", "=", module_name)]],
            )

            if not module_ids:
                raise ConnectionError(f"Module '{module_name}' not found")

            # Trigger uninstall
            await self._execute_kw(
                "ir.module.module",
                "button_immediate_uninstall",
                [module_ids],
            )

            logger.info(f"Odoo module '{module_name}' uninstallation initiated")
            return True

        except Exception as e:
            logger.error(f"Failed to uninstall module '{module_name}': {e}")
            raise ConnectionError(f"Uninstallation failed: {e}")

    async def _get_module_dependencies(self, module_name: str) -> List[str]:
        """
        Get module dependencies.

        Args:
            module_name: Technical module name

        Returns:
            List of dependency module names
        """
        try:
            deps = await self._execute_kw(
                "ir.module.module.dependency",
                "search_read",
                [[("module_id.name", "=", module_name)]],
                {"fields": ["name"]},
            )

            return [dep["name"] for dep in deps]

        except Exception as e:
            logger.warning(f"Failed to get dependencies for '{module_name}': {e}")
            return []

    @staticmethod
    def _parse_module_state(state_str: str) -> OdooModuleState:
        """
        Parse Odoo module state string to enum.

        Args:
            state_str: State string from Odoo

        Returns:
            OdooModuleState enum value
        """
        state_map = {
            "uninstalled": OdooModuleState.UNINSTALLED,
            "installed": OdooModuleState.INSTALLED,
            "to install": OdooModuleState.TO_INSTALL,
            "to upgrade": OdooModuleState.TO_UPGRADE,
            "to remove": OdooModuleState.TO_REMOVE,
        }

        return state_map.get(state_str, OdooModuleState.UNKNOWN)
