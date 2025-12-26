"""
IPv6 Gate Checker

Verifies IPv6 enforcement in sovereign mode.
Ensures IPv6 cannot be used as an egress bypass when sovereign mode is active.
"""

import subprocess
from typing import Literal, Optional
from loguru import logger
from pydantic import BaseModel, Field
from datetime import datetime


class IPv6GateResult(BaseModel):
    """Result of IPv6 gate check."""

    status: Literal["pass", "fail", "not_applicable"]
    ipv6_active: bool
    policy: str
    firewall_rules_applied: bool = False
    ip6tables_available: bool = False
    error: Optional[str] = None
    checked_at: datetime = Field(default_factory=datetime.utcnow)


class IPv6GateChecker:
    """
    Check IPv6 enforcement for sovereign mode.

    Verifies:
    1. IPv6 is detected (active or not)
    2. If active, ip6tables is available
    3. If active, firewall rules are applied
    """

    def __init__(self, policy: str = "block"):
        """
        Initialize IPv6 gate checker.

        Args:
            policy: IPv6 policy (block, allowlist, off)
        """
        self.policy = policy

    def _check_ipv6_active(self) -> bool:
        """
        Check if IPv6 is active on host.

        Returns:
            True if IPv6 addresses found (excluding link-local)
        """
        try:
            result = subprocess.run(
                ["ip", "-6", "addr", "show"],
                capture_output=True,
                text=True,
                timeout=5,
            )

            if result.returncode == 0:
                # Check if there are any inet6 addresses with global scope
                # (not just ::1 localhost or fe80:: link-local)
                lines = result.stdout.splitlines()
                for line in lines:
                    if "inet6" in line and "scope global" in line:
                        return True

            return False

        except Exception as e:
            logger.warning(f"Failed to check IPv6 status: {e}")
            return False

    def _check_ip6tables_available(self) -> bool:
        """
        Check if ip6tables command is available.

        Returns:
            True if ip6tables exists
        """
        try:
            result = subprocess.run(
                ["which", "ip6tables"],
                capture_output=True,
                timeout=5,
            )
            return result.returncode == 0

        except Exception:
            return False

    def _check_ipv6_rules_applied(self) -> bool:
        """
        Check if IPv6 firewall rules are applied.

        Returns:
            True if brain-sovereign-ipv6 rules found
        """
        try:
            result = subprocess.run(
                ["ip6tables", "-L", "DOCKER-USER", "-n"],
                capture_output=True,
                text=True,
                timeout=5,
            )

            if result.returncode == 0:
                # Look for our specific IPv6 rules
                return "brain-sovereign-ipv6" in result.stdout

            return False

        except Exception:
            return False

    async def check(self) -> IPv6GateResult:
        """
        Perform IPv6 gate check.

        Returns:
            IPv6GateResult with status and details
        """
        ipv6_active = self._check_ipv6_active()

        # If IPv6 not active, gate check not applicable
        if not ipv6_active:
            logger.info("IPv6 not active, gate check not applicable")
            return IPv6GateResult(
                status="not_applicable",
                ipv6_active=False,
                policy=self.policy,
            )

        # If policy is "off", also not applicable (but log warning)
        if self.policy == "off":
            logger.warning("IPv6 is active but policy is 'off' (security bypass risk)")
            return IPv6GateResult(
                status="not_applicable",
                ipv6_active=True,
                policy=self.policy,
            )

        # IPv6 is active and policy requires blocking
        # Check if ip6tables is available
        ip6tables_available = self._check_ip6tables_available()

        if not ip6tables_available:
            error_msg = (
                "IPv6 is active but ip6tables is not available. "
                "Cannot enforce IPv6 blocking. "
                "Install iptables package or disable IPv6 on the host."
            )
            logger.error(error_msg)
            return IPv6GateResult(
                status="fail",
                ipv6_active=True,
                policy=self.policy,
                ip6tables_available=False,
                error=error_msg,
            )

        # Check if rules are applied
        rules_applied = self._check_ipv6_rules_applied()

        if not rules_applied:
            error_msg = (
                "IPv6 is active and ip6tables is available, "
                "but firewall rules are not applied. "
                "Run: sudo scripts/sovereign-fw.sh apply sovereign"
            )
            logger.error(error_msg)
            return IPv6GateResult(
                status="fail",
                ipv6_active=True,
                policy=self.policy,
                ip6tables_available=True,
                firewall_rules_applied=False,
                error=error_msg,
            )

        # All checks passed
        logger.info("IPv6 gate check passed: IPv6 is properly blocked")
        return IPv6GateResult(
            status="pass",
            ipv6_active=True,
            policy=self.policy,
            ip6tables_available=True,
            firewall_rules_applied=True,
        )


# Singleton
_ipv6_gate_checker: Optional[IPv6GateChecker] = None


def get_ipv6_gate_checker() -> IPv6GateChecker:
    """Get singleton IPv6 gate checker instance."""
    global _ipv6_gate_checker
    if _ipv6_gate_checker is None:
        # Get policy from environment
        import os

        policy = os.getenv("BRAIN_SOVEREIGN_IPV6_POLICY", "block")
        _ipv6_gate_checker = IPv6GateChecker(policy=policy)
    return _ipv6_gate_checker
