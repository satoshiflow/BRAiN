"""
Hetzner DNS Module - Service Layer (Sprint II)

Business logic for DNS operations with security enforcement.

Features:
- Idempotent DNS record apply (upsert)
- Zone allowlist enforcement
- Default value injection from ENV
- Audit trail integration

Security:
- STRICT zone allowlist (no auto-discovery)
- ENV-based configuration (no secrets in Git)
- LOCAL trust tier only (enforced in router)

Configuration (ENV):
- HETZNER_DNS_API_TOKEN: API token (required)
- HETZNER_DNS_ALLOWED_ZONES: Comma-separated zone names (required)
- HETZNER_DNS_DEFAULT_TTL: Default TTL (optional, default: 300)
- BRAIN_PUBLIC_IPV4: Default IPv4 (optional)
- BRAIN_PUBLIC_IPV6: Default IPv6 (optional)
"""

from __future__ import annotations

import os
from typing import List, Optional, Literal

from loguru import logger

from .client import HetznerDNSClient
from .schemas import (
    DNSZone,
    DNSRecord,
    DNSRecordType,
    DNSApplyResult,
    HetznerDNSConfig,
)


# ============================================================================
# Configuration from ENV
# ============================================================================


def load_config_from_env() -> HetznerDNSConfig:
    """
    Load Hetzner DNS configuration from environment variables.

    Returns:
        HetznerDNSConfig from ENV

    Raises:
        ValueError: If required ENV vars missing
    """
    api_token = os.getenv("HETZNER_DNS_API_TOKEN")
    if not api_token:
        raise ValueError("HETZNER_DNS_API_TOKEN environment variable not set")

    allowed_zones_str = os.getenv("HETZNER_DNS_ALLOWED_ZONES", "")
    if not allowed_zones_str:
        raise ValueError("HETZNER_DNS_ALLOWED_ZONES environment variable not set")

    allowed_zones = [z.strip() for z in allowed_zones_str.split(",") if z.strip()]
    if not allowed_zones:
        raise ValueError("HETZNER_DNS_ALLOWED_ZONES is empty")

    return HetznerDNSConfig(
        api_token=api_token,
        allowed_zones=allowed_zones,
        default_ttl=int(os.getenv("HETZNER_DNS_DEFAULT_TTL", "300")),
        public_ipv4=os.getenv("BRAIN_PUBLIC_IPV4"),
        public_ipv6=os.getenv("BRAIN_PUBLIC_IPV6"),
        timeout=int(os.getenv("HETZNER_DNS_API_TIMEOUT", "30")),
    )


# ============================================================================
# DNS Service
# ============================================================================


class HetznerDNSService:
    """
    Hetzner DNS service with security enforcement (Sprint II).

    Features:
    - Idempotent apply (create or update)
    - Zone allowlist enforcement
    - Default value injection
    - Audit integration (TODO)
    """

    def __init__(self, config: Optional[HetznerDNSConfig] = None):
        """
        Initialize Hetzner DNS service.

        Args:
            config: DNS configuration (if None: load from ENV)
        """
        self.config = config or load_config_from_env()
        self.client = HetznerDNSClient(
            api_token=self.config.api_token,
            api_base_url=self.config.api_base_url,
            timeout=self.config.timeout,
        )

        logger.info(
            f"HetznerDNSService initialized "
            f"(allowed_zones={len(self.config.allowed_zones)}, "
            f"default_ttl={self.config.default_ttl})"
        )

    # ========================================================================
    # Zone Operations
    # ========================================================================

    async def list_zones(self) -> List[DNSZone]:
        """
        List all DNS zones (filtered by allowlist).

        Returns:
            List of DNSZone objects (only allowed zones)
        """
        all_zones = await self.client.get_zones()

        # Filter by allowlist
        allowed_zones = [
            zone
            for zone in all_zones
            if zone.name in self.config.allowed_zones
        ]

        logger.debug(
            f"Listed {len(allowed_zones)} allowed zones "
            f"(total: {len(all_zones)})"
        )

        return allowed_zones

    async def get_zone_by_name(self, zone_name: str) -> Optional[DNSZone]:
        """
        Get zone by name (with allowlist check).

        Args:
            zone_name: Zone name

        Returns:
            DNSZone if found and allowed, None otherwise

        Raises:
            ValueError: If zone not in allowlist
        """
        # Check allowlist
        if zone_name not in self.config.allowed_zones:
            raise ValueError(
                f"Zone '{zone_name}' not in allowlist. "
                f"Allowed zones: {', '.join(self.config.allowed_zones)}"
            )

        return await self.client.get_zone_by_name(zone_name)

    # ========================================================================
    # Record Operations
    # ========================================================================

    async def apply_dns_record(
        self,
        zone: str,
        record_type: DNSRecordType,
        name: str,
        value: Optional[str] = None,
        ttl: Optional[int] = None,
    ) -> DNSApplyResult:
        """
        Apply DNS record (idempotent upsert).

        Creates record if doesn't exist, updates if exists with different value.
        No action if record exists with same value.

        Args:
            zone: Zone name (e.g., 'example.com')
            record_type: Record type (A, AAAA, CNAME, etc.)
            name: Record name (@ for root, subdomain, etc.)
            value: Record value (if None: use default from ENV)
            ttl: TTL in seconds (if None: use default from ENV)

        Returns:
            DNSApplyResult with action taken

        Raises:
            ValueError: If zone not in allowlist or value missing
        """
        warnings: List[str] = []

        # Check allowlist
        if zone not in self.config.allowed_zones:
            return DNSApplyResult(
                success=False,
                zone=zone,
                record_type=record_type.value,
                name=name,
                value=value or "",
                ttl=ttl or self.config.default_ttl,
                action="no_change",
                message=f"Zone '{zone}' not in allowlist",
                errors=[f"Zone not allowed: {zone}"],
            )

        # Default value from ENV
        if value is None:
            if record_type == DNSRecordType.A and self.config.public_ipv4:
                value = self.config.public_ipv4
                logger.debug(f"Using default IPv4 from ENV: {value}")
            elif record_type == DNSRecordType.AAAA and self.config.public_ipv6:
                value = self.config.public_ipv6
                logger.debug(f"Using default IPv6 from ENV: {value}")
            else:
                return DNSApplyResult(
                    success=False,
                    zone=zone,
                    record_type=record_type.value,
                    name=name,
                    value="",
                    ttl=ttl or self.config.default_ttl,
                    action="no_change",
                    message="No value provided and no default available",
                    errors=[
                        f"No value provided for {record_type.value} record and "
                        f"BRAIN_PUBLIC_IPV{'4' if record_type == DNSRecordType.A else '6'} not set"
                    ],
                )

        # Default TTL
        if ttl is None:
            ttl = self.config.default_ttl

        try:
            # Get zone
            zone_obj = await self.get_zone_by_name(zone)
            if not zone_obj:
                return DNSApplyResult(
                    success=False,
                    zone=zone,
                    record_type=record_type.value,
                    name=name,
                    value=value,
                    ttl=ttl,
                    action="no_change",
                    message=f"Zone not found: {zone}",
                    errors=[f"Zone '{zone}' not found in Hetzner DNS"],
                )

            # Check if record exists
            existing_record = await self.client.find_record(
                zone_id=zone_obj.id,
                record_type=record_type,
                name=name,
            )

            if existing_record:
                # Record exists - check if update needed
                if existing_record.value == value and existing_record.ttl == ttl:
                    # No change needed
                    logger.info(
                        f"DNS record already exists with same value: "
                        f"{record_type.value} {name}.{zone} -> {value} (ttl={ttl})"
                    )

                    return DNSApplyResult(
                        success=True,
                        zone=zone,
                        record_type=record_type.value,
                        name=name,
                        value=value,
                        ttl=ttl,
                        action="no_change",
                        record_id=existing_record.id,
                        message="DNS record already exists with same value (no change needed)",
                    )

                else:
                    # Update needed
                    logger.info(
                        f"Updating DNS record: {record_type.value} {name}.{zone} "
                        f"({existing_record.value} -> {value}, ttl={existing_record.ttl} -> {ttl})"
                    )

                    updated_record = await self.client.update_record(
                        record_id=existing_record.id,
                        zone_id=zone_obj.id,
                        value=value,
                        ttl=ttl,
                    )

                    return DNSApplyResult(
                        success=True,
                        zone=zone,
                        record_type=record_type.value,
                        name=name,
                        value=value,
                        ttl=ttl,
                        action="updated",
                        record_id=updated_record.id,
                        message=f"DNS record updated successfully (old value: {existing_record.value})",
                    )

            else:
                # Record doesn't exist - create it
                logger.info(
                    f"Creating DNS record: {record_type.value} {name}.{zone} -> {value} (ttl={ttl})"
                )

                created_record = await self.client.create_record(
                    zone_id=zone_obj.id,
                    record_type=record_type,
                    name=name,
                    value=value,
                    ttl=ttl,
                )

                return DNSApplyResult(
                    success=True,
                    zone=zone,
                    record_type=record_type.value,
                    name=name,
                    value=value,
                    ttl=ttl,
                    action="created",
                    record_id=created_record.id,
                    message="DNS record created successfully",
                )

        except Exception as e:
            logger.error(f"Failed to apply DNS record: {e}")
            return DNSApplyResult(
                success=False,
                zone=zone,
                record_type=record_type.value,
                name=name,
                value=value,
                ttl=ttl,
                action="no_change",
                message=f"Failed to apply DNS record: {str(e)}",
                errors=[str(e)],
            )


# ============================================================================
# Singleton
# ============================================================================

_dns_service: Optional[HetznerDNSService] = None


def get_dns_service() -> HetznerDNSService:
    """
    Get singleton HetznerDNSService instance.

    Returns:
        HetznerDNSService

    Raises:
        ValueError: If required ENV vars not set
    """
    global _dns_service
    if _dns_service is None:
        _dns_service = HetznerDNSService()
    return _dns_service
