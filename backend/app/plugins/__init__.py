"""
Plugin System Module

Extensible plugin architecture for BRAiN.

Features:
- Plugin discovery and loading
- Plugin lifecycle management (load, enable, disable, unload)
- Multiple plugin types (Agent, Mission, API, Middleware, Event Listener)
- Plugin configuration and validation
- Hook system for extensibility
- Hot reload support

Created: 2025-12-20
Phase: 5 - Developer Experience & Advanced Features
"""

from __future__ import annotations

from .base import (
    APIPlugin,
    AgentPlugin,
    BasePlugin,
    EventListenerPlugin,
    GenericPlugin,
    MiddlewarePlugin,
    MissionTypePlugin,
    PluginHook,
    PluginMetadata,
    PluginStatus,
    PluginType,
)
from .loader import PluginLoader
from .manager import PluginManager, get_plugin_manager
from .registry import PluginRegistry

__all__ = [
    # Base classes
    "BasePlugin",
    "AgentPlugin",
    "MissionTypePlugin",
    "APIPlugin",
    "MiddlewarePlugin",
    "EventListenerPlugin",
    "GenericPlugin",
    # Metadata
    "PluginMetadata",
    "PluginType",
    "PluginStatus",
    # Hook system
    "PluginHook",
    # Management
    "PluginManager",
    "PluginLoader",
    "PluginRegistry",
    "get_plugin_manager",
]
