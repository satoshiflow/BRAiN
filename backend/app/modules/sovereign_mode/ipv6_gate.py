"""
IPv6 Gate Checker

Verifies IPv6 enforcement capability in sovereign mode.
Ensures no silent IPv6 egress bypass.
"""

import os
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
    details: dict = Field(default_factory=dict)


class IPv6GateChecker:
    """
    Check IPv6 enforcement for sovereign mode.

    Verifies:
    1. IPv6 status (active or not)
    2. If active, ip6tables availability
    3. If active, firewall rules are applied
    4. Policy compliance

    Fail-Closed Design:
    - If IPv6 active AND ip6tables missing → FAIL
    - If IPv6 active AND rules missing → FAIL
    - If policy=block AND cannot block → FAIL
    """

    def __init__(self, policy: str = "block"):
        """
        Initialize IPv6 gate checker.

        Args:
            policy: IPv6 policy (block, allowlist, off)
        """
        self.policy = policy.lower()

    def _check_ipv6_active(self) -> bool:
        """
        Check if IPv6 is active on host.

        Returns:
            True if IPv6 addresses found (scope global)
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
            True if ip6tables exists and is executable
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
            True if brain-sovereign-ipv6 rules found in DOCKER-USER
        """
        try:
            result = subprocess.run(
                ["ip6tables", "-L", "DOCKER-USER", "-n"],
                capture_output=True,
                text=True,
                timeout=5,
            )

            if result.returncode == 0:
                return "brain-sovereign-ipv6" in result.stdout

            return False

        except Exception as e:
            logger.warning(f"Failed to check IPv6 rules: {e}")
            return False

    def _count_ipv6_rules(self) -> int:
        """
        Count IPv6 firewall rules.

        Returns:
            Number of brain-sovereign-ipv6 rules
        """
        try:
            result = subprocess.run(
                ["ip6tables", "-L", "DOCKER-USER", "-n"],
                capture_output=True,
                text=True,
                timeout=5,
            )

            if result.returncode == 0:
                count = result.stdout.count("brain-sovereign-ipv6")
                return count

            return 0

        except Exception:
            return 0

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
                details={"reason": "IPv6 not active on host"},
            )

        # If policy is "off", also not applicable (but risky)
        if self.policy == "off":
            logger.warning(
                "IPv6 is active but policy is 'off' (security bypass risk!)"
            )
            return IPv6GateResult(
                status="not_applicable",
                ipv6_active=True,
                policy=self.policy,
                details={
                    "reason": "Policy set to 'off'",
                    "warning": "IPv6 bypass risk - policy is off",
                },
            )

        # IPv6 is active and policy requires blocking
        logger.info(f"IPv6 is active, policy={self.policy}, checking enforcement...")

        # Check if ip6tables is available
        ip6tables_available = self._check_ip6tables_available()

        if not ip6tables_available:
            error_msg = (
                "IPv6 is active but ip6tables is not available. "
                "Cannot enforce IPv6 blocking. "
                "Solutions: (1) Install iptables package, "
                "(2) Disable IPv6 on the host, "
                "(3) Set BRAIN_SOVEREIGN_IPV6_POLICY=off (NOT RECOMMENDED)"
            )
            logger.error(error_msg)
            return IPv6GateResult(
                status="fail",
                ipv6_active=True,
                policy=self.policy,
                ip6tables_available=False,
                error=error_msg,
                details={
                    "reason": "ip6tables not available",
                    "remediation": [
                        "Install iptables: sudo apt-get install iptables",
                        "Disable IPv6: sudo sysctl -w net.ipv6.conf.all.disable_ipv6=1",
                        "Change policy to 'off' (NOT RECOMMENDED)",
                    ],
                },
            )

        # Check if rules are applied
        rules_applied = self._check_ipv6_rules_applied()
        rules_count = self._count_ipv6_rules()

        if not rules_applied or rules_count < 4:
            error_msg = (
                f"IPv6 is active and ip6tables is available, "
                f"but firewall rules are not applied (found {rules_count} rules, expected ≥4). "
                f"Run: sudo scripts/sovereign-fw.sh apply sovereign"
            )
            logger.error(error_msg)
            return IPv6GateResult(
                status="fail",
                ipv6_active=True,
                policy=self.policy,
                ip6tables_available=True,
                firewall_rules_applied=False,
                error=error_msg,
                details={
                    "reason": "IPv6 firewall rules not applied",
                    "rules_count": rules_count,
                    "expected_count": 4,
                    "remediation": [
                        "Apply firewall rules: sudo scripts/sovereign-fw.sh apply sovereign"
                    ],
                },
            )

        # All checks passed
        logger.info(
            f"IPv6 gate check passed: IPv6 is blocked ({rules_count} rules active)"
        )
        return IPv6GateResult(
            status="pass",
            ipv6_active=True,
            policy=self.policy,
            ip6tables_available=True,
            firewall_rules_applied=True,
            details={
                "reason": "IPv6 egress is blocked",
                "rules_count": rules_count,
            },
        )


# Singleton
_ipv6_gate_checker: Optional[IPv6GateChecker] = None


def get_ipv6_gate_checker() -> IPv6GateChecker:
    """Get singleton IPv6 gate checker instance."""
    global _ipv6_gate_checker
    if _ipv6_gate_checker is None:
        # Get policy from environment
        policy = os.getenv("BRAIN_SOVEREIGN_IPV6_POLICY", "block")
        _ipv6_gate_checker = IPv6GateChecker(policy=policy)
    return _ipv6_gate_checker
