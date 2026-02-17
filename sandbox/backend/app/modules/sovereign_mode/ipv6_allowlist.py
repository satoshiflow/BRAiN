"""
IPv6 Allowlist Validation

Validate and manage IPv6 allowlist for sovereign mode.
"""

import ipaddress
from typing import List, Optional, Set
from loguru import logger
from pydantic import BaseModel


class IPv6Address(BaseModel):
    """Validated IPv6 address."""

    address: str
    is_network: bool  # True if CIDR notation
    network_size: Optional[int] = None  # Prefix length if network


class IPv6AllowlistValidator:
    """
    Validate IPv6 allowlist entries.

    Supports:
    - Individual addresses: fc00::1
    - CIDR networks: fc00::/7
    - Link-local addresses: fe80::/10
    - Unique Local Addresses (ULA): fc00::/7, fd00::/8
    """

    # Well-known IPv6 ranges
    LOCALHOST = ipaddress.IPv6Address("::1")
    ULA_PREFIX = ipaddress.IPv6Network("fc00::/7")  # Unique Local Addresses
    LINK_LOCAL_PREFIX = ipaddress.IPv6Network("fe80::/10")  # Link-local

    def __init__(self):
        self._validated_addresses: Set[str] = set()
        self._validated_networks: List[ipaddress.IPv6Network] = []

    def validate_address(self, address_str: str) -> IPv6Address:
        """
        Validate a single IPv6 address or network.

        Args:
            address_str: IPv6 address (e.g., "fc00::1" or "fc00::/7")

        Returns:
            IPv6Address: Validated address

        Raises:
            ValueError: If address is invalid
        """
        address_str = address_str.strip()

        # Check if it's a network (CIDR notation)
        if "/" in address_str:
            try:
                network = ipaddress.IPv6Network(address_str, strict=False)
                return IPv6Address(
                    address=str(network),
                    is_network=True,
                    network_size=network.prefixlen,
                )
            except ValueError as e:
                raise ValueError(f"Invalid IPv6 network '{address_str}': {e}")

        # Individual address
        else:
            try:
                addr = ipaddress.IPv6Address(address_str)
                return IPv6Address(
                    address=str(addr),
                    is_network=False,
                )
            except ValueError as e:
                raise ValueError(f"Invalid IPv6 address '{address_str}': {e}")

    def validate_allowlist(
        self, allowlist_str: str
    ) -> tuple[List[IPv6Address], List[str]]:
        """
        Validate an allowlist string (comma-separated).

        Args:
            allowlist_str: Comma-separated IPv6 addresses/networks

        Returns:
            Tuple of (valid_addresses, errors)
        """
        if not allowlist_str or not allowlist_str.strip():
            return ([], [])

        valid_addresses = []
        errors = []

        for entry in allowlist_str.split(","):
            entry = entry.strip()

            if not entry:
                continue

            try:
                validated = self.validate_address(entry)
                valid_addresses.append(validated)

            except ValueError as e:
                errors.append(str(e))

        return (valid_addresses, errors)

    def is_address_in_allowlist(
        self, address: str, allowlist: List[IPv6Address]
    ) -> bool:
        """
        Check if an IPv6 address is in the allowlist.

        Args:
            address: IPv6 address to check
            allowlist: List of allowed addresses/networks

        Returns:
            True if address is allowed
        """
        try:
            check_addr = ipaddress.IPv6Address(address)

        except ValueError:
            logger.warning(f"Invalid IPv6 address for checking: {address}")
            return False

        for allowed in allowlist:
            if allowed.is_network:
                # Check if address is in network
                try:
                    network = ipaddress.IPv6Network(allowed.address, strict=False)
                    if check_addr in network:
                        return True

                except ValueError:
                    pass

            else:
                # Check exact match
                try:
                    allowed_addr = ipaddress.IPv6Address(allowed.address)
                    if check_addr == allowed_addr:
                        return True

                except ValueError:
                    pass

        return False

    def get_recommended_allowlist(self) -> str:
        """
        Get recommended allowlist for typical use cases.

        Returns:
            Comma-separated string of recommended addresses
        """
        return "::1/128,fc00::/7,fe80::/10"

    def get_allowlist_info(
        self, allowlist: List[IPv6Address]
    ) -> dict:
        """
        Get information about an allowlist.

        Returns:
            Dictionary with allowlist statistics
        """
        total_addresses = sum(1 for addr in allowlist if not addr.is_network)
        total_networks = sum(1 for addr in allowlist if addr.is_network)

        # Calculate approximate total IPs (for networks)
        total_ips_approx = total_addresses

        for addr in allowlist:
            if addr.is_network and addr.network_size is not None:
                # 2^(128 - prefix_length) addresses
                network_size = 2 ** (128 - addr.network_size)
                if network_size < 1_000_000:  # Only count if reasonable
                    total_ips_approx += network_size

        has_localhost = any(
            addr.address == "::1/128" or addr.address == "::1"
            for addr in allowlist
        )
        has_ula = any(
            addr.address.startswith("fc00:") or addr.address.startswith("fd00:")
            for addr in allowlist
        )
        has_link_local = any(
            addr.address.startswith("fe80:") for addr in allowlist
        )

        return {
            "total_entries": len(allowlist),
            "individual_addresses": total_addresses,
            "networks": total_networks,
            "approximate_total_ips": total_ips_approx if total_ips_approx < 1_000_000 else "large",
            "includes_localhost": has_localhost,
            "includes_ula": has_ula,
            "includes_link_local": has_link_local,
        }


# Singleton
_validator: Optional[IPv6AllowlistValidator] = None


def get_ipv6_allowlist_validator() -> IPv6AllowlistValidator:
    """Get singleton IPv6 allowlist validator."""
    global _validator
    if _validator is None:
        _validator = IPv6AllowlistValidator()
    return _validator
