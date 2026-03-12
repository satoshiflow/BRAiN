"""
Health Monitor System - Service Layer
"""

from __future__ import annotations

import asyncio
from datetime import datetime, timezone, timedelta
from typing import List, Optional, Dict, Any
from uuid import UUID

from loguru import logger
from sqlalchemy import select, desc, func
from sqlalchemy.ext.asyncio import AsyncSession

from .models import HealthCheckModel, HealthCheckHistoryModel, HealthStatus
from .schemas import (
    HealthCheckCreate, HealthCheckResponse, HealthStatusSummary,
    HealthCheckResult, HealthHistoryResponse
)


class HealthMonitorService:
    """Health monitoring service with EventStream integration."""
    
    def __init__(self, event_stream=None):
        self.event_stream = event_stream
        logger.info("🏥 Health Monitor Service initialized")
    
    async def _publish_event(self, event_type: str, service_name: str, data: Dict[str, Any] = None):
        """Publish event to EventStream if available."""
        if self.event_stream is None:
            return
        try:
            await self.event_stream.publish({
                "type": event_type,
                "service_name": service_name,
                "timestamp": datetime.utcnow().isoformat(),
                "data": data or {}
            })
        except Exception as e:
            logger.warning(f"Failed to publish event {event_type}: {e}")
    
    async def register_service(self, db: AsyncSession, service_data: HealthCheckCreate) -> HealthCheckModel:
        """Register a new service for health monitoring."""
        # Check if service already exists
        result = await db.execute(
            select(HealthCheckModel).where(HealthCheckModel.service_name == service_data.service_name)
        )
        existing = result.scalar_one_or_none()
        
        if existing:
            # Update existing
            existing.service_type = service_data.service_type
            existing.check_interval_seconds = service_data.check_interval_seconds
            existing.metadata = service_data.metadata
            await db.commit()
            await db.refresh(existing)
            logger.info(f"🔄 Updated health check for: {service_data.service_name}")
            return existing
        
        # Create new
        check = HealthCheckModel(
            service_name=service_data.service_name,
            service_type=service_data.service_type,
            check_interval_seconds=service_data.check_interval_seconds,
            metadata=service_data.metadata,
        )
        db.add(check)
        await db.commit()
        await db.refresh(check)
        
        logger.info(f"➕ Registered health check for: {service_data.service_name}")
        return check
    
    async def record_check(self, db: AsyncSession, result: HealthCheckResult) -> HealthCheckModel:
        """Record a health check result."""
        result = await db.execute(
            select(HealthCheckModel).where(HealthCheckModel.service_name == result.service_name)
        )
        check = result.scalar_one_or_none()
        
        if not check:
            logger.warning(f"Health check for unknown service: {result.service_name}")
            return None
        
        now = datetime.now(timezone.utc)
        previous_status = check.status
        
        # Update check stats
        check.last_check_at = now
        check.next_check_at = now + timedelta(seconds=check.check_interval_seconds)
        check.response_time_ms = result.response_time_ms
        check.total_checks += 1
        
        if result.error_message:
            check.error_message = result.error_message
            check.failed_checks += 1
            check.consecutive_failures += 1
            check.consecutive_successes = 0
            check.last_failure_at = now
        else:
            check.check_output = result.output
            check.consecutive_successes += 1
            check.consecutive_failures = 0
            check.last_healthy_at = now
        
        # Calculate uptime percentage
        if check.total_checks > 0:
            check.uptime_percentage = ((check.total_checks - check.failed_checks) / check.total_checks) * 100
        
        # Determine status based on consecutive failures
        if check.consecutive_failures >= 3:
            new_status = HealthStatus.UNHEALTHY
        elif check.consecutive_failures >= 1:
            new_status = HealthStatus.DEGRADED
        elif check.consecutive_successes >= 2:
            new_status = HealthStatus.HEALTHY
        else:
            new_status = HealthStatus.UNKNOWN
        
        # Handle status change
        if new_status != previous_status:
            check.previous_status = previous_status
            check.status = new_status
            check.status_changed_at = now
            
            if new_status == HealthStatus.HEALTHY and previous_status in (HealthStatus.DEGRADED, HealthStatus.UNHEALTHY):
                # Recovery
                downtime = None
                if check.last_failure_at:
                    downtime = (now - check.last_failure_at).total_seconds()
                logger.info(f"✅ Service {check.service_name} recovered from {previous_status.value}")
                await self._publish_event("health.recovered", check.service_name, {
                    "previous_status": previous_status.value,
                    "downtime_seconds": downtime
                })
            elif new_status in (HealthStatus.DEGRADED, HealthStatus.UNHEALTHY):
                # Degradation
                event_type = "health.critical" if new_status == HealthStatus.UNHEALTHY else "health.degraded"
                logger.warning(f"⚠️ Service {check.service_name} is now {new_status.value}")
                await self._publish_event(event_type, check.service_name, {
                    "previous_status": previous_status.value if previous_status else None,
                    "error_message": result.error_message,
                    "consecutive_failures": check.consecutive_failures
                })
        
        await db.commit()
        await db.refresh(check)
        
        # Publish periodic check event
        await self._publish_event("health.check", check.service_name, {
            "status": check.status.value,
            "response_time_ms": check.response_time_ms
        })
        
        # Add to history
        history = HealthCheckHistoryModel(
            service_name=check.service_name,
            status=check.status,
            response_time_ms=check.response_time_ms,
            error_message=check.error_message,
        )
        db.add(history)
        await db.commit()
        
        return check
    
    async def get_status(self, db: AsyncSession) -> HealthStatusSummary:
        """Get overall health status summary."""
        result = await db.execute(select(HealthCheckModel))
        services = result.scalars().all()
        
        # Count by status
        healthy = sum(1 for s in services if s.status == HealthStatus.HEALTHY)
        degraded = sum(1 for s in services if s.status == HealthStatus.DEGRADED)
        unhealthy = sum(1 for s in services if s.status == HealthStatus.UNHEALTHY)
        unknown = sum(1 for s in services if s.status == HealthStatus.UNKNOWN)
        
        # Determine overall status
        if unhealthy > 0:
            overall = HealthStatus.UNHEALTHY
        elif degraded > 0:
            overall = HealthStatus.DEGRADED
        elif healthy > 0:
            overall = HealthStatus.HEALTHY
        else:
            overall = HealthStatus.UNKNOWN
        
        return HealthStatusSummary(
            overall_status=overall,
            total_services=len(services),
            healthy_count=healthy,
            degraded_count=degraded,
            unhealthy_count=unhealthy,
            unknown_count=unknown,
            services=[HealthCheckResponse.model_validate(s) for s in services],
        )
    
    async def get_service(self, db: AsyncSession, service_name: str) -> Optional[HealthCheckModel]:
        """Get health check for a specific service."""
        result = await db.execute(
            select(HealthCheckModel).where(HealthCheckModel.service_name == service_name)
        )
        return result.scalar_one_or_none()
    
    async def get_history(
        self,
        db: AsyncSession,
        service_name: str,
        limit: int = 100
    ) -> HealthHistoryResponse:
        """Get health check history for a service."""
        result = await db.execute(
            select(HealthCheckHistoryModel)
            .where(HealthCheckHistoryModel.service_name == service_name)
            .order_by(desc(HealthCheckHistoryModel.checked_at))
            .limit(limit)
        )
        entries = result.scalars().all()
        
        return HealthHistoryResponse(
            service_name=service_name,
            entries=[HealthHistoryEntry.model_validate(e) for e in entries],
            total=len(entries)
        )
    
    async def check_all_services(self, db: AsyncSession) -> List[HealthCheckResult]:
        """Run health checks on all registered services."""
        result = await db.execute(select(HealthCheckModel))
        services = result.scalars().all()
        
        results = []
        for service in services:
            # Perform actual health check
            check_result = await self._perform_health_check(service)
            await self.record_check(db, check_result)
            results.append(check_result)
        
        return results
    
    async def _perform_health_check(self, service: HealthCheckModel) -> HealthCheckResult:
        """Perform actual health check based on service type."""
        from .schemas import HealthCheckResult, HealthStatus
        import time
        
        start = time.time()
        
        try:
            if service.service_type == "database":
                # Database health check: attempt simple query
                status, error = await self._check_database()
            elif service.service_type == "cache":
                # Cache health check: attempt Redis ping
                status, error = await self._check_cache()
            elif service.service_type == "external":
                # External API check: use metadata for endpoint if provided
                status, error = await self._check_external(service)
            else:
                # Internal service: mark as healthy by default (no check implemented)
                status = HealthStatus.HEALTHY
                error = None
            
            response_time = (time.time() - start) * 1000
            
            return HealthCheckResult(
                service_name=service.service_name,
                status=status,
                response_time_ms=response_time,
                error_message=error,
                output="Check passed" if status == HealthStatus.HEALTHY else "Check failed"
            )
        except Exception as e:
            return HealthCheckResult(
                service_name=service.service_name,
                status=HealthStatus.UNHEALTHY,
                response_time_ms=(time.time() - start) * 1000,
                error_message=str(e),
                output="Check failed"
            )
    
    async def _check_database(self) -> tuple[HealthStatus, Optional[str]]:
        """Check database connectivity."""
        try:
            from app.core.database import AsyncSessionLocal
            async with AsyncSessionLocal() as db:
                # Simple ping query
                from sqlalchemy import text
                await db.execute(text("SELECT 1"))
            return HealthStatus.HEALTHY, None
        except Exception as e:
            logger.error(f"[HealthMonitor] Database check failed: {e}")
            return HealthStatus.UNHEALTHY, str(e)
    
    async def _check_cache(self) -> tuple[HealthStatus, Optional[str]]:
        """Check Redis cache connectivity."""
        try:
            from app.core.redis_client import get_redis
            redis = await get_redis()
            await redis.ping()
            return HealthStatus.HEALTHY, None
        except Exception as e:
            logger.error(f"[HealthMonitor] Cache check failed: {e}")
            return HealthStatus.UNHEALTHY, str(e)
    
    async def _check_external(self, service: HealthCheckModel) -> tuple[HealthStatus, Optional[str]]:
        """Check external service via HTTP probe."""
        try:
            # Check if metadata contains probe URL
            if not service.metadata or "probe_url" not in service.metadata:
                logger.debug(f"[HealthMonitor] No probe_url for {service.service_name}, skipping")
                return HealthStatus.UNKNOWN, "No probe URL configured"
            
            import httpx
            probe_url = service.metadata["probe_url"]
            timeout = service.metadata.get("timeout_seconds", 5)
            
            async with httpx.AsyncClient() as client:
                response = await client.get(probe_url, timeout=timeout)
                if response.status_code == 200:
                    return HealthStatus.HEALTHY, None
                else:
                    return HealthStatus.DEGRADED, f"HTTP {response.status_code}"
        except Exception as e:
            logger.error(f"[HealthMonitor] External check failed for {service.service_name}: {e}")
            return HealthStatus.UNHEALTHY, str(e)


_service: Optional[HealthMonitorService] = None

def get_health_monitor_service(event_stream=None) -> HealthMonitorService:
    """Get or create the health monitor service singleton."""
    global _service
    if _service is None:
        _service = HealthMonitorService(event_stream=event_stream)
    return _service
