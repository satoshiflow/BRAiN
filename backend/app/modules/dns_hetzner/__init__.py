"""
Hetzner DNS Module

Automatic DNS record management via Hetzner DNS API (Sprint II).

Security:
- DNS operations are STRICTLY LOCAL trust tier only
- Zone allowlist enforcement (no auto-discovery)
- No secrets in Git (token from ENV)
- Fail-closed policy

Features:
- Automatic DNS record creation (A, AAAA, CNAME)
- Idempotent apply operations
- Zone allowlist enforcement
- Integration with WebGenesis deployment
"""

from .schemas import (
    # Enums
    DNSRecordType,
    DNSRecordStatus,
    # Models
    DNSZone,
    DNSRecord,
    HetznerDNSConfig,
    # Requests
    DNSRecordCreateRequest,
    DNSRecordUpdateRequest,
    DNSRecordApplyRequest,
    # Responses
    DNSApplyResult,
    ZonesListResponse,
    RecordsListResponse,
)

__all__ = [
    # Enums
    "DNSRecordType",
    "DNSRecordStatus",
    # Models
    "DNSZone",
    "DNSRecord",
    "HetznerDNSConfig",
    # Requests
    "DNSRecordCreateRequest",
    "DNSRecordUpdateRequest",
    "DNSRecordApplyRequest",
    # Responses
    "DNSApplyResult",
    "ZonesListResponse",
    "RecordsListResponse",
]
