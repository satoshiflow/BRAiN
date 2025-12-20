"""
Comprehensive Audit Logging System for BRAiN Core.

Provides complete audit trail for:
- All API requests (endpoint, method, user, status, duration)
- Data changes (create, update, delete operations)
- User actions (login, logout, permission changes)
- Security events (failed auth, rate limits, suspicious activity)

Features:
- Structured JSON logging
- Async logging (non-blocking)
- Redis-based storage (fast, queryable)
- Automatic retention policy
- Full-text search capabilities
- Audit log API for querying

Usage:
    from app.core.audit import audit_log, AuditLogger, AuditAction

    # Log API request
    await audit_log.log_api_request(
        method="POST",
        endpoint="/api/missions/enqueue",
        user_id="user_123",
        status_code=200,
        duration_ms=45.3
    )

    # Log data change
    await audit_log.log_data_change(
        action=AuditAction.CREATE,
        resource_type="mission",
        resource_id="mission_123",
        user_id="user_123",
        changes={"status": "pending"}
    )

    # Decorator for automatic logging
    @audit_logged(action="create_mission", resource_type="mission")
    async def create_mission(mission_data: dict, user_id: str):
        # Function automatically logged
        pass
"""

from __future__ import annotations

import json
import time
from datetime import datetime, timedelta
from enum import Enum
from typing import Any, Dict, List, Optional
from functools import wraps

import redis.asyncio as redis
from pydantic import BaseModel, Field
from loguru import logger


# ============================================================================
# Models
# ============================================================================

class AuditAction(str, Enum):
    """Audit action types."""
    # API actions
    API_REQUEST = "api_request"

    # Data actions
    CREATE = "create"
    UPDATE = "update"
    DELETE = "delete"
    READ = "read"

    # Auth actions
    LOGIN = "login"
    LOGOUT = "logout"
    LOGIN_FAILED = "login_failed"
    TOKEN_REFRESH = "token_refresh"

    # Permission actions
    PERMISSION_GRANT = "permission_grant"
    PERMISSION_REVOKE = "permission_revoke"
    ROLE_ASSIGN = "role_assign"
    ROLE_REVOKE = "role_revoke"

    # Security events
    RATE_LIMIT_HIT = "rate_limit_hit"
    API_KEY_CREATED = "api_key_created"
    API_KEY_REVOKED = "api_key_revoked"
    SUSPICIOUS_ACTIVITY = "suspicious_activity"


class AuditLevel(str, Enum):
    """Audit log levels."""
    INFO = "info"
    WARNING = "warning"
    ERROR = "error"
    CRITICAL = "critical"


class AuditEntry(BaseModel):
    """Audit log entry."""
    id: str
    timestamp: datetime
    action: AuditAction
    level: AuditLevel = AuditLevel.INFO

    # User context
    user_id: Optional[str] = None
    principal_id: Optional[str] = None
    ip_address: Optional[str] = None

    # Request context
    method: Optional[str] = None
    endpoint: Optional[str] = None
    status_code: Optional[int] = None
    duration_ms: Optional[float] = None

    # Resource context
    resource_type: Optional[str] = None
    resource_id: Optional[str] = None
    changes: Optional[Dict[str, Any]] = None

    # Additional context
    metadata: Dict[str, Any] = Field(default_factory=dict)
    error: Optional[str] = None


# ============================================================================
# Audit Logger
# ============================================================================

class AuditLogger:
    """
    Comprehensive audit logging system.

    Stores audit logs in Redis for fast querying and automatic retention.
    """

    def __init__(
        self,
        redis_client: Optional[redis.Redis] = None,
        retention_days: int = 90
    ):
        """
        Initialize audit logger.

        Args:
            redis_client: Async Redis client
            retention_days: Number of days to retain logs (default: 90)
        """
        self._redis: Optional[redis.Redis] = redis_client
        self._initialized = False
        self.retention_days = retention_days

    async def _ensure_initialized(self):
        """Lazy initialization of Redis client."""
        if not self._initialized:
            if self._redis is None:
                from app.core.redis_client import get_redis
                self._redis = await get_redis()
            self._initialized = True

    def _make_entry_key(self, entry_id: str) -> str:
        """Generate Redis key for audit entry."""
        return f"brain:audit:entry:{entry_id}"

    def _make_index_key(self, index_type: str, index_value: str) -> str:
        """Generate Redis key for index."""
        return f"brain:audit:index:{index_type}:{index_value}"

    async def log(
        self,
        action: AuditAction,
        level: AuditLevel = AuditLevel.INFO,
        user_id: Optional[str] = None,
        principal_id: Optional[str] = None,
        ip_address: Optional[str] = None,
        method: Optional[str] = None,
        endpoint: Optional[str] = None,
        status_code: Optional[int] = None,
        duration_ms: Optional[float] = None,
        resource_type: Optional[str] = None,
        resource_id: Optional[str] = None,
        changes: Optional[Dict[str, Any]] = None,
        metadata: Optional[Dict[str, Any]] = None,
        error: Optional[str] = None,
    ) -> str:
        """
        Log audit entry.

        Args:
            action: Audit action type
            level: Log level
            user_id: User ID
            principal_id: Principal ID (authenticated entity)
            ip_address: Client IP address
            method: HTTP method
            endpoint: API endpoint
            status_code: HTTP status code
            duration_ms: Request duration in milliseconds
            resource_type: Resource type (e.g., "mission", "agent")
            resource_id: Resource ID
            changes: Data changes (for update/delete)
            metadata: Additional metadata
            error: Error message (if any)

        Returns:
            Audit entry ID
        """
        await self._ensure_initialized()

        # Generate entry ID
        entry_id = f"{int(time.time() * 1000)}_{time.time_ns() % 1000000}"

        # Create audit entry
        entry = AuditEntry(
            id=entry_id,
            timestamp=datetime.utcnow(),
            action=action,
            level=level,
            user_id=user_id,
            principal_id=principal_id,
            ip_address=ip_address,
            method=method,
            endpoint=endpoint,
            status_code=status_code,
            duration_ms=duration_ms,
            resource_type=resource_type,
            resource_id=resource_id,
            changes=changes,
            metadata=metadata or {},
            error=error,
        )

        try:
            # Store entry in Redis
            entry_key = self._make_entry_key(entry_id)
            entry_json = entry.model_dump_json()
            ttl = self.retention_days * 86400  # Convert days to seconds

            await self._redis.setex(entry_key, ttl, entry_json)

            # Create indexes for querying
            await self._create_indexes(entry)

            logger.debug(f"Audit log created: {entry_id} ({action})")

            return entry_id

        except Exception as e:
            logger.error(f"Failed to create audit log: {e}")
            raise

    async def _create_indexes(self, entry: AuditEntry):
        """Create indexes for faster querying."""
        ttl = self.retention_days * 86400

        # Index by user
        if entry.user_id:
            index_key = self._make_index_key("user", entry.user_id)
            await self._redis.zadd(index_key, {entry.id: entry.timestamp.timestamp()})
            await self._redis.expire(index_key, ttl)

        # Index by action
        index_key = self._make_index_key("action", entry.action)
        await self._redis.zadd(index_key, {entry.id: entry.timestamp.timestamp()})
        await self._redis.expire(index_key, ttl)

        # Index by resource
        if entry.resource_type and entry.resource_id:
            index_key = self._make_index_key(
                "resource",
                f"{entry.resource_type}:{entry.resource_id}"
            )
            await self._redis.zadd(index_key, {entry.id: entry.timestamp.timestamp()})
            await self._redis.expire(index_key, ttl)

        # Index by endpoint
        if entry.endpoint:
            index_key = self._make_index_key("endpoint", entry.endpoint)
            await self._redis.zadd(index_key, {entry.id: entry.timestamp.timestamp()})
            await self._redis.expire(index_key, ttl)

    async def query(
        self,
        user_id: Optional[str] = None,
        action: Optional[AuditAction] = None,
        resource_type: Optional[str] = None,
        resource_id: Optional[str] = None,
        endpoint: Optional[str] = None,
        start_time: Optional[datetime] = None,
        end_time: Optional[datetime] = None,
        limit: int = 100,
    ) -> List[AuditEntry]:
        """
        Query audit logs.

        Args:
            user_id: Filter by user ID
            action: Filter by action type
            resource_type: Filter by resource type
            resource_id: Filter by resource ID
            endpoint: Filter by endpoint
            start_time: Filter by start time
            end_time: Filter by end time
            limit: Maximum number of results

        Returns:
            List of audit entries
        """
        await self._ensure_initialized()

        # Determine which index to use
        index_key = None
        if user_id:
            index_key = self._make_index_key("user", user_id)
        elif action:
            index_key = self._make_index_key("action", action)
        elif resource_type and resource_id:
            index_key = self._make_index_key("resource", f"{resource_type}:{resource_id}")
        elif endpoint:
            index_key = self._make_index_key("endpoint", endpoint)
        else:
            # No specific index - return recent entries
            # This is expensive, should be avoided in production
            logger.warning("Audit query without index - performance may be poor")
            return []

        # Calculate score range (timestamp range)
        min_score = start_time.timestamp() if start_time else 0
        max_score = end_time.timestamp() if end_time else time.time()

        try:
            # Get entry IDs from index
            entry_ids = await self._redis.zrevrangebyscore(
                index_key,
                max_score,
                min_score,
                start=0,
                num=limit
            )

            # Fetch entries
            entries = []
            for entry_id in entry_ids:
                entry_key = self._make_entry_key(entry_id.decode())
                entry_json = await self._redis.get(entry_key)

                if entry_json:
                    entry = AuditEntry.model_validate_json(entry_json)
                    entries.append(entry)

            return entries

        except Exception as e:
            logger.error(f"Failed to query audit logs: {e}")
            return []

    # Convenience methods for common audit events

    async def log_api_request(
        self,
        method: str,
        endpoint: str,
        user_id: Optional[str],
        ip_address: Optional[str],
        status_code: int,
        duration_ms: float,
        error: Optional[str] = None,
    ):
        """Log API request."""
        level = AuditLevel.ERROR if status_code >= 400 else AuditLevel.INFO

        return await self.log(
            action=AuditAction.API_REQUEST,
            level=level,
            user_id=user_id,
            ip_address=ip_address,
            method=method,
            endpoint=endpoint,
            status_code=status_code,
            duration_ms=duration_ms,
            error=error,
        )

    async def log_data_change(
        self,
        action: AuditAction,
        resource_type: str,
        resource_id: str,
        user_id: Optional[str],
        changes: Optional[Dict[str, Any]] = None,
    ):
        """Log data change (create, update, delete)."""
        return await self.log(
            action=action,
            user_id=user_id,
            resource_type=resource_type,
            resource_id=resource_id,
            changes=changes,
        )

    async def log_auth_event(
        self,
        action: AuditAction,
        user_id: str,
        ip_address: Optional[str],
        success: bool,
        error: Optional[str] = None,
    ):
        """Log authentication event."""
        level = AuditLevel.WARNING if not success else AuditLevel.INFO

        return await self.log(
            action=action,
            level=level,
            user_id=user_id,
            ip_address=ip_address,
            error=error,
        )

    async def log_security_event(
        self,
        action: AuditAction,
        user_id: Optional[str],
        ip_address: Optional[str],
        metadata: Optional[Dict[str, Any]] = None,
    ):
        """Log security event."""
        return await self.log(
            action=action,
            level=AuditLevel.WARNING,
            user_id=user_id,
            ip_address=ip_address,
            metadata=metadata,
        )


# ============================================================================
# Decorator for Automatic Audit Logging
# ============================================================================

def audit_logged(
    action: str,
    resource_type: Optional[str] = None,
    extract_resource_id: Optional[str] = None,
    extract_user_id: Optional[str] = None,
):
    """
    Decorator for automatic audit logging of function calls.

    Args:
        action: Action name
        resource_type: Resource type
        extract_resource_id: Function argument name to use as resource_id
        extract_user_id: Function argument name to use as user_id

    Usage:
        @audit_logged(action="create_mission", resource_type="mission", extract_user_id="user_id")
        async def create_mission(name: str, user_id: str):
            # Function automatically logged
            pass
    """

    def decorator(func):
        @wraps(func)
        async def wrapper(*args, **kwargs):
            # Extract user_id and resource_id from arguments
            user_id = kwargs.get(extract_user_id) if extract_user_id else None
            resource_id = kwargs.get(extract_resource_id) if extract_resource_id else None

            # Call function
            start_time = time.time()
            try:
                result = await func(*args, **kwargs)

                # Log success
                duration_ms = (time.time() - start_time) * 1000

                await audit_log.log(
                    action=AuditAction(action) if action in [e.value for e in AuditAction] else AuditAction.API_REQUEST,
                    user_id=user_id,
                    resource_type=resource_type,
                    resource_id=resource_id,
                    duration_ms=duration_ms,
                    metadata={"function": func.__name__},
                )

                return result

            except Exception as e:
                # Log failure
                duration_ms = (time.time() - start_time) * 1000

                await audit_log.log(
                    action=AuditAction(action) if action in [e.value for e in AuditAction] else AuditAction.API_REQUEST,
                    level=AuditLevel.ERROR,
                    user_id=user_id,
                    resource_type=resource_type,
                    resource_id=resource_id,
                    duration_ms=duration_ms,
                    error=str(e),
                    metadata={"function": func.__name__},
                )

                raise

        return wrapper

    return decorator


# ============================================================================
# Global Audit Logger
# ============================================================================

_audit_logger: Optional[AuditLogger] = None


def get_audit_logger() -> AuditLogger:
    """Get global audit logger instance."""
    global _audit_logger
    if _audit_logger is None:
        _audit_logger = AuditLogger()
    return _audit_logger


# Convenience global instance
audit_log = get_audit_logger()
