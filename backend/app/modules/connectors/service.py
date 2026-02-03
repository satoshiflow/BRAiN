"""
Connectors Module - ConnectorService

Central registry and lifecycle management for all connectors.
Singleton pattern via get_connector_service().
"""

from __future__ import annotations

import asyncio
import time
from typing import Any, Dict, List, Optional

from loguru import logger

from app.modules.connectors.base_connector import BaseConnector
from app.modules.connectors.schemas import (
    ConnectorHealth,
    ConnectorInfo,
    ConnectorStats,
    ConnectorStatus,
    ConnectorType,
)


class ConnectorService:
    """
    Central service for connector registration, lifecycle, and health.

    Responsibilities:
    - Register/unregister connectors
    - Start/stop connectors
    - Health monitoring
    - Statistics aggregation
    """

    def __init__(self) -> None:
        self._connectors: Dict[str, BaseConnector] = {}
        self._started_at: Optional[float] = None
        logger.info("ConnectorService initialized")

    # ========================================================================
    # Registry
    # ========================================================================

    def register(self, connector: BaseConnector) -> None:
        """Register a connector instance."""
        if connector.connector_id in self._connectors:
            logger.warning(
                f"Connector {connector.connector_id} already registered, replacing"
            )
        self._connectors[connector.connector_id] = connector
        logger.info(
            f"Registered connector: {connector.connector_id} "
            f"({connector.connector_type.value})"
        )

    def unregister(self, connector_id: str) -> bool:
        """Unregister a connector. Returns True if found and removed."""
        if connector_id in self._connectors:
            connector = self._connectors.pop(connector_id)
            logger.info(f"Unregistered connector: {connector_id}")
            return True
        return False

    def get(self, connector_id: str) -> Optional[BaseConnector]:
        """Get a connector by ID."""
        return self._connectors.get(connector_id)

    def list_connectors(self) -> List[ConnectorInfo]:
        """List all registered connectors with their info."""
        return [c.info for c in self._connectors.values()]

    def list_by_type(self, connector_type: ConnectorType) -> List[ConnectorInfo]:
        """List connectors of a specific type."""
        return [
            c.info
            for c in self._connectors.values()
            if c.connector_type == connector_type
        ]

    def list_active(self) -> List[ConnectorInfo]:
        """List only connected/active connectors."""
        return [
            c.info
            for c in self._connectors.values()
            if c.status == ConnectorStatus.CONNECTED
        ]

    # ========================================================================
    # Lifecycle
    # ========================================================================

    async def start_connector(self, connector_id: str) -> bool:
        """Start a specific connector."""
        connector = self._connectors.get(connector_id)
        if not connector:
            logger.error(f"Connector not found: {connector_id}")
            return False

        if connector.status == ConnectorStatus.CONNECTED:
            logger.warning(f"Connector {connector_id} already running")
            return True

        try:
            await connector.start()
            logger.info(f"Started connector: {connector_id}")
            return True
        except Exception as e:
            logger.error(f"Failed to start connector {connector_id}: {e}")
            return False

    async def stop_connector(self, connector_id: str) -> bool:
        """Stop a specific connector."""
        connector = self._connectors.get(connector_id)
        if not connector:
            logger.error(f"Connector not found: {connector_id}")
            return False

        if connector.status == ConnectorStatus.STOPPED:
            logger.warning(f"Connector {connector_id} already stopped")
            return True

        try:
            await connector.stop()
            logger.info(f"Stopped connector: {connector_id}")
            return True
        except Exception as e:
            logger.error(f"Failed to stop connector {connector_id}: {e}")
            return False

    async def restart_connector(self, connector_id: str) -> bool:
        """Restart a connector (stop then start)."""
        await self.stop_connector(connector_id)
        await asyncio.sleep(0.1)
        return await self.start_connector(connector_id)

    async def start_all(self) -> Dict[str, bool]:
        """Start all registered connectors. Returns {id: success}."""
        self._started_at = time.time()
        results = {}
        for cid in self._connectors:
            results[cid] = await self.start_connector(cid)
        return results

    async def stop_all(self) -> Dict[str, bool]:
        """Stop all running connectors. Returns {id: success}."""
        results = {}
        for cid in self._connectors:
            results[cid] = await self.stop_connector(cid)
        self._started_at = None
        return results

    # ========================================================================
    # Health & Stats
    # ========================================================================

    async def health_check(self, connector_id: str) -> Optional[ConnectorHealth]:
        """Run health check on a specific connector."""
        connector = self._connectors.get(connector_id)
        if not connector:
            return None
        try:
            return await connector.health_check()
        except Exception as e:
            return ConnectorHealth(
                connector_id=connector_id,
                status=ConnectorStatus.ERROR,
                error=str(e),
            )

    async def health_check_all(self) -> List[ConnectorHealth]:
        """Run health checks on all connectors."""
        results = []
        for cid in self._connectors:
            health = await self.health_check(cid)
            if health:
                results.append(health)
        return results

    def get_stats(self, connector_id: str) -> Optional[ConnectorStats]:
        """Get statistics for a specific connector."""
        connector = self._connectors.get(connector_id)
        if not connector:
            return None
        return connector.stats

    def get_aggregate_stats(self) -> Dict[str, Any]:
        """Get aggregated statistics across all connectors."""
        total_in = 0
        total_out = 0
        total_errors = 0
        active = 0
        by_type: Dict[str, int] = {}

        for c in self._connectors.values():
            stats = c.stats
            total_in += stats.messages_received
            total_out += stats.messages_sent
            total_errors += stats.errors
            if c.status == ConnectorStatus.CONNECTED:
                active += 1
            type_key = c.connector_type.value
            by_type[type_key] = by_type.get(type_key, 0) + 1

        return {
            "total_connectors": len(self._connectors),
            "active_connectors": active,
            "by_type": by_type,
            "total_messages_received": total_in,
            "total_messages_sent": total_out,
            "total_errors": total_errors,
            "uptime_seconds": (
                time.time() - self._started_at if self._started_at else 0.0
            ),
        }


# ============================================================================
# Singleton
# ============================================================================

_connector_service: Optional[ConnectorService] = None


def get_connector_service() -> ConnectorService:
    """Get the singleton ConnectorService instance."""
    global _connector_service
    if _connector_service is None:
        _connector_service = ConnectorService()
    return _connector_service
