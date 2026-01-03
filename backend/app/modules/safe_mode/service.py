"""
Safe Mode Service (Sprint 7.4)

Global kill-switch for BRAiN operations.
Allows instant transition to read-only safe mode.
"""

import os
from typing import Optional
from threading import RLock
from datetime import datetime
from loguru import logger

from app.modules.sovereign_mode.schemas import (
    AuditEventType,
    AuditSeverity,
)


class SafeModeService:
    """
    Global safe mode control for BRAiN.

    When safe mode is enabled:
    - ❌ No new executions
    - ❌ No deployments
    - ✅ Read-only APIs allowed
    - ✅ Monitoring & audit stay active
    - ✅ Metrics continue collecting

    Activation:
    - Environment variable: BRAIN_SAFE_MODE=true
    - API call: POST /api/safe-mode/enable

    Design Principles:
    - No restart required
    - Idempotent
    - Fail-closed default
    - Full audit trail
    """

    ENV_SAFE_MODE_KEY = "BRAIN_SAFE_MODE"

    def __init__(self):
        """Initialize safe mode service."""
        self.lock = RLock()

        # Check environment variable
        env_safe_mode = os.getenv(self.ENV_SAFE_MODE_KEY, "false").lower()
        self._safe_mode_enabled = env_safe_mode in ["true", "1", "yes"]

        # Metadata
        self._enabled_at: Optional[datetime] = None
        self._enabled_reason: str = "Environment variable" if self._safe_mode_enabled else ""
        self._enabled_by: str = "env" if self._safe_mode_enabled else ""

        if self._safe_mode_enabled:
            logger.warning("Safe mode ENABLED via environment variable")
            self._enabled_at = datetime.utcnow()
        else:
            logger.info("Safe mode initialized (currently DISABLED)")

    def is_safe_mode_enabled(self) -> bool:
        """
        Check if safe mode is currently enabled.

        Returns:
            True if safe mode is active, False otherwise
        """
        with self.lock:
            return self._safe_mode_enabled

    def enable_safe_mode(
        self,
        reason: str = "Manual activation",
        enabled_by: str = "api"
    ) -> bool:
        """
        Enable safe mode.

        Args:
            reason: Reason for enabling safe mode
            enabled_by: Who/what enabled safe mode

        Returns:
            True if safe mode was enabled, False if already enabled
        """
        with self.lock:
            if self._safe_mode_enabled:
                logger.warning("Safe mode already enabled")
                return False

            self._safe_mode_enabled = True
            self._enabled_at = datetime.utcnow()
            self._enabled_reason = reason
            self._enabled_by = enabled_by

            logger.critical(
                f"🛑 SAFE MODE ENABLED: {reason} (by {enabled_by})"
            )

            # Emit audit event
            self._emit_audit_event(
                event_type=AuditEventType.SYSTEM_SAFE_MODE_ENABLED.value,
                success=True,
                severity=AuditSeverity.CRITICAL,
                reason=reason,
                triggered_by=enabled_by,
            )

            return True

    def disable_safe_mode(
        self,
        reason: str = "Manual deactivation",
        disabled_by: str = "api"
    ) -> bool:
        """
        Disable safe mode.

        Args:
            reason: Reason for disabling safe mode
            disabled_by: Who/what disabled safe mode

        Returns:
            True if safe mode was disabled, False if already disabled
        """
        with self.lock:
            if not self._safe_mode_enabled:
                logger.warning("Safe mode already disabled")
                return False

            self._safe_mode_enabled = False

            logger.warning(
                f"✅ SAFE MODE DISABLED: {reason} (by {disabled_by})"
            )

            # Emit audit event
            self._emit_audit_event(
                event_type=AuditEventType.SYSTEM_SAFE_MODE_DISABLED.value,
                success=True,
                severity=AuditSeverity.WARNING,
                reason=reason,
                triggered_by=disabled_by,
            )

            # Clear metadata
            self._enabled_at = None
            self._enabled_reason = ""
            self._enabled_by = ""

            return True

    def check_and_block(self, operation: str) -> None:
        """
        Check if operation is allowed in safe mode.

        Args:
            operation: Operation name (for logging)

        Raises:
            RuntimeError: If safe mode is enabled
        """
        if self.is_safe_mode_enabled():
            logger.error(
                f"Operation blocked by safe mode: {operation}"
            )

            # Emit audit event
            self._emit_audit_event(
                event_type=AuditEventType.SYSTEM_SAFE_MODE_EXECUTION_BLOCKED.value,
                success=False,
                severity=AuditSeverity.WARNING,
                reason=f"Operation blocked: {operation}",
                triggered_by="safe_mode",
            )

            raise RuntimeError(
                f"🛑 Operation blocked: BRAiN is in SAFE MODE.\n"
                f"Blocked operation: {operation}\n"
                f"Safe mode enabled at: {self._enabled_at}\n"
                f"Reason: {self._enabled_reason}\n"
                f"Enabled by: {self._enabled_by}\n\n"
                f"To disable safe mode:\n"
                f"1. Via API: POST /api/safe-mode/disable\n"
                f"2. Via ENV: Set BRAIN_SAFE_MODE=false and restart"
            )

    def get_status(self) -> dict:
        """
        Get safe mode status.

        Returns:
            Status dictionary
        """
        with self.lock:
            return {
                "safe_mode_enabled": self._safe_mode_enabled,
                "enabled_at": self._enabled_at.isoformat() if self._enabled_at else None,
                "enabled_reason": self._enabled_reason,
                "enabled_by": self._enabled_by,
                "blocked_operations": [
                    "Factory executions",
                    "Deployments",
                    "Bundle loads",
                ] if self._safe_mode_enabled else [],
                "allowed_operations": [
                    "Read-only APIs",
                    "Monitoring",
                    "Audit log access",
                    "Metrics",
                ]
            }

    def _emit_audit_event(
        self,
        event_type: str,
        success: bool,
        severity: AuditSeverity,
        reason: str,
        triggered_by: str
    ):
        """
        Emit safe mode audit event.

        Args:
            event_type: Event type
            success: Operation success
            severity: Event severity
            reason: Event reason
            triggered_by: Who/what triggered event
        """
        try:
            # Import here to avoid circular dependency
            from app.modules.sovereign_mode.service import get_sovereign_service

            service = get_sovereign_service()
            service._audit(
                event_type=event_type,
                success=success,
                severity=severity,
                reason=reason,
                triggered_by=triggered_by,
            )
        except Exception as e:
            logger.error(f"Failed to emit safe mode audit event: {e}")


# Singleton instance
_safe_mode_service: Optional[SafeModeService] = None
_safe_mode_lock = RLock()


def get_safe_mode_service() -> SafeModeService:
    """
    Get singleton safe mode service instance.

    Returns:
        SafeModeService instance
    """
    global _safe_mode_service

    with _safe_mode_lock:
        if _safe_mode_service is None:
            _safe_mode_service = SafeModeService()
        return _safe_mode_service
