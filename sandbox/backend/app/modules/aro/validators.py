"""
ARO Validators - Operation Validation

Validates repository operations before execution.

Principles:
- Fail-closed: Invalid operations are rejected
- Multi-level validation: Syntax, safety, policy
- Explicit checks: No implicit assumptions
- Detailed feedback: Clear error messages
"""

from __future__ import annotations

import os
import re
from abc import ABC, abstractmethod
from pathlib import Path
from typing import List, Optional, Set
from loguru import logger

from .schemas import (
    RepoOperationContext,
    RepoOperationType,
    ValidationResult,
    ValidationSeverity,
    AuthorizationLevel,
)


# ============================================================================
# Base Validator
# ============================================================================


class BaseValidator(ABC):
    """
    Abstract base class for validators.

    All validators must implement the validate() method.
    """

    def __init__(self, validator_id: str):
        """
        Initialize validator.

        Args:
            validator_id: Unique validator identifier
        """
        self.validator_id = validator_id

    @abstractmethod
    async def validate(
        self,
        context: RepoOperationContext
    ) -> ValidationResult:
        """
        Validate an operation context.

        Args:
            context: Operation context to validate

        Returns:
            Validation result
        """
        pass

    def _create_result(
        self,
        valid: bool,
        severity: ValidationSeverity,
        issues: List[str],
        warnings: List[str],
        checks_passed: int,
        checks_failed: int,
    ) -> ValidationResult:
        """Helper to create validation result"""
        return ValidationResult(
            valid=valid,
            severity=severity,
            issues=issues,
            warnings=warnings,
            checks_passed=checks_passed,
            checks_failed=checks_failed,
            validator_id=self.validator_id,
        )


# ============================================================================
# Concrete Validators
# ============================================================================


class RepositoryPathValidator(BaseValidator):
    """
    Validates repository paths.

    Checks:
    - Path exists
    - Path is a git repository
    - Path is not outside allowed directories
    """

    def __init__(self):
        super().__init__("repository_path_validator")
        # Define allowed base directories (security measure)
        self.allowed_base_dirs: Set[str] = {
            "/home/user/BRAiN",  # Development directory
            "/srv/dev",          # Dev deployment
            "/srv/stage",        # Stage deployment
            "/srv/prod",         # Prod deployment
        }

    async def validate(
        self,
        context: RepoOperationContext
    ) -> ValidationResult:
        """Validate repository path"""
        issues = []
        warnings = []
        checks_passed = 0
        checks_failed = 0

        repo_path = context.repo_path

        # Check 1: Path exists
        if not Path(repo_path).exists():
            issues.append(f"Repository path does not exist: {repo_path}")
            checks_failed += 1
        else:
            checks_passed += 1

        # Check 2: Path is a directory
        if not Path(repo_path).is_dir():
            issues.append(f"Repository path is not a directory: {repo_path}")
            checks_failed += 1
        else:
            checks_passed += 1

        # Check 3: Path contains .git directory
        git_dir = Path(repo_path) / ".git"
        if not git_dir.exists():
            issues.append(f"Not a git repository: {repo_path} (no .git directory)")
            checks_failed += 1
        else:
            checks_passed += 1

        # Check 4: Path is within allowed directories (security)
        path_allowed = any(
            repo_path.startswith(base_dir)
            for base_dir in self.allowed_base_dirs
        )
        if not path_allowed:
            issues.append(
                f"Repository path not in allowed directories: {repo_path}. "
                f"Allowed: {self.allowed_base_dirs}"
            )
            checks_failed += 1
        else:
            checks_passed += 1

        # Check 5: Path is readable
        if not os.access(repo_path, os.R_OK):
            issues.append(f"Repository path is not readable: {repo_path}")
            checks_failed += 1
        else:
            checks_passed += 1

        # Determine validity
        valid = len(issues) == 0
        severity = ValidationSeverity.ERROR if not valid else ValidationSeverity.INFO

        return self._create_result(
            valid=valid,
            severity=severity,
            issues=issues,
            warnings=warnings,
            checks_passed=checks_passed,
            checks_failed=checks_failed,
        )


class BranchNameValidator(BaseValidator):
    """
    Validates git branch names.

    Checks:
    - Branch name follows git conventions
    - Branch name is not dangerous (main, master without auth)
    - Branch name matches expected patterns
    """

    def __init__(self):
        super().__init__("branch_name_validator")

        # Dangerous branches that require elevated authorization
        self.protected_branches: Set[str] = {"main", "master", "production", "prod"}

        # Valid branch name pattern (git conventions)
        # Letters, numbers, dash, underscore, slash
        self.valid_pattern = re.compile(r"^[a-zA-Z0-9/_-]+$")

    async def validate(
        self,
        context: RepoOperationContext
    ) -> ValidationResult:
        """Validate branch name"""
        issues = []
        warnings = []
        checks_passed = 0
        checks_failed = 0

        branch = context.branch

        # Check 1: Branch name is not empty
        if not branch or branch.strip() == "":
            issues.append("Branch name is empty")
            checks_failed += 1
        else:
            checks_passed += 1

        # Check 2: Branch name matches valid pattern
        if not self.valid_pattern.match(branch):
            issues.append(
                f"Branch name contains invalid characters: {branch}. "
                "Allowed: letters, numbers, dash, underscore, slash"
            )
            checks_failed += 1
        else:
            checks_passed += 1

        # Check 3: Branch name is not too long
        if len(branch) > 255:
            issues.append(f"Branch name is too long: {len(branch)} chars (max 255)")
            checks_failed += 1
        else:
            checks_passed += 1

        # Check 4: Protected branches require admin authorization
        if branch in self.protected_branches:
            if context.granted_auth_level != AuthorizationLevel.ADMIN:
                issues.append(
                    f"Branch '{branch}' is protected and requires ADMIN authorization. "
                    f"Current level: {context.granted_auth_level.value}"
                )
                checks_failed += 1
            else:
                warnings.append(
                    f"Operating on protected branch: {branch} (authorized)"
                )
                checks_passed += 1

        # Check 5: Branch name should not start with special characters
        if branch.startswith("-") or branch.startswith("/"):
            issues.append(f"Branch name should not start with '-' or '/': {branch}")
            checks_failed += 1
        else:
            checks_passed += 1

        valid = len(issues) == 0
        severity = ValidationSeverity.ERROR if not valid else ValidationSeverity.INFO

        return self._create_result(
            valid=valid,
            severity=severity,
            issues=issues,
            warnings=warnings,
            checks_passed=checks_passed,
            checks_failed=checks_failed,
        )


class OperationTypeValidator(BaseValidator):
    """
    Validates operation type against authorization level.

    Checks:
    - Operation type requires appropriate authorization
    - Dangerous operations have elevated requirements
    """

    def __init__(self):
        super().__init__("operation_type_validator")

        # Map operation types to required authorization levels
        self.required_auth: dict[RepoOperationType, AuthorizationLevel] = {
            # Read operations
            RepoOperationType.READ_FILE: AuthorizationLevel.READ_ONLY,
            RepoOperationType.LIST_FILES: AuthorizationLevel.READ_ONLY,
            RepoOperationType.GET_STATUS: AuthorizationLevel.READ_ONLY,
            RepoOperationType.GET_DIFF: AuthorizationLevel.READ_ONLY,
            RepoOperationType.GET_LOG: AuthorizationLevel.READ_ONLY,

            # Write operations
            RepoOperationType.CREATE_FILE: AuthorizationLevel.WRITE,
            RepoOperationType.UPDATE_FILE: AuthorizationLevel.WRITE,
            RepoOperationType.DELETE_FILE: AuthorizationLevel.WRITE,
            RepoOperationType.CREATE_BRANCH: AuthorizationLevel.WRITE,

            # Git operations
            RepoOperationType.COMMIT: AuthorizationLevel.COMMIT,
            RepoOperationType.PUSH: AuthorizationLevel.PUSH,
            RepoOperationType.MERGE: AuthorizationLevel.PUSH,
            RepoOperationType.REBASE: AuthorizationLevel.PUSH,

            # Dangerous operations
            RepoOperationType.FORCE_PUSH: AuthorizationLevel.ADMIN,
            RepoOperationType.DELETE_BRANCH: AuthorizationLevel.ADMIN,
            RepoOperationType.RESET_HARD: AuthorizationLevel.ADMIN,
        }

        # Authorization level hierarchy (higher value = more permissive)
        self.auth_hierarchy = {
            AuthorizationLevel.NONE: 0,
            AuthorizationLevel.READ_ONLY: 1,
            AuthorizationLevel.WRITE: 2,
            AuthorizationLevel.COMMIT: 3,
            AuthorizationLevel.PUSH: 4,
            AuthorizationLevel.ADMIN: 5,
        }

    async def validate(
        self,
        context: RepoOperationContext
    ) -> ValidationResult:
        """Validate operation type"""
        issues = []
        warnings = []
        checks_passed = 0
        checks_failed = 0

        operation_type = context.operation_type
        granted_level = context.granted_auth_level

        # Check 1: Operation type has a defined required level
        required_level = self.required_auth.get(operation_type)
        if required_level is None:
            issues.append(f"Unknown operation type: {operation_type}")
            checks_failed += 1
            # Cannot continue without knowing required level
            return self._create_result(
                valid=False,
                severity=ValidationSeverity.ERROR,
                issues=issues,
                warnings=warnings,
                checks_passed=checks_passed,
                checks_failed=checks_failed,
            )

        checks_passed += 1

        # Check 2: Granted level is sufficient
        granted_rank = self.auth_hierarchy.get(granted_level, 0)
        required_rank = self.auth_hierarchy.get(required_level, 999)

        if granted_rank < required_rank:
            issues.append(
                f"Insufficient authorization for operation '{operation_type.value}'. "
                f"Required: {required_level.value}, Granted: {granted_level.value}"
            )
            checks_failed += 1
        else:
            checks_passed += 1

        # Check 3: Warn on dangerous operations
        dangerous_ops = {
            RepoOperationType.FORCE_PUSH,
            RepoOperationType.DELETE_BRANCH,
            RepoOperationType.RESET_HARD,
        }
        if operation_type in dangerous_ops:
            warnings.append(
                f"Dangerous operation: {operation_type.value}. "
                "This operation is irreversible and requires ADMIN authorization."
            )

        valid = len(issues) == 0
        severity = ValidationSeverity.ERROR if not valid else (
            ValidationSeverity.WARNING if warnings else ValidationSeverity.INFO
        )

        return self._create_result(
            valid=valid,
            severity=severity,
            issues=issues,
            warnings=warnings,
            checks_passed=checks_passed,
            checks_failed=checks_failed,
        )


class ParameterValidator(BaseValidator):
    """
    Validates operation parameters.

    Checks:
    - Required parameters are present
    - Parameters have valid values
    - No injection attacks in parameters
    """

    def __init__(self):
        super().__init__("parameter_validator")

        # Define required parameters for each operation type
        self.required_params: dict[RepoOperationType, Set[str]] = {
            RepoOperationType.READ_FILE: {"file_path"},
            RepoOperationType.CREATE_FILE: {"file_path", "content"},
            RepoOperationType.UPDATE_FILE: {"file_path", "content"},
            RepoOperationType.DELETE_FILE: {"file_path"},
            RepoOperationType.CREATE_BRANCH: {"branch_name"},
            RepoOperationType.COMMIT: {"message"},
            RepoOperationType.PUSH: {},  # No required params
            RepoOperationType.MERGE: {"source_branch"},
            RepoOperationType.REBASE: {"base_branch"},
            RepoOperationType.FORCE_PUSH: {},
            RepoOperationType.DELETE_BRANCH: {"branch_name"},
            RepoOperationType.RESET_HARD: {"commit_hash"},
        }

    async def validate(
        self,
        context: RepoOperationContext
    ) -> ValidationResult:
        """Validate parameters"""
        issues = []
        warnings = []
        checks_passed = 0
        checks_failed = 0

        operation_type = context.operation_type
        params = context.params

        # Check 1: Required parameters are present
        required = self.required_params.get(operation_type, set())
        for param in required:
            if param not in params:
                issues.append(
                    f"Missing required parameter for {operation_type.value}: {param}"
                )
                checks_failed += 1
            else:
                checks_passed += 1

        # Check 2: Validate specific parameter values
        # Example: file_path should not contain ".."
        if "file_path" in params:
            file_path = params["file_path"]
            if ".." in file_path:
                issues.append(
                    f"Invalid file path (contains '..'): {file_path}. "
                    "Path traversal is not allowed."
                )
                checks_failed += 1
            else:
                checks_passed += 1

        # Check 3: Validate commit message (if present)
        if "message" in params:
            message = params["message"]
            if not message or message.strip() == "":
                issues.append("Commit message is empty")
                checks_failed += 1
            elif len(message) > 1000:
                warnings.append(
                    f"Commit message is very long ({len(message)} chars)"
                )
                checks_passed += 1
            else:
                checks_passed += 1

        # Check 4: Validate branch names (if present)
        for branch_param in ["branch_name", "source_branch", "base_branch"]:
            if branch_param in params:
                branch_name = params[branch_param]
                if not re.match(r"^[a-zA-Z0-9/_-]+$", branch_name):
                    issues.append(
                        f"Invalid branch name in {branch_param}: {branch_name}"
                    )
                    checks_failed += 1
                else:
                    checks_passed += 1

        valid = len(issues) == 0
        severity = ValidationSeverity.ERROR if not valid else (
            ValidationSeverity.WARNING if warnings else ValidationSeverity.INFO
        )

        return self._create_result(
            valid=valid,
            severity=severity,
            issues=issues,
            warnings=warnings,
            checks_passed=checks_passed,
            checks_failed=checks_failed,
        )


# ============================================================================
# Validator Manager
# ============================================================================


class ValidatorManager:
    """
    Manages all validators and coordinates validation.

    Runs all validators and aggregates results.
    """

    def __init__(self):
        """Initialize validator manager"""
        self.validators: List[BaseValidator] = [
            RepositoryPathValidator(),
            BranchNameValidator(),
            OperationTypeValidator(),
            ParameterValidator(),
        ]

        logger.info(
            f"✅ Validator Manager initialized ({len(self.validators)} validators)"
        )

    async def validate_all(
        self,
        context: RepoOperationContext
    ) -> List[ValidationResult]:
        """
        Run all validators on a context.

        Args:
            context: Operation context to validate

        Returns:
            List of validation results (one per validator)
        """
        results = []

        for validator in self.validators:
            try:
                result = await validator.validate(context)
                results.append(result)

                if not result.valid:
                    logger.warning(
                        f"⚠️ Validation failed: {validator.validator_id} - "
                        f"{result.issues}"
                    )

            except Exception as e:
                logger.error(f"❌ Validator {validator.validator_id} failed: {e}")
                # Create error result
                error_result = ValidationResult(
                    valid=False,
                    severity=ValidationSeverity.CRITICAL,
                    issues=[f"Validator crashed: {str(e)}"],
                    warnings=[],
                    checks_passed=0,
                    checks_failed=1,
                    validator_id=validator.validator_id,
                )
                results.append(error_result)

        return results

    def is_valid(self, results: List[ValidationResult]) -> bool:
        """
        Check if all validation results are valid.

        Args:
            results: List of validation results

        Returns:
            True if all results are valid
        """
        return all(r.valid for r in results)


# ============================================================================
# Singleton Instance
# ============================================================================

_validator_manager: Optional[ValidatorManager] = None


def get_validator_manager() -> ValidatorManager:
    """Get the singleton validator manager instance"""
    global _validator_manager
    if _validator_manager is None:
        _validator_manager = ValidatorManager()
    return _validator_manager
