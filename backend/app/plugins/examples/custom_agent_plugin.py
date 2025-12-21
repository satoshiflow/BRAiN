"""
Custom Agent Plugin Example

Example plugin that adds a custom agent to BRAiN.

This plugin:
- Demonstrates AgentPlugin implementation
- Shows how to create custom agents
- Integrates with existing agent system
- Provides custom capabilities

Created: 2025-12-20
Phase: 5 - Developer Experience & Advanced Features
"""

from __future__ import annotations

from typing import Any, Dict, List

from loguru import logger

from backend.app.plugins.base import AgentPlugin, PluginMetadata, PluginType


# ============================================================================
# Custom Data Analyst Agent
# ============================================================================

class CustomDataAnalystAgent:
    """
    Custom data analyst agent implementation.

    Note: In a real implementation, this would inherit from BaseAgent.
    This example shows the structure for demonstration purposes.
    """

    def __init__(self, config: Dict[str, Any]):
        """
        Initialize agent.

        Args:
            config: Agent configuration
        """
        self.config = config
        self.agent_id = "custom_data_analyst"
        self.name = "Custom Data Analyst"

    async def run(self, task: str) -> Dict[str, Any]:
        """
        Execute agent task.

        Args:
            task: Task description

        Returns:
            Execution result
        """
        logger.info(f"CustomDataAnalystAgent executing task: {task}")

        # Simulate data analysis
        result = {
            "task": task,
            "agent": self.agent_id,
            "analysis": f"Analyzed: {task}",
            "insights": [
                "Insight 1: Data shows positive trend",
                "Insight 2: No anomalies detected",
                "Insight 3: Prediction confidence: 85%",
            ],
            "metrics": {
                "accuracy": 0.85,
                "processing_time_ms": 125.3,
                "data_points_analyzed": 1000,
            },
        }

        logger.info(f"CustomDataAnalystAgent completed task: {result}")

        return result

    async def analyze_data(self, data: List[Any]) -> Dict[str, Any]:
        """
        Analyze data.

        Args:
            data: Data to analyze

        Returns:
            Analysis results
        """
        logger.info(f"Analyzing {len(data)} data points")

        return {
            "data_count": len(data),
            "summary": "Data analysis complete",
            "statistics": {
                "mean": sum(data) / len(data) if data else 0,
                "min": min(data) if data else 0,
                "max": max(data) if data else 0,
            },
        }


# ============================================================================
# Data Analyst Plugin
# ============================================================================

class DataAnalystPlugin(AgentPlugin):
    """
    Plugin that provides a custom data analyst agent.

    This plugin adds data analysis capabilities to BRAiN.
    """

    def get_metadata(self) -> PluginMetadata:
        """Get plugin metadata."""
        return PluginMetadata(
            id="data_analyst_plugin",
            name="Data Analyst Agent Plugin",
            version="1.0.0",
            description="Adds custom data analyst agent with advanced analytics capabilities",
            author="BRAiN Team",
            plugin_type=PluginType.AGENT,
            dependencies=[],
            config_schema={
                "type": "object",
                "properties": {
                    "analysis_depth": {
                        "type": "string",
                        "enum": ["basic", "intermediate", "advanced"],
                        "default": "intermediate",
                        "description": "Depth of analysis to perform",
                    },
                    "enable_ml": {
                        "type": "boolean",
                        "default": False,
                        "description": "Enable machine learning models",
                    },
                    "max_data_points": {
                        "type": "integer",
                        "default": 10000,
                        "description": "Maximum data points to analyze",
                    },
                },
            },
        )

    async def on_load(self):
        """Called when plugin is loaded."""
        logger.info("DataAnalystPlugin loaded")

        # Validate configuration
        analysis_depth = self.get_config("analysis_depth", "intermediate")
        if analysis_depth not in ["basic", "intermediate", "advanced"]:
            raise ValueError(f"Invalid analysis_depth: {analysis_depth}")

        max_data_points = self.get_config("max_data_points", 10000)
        if max_data_points < 1 or max_data_points > 1000000:
            raise ValueError(f"Invalid max_data_points: {max_data_points}")

    async def on_enable(self):
        """Called when plugin is enabled."""
        logger.info("DataAnalystPlugin enabled")

        # Initialize resources
        analysis_depth = self.get_config("analysis_depth", "intermediate")
        enable_ml = self.get_config("enable_ml", False)

        logger.info(f"Data analyst configured: depth={analysis_depth}, ml={enable_ml}")

        # In a real implementation, you might:
        # - Load ML models if enable_ml is True
        # - Initialize database connections
        # - Set up caching
        # - etc.

    async def on_disable(self):
        """Called when plugin is disabled."""
        logger.info("DataAnalystPlugin disabled")

        # Cleanup resources
        # - Unload ML models
        # - Close connections
        # - Clear caches
        # - etc.

    def create_agent(self) -> CustomDataAnalystAgent:
        """
        Create agent instance.

        Returns:
            Custom data analyst agent
        """
        agent = CustomDataAnalystAgent(config=self.config)

        logger.info(f"Created agent: {agent.agent_id}")

        return agent

    def get_agent_capabilities(self) -> List[str]:
        """
        Get agent capabilities.

        Returns:
            List of capabilities
        """
        capabilities = [
            "data_analysis",
            "statistical_analysis",
            "trend_detection",
            "anomaly_detection",
            "data_visualization",
        ]

        # Add ML capabilities if enabled
        if self.get_config("enable_ml", False):
            capabilities.extend([
                "predictive_modeling",
                "clustering",
                "classification",
            ])

        return capabilities


# ============================================================================
# Usage Example
# ============================================================================

if __name__ == "__main__":
    # Example: Using the plugin programmatically
    import asyncio

    async def main():
        # Create plugin instance
        plugin = DataAnalystPlugin(config={
            "analysis_depth": "advanced",
            "enable_ml": True,
            "max_data_points": 50000,
        })

        # Load plugin
        await plugin.on_load()

        # Enable plugin
        await plugin.on_enable()

        # Create agent
        agent = plugin.create_agent()

        # Get capabilities
        capabilities = plugin.get_agent_capabilities()
        print(f"Agent capabilities: {capabilities}")

        # Execute agent task
        result = await agent.run("Analyze user behavior patterns")
        print(f"Task result: {result}")

        # Analyze some data
        sample_data = [10, 20, 30, 40, 50, 45, 35, 25, 15, 5]
        analysis = await agent.analyze_data(sample_data)
        print(f"Data analysis: {analysis}")

        # Disable plugin
        await plugin.on_disable()

    # Run example
    asyncio.run(main())
