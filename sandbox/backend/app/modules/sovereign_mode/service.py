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

from app.modules.sovereign_mode.schemas import (
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
from app.modules.sovereign_mode.mode_detector import (
    get_mode_detector,
    get_network_monitor,
    ModeDetector,
    NetworkMonitor,
)
from app.modules.sovereign_mode.bundle_manager import (
    get_bundle_manager,
    BundleManager,
)
from app.modules.sovereign_mode.hash_validator import (
    get_hash_validator,
    HashValidator,
)
from app.modules.sovereign_mode.network_guard import (
    get_network_guard,
    NetworkGuard,
)
from app.modules.sovereign_mode.ipv6_gate import (
    get_ipv6_gate_checker,
    IPv6GateResult,
)

# Sprint 7: Metrics integration
try:
    from app.modules.monitoring.metrics import get_metrics_collector
    METRICS_AVAILABLE = True
except ImportError:
    METRICS_AVAILABLE = False
    logger.warning("Metrics module not available")


# Import DMZ control (lazy to avoid circular imports)
def _get_dmz_service():
    """Lazy import to avoid circular dependency."""
    from app.modules.dmz_control.service import get_dmz_control_service

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

    async def change_mode(
        self,
        request: ModeChangeRequest,
        triggered_by: str = "manual",
    ) -> SovereignMode:
        """
        Change operation mode.

        Args:
            request: Mode change request
            triggered_by: Who/what triggered the change

        Returns:
            Updated SovereignMode status

        Raises:
            ValueError: If mode change is invalid
        """
        with self.lock:
            old_mode = self.config.current_mode
            new_mode = request.target_mode

            logger.info(
                f"Mode change requested: {old_mode} -> {new_mode} "
                f"(triggered_by={triggered_by}, force={request.force})"
            )

            # Validate mode change
            if old_mode == new_mode and not request.force:
                logger.warning(f"Already in {new_mode} mode, no change")
                return await self.get_status()

            # Check if network is required for ONLINE mode
            if new_mode == OperationMode.ONLINE and not request.force:
                network_check = await self.detector.check_connectivity()
                if not network_check.is_online:
                    raise ValueError(
                        "Cannot switch to ONLINE mode: network unavailable"
                    )

            # IPv6 gate check for SOVEREIGN mode
            if new_mode == OperationMode.SOVEREIGN and not request.force:
                ipv6_checker = get_ipv6_gate_checker()
                ipv6_result = await ipv6_checker.check()

                # Audit IPv6 gate check
                self._audit(
                    event_type=AuditEventType.IPV6_GATE_CHECKED.value,
                    success=(ipv6_result.status in ["pass", "not_applicable"]),
                    severity=(
                        AuditSeverity.INFO
                        if ipv6_result.status == "pass"
                        else (
                            AuditSeverity.WARNING
                            if ipv6_result.status == "not_applicable"
                            else AuditSeverity.ERROR
                        )
                    ),
                    reason=f"IPv6 gate check: {ipv6_result.status}",
                    ipv6_related=True,
                    metadata={
                        "ipv6_active": ipv6_result.ipv6_active,
                        "policy": ipv6_result.policy,
                        "ip6tables_available": ipv6_result.ip6tables_available,
                        "rules_applied": ipv6_result.firewall_rules_applied,
                    },
                )

                if ipv6_result.status == "fail":
                    # Emit critical audit event
                    self._audit(
                        event_type=AuditEventType.IPV6_GATE_FAILED.value,
                        success=False,
                        severity=AuditSeverity.CRITICAL,
                        reason="IPv6 gate check failed - cannot activate sovereign mode",
                        error=ipv6_result.error,
                        ipv6_related=True,
                        metadata={
                            "ipv6_active": ipv6_result.ipv6_active,
                            "policy": ipv6_result.policy,
                            "ip6tables_available": ipv6_result.ip6tables_available,
                        },
                    )

                    # Build user-friendly error message
                    error_msg = (
                        "❌ Cannot activate Sovereign Mode: IPv6 gate check failed.\n\n"
                        f"Reason: {ipv6_result.error}\n\n"
                        "Solutions:\n"
                        "1. Install ip6tables:\n"
                        "   sudo apt-get update && sudo apt-get install iptables\n\n"
                        "2. Disable IPv6 on host:\n"
                        "   sudo sysctl -w net.ipv6.conf.all.disable_ipv6=1\n"
                        "   sudo sysctl -w net.ipv6.conf.default.disable_ipv6=1\n\n"
                        "   Make persistent: Add to /etc/sysctl.conf:\n"
                        "   net.ipv6.conf.all.disable_ipv6 = 1\n"
                        "   net.ipv6.conf.default.disable_ipv6 = 1\n\n"
                        "3. Apply IPv6 firewall rules:\n"
                        "   sudo scripts/sovereign-fw.sh apply sovereign\n\n"
                        f"Current Status:\n"
                        f"- IPv6 Active: {'Yes' if ipv6_result.ipv6_active else 'No'}\n"
                        f"- ip6tables Available: {'Yes' if ipv6_result.ip6tables_available else 'No'}\n"
                        f"- Policy: {ipv6_result.policy}\n"
                        f"- Rules Applied: {'Yes' if ipv6_result.firewall_rules_applied else 'No'}"
                    )

                    raise ValueError(error_msg)

                elif ipv6_result.status == "pass":
                    # Emit success audit event
                    self._audit(
                        event_type=AuditEventType.IPV6_GATE_PASSED.value,
                        success=True,
                        severity=AuditSeverity.INFO,
                        reason="IPv6 gate check passed - IPv6 is properly blocked",
                        ipv6_related=True,
                        metadata={
                            "ipv6_active": ipv6_result.ipv6_active,
                            "policy": ipv6_result.policy,
                            "rules_applied": ipv6_result.firewall_rules_applied,
                        },
                    )

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
                        # Log warning but don't block mode change
                        # (DMZ might not be running or compose file might not exist)
                        logger.warning("Failed to stop DMZ gateway (might not be running)")
                        self._audit(
                            event_type=AuditEventType.DMZ_STOPPED.value,
                            success=False,
                            severity=AuditSeverity.WARNING,
                            reason=f"Failed to stop DMZ for {new_mode.value} mode",
                            error="DMZ stop command failed",
                        )

                except Exception as e:
                    # Log error but don't block mode change
                    logger.error(f"Error stopping DMZ: {e}")
                    self._audit(
                        event_type=AuditEventType.DMZ_STOPPED.value,
                        success=False,
                        severity=AuditSeverity.ERROR,
                        reason="Error stopping DMZ",
                        error=str(e),
                    )

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
                            self._audit(
                                event_type=AuditEventType.DMZ_STARTED.value,
                                success=False,
                                severity=AuditSeverity.WARNING,
                                reason="Failed to start DMZ for ONLINE mode",
                                error="DMZ start command failed",
                            )

                    except Exception as e:
                        logger.error(f"Error starting DMZ: {e}")
                        self._audit(
                            event_type=AuditEventType.DMZ_STARTED.value,
                            success=False,
                            severity=AuditSeverity.ERROR,
                            reason="Error starting DMZ",
                            error=str(e),
                        )
                else:
                    logger.debug("DMZ not enabled (BRAIN_DMZ_ENABLED=false)")

            # Update mode
            self.config.current_mode = new_mode
            self.guard.set_mode(new_mode)
            self.last_mode_change = datetime.utcnow()

            # Sprint 7: Record mode switch in metrics (fail-safe)
            if METRICS_AVAILABLE:
                try:
                    metrics = get_metrics_collector()
                    metrics.record_mode_switch(new_mode)
                except Exception as e:
                    logger.warning(f"Failed to record mode switch metric: {e}")

            # Save config
            self._save_config()

            # Audit log
            if self.config.audit_mode_changes:
                self._audit(
                    event_type=AuditEventType.MODE_CHANGED.value,
                    success=True,
                    severity=AuditSeverity.INFO,
                    mode_before=old_mode,
                    mode_after=new_mode,
                    bundle_id=self.config.active_bundle_id,
                    reason=request.reason,
                    triggered_by=triggered_by,
                )

            logger.info(
                f"Mode changed: {old_mode} -> {new_mode} "
                f"(triggered_by={triggered_by})"
            )

            return await self.get_status()

    async def load_bundle(self, request: BundleLoadRequest) -> Bundle:
        """
        Load an offline bundle.

        Args:
            request: Bundle load request

        Returns:
            Loaded Bundle

        Raises:
            ValueError: If bundle load fails
        """
        with self.lock:
            bundle_id = request.bundle_id

            logger.info(f"Loading bundle: {bundle_id}")

            # Validate bundle
            if request.force_revalidate:
                result = self.bundle_manager.validate_bundle(bundle_id, force=True)
            else:
                result = self.bundle_manager.validate_bundle(bundle_id, force=False)

            if not result.is_valid:
                if self.config.quarantine_on_failure:
                    self.bundle_manager.quarantine_bundle(
                        bundle_id,
                        f"Validation failed: {result.errors}",
                    )

                raise ValueError(f"Bundle validation failed: {result.errors}")

            # Load bundle
            success = self.bundle_manager.load_bundle(
                bundle_id,
                skip_validation=request.skip_quarantine_check,
            )

            if not success:
                raise ValueError(f"Failed to load bundle: {bundle_id}")

            # Update config
            self.config.active_bundle_id = bundle_id
            self._save_config()

            # Audit log
            if self.config.audit_bundle_loads:
                self._audit(
                    event_type=AuditEventType.BUNDLE_LOADED.value,
                    success=True,
                    bundle_id=bundle_id,
                    triggered_by="manual",
                )

            bundle = self.bundle_manager.get_bundle(bundle_id)
            logger.info(f"Bundle loaded: {bundle_id}")

            return bundle

    async def validate_bundle(
        self, bundle_id: str, force: bool = False
    ) -> ValidationResult:
        """
        Validate bundle integrity.

        Args:
            bundle_id: Bundle to validate
            force: Force revalidation

        Returns:
            ValidationResult
        """
        logger.info(f"Validating bundle: {bundle_id} (force={force})")

        result = self.bundle_manager.validate_bundle(bundle_id, force=force)

        # Quarantine if failed and auto-quarantine enabled
        if not result.is_valid and self.config.quarantine_on_failure:
            self.bundle_manager.quarantine_bundle(
                bundle_id,
                f"Validation failed: {result.errors}",
            )
            logger.warning(f"Bundle {bundle_id} quarantined due to validation failure")

        return result

    async def check_network(self) -> NetworkCheckResult:
        """
        Check network connectivity.

        Returns:
            NetworkCheckResult
        """
        result = await self.detector.check_connectivity()
        self.last_network_check = result

        # Audit network probe
        if result.is_online:
            self._audit(
                event_type=AuditEventType.NETWORK_PROBE_PASSED.value,
                success=True,
                reason=f"Network probe successful via {result.check_method}",
                latency_ms=result.latency_ms,
                check_method=result.check_method,
            )
        else:
            self._audit(
                event_type=AuditEventType.NETWORK_PROBE_FAILED.value,
                success=False,
                severity=AuditSeverity.WARNING,
                reason=f"Network probe failed: {result.error or 'No connectivity'}",
                error=result.error,
                check_method=result.check_method,
            )

        logger.info(
            f"Network check: {'ONLINE' if result.is_online else 'OFFLINE'} "
            f"(latency={result.latency_ms}ms, method={result.check_method})"
        )

        return result

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
