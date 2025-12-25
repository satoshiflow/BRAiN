"""
Sovereign Mode Schemas

Data models for sovereign mode operation, bundle management,
and validation results.
"""

from enum import Enum
from typing import Dict, List, Optional, Any
from pydantic import BaseModel, Field
from datetime import datetime


class OperationMode(str, Enum):
    """Operation mode states."""

    ONLINE = "online"  # Full internet access, external models allowed
    OFFLINE = "offline"  # No internet, offline bundles only
    SOVEREIGN = "sovereign"  # Strict mode: offline + enhanced validation
    QUARANTINE = "quarantine"  # Isolated mode: all external access blocked


class BundleStatus(str, Enum):
    """Bundle validation and loading status."""

    PENDING = "pending"  # Not yet validated
    VALIDATED = "validated"  # Hash verified, ready to load
    LOADED = "loaded"  # Currently active
    QUARANTINED = "quarantined"  # Failed validation or security check
    FAILED = "failed"  # Load error


class Bundle(BaseModel):
    """Offline model bundle metadata."""

    id: str = Field(..., description="Unique bundle identifier")
    name: str = Field(..., description="Human-readable name")
    version: str = Field(..., description="Semantic version (e.g., 1.0.0)")
    model_type: str = Field(..., description="Model type (e.g., 'llama', 'mistral')")
    model_size: str = Field(..., description="Model size (e.g., '7B', '13B')")
    file_path: str = Field(..., description="Relative path to model file")
    manifest_path: str = Field(..., description="Path to manifest.json")

    # Security
    sha256_hash: str = Field(..., description="SHA256 hash of model file")
    sha256_manifest_hash: str = Field(..., description="SHA256 hash of manifest")

    # G1: Bundle Signing & Trusted Origin
    signature: Optional[str] = Field(None, description="Ed25519 signature (hex, 128 chars)")
    signature_algorithm: str = Field(default="ed25519", description="Signature algorithm")
    signed_by_key_id: Optional[str] = Field(None, description="Key ID that signed this bundle")
    signed_at: Optional[datetime] = Field(None, description="Signature timestamp")

    # Metadata
    description: Optional[str] = Field(None, description="Bundle description")
    capabilities: List[str] = Field(default_factory=list, description="Model capabilities")
    requirements: Dict[str, Any] = Field(default_factory=dict, description="System requirements")

    # Status
    status: BundleStatus = Field(default=BundleStatus.PENDING)
    last_validated: Optional[datetime] = Field(None, description="Last validation timestamp")
    last_loaded: Optional[datetime] = Field(None, description="Last load timestamp")
    load_count: int = Field(default=0, description="Number of times loaded")

    # Quarantine info
    quarantine_reason: Optional[str] = Field(None, description="Reason for quarantine")
    quarantine_timestamp: Optional[datetime] = Field(None, description="Quarantine time")

    class Config:
        json_schema_extra = {
            "example": {
                "id": "llama-3.2-7b-v1.0",
                "name": "Llama 3.2 7B",
                "version": "1.0.0",
                "model_type": "llama",
                "model_size": "7B",
                "file_path": "storage/models/bundles/llama-3.2-7b/model.gguf",
                "manifest_path": "storage/models/bundles/llama-3.2-7b/manifest.json",
                "sha256_hash": "abc123...",
                "sha256_manifest_hash": "def456...",
                "description": "Offline Llama 3.2 7B model",
                "capabilities": ["chat", "completion", "reasoning"],
                "requirements": {"ram_gb": 16, "disk_gb": 8},
                "status": "validated",
            }
        }


class ValidationResult(BaseModel):
    """Result of bundle or operation validation."""

    is_valid: bool = Field(..., description="Validation passed")
    bundle_id: Optional[str] = Field(None, description="Bundle being validated")

    # Hash validation
    hash_match: bool = Field(default=True, description="SHA256 hash matches")
    expected_hash: Optional[str] = Field(None, description="Expected SHA256")
    actual_hash: Optional[str] = Field(None, description="Computed SHA256")

    # File checks
    file_exists: bool = Field(default=True, description="File exists on disk")
    manifest_valid: bool = Field(default=True, description="Manifest is valid JSON")

    # G1: Signature validation
    signature_valid: bool = Field(default=True, description="Ed25519 signature is valid")
    signature_present: bool = Field(default=False, description="Bundle has signature")
    key_trusted: bool = Field(default=False, description="Signing key is trusted")
    key_id: Optional[str] = Field(None, description="Signing key ID")

    # Errors
    errors: List[str] = Field(default_factory=list, description="Validation errors")
    warnings: List[str] = Field(default_factory=list, description="Validation warnings")

    # Metadata
    validated_at: datetime = Field(default_factory=datetime.utcnow)
    validator_version: str = Field(default="1.0.0", description="Validator version")

    class Config:
        json_schema_extra = {
            "example": {
                "is_valid": True,
                "bundle_id": "llama-3.2-7b-v1.0",
                "hash_match": True,
                "expected_hash": "abc123...",
                "actual_hash": "abc123...",
                "file_exists": True,
                "manifest_valid": True,
                "errors": [],
                "warnings": [],
                "validated_at": "2025-12-23T12:00:00Z",
                "validator_version": "1.0.0",
            }
        }


class ModeConfig(BaseModel):
    """Sovereign mode configuration."""

    # Current state
    current_mode: OperationMode = Field(default=OperationMode.ONLINE)
    active_bundle_id: Optional[str] = Field(None, description="Currently loaded bundle")

    # Auto-detection
    auto_detect_network: bool = Field(default=True, description="Auto-switch on network loss")
    network_check_interval: int = Field(default=30, description="Seconds between checks")
    network_check_enabled: bool = Field(default=True, description="Enable network monitoring")

    # Security settings
    strict_validation: bool = Field(default=True, description="Enforce strict hash validation")
    allow_unsigned_bundles: bool = Field(default=False, description="Allow unsigned bundles")
    quarantine_on_failure: bool = Field(default=True, description="Auto-quarantine failed bundles")

    # Network guards
    block_external_http: bool = Field(default=True, description="Block HTTP in offline mode")
    block_external_dns: bool = Field(default=True, description="Block DNS in offline mode")
    allowed_domains: List[str] = Field(default_factory=list, description="Whitelisted domains")

    # Fallback
    fallback_to_offline: bool = Field(default=True, description="Fallback on network loss")
    fallback_bundle_id: Optional[str] = Field(None, description="Default offline bundle")

    # Audit
    audit_mode_changes: bool = Field(default=True, description="Log all mode changes")
    audit_bundle_loads: bool = Field(default=True, description="Log all bundle operations")
    audit_network_blocks: bool = Field(default=True, description="Log blocked requests")

    class Config:
        json_schema_extra = {
            "example": {
                "current_mode": "online",
                "active_bundle_id": None,
                "auto_detect_network": True,
                "network_check_interval": 30,
                "strict_validation": True,
                "allow_unsigned_bundles": False,
                "quarantine_on_failure": True,
                "block_external_http": True,
                "block_external_dns": True,
                "allowed_domains": ["localhost", "127.0.0.1"],
                "fallback_to_offline": True,
                "fallback_bundle_id": "llama-3.2-7b-v1.0",
                "audit_mode_changes": True,
                "audit_bundle_loads": True,
                "audit_network_blocks": True,
            }
        }


class SovereignMode(BaseModel):
    """Sovereign mode status response."""

    mode: OperationMode = Field(..., description="Current operation mode")
    is_online: bool = Field(..., description="Network connectivity detected")
    is_sovereign: bool = Field(..., description="In sovereign mode")

    # Active bundle
    active_bundle: Optional[Bundle] = Field(None, description="Currently loaded bundle")

    # Statistics
    available_bundles: int = Field(default=0, description="Total bundles available")
    validated_bundles: int = Field(default=0, description="Validated bundles")
    quarantined_bundles: int = Field(default=0, description="Quarantined bundles")

    # Network guards
    network_blocks_count: int = Field(default=0, description="Blocked requests count")
    last_network_check: Optional[datetime] = Field(None, description="Last connectivity check")

    # Config
    config: ModeConfig = Field(..., description="Current configuration")

    # Metadata
    system_version: str = Field(default="1.0.0", description="Sovereign mode version")
    last_mode_change: Optional[datetime] = Field(None, description="Last mode switch")

    class Config:
        json_schema_extra = {
            "example": {
                "mode": "sovereign",
                "is_online": False,
                "is_sovereign": True,
                "active_bundle": {
                    "id": "llama-3.2-7b-v1.0",
                    "name": "Llama 3.2 7B",
                    "status": "loaded",
                },
                "available_bundles": 3,
                "validated_bundles": 2,
                "quarantined_bundles": 1,
                "network_blocks_count": 42,
                "last_network_check": "2025-12-23T12:00:00Z",
                "config": {"current_mode": "sovereign"},
                "system_version": "1.0.0",
                "last_mode_change": "2025-12-23T11:00:00Z",
            }
        }


class ModeChangeRequest(BaseModel):
    """Request to change operation mode."""

    target_mode: OperationMode = Field(..., description="Desired mode")
    force: bool = Field(default=False, description="Force mode change")
    reason: Optional[str] = Field(None, description="Reason for change")
    bundle_id: Optional[str] = Field(None, description="Bundle to load (for offline)")

    class Config:
        json_schema_extra = {
            "example": {
                "target_mode": "sovereign",
                "force": False,
                "reason": "Network unavailable",
                "bundle_id": "llama-3.2-7b-v1.0",
            }
        }


class BundleLoadRequest(BaseModel):
    """Request to load a bundle."""

    bundle_id: str = Field(..., description="Bundle ID to load")
    force_revalidate: bool = Field(default=False, description="Revalidate before loading")
    skip_quarantine_check: bool = Field(default=False, description="Skip quarantine check (unsafe)")

    class Config:
        json_schema_extra = {
            "example": {
                "bundle_id": "llama-3.2-7b-v1.0",
                "force_revalidate": True,
                "skip_quarantine_check": False,
            }
        }


class NetworkCheckResult(BaseModel):
    """Result of network connectivity check."""

    is_online: bool = Field(..., description="Network is available")
    latency_ms: Optional[float] = Field(None, description="Ping latency in milliseconds")
    check_method: str = Field(..., description="Method used (dns, http, ping)")
    checked_at: datetime = Field(default_factory=datetime.utcnow)
    error: Optional[str] = Field(None, description="Error if check failed")

    # Host firewall state (Phase 2 integration)
    firewall_state: Optional[Dict[str, Any]] = Field(
        None,
        description="Host firewall enforcement state (iptables)"
    )

    class Config:
        json_schema_extra = {
            "example": {
                "is_online": True,
                "latency_ms": 23.5,
                "check_method": "dns",
                "checked_at": "2025-12-23T12:00:00Z",
                "error": None,
                "firewall_state": {
                    "firewall_enabled": True,
                    "mode": "sovereign",
                    "rules_count": 6,
                    "last_check": "2025-12-24T10:00:00Z",
                    "error": None
                }
            }
        }


class AuditSeverity(str, Enum):
    """Audit event severity levels."""

    INFO = "info"
    WARNING = "warning"
    ERROR = "error"
    CRITICAL = "critical"


class AuditEventType(str, Enum):
    """Sovereign mode audit event types."""

    # Mode changes
    MODE_CHANGED = "sovereign.mode_changed"

    # Gate checks
    GATE_CHECK_PASSED = "sovereign.gate_check_passed"
    GATE_CHECK_FAILED = "sovereign.gate_check_failed"

    # Firewall/Egress
    EGRESS_RULES_APPLIED = "sovereign.egress_rules_applied"
    EGRESS_RULES_REMOVED = "sovereign.egress_rules_removed"
    EGRESS_RULES_FAILED = "sovereign.egress_rules_failed"

    # Network probes
    NETWORK_PROBE_PASSED = "sovereign.network_probe_passed"
    NETWORK_PROBE_FAILED = "sovereign.network_probe_failed"

    # IPv6
    IPV6_GATE_CHECKED = "sovereign.ipv6_gate_checked"

    # Business Factory events (Sprint 5)
    FACTORY_PLAN_GENERATED = "factory.plan_generated"
    FACTORY_EXECUTION_STARTED = "factory.execution_started"
    FACTORY_STEP_STARTED = "factory.step_started"
    FACTORY_STEP_COMPLETED = "factory.step_completed"
    FACTORY_STEP_FAILED = "factory.step_failed"
    FACTORY_EXECUTION_COMPLETED = "factory.execution_completed"
    FACTORY_EXECUTION_FAILED = "factory.execution_failed"
    FACTORY_ROLLBACK_STARTED = "factory.rollback_started"
    FACTORY_ROLLBACK_COMPLETED = "factory.rollback_completed"
    IPV6_GATE_PASSED = "sovereign.ipv6_gate_passed"
    IPV6_GATE_FAILED = "sovereign.ipv6_gate_failed"
    IPV6_GATE_BLOCKED = "sovereign.ipv6_gate_blocked"

    # Connectors/Gateway
    CONNECTOR_BLOCKED = "sovereign.connector_blocked"
    DMZ_STOPPED = "sovereign.dmz_stopped"
    DMZ_STARTED = "sovereign.dmz_started"

    # Bundle operations
    BUNDLE_LOADED = "sovereign.bundle_loaded"
    BUNDLE_LOAD_FAILED = "sovereign.bundle_load_failed"

    # G1: Bundle Signing & Trusted Origin
    BUNDLE_SIGNATURE_VERIFIED = "sovereign.bundle_signature_verified"
    BUNDLE_SIGNATURE_INVALID = "sovereign.bundle_signature_invalid"
    BUNDLE_KEY_UNTRUSTED = "sovereign.bundle_key_untrusted"
    BUNDLE_QUARANTINED = "sovereign.bundle_quarantined"
    BUNDLE_UNSIGNED = "sovereign.bundle_unsigned"

    # AXE Governance (G3)
    AXE_REQUEST_RECEIVED = "axe.request_received"
    AXE_REQUEST_FORWARDED = "axe.request_forwarded"
    AXE_REQUEST_BLOCKED = "axe.request_blocked"
    AXE_TRUST_TIER_VIOLATION = "axe.trust_tier_violation"


class AuditEntry(BaseModel):
    """Audit log entry for sovereign mode operations."""

    id: str = Field(..., description="Unique entry ID")
    timestamp: datetime = Field(default_factory=datetime.utcnow)
    event_type: str = Field(..., description="Event type (mode_change, bundle_load, etc.)")
    severity: AuditSeverity = Field(default=AuditSeverity.INFO, description="Event severity")

    # Event details
    mode_before: Optional[OperationMode] = Field(None)
    mode_after: Optional[OperationMode] = Field(None)
    bundle_id: Optional[str] = Field(None)

    # Context
    reason: Optional[str] = Field(None, description="Reason for event")
    triggered_by: str = Field(default="system", description="Who/what triggered event")

    # Result
    success: bool = Field(..., description="Operation succeeded")
    error: Optional[str] = Field(None, description="Error if failed")

    # Flags
    ipv6_related: bool = Field(default=False, description="Event is IPv6-related")

    # Metadata
    metadata: Dict[str, Any] = Field(default_factory=dict, description="Additional context")

    class Config:
        json_schema_extra = {
            "example": {
                "id": "audit_123",
                "timestamp": "2025-12-23T12:00:00Z",
                "event_type": "mode_change",
                "mode_before": "online",
                "mode_after": "sovereign",
                "bundle_id": "llama-3.2-7b-v1.0",
                "reason": "Network unavailable",
                "triggered_by": "auto_detect",
                "success": True,
                "error": None,
                "metadata": {"network_check_failed": True},
            }
        }
