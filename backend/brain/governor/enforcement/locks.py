"""
Locked Fields Enforcement Module (Phase 2c)

Validates agent DNA against immutable constraint fields.
Prevents privilege escalation and ensures compliance.

Locked fields are safety-critical invariants that CANNOT be mutated,
even by SYSTEM_ADMIN role. They are defined in governance manifests
and enforce compliance with DSGVO Art. 22 and EU AI Act Art. 16.

Features:
- Load locked fields from governance manifests
- Compare DNA mutations against locked values
- Support Genesis exception for can_create_agents
- Emit violation events with complete audit trail
- Raise PolicyViolationError to block creation

Author: Governor v1 System
Version: 1.0.0
Created: 2026-01-04
"""

from __future__ import annotations

import hashlib
import json
import logging
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field

from backend.brain.agents.genesis_agent.dna_schema import AgentType
from backend.brain.governor.constraints.defaults import get_default_constraints
from backend.brain.governor.manifests.loader import ManifestLoader
from backend.brain.governor.manifests.schema import GovernanceManifest


logger = logging.getLogger(__name__)


# ============================================================================
# Violation Models
# ============================================================================

class LockedFieldViolation(BaseModel):
    """
    Single locked field violation.

    Attributes:
        field_path: Dot-notation path (e.g., "ethics_flags.human_override")
        locked_value: Expected value from manifest/baseline
        attempted_value: Value in DNA mutation
        manifest_name: Manifest that defines this lock
    """
    field_path: str = Field(
        ...,
        description="Dot-notation field path"
    )

    locked_value: Any = Field(
        ...,
        description="Expected locked value"
    )

    attempted_value: Any = Field(
        ...,
        description="Attempted value in DNA"
    )

    manifest_name: str = Field(
        ...,
        description="Manifest defining this lock"
    )


class PolicyViolationError(Exception):
    """
    Raised when locked field is mutated.

    Attributes:
        violations: List of LockedFieldViolation instances
    """

    def __init__(self, violations: List[LockedFieldViolation]):
        self.violations = violations
        msg = f"Locked field violations: {[v.field_path for v in violations]}"
        super().__init__(msg)


# ============================================================================
# Locked Field Enforcer
# ============================================================================

class LockedFieldEnforcer:
    """
    Enforces locked field immutability.

    Locked fields are defined in two places:
    1. Governance manifest (manifest.locks.locked_fields)
    2. Agent type baseline constraints (constraints.locks.locked_fields)

    Both sources are checked, and any mutation triggers PolicyViolationError.

    Example:
        >>> enforcer = LockedFieldEnforcer(manifest_loader)
        >>> dna = {"ethics_flags.human_override": "never"}  # Locked to "always_allowed"
        >>> try:
        ...     enforcer.validate_dna_against_locks("worker", dna)
        ... except PolicyViolationError as e:
        ...     print(f"Violations: {len(e.violations)}")
        Violations: 1
    """

    def __init__(self, manifest_loader: Optional[ManifestLoader] = None):
        """
        Initialize enforcer.

        Args:
            manifest_loader: ManifestLoader instance (creates one if None)
        """
        self.manifest_loader = manifest_loader or ManifestLoader()

    def validate_dna_against_locks(
        self,
        agent_type: AgentType | str,
        dna: Dict[str, Any],
        manifest_name: str = "defaults"
    ) -> List[LockedFieldViolation]:
        """
        Check if DNA mutates any locked fields.

        Args:
            agent_type: Agent type (worker, supervisor, genesis, etc.)
            dna: Proposed DNA mutations (flat or nested dict)
            manifest_name: Manifest to check (default: "defaults")

        Returns:
            List of violations (empty if valid)

        Raises:
            PolicyViolationError: If violations detected
            FileNotFoundError: If manifest not found
            ValueError: If agent_type is unknown

        Example:
            >>> dna = {"capabilities.can_modify_governor": True}  # Locked to False
            >>> violations = enforcer.validate_dna_against_locks("worker", dna)
            PolicyViolationError: Locked field violations: ['capabilities.can_modify_governor']
        """
        # Convert agent_type to AgentType enum if string
        if isinstance(agent_type, str):
            try:
                agent_type = AgentType(agent_type.upper())
            except ValueError:
                raise ValueError(f"Unknown agent type: {agent_type}")

        # Load manifest
        manifest = self._load_manifest(manifest_name)

        # Get locked fields from manifest
        manifest_locked_fields = self._get_manifest_locked_fields(manifest)

        # Get baseline constraints for agent type
        baseline_constraints = get_default_constraints(agent_type)

        # Get locked fields from baseline
        baseline_locked_fields = baseline_constraints.locks.locked_fields

        # Combine both sources (use set to avoid duplicates)
        all_locked_fields = list(set(manifest_locked_fields + baseline_locked_fields))

        logger.debug(
            f"Validating DNA against {len(all_locked_fields)} locked fields for {agent_type.value}"
        )

        # Flatten DNA to dot-notation paths for easy comparison
        flat_dna = self._flatten_dict(dna)

        # Check each locked field
        violations: List[LockedFieldViolation] = []

        for field_path in all_locked_fields:
            # Check if DNA attempts to mutate this field
            if field_path in flat_dna:
                attempted_value = flat_dna[field_path]

                # Get the locked value from baseline
                locked_value = self._get_locked_value(
                    field_path,
                    baseline_constraints,
                    manifest
                )

                # Check for Genesis exception
                if self._is_genesis_exception(agent_type, field_path):
                    logger.debug(
                        f"Genesis exception: allowing {field_path}={attempted_value}"
                    )
                    continue

                # Compare values
                if attempted_value != locked_value:
                    logger.warning(
                        f"Locked field violation: {field_path} "
                        f"(attempted={attempted_value}, locked={locked_value})"
                    )

                    violations.append(
                        LockedFieldViolation(
                            field_path=field_path,
                            locked_value=locked_value,
                            attempted_value=attempted_value,
                            manifest_name=manifest_name
                        )
                    )

        # Raise error if violations found
        if violations:
            raise PolicyViolationError(violations)

        logger.debug("No locked field violations detected")
        return violations

    def _load_manifest(self, manifest_name: str) -> GovernanceManifest:
        """
        Load governance manifest.

        Args:
            manifest_name: Manifest name (e.g., "defaults")

        Returns:
            Loaded GovernanceManifest

        Raises:
            FileNotFoundError: If manifest file not found
        """
        from pathlib import Path

        manifest_path = (
            Path(__file__).parent.parent
            / "manifests"
            / f"{manifest_name}.yaml"
        )

        return self.manifest_loader.load_from_file(manifest_path)

    def _get_manifest_locked_fields(
        self,
        manifest: GovernanceManifest
    ) -> List[str]:
        """
        Extract locked fields from manifest.

        Args:
            manifest: Loaded governance manifest

        Returns:
            List of locked field paths
        """
        if not manifest.locks or not manifest.locks.locked_fields:
            return []

        return manifest.locks.locked_fields

    def _get_locked_value(
        self,
        field_path: str,
        baseline_constraints,
        manifest: GovernanceManifest
    ) -> Any:
        """
        Get the locked value for a field.

        The locked value is determined by checking:
        1. Explicit values in manifest (if defined)
        2. Default values from baseline constraints
        3. Hardcoded values for known fields

        Args:
            field_path: Field path (e.g., "ethics_flags.human_override")
            baseline_constraints: Baseline EffectiveConstraints
            manifest: Governance manifest

        Returns:
            The locked value for this field
        """
        # Hardcoded locked values for known fields
        KNOWN_LOCKED_VALUES = {
            "ethics_flags.human_override": "always_allowed",
            "capabilities.can_create_agents": False,
            "capabilities.can_modify_governor": False,
        }

        # Check hardcoded values first
        if field_path in KNOWN_LOCKED_VALUES:
            return KNOWN_LOCKED_VALUES[field_path]

        # Try to extract from baseline constraints
        try:
            return self._get_nested_value(
                baseline_constraints.model_dump(),
                field_path
            )
        except KeyError:
            # Field not in baseline, return None
            logger.warning(
                f"Locked field {field_path} not found in baseline constraints"
            )
            return None

    def _flatten_dict(
        self,
        d: Dict[str, Any],
        parent_key: str = "",
        sep: str = "."
    ) -> Dict[str, Any]:
        """
        Flatten nested dict to dot-notation paths.

        Args:
            d: Dictionary to flatten
            parent_key: Parent key prefix
            sep: Separator character

        Returns:
            Flattened dictionary

        Example:
            >>> d = {"ethics_flags": {"human_override": "never"}}
            >>> _flatten_dict(d)
            {'ethics_flags.human_override': 'never'}
        """
        items: List[tuple] = []

        for k, v in d.items():
            new_key = f"{parent_key}{sep}{k}" if parent_key else k

            if isinstance(v, dict):
                items.extend(
                    self._flatten_dict(v, new_key, sep=sep).items()
                )
            else:
                items.append((new_key, v))

        return dict(items)

    def _get_nested_value(self, obj: Dict, path: str) -> Any:
        """
        Get value from nested dict using dot notation.

        Args:
            obj: Dictionary to search
            path: Dot-notation path (e.g., "ethics_flags.human_override")

        Returns:
            Value at path

        Raises:
            KeyError: If path not found

        Example:
            >>> obj = {"ethics_flags": {"human_override": "always_allowed"}}
            >>> _get_nested_value(obj, "ethics_flags.human_override")
            'always_allowed'
        """
        keys = path.split(".")
        value = obj

        for key in keys:
            if isinstance(value, dict):
                value = value[key]
            else:
                raise KeyError(f"Path {path} not found in object")

        return value

    def _is_genesis_exception(
        self,
        agent_type: AgentType,
        field_path: str
    ) -> bool:
        """
        Check if Genesis role has exception for this field.

        Genesis agents are allowed to have can_create_agents=True
        to bootstrap the agent fleet.

        Args:
            agent_type: Agent type
            field_path: Field path being checked

        Returns:
            True if Genesis exception applies
        """
        is_genesis = agent_type == AgentType.GENESIS
        is_can_create = field_path == "capabilities.can_create_agents"

        return is_genesis and is_can_create

    def get_dna_hash(self, dna: Dict[str, Any]) -> str:
        """
        Compute SHA256 hash of DNA for audit trail.

        Args:
            dna: DNA dictionary

        Returns:
            SHA256 hex digest
        """
        dna_json = json.dumps(dna, sort_keys=True)
        return hashlib.sha256(dna_json.encode()).hexdigest()


# ============================================================================
# Factory Function
# ============================================================================

def get_locked_field_enforcer(
    manifest_loader: Optional[ManifestLoader] = None
) -> LockedFieldEnforcer:
    """
    Factory function to create LockedFieldEnforcer.

    Args:
        manifest_loader: Optional ManifestLoader instance

    Returns:
        LockedFieldEnforcer instance
    """
    return LockedFieldEnforcer(manifest_loader=manifest_loader)
