"""
ARO Audit Logger - Append-Only Audit Trail

Provides immutable audit logging for all repository operations.

Principles:
- Append-only: Entries are NEVER modified or deleted
- Chain verification: Each entry links to previous
- Immutable: AuditLogEntry is frozen (Pydantic)
- Complete trail: Every state change is logged
- Integrity checks: Chain can be verified
"""

from __future__ import annotations

import hashlib
import json
import time
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional
from loguru import logger

from .schemas import (
    AuditLogEntry,
    OperationState,
    RepoOperationType,
)


class AuditLogIntegrityError(Exception):
    """
    Raised when audit log integrity is compromised.

    This is a critical security violation.
    """
    pass


class AuditLogger:
    """
    Append-only audit logger for repository operations.

    Maintains a complete, immutable trail of all operations.
    """

    def __init__(self, storage_path: Optional[str] = None):
        """
        Initialize audit logger.

        Args:
            storage_path: Path to store audit logs (default: storage/aro/audit_logs)
        """
        # Storage path
        if storage_path is None:
            storage_path = "storage/aro/audit_logs"

        self.storage_path = Path(storage_path)
        self.storage_path.mkdir(parents=True, exist_ok=True)

        # In-memory cache (for fast access)
        # In production, this should be a database
        self.entries: Dict[str, AuditLogEntry] = {}
        self.entry_sequence: List[str] = []  # Ordered list of entry IDs

        # Integrity tracking
        self.last_entry_id: Optional[str] = None
        self.entry_count = 0

        # Load existing entries
        self._load_entries()

        logger.info(
            f"📝 Audit Logger initialized (entries={self.entry_count}, "
            f"storage={self.storage_path})"
        )

    def _load_entries(self):
        """Load existing audit log entries from storage"""
        try:
            # Load all .json files in storage
            for entry_file in sorted(self.storage_path.glob("*.json")):
                with open(entry_file, "r") as f:
                    data = json.load(f)
                    entry = AuditLogEntry(**data)

                    self.entries[entry.entry_id] = entry
                    self.entry_sequence.append(entry.entry_id)
                    self.last_entry_id = entry.entry_id
                    self.entry_count += 1

            if self.entry_count > 0:
                logger.info(f"✅ Loaded {self.entry_count} audit log entries")

        except Exception as e:
            logger.error(f"❌ Failed to load audit logs: {e}")
            # Don't raise - start fresh if loading fails

    def _generate_entry_id(self) -> str:
        """
        Generate unique entry ID.

        Format: audit_<timestamp>_<counter>
        """
        timestamp = int(time.time() * 1000)  # Milliseconds
        return f"audit_{timestamp}_{self.entry_count + 1}"

    def _compute_entry_hash(self, entry: AuditLogEntry) -> str:
        """
        Compute hash of entry for integrity verification.

        Args:
            entry: Audit log entry

        Returns:
            SHA256 hash of entry
        """
        # Create deterministic representation
        data = {
            "entry_id": entry.entry_id,
            "operation_id": entry.operation_id,
            "operation_type": entry.operation_type.value,
            "previous_state": entry.previous_state.value if entry.previous_state else None,
            "new_state": entry.new_state.value,
            "agent_id": entry.agent_id,
            "event_type": entry.event_type,
            "message": entry.message,
            "timestamp": entry.timestamp.isoformat(),
            "previous_entry_id": entry.previous_entry_id,
        }

        # Compute hash
        json_str = json.dumps(data, sort_keys=True)
        return hashlib.sha256(json_str.encode()).hexdigest()

    def _persist_entry(self, entry: AuditLogEntry):
        """
        Persist entry to disk (append-only).

        Args:
            entry: Entry to persist
        """
        try:
            # File path: storage/aro/audit_logs/audit_<id>.json
            entry_path = self.storage_path / f"{entry.entry_id}.json"

            # Write to disk (append-only - file should not exist)
            if entry_path.exists():
                raise AuditLogIntegrityError(
                    f"Entry file already exists: {entry_path}. "
                    "This indicates a duplicate entry ID, which is a critical error."
                )

            with open(entry_path, "w") as f:
                json.dump(entry.model_dump(mode="json"), f, indent=2, default=str)

            logger.debug(f"💾 Persisted audit entry: {entry.entry_id}")

        except Exception as e:
            logger.error(f"❌ Failed to persist audit entry: {e}")
            raise

    async def log(
        self,
        operation_id: str,
        operation_type: RepoOperationType,
        agent_id: str,
        event_type: str,
        message: str,
        previous_state: Optional[OperationState] = None,
        new_state: Optional[OperationState] = None,
        details: Optional[Dict] = None,
    ) -> AuditLogEntry:
        """
        Log an event to the audit trail.

        Args:
            operation_id: Operation ID
            operation_type: Type of operation
            agent_id: Agent performing action
            event_type: Type of event (e.g., "state_change", "validation", "error")
            message: Human-readable message
            previous_state: Previous state (if state change)
            new_state: New state (if state change)
            details: Additional details

        Returns:
            Created audit log entry

        Raises:
            AuditLogIntegrityError: If entry creation fails
        """
        # Generate entry ID
        entry_id = self._generate_entry_id()

        # Create entry
        entry = AuditLogEntry(
            entry_id=entry_id,
            operation_id=operation_id,
            operation_type=operation_type,
            previous_state=previous_state,
            new_state=new_state or OperationState.PROPOSED,  # Default
            agent_id=agent_id,
            event_type=event_type,
            message=message,
            details=details or {},
            timestamp=datetime.utcnow(),
            previous_entry_id=self.last_entry_id,
        )

        # Persist to disk (append-only)
        self._persist_entry(entry)

        # Add to in-memory cache
        self.entries[entry_id] = entry
        self.entry_sequence.append(entry_id)
        self.last_entry_id = entry_id
        self.entry_count += 1

        logger.info(
            f"📝 Audit log: {event_type} | op={operation_id} | {message}"
        )

        return entry

    async def log_state_change(
        self,
        operation_id: str,
        operation_type: RepoOperationType,
        agent_id: str,
        previous_state: OperationState,
        new_state: OperationState,
        reason: str = "",
    ) -> AuditLogEntry:
        """
        Log a state change event.

        Args:
            operation_id: Operation ID
            operation_type: Type of operation
            agent_id: Agent performing action
            previous_state: Previous state
            new_state: New state
            reason: Reason for state change

        Returns:
            Created audit log entry
        """
        message = (
            f"State transition: {previous_state.value} → {new_state.value}"
            + (f" ({reason})" if reason else "")
        )

        return await self.log(
            operation_id=operation_id,
            operation_type=operation_type,
            agent_id=agent_id,
            event_type="state_change",
            message=message,
            previous_state=previous_state,
            new_state=new_state,
        )

    async def log_validation(
        self,
        operation_id: str,
        operation_type: RepoOperationType,
        agent_id: str,
        validator_id: str,
        passed: bool,
        issues: List[str],
    ) -> AuditLogEntry:
        """
        Log a validation event.

        Args:
            operation_id: Operation ID
            operation_type: Type of operation
            agent_id: Agent performing action
            validator_id: Validator that ran
            passed: Whether validation passed
            issues: List of validation issues

        Returns:
            Created audit log entry
        """
        message = (
            f"Validation {'passed' if passed else 'failed'}: {validator_id}"
        )

        return await self.log(
            operation_id=operation_id,
            operation_type=operation_type,
            agent_id=agent_id,
            event_type="validation",
            message=message,
            details={
                "validator_id": validator_id,
                "passed": passed,
                "issues": issues,
            },
        )

    async def log_safety_check(
        self,
        operation_id: str,
        operation_type: RepoOperationType,
        agent_id: str,
        checkpoint_id: str,
        safe: bool,
        reason: str,
    ) -> AuditLogEntry:
        """
        Log a safety check event.

        Args:
            operation_id: Operation ID
            operation_type: Type of operation
            agent_id: Agent performing action
            checkpoint_id: Safety checkpoint that ran
            safe: Whether operation is safe
            reason: Reason for decision

        Returns:
            Created audit log entry
        """
        message = (
            f"Safety check {'passed' if safe else 'failed'}: {checkpoint_id}"
        )

        return await self.log(
            operation_id=operation_id,
            operation_type=operation_type,
            agent_id=agent_id,
            event_type="safety_check",
            message=message,
            details={
                "checkpoint_id": checkpoint_id,
                "safe": safe,
                "reason": reason,
            },
        )

    async def log_error(
        self,
        operation_id: str,
        operation_type: RepoOperationType,
        agent_id: str,
        error_message: str,
        error_type: str = "unknown",
    ) -> AuditLogEntry:
        """
        Log an error event.

        Args:
            operation_id: Operation ID
            operation_type: Type of operation
            agent_id: Agent performing action
            error_message: Error message
            error_type: Type of error

        Returns:
            Created audit log entry
        """
        return await self.log(
            operation_id=operation_id,
            operation_type=operation_type,
            agent_id=agent_id,
            event_type="error",
            message=f"Error: {error_message}",
            details={
                "error_type": error_type,
                "error_message": error_message,
            },
        )

    def get_entries_for_operation(
        self,
        operation_id: str
    ) -> List[AuditLogEntry]:
        """
        Get all audit log entries for a specific operation.

        Args:
            operation_id: Operation ID

        Returns:
            List of audit log entries, ordered by timestamp
        """
        entries = [
            e for e in self.entries.values()
            if e.operation_id == operation_id
        ]
        entries.sort(key=lambda e: e.timestamp)
        return entries

    def get_recent_entries(self, limit: int = 100) -> List[AuditLogEntry]:
        """
        Get most recent audit log entries.

        Args:
            limit: Maximum number of entries to return

        Returns:
            List of recent audit log entries
        """
        # Get last N entry IDs
        recent_ids = self.entry_sequence[-limit:]

        # Get entries
        entries = [self.entries[eid] for eid in recent_ids]
        entries.reverse()  # Most recent first
        return entries

    def verify_chain_integrity(self) -> tuple[bool, List[str]]:
        """
        Verify the integrity of the audit log chain.

        Checks:
        1. Each entry links to previous entry
        2. No gaps in the chain
        3. Entry hashes are valid (future enhancement)

        Returns:
            Tuple of (is_valid, list_of_issues)
        """
        issues = []

        if not self.entry_sequence:
            # Empty chain is valid
            return True, []

        # Check chain linkage
        previous_id = None
        for entry_id in self.entry_sequence:
            entry = self.entries[entry_id]

            # Check linkage
            if entry.previous_entry_id != previous_id:
                issues.append(
                    f"Entry {entry_id} has incorrect previous_entry_id: "
                    f"expected {previous_id}, got {entry.previous_entry_id}"
                )

            previous_id = entry_id

        is_valid = len(issues) == 0

        if is_valid:
            logger.info(
                f"✅ Audit log chain integrity verified ({self.entry_count} entries)"
            )
        else:
            logger.error(
                f"❌ Audit log chain integrity check failed: {issues}"
            )

        return is_valid, issues

    def get_statistics(self) -> Dict[str, int]:
        """
        Get audit log statistics.

        Returns:
            Dictionary with statistics
        """
        # Count by event type
        event_counts: Dict[str, int] = {}
        for entry in self.entries.values():
            event_counts[entry.event_type] = event_counts.get(entry.event_type, 0) + 1

        # Count by operation type
        operation_counts: Dict[str, int] = {}
        for entry in self.entries.values():
            op_type = entry.operation_type.value
            operation_counts[op_type] = operation_counts.get(op_type, 0) + 1

        return {
            "total_entries": self.entry_count,
            "event_types": event_counts,
            "operation_types": operation_counts,
        }


# ============================================================================
# Singleton Instance
# ============================================================================

_audit_logger: Optional[AuditLogger] = None


def get_audit_logger() -> AuditLogger:
    """Get the singleton audit logger instance"""
    global _audit_logger
    if _audit_logger is None:
        _audit_logger = AuditLogger()

        # Verify integrity on first use
        is_valid, issues = _audit_logger.verify_chain_integrity()
        if not is_valid:
            logger.warning(
                f"⚠️ Audit log chain integrity issues detected: {issues}"
            )
            # Don't raise - allow operation but log warning

    return _audit_logger
