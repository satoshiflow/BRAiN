"""
Template Validator

Validates template manifests and variable values.
"""

from __future__ import annotations

from typing import Dict, List, Any
import re
from loguru import logger

from app.modules.template_registry.schemas import (
    Template,
    TemplateVariable,
    VariableType,
    ValidationResult,
)


class TemplateValidator:
    """
    Validates templates and template variables.

    Features:
    - Manifest structure validation
    - Variable type checking
    - Value range validation
    - Security checks (no code injection)
    """

    # Regex patterns for validation
    COLOR_PATTERN = re.compile(r"^#[0-9a-fA-F]{6}$")
    EMAIL_PATTERN = re.compile(r"^[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+$")
    URL_PATTERN = re.compile(r"^https?://[^\s]+$")

    def __init__(self):
        """Initialize template validator"""
        logger.debug("TemplateValidator initialized")

    def validate(self, template: Template) -> ValidationResult:
        """
        Validate template manifest.

        Args:
            template: Template to validate

        Returns:
            Validation result
        """
        errors = []
        warnings = []

        # Check template_id format
        if not template.template_id:
            errors.append("template_id is required")
        elif not re.match(r"^[a-z0-9_]+$", template.template_id):
            errors.append("template_id must be lowercase alphanumeric with underscores")

        # Check version format (semantic versioning)
        if not template.version:
            errors.append("version is required")
        elif not re.match(r"^\d+\.\d+\.\d+$", template.version):
            errors.append("version must follow semantic versioning (e.g., '1.0.0')")

        # Check variables
        for var in template.variables:
            var_errors = self._validate_variable_definition(var)
            errors.extend(var_errors)

        # Check files
        if not template.files:
            warnings.append("Template has no files defined")

        for file_def in template.files:
            if not file_def.path:
                errors.append("File path cannot be empty")
            if not file_def.output_path:
                errors.append("File output_path cannot be empty")

        # Security checks
        for var in template.variables:
            if var.name in ["__", "_mro_", "__class__", "__init__", "__globals__"]:
                errors.append(f"Variable name '{var.name}' is reserved and not allowed (security)")

        return ValidationResult(
            is_valid=len(errors) == 0,
            errors=errors,
            warnings=warnings,
        )

    def _validate_variable_definition(self, var: TemplateVariable) -> List[str]:
        """
        Validate variable definition.

        Args:
            var: Variable definition

        Returns:
            List of validation errors
        """
        errors = []

        # Check name format
        if not var.name:
            errors.append("Variable name is required")
        elif not re.match(r"^[a-z][a-z0-9_]*$", var.name):
            errors.append(f"Variable name '{var.name}' must be lowercase alphanumeric starting with letter")

        # Check default value type matches
        if var.default is not None:
            value_errors = self._validate_variable_value(var, var.default)
            if value_errors:
                errors.append(f"Default value for '{var.name}' is invalid: {', '.join(value_errors)}")

        return errors

    def validate_variables(
        self,
        template: Template,
        variables: Dict[str, Any]
    ) -> List[str]:
        """
        Validate variable values against template requirements.

        Args:
            template: Template with variable definitions
            variables: Variable values to validate

        Returns:
            List of validation errors (empty if valid)
        """
        errors = []

        # Build variable map
        var_map = {var.name: var for var in template.variables}

        # Check required variables are provided
        for var in template.variables:
            if var.required and var.name not in variables:
                # Check if default exists
                if var.default is None:
                    errors.append(f"Required variable '{var.name}' is missing")

        # Validate provided variables
        for var_name, value in variables.items():
            if var_name not in var_map:
                # Unknown variable (warning, not error - allows extra vars)
                logger.warning(f"Unknown variable provided: {var_name}")
                continue

            var_def = var_map[var_name]
            value_errors = self._validate_variable_value(var_def, value)
            errors.extend(value_errors)

        return errors

    def _validate_variable_value(
        self,
        var_def: TemplateVariable,
        value: Any
    ) -> List[str]:
        """
        Validate a single variable value.

        Args:
            var_def: Variable definition
            value: Value to validate

        Returns:
            List of validation errors
        """
        errors = []

        # Type validation
        if var_def.type == VariableType.STRING:
            if not isinstance(value, str):
                errors.append(f"Variable '{var_def.name}' must be a string")
            else:
                errors.extend(self._validate_string(var_def, value))

        elif var_def.type == VariableType.INTEGER:
            if not isinstance(value, int) or isinstance(value, bool):
                errors.append(f"Variable '{var_def.name}' must be an integer")
            else:
                errors.extend(self._validate_number(var_def, value))

        elif var_def.type == VariableType.FLOAT:
            if not isinstance(value, (int, float)) or isinstance(value, bool):
                errors.append(f"Variable '{var_def.name}' must be a number")
            else:
                errors.extend(self._validate_number(var_def, value))

        elif var_def.type == VariableType.BOOLEAN:
            if not isinstance(value, bool):
                errors.append(f"Variable '{var_def.name}' must be a boolean")

        elif var_def.type == VariableType.COLOR:
            if not isinstance(value, str):
                errors.append(f"Variable '{var_def.name}' must be a string")
            elif not self.COLOR_PATTERN.match(value):
                errors.append(f"Variable '{var_def.name}' must be a valid hex color (#RRGGBB)")

        elif var_def.type == VariableType.EMAIL:
            if not isinstance(value, str):
                errors.append(f"Variable '{var_def.name}' must be a string")
            elif not self.EMAIL_PATTERN.match(value):
                errors.append(f"Variable '{var_def.name}' must be a valid email address")

        elif var_def.type == VariableType.URL:
            if not isinstance(value, str):
                errors.append(f"Variable '{var_def.name}' must be a string")
            elif not self.URL_PATTERN.match(value):
                errors.append(f"Variable '{var_def.name}' must be a valid URL (http:// or https://)")

        elif var_def.type == VariableType.LIST:
            if not isinstance(value, list):
                errors.append(f"Variable '{var_def.name}' must be a list")

        elif var_def.type == VariableType.DICT:
            if not isinstance(value, dict):
                errors.append(f"Variable '{var_def.name}' must be a dictionary")

        return errors

    def _validate_string(self, var_def: TemplateVariable, value: str) -> List[str]:
        """Validate string-specific constraints"""
        errors = []

        if var_def.validation:
            min_len = var_def.validation.get("min_length")
            max_len = var_def.validation.get("max_length")
            pattern = var_def.validation.get("pattern")

            if min_len is not None and len(value) < min_len:
                errors.append(f"Variable '{var_def.name}' must be at least {min_len} characters")

            if max_len is not None and len(value) > max_len:
                errors.append(f"Variable '{var_def.name}' must be at most {max_len} characters")

            if pattern and not re.match(pattern, value):
                errors.append(f"Variable '{var_def.name}' does not match required pattern")

        return errors

    def _validate_number(
        self,
        var_def: TemplateVariable,
        value: int | float
    ) -> List[str]:
        """Validate number-specific constraints"""
        errors = []

        if var_def.validation:
            min_val = var_def.validation.get("min")
            max_val = var_def.validation.get("max")

            if min_val is not None and value < min_val:
                errors.append(f"Variable '{var_def.name}' must be at least {min_val}")

            if max_val is not None and value > max_val:
                errors.append(f"Variable '{var_def.name}' must be at most {max_val}")

        return errors
