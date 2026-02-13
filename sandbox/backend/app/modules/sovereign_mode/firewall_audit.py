"""
Firewall Audit Logging

Log all firewall rule changes to dedicated audit log.
"""

import json
import time
from pathlib import Path
from typing import Optional, List, Dict, Any
from loguru import logger
from pydantic import BaseModel
from datetime import datetime
from enum import Enum


class FirewallOperation(str, Enum):
    """Firewall operations."""

    RULE_ADDED = "rule_added"
    RULE_REMOVED = "rule_removed"
    RULES_FLUSHED = "rules_flushed"
    MODE_CHANGED = "mode_changed"
    SCRIPT_EXECUTED = "script_executed"


class FirewallAuditEntry(BaseModel):
    """Single firewall audit log entry."""

    timestamp: datetime
    operation: FirewallOperation
    script: str  # sovereign-fw.sh or dmz-fw.sh
    mode: Optional[str] = None  # sovereign, connected, dmz_isolation
    rule_type: Optional[str] = None  # ipv4, ipv6, dmz
    rules_count: int = 0
    success: bool
    error: Optional[str] = None
    metadata: Dict[str, Any] = {}


class FirewallAuditLog:
    """
    Firewall audit logger.

    Logs all firewall rule changes to:
    - storage/firewall_audit.jsonl (JSONL format)
    """

    def __init__(self, log_path: str = "storage/firewall_audit.jsonl"):
        self.log_path = Path(log_path)
        self.log_path.parent.mkdir(parents=True, exist_ok=True)

    async def log(
        self,
        operation: FirewallOperation,
        script: str,
        mode: Optional[str] = None,
        rule_type: Optional[str] = None,
        rules_count: int = 0,
        success: bool = True,
        error: Optional[str] = None,
        **metadata,
    ) -> FirewallAuditEntry:
        """
        Log a firewall operation.

        Args:
            operation: Type of firewall operation
            script: Which script executed the operation
            mode: Firewall mode (sovereign, connected, dmz_isolation)
            rule_type: Type of rules (ipv4, ipv6, dmz)
            rules_count: Number of rules affected
            success: Whether operation succeeded
            error: Error message if operation failed
            **metadata: Additional metadata

        Returns:
            FirewallAuditEntry: The logged entry
        """
        entry = FirewallAuditEntry(
            timestamp=datetime.utcnow(),
            operation=operation,
            script=script,
            mode=mode,
            rule_type=rule_type,
            rules_count=rules_count,
            success=success,
            error=error,
            metadata=metadata,
        )

        # Write to JSONL file
        try:
            with open(self.log_path, "a") as f:
                f.write(entry.model_dump_json() + "\n")

            logger.info(
                f"Firewall audit: {operation.value} | script={script} | mode={mode} | rules={rules_count} | success={success}"
            )

        except Exception as e:
            logger.error(f"Failed to write firewall audit log: {e}")

        return entry

    async def get_recent_entries(
        self, limit: int = 100, operation: Optional[FirewallOperation] = None
    ) -> List[FirewallAuditEntry]:
        """
        Get recent firewall audit entries.

        Args:
            limit: Maximum number of entries to return
            operation: Filter by operation type (optional)

        Returns:
            List of recent audit entries
        """
        if not self.log_path.exists():
            return []

        entries = []

        try:
            with open(self.log_path, "r") as f:
                # Read all lines
                lines = f.readlines()

                # Get last N lines
                for line in reversed(lines[-limit:]):
                    if not line.strip():
                        continue

                    try:
                        data = json.loads(line)
                        entry = FirewallAuditEntry(**data)

                        # Filter by operation if specified
                        if operation is None or entry.operation == operation:
                            entries.append(entry)

                    except Exception as e:
                        logger.warning(f"Failed to parse audit entry: {e}")

        except Exception as e:
            logger.error(f"Failed to read firewall audit log: {e}")

        return entries

    async def get_stats(self) -> Dict[str, Any]:
        """
        Get firewall audit statistics.

        Returns:
            Statistics about firewall operations
        """
        if not self.log_path.exists():
            return {
                "total_entries": 0,
                "by_operation": {},
                "by_script": {},
                "by_mode": {},
                "success_rate": 0.0,
            }

        total = 0
        by_operation = {}
        by_script = {}
        by_mode = {}
        successes = 0

        try:
            with open(self.log_path, "r") as f:
                for line in f:
                    if not line.strip():
                        continue

                    try:
                        data = json.loads(line)
                        total += 1

                        # Count by operation
                        op = data.get("operation", "unknown")
                        by_operation[op] = by_operation.get(op, 0) + 1

                        # Count by script
                        script = data.get("script", "unknown")
                        by_script[script] = by_script.get(script, 0) + 1

                        # Count by mode
                        mode = data.get("mode")
                        if mode:
                            by_mode[mode] = by_mode.get(mode, 0) + 1

                        # Count successes
                        if data.get("success", False):
                            successes += 1

                    except Exception:
                        pass

        except Exception as e:
            logger.error(f"Failed to read firewall audit log: {e}")

        success_rate = (successes / total * 100.0) if total > 0 else 0.0

        return {
            "total_entries": total,
            "by_operation": by_operation,
            "by_script": by_script,
            "by_mode": by_mode,
            "success_rate": success_rate,
        }


# Singleton
_audit_log: Optional[FirewallAuditLog] = None


def get_firewall_audit_log() -> FirewallAuditLog:
    """Get singleton firewall audit log."""
    global _audit_log
    if _audit_log is None:
        _audit_log = FirewallAuditLog()
    return _audit_log
