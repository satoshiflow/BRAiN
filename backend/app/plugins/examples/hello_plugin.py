"""
Hello World Plugin Example

Simple example plugin demonstrating basic plugin structure.

This plugin:
- Shows minimal plugin implementation
- Demonstrates metadata definition
- Shows lifecycle hooks (on_load, on_enable, on_disable)
- Provides simple execute functionality

Created: 2025-12-20
Phase: 5 - Developer Experience & Advanced Features
"""

from __future__ import annotations

from typing import Any

from loguru import logger

from backend.app.plugins.base import GenericPlugin, PluginMetadata, PluginType


# ============================================================================
# Hello World Plugin
# ============================================================================

class HelloPlugin(GenericPlugin):
    """
    Simple hello world plugin.

    Demonstrates basic plugin structure and lifecycle.
    """

    def get_metadata(self) -> PluginMetadata:
        """Get plugin metadata."""
        return PluginMetadata(
            id="hello_plugin",
            name="Hello World Plugin",
            version="1.0.0",
            description="Simple example plugin that greets the world",
            author="BRAiN Team",
            plugin_type=PluginType.GENERIC,
            dependencies=[],
            config_schema={
                "type": "object",
                "properties": {
                    "greeting": {
                        "type": "string",
                        "default": "Hello",
                        "description": "Greeting message",
                    },
                    "name": {
                        "type": "string",
                        "default": "World",
                        "description": "Name to greet",
                    },
                },
            },
        )

    async def on_load(self):
        """Called when plugin is loaded."""
        logger.info(f"HelloPlugin loaded with config: {self.config}")

        # Validate configuration
        if "greeting" in self.config:
            if not isinstance(self.config["greeting"], str):
                raise ValueError("Greeting must be a string")

    async def on_enable(self):
        """Called when plugin is enabled."""
        logger.info("HelloPlugin enabled")

        # Perform initialization
        greeting = self.get_config("greeting", "Hello")
        name = self.get_config("name", "World")

        logger.info(f"{greeting}, {name}! Plugin is now active.")

    async def on_disable(self):
        """Called when plugin is disabled."""
        logger.info("HelloPlugin disabled")

    async def execute(self, *args, **kwargs) -> Any:
        """
        Execute plugin functionality.

        Args:
            name: Optional name to greet (overrides config)

        Returns:
            Greeting message
        """
        # Get name from args or config
        name = kwargs.get("name", self.get_config("name", "World"))
        greeting = self.get_config("greeting", "Hello")

        message = f"{greeting}, {name}!"

        logger.info(f"HelloPlugin executed: {message}")

        return {
            "message": message,
            "timestamp": __import__("time").time(),
            "plugin_id": self.get_metadata().id,
        }


# ============================================================================
# Usage Example
# ============================================================================

if __name__ == "__main__":
    # Example: Using the plugin programmatically
    import asyncio

    async def main():
        # Create plugin instance
        plugin = HelloPlugin(config={"greeting": "Hola", "name": "BRAiN"})

        # Load plugin
        await plugin.on_load()

        # Enable plugin
        await plugin.on_enable()

        # Execute plugin
        result = await plugin.execute(name="User")
        print(f"Result: {result}")

        # Disable plugin
        await plugin.on_disable()

    # Run example
    asyncio.run(main())
