"""
DNS Automation Node (Sprint 8.4)

Automated DNS configuration using Hetzner DNS API.
Creates A/AAAA records with rollback support.
"""

from typing import Dict, Any, List, Optional
import os
from loguru import logger
import httpx

from app.modules.autonomous_pipeline.execution_node import (
    ExecutionNode,
    ExecutionContext,
    ExecutionNodeError,
    RollbackError,
)
from app.modules.autonomous_pipeline.schemas import ExecutionNodeSpec


class DNSNode(ExecutionNode):
    """
    DNS configuration execution node.

    Features:
    - Hetzner DNS API integration
    - A/AAAA record creation
    - TTL configuration
    - Rollback support (record deletion)
    - Dry-run simulation
    """

    # Hetzner DNS API
    HETZNER_API_BASE = "https://dns.hetzner.com/api/v1"
    DEFAULT_TTL = 3600  # 1 hour

    def __init__(self, spec: ExecutionNodeSpec):
        """
        Initialize DNS node.

        Args:
            spec: Node specification with executor_params:
                - domain: str (domain name, e.g., "example.com")
                - target_ip: str (IP address to point to)
                - record_type: str (A or AAAA, default: A)
                - ttl: int (TTL in seconds, default: 3600)
                - zone_id: str (Hetzner zone ID, optional)
                - hetzner_api_token: str (API token from env or param)
        """
        super().__init__(spec)

        # Extract parameters
        params = spec.executor_params
        self.domain = params.get("domain")
        self.target_ip = params.get("target_ip")
        self.record_type = params.get("record_type", "A")
        self.ttl = params.get("ttl", self.DEFAULT_TTL)
        self.zone_id = params.get("zone_id")

        # Validate required params
        if not self.domain:
            raise ExecutionNodeError("Missing required parameter: domain")
        if not self.target_ip:
            raise ExecutionNodeError("Missing required parameter: target_ip")

        # Validate record type
        if self.record_type not in ["A", "AAAA"]:
            raise ExecutionNodeError(f"Invalid record_type: {self.record_type}. Must be A or AAAA")

        # Get API token from environment or params
        self.api_token = params.get("hetzner_api_token") or os.getenv("HETZNER_DNS_API_TOKEN")
        if not self.api_token:
            logger.warning(
                f"[{self.node_id}] No Hetzner API token provided. "
                f"Set HETZNER_DNS_API_TOKEN env var or provide in executor_params."
            )

        # State
        self.created_record_id: Optional[str] = None
        self.zone_id_actual: Optional[str] = None

    async def execute(self, context: ExecutionContext) -> tuple[Dict[str, Any], List[str]]:
        """
        Create DNS record (LIVE mode).

        Args:
            context: Execution context

        Returns:
            Tuple of (output_data, artifact_paths)

        Raises:
            ExecutionNodeError: If DNS operation fails
        """
        logger.info(
            f"[{self.node_id}] Creating DNS record: {self.domain} -> {self.target_ip} "
            f"(type={self.record_type}, ttl={self.ttl})"
        )

        if not self.api_token:
            raise ExecutionNodeError(
                "Cannot create DNS record: Hetzner API token not configured"
            )

        try:
            async with httpx.AsyncClient() as client:
                # 1. Find or validate zone
                if not self.zone_id:
                    self.zone_id_actual = await self._find_zone_id(client, self.domain)
                else:
                    self.zone_id_actual = self.zone_id

                if not self.zone_id_actual:
                    raise ExecutionNodeError(
                        f"Could not find DNS zone for domain: {self.domain}"
                    )

                # 2. Create DNS record
                record_id = await self._create_dns_record(client)
                self.created_record_id = record_id

                # 3. Verify record creation (optional)
                record_details = await self._get_record_details(client, record_id)

                # Output data
                output = {
                    "dns_record_id": record_id,
                    "zone_id": self.zone_id_actual,
                    "domain": self.domain,
                    "target_ip": self.target_ip,
                    "record_type": self.record_type,
                    "ttl": self.ttl,
                    "dns_status": "created",
                    "record_details": record_details,
                }

                # Artifacts (none for DNS)
                artifacts = []

                # Emit audit event
                context.emit_audit_event({
                    "event_type": "dns_record_created",
                    "domain": self.domain,
                    "target_ip": self.target_ip,
                    "record_id": record_id,
                    "zone_id": self.zone_id_actual,
                })

                logger.info(
                    f"[{self.node_id}] DNS record created successfully: {record_id}"
                )

                return output, artifacts

        except httpx.HTTPStatusError as e:
            logger.error(f"[{self.node_id}] Hetzner API error: {e.response.status_code} {e.response.text}")
            raise ExecutionNodeError(f"Hetzner API error: {e.response.status_code}")

        except Exception as e:
            logger.error(f"[{self.node_id}] DNS record creation failed: {e}")
            raise ExecutionNodeError(f"DNS record creation failed: {e}")

    async def dry_run(self, context: ExecutionContext) -> tuple[Dict[str, Any], List[str]]:
        """
        Simulate DNS record creation (DRY-RUN mode).

        Args:
            context: Execution context

        Returns:
            Tuple of (simulated_output, simulated_artifacts)
        """
        logger.info(
            f"[{self.node_id}] DRY-RUN: Simulating DNS record creation "
            f"({self.domain} -> {self.target_ip})"
        )

        # Simulated output
        output = {
            "dns_record_id": f"sim_record_{self.domain}",
            "zone_id": self.zone_id or f"sim_zone_{self.domain}",
            "domain": self.domain,
            "target_ip": self.target_ip,
            "record_type": self.record_type,
            "ttl": self.ttl,
            "dns_status": "simulated",
            "record_details": {
                "name": self.domain,
                "value": self.target_ip,
                "type": self.record_type,
                "ttl": self.ttl,
                "simulated": True,
            },
        }

        # Simulated artifacts
        artifacts = []

        logger.info(
            f"[{self.node_id}] DRY-RUN complete: DNS record simulated (no API call made)"
        )

        return output, artifacts

    async def rollback(self, context: ExecutionContext):
        """
        Rollback DNS record creation (delete record).

        Args:
            context: Execution context

        Raises:
            RollbackError: If rollback fails
        """
        if not self.created_record_id:
            logger.warning(f"[{self.node_id}] No DNS record to rollback")
            return

        logger.warning(
            f"[{self.node_id}] Rolling back DNS record: {self.created_record_id}"
        )

        if not self.api_token:
            raise RollbackError("Cannot rollback: Hetzner API token not configured")

        try:
            async with httpx.AsyncClient() as client:
                await self._delete_dns_record(client, self.created_record_id)

            logger.info(f"[{self.node_id}] DNS record deleted: {self.created_record_id}")

            # Emit audit event
            context.emit_audit_event({
                "event_type": "dns_record_deleted",
                "record_id": self.created_record_id,
                "domain": self.domain,
            })

        except Exception as e:
            logger.error(f"[{self.node_id}] DNS rollback failed: {e}")
            raise RollbackError(f"DNS rollback failed: {e}")

    async def _find_zone_id(self, client: httpx.AsyncClient, domain: str) -> Optional[str]:
        """
        Find zone ID for domain.

        Args:
            client: HTTP client
            domain: Domain name

        Returns:
            Zone ID or None if not found
        """
        # Extract root domain (e.g., subdomain.example.com -> example.com)
        parts = domain.split(".")
        if len(parts) >= 2:
            root_domain = ".".join(parts[-2:])
        else:
            root_domain = domain

        # Query Hetzner API for zones
        response = await client.get(
            f"{self.HETZNER_API_BASE}/zones",
            headers={"Auth-API-Token": self.api_token}
        )
        response.raise_for_status()

        zones = response.json().get("zones", [])

        # Find zone matching root domain
        for zone in zones:
            if zone["name"] == root_domain:
                return zone["id"]

        return None

    async def _create_dns_record(self, client: httpx.AsyncClient) -> str:
        """
        Create DNS record via Hetzner API.

        Args:
            client: HTTP client

        Returns:
            Created record ID

        Raises:
            httpx.HTTPStatusError: If API request fails
        """
        payload = {
            "zone_id": self.zone_id_actual,
            "type": self.record_type,
            "name": self.domain,
            "value": self.target_ip,
            "ttl": self.ttl,
        }

        response = await client.post(
            f"{self.HETZNER_API_BASE}/records",
            headers={"Auth-API-Token": self.api_token},
            json=payload,
        )
        response.raise_for_status()

        record_data = response.json().get("record", {})
        return record_data["id"]

    async def _get_record_details(self, client: httpx.AsyncClient, record_id: str) -> Dict[str, Any]:
        """
        Get DNS record details.

        Args:
            client: HTTP client
            record_id: Record ID

        Returns:
            Record details dict
        """
        response = await client.get(
            f"{self.HETZNER_API_BASE}/records/{record_id}",
            headers={"Auth-API-Token": self.api_token}
        )
        response.raise_for_status()

        return response.json().get("record", {})

    async def _delete_dns_record(self, client: httpx.AsyncClient, record_id: str):
        """
        Delete DNS record.

        Args:
            client: HTTP client
            record_id: Record ID to delete

        Raises:
            httpx.HTTPStatusError: If API request fails
        """
        response = await client.delete(
            f"{self.HETZNER_API_BASE}/records/{record_id}",
            headers={"Auth-API-Token": self.api_token}
        )
        response.raise_for_status()
