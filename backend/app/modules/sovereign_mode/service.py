"""
Sovereign Mode Service

Core orchestration service for sovereign mode operations.
Integrates all components and provides unified API.
"""

import json
import asyncio
from pathlib import Path
from typing import Optional, Dict, Any, List
from datetime import datetime
from threading import RLock
from loguru import logger

from backend.app.modules.sovereign_mode.schemas import (
    OperationMode,
    Bundle,
    BundleStatus,
    ValidationResult,
    ModeConfig,
    SovereignMode,
    ModeChangeRequest,
    BundleLoadRequest,
    NetworkCheckResult,
    AuditEntry,
    AuditSeverity,
    AuditEventType,
)
from backend.app.modules.sovereign_mode.mode_detector import (
    get_mode_detector,
    get_network_monitor,
    ModeDetector,
    NetworkMonitor,
)
from backend.app.modules.sovereign_mode.bundle_manager import (
    get_bundle_manager,
    BundleManager,
)
from backend.app.modules.sovereign_mode.hash_validator import (
    get_hash_validator,
    HashValidator,
)
from backend.app.modules.sovereign_mode.network_guard import (
    get_network_guard,
    NetworkGuard,
)
from backend.app.modules.sovereign_mode.ipv6_gate import (
    get_ipv6_gate_checker,
    IPv6GateResult,
)


# Import DMZ control (lazy to avoid circular imports)
def _get_dmz_service():
    """Lazy import to avoid circular dependency."""
    from backend.app.modules.dmz_control.service import get_dmz_control_service

    return get_dmz_control_service()


class SovereignModeService:
    """
    Sovereign Mode orchestration service.

    Manages all sovereign mode operations with fail-closed security.
    """

    CONFIG_PATH = "storage/sovereign_mode_config.json"
    AUDIT_LOG_PATH = "storage/sovereign_mode_audit.jsonl"
    SYSTEM_VERSION = "1.0.0"

    def __init__(self):
        """Initialize sovereign mode service."""
        self.lock = RLock()

        # Components
        self.detector: ModeDetector = get_mode_detector()
        self.bundle_manager: BundleManager = get_bundle_manager()
        self.validator: HashValidator = get_hash_validator()
        self.guard: NetworkGuard = get_network_guard()
        self.monitor: Optional[NetworkMonitor] = None

        # Configuration
        self.config: ModeConfig = self._load_config()

        # State
        self.last_mode_change: Optional[datetime] = None
        self.last_network_check: Optional[NetworkCheckResult] = None

        # Audit log
        self.audit_log: List[AuditEntry] = []

        # G2: Owner Override State (in-memory, single-use)
        self.active_override: Optional["OwnerOverride"] = None
        self.override_lock = RLock()

        # Initialize
        self._initialize()

        logger.info(
            f"Sovereign Mode Service initialized (v{self.SYSTEM_VERSION}): "
            f"mode={self.config.current_mode}"
        )

    def _load_config(self) -> ModeConfig:
        """Load configuration from file or create defaults."""
        config_path = Path(self.CONFIG_PATH)

        if config_path.exists():
            try:
                with open(config_path, "r") as f:
                    data = json.load(f)
                return ModeConfig(**data)
            except Exception as e:
                logger.error(f"Error loading config: {e}, using defaults")

        # Return defaults
        return ModeConfig()

    def _save_config(self):
        """Save configuration to file."""
        try:
            config_path = Path(self.CONFIG_PATH)
            config_path.parent.mkdir(parents=True, exist_ok=True)

            with open(config_path, "w") as f:
                json.dump(
                    self.config.model_dump(),
                    f,
                    indent=2,
                    default=str,
                )

            logger.debug("Saved sovereign mode config")

        except Exception as e:
            logger.error(f"Error saving config: {e}")

    def _initialize(self):
        """Initialize service state."""
        # Discover bundles
        bundles = self.bundle_manager.discover_bundles()
        logger.info(f"Discovered {len(bundles)} bundles")

        # Update guard with config
        self.guard.set_mode(self.config.current_mode)
        for domain in self.config.allowed_domains:
            self.guard.add_allowed_domain(domain)

        # Start network monitor if enabled
        if self.config.network_check_enabled:
            self._start_network_monitoring()

    def _start_network_monitoring(self):
        """Start background network monitoring."""
        if self.monitor and self.monitor.is_running:
            logger.debug("Network monitor already running")
            return

        self.monitor = get_network_monitor(
            check_interval=self.config.network_check_interval,
            on_status_change=self._on_network_status_change,
        )

        # Start monitor in background
        asyncio.create_task(self.monitor.start())

        logger.info(
            f"Started network monitoring (interval={self.config.network_check_interval}s)"
        )

    async def _on_network_status_change(self, is_online: bool):
        """
        Callback for network status changes.

        Args:
            is_online: Current network status
        """
        logger.warning(
            f"Network status change detected: {'ONLINE' if is_online else 'OFFLINE'}"
        )

        # Auto-switch if enabled
        if self.config.auto_detect_network and self.config.fallback_to_offline:
            if not is_online and self.config.current_mode == OperationMode.ONLINE:
                # Network lost, switch to offline
                target_mode = OperationMode.OFFLINE

                logger.warning(f"Auto-switching to {target_mode.value} mode")

                await self.change_mode(
                    ModeChangeRequest(
                        target_mode=target_mode,
                        force=False,
                        reason="Network connectivity lost (auto-detect)",
                        bundle_id=self.config.fallback_bundle_id,
                    ),
                    triggered_by="auto_detect",
                )

            elif is_online and self.config.current_mode in [
                OperationMode.OFFLINE,
                OperationMode.SOVEREIGN,
            ]:
                # Network restored, ask if we should switch back
                logger.info(
                    "Network restored but staying in offline mode (manual switch required)"
                )

    # =========================================================================
    # G2: Mode Switch Governance - Preflight Engine (2-Phase Commit)
    # =========================================================================

    async def _check_network_gate(
        self, target_mode: OperationMode
    ) -> "GateCheckResult":
        """
        Check network connectivity gate.

        Required for: ONLINE mode
        """
        from backend.app.modules.sovereign_mode.schemas import (
            GateCheckResult,
            GateCheckStatus,
        )

        required = target_mode == OperationMode.ONLINE
        blocking = required

        try:
            network_check = await self.detector.check_connectivity()
            is_online = network_check.is_online

            if required and not is_online:
                return GateCheckResult(
                    gate_name="network_gate",
                    status=GateCheckStatus.FAIL,
                    required=True,
                    blocking=True,
                    reason="Network unavailable but required for ONLINE mode",
                    error="Network connectivity check failed",
                    metadata={"is_online": False, "check_method": network_check.check_method},
                )
            elif is_online:
                return GateCheckResult(
                    gate_name="network_gate",
                    status=GateCheckStatus.PASS,
                    required=required,
                    blocking=blocking,
                    reason="Network connectivity verified" if required else "Network available (not required)",
                    metadata={
                        "is_online": True,
                        "latency_ms": network_check.latency_ms,
                        "check_method": network_check.check_method,
                    },
                )
            else:
                return GateCheckResult(
                    gate_name="network_gate",
                    status=GateCheckStatus.NOT_APPLICABLE,
                    required=False,
                    blocking=False,
                    reason=f"Network not required for {target_mode.value} mode",
                    metadata={"is_online": False},
                )

        except Exception as e:
            logger.error(f"Network gate check error: {e}")
            return GateCheckResult(
                gate_name="network_gate",
                status=GateCheckStatus.FAIL if required else GateCheckStatus.WARNING,
                required=required,
                blocking=blocking,
                reason="Network check error",
                error=str(e),
                metadata={},
            )

    async def _check_ipv6_gate(
        self, target_mode: OperationMode
    ) -> "GateCheckResult":
        """
        Check IPv6 security gate.

        Required for: SOVEREIGN mode
        """
        from backend.app.modules.sovereign_mode.schemas import (
            GateCheckResult,
            GateCheckStatus,
        )

        required = target_mode == OperationMode.SOVEREIGN
        blocking = required

        if not required:
            return GateCheckResult(
                gate_name="ipv6_gate",
                status=GateCheckStatus.NOT_APPLICABLE,
                required=False,
                blocking=False,
                reason=f"IPv6 check not required for {target_mode.value} mode",
                metadata={},
            )

        try:
            ipv6_checker = get_ipv6_gate_checker()
            ipv6_result = await ipv6_checker.check()

            if ipv6_result.status == "fail":
                return GateCheckResult(
                    gate_name="ipv6_gate",
                    status=GateCheckStatus.FAIL,
                    required=True,
                    blocking=True,
                    reason="IPv6 security check failed - IPv6 active but not properly blocked",
                    error=ipv6_result.error,
                    metadata={
                        "ipv6_active": ipv6_result.ipv6_active,
                        "policy": ipv6_result.policy,
                        "ip6tables_available": ipv6_result.ip6tables_available,
                        "firewall_rules_applied": ipv6_result.firewall_rules_applied,
                    },
                )
            elif ipv6_result.status == "pass":
                return GateCheckResult(
                    gate_name="ipv6_gate",
                    status=GateCheckStatus.PASS,
                    required=True,
                    blocking=True,
                    reason="IPv6 properly blocked - safe to activate SOVEREIGN mode",
                    metadata={
                        "ipv6_active": ipv6_result.ipv6_active,
                        "policy": ipv6_result.policy,
                        "firewall_rules_applied": ipv6_result.firewall_rules_applied,
                    },
                )
            else:  # not_applicable
                return GateCheckResult(
                    gate_name="ipv6_gate",
                    status=GateCheckStatus.WARNING,
                    required=True,
                    blocking=False,
                    reason="IPv6 not active on system (check not applicable)",
                    metadata={
                        "ipv6_active": ipv6_result.ipv6_active,
                        "policy": ipv6_result.policy,
                    },
                )

        except Exception as e:
            logger.error(f"IPv6 gate check error: {e}")
            return GateCheckResult(
                gate_name="ipv6_gate",
                status=GateCheckStatus.FAIL,
                required=True,
                blocking=True,
                reason="IPv6 gate check error",
                error=str(e),
                metadata={},
            )

    async def _check_dmz_gate(
        self, target_mode: OperationMode
    ) -> "GateCheckResult":
        """
        Check DMZ status gate.

        Required for: SOVEREIGN, OFFLINE modes (DMZ must be stopped)
        """
        from backend.app.modules.sovereign_mode.schemas import (
            GateCheckResult,
            GateCheckStatus,
        )

        required_stopped = target_mode in [OperationMode.SOVEREIGN, OperationMode.OFFLINE]
        required_running = target_mode == OperationMode.ONLINE

        try:
            dmz_service = _get_dmz_service()
            dmz_status = await dmz_service.get_status()
            is_running = dmz_status.get("running", False)

            if required_stopped and is_running:
                return GateCheckResult(
                    gate_name="dmz_gate",
                    status=GateCheckStatus.WARNING,
                    required=True,
                    blocking=False,  # Will be stopped automatically
                    reason=f"DMZ running but will be stopped for {target_mode.value} mode",
                    metadata={"dmz_running": True, "will_stop": True},
                )
            elif required_stopped and not is_running:
                return GateCheckResult(
                    gate_name="dmz_gate",
                    status=GateCheckStatus.PASS,
                    required=True,
                    blocking=False,
                    reason=f"DMZ not running (correct for {target_mode.value} mode)",
                    metadata={"dmz_running": False},
                )
            elif required_running:
                import os
                dmz_enabled = os.getenv("BRAIN_DMZ_ENABLED", "false").lower() == "true"

                if dmz_enabled:
                    return GateCheckResult(
                        gate_name="dmz_gate",
                        status=GateCheckStatus.WARNING if not is_running else GateCheckStatus.PASS,
                        required=False,
                        blocking=False,
                        reason="DMZ will be started for ONLINE mode" if not is_running else "DMZ already running",
                        metadata={"dmz_running": is_running, "dmz_enabled": True},
                    )
                else:
                    return GateCheckResult(
                        gate_name="dmz_gate",
                        status=GateCheckStatus.NOT_APPLICABLE,
                        required=False,
                        blocking=False,
                        reason="DMZ not enabled in configuration",
                        metadata={"dmz_running": is_running, "dmz_enabled": False},
                    )
            else:
                return GateCheckResult(
                    gate_name="dmz_gate",
                    status=GateCheckStatus.NOT_APPLICABLE,
                    required=False,
                    blocking=False,
                    reason="DMZ check not applicable for this mode",
                    metadata={"dmz_running": is_running},
                )

        except Exception as e:
            logger.error(f"DMZ gate check error: {e}")
            return GateCheckResult(
                gate_name="dmz_gate",
                status=GateCheckStatus.WARNING,
                required=False,
                blocking=False,
                reason="DMZ status check error (non-critical)",
                error=str(e),
                metadata={},
            )

    async def _check_bundle_trust_gate(
        self, target_mode: OperationMode, bundle_id: Optional[str]
    ) -> "GateCheckResult":
        """
        Check bundle trust gate (G1 integration).

        Required for: SOVEREIGN, OFFLINE modes
        """
        from backend.app.modules.sovereign_mode.schemas import (
            GateCheckResult,
            GateCheckStatus,
        )

        required = target_mode in [OperationMode.SOVEREIGN, OperationMode.OFFLINE]

        if not required:
            return GateCheckResult(
                gate_name="bundle_trust_gate",
                status=GateCheckStatus.NOT_APPLICABLE,
                required=False,
                blocking=False,
                reason=f"Bundle not required for {target_mode.value} mode",
                metadata={},
            )

        # Check if bundle is specified
        effective_bundle_id = bundle_id or self.config.fallback_bundle_id

        if not effective_bundle_id:
            return GateCheckResult(
                gate_name="bundle_trust_gate",
                status=GateCheckStatus.WARNING,
                required=True,
                blocking=False,
                reason="No bundle specified for offline mode",
                metadata={"bundle_id": None},
            )

        try:
            # Check if bundle exists and is trusted
            bundle = self.bundle_manager.get_bundle(effective_bundle_id)

            if not bundle:
                return GateCheckResult(
                    gate_name="bundle_trust_gate",
                    status=GateCheckStatus.FAIL,
                    required=True,
                    blocking=True,
                    reason=f"Bundle not found: {effective_bundle_id}",
                    error="Bundle does not exist",
                    metadata={"bundle_id": effective_bundle_id},
                )

            # Check quarantine status
            if bundle.status == "quarantined":
                return GateCheckResult(
                    gate_name="bundle_trust_gate",
                    status=GateCheckStatus.FAIL,
                    required=True,
                    blocking=True,
                    reason=f"Bundle is quarantined: {bundle.quarantine_reason}",
                    error="Bundle in quarantine",
                    metadata={
                        "bundle_id": effective_bundle_id,
                        "quarantine_reason": bundle.quarantine_reason,
                    },
                )

            # Check signature if enforce policy (G1)
            if not self.config.allow_unsigned_bundles:
                if not bundle.signature:
                    return GateCheckResult(
                        gate_name="bundle_trust_gate",
                        status=GateCheckStatus.FAIL,
                        required=True,
                        blocking=True,
                        reason="Bundle not signed (policy requires signature)",
                        error="Unsigned bundle not allowed",
                        metadata={
                            "bundle_id": effective_bundle_id,
                            "allow_unsigned_bundles": False,
                        },
                    )

            # All checks passed
            return GateCheckResult(
                gate_name="bundle_trust_gate",
                status=GateCheckStatus.PASS,
                required=True,
                blocking=False,
                reason=f"Bundle validated and trusted: {effective_bundle_id}",
                metadata={
                    "bundle_id": effective_bundle_id,
                    "signed": bool(bundle.signature),
                    "status": bundle.status.value,
                },
            )

        except Exception as e:
            logger.error(f"Bundle trust gate check error: {e}")
            return GateCheckResult(
                gate_name="bundle_trust_gate",
                status=GateCheckStatus.FAIL,
                required=True,
                blocking=True,
                reason="Bundle validation error",
                error=str(e),
                metadata={"bundle_id": effective_bundle_id},
            )

    async def preflight_mode_change(
        self,
        target_mode: OperationMode,
        bundle_id: Optional[str] = None,
        request_id: Optional[str] = None,
    ) -> "ModeChangePreflightResult":
        """
        Perform preflight checks for mode change (G2 - Phase 1 of 2-Phase Commit).

        NO SIDE EFFECTS - this method only checks, does not modify state.

        Args:
            target_mode: Desired target mode
            bundle_id: Optional bundle ID for offline modes
            request_id: Optional correlation ID

        Returns:
            ModeChangePreflightResult with all gate check results
        """
        from backend.app.modules.sovereign_mode.schemas import (
            ModeChangePreflightResult,
            ModeChangePreflightStatus,
        )
        import uuid

        request_id = request_id or str(uuid.uuid4())
        current_mode = self.config.current_mode

        logger.info(
            f"[G2] Preflight check: {current_mode.value} -> {target_mode.value} "
            f"(request_id={request_id})"
        )

        # Execute all gate checks in parallel for efficiency
        gate_checks = await asyncio.gather(
            self._check_network_gate(target_mode),
            self._check_ipv6_gate(target_mode),
            self._check_dmz_gate(target_mode),
            self._check_bundle_trust_gate(target_mode, bundle_id),
            return_exceptions=True,
        )

        # Filter out exceptions and log them
        checks = []
        for i, check in enumerate(gate_checks):
            if isinstance(check, Exception):
                logger.error(f"Gate check {i} failed with exception: {check}")
                # Create fallback FAIL check
                from backend.app.modules.sovereign_mode.schemas import (
                    GateCheckResult,
                    GateCheckStatus,
                )
                checks.append(
                    GateCheckResult(
                        gate_name=f"gate_{i}",
                        status=GateCheckStatus.FAIL,
                        required=True,
                        blocking=True,
                        reason="Gate check raised exception",
                        error=str(check),
                        metadata={},
                    )
                )
            else:
                checks.append(check)

        # Aggregate results
        blocking_reasons = []
        warnings = []

        for check in checks:
            if check.blocking and check.status == "fail":
                blocking_reasons.append(f"{check.gate_name}: {check.reason}")
            elif check.status == "warning":
                warnings.append(f"{check.gate_name}: {check.reason}")

        # Determine overall status
        has_blocking_failures = len(blocking_reasons) > 0
        has_warnings = len(warnings) > 0

        if has_blocking_failures:
            overall_status = ModeChangePreflightStatus.FAIL
        elif has_warnings:
            overall_status = ModeChangePreflightStatus.WARNING
        else:
            overall_status = ModeChangePreflightStatus.PASS

        can_proceed = overall_status == ModeChangePreflightStatus.PASS
        override_required = overall_status == ModeChangePreflightStatus.FAIL

        result = ModeChangePreflightResult(
            target_mode=target_mode,
            current_mode=current_mode,
            checks=checks,
            overall_status=overall_status,
            blocking_reasons=blocking_reasons,
            warnings=warnings,
            can_proceed=can_proceed,
            override_required=override_required,
            request_id=request_id,
            checked_by="system",
        )

        logger.info(
            f"[G2] Preflight result: {overall_status.value} "
            f"(can_proceed={can_proceed}, override_required={override_required})"
        )

        return result

    # =========================================================================
    # G2: End of Preflight Engine
    # =========================================================================

    # =========================================================================
    # G2: Owner Override Management
    # =========================================================================

    def _create_override(
        self, reason: str, duration_seconds: int, token: Optional[str] = None
    ) -> "OwnerOverride":
        """
        Create and store an owner override.

        Override is single-use and time-limited.
        """
        from backend.app.modules.sovereign_mode.schemas import OwnerOverride
        from datetime import timedelta

        override = OwnerOverride(
            reason=reason,
            duration_seconds=duration_seconds,
            override_token=token,
            granted_by="owner",
        )

        # Calculate expiration
        override.expires_at = override.granted_at + timedelta(seconds=duration_seconds)

        with self.override_lock:
            self.active_override = override

        logger.info(
            f"[G2] Owner override created: reason='{reason[:50]}...', "
            f"expires_at={override.expires_at}"
        )

        return override

    def _validate_override(self) -> bool:
        """
        Validate active override.

        Returns True if override is valid and not consumed.
        Automatically expires outdated overrides.
        """
        with self.override_lock:
            if self.active_override is None:
                return False

            # Check if consumed
            if self.active_override.consumed:
                logger.warning("[G2] Override already consumed")
                return False

            # Check if expired
            now = datetime.utcnow()
            if self.active_override.expires_at and now > self.active_override.expires_at:
                logger.warning(
                    f"[G2] Override expired at {self.active_override.expires_at}"
                )

                # Emit expired audit event
                self._audit(
                    event_type=AuditEventType.MODE_OVERRIDE_EXPIRED.value,
                    success=False,
                    severity=AuditSeverity.INFO,
                    reason=f"Override expired: {self.active_override.reason}",
                    metadata={
                        "granted_at": str(self.active_override.granted_at),
                        "expires_at": str(self.active_override.expires_at),
                        "duration_seconds": self.active_override.duration_seconds,
                    },
                )

                self.active_override = None
                return False

            return True

    def _consume_override(self) -> Optional["OwnerOverride"]:
        """
        Consume active override (single-use).

        Returns the override if valid, None otherwise.
        """
        with self.override_lock:
            if not self._validate_override():
                return None

            override = self.active_override
            override.consumed = True
            override.consumed_at = datetime.utcnow()

            logger.info(
                f"[G2] Override consumed: reason='{override.reason[:50]}...'"
            )

            # Clear from active state
            self.active_override = None

            return override

    # =========================================================================
    # G2: End of Override Management
    # =========================================================================

    async def change_mode(
        self,
        request: ModeChangeRequest,
        triggered_by: str = "manual",
    ) -> SovereignMode:
        """
        Change operation mode (G2 - 2-Phase Commit with Governance).

        **G2 Governance Flow:**
        1. Run preflight checks (all gates)
        2. Check if override is provided/valid
        3. Only commit if PASS or valid override
        4. Rollback on errors
        5. Comprehensive audit trail

        Args:
            request: Mode change request
            triggered_by: Who/what triggered the change

        Returns:
            Updated SovereignMode status

        Raises:
            ValueError: If preflight fails and no valid override
        """
        with self.lock:
            old_mode = self.config.current_mode
            new_mode = request.target_mode
            import uuid
            request_id = str(uuid.uuid4())

            logger.info(
                f"[G2] Mode change requested: {old_mode.value} -> {new_mode.value} "
                f"(triggered_by={triggered_by}, request_id={request_id})"
            )

            # Skip if already in target mode (unless force/override)
            if old_mode == new_mode and not request.force and not request.override_reason:
                logger.warning(f"Already in {new_mode.value} mode, no change")
                return await self.get_status()

            # ================================================================
            # G2 PHASE 1: PREFLIGHT (Governance Gate Checks)
            # ================================================================

            # Run preflight checks
            preflight_result = await self.preflight_mode_change(
                target_mode=new_mode,
                bundle_id=request.bundle_id,
                request_id=request_id,
            )

            # Emit preflight audit event
            if preflight_result.overall_status == "pass":
                self._audit(
                    event_type=AuditEventType.MODE_PREFLIGHT_OK.value,
                    success=True,
                    severity=AuditSeverity.INFO,
                    reason=f"Preflight passed for {old_mode.value} -> {new_mode.value}",
                    mode_before=old_mode,
                    mode_after=new_mode,
                    metadata={
                        "request_id": request_id,
                        "checks": len(preflight_result.checks),
                        "warnings": len(preflight_result.warnings),
                    },
                )
            elif preflight_result.overall_status == "warning":
                self._audit(
                    event_type=AuditEventType.MODE_PREFLIGHT_WARNING.value,
                    success=True,
                    severity=AuditSeverity.WARNING,
                    reason=f"Preflight passed with warnings: {', '.join(preflight_result.warnings)}",
                    mode_before=old_mode,
                    mode_after=new_mode,
                    metadata={
                        "request_id": request_id,
                        "warnings": preflight_result.warnings,
                    },
                )
            else:  # fail
                self._audit(
                    event_type=AuditEventType.MODE_PREFLIGHT_FAILED.value,
                    success=False,
                    severity=AuditSeverity.ERROR,
                    reason=f"Preflight failed: {', '.join(preflight_result.blocking_reasons)}",
                    mode_before=old_mode,
                    mode_after=new_mode,
                    metadata={
                        "request_id": request_id,
                        "blocking_reasons": preflight_result.blocking_reasons,
                    },
                )

            # ================================================================
            # G2: OVERRIDE VALIDATION & GOVERNANCE DECISION
            # ================================================================

            can_proceed = False
            used_override = None

            if preflight_result.can_proceed:
                # Preflight passed - proceed normally
                can_proceed = True
                logger.info("[G2] Preflight PASS - proceeding with mode change")

            else:
                # Preflight failed - check for override

                # Legacy force flag (deprecated) -> convert to override
                if request.force and not request.override_reason:
                    logger.warning(
                        "[G2] DEPRECATED: force=true used without override_reason. "
                        "This will be removed in future versions."
                    )
                    # Allow legacy force but log warning
                    can_proceed = True

                # New override mechanism (G2)
                elif request.override_reason:
                    # Create override
                    override = self._create_override(
                        reason=request.override_reason,
                        duration_seconds=request.override_duration_seconds,
                        token=request.override_token,
                    )

                    # Validate and consume
                    used_override = self._consume_override()

                    if used_override:
                        can_proceed = True
                        logger.warning(
                            f"[G2] Override USED - bypassing preflight failures. "
                            f"Reason: {used_override.reason[:100]}"
                        )

                        # Emit override audit event
                        self._audit(
                            event_type=AuditEventType.MODE_OVERRIDE_USED.value,
                            success=True,
                            severity=AuditSeverity.WARNING,
                            reason=f"Override used: {used_override.reason}",
                            mode_before=old_mode,
                            mode_after=new_mode,
                            metadata={
                                "request_id": request_id,
                                "override_duration_seconds": used_override.duration_seconds,
                                "override_granted_at": str(used_override.granted_at),
                                "override_granted_by": used_override.granted_by,
                                "blocking_reasons_overridden": preflight_result.blocking_reasons,
                            },
                        )
                    else:
                        logger.error("[G2] Override creation/validation failed")

            # Final decision: BLOCK if no valid override and preflight failed
            if not can_proceed:
                error_msg = (
                    f"❌ Mode change BLOCKED by governance (G2):\n\n"
                    f"Preflight status: {preflight_result.overall_status.upper()}\n\n"
                    f"Blocking reasons:\n"
                )
                for reason in preflight_result.blocking_reasons:
                    error_msg += f"  - {reason}\n"

                error_msg += (
                    f"\n\nTo override, provide:\n"
                    f"  - override_reason: <detailed reason (min 10 chars)>\n"
                    f"  - override_duration_seconds: <validity time (default 3600s)>\n"
                )

                logger.error(f"[G2] Mode change BLOCKED: {error_msg}")
                raise ValueError(error_msg)

            # ================================================================
            # G2 PHASE 2: COMMIT (Mode Change Execution)
            # ================================================================

            try:
                logger.info(f"[G2] COMMIT: Executing mode change {old_mode.value} -> {new_mode.value}")

                # Load bundle if switching to offline modes
                if new_mode in [OperationMode.OFFLINE, OperationMode.SOVEREIGN]:
                    bundle_id = request.bundle_id or self.config.fallback_bundle_id

                    if bundle_id:
                        success = self.bundle_manager.load_bundle(bundle_id)
                        if not success:
                            raise ValueError(f"Failed to load bundle: {bundle_id}")

                        self.config.active_bundle_id = bundle_id
                        logger.info(f"Loaded bundle: {bundle_id}")
                    else:
                        logger.warning("No bundle specified for offline mode")

                # Stop DMZ if switching to SOVEREIGN or OFFLINE
                if new_mode in [OperationMode.SOVEREIGN, OperationMode.OFFLINE]:
                    try:
                        dmz_service = _get_dmz_service()
                        dmz_stopped = await dmz_service.stop_dmz()

                        if dmz_stopped:
                            self._audit(
                                event_type=AuditEventType.DMZ_STOPPED.value,
                                success=True,
                                severity=AuditSeverity.INFO,
                                reason=f"DMZ stopped for {new_mode.value} mode",
                                mode_after=new_mode,
                            )
                            logger.info(f"DMZ gateway stopped for {new_mode.value} mode")
                        else:
                            logger.warning("Failed to stop DMZ gateway (might not be running)")

                    except Exception as e:
                        logger.error(f"Error stopping DMZ: {e}")
                        # Don't block mode change on DMZ errors

                # Start DMZ if switching to ONLINE (and DMZ enabled in ENV)
                elif new_mode == OperationMode.ONLINE:
                    import os
                    dmz_enabled = os.getenv("BRAIN_DMZ_ENABLED", "false").lower() == "true"

                    if dmz_enabled:
                        try:
                            dmz_service = _get_dmz_service()
                            dmz_started = await dmz_service.start_dmz()

                            if dmz_started:
                                self._audit(
                                    event_type=AuditEventType.DMZ_STARTED.value,
                                    success=True,
                                    severity=AuditSeverity.INFO,
                                    reason="DMZ started for ONLINE mode",
                                    mode_after=new_mode,
                                )
                                logger.info("DMZ gateway started for ONLINE mode")
                            else:
                                logger.warning("Failed to start DMZ gateway")

                        except Exception as e:
                            logger.error(f"Error starting DMZ: {e}")
                            # Don't block mode change on DMZ errors

                # COMMIT: Update mode
                self.config.current_mode = new_mode
                self.last_mode_change = datetime.utcnow()

                # Update network guard
                self.guard.set_mode(new_mode)

                # Save config
                self._save_config()

                # Emit mode change audit event
                self._audit(
                    event_type=AuditEventType.MODE_CHANGED.value,
                    success=True,
                    severity=AuditSeverity.INFO,
                    reason=f"Mode changed: {old_mode.value} -> {new_mode.value}",
                    mode_before=old_mode,
                    mode_after=new_mode,
                    triggered_by=triggered_by,
                    metadata={
                        "request_id": request_id,
                        "override_used": used_override is not None,
                        "preflight_status": preflight_result.overall_status.value,
                    },
                )

                logger.info(
                    f"[G2] Mode change COMMITTED: {old_mode.value} -> {new_mode.value} "
                    f"(override={used_override is not None})"
                )

                return await self.get_status()

            except Exception as e:
                # ROLLBACK on commit error
                logger.error(f"[G2] Mode change COMMIT FAILED - attempting rollback: {e}")

                # Emit commit failed audit
                self._audit(
                    event_type=AuditEventType.MODE_COMMIT_FAILED.value,
                    success=False,
                    severity=AuditSeverity.CRITICAL,
                    reason=f"Mode commit failed: {str(e)}",
                    mode_before=old_mode,
                    mode_after=new_mode,
                    error=str(e),
                    metadata={"request_id": request_id},
                )

                # Rollback (restore old mode)
                self.config.current_mode = old_mode
                self.guard.set_mode(old_mode)
                self._save_config()

                # Emit rollback audit
                self._audit(
                    event_type=AuditEventType.MODE_ROLLBACK.value,
                    success=True,
                    severity=AuditSeverity.WARNING,
                    reason=f"Rolled back to {old_mode.value} after commit failure",
                    mode_before=new_mode,
                    mode_after=old_mode,
                    metadata={"request_id": request_id, "error": str(e)},
                )

                logger.warning(f"[G2] Rolled back to {old_mode.value}")

                raise ValueError(f"Mode change failed: {str(e)}")
    async def get_status(self) -> SovereignMode:
        """
        Get current sovereign mode status.

        Returns:
            SovereignMode status
        """
        # Get bundle stats
        stats = self.bundle_manager.get_statistics()

        # Get active bundle
        active_bundle = self.bundle_manager.get_active_bundle()

        # Get guard stats
        guard_stats = self.guard.get_statistics()

        # Check if we're online
        is_online = False
        if self.last_network_check:
            is_online = self.last_network_check.is_online
        else:
            # Perform check
            result = await self.detector.check_connectivity()
            is_online = result.is_online
            self.last_network_check = result

        return SovereignMode(
            mode=self.config.current_mode,
            is_online=is_online,
            is_sovereign=(self.config.current_mode == OperationMode.SOVEREIGN),
            active_bundle=active_bundle,
            available_bundles=stats["total_bundles"],
            validated_bundles=stats["validated"],
            quarantined_bundles=stats["quarantined"],
            network_blocks_count=guard_stats["blocked_count"],
            last_network_check=self.last_network_check.checked_at
            if self.last_network_check
            else None,
            config=self.config,
            system_version=self.SYSTEM_VERSION,
            last_mode_change=self.last_mode_change,
        )

    def get_bundles(self, status: Optional[BundleStatus] = None) -> List[Bundle]:
        """
        List available bundles.

        Args:
            status: Optional status filter

        Returns:
            List of bundles
        """
        return self.bundle_manager.list_bundles(status=status)

    def get_bundle(self, bundle_id: str) -> Optional[Bundle]:
        """
        Get bundle by ID.

        Args:
            bundle_id: Bundle identifier

        Returns:
            Bundle or None
        """
        return self.bundle_manager.get_bundle(bundle_id)

    def update_config(self, **kwargs) -> ModeConfig:
        """
        Update configuration.

        Args:
            **kwargs: Configuration fields to update

        Returns:
            Updated configuration
        """
        with self.lock:
            # Update fields
            for key, value in kwargs.items():
                if hasattr(self.config, key):
                    setattr(self.config, key, value)
                    logger.debug(f"Updated config: {key}={value}")

            # Update guard if relevant
            if "current_mode" in kwargs:
                self.guard.set_mode(self.config.current_mode)

            if "allowed_domains" in kwargs:
                for domain in self.config.allowed_domains:
                    self.guard.add_allowed_domain(domain)

            # Restart monitor if interval changed
            if "network_check_interval" in kwargs and self.monitor:
                asyncio.create_task(self.monitor.stop())
                self._start_network_monitoring()

            # Save config
            self._save_config()

            return self.config

    def _audit(
        self,
        event_type: str,
        success: bool = True,
        severity: Optional[AuditSeverity] = None,
        reason: Optional[str] = None,
        error: Optional[str] = None,
        triggered_by: str = "system",
        mode_before: Optional[OperationMode] = None,
        mode_after: Optional[OperationMode] = None,
        bundle_id: Optional[str] = None,
        ipv6_related: bool = False,
        **metadata,
    ):
        """
        Create and log audit entry with automatic severity mapping.

        Args:
            event_type: Event type (use AuditEventType enum values)
            success: Operation succeeded
            severity: Event severity (auto-detected if not provided)
            reason: Reason for event
            error: Error message if failed
            triggered_by: Who/what triggered event
            mode_before: Mode before change
            mode_after: Mode after change
            bundle_id: Associated bundle ID
            ipv6_related: Event is IPv6-related
            **metadata: Additional metadata
        """
        # Auto-detect severity if not provided
        if severity is None:
            if not success:
                severity = AuditSeverity.ERROR
            elif "failed" in event_type or "blocked" in event_type:
                severity = AuditSeverity.WARNING
            elif "critical" in event_type:
                severity = AuditSeverity.CRITICAL
            else:
                severity = AuditSeverity.INFO

        # Create audit entry
        entry = AuditEntry(
            id=f"{event_type.split('.')[-1]}_{int(datetime.utcnow().timestamp() * 1000)}",
            timestamp=datetime.utcnow(),
            event_type=event_type,
            severity=severity,
            mode_before=mode_before,
            mode_after=mode_after,
            bundle_id=bundle_id,
            reason=reason,
            triggered_by=triggered_by,
            success=success,
            error=error,
            ipv6_related=ipv6_related,
            metadata=metadata,
        )

        self._log_audit(entry)

    def _log_audit(self, entry: AuditEntry):
        """
        Write audit entry to storage.

        Args:
            entry: Audit entry to log
        """
        self.audit_log.append(entry)

        # Write to file
        try:
            audit_path = Path(self.AUDIT_LOG_PATH)
            audit_path.parent.mkdir(parents=True, exist_ok=True)

            with open(audit_path, "a") as f:
                f.write(entry.model_dump_json() + "\n")

            logger.debug(f"Audit event logged: {entry.event_type} (severity={entry.severity})")

        except Exception as e:
            logger.error(f"Error writing audit log: {e}")

    def get_audit_log(
        self,
        limit: int = 100,
        event_type: Optional[str] = None,
    ) -> List[AuditEntry]:
        """
        Get audit log entries.

        Args:
            limit: Maximum entries to return
            event_type: Optional event type filter

        Returns:
            List of audit entries
        """
        entries = self.audit_log

        if event_type:
            entries = [e for e in entries if e.event_type == event_type]

        return entries[-limit:]

    def get_statistics(self) -> Dict[str, Any]:
        """
        Get comprehensive statistics.

        Returns:
            Statistics dictionary
        """
        return {
            "system_version": self.SYSTEM_VERSION,
            "current_mode": self.config.current_mode.value,
            "bundles": self.bundle_manager.get_statistics(),
            "network_guard": self.guard.get_statistics(),
            "network_detector": self.detector.get_statistics(),
            "audit_entries": len(self.audit_log),
        }


# Singleton instance
_service: Optional[SovereignModeService] = None


def get_sovereign_service() -> SovereignModeService:
    """Get singleton sovereign mode service instance."""
    global _service
    if _service is None:
        _service = SovereignModeService()
    return _service
