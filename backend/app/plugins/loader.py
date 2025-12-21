"""
Plugin Loader

Discovers and loads plugins from filesystem.

Created: 2025-12-20
Phase: 5 - Developer Experience & Advanced Features
"""

from __future__ import annotations

import importlib.util
import inspect
import sys
from pathlib import Path
from typing import List, Type

from loguru import logger

from .base import BasePlugin


# ============================================================================
# Plugin Loader
# ============================================================================

class PluginLoader:
    """
    Plugin discovery and loading system.

    Finds and loads plugin classes from Python files.
    """

    def __init__(self):
        """Initialize plugin loader."""
        self.loaded_modules: List[str] = []

    # ========================================================================
    # Plugin Discovery
    # ========================================================================

    def discover_plugins(self, plugin_dir: Path) -> List[Type[BasePlugin]]:
        """
        Discover plugins in directory.

        Args:
            plugin_dir: Directory to search

        Returns:
            List of plugin classes
        """
        plugins = []

        if not plugin_dir.exists() or not plugin_dir.is_dir():
            logger.warning(f"Plugin directory does not exist: {plugin_dir}")
            return plugins

        # Find all Python files
        python_files = list(plugin_dir.glob("**/*.py"))

        # Filter out __init__.py and files starting with _
        python_files = [
            f for f in python_files
            if f.name != "__init__.py" and not f.name.startswith("_")
        ]

        logger.debug(f"Found {len(python_files)} Python files in {plugin_dir}")

        for file_path in python_files:
            try:
                plugin_classes = self._load_plugins_from_file(file_path)
                plugins.extend(plugin_classes)
            except Exception as e:
                logger.error(f"Failed to load plugins from {file_path}: {e}")

        return plugins

    def _load_plugins_from_file(self, file_path: Path) -> List[Type[BasePlugin]]:
        """
        Load plugin classes from file.

        Args:
            file_path: Path to plugin file

        Returns:
            List of plugin classes found in file
        """
        plugins = []

        # Generate module name from file path
        module_name = self._generate_module_name(file_path)

        # Load module
        module = self._load_module_from_file(file_path, module_name)

        if not module:
            return plugins

        # Find plugin classes in module
        for name, obj in inspect.getmembers(module, inspect.isclass):
            # Check if it's a BasePlugin subclass (but not BasePlugin itself)
            if (
                issubclass(obj, BasePlugin)
                and obj is not BasePlugin
                and obj.__module__ == module_name
            ):
                logger.debug(f"Found plugin class: {name} in {file_path}")
                plugins.append(obj)

        return plugins

    # ========================================================================
    # Module Loading
    # ========================================================================

    def load_plugin_from_file(self, file_path: Path) -> Type[BasePlugin]:
        """
        Load single plugin from file.

        Args:
            file_path: Path to plugin file

        Returns:
            Plugin class

        Raises:
            ValueError: If no plugin class found or multiple found
        """
        plugins = self._load_plugins_from_file(file_path)

        if not plugins:
            raise ValueError(f"No plugin class found in {file_path}")

        if len(plugins) > 1:
            logger.warning(f"Multiple plugin classes found in {file_path}, using first one")

        return plugins[0]

    def _load_module_from_file(self, file_path: Path, module_name: str):
        """
        Load Python module from file.

        Args:
            file_path: Path to Python file
            module_name: Module name to use

        Returns:
            Loaded module or None
        """
        try:
            # Create module spec
            spec = importlib.util.spec_from_file_location(module_name, file_path)

            if not spec or not spec.loader:
                logger.error(f"Failed to create module spec for {file_path}")
                return None

            # Create module
            module = importlib.util.module_from_spec(spec)

            # Add to sys.modules
            sys.modules[module_name] = module

            # Execute module
            spec.loader.exec_module(module)

            # Track loaded module
            self.loaded_modules.append(module_name)

            logger.debug(f"Loaded module: {module_name}")
            return module

        except Exception as e:
            logger.error(f"Failed to load module from {file_path}: {e}")
            return None

    def _generate_module_name(self, file_path: Path) -> str:
        """
        Generate unique module name from file path.

        Args:
            file_path: Path to file

        Returns:
            Module name string
        """
        # Use relative path from plugins directory
        # Replace / with . and remove .py extension
        module_name = str(file_path.stem)

        # Add plugin prefix
        module_name = f"brain_plugin_{module_name}"

        # Make unique if already loaded
        counter = 1
        original_name = module_name
        while module_name in sys.modules:
            module_name = f"{original_name}_{counter}"
            counter += 1

        return module_name

    # ========================================================================
    # Hot Reload
    # ========================================================================

    def reload_plugin(self, plugin_class: Type[BasePlugin]) -> Type[BasePlugin]:
        """
        Reload plugin class.

        Args:
            plugin_class: Plugin class to reload

        Returns:
            Reloaded plugin class

        Raises:
            ValueError: If plugin module not found
        """
        module_name = plugin_class.__module__

        if module_name not in sys.modules:
            raise ValueError(f"Module {module_name} not loaded")

        try:
            # Reload module
            module = sys.modules[module_name]
            importlib.reload(module)

            # Find plugin class in reloaded module
            for name, obj in inspect.getmembers(module, inspect.isclass):
                if obj.__name__ == plugin_class.__name__:
                    logger.info(f"Reloaded plugin: {name}")
                    return obj

            raise ValueError(f"Plugin class {plugin_class.__name__} not found after reload")

        except Exception as e:
            logger.error(f"Failed to reload plugin {plugin_class.__name__}: {e}")
            raise

    # ========================================================================
    # Validation
    # ========================================================================

    def validate_plugin_class(self, plugin_class: Type[BasePlugin]) -> bool:
        """
        Validate plugin class structure.

        Args:
            plugin_class: Plugin class to validate

        Returns:
            True if valid
        """
        try:
            # Check if it's a class
            if not inspect.isclass(plugin_class):
                logger.error("Plugin must be a class")
                return False

            # Check if it inherits from BasePlugin
            if not issubclass(plugin_class, BasePlugin):
                logger.error("Plugin must inherit from BasePlugin")
                return False

            # Check if abstract methods are implemented
            abstract_methods = {
                name
                for name, method in inspect.getmembers(BasePlugin, inspect.ismethod)
                if getattr(method, "__isabstractmethod__", False)
            }

            implemented_methods = {
                name
                for name, method in inspect.getmembers(plugin_class, inspect.ismethod)
            }

            missing_methods = abstract_methods - implemented_methods

            if missing_methods:
                logger.error(f"Plugin missing required methods: {missing_methods}")
                return False

            # Try to instantiate with empty config
            try:
                instance = plugin_class({})
                metadata = instance.get_metadata()

                # Validate metadata
                if not metadata.id or not metadata.name or not metadata.version:
                    logger.error("Plugin metadata incomplete (missing id, name, or version)")
                    return False

            except Exception as e:
                logger.error(f"Failed to instantiate plugin: {e}")
                return False

            return True

        except Exception as e:
            logger.error(f"Plugin validation error: {e}")
            return False


# ============================================================================
# Exports
# ============================================================================

__all__ = ["PluginLoader"]
