"""
Hetzner DNS Module - HTTP Client (Sprint II)

HTTP client for Hetzner DNS API.

API Documentation: https://dns.hetzner.com/api-docs

Features:
- Async HTTP client with httpx
- Bearer token authentication
- Zone and record CRUD operations
- Timeout enforcement

Security:
- Token from ENV (no hardcoding)
- HTTPS only
- Timeout enforcement

API Base URL: https://dns.hetzner.com/api/v1
"""

from __future__ import annotations

import os
from typing import List, Optional, Dict, Any

import httpx
from loguru import logger

from .schemas import DNSZone, DNSRecord, DNSRecordType


# ============================================================================
# Configuration
# ============================================================================

DEFAULT_API_BASE_URL = "https://dns.hetzner.com/api/v1"
DEFAULT_TIMEOUT = int(os.getenv("HETZNER_DNS_API_TIMEOUT", "30"))


# ============================================================================
# Hetzner DNS Client
# ============================================================================


class HetznerDNSClient:
    """
    Async HTTP client for Hetzner DNS API (Sprint II).

    Features:
    - Zone listing
    - Record CRUD operations
    - Bearer token authentication
    - Timeout enforcement
    """

    def __init__(
        self,
        api_token: str,
        api_base_url: str = DEFAULT_API_BASE_URL,
        timeout: int = DEFAULT_TIMEOUT,
    ):
        """
        Initialize Hetzner DNS client.

        Args:
            api_token: Hetzner DNS API token
            api_base_url: API base URL
            timeout: Request timeout in seconds
        """
        self.api_token = api_token
        self.api_base_url = api_base_url.rstrip("/")
        self.timeout = timeout

        # Headers with Bearer token
        self.headers = {
            "Auth-API-Token": api_token,  # Hetzner uses Auth-API-Token header
            "Content-Type": "application/json",
        }

        logger.info(
            f"HetznerDNSClient initialized "
            f"(api_base={self.api_base_url}, timeout={self.timeout}s)"
        )

    # ========================================================================
    # Zones
    # ========================================================================

    async def get_zones(self) -> List[DNSZone]:
        """
        Get all DNS zones.

        Returns:
            List of DNSZone objects

        Raises:
            httpx.HTTPError: On API request failure
        """
        url = f"{self.api_base_url}/zones"

        async with httpx.AsyncClient(timeout=self.timeout) as client:
            response = await client.get(url, headers=self.headers)
            response.raise_for_status()

            data = response.json()
            zones_data = data.get("zones", [])

            zones = [DNSZone(**zone) for zone in zones_data]

            logger.debug(f"Retrieved {len(zones)} DNS zones")
            return zones

    async def get_zone_by_name(self, zone_name: str) -> Optional[DNSZone]:
        """
        Get zone by name.

        Args:
            zone_name: Zone name (e.g., 'example.com')

        Returns:
            DNSZone if found, None otherwise

        Raises:
            httpx.HTTPError: On API request failure
        """
        zones = await self.get_zones()

        for zone in zones:
            if zone.name == zone_name:
                return zone

        return None

    async def get_zone_by_id(self, zone_id: str) -> Optional[DNSZone]:
        """
        Get zone by ID.

        Args:
            zone_id: Zone ID

        Returns:
            DNSZone if found, None otherwise

        Raises:
            httpx.HTTPError: On API request failure
        """
        url = f"{self.api_base_url}/zones/{zone_id}"

        async with httpx.AsyncClient(timeout=self.timeout) as client:
            try:
                response = await client.get(url, headers=self.headers)
                response.raise_for_status()

                data = response.json()
                zone_data = data.get("zone", {})

                return DNSZone(**zone_data)

            except httpx.HTTPStatusError as e:
                if e.response.status_code == 404:
                    return None
                raise

    # ========================================================================
    # Records
    # ========================================================================

    async def get_records(self, zone_id: str) -> List[DNSRecord]:
        """
        Get all records for a zone.

        Args:
            zone_id: Zone ID

        Returns:
            List of DNSRecord objects

        Raises:
            httpx.HTTPError: On API request failure
        """
        url = f"{self.api_base_url}/records"
        params = {"zone_id": zone_id}

        async with httpx.AsyncClient(timeout=self.timeout) as client:
            response = await client.get(url, headers=self.headers, params=params)
            response.raise_for_status()

            data = response.json()
            records_data = data.get("records", [])

            records = [DNSRecord(**record) for record in records_data]

            logger.debug(f"Retrieved {len(records)} DNS records for zone {zone_id}")
            return records

    async def get_record_by_id(self, record_id: str) -> Optional[DNSRecord]:
        """
        Get record by ID.

        Args:
            record_id: Record ID

        Returns:
            DNSRecord if found, None otherwise

        Raises:
            httpx.HTTPError: On API request failure
        """
        url = f"{self.api_base_url}/records/{record_id}"

        async with httpx.AsyncClient(timeout=self.timeout) as client:
            try:
                response = await client.get(url, headers=self.headers)
                response.raise_for_status()

                data = response.json()
                record_data = data.get("record", {})

                return DNSRecord(**record_data)

            except httpx.HTTPStatusError as e:
                if e.response.status_code == 404:
                    return None
                raise

    async def create_record(
        self,
        zone_id: str,
        record_type: DNSRecordType,
        name: str,
        value: str,
        ttl: int = 300,
    ) -> DNSRecord:
        """
        Create a new DNS record.

        Args:
            zone_id: Zone ID
            record_type: Record type (A, AAAA, CNAME, etc.)
            name: Record name (@ for root, subdomain, etc.)
            value: Record value (IP, target, etc.)
            ttl: TTL in seconds

        Returns:
            Created DNSRecord

        Raises:
            httpx.HTTPError: On API request failure
        """
        url = f"{self.api_base_url}/records"

        payload = {
            "zone_id": zone_id,
            "type": record_type.value,
            "name": name,
            "value": value,
            "ttl": ttl,
        }

        async with httpx.AsyncClient(timeout=self.timeout) as client:
            response = await client.post(url, headers=self.headers, json=payload)
            response.raise_for_status()

            data = response.json()
            record_data = data.get("record", {})

            record = DNSRecord(**record_data)

            logger.info(
                f"Created DNS record: {record.type} {record.name} -> {record.value} "
                f"(zone_id={zone_id}, ttl={ttl})"
            )

            return record

    async def update_record(
        self,
        record_id: str,
        zone_id: str,
        record_type: Optional[DNSRecordType] = None,
        name: Optional[str] = None,
        value: Optional[str] = None,
        ttl: Optional[int] = None,
    ) -> DNSRecord:
        """
        Update an existing DNS record.

        Args:
            record_id: Record ID
            zone_id: Zone ID
            record_type: Record type (optional)
            name: Record name (optional)
            value: Record value (optional)
            ttl: TTL (optional)

        Returns:
            Updated DNSRecord

        Raises:
            httpx.HTTPError: On API request failure
        """
        url = f"{self.api_base_url}/records/{record_id}"

        # Build payload with only provided fields
        payload: Dict[str, Any] = {"zone_id": zone_id}

        if record_type is not None:
            payload["type"] = record_type.value
        if name is not None:
            payload["name"] = name
        if value is not None:
            payload["value"] = value
        if ttl is not None:
            payload["ttl"] = ttl

        async with httpx.AsyncClient(timeout=self.timeout) as client:
            response = await client.put(url, headers=self.headers, json=payload)
            response.raise_for_status()

            data = response.json()
            record_data = data.get("record", {})

            record = DNSRecord(**record_data)

            logger.info(
                f"Updated DNS record {record_id}: {record.type} {record.name} -> {record.value}"
            )

            return record

    async def delete_record(self, record_id: str) -> bool:
        """
        Delete a DNS record.

        Args:
            record_id: Record ID

        Returns:
            True if deleted successfully

        Raises:
            httpx.HTTPError: On API request failure
        """
        url = f"{self.api_base_url}/records/{record_id}"

        async with httpx.AsyncClient(timeout=self.timeout) as client:
            response = await client.delete(url, headers=self.headers)
            response.raise_for_status()

            logger.info(f"Deleted DNS record {record_id}")
            return True

    async def find_record(
        self,
        zone_id: str,
        record_type: DNSRecordType,
        name: str,
    ) -> Optional[DNSRecord]:
        """
        Find a record by zone, type, and name.

        Args:
            zone_id: Zone ID
            record_type: Record type
            name: Record name

        Returns:
            DNSRecord if found, None otherwise

        Raises:
            httpx.HTTPError: On API request failure
        """
        records = await self.get_records(zone_id)

        for record in records:
            if record.type == record_type and record.name == name:
                return record

        return None
