"""
Plugin Registry

Tracks and manages registered plugins.

Created: 2025-12-20
Phase: 5 - Developer Experience & Advanced Features
"""

from __future__ import annotations

from typing import Dict, List, Optional

from .base import BasePlugin, PluginStatus, PluginType


# ============================================================================
# Plugin Registry
# ============================================================================

class PluginRegistry:
    """
    Plugin registration and tracking system.

    Maintains registry of all plugins and their state.
    """

    def __init__(self):
        """Initialize plugin registry."""
        self.plugins: Dict[str, BasePlugin] = {}

    # ========================================================================
    # Registration
    # ========================================================================

    def register(self, plugin_id: str, plugin: BasePlugin):
        """
        Register plugin.

        Args:
            plugin_id: Plugin identifier
            plugin: Plugin instance

        Raises:
            ValueError: If plugin_id already registered
        """
        if plugin_id in self.plugins:
            raise ValueError(f"Plugin already registered: {plugin_id}")

        self.plugins[plugin_id] = plugin

    def unregister(self, plugin_id: str) -> bool:
        """
        Unregister plugin.

        Args:
            plugin_id: Plugin identifier

        Returns:
            True if unregistered, False if not found
        """
        if plugin_id not in self.plugins:
            return False

        del self.plugins[plugin_id]
        return True

    # ========================================================================
    # Queries
    # ========================================================================

    def get(self, plugin_id: str) -> Optional[BasePlugin]:
        """
        Get plugin by ID.

        Args:
            plugin_id: Plugin identifier

        Returns:
            Plugin instance or None
        """
        return self.plugins.get(plugin_id)

    def exists(self, plugin_id: str) -> bool:
        """
        Check if plugin exists.

        Args:
            plugin_id: Plugin identifier

        Returns:
            True if registered
        """
        return plugin_id in self.plugins

    def list(
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
        plugins = list(self.plugins.values())

        # Filter by type
        if plugin_type:
            plugins = [
                p for p in plugins
                if p.get_metadata().plugin_type == plugin_type
            ]

        # Filter by status
        if status:
            plugins = [
                p for p in plugins
                if p.get_status() == status
            ]

        return plugins

    def count(self) -> int:
        """
        Get total plugin count.

        Returns:
            Number of registered plugins
        """
        return len(self.plugins)

    def get_ids(self) -> List[str]:
        """
        Get all plugin IDs.

        Returns:
            List of plugin identifiers
        """
        return list(self.plugins.keys())

    # ========================================================================
    # Statistics
    # ========================================================================

    def get_stats(self) -> Dict[str, int]:
        """
        Get registry statistics.

        Returns:
            Statistics dictionary
        """
        plugins = list(self.plugins.values())

        # Count by status
        status_counts = {}
        for status in PluginStatus:
            status_counts[status.value] = len([
                p for p in plugins
                if p.get_status() == status
            ])

        # Count by type
        type_counts = {}
        for plugin_type in PluginType:
            type_counts[plugin_type.value] = len([
                p for p in plugins
                if p.get_metadata().plugin_type == plugin_type
            ])

        return {
            "total": len(plugins),
            "by_status": status_counts,
            "by_type": type_counts,
        }

    # ========================================================================
    # Bulk Operations
    # ========================================================================

    def clear(self):
        """Clear all registered plugins."""
        self.plugins.clear()


# ============================================================================
# Exports
# ============================================================================

__all__ = ["PluginRegistry"]
