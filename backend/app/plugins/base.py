"""
Plugin Base Classes

Abstract base classes for BRAiN plugins.

Plugin Types:
- AgentPlugin - Custom agent implementations
- MissionTypePlugin - Custom mission type handlers
- APIPlugin - Custom API endpoint extensions
- MiddlewarePlugin - Request/response middleware
- EventListenerPlugin - Event system listeners

Created: 2025-12-20
Phase: 5 - Developer Experience & Advanced Features
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from enum import Enum
from typing import Any, Callable, Dict, List, Optional

from fastapi import APIRouter
from pydantic import BaseModel, Field


# ============================================================================
# Plugin Metadata
# ============================================================================

class PluginType(str, Enum):
    """Plugin type enumeration."""

    AGENT = "agent"
    MISSION_TYPE = "mission_type"
    API = "api"
    MIDDLEWARE = "middleware"
    EVENT_LISTENER = "event_listener"
    GENERIC = "generic"


class PluginStatus(str, Enum):
    """Plugin status enumeration."""

    LOADED = "loaded"
    ENABLED = "enabled"
    DISABLED = "disabled"
    ERROR = "error"


class PluginMetadata(BaseModel):
    """Plugin metadata model."""

    id: str = Field(..., description="Unique plugin identifier")
    name: str = Field(..., description="Human-readable plugin name")
    version: str = Field(..., description="Plugin version (semver)")
    description: str = Field(..., description="Plugin description")
    author: str = Field(default="Unknown", description="Plugin author")
    plugin_type: PluginType = Field(..., description="Plugin type")
    dependencies: List[str] = Field(default_factory=list, description="Plugin dependencies")
    config_schema: Optional[Dict[str, Any]] = Field(None, description="Configuration schema")


# ============================================================================
# Base Plugin Class
# ============================================================================

class BasePlugin(ABC):
    """
    Abstract base class for all plugins.

    All plugins must inherit from this class and implement required methods.
    """

    def __init__(self, config: Optional[Dict[str, Any]] = None):
        """
        Initialize plugin.

        Args:
            config: Plugin configuration dictionary
        """
        self.config = config or {}
        self._metadata: Optional[PluginMetadata] = None
        self._status = PluginStatus.LOADED
        self._error: Optional[str] = None

    @abstractmethod
    def get_metadata(self) -> PluginMetadata:
        """
        Get plugin metadata.

        Returns:
            Plugin metadata with id, name, version, etc.
        """
        pass

    @abstractmethod
    async def on_load(self):
        """
        Called when plugin is loaded.

        Use this to initialize resources, validate configuration, etc.
        """
        pass

    @abstractmethod
    async def on_enable(self):
        """
        Called when plugin is enabled.

        Use this to start background tasks, register handlers, etc.
        """
        pass

    @abstractmethod
    async def on_disable(self):
        """
        Called when plugin is disabled.

        Use this to stop background tasks, cleanup resources, etc.
        """
        pass

    async def on_unload(self):
        """
        Called when plugin is unloaded.

        Override this to perform cleanup before plugin removal.
        """
        pass

    def get_status(self) -> PluginStatus:
        """Get current plugin status."""
        return self._status

    def set_status(self, status: PluginStatus):
        """Set plugin status."""
        self._status = status

    def get_error(self) -> Optional[str]:
        """Get last error message."""
        return self._error

    def set_error(self, error: str):
        """Set error message and status."""
        self._error = error
        self._status = PluginStatus.ERROR

    def get_config(self, key: str, default: Any = None) -> Any:
        """
        Get configuration value.

        Args:
            key: Configuration key
            default: Default value if key not found

        Returns:
            Configuration value
        """
        return self.config.get(key, default)


# ============================================================================
# Specialized Plugin Classes
# ============================================================================

class AgentPlugin(BasePlugin):
    """
    Plugin for custom agent implementations.

    Use this to add new agent types to BRAiN.
    """

    @abstractmethod
    def create_agent(self) -> Any:
        """
        Create agent instance.

        Returns:
            Agent instance (should inherit from BaseAgent)
        """
        pass

    @abstractmethod
    def get_agent_capabilities(self) -> List[str]:
        """
        Get agent capabilities.

        Returns:
            List of capability identifiers
        """
        pass


class MissionTypePlugin(BasePlugin):
    """
    Plugin for custom mission type handlers.

    Use this to add support for new mission types.
    """

    @abstractmethod
    def get_mission_type(self) -> str:
        """
        Get mission type identifier.

        Returns:
            Mission type string (e.g., "custom_analysis")
        """
        pass

    @abstractmethod
    async def execute_mission(self, mission: Any) -> Dict[str, Any]:
        """
        Execute mission.

        Args:
            mission: Mission instance

        Returns:
            Execution result
        """
        pass

    @abstractmethod
    def validate_mission_payload(self, payload: Dict[str, Any]) -> bool:
        """
        Validate mission payload.

        Args:
            payload: Mission payload

        Returns:
            True if valid, False otherwise
        """
        pass


class APIPlugin(BasePlugin):
    """
    Plugin for custom API endpoint extensions.

    Use this to add new API routes to BRAiN.
    """

    @abstractmethod
    def get_router(self) -> APIRouter:
        """
        Get FastAPI router with plugin endpoints.

        Returns:
            FastAPI APIRouter instance
        """
        pass

    @abstractmethod
    def get_prefix(self) -> str:
        """
        Get API route prefix.

        Returns:
            Route prefix (e.g., "/api/custom")
        """
        pass

    def get_tags(self) -> List[str]:
        """
        Get API route tags.

        Returns:
            List of route tags
        """
        return [self.get_metadata().id]


class MiddlewarePlugin(BasePlugin):
    """
    Plugin for request/response middleware.

    Use this to add custom middleware to the request pipeline.
    """

    @abstractmethod
    async def process_request(self, request: Any) -> Any:
        """
        Process incoming request.

        Args:
            request: Starlette Request object

        Returns:
            Modified request or None to continue
        """
        pass

    @abstractmethod
    async def process_response(self, request: Any, response: Any) -> Any:
        """
        Process outgoing response.

        Args:
            request: Starlette Request object
            response: Starlette Response object

        Returns:
            Modified response
        """
        pass


class EventListenerPlugin(BasePlugin):
    """
    Plugin for event system listeners.

    Use this to react to BRAiN system events.
    """

    @abstractmethod
    def get_event_subscriptions(self) -> List[str]:
        """
        Get event channel subscriptions.

        Returns:
            List of event channels to subscribe to
        """
        pass

    @abstractmethod
    async def on_event(self, event_type: str, event_data: Dict[str, Any]):
        """
        Handle event.

        Args:
            event_type: Event type identifier
            event_data: Event payload
        """
        pass


class GenericPlugin(BasePlugin):
    """
    Generic plugin for custom functionality.

    Use this for plugins that don't fit other categories.
    """

    @abstractmethod
    async def execute(self, *args, **kwargs) -> Any:
        """
        Execute plugin functionality.

        Args:
            *args: Positional arguments
            **kwargs: Keyword arguments

        Returns:
            Execution result
        """
        pass


# ============================================================================
# Plugin Hook System
# ============================================================================

class PluginHook:
    """
    Plugin hook for extending core functionality.

    Hooks allow plugins to register callbacks for specific events.
    """

    def __init__(self, name: str):
        """
        Initialize hook.

        Args:
            name: Hook identifier
        """
        self.name = name
        self.callbacks: List[Callable] = []

    def register(self, callback: Callable):
        """
        Register callback for this hook.

        Args:
            callback: Callback function
        """
        if callback not in self.callbacks:
            self.callbacks.append(callback)

    def unregister(self, callback: Callable):
        """
        Unregister callback.

        Args:
            callback: Callback function
        """
        if callback in self.callbacks:
            self.callbacks.remove(callback)

    async def execute(self, *args, **kwargs) -> List[Any]:
        """
        Execute all registered callbacks.

        Args:
            *args: Positional arguments
            **kwargs: Keyword arguments

        Returns:
            List of callback results
        """
        results = []
        for callback in self.callbacks:
            try:
                if asyncio.iscoroutinefunction(callback):
                    result = await callback(*args, **kwargs)
                else:
                    result = callback(*args, **kwargs)
                results.append(result)
            except Exception as e:
                # Log error but continue with other callbacks
                results.append({"error": str(e)})
        return results

    def clear(self):
        """Clear all registered callbacks."""
        self.callbacks.clear()


# ============================================================================
# Import asyncio
# ============================================================================

import asyncio


# ============================================================================
# Exports
# ============================================================================

__all__ = [
    "PluginType",
    "PluginStatus",
    "PluginMetadata",
    "BasePlugin",
    "AgentPlugin",
    "MissionTypePlugin",
    "APIPlugin",
    "MiddlewarePlugin",
    "EventListenerPlugin",
    "GenericPlugin",
    "PluginHook",
]
