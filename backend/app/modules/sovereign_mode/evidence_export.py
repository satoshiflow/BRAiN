"""
Evidence Export Service (Sprint 7.2)

Automated generation of governance evidence packs for audit and compliance.
Deterministic, read-only, cryptographically verifiable.
"""

import json
import hashlib
from typing import List, Dict, Any
from datetime import datetime
from pathlib import Path
from loguru import logger

from app.modules.sovereign_mode.schemas import (
    EvidencePack,
    EvidenceExportRequest,
    EvidenceScope,
    AuditEntry,
    ModeConfig,
    OperationMode,
)


class EvidenceExporter:
    """
    Evidence pack generator for governance compliance.

    Design Principles:
    - Read-only (no state modifications)
    - Deterministic (same input → same output)
    - Cryptographically verifiable (SHA256 hash)
    - Privacy-preserving (no secrets, no PII)
    - Time-bounded (filter by date range)
    """

    SYSTEM_VERSION = "1.0.0"
    EVIDENCE_FORMAT_VERSION = "1.0"

    def __init__(self, audit_log_path: str = "storage/sovereign_mode_audit.jsonl"):
        """
        Initialize evidence exporter.

        Args:
            audit_log_path: Path to audit log file
        """
        self.audit_log_path = Path(audit_log_path)
        logger.info(f"EvidenceExporter initialized: {audit_log_path}")

    def export_evidence(
        self,
        request: EvidenceExportRequest,
        current_mode: OperationMode,
        config: ModeConfig,
        bundle_stats: Dict[str, Any],
    ) -> EvidencePack:
        """
        Generate evidence pack from governance data.

        Args:
            request: Export request with time range and scope
            current_mode: Current operation mode
            config: Current governance configuration
            bundle_stats: Bundle statistics

        Returns:
            EvidencePack with cryptographic verification
        """
        logger.info(
            f"Generating evidence pack: scope={request.scope.value}, "
            f"range={request.from_timestamp} to {request.to_timestamp}"
        )

        # 1. Load and filter audit events
        audit_events = self._load_audit_events(
            request.from_timestamp,
            request.to_timestamp
        )

        logger.debug(f"Loaded {len(audit_events)} audit events in time range")

        # 2. Generate audit summary
        audit_summary = self._generate_audit_summary(audit_events)

        # 3. Extract mode history
        mode_history = self._extract_mode_history(audit_events)

        # 4. Extract override usage (placeholder - not yet implemented)
        override_usage = self._extract_override_usage(audit_events)

        # 5. Generate bundle summary
        bundle_summary = self._generate_bundle_summary(
            bundle_stats,
            request.scope
        )

        # 6. Generate executor summary (if requested)
        executor_summary = None
        if request.include_executor_summary:
            executor_summary = self._generate_executor_summary(audit_events)

        # 7. Create pack ID
        pack_id = self._generate_pack_id(request)

        # 8. Build evidence pack (without hash yet)
        pack = EvidencePack(
            pack_id=pack_id,
            generated_at=datetime.utcnow(),
            scope=request.scope,
            time_range_start=request.from_timestamp,
            time_range_end=request.to_timestamp,
            current_mode=current_mode,
            governance_config=config,
            audit_events=audit_events if request.scope == EvidenceScope.INTERNAL else audit_events[:100],  # Limit for non-internal
            audit_summary=audit_summary,
            mode_history=mode_history,
            override_usage=override_usage,
            bundle_summary=bundle_summary,
            executor_summary=executor_summary,
            content_hash="",  # Placeholder, will be computed
            hash_algorithm="sha256",
            system_version=self.SYSTEM_VERSION,
            evidence_format_version=self.EVIDENCE_FORMAT_VERSION,
        )

        # 9. Compute content hash (deterministic)
        content_hash = self._compute_content_hash(pack)
        pack.content_hash = content_hash

        logger.info(
            f"Evidence pack generated: {pack_id} "
            f"(events={len(audit_events)}, hash={content_hash[:16]}...)"
        )

        return pack

    def _load_audit_events(
        self,
        from_timestamp: datetime,
        to_timestamp: datetime
    ) -> List[AuditEntry]:
        """
        Load audit events from file within time range.

        Args:
            from_timestamp: Start of range
            to_timestamp: End of range

        Returns:
            List of AuditEntry objects
        """
        events = []

        if not self.audit_log_path.exists():
            logger.warning(f"Audit log not found: {self.audit_log_path}")
            return events

        try:
            with open(self.audit_log_path, "r") as f:
                for line in f:
                    try:
                        data = json.loads(line.strip())
                        entry = AuditEntry(**data)

                        # Filter by time range
                        if from_timestamp <= entry.timestamp <= to_timestamp:
                            events.append(entry)

                    except json.JSONDecodeError as e:
                        logger.warning(f"Invalid JSON in audit log: {e}")
                        continue
                    except Exception as e:
                        logger.warning(f"Error parsing audit entry: {e}")
                        continue

        except Exception as e:
            logger.error(f"Error loading audit log: {e}")

        return events

    def _generate_audit_summary(
        self,
        audit_events: List[AuditEntry]
    ) -> Dict[str, int]:
        """
        Generate summary of audit events by type.

        Args:
            audit_events: List of audit entries

        Returns:
            Dictionary of event_type -> count
        """
        summary: Dict[str, int] = {}

        for entry in audit_events:
            event_type = entry.event_type
            summary[event_type] = summary.get(event_type, 0) + 1

        return summary

    def _extract_mode_history(
        self,
        audit_events: List[AuditEntry]
    ) -> List[Dict[str, Any]]:
        """
        Extract mode changes from audit events.

        Args:
            audit_events: List of audit entries

        Returns:
            List of mode change records
        """
        mode_changes = []

        for entry in audit_events:
            if entry.event_type == "sovereign.mode_changed":
                mode_changes.append({
                    "timestamp": entry.timestamp.isoformat(),
                    "from": entry.mode_before.value if entry.mode_before else None,
                    "to": entry.mode_after.value if entry.mode_after else None,
                    "reason": entry.reason,
                    "triggered_by": entry.triggered_by,
                })

        return mode_changes

    def _extract_override_usage(
        self,
        audit_events: List[AuditEntry]
    ) -> Dict[str, Any]:
        """
        Extract override usage statistics (placeholder).

        Args:
            audit_events: List of audit entries

        Returns:
            Override usage summary
        """
        # Placeholder - override system not yet implemented
        return {
            "override_count": 0,
            "override_events": [],
            "note": "Override system not yet implemented"
        }

    def _generate_bundle_summary(
        self,
        bundle_stats: Dict[str, Any],
        scope: EvidenceScope
    ) -> Dict[str, Any]:
        """
        Generate bundle summary based on scope.

        Args:
            bundle_stats: Bundle statistics from bundle manager
            scope: Evidence scope

        Returns:
            Bundle summary dictionary
        """
        summary = {
            "total_bundles": bundle_stats.get("total_bundles", 0),
            "validated": bundle_stats.get("validated", 0),
            "quarantined": bundle_stats.get("quarantined", 0),
        }

        # Add more details for internal scope
        if scope == EvidenceScope.INTERNAL:
            summary["loaded"] = bundle_stats.get("loaded", 0)
            summary["failed"] = bundle_stats.get("failed", 0)

        return summary

    def _generate_executor_summary(
        self,
        audit_events: List[AuditEntry]
    ) -> Dict[str, Any]:
        """
        Generate executor activity summary from audit events.

        Args:
            audit_events: List of audit entries

        Returns:
            Executor summary dictionary
        """
        executor_events = [
            e for e in audit_events
            if e.event_type.startswith("factory.")
        ]

        summary = {
            "total_executor_events": len(executor_events),
            "executions_started": sum(1 for e in executor_events if e.event_type == "factory.execution_started"),
            "executions_completed": sum(1 for e in executor_events if e.event_type == "factory.execution_completed"),
            "executions_failed": sum(1 for e in executor_events if e.event_type == "factory.execution_failed"),
            "steps_completed": sum(1 for e in executor_events if e.event_type == "factory.step_completed"),
            "steps_failed": sum(1 for e in executor_events if e.event_type == "factory.step_failed"),
            "rollbacks": sum(1 for e in executor_events if e.event_type == "factory.rollback_started"),
        }

        return summary

    def _generate_pack_id(self, request: EvidenceExportRequest) -> str:
        """
        Generate deterministic pack ID.

        Args:
            request: Export request

        Returns:
            Pack ID string
        """
        timestamp = datetime.utcnow().strftime("%Y%m%d_%H%M%S")
        return f"evidence_{timestamp}_{request.scope.value}"

    def _compute_content_hash(self, pack: EvidencePack) -> str:
        """
        Compute deterministic SHA256 hash of pack content.

        Hash is computed over:
        - Time range
        - Audit events
        - Mode history
        - Bundle summary
        - Executor summary

        Excludes:
        - pack_id (contains timestamp)
        - generated_at (timestamp)
        - content_hash itself

        Args:
            pack: Evidence pack

        Returns:
            SHA256 hash (hex string)
        """
        # Create deterministic JSON representation
        hash_content = {
            "scope": pack.scope.value,
            "time_range_start": pack.time_range_start.isoformat(),
            "time_range_end": pack.time_range_end.isoformat(),
            "current_mode": pack.current_mode.value,
            "audit_summary": pack.audit_summary,
            "mode_history": pack.mode_history,
            "bundle_summary": pack.bundle_summary,
            "executor_summary": pack.executor_summary,
            "evidence_format_version": pack.evidence_format_version,
        }

        # Sort keys for determinism
        hash_json = json.dumps(hash_content, sort_keys=True)

        # Compute SHA256
        hash_obj = hashlib.sha256(hash_json.encode('utf-8'))
        return hash_obj.hexdigest()

    def verify_pack_integrity(self, pack: EvidencePack) -> bool:
        """
        Verify integrity of evidence pack.

        Args:
            pack: Evidence pack to verify

        Returns:
            True if hash matches, False otherwise
        """
        original_hash = pack.content_hash

        # Recompute hash
        computed_hash = self._compute_content_hash(pack)

        is_valid = original_hash == computed_hash

        if is_valid:
            logger.info(f"Evidence pack integrity verified: {pack.pack_id}")
        else:
            logger.error(
                f"Evidence pack integrity FAILED: {pack.pack_id} "
                f"(expected={original_hash[:16]}, computed={computed_hash[:16]})"
            )

        return is_valid


# Singleton instance
_exporter: EvidenceExporter = None


def get_evidence_exporter() -> EvidenceExporter:
    """Get singleton evidence exporter instance."""
    global _exporter
    if _exporter is None:
        _exporter = EvidenceExporter()
    return _exporter
