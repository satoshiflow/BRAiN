"""
Auto-scaling background worker for cluster system.

This worker periodically checks all active clusters for scaling needs
and triggers scaling operations based on configured metrics.
"""
import asyncio
import logging
from datetime import datetime
from typing import List

from app.modules.cluster_system.service import ClusterService
from app.modules.cluster_system.models import Cluster, ClusterStatus
from sqlalchemy.ext.asyncio import AsyncSession
from app.core.db import get_session

logger = logging.getLogger(__name__)


class AutoscalerWorker:
    """Background worker that checks all active clusters for scaling needs."""
    
    def __init__(self, check_interval: int = 60):
        self.check_interval = check_interval  # seconds
        self.running = False
        self.service = None
        self._schema_missing_logged = False
    
    async def start(self):
        """Start the autoscaling loop."""
        self.running = True
        logger.info(f"🔄 Autoscaler started (interval: {self.check_interval}s)")
        
        while self.running:
            try:
                await self._check_all_clusters()
            except Exception as e:
                logger.error(f"❌ Error in autoscale loop: {e}", exc_info=True)
            
            await asyncio.sleep(self.check_interval)
    
    async def _check_all_clusters(self):
        """Check all active clusters for scaling needs."""
        from sqlalchemy import select
        from sqlalchemy.exc import ProgrammingError
        
        try:
            async with get_session() as db:
                self.service = ClusterService(db)
                
                # Get all active clusters
                try:
                    result = await db.execute(
                        select(Cluster).where(Cluster.status == ClusterStatus.ACTIVE)
                    )
                    clusters = result.scalars().all()
                except ProgrammingError as e:
                    error_text = str(e)
                    if (
                        "relation \"clusters\" does not exist" in error_text
                        or "type \"clusterstatus\" does not exist" in error_text
                    ):
                        if not self._schema_missing_logged:
                            logger.warning("⚠️  Cluster schema not ready. Skipping auto-scaling until migrations are aligned.")
                            self._schema_missing_logged = True
                        else:
                            logger.debug("Cluster schema still unavailable; autoscaling skipped")
                        return
                    raise
                
                if clusters:
                    logger.debug(f"🔍 Checking {len(clusters)} active clusters for scaling needs")
                
                for cluster in clusters:
                    try:
                        new_target = await self.service.check_scaling_needed(cluster.id)
                        
                        if new_target and new_target != cluster.current_workers:
                            logger.info(f"🚀 Scaling cluster {cluster.id}: {cluster.current_workers} -> {new_target}")
                            
                            from app.modules.cluster_system.schemas import ClusterScale
                            await self.service.scale_cluster(
                                cluster.id, 
                                ClusterScale(target_workers=new_target, reason="Auto-scaling triggered")
                            )
                    
                    except Exception as e:
                        logger.error(f"❌ Error scaling cluster {cluster.id}: {e}", exc_info=True)
        except Exception as e:
            logger.error(f"❌ Error in autoscale loop: {e}", exc_info=True)
    
    def stop(self):
        """Stop the autoscaling loop."""
        self.running = False
        logger.info("🛑 Autoscaler stopped")


# Singleton instance
_autoscaler = None


async def start_autoscaler(check_interval: int = 60):
    """Start the global autoscaler worker."""
    global _autoscaler
    if _autoscaler is None:
        _autoscaler = AutoscalerWorker(check_interval)
        await _autoscaler.start()


def stop_autoscaler():
    """Stop the global autoscaler worker."""
    global _autoscaler
    if _autoscaler:
        _autoscaler.stop()
        _autoscaler = None
