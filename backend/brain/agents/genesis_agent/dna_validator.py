"""
DNA Validator for Genesis Agent System

This module provides comprehensive validation for Agent DNA including:
- Schema validation (Pydantic)
- Template hash verification
- Customization whitelist enforcement
- Security checks for forbidden modifications

Security Features:
- Only whitelisted fields can be customized
- Immutable fields (ethics_flags, created_by) are protected
- Template integrity verified via SHA256 hash
- Resource limits validated for reasonableness

Author: Genesis Agent System
Version: 2.0.0
Created: 2026-01-02
"""

from __future__ import annotations

import hashlib
import re
from pathlib import Path
from typing import Any, Dict, List, Optional

from pydantic import ValidationError as PydanticValidationError

from .dna_schema import AgentDNA, EthicsFlags


class ValidationError(Exception):
    """Custom validation error for DNA validation failures."""
    pass


class TemplateNotFoundError(Exception):
    """Raised when a template file cannot be found."""
    pass


# ============================================================================
# Customization Rules
# ============================================================================

ALLOWED_CUSTOMIZATIONS = {
    "metadata.name": {
        "type": "string",
        "max_length": 100,
        "pattern": r"^[a-z0-9_]+$",
        "description": "Agent name (lowercase, alphanumeric + underscore)"
    },
    "skills[].domains": {
        "type": "array",
        "action": "append",  # Can only ADD domains, not remove
        "max_items": 10,
        "description": "Add skill domains (append-only)"
    },
    "memory_seeds": {
        "type": "array",
        "action": "append",  # Can only ADD seeds, not remove
        "max_items": 20,
        "description": "Add memory seeds (append-only)"
    },
}

FORBIDDEN_CUSTOMIZATIONS = {
    "ethics_flags",              # Ethics and compliance (IMMUTABLE)
    "ethics_flags.data_privacy",
    "ethics_flags.transparency",
    "ethics_flags.bias_awareness",
    "ethics_flags.human_override",
    "resource_limits",           # Resource control (IMMUTABLE)
    "resource_limits.max_credits_per_mission",
    "resource_limits.max_llm_calls_per_day",
    "resource_limits.timeout_seconds",
    "traits.autonomy_level",     # Autonomy control (IMMUTABLE)
    "traits.base_type",          # Type integrity (IMMUTABLE)
    "capabilities",              # Security permissions (IMMUTABLE)
    "capabilities.tools_allowed",
    "capabilities.connectors_allowed",
    "capabilities.network_access",
    "runtime",                   # Runtime control (IMMUTABLE)
    "runtime.model_policy",
    "runtime.temperature_cap",
    "runtime.max_tokens_cap",
    "runtime.allowed_models",
    "metadata.created_by",       # Creator attribution (IMMUTABLE)
    "metadata.id",               # Identity (IMMUTABLE)
    "metadata.type",             # Type (IMMUTABLE)
    "metadata.dna_schema_version",  # Schema version (IMMUTABLE)
    "metadata.template_hash",    # Template integrity (IMMUTABLE)
}


class DNAValidator:
    """
    Validates Agent DNA for security, consistency, and compliance.

    This validator ensures that all agent DNA:
    1. Passes Pydantic schema validation
    2. Has valid template hash
    3. Only contains whitelisted customizations
    4. Meets business rules (proficiencies, limits, etc.)
    5. Preserves immutable fields

    Example:
        >>> validator = DNAValidator(templates_dir=Path("./templates"))
        >>> validator.validate_dna(agent_dna)
        >>> template_hash = validator.compute_template_hash("worker_base")
        >>> validator.validate_customizations(customizations)
    """

    def __init__(self, templates_dir: Path):
        """
        Initialize the DNA validator.

        Args:
            templates_dir: Path to directory containing template YAML files

        Raises:
            FileNotFoundError: If templates_dir does not exist
        """
        self.templates_dir = Path(templates_dir)
        if not self.templates_dir.exists():
            raise FileNotFoundError(
                f"Templates directory not found: {self.templates_dir}"
            )

    # ========================================================================
    # Template Hash Computation
    # ========================================================================

    def compute_template_hash(self, template_name: str) -> str:
        """
        Compute SHA256 hash of template file.

        This provides reproducibility and template integrity verification.
        The same template file will always produce the same hash.

        Args:
            template_name: Name of template without extension (e.g., "worker_base")

        Returns:
            str: Template hash in format "sha256:abc123..."

        Raises:
            TemplateNotFoundError: If template file does not exist

        Example:
            >>> validator = DNAValidator(templates_dir=Path("./templates"))
            >>> hash_val = validator.compute_template_hash("worker_base")
            >>> print(hash_val)
            'sha256:abc123def456...'
        """
        template_path = self.templates_dir / f"{template_name}.yaml"
        if not template_path.exists():
            raise TemplateNotFoundError(
                f"Template not found: {template_name} "
                f"(expected at {template_path})"
            )

        content = template_path.read_bytes()
        hash_digest = hashlib.sha256(content).hexdigest()
        return f"sha256:{hash_digest}"

    def verify_template_hash(
        self,
        template_name: str,
        expected_hash: str
    ) -> bool:
        """
        Verify that template hash matches expected value.

        Args:
            template_name: Name of template
            expected_hash: Expected hash value

        Returns:
            bool: True if hash matches, False otherwise

        Example:
            >>> is_valid = validator.verify_template_hash(
            ...     "worker_base",
            ...     "sha256:abc123..."
            ... )
        """
        actual_hash = self.compute_template_hash(template_name)
        return actual_hash == expected_hash

    # ========================================================================
    # Customization Validation
    # ========================================================================

    def validate_customizations(self, customizations: Dict[str, Any]) -> None:
        """
        Validate that customizations only modify allowed fields.

        This enforces the security whitelist, ensuring that:
        1. Only whitelisted fields can be modified
        2. Forbidden fields are protected
        3. Customization types and constraints are enforced

        Args:
            customizations: Dictionary of field paths to new values

        Raises:
            ValidationError: If any customization is invalid

        Example:
            >>> customizations = {
            ...     "metadata.name": "worker_specialized_01",
            ...     "skills[].domains": ["rest_api", "graphql"]
            ... }
            >>> validator.validate_customizations(customizations)
        """
        for key, value in customizations.items():
            # Check if field is forbidden
            if key in FORBIDDEN_CUSTOMIZATIONS:
                raise ValidationError(
                    f"Customization '{key}' is FORBIDDEN. "
                    f"This field is immutable for security/compliance reasons. "
                    f"Allowed customizations: {list(ALLOWED_CUSTOMIZATIONS.keys())}"
                )

            # Check if field is in whitelist
            if key not in ALLOWED_CUSTOMIZATIONS:
                raise ValidationError(
                    f"Customization '{key}' is not in whitelist. "
                    f"Allowed customizations: {list(ALLOWED_CUSTOMIZATIONS.keys())}"
                )

            # Validate against customization schema
            schema = ALLOWED_CUSTOMIZATIONS[key]
            self._validate_customization_value(key, value, schema)

    def _validate_customization_value(
        self,
        key: str,
        value: Any,
        schema: Dict[str, Any]
    ) -> None:
        """
        Validate a single customization value against its schema.

        Args:
            key: Customization key
            value: Customization value
            schema: Validation schema from ALLOWED_CUSTOMIZATIONS

        Raises:
            ValidationError: If value doesn't meet schema requirements
        """
        # Type validation
        expected_type = schema.get("type")

        if expected_type == "string":
            if not isinstance(value, str):
                raise ValidationError(
                    f"Customization '{key}' must be a string, got {type(value).__name__}"
                )

            # Pattern validation
            if "pattern" in schema:
                pattern = schema["pattern"]
                if not re.match(pattern, value):
                    raise ValidationError(
                        f"Customization '{key}' value '{value}' does not match "
                        f"required pattern: {pattern}"
                    )

            # Length validation
            if "max_length" in schema:
                max_len = schema["max_length"]
                if len(value) > max_len:
                    raise ValidationError(
                        f"Customization '{key}' exceeds max length of {max_len}"
                    )

        elif expected_type == "array":
            if not isinstance(value, list):
                raise ValidationError(
                    f"Customization '{key}' must be an array, got {type(value).__name__}"
                )

            # Item limit validation
            if "max_items" in schema:
                max_items = schema["max_items"]
                if len(value) > max_items:
                    raise ValidationError(
                        f"Customization '{key}' exceeds max items of {max_items}"
                    )

            # Action validation (append-only)
            action = schema.get("action")
            if action == "append":
                # For append-only fields, we don't validate the base list
                # since customizations only add to it
                pass

    # ========================================================================
    # DNA Validation
    # ========================================================================

    def validate_dna(self, dna: AgentDNA) -> None:
        """
        Validate DNA against schema and business rules.

        Validation Checks:
        1. Pydantic schema validation (automatic)
        2. Proficiency bounds (0-1)
        3. Resource limits reasonable
        4. Ethics flags immutable
        5. Mandatory fields present
        6. Base type consistency

        Args:
            dna: Agent DNA to validate

        Raises:
            ValidationError: If DNA validation fails

        Example:
            >>> validator.validate_dna(agent_dna)
        """
        # 1. Pydantic schema validation (already done by Pydantic)
        # If we get here, schema is valid

        # 2. Business rules validation

        # Validate skills proficiency
        for skill in dna.skills:
            if not (0.0 <= skill.proficiency <= 1.0):
                raise ValidationError(
                    f"Skill '{skill.skill_id}' proficiency must be 0-1, "
                    f"got {skill.proficiency}"
                )

        # 3. Mandatory fields validation
        if not dna.metadata.dna_schema_version:
            raise ValidationError(
                "dna_schema_version is MANDATORY (required by Registry)"
            )

        if not dna.metadata.template_hash:
            raise ValidationError(
                "template_hash is MANDATORY (required for reproducibility)"
            )

        # Validate template hash format
        if not dna.metadata.template_hash.startswith("sha256:"):
            raise ValidationError(
                f"template_hash must start with 'sha256:', "
                f"got: {dna.metadata.template_hash}"
            )

        # 4. Immutable fields validation
        if dna.metadata.created_by != "genesis_agent":
            raise ValidationError(
                "created_by must be 'genesis_agent' (IMMUTABLE)"
            )

        if dna.ethics_flags.human_override != "always_allowed":
            raise ValidationError(
                "ethics_flags.human_override must be 'always_allowed' "
                "(IMMUTABLE, EU AI Act Art. 16)"
            )

        # 5. Resource limits reasonableness
        if dna.resource_limits.max_credits_per_mission < 0:
            raise ValidationError(
                "max_credits_per_mission must be >= 0"
            )

        if dna.resource_limits.max_llm_calls_per_day < 0:
            raise ValidationError(
                "max_llm_calls_per_day must be >= 0"
            )

        if dna.resource_limits.timeout_seconds < 0:
            raise ValidationError(
                "timeout_seconds must be >= 0"
            )

        # 6. Base type consistency (validated in AgentDNA.model_post_init)

    # ========================================================================
    # Validation Utilities
    # ========================================================================

    def validate_template_exists(self, template_name: str) -> bool:
        """
        Check if a template file exists.

        Args:
            template_name: Name of template without extension

        Returns:
            bool: True if template exists, False otherwise

        Example:
            >>> exists = validator.validate_template_exists("worker_base")
        """
        template_path = self.templates_dir / f"{template_name}.yaml"
        return template_path.exists()

    def list_available_templates(self) -> List[str]:
        """
        List all available template names.

        Returns:
            List[str]: List of template names (without .yaml extension)

        Example:
            >>> templates = validator.list_available_templates()
            >>> print(templates)
            ['worker_base', 'analyst_base', 'builder_base', 'genesis_base']
        """
        return [
            f.stem
            for f in self.templates_dir.glob("*.yaml")
        ]

    def get_customization_help(self) -> Dict[str, Dict[str, Any]]:
        """
        Get documentation for allowed customizations.

        Returns:
            Dict mapping field paths to their schemas with descriptions

        Example:
            >>> help_info = validator.get_customization_help()
            >>> for field, schema in help_info.items():
            ...     print(f"{field}: {schema['description']}")
        """
        return ALLOWED_CUSTOMIZATIONS.copy()


# ============================================================================
# Validation Helpers
# ============================================================================

def validate_agent_dna(
    dna: AgentDNA,
    templates_dir: Path,
    template_name: Optional[str] = None
) -> None:
    """
    Convenience function for validating agent DNA.

    Args:
        dna: Agent DNA to validate
        templates_dir: Path to templates directory
        template_name: Optional template name for hash verification

    Raises:
        ValidationError: If validation fails

    Example:
        >>> validate_agent_dna(
        ...     dna=agent_dna,
        ...     templates_dir=Path("./templates"),
        ...     template_name="worker_base"
        ... )
    """
    validator = DNAValidator(templates_dir)
    validator.validate_dna(dna)

    if template_name:
        expected_hash = dna.metadata.template_hash
        if not validator.verify_template_hash(template_name, expected_hash):
            raise ValidationError(
                f"Template hash mismatch for '{template_name}'. "
                f"DNA may have been tampered with or template modified."
            )


def validate_customizations(
    customizations: Dict[str, Any],
    templates_dir: Path
) -> None:
    """
    Convenience function for validating customizations.

    Args:
        customizations: Customizations to validate
        templates_dir: Path to templates directory

    Raises:
        ValidationError: If validation fails

    Example:
        >>> validate_customizations(
        ...     customizations={"metadata.name": "worker_01"},
        ...     templates_dir=Path("./templates")
        ... )
    """
    validator = DNAValidator(templates_dir)
    validator.validate_customizations(customizations)
