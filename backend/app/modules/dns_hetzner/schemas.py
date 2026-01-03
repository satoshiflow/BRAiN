"""
Hetzner DNS Module - Data Models

Schemas for Hetzner DNS API integration (Sprint II).

Security: DNS operations are STRICTLY LOCAL trust tier only.
"""

from __future__ import annotations

from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Literal, Optional

from pydantic import BaseModel, Field, validator


# ============================================================================
# Enums
# ============================================================================


class DNSRecordType(str, Enum):
    """DNS record types supported"""

    A = "A"  # IPv4 address
    AAAA = "AAAA"  # IPv6 address
    CNAME = "CNAME"  # Canonical name
    MX = "MX"  # Mail exchange
    TXT = "TXT"  # Text record
    NS = "NS"  # Name server
    SRV = "SRV"  # Service record
    CAA = "CAA"  # Certificate Authority Authorization


class DNSRecordStatus(str, Enum):
    """DNS record status"""

    ACTIVE = "active"
    INACTIVE = "inactive"
    PENDING = "pending"


# ============================================================================
# Main Models
# ============================================================================


class DNSZone(BaseModel):
    """
    DNS Zone (Domain) in Hetzner DNS.

    Represents a managed DNS zone.
    """

    id: str = Field(..., description="Zone ID")
    name: str = Field(..., description="Zone name (e.g., 'example.com')")
    ttl: int = Field(..., description="Default TTL for zone")
    is_secondary_dns: bool = Field(False, description="Whether zone is secondary DNS")
    legacy_dns_host: Optional[str] = Field(None, description="Legacy DNS host")
    legacy_ns: Optional[List[str]] = Field(None, description="Legacy nameservers")
    ns: List[str] = Field(..., description="Nameservers for zone")
    created: Optional[datetime] = Field(None, description="Zone creation timestamp")
    verified: Optional[datetime] = Field(None, description="Zone verification timestamp")
    modified: Optional[datetime] = Field(None, description="Last modification timestamp")
    owner: Optional[str] = Field(None, description="Zone owner")
    paused: bool = Field(False, description="Whether zone is paused")
    permission: Optional[str] = Field(None, description="User permission level")
    project: Optional[str] = Field(None, description="Project ID")
    registrar: Optional[str] = Field(None, description="Domain registrar")
    status: str = Field("verified", description="Zone status")
    txt_verification: Optional[Dict[str, str]] = Field(
        None, description="TXT verification records"
    )

    class Config:
        json_schema_extra = {
            "example": {
                "id": "zone123",
                "name": "example.com",
                "ttl": 86400,
                "is_secondary_dns": False,
                "ns": ["ns1.hetzner.com", "ns2.hetzner.com", "ns3.hetzner.com"],
                "status": "verified",
            }
        }


class DNSRecord(BaseModel):
    """
    DNS Record in Hetzner DNS.

    Represents a single DNS record within a zone.
    """

    id: Optional[str] = Field(None, description="Record ID (assigned by API)")
    zone_id: str = Field(..., description="Zone ID this record belongs to")
    type: DNSRecordType = Field(..., description="Record type")
    name: str = Field(..., description="Record name (@ for root, subdomain, etc.)")
    value: str = Field(..., description="Record value (IP, target, etc.)")
    ttl: int = Field(300, description="TTL in seconds", ge=60, le=86400)
    created: Optional[datetime] = Field(None, description="Record creation timestamp")
    modified: Optional[datetime] = Field(None, description="Last modification timestamp")

    class Config:
        json_schema_extra = {
            "example": {
                "id": "record123",
                "zone_id": "zone123",
                "type": "A",
                "name": "www",
                "value": "1.2.3.4",
                "ttl": 300,
            }
        }


# ============================================================================
# API Request/Response Models
# ============================================================================


class DNSRecordCreateRequest(BaseModel):
    """Request to create a DNS record"""

    zone_id: str = Field(..., description="Zone ID")
    type: DNSRecordType = Field(..., description="Record type")
    name: str = Field(..., description="Record name (@ for root)")
    value: str = Field(..., description="Record value")
    ttl: int = Field(300, description="TTL in seconds", ge=60, le=86400)

    @validator("name")
    def validate_name(cls, v):
        """Validate record name"""
        if not v:
            raise ValueError("Record name cannot be empty")
        # @ is valid for root domain
        if v == "@":
            return v
        # Basic DNS name validation
        import re

        if not re.match(r"^[a-zA-Z0-9]([a-zA-Z0-9-]*[a-zA-Z0-9])?$", v):
            raise ValueError(
                "Record name must contain only alphanumeric characters and hyphens"
            )
        return v

    class Config:
        json_schema_extra = {
            "example": {
                "zone_id": "zone123",
                "type": "A",
                "name": "www",
                "value": "1.2.3.4",
                "ttl": 300,
            }
        }


class DNSRecordUpdateRequest(BaseModel):
    """Request to update a DNS record"""

    record_id: str = Field(..., description="Record ID to update")
    zone_id: str = Field(..., description="Zone ID")
    type: Optional[DNSRecordType] = Field(None, description="Record type")
    name: Optional[str] = Field(None, description="Record name")
    value: Optional[str] = Field(None, description="Record value")
    ttl: Optional[int] = Field(None, description="TTL in seconds", ge=60, le=86400)

    class Config:
        json_schema_extra = {
            "example": {
                "record_id": "record123",
                "zone_id": "zone123",
                "value": "2.3.4.5",
                "ttl": 600,
            }
        }


class DNSRecordApplyRequest(BaseModel):
    """
    Request to apply (upsert) a DNS record.

    Idempotent operation: creates if doesn't exist, updates if exists.
    """

    zone: str = Field(..., description="Zone name (e.g., 'example.com')")
    record_type: DNSRecordType = Field(..., description="Record type")
    name: str = Field(..., description="Record name (@ for root, www, subdomain, etc.)")
    value: str = Field(..., description="Record value (IP, target, etc.)")
    ttl: int = Field(300, description="TTL in seconds", ge=60, le=86400)

    class Config:
        json_schema_extra = {
            "example": {
                "zone": "example.com",
                "record_type": "A",
                "name": "www",
                "value": "1.2.3.4",
                "ttl": 300,
            }
        }


class DNSApplyResult(BaseModel):
    """Result of DNS record apply operation"""

    success: bool = Field(..., description="Operation success")
    zone: str = Field(..., description="Zone name")
    record_type: str = Field(..., description="Record type")
    name: str = Field(..., description="Record name")
    value: str = Field(..., description="Record value")
    ttl: int = Field(..., description="TTL")
    action: Literal["created", "updated", "no_change"] = Field(
        ..., description="Action taken"
    )
    record_id: Optional[str] = Field(None, description="Record ID")
    message: str = Field(..., description="Status message")
    errors: List[str] = Field(default_factory=list, description="Errors if any")
    warnings: List[str] = Field(default_factory=list, description="Warnings if any")

    class Config:
        json_schema_extra = {
            "example": {
                "success": True,
                "zone": "example.com",
                "record_type": "A",
                "name": "www",
                "value": "1.2.3.4",
                "ttl": 300,
                "action": "created",
                "record_id": "record123",
                "message": "DNS record created successfully",
                "errors": [],
                "warnings": [],
            }
        }


class ZonesListResponse(BaseModel):
    """Response for listing DNS zones"""

    zones: List[DNSZone] = Field(..., description="List of zones")
    total_count: int = Field(..., description="Total number of zones")
    allowed_zones: List[str] = Field(
        ..., description="Zones allowed by allowlist policy"
    )

    class Config:
        json_schema_extra = {
            "example": {
                "zones": [],
                "total_count": 3,
                "allowed_zones": ["example.com", "test.example.com"],
            }
        }


class RecordsListResponse(BaseModel):
    """Response for listing DNS records"""

    zone_id: str = Field(..., description="Zone ID")
    zone_name: str = Field(..., description="Zone name")
    records: List[DNSRecord] = Field(..., description="List of records")
    total_count: int = Field(..., description="Total number of records")

    class Config:
        json_schema_extra = {
            "example": {
                "zone_id": "zone123",
                "zone_name": "example.com",
                "records": [],
                "total_count": 5,
            }
        }


# ============================================================================
# Configuration Models
# ============================================================================


class HetznerDNSConfig(BaseModel):
    """Hetzner DNS configuration (from environment)"""

    api_token: str = Field(..., description="Hetzner DNS API token")
    api_base_url: str = Field(
        "https://dns.hetzner.com/api/v1", description="API base URL"
    )
    allowed_zones: List[str] = Field(
        ..., description="Allowed zones (comma-separated from ENV)"
    )
    default_ttl: int = Field(300, description="Default TTL in seconds", ge=60, le=86400)
    public_ipv4: Optional[str] = Field(None, description="Public IPv4 address")
    public_ipv6: Optional[str] = Field(None, description="Public IPv6 address")
    timeout: int = Field(30, description="API request timeout in seconds")

    class Config:
        json_schema_extra = {
            "example": {
                "api_token": "your_token_here",
                "api_base_url": "https://dns.hetzner.com/api/v1",
                "allowed_zones": ["example.com", "test.example.com"],
                "default_ttl": 300,
                "public_ipv4": "1.2.3.4",
                "timeout": 30,
            }
        }
