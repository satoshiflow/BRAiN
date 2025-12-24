"""
Network Guard

HTTP request interception and blocking for sovereign/offline modes.
Implements fail-closed security with comprehensive audit logging.
"""

from typing import Optional, Set, Callable, List
from urllib.parse import urlparse
from datetime import datetime
import httpx
from loguru import logger

from backend.app.modules.sovereign_mode.schemas import OperationMode


class NetworkGuardException(Exception):
    """Exception raised when network access is blocked."""

    def __init__(
        self,
        message: str,
        url: str,
        mode: OperationMode,
        reason: str,
    ):
        super().__init__(message)
        self.url = url
        self.mode = mode
        self.reason = reason
        self.timestamp = datetime.utcnow()


class NetworkGuard:
    """
    Network request guard with fail-closed security.

    Blocks external HTTP requests in sovereign/offline modes.
    Provides whitelist for allowed domains.
    """

    # Localhost/loopback addresses (always allowed)
    LOCALHOST_HOSTS = {
        "localhost",
        "127.0.0.1",
        "::1",
        "0.0.0.0",
    }

    def __init__(
        self,
        current_mode: OperationMode = OperationMode.ONLINE,
        allowed_domains: Optional[Set[str]] = None,
        on_block_callback: Optional[Callable] = None,
    ):
        """
        Initialize network guard.

        Args:
            current_mode: Current operation mode
            allowed_domains: Set of whitelisted domains
            on_block_callback: Callback when request is blocked
        """
        self.current_mode = current_mode
        self.allowed_domains = allowed_domains or set()
        self.on_block_callback = on_block_callback

        # Statistics
        self.blocked_count = 0
        self.allowed_count = 0
        self.blocked_requests: List[dict] = []

        # Always allow localhost
        self.allowed_domains.update(self.LOCALHOST_HOSTS)

        logger.info(
            f"Network guard initialized: mode={current_mode}, "
            f"allowed_domains={len(self.allowed_domains)}"
        )

    def set_mode(self, mode: OperationMode):
        """
        Update operation mode.

        Args:
            mode: New operation mode
        """
        old_mode = self.current_mode
        self.current_mode = mode

        logger.info(f"Network guard mode changed: {old_mode} -> {mode}")

    def add_allowed_domain(self, domain: str):
        """
        Add domain to whitelist.

        Args:
            domain: Domain to allow (e.g., 'example.com')
        """
        self.allowed_domains.add(domain.lower())
        logger.debug(f"Added allowed domain: {domain}")

    def remove_allowed_domain(self, domain: str):
        """
        Remove domain from whitelist.

        Args:
            domain: Domain to remove
        """
        # Don't allow removing localhost
        if domain.lower() in self.LOCALHOST_HOSTS:
            logger.warning(f"Cannot remove localhost domain: {domain}")
            return

        self.allowed_domains.discard(domain.lower())
        logger.debug(f"Removed allowed domain: {domain}")

    def is_domain_allowed(self, url: str) -> bool:
        """
        Check if domain is whitelisted.

        Args:
            url: URL to check

        Returns:
            True if domain is allowed
        """
        try:
            parsed = urlparse(url)
            hostname = parsed.hostname

            if not hostname:
                return False

            hostname_lower = hostname.lower()

            # Check exact match
            if hostname_lower in self.allowed_domains:
                return True

            # Check wildcard domains (*.example.com)
            for allowed in self.allowed_domains:
                if allowed.startswith("*."):
                    domain_suffix = allowed[2:]  # Remove "*."
                    if hostname_lower.endswith(domain_suffix):
                        return True

            return False

        except Exception as e:
            logger.error(f"Error parsing URL {url}: {e}")
            return False

    def should_block_request(self, url: str) -> tuple[bool, str]:
        """
        Determine if request should be blocked.

        Args:
            url: URL to check

        Returns:
            Tuple of (should_block, reason)
        """
        # In ONLINE mode, allow all (except explicit blocks)
        if self.current_mode == OperationMode.ONLINE:
            return False, "online_mode"

        # In OFFLINE/SOVEREIGN/QUARANTINE modes, check whitelist
        if self.is_domain_allowed(url):
            return False, "domain_whitelisted"

        # Block the request
        reason = f"external_request_in_{self.current_mode.value}_mode"
        return True, reason

    def check_request(self, url: str, method: str = "GET") -> bool:
        """
        Check if request is allowed.

        Args:
            url: URL to request
            method: HTTP method

        Returns:
            True if allowed

        Raises:
            NetworkGuardException: If request is blocked
        """
        should_block, reason = self.should_block_request(url)

        if should_block:
            # Record blocked request
            self.blocked_count += 1
            blocked_info = {
                "url": url,
                "method": method,
                "mode": self.current_mode.value,
                "reason": reason,
                "timestamp": datetime.utcnow().isoformat(),
            }
            self.blocked_requests.append(blocked_info)

            # Trigger callback
            if self.on_block_callback:
                try:
                    self.on_block_callback(blocked_info)
                except Exception as e:
                    logger.error(f"Error in block callback: {e}")

            # Log blocked request
            logger.warning(
                f"BLOCKED request: {method} {url} "
                f"(mode={self.current_mode.value}, reason={reason})"
            )

            # Raise exception
            raise NetworkGuardException(
                message=f"Network request blocked in {self.current_mode.value} mode",
                url=url,
                mode=self.current_mode,
                reason=reason,
            )

        # Request allowed
        self.allowed_count += 1
        logger.debug(f"ALLOWED request: {method} {url} (reason={reason})")

        return True

    def get_statistics(self) -> dict:
        """
        Get guard statistics.

        Returns:
            Dictionary with statistics
        """
        return {
            "current_mode": self.current_mode.value,
            "allowed_domains": list(self.allowed_domains),
            "blocked_count": self.blocked_count,
            "allowed_count": self.allowed_count,
            "total_requests": self.blocked_count + self.allowed_count,
            "recent_blocked": self.blocked_requests[-10:],  # Last 10
        }

    def reset_statistics(self):
        """Reset guard statistics."""
        self.blocked_count = 0
        self.allowed_count = 0
        self.blocked_requests = []
        logger.debug("Reset network guard statistics")


class GuardedHTTPTransport(httpx.AsyncHTTPTransport):
    """
    Custom httpx transport with network guard integration.

    Intercepts all HTTP requests and enforces network guard rules.
    """

    def __init__(self, guard: NetworkGuard, *args, **kwargs):
        """
        Initialize guarded transport.

        Args:
            guard: NetworkGuard instance
            *args, **kwargs: Passed to AsyncHTTPTransport
        """
        super().__init__(*args, **kwargs)
        self.guard = guard

    async def handle_async_request(self, request):
        """
        Handle HTTP request with guard check.

        Args:
            request: httpx Request

        Returns:
            httpx Response

        Raises:
            NetworkGuardException: If request is blocked
        """
        url = str(request.url)
        method = request.method

        # Check with guard
        self.guard.check_request(url, method)

        # Request allowed, proceed
        return await super().handle_async_request(request)


def create_guarded_client(
    guard: NetworkGuard,
    **kwargs,
) -> httpx.AsyncClient:
    """
    Create httpx AsyncClient with network guard.

    Args:
        guard: NetworkGuard instance
        **kwargs: Additional httpx.AsyncClient arguments

    Returns:
        Guarded AsyncClient instance
    """
    transport = GuardedHTTPTransport(guard=guard)

    return httpx.AsyncClient(transport=transport, **kwargs)


class NetworkGuardMiddleware:
    """
    Middleware for integrating network guard with existing httpx clients.

    Can be used to patch existing clients at runtime.
    """

    def __init__(self, guard: NetworkGuard):
        """
        Initialize middleware.

        Args:
            guard: NetworkGuard instance
        """
        self.guard = guard

    async def __call__(self, request, call_next):
        """
        Middleware handler.

        Args:
            request: Request object
            call_next: Next middleware/handler

        Returns:
            Response

        Raises:
            NetworkGuardException: If request is blocked
        """
        url = str(request.url)
        method = request.method

        # Check with guard
        self.guard.check_request(url, method)

        # Proceed to next handler
        return await call_next(request)


# Singleton instance
_guard: Optional[NetworkGuard] = None


def get_network_guard() -> NetworkGuard:
    """Get singleton network guard instance."""
    global _guard
    if _guard is None:
        _guard = NetworkGuard(current_mode=OperationMode.ONLINE)
    return _guard


def patch_httpx_client(client: httpx.AsyncClient, guard: Optional[NetworkGuard] = None):
    """
    Patch existing httpx client with network guard.

    Args:
        client: httpx.AsyncClient to patch
        guard: Optional NetworkGuard (uses singleton if None)
    """
    if guard is None:
        guard = get_network_guard()

    # Replace transport
    client._transport = GuardedHTTPTransport(guard=guard)

    logger.info("Patched httpx client with network guard")


async def check_host_firewall_state() -> dict:
    """
    Check if host firewall is enforcing sovereign mode.

    Executes sovereign-fw.sh check command via subprocess to verify
    that iptables rules are active on the host system.

    Returns:
        Dictionary with firewall state:
        {
            "firewall_enabled": bool,
            "mode": "sovereign" | "connected" | "unknown",
            "rules_count": int,
            "last_check": datetime,
            "error": Optional[str]
        }
    """
    import asyncio
    import os
    from pathlib import Path

    # Find script path (relative to backend directory)
    backend_root = Path(__file__).parent.parent.parent.parent
    script_path = backend_root.parent / "scripts" / "sovereign-fw.sh"

    result = {
        "firewall_enabled": False,
        "mode": "unknown",
        "rules_count": 0,
        "last_check": datetime.utcnow(),
        "error": None
    }

    # Check if script exists
    if not script_path.exists():
        result["error"] = f"Firewall script not found: {script_path}"
        logger.warning(result["error"])
        return result

    try:
        # Execute status command (doesn't require root to read state)
        proc = await asyncio.create_subprocess_exec(
            str(script_path),
            "status",
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE
        )

        stdout, stderr = await asyncio.wait_for(
            proc.communicate(),
            timeout=10.0
        )

        # Parse output
        output = stdout.decode('utf-8')

        # Extract mode from output (looking for "Mode: sovereign" or "Mode: connected")
        for line in output.split('\n'):
            if 'Mode:' in line:
                mode_text = line.split('Mode:')[1].strip()
                if 'sovereign' in mode_text.lower():
                    result["mode"] = "sovereign"
                    result["firewall_enabled"] = True
                elif 'connected' in mode_text.lower():
                    result["mode"] = "connected"
                    result["firewall_enabled"] = False
                break

            if 'Active Rules:' in line:
                try:
                    rules_text = line.split('Active Rules:')[1].strip()
                    result["rules_count"] = int(rules_text)
                except (ValueError, IndexError):
                    pass

        logger.debug(f"Host firewall check: mode={result['mode']}, rules={result['rules_count']}")

    except asyncio.TimeoutError:
        result["error"] = "Firewall script timeout"
        logger.warning("Timeout checking host firewall state")

    except Exception as e:
        result["error"] = str(e)
        logger.error(f"Error checking host firewall state: {e}")

    return result
