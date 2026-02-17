"""
Mode Detector

Network connectivity detection for automatic mode switching.
Provides multiple detection methods with fallbacks.
"""

import asyncio
import socket
from typing import Optional, List
from datetime import datetime
from loguru import logger
import httpx

from app.modules.sovereign_mode.schemas import NetworkCheckResult


class ModeDetector:
    """Network connectivity detector for auto mode switching."""

    # Default check targets
    DEFAULT_DNS_HOSTS = ["8.8.8.8", "1.1.1.1"]  # Google DNS, Cloudflare DNS
    DEFAULT_HTTP_URLS = [
        "https://www.google.com",
        "https://www.cloudflare.com",
    ]
    DEFAULT_TIMEOUT = 5.0  # seconds

    def __init__(
        self,
        dns_hosts: Optional[List[str]] = None,
        http_urls: Optional[List[str]] = None,
        timeout: float = DEFAULT_TIMEOUT,
    ):
        """
        Initialize mode detector.

        Args:
            dns_hosts: DNS servers to check (default: Google, Cloudflare)
            http_urls: HTTP endpoints to check (default: Google, Cloudflare)
            timeout: Timeout for checks in seconds
        """
        self.dns_hosts = dns_hosts or self.DEFAULT_DNS_HOSTS
        self.http_urls = http_urls or self.DEFAULT_HTTP_URLS
        self.timeout = timeout

        self.last_check: Optional[NetworkCheckResult] = None
        self.check_count = 0
        self.online_count = 0
        self.offline_count = 0

    async def check_dns_connectivity(self) -> NetworkCheckResult:
        """
        Check network connectivity via DNS resolution.

        Tries to connect to DNS servers (non-blocking).

        Returns:
            NetworkCheckResult with DNS check status
        """
        start_time = datetime.utcnow()

        for host in self.dns_hosts:
            try:
                # Try to connect to DNS server on port 53
                loop = asyncio.get_event_loop()
                await asyncio.wait_for(
                    loop.run_in_executor(
                        None,
                        lambda: socket.create_connection(
                            (host, 53), timeout=self.timeout
                        ),
                    ),
                    timeout=self.timeout,
                )

                # Connection successful
                latency = (datetime.utcnow() - start_time).total_seconds() * 1000

                result = NetworkCheckResult(
                    is_online=True,
                    latency_ms=latency,
                    check_method="dns",
                    checked_at=datetime.utcnow(),
                    error=None,
                )

                logger.debug(f"DNS check passed: {host} ({latency:.2f}ms)")
                self.last_check = result
                return result

            except (socket.timeout, socket.error, asyncio.TimeoutError) as e:
                logger.debug(f"DNS check failed for {host}: {e}")
                continue

        # All DNS checks failed
        result = NetworkCheckResult(
            is_online=False,
            latency_ms=None,
            check_method="dns",
            checked_at=datetime.utcnow(),
            error="All DNS servers unreachable",
        )

        logger.warning("DNS connectivity check: OFFLINE")
        self.last_check = result
        return result

    async def check_http_connectivity(self) -> NetworkCheckResult:
        """
        Check network connectivity via HTTP request.

        Tries to reach known HTTP endpoints.

        Returns:
            NetworkCheckResult with HTTP check status
        """
        start_time = datetime.utcnow()

        async with httpx.AsyncClient(timeout=self.timeout) as client:
            for url in self.http_urls:
                try:
                    response = await client.get(url, follow_redirects=True)

                    if response.status_code < 500:  # Accept 2xx, 3xx, 4xx
                        latency = (
                            datetime.utcnow() - start_time
                        ).total_seconds() * 1000

                        result = NetworkCheckResult(
                            is_online=True,
                            latency_ms=latency,
                            check_method="http",
                            checked_at=datetime.utcnow(),
                            error=None,
                        )

                        logger.debug(f"HTTP check passed: {url} ({latency:.2f}ms)")
                        self.last_check = result
                        return result

                except (httpx.RequestError, httpx.TimeoutException) as e:
                    logger.debug(f"HTTP check failed for {url}: {e}")
                    continue

        # All HTTP checks failed
        result = NetworkCheckResult(
            is_online=False,
            latency_ms=None,
            check_method="http",
            checked_at=datetime.utcnow(),
            error="All HTTP endpoints unreachable",
        )

        logger.warning("HTTP connectivity check: OFFLINE")
        self.last_check = result
        return result

    async def check_connectivity(
        self, method: str = "auto"
    ) -> NetworkCheckResult:
        """
        Check network connectivity using specified method.

        Args:
            method: Check method ('dns', 'http', or 'auto')

        Returns:
            NetworkCheckResult with check status
        """
        self.check_count += 1

        if method == "dns":
            result = await self.check_dns_connectivity()
        elif method == "http":
            result = await self.check_http_connectivity()
        else:  # auto - try DNS first (faster), fallback to HTTP
            result = await self.check_dns_connectivity()

            if not result.is_online:
                # DNS failed, try HTTP
                logger.debug("DNS check failed, trying HTTP...")
                result = await self.check_http_connectivity()

        # Update statistics
        if result.is_online:
            self.online_count += 1
        else:
            self.offline_count += 1

        logger.info(
            f"Network check #{self.check_count}: "
            f"{'ONLINE' if result.is_online else 'OFFLINE'} "
            f"(method={result.check_method}, "
            f"stats={self.online_count}/{self.check_count} online)"
        )

        return result

    async def is_online(self, method: str = "auto") -> bool:
        """
        Quick check if network is online.

        Args:
            method: Check method ('dns', 'http', or 'auto')

        Returns:
            True if online, False if offline
        """
        result = await self.check_connectivity(method=method)
        return result.is_online

    def get_last_check(self) -> Optional[NetworkCheckResult]:
        """
        Get last network check result.

        Returns:
            Last NetworkCheckResult or None if no checks performed
        """
        return self.last_check

    def get_statistics(self) -> dict:
        """
        Get detector statistics.

        Returns:
            Dictionary with check statistics
        """
        online_rate = (
            (self.online_count / self.check_count * 100) if self.check_count > 0 else 0
        )

        return {
            "total_checks": self.check_count,
            "online_checks": self.online_count,
            "offline_checks": self.offline_count,
            "online_rate_percent": round(online_rate, 2),
            "last_check": self.last_check.model_dump() if self.last_check else None,
        }

    def reset_statistics(self):
        """Reset check statistics."""
        self.check_count = 0
        self.online_count = 0
        self.offline_count = 0
        self.last_check = None
        logger.debug("Reset network detector statistics")


class NetworkMonitor:
    """Continuous network monitoring with auto mode switching."""

    def __init__(
        self,
        detector: ModeDetector,
        check_interval: int = 30,
        on_status_change=None,
    ):
        """
        Initialize network monitor.

        Args:
            detector: ModeDetector instance
            check_interval: Seconds between checks
            on_status_change: Callback for status changes (online <-> offline)
        """
        self.detector = detector
        self.check_interval = check_interval
        self.on_status_change = on_status_change

        self.is_running = False
        self.task: Optional[asyncio.Task] = None
        self.last_status: Optional[bool] = None

    async def start(self):
        """Start continuous monitoring."""
        if self.is_running:
            logger.warning("Network monitor already running")
            return

        self.is_running = True
        self.task = asyncio.create_task(self._monitor_loop())
        logger.info(
            f"Network monitor started (interval={self.check_interval}s)"
        )

    async def stop(self):
        """Stop continuous monitoring."""
        if not self.is_running:
            return

        self.is_running = False

        if self.task:
            self.task.cancel()
            try:
                await self.task
            except asyncio.CancelledError:
                pass

        logger.info("Network monitor stopped")

    async def _monitor_loop(self):
        """Main monitoring loop."""
        while self.is_running:
            try:
                # Check connectivity
                result = await self.detector.check_connectivity()

                # Detect status change
                if self.last_status is not None and result.is_online != self.last_status:
                    logger.warning(
                        f"Network status changed: "
                        f"{'OFFLINE -> ONLINE' if result.is_online else 'ONLINE -> OFFLINE'}"
                    )

                    # Trigger callback
                    if self.on_status_change:
                        try:
                            if asyncio.iscoroutinefunction(self.on_status_change):
                                await self.on_status_change(result.is_online)
                            else:
                                self.on_status_change(result.is_online)
                        except Exception as e:
                            logger.error(f"Error in status change callback: {e}")

                self.last_status = result.is_online

                # Sleep until next check
                await asyncio.sleep(self.check_interval)

            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Error in network monitor loop: {e}")
                await asyncio.sleep(self.check_interval)


# Singleton instance
_detector: Optional[ModeDetector] = None
_monitor: Optional[NetworkMonitor] = None


def get_mode_detector() -> ModeDetector:
    """Get singleton mode detector instance."""
    global _detector
    if _detector is None:
        _detector = ModeDetector()
    return _detector


def get_network_monitor(
    check_interval: int = 30,
    on_status_change=None,
) -> NetworkMonitor:
    """Get singleton network monitor instance."""
    global _monitor
    if _monitor is None:
        detector = get_mode_detector()
        _monitor = NetworkMonitor(
            detector=detector,
            check_interval=check_interval,
            on_status_change=on_status_change,
        )
    return _monitor
