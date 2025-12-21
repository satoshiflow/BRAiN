"""
Plugin Manager

Manages plugin lifecycle: loading, enabling, disabling, and unloading.

Created: 2025-12-20
Phase: 5 - Developer Experience & Advanced Features
"""

from __future__ import annotations

import asyncio
from pathlib import Path
from typing import Any, Dict, List, Optional, Type

from loguru import logger

from .base import (
    APIPlugin,
    AgentPlugin,
    BasePlugin,
    EventListenerPlugin,
    MiddlewarePlugin,
    MissionTypePlugin,
    PluginHook,
    PluginMetadata,
    PluginStatus,
    PluginType,
)
from .loader import PluginLoader
from .registry import PluginRegistry


# ============================================================================
# Plugin Manager
# ============================================================================

class PluginManager:
    """
    Central plugin management system.

    Handles plugin discovery, loading, lifecycle, and coordination.
    """

    def __init__(self, plugin_dirs: Optional[List[Path]] = None):
        """
        Initialize plugin manager.

        Args:
            plugin_dirs: List of directories to search for plugins
        """
        self.plugin_dirs = plugin_dirs or []
        self.registry = PluginRegistry()
        self.loader = PluginLoader()
        self.hooks: Dict[str, PluginHook] = {}
        self._initialized = False

    # ========================================================================
    # Initialization
    # ========================================================================

    async def initialize(self):
        """Initialize plugin system."""
        if self._initialized:
            return

        logger.info("Initializing plugin system")

        # Create standard hooks
        self._create_standard_hooks()

        # Discover and load plugins
        await self.discover_plugins()

        self._initialized = True
        logger.info(f"Plugin system initialized with {self.registry.count()} plugins")

    def _create_standard_hooks(self):
        """Create standard plugin hooks."""
        hook_names = [
            "app_startup",
            "app_shutdown",
            "mission_created",
            "mission_completed",
            "agent_started",
            "agent_stopped",
            "request_received",
            "response_sent",
        ]

        for name in hook_names:
            self.hooks[name] = PluginHook(name)

    # ========================================================================
    # Plugin Discovery
    # ========================================================================

    async def discover_plugins(self):
        """Discover plugins in configured directories."""
        logger.info(f"Discovering plugins in {len(self.plugin_dirs)} directories")

        for plugin_dir in self.plugin_dirs:
            if not plugin_dir.exists():
                logger.warning(f"Plugin directory does not exist: {plugin_dir}")
                continue

            plugins = self.loader.discover_plugins(plugin_dir)
            logger.info(f"Found {len(plugins)} plugins in {plugin_dir}")

            for plugin_class in plugins:
                await self._register_plugin_class(plugin_class)

    async def _register_plugin_class(self, plugin_class: Type[BasePlugin]):
        """
        Register plugin class.

        Args:
            plugin_class: Plugin class to register
        """
        try:
            # Create instance with empty config
            plugin = plugin_class({})

            # Get metadata
            metadata = plugin.get_metadata()

            # Register in registry
            self.registry.register(metadata.id, plugin)

            logger.info(f"Registered plugin: {metadata.name} v{metadata.version}")

        except Exception as e:
            logger.error(f"Failed to register plugin {plugin_class.__name__}: {e}")

    # ========================================================================
    # Plugin Loading
    # ========================================================================

    async def load_plugin(
        self, plugin_id: str, config: Optional[Dict[str, Any]] = None
    ) -> bool:
        """
        Load plugin by ID.

        Args:
            plugin_id: Plugin identifier
            config: Plugin configuration

        Returns:
            True if loaded successfully
        """
        plugin = self.registry.get(plugin_id)
        if not plugin:
            logger.error(f"Plugin not found: {plugin_id}")
            return False

        try:
            # Update config if provided
            if config:
                plugin.config.update(config)

            # Call on_load hook
            await plugin.on_load()

            # Update status
            plugin.set_status(PluginStatus.LOADED)

            logger.info(f"Loaded plugin: {plugin_id}")
            return True

        except Exception as e:
            error_msg = f"Failed to load plugin {plugin_id}: {e}"
            logger.error(error_msg)
            plugin.set_error(error_msg)
            return False

    async def load_plugin_from_file(
        self, file_path: Path, config: Optional[Dict[str, Any]] = None
    ) -> bool:
        """
        Load plugin from file.

        Args:
            file_path: Path to plugin file
            config: Plugin configuration

        Returns:
            True if loaded successfully
        """
        try:
            plugin_class = self.loader.load_plugin_from_file(file_path)
            await self._register_plugin_class(plugin_class)

            # Get plugin ID from instance
            plugin = plugin_class({})
            metadata = plugin.get_metadata()

            # Load with config
            return await self.load_plugin(metadata.id, config)

        except Exception as e:
            logger.error(f"Failed to load plugin from {file_path}: {e}")
            return False

    # ========================================================================
    # Plugin Enable/Disable
    # ========================================================================

    async def enable_plugin(self, plugin_id: str) -> bool:
        """
        Enable plugin.

        Args:
            plugin_id: Plugin identifier

        Returns:
            True if enabled successfully
        """
        plugin = self.registry.get(plugin_id)
        if not plugin:
            logger.error(f"Plugin not found: {plugin_id}")
            return False

        if plugin.get_status() == PluginStatus.ENABLED:
            logger.warning(f"Plugin already enabled: {plugin_id}")
            return True

        try:
            # Call on_enable hook
            await plugin.on_enable()

            # Register plugin-specific hooks
            await self._register_plugin_hooks(plugin)

            # Update status
            plugin.set_status(PluginStatus.ENABLED)

            logger.info(f"Enabled plugin: {plugin_id}")
            return True

        except Exception as e:
            error_msg = f"Failed to enable plugin {plugin_id}: {e}"
            logger.error(error_msg)
            plugin.set_error(error_msg)
            return False

    async def disable_plugin(self, plugin_id: str) -> bool:
        """
        Disable plugin.

        Args:
            plugin_id: Plugin identifier

        Returns:
            True if disabled successfully
        """
        plugin = self.registry.get(plugin_id)
        if not plugin:
            logger.error(f"Plugin not found: {plugin_id}")
            return False

        if plugin.get_status() == PluginStatus.DISABLED:
            logger.warning(f"Plugin already disabled: {plugin_id}")
            return True

        try:
            # Call on_disable hook
            await plugin.on_disable()

            # Unregister plugin hooks
            await self._unregister_plugin_hooks(plugin)

            # Update status
            plugin.set_status(PluginStatus.DISABLED)

            logger.info(f"Disabled plugin: {plugin_id}")
            return True

        except Exception as e:
            error_msg = f"Failed to disable plugin {plugin_id}: {e}"
            logger.error(error_msg)
            plugin.set_error(error_msg)
            return False

    # ========================================================================
    # Plugin Unloading
    # ========================================================================

    async def unload_plugin(self, plugin_id: str) -> bool:
        """
        Unload plugin.

        Args:
            plugin_id: Plugin identifier

        Returns:
            True if unloaded successfully
        """
        plugin = self.registry.get(plugin_id)
        if not plugin:
            logger.error(f"Plugin not found: {plugin_id}")
            return False

        try:
            # Disable first if enabled
            if plugin.get_status() == PluginStatus.ENABLED:
                await self.disable_plugin(plugin_id)

            # Call on_unload hook
            await plugin.on_unload()

            # Unregister from registry
            self.registry.unregister(plugin_id)

            logger.info(f"Unloaded plugin: {plugin_id}")
            return True

        except Exception as e:
            logger.error(f"Failed to unload plugin {plugin_id}: {e}")
            return False

    # ========================================================================
    # Plugin Hooks
    # ========================================================================

    async def _register_plugin_hooks(self, plugin: BasePlugin):
        """
        Register plugin-specific hooks.

        Args:
            plugin: Plugin instance
        """
        # Event listener plugins
        if isinstance(plugin, EventListenerPlugin):
            subscriptions = plugin.get_event_subscriptions()
            for event_type in subscriptions:
                if event_type not in self.hooks:
                    self.hooks[event_type] = PluginHook(event_type)
                self.hooks[event_type].register(plugin.on_event)

    async def _unregister_plugin_hooks(self, plugin: BasePlugin):
        """
        Unregister plugin hooks.

        Args:
            plugin: Plugin instance
        """
        # Event listener plugins
        if isinstance(plugin, EventListenerPlugin):
            subscriptions = plugin.get_event_subscriptions()
            for event_type in subscriptions:
                if event_type in self.hooks:
                    self.hooks[event_type].unregister(plugin.on_event)

    def get_hook(self, name: str) -> Optional[PluginHook]:
        """
        Get hook by name.

        Args:
            name: Hook identifier

        Returns:
            PluginHook instance or None
        """
        return self.hooks.get(name)

    async def execute_hook(self, name: str, *args, **kwargs) -> List[Any]:
        """
        Execute hook callbacks.

        Args:
            name: Hook identifier
            *args: Positional arguments
            **kwargs: Keyword arguments

        Returns:
            List of callback results
        """
        hook = self.get_hook(name)
        if not hook:
            return []

        return await hook.execute(*args, **kwargs)

    # ========================================================================
    # Plugin Queries
    # ========================================================================

    def get_plugin(self, plugin_id: str) -> Optional[BasePlugin]:
        """
        Get plugin by ID.

        Args:
            plugin_id: Plugin identifier

        Returns:
            Plugin instance or None
        """
        return self.registry.get(plugin_id)

    def list_plugins(
        self,
        plugin_type: Optional[PluginType] = None,
        status: Optional[PluginStatus] = None,
    ) -> List[BasePlugin]:
        """
        List plugins with optional filters.

        Args:
            plugin_type: Filter by plugin type
            status: Filter by status

        Returns:
            List of matching plugins
        """
        return self.registry.list(plugin_type=plugin_type, status=status)

    def get_plugin_metadata(self, plugin_id: str) -> Optional[PluginMetadata]:
        """
        Get plugin metadata.

        Args:
            plugin_id: Plugin identifier

        Returns:
            Plugin metadata or None
        """
        plugin = self.get_plugin(plugin_id)
        if not plugin:
            return None

        return plugin.get_metadata()

    def get_plugins_by_type(self, plugin_type: PluginType) -> List[BasePlugin]:
        """
        Get plugins by type.

        Args:
            plugin_type: Plugin type

        Returns:
            List of plugins
        """
        return self.registry.list(plugin_type=plugin_type)

    # ========================================================================
    # API Plugins
    # ========================================================================

    def get_api_routers(self) -> List[tuple[str, Any]]:
        """
        Get all API plugin routers.

        Returns:
            List of (prefix, router) tuples
        """
        routers = []

        api_plugins = self.get_plugins_by_type(PluginType.API)

        for plugin in api_plugins:
            if not isinstance(plugin, APIPlugin):
                continue

            if plugin.get_status() != PluginStatus.ENABLED:
                continue

            try:
                router = plugin.get_router()
                prefix = plugin.get_prefix()
                routers.append((prefix, router))
            except Exception as e:
                logger.error(f"Failed to get router from {plugin.get_metadata().id}: {e}")

        return routers

    # ========================================================================
    # Shutdown
    # ========================================================================

    async def shutdown(self):
        """Shutdown plugin system."""
        logger.info("Shutting down plugin system")

        # Execute shutdown hook
        await self.execute_hook("app_shutdown")

        # Disable all enabled plugins
        enabled_plugins = self.list_plugins(status=PluginStatus.ENABLED)
        for plugin in enabled_plugins:
            metadata = plugin.get_metadata()
            await self.disable_plugin(metadata.id)

        # Unload all loaded plugins
        all_plugins = self.list_plugins()
        for plugin in all_plugins:
            metadata = plugin.get_metadata()
            await self.unload_plugin(metadata.id)

        logger.info("Plugin system shutdown complete")


# ============================================================================
# Singleton Manager
# ============================================================================

_plugin_manager: Optional[PluginManager] = None


def get_plugin_manager() -> PluginManager:
    """Get global plugin manager instance."""
    global _plugin_manager
    if _plugin_manager is None:
        _plugin_manager = PluginManager()
    return _plugin_manager


# ============================================================================
# Exports
# ============================================================================

__all__ = ["PluginManager", "get_plugin_manager"]
