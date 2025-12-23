"""
Physical Gateway Audit Trail

Append-only audit logging for all gateway operations.

Features:
- Immutable event log
- Command tracking
- Security events
- Compliance reporting
- Tamper detection
"""

from __future__ import annotations

import json
import hashlib
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional
from loguru import logger

from .schemas import AuditEvent, AuditQuery


# ============================================================================
# Audit Trail Manager
# ============================================================================


class AuditTrailManager:
    """
    Manages append-only audit trail for gateway operations.

    Features:
    - Immutable event logging
    - Chain-of-custody tracking
    - Tamper detection via hashing
    - Compliance reporting
    """

    def __init__(
        self,
        storage_path: str = "storage/audit/physical_gateway_audit.jsonl",
    ):
        """
        Initialize audit trail manager.

        Args:
            storage_path: Path to audit log file (JSONL format)
        """
        self.storage_path = Path(storage_path)
        self.storage_path.parent.mkdir(parents=True, exist_ok=True)

        # In-memory cache for recent events
        self.recent_events: List[AuditEvent] = []
        self.max_cache_size = 1000

        # Event counters
        self.total_events = 0
        self.events_by_type: Dict[str, int] = {}

        # Last event hash for chain verification
        self.last_event_hash: Optional[str] = None

        # Load existing events
        self._load_existing_events()

        logger.info(f"Audit Trail Manager initialized (storage: {storage_path})")

    # ========================================================================
    # Event Logging
    # ========================================================================

    def log_event(
        self,
        event_type: str,
        action: str,
        status: str,
        agent_id: Optional[str] = None,
        command_id: Optional[str] = None,
        user_id: Optional[str] = None,
        details: Optional[Dict[str, Any]] = None,
        source_ip: Optional[str] = None,
        user_agent: Optional[str] = None,
    ) -> AuditEvent:
        """
        Log an audit event.

        Args:
            event_type: Type of event (command, auth, security, etc.)
            action: Action performed
            status: Event status (success, failure, etc.)
            agent_id: Associated agent ID
            command_id: Associated command ID
            user_id: User who triggered event
            details: Additional event details
            source_ip: Source IP address
            user_agent: User agent string

        Returns:
            Created audit event
        """
        # Generate event ID
        event_id = self._generate_event_id()

        # Create event
        event = AuditEvent(
            event_id=event_id,
            event_type=event_type,
            action=action,
            status=status,
            agent_id=agent_id,
            command_id=command_id,
            user_id=user_id,
            details=details or {},
            source_ip=source_ip,
            user_agent=user_agent,
            timestamp=datetime.utcnow(),
        )

        # Append to storage
        self._append_event(event)

        # Update cache
        self.recent_events.append(event)
        if len(self.recent_events) > self.max_cache_size:
            self.recent_events.pop(0)

        # Update counters
        self.total_events += 1
        self.events_by_type[event_type] = self.events_by_type.get(event_type, 0) + 1

        logger.debug(f"Audit event logged: {event_id} ({event_type}: {action})")

        return event

    def _append_event(self, event: AuditEvent):
        """
        Append event to storage file.

        Args:
            event: Event to append
        """
        # Compute event hash including previous hash (chain)
        event_hash = self._compute_event_hash(event, self.last_event_hash)
        self.last_event_hash = event_hash

        # Add hash to details
        event_dict = event.model_dump()
        event_dict["_hash"] = event_hash
        event_dict["_prev_hash"] = self.last_event_hash

        # Append to file
        try:
            with open(self.storage_path, "a") as f:
                f.write(json.dumps(event_dict) + "\n")
        except Exception as e:
            logger.error(f"Failed to append audit event: {e}")

    def _compute_event_hash(
        self,
        event: AuditEvent,
        prev_hash: Optional[str] = None,
    ) -> str:
        """
        Compute hash for event including previous hash.

        Args:
            event: Event to hash
            prev_hash: Previous event hash

        Returns:
            SHA-256 hash of event
        """
        event_dict = event.model_dump()
        event_dict["_prev_hash"] = prev_hash or "genesis"

        event_json = json.dumps(event_dict, sort_keys=True, default=str)
        return hashlib.sha256(event_json.encode("utf-8")).hexdigest()

    def _generate_event_id(self) -> str:
        """
        Generate unique event ID.

        Returns:
            Event ID (timestamp-based)
        """
        timestamp = datetime.utcnow().isoformat()
        counter = self.total_events
        return f"EVT-{timestamp}-{counter:06d}"

    # ========================================================================
    # Specialized Event Loggers
    # ========================================================================

    def log_command_event(
        self,
        command_id: str,
        agent_id: str,
        action: str,
        status: str,
        details: Optional[Dict[str, Any]] = None,
    ) -> AuditEvent:
        """Log command-related event."""
        return self.log_event(
            event_type="command",
            action=action,
            status=status,
            agent_id=agent_id,
            command_id=command_id,
            details=details,
        )

    def log_auth_event(
        self,
        agent_id: str,
        action: str,
        status: str,
        source_ip: Optional[str] = None,
        details: Optional[Dict[str, Any]] = None,
    ) -> AuditEvent:
        """Log authentication event."""
        return self.log_event(
            event_type="authentication",
            action=action,
            status=status,
            agent_id=agent_id,
            source_ip=source_ip,
            details=details,
        )

    def log_security_event(
        self,
        action: str,
        status: str,
        agent_id: Optional[str] = None,
        details: Optional[Dict[str, Any]] = None,
    ) -> AuditEvent:
        """Log security-related event."""
        return self.log_event(
            event_type="security",
            action=action,
            status=status,
            agent_id=agent_id,
            details=details,
        )

    def log_agent_event(
        self,
        agent_id: str,
        action: str,
        status: str,
        details: Optional[Dict[str, Any]] = None,
    ) -> AuditEvent:
        """Log agent lifecycle event."""
        return self.log_event(
            event_type="agent",
            action=action,
            status=status,
            agent_id=agent_id,
            details=details,
        )

    # ========================================================================
    # Query Interface
    # ========================================================================

    def query_events(self, query: AuditQuery) -> List[AuditEvent]:
        """
        Query audit events.

        Args:
            query: Query parameters

        Returns:
            List of matching audit events
        """
        results: List[AuditEvent] = []

        # Read from file for comprehensive results
        try:
            with open(self.storage_path, "r") as f:
                for line in f:
                    try:
                        event_dict = json.loads(line)

                        # Remove internal fields
                        event_dict.pop("_hash", None)
                        event_dict.pop("_prev_hash", None)

                        event = AuditEvent(**event_dict)

                        # Apply filters
                        if query.agent_id and event.agent_id != query.agent_id:
                            continue

                        if query.command_id and event.command_id != query.command_id:
                            continue

                        if query.event_type and event.event_type != query.event_type:
                            continue

                        if query.start_time and event.timestamp < query.start_time:
                            continue

                        if query.end_time and event.timestamp > query.end_time:
                            continue

                        results.append(event)

                        # Limit results
                        if len(results) >= query.limit:
                            break

                    except Exception as e:
                        logger.warning(f"Failed to parse audit event: {e}")
                        continue

        except FileNotFoundError:
            logger.warning("Audit log file not found")

        return results

    def get_recent_events(self, limit: int = 100) -> List[AuditEvent]:
        """
        Get recent events from cache.

        Args:
            limit: Maximum number of events to return

        Returns:
            Recent audit events
        """
        return self.recent_events[-limit:]

    # ========================================================================
    # Statistics
    # ========================================================================

    def get_statistics(self) -> Dict[str, Any]:
        """
        Get audit trail statistics.

        Returns:
            Statistics dictionary
        """
        return {
            "total_events": self.total_events,
            "events_by_type": self.events_by_type,
            "storage_path": str(self.storage_path),
            "storage_size_bytes": (
                self.storage_path.stat().st_size
                if self.storage_path.exists()
                else 0
            ),
            "cached_events": len(self.recent_events),
        }

    # ========================================================================
    # Integrity Verification
    # ========================================================================

    def verify_integrity(self) -> tuple[bool, List[str]]:
        """
        Verify audit trail integrity by checking hash chain.

        Returns:
            (is_valid, list_of_errors)
        """
        errors: List[str] = []

        if not self.storage_path.exists():
            return True, []  # Empty trail is valid

        try:
            prev_hash = None
            line_number = 0

            with open(self.storage_path, "r") as f:
                for line in f:
                    line_number += 1

                    try:
                        event_dict = json.loads(line)

                        # Extract stored hashes
                        stored_hash = event_dict.pop("_hash", None)
                        stored_prev_hash = event_dict.pop("_prev_hash", None)

                        # Verify previous hash matches
                        if stored_prev_hash != prev_hash:
                            if not (prev_hash is None and stored_prev_hash == "genesis"):
                                errors.append(
                                    f"Line {line_number}: Previous hash mismatch"
                                )

                        # Recompute hash
                        event = AuditEvent(**event_dict)
                        computed_hash = self._compute_event_hash(event, prev_hash)

                        # Verify hash
                        if stored_hash != computed_hash:
                            errors.append(f"Line {line_number}: Hash verification failed")

                        # Update for next iteration
                        prev_hash = stored_hash

                    except Exception as e:
                        errors.append(f"Line {line_number}: Parse error - {e}")

        except Exception as e:
            errors.append(f"Failed to read audit file: {e}")

        is_valid = len(errors) == 0

        if is_valid:
            logger.info("✅ Audit trail integrity verified")
        else:
            logger.error(f"❌ Audit trail integrity check failed: {len(errors)} errors")

        return is_valid, errors

    # ========================================================================
    # Initialization
    # ========================================================================

    def _load_existing_events(self):
        """Load existing events to initialize state."""
        if not self.storage_path.exists():
            return

        try:
            with open(self.storage_path, "r") as f:
                for line in f:
                    try:
                        event_dict = json.loads(line)

                        # Update counter
                        self.total_events += 1

                        # Update event type counter
                        event_type = event_dict.get("event_type", "unknown")
                        self.events_by_type[event_type] = (
                            self.events_by_type.get(event_type, 0) + 1
                        )

                        # Update last hash
                        self.last_event_hash = event_dict.get("_hash")

                        # Add to cache if recent
                        event_dict.pop("_hash", None)
                        event_dict.pop("_prev_hash", None)
                        event = AuditEvent(**event_dict)

                        if len(self.recent_events) < self.max_cache_size:
                            self.recent_events.append(event)

                    except Exception:
                        # Skip malformed events
                        continue

            logger.info(f"Loaded {self.total_events} existing audit events")

        except Exception as e:
            logger.error(f"Failed to load existing events: {e}")


# ============================================================================
# Singleton
# ============================================================================

_audit_manager: Optional[AuditTrailManager] = None


def get_audit_manager() -> AuditTrailManager:
    """Get singleton AuditTrailManager instance."""
    global _audit_manager
    if _audit_manager is None:
        _audit_manager = AuditTrailManager()
    return _audit_manager
