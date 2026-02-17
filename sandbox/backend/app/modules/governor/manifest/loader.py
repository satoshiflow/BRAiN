"""
Governor Manifest Loader (Phase 2).

Loads manifests from JSON files/dictionaries.

Features:
- JSON schema validation
- Hash computation
- Rule priority validation
- Default manifest templates
"""

from __future__ import annotations
from typing import Optional, Dict, Any
import json
from pathlib import Path
from loguru import logger

from app.modules.governor.manifest.schemas import (
    GovernorManifest,
    ManifestRule,
    Budget,
    RiskClass,
    RuleCondition,
)
from app.modules.neurorail.errors import ManifestInvalidSchemaError


class ManifestLoader:
    """
    Loads and validates manifests from JSON.

    Supports:
    - JSON file loading
    - Dict loading
    - Schema validation
    - Default templates
    """

    # ========================================================================
    # Loading
    # ========================================================================

    @staticmethod
    def from_file(file_path: str) -> GovernorManifest:
        """
        Load manifest from JSON file.

        Args:
            file_path: Path to JSON file

        Returns:
            Loaded manifest

        Raises:
            ManifestInvalidSchemaError: If validation fails
            FileNotFoundError: If file not found
        """
        logger.info(f"Loading manifest from file: {file_path}")

        path = Path(file_path)
        if not path.exists():
            raise FileNotFoundError(f"Manifest file not found: {file_path}")

        with open(path) as f:
            data = json.load(f)

        return ManifestLoader.from_dict(data)

    @staticmethod
    def from_dict(data: Dict[str, Any]) -> GovernorManifest:
        """
        Load manifest from dictionary.

        Args:
            data: Manifest data

        Returns:
            Loaded manifest

        Raises:
            ManifestInvalidSchemaError: If validation fails
        """
        try:
            # Parse rules
            rules_data = data.get("rules", [])
            rules = []
            for rule_data in rules_data:
                # Parse condition
                when_data = rule_data.get("when", {})
                when = RuleCondition(**when_data)

                # Parse rule
                rule = ManifestRule(
                    rule_id=rule_data["rule_id"],
                    priority=rule_data["priority"],
                    description=rule_data["description"],
                    when=when,
                    then=rule_data.get("then", {}),
                    mode=rule_data.get("mode", "RAIL"),
                    budget_override=(
                        Budget(**rule_data["budget_override"])
                        if "budget_override" in rule_data else None
                    ),
                    recovery_strategy=rule_data.get("recovery_strategy"),
                    reason=rule_data["reason"],
                    enabled=rule_data.get("enabled", True),
                )
                rules.append(rule)

            # Parse budget defaults
            budget_defaults = Budget(**data["budget_defaults"])

            # Parse risk classes
            risk_classes = {}
            for name, risk_data in data.get("risk_classes", {}).items():
                risk_classes[name] = RiskClass(**risk_data)

            # Parse job overrides
            job_overrides = {}
            for job_type, budget_data in data.get("job_overrides", {}).items():
                job_overrides[job_type] = Budget(**budget_data)

            # Create manifest
            manifest = GovernorManifest(
                manifest_id=data.get("manifest_id", f"manifest_{data['version']}"),
                version=data["version"],
                hash_prev=data.get("hash_prev"),
                name=data["name"],
                description=data["description"],
                rules=rules,
                budget_defaults=budget_defaults,
                risk_classes=risk_classes,
                job_overrides=job_overrides,
                shadow_mode=data.get("shadow_mode", True),
                metadata=data.get("metadata", {}),
            )

            logger.info(
                f"Manifest loaded: {manifest.version} "
                f"({len(rules)} rules, hash={manifest.hash_self[:8]}...)"
            )

            return manifest

        except Exception as e:
            logger.error(f"Manifest schema validation failed: {e}")
            raise ManifestInvalidSchemaError(
                validation_errors=[str(e)]
            ) from e

    # ========================================================================
    # Default Templates
    # ========================================================================

    @staticmethod
    def create_default_manifest() -> GovernorManifest:
        """
        Create default manifest template.

        Returns:
            Default manifest
        """
        return ManifestLoader.from_dict({
            "version": "1.0.0",
            "name": "default",
            "description": "Default manifest with basic governance rules",
            "budget_defaults": {
                "timeout_ms": 30000,  # 30 seconds
                "max_retries": 3,
                "max_parallel_attempts": 5,
                "max_global_parallel": 20,
                "max_llm_tokens": 2000,
                "grace_period_ms": 5000,
            },
            "risk_classes": {
                "INTERNAL": {
                    "name": "INTERNAL",
                    "description": "Internal operations (safe, idempotent)",
                    "recovery_strategy": "RETRY",
                    "require_approval": False,
                    "budget_multiplier": 1.0,
                },
                "EXTERNAL": {
                    "name": "EXTERNAL",
                    "description": "External dependencies (may be unreliable)",
                    "recovery_strategy": "RETRY",
                    "require_approval": False,
                    "budget_multiplier": 1.5,  # More generous timeout
                },
                "NON_IDEMPOTENT": {
                    "name": "NON_IDEMPOTENT",
                    "description": "Non-idempotent operations (manual rollback required)",
                    "recovery_strategy": "ROLLBACK_REQUIRED",
                    "require_approval": True,
                    "budget_multiplier": 2.0,  # Very generous budget
                },
            },
            "rules": [
                {
                    "rule_id": "llm_call_governance",
                    "priority": 100,
                    "description": "LLM calls require governance for token tracking",
                    "when": {"job_type": "llm_call"},
                    "then": {},
                    "mode": "RAIL",
                    "reason": "LLM calls require token budget enforcement",
                },
                {
                    "rule_id": "production_governance",
                    "priority": 200,
                    "description": "Production deployments require strict governance",
                    "when": {"environment": "production"},
                    "then": {},
                    "mode": "RAIL",
                    "reason": "Production requires audit trail and budget limits",
                },
                {
                    "rule_id": "personal_data_governance",
                    "priority": 150,
                    "description": "Personal data processing requires governance (DSGVO)",
                    "when": {"uses_personal_data": True},
                    "then": {},
                    "mode": "RAIL",
                    "recovery_strategy": "MANUAL_CONFIRM",
                    "reason": "Personal data requires manual oversight (DSGVO Art. 25)",
                },
                {
                    "rule_id": "default_direct",
                    "priority": 1000,
                    "description": "Low-risk operations use direct execution",
                    "when": {},  # Empty condition = matches everything
                    "then": {},
                    "mode": "DIRECT",
                    "reason": "Default: low-risk operations bypass rail overhead",
                },
            ],
        })
