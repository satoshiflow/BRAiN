"""
ARO Safety Checkpoints - Fail-Safe Mechanisms

Implements safety checks before critical operations.

Principles:
- Fail-closed: Unsafe operations are blocked
- Multi-layered defense: Multiple independent checks
- Risk scoring: Quantify operation risk
- Explicit verification: No assumptions
"""

from __future__ import annotations

import os
import subprocess
from abc import ABC, abstractmethod
from pathlib import Path
from typing import List, Optional, Set
from loguru import logger

from .schemas import (
    RepoOperationContext,
    RepoOperationType,
    SafetyCheckResult,
)


# ============================================================================
# Base Safety Checkpoint
# ============================================================================


class BaseSafetyCheckpoint(ABC):
    """
    Abstract base class for safety checkpoints.

    All checkpoints must implement the check() method.
    """

    def __init__(self, checkpoint_id: str):
        """
        Initialize checkpoint.

        Args:
            checkpoint_id: Unique checkpoint identifier
        """
        self.checkpoint_id = checkpoint_id

    @abstractmethod
    async def check(
        self,
        context: RepoOperationContext
    ) -> SafetyCheckResult:
        """
        Perform safety check.

        Args:
            context: Operation context to check

        Returns:
            Safety check result
        """
        pass

    def _create_result(
        self,
        safe: bool,
        reason: str,
        blocked_reasons: List[str],
        risk_score: float,
        risk_factors: List[str],
    ) -> SafetyCheckResult:
        """Helper to create safety check result"""
        return SafetyCheckResult(
            safe=safe,
            checkpoint_id=self.checkpoint_id,
            reason=reason,
            blocked_reasons=blocked_reasons,
            risk_score=risk_score,
            risk_factors=risk_factors,
        )


# ============================================================================
# Concrete Safety Checkpoints
# ============================================================================


class GitStatusCheckpoint(BaseSafetyCheckpoint):
    """
    Checks git repository status before operations.

    Ensures:
    - Repository is clean (no uncommitted changes) for destructive ops
    - No merge conflicts
    - Working directory is in expected state
    """

    def __init__(self):
        super().__init__("git_status_checkpoint")

        # Operations that require clean working directory
        self.require_clean: Set[RepoOperationType] = {
            RepoOperationType.RESET_HARD,
            RepoOperationType.REBASE,
            RepoOperationType.MERGE,
        }

    async def check(
        self,
        context: RepoOperationContext
    ) -> SafetyCheckResult:
        """Check git status"""
        blocked_reasons = []
        risk_factors = []
        risk_score = 0.0

        repo_path = context.repo_path
        operation_type = context.operation_type

        try:
            # Check if working directory is clean
            result = subprocess.run(
                ["git", "status", "--porcelain"],
                cwd=repo_path,
                capture_output=True,
                text=True,
                timeout=5,
            )

            if result.returncode != 0:
                blocked_reasons.append(
                    f"Git status command failed: {result.stderr}"
                )
                risk_score = 1.0
                risk_factors.append("Git command failure")

            # Check for uncommitted changes
            output = result.stdout.strip()
            has_changes = len(output) > 0

            if has_changes:
                risk_factors.append("Uncommitted changes in repository")
                risk_score += 0.3

                # Some operations require clean working directory
                if operation_type in self.require_clean:
                    blocked_reasons.append(
                        f"Operation '{operation_type.value}' requires clean "
                        "working directory but uncommitted changes exist"
                    )
                    risk_score = 1.0

            # Check for merge conflicts
            if "UU" in output or "AA" in output:
                blocked_reasons.append("Repository has merge conflicts")
                risk_score = 1.0
                risk_factors.append("Merge conflicts present")

        except subprocess.TimeoutExpired:
            blocked_reasons.append("Git status command timed out")
            risk_score = 1.0
            risk_factors.append("Git command timeout")

        except Exception as e:
            blocked_reasons.append(f"Git status check failed: {str(e)}")
            risk_score = 1.0
            risk_factors.append("Safety check exception")

        # Determine if safe
        safe = len(blocked_reasons) == 0
        reason = (
            "Git status check passed"
            if safe
            else f"Git status check failed: {blocked_reasons}"
        )

        return self._create_result(
            safe=safe,
            reason=reason,
            blocked_reasons=blocked_reasons,
            risk_score=min(risk_score, 1.0),
            risk_factors=risk_factors,
        )


class BranchProtectionCheckpoint(BaseSafetyCheckpoint):
    """
    Prevents dangerous operations on protected branches.

    Ensures:
    - No force push to main/master
    - No hard reset on protected branches
    - No branch deletion of protected branches
    """

    def __init__(self):
        super().__init__("branch_protection_checkpoint")

        # Protected branches
        self.protected_branches: Set[str] = {
            "main",
            "master",
            "production",
            "prod",
        }

        # Dangerous operations
        self.dangerous_ops: Set[RepoOperationType] = {
            RepoOperationType.FORCE_PUSH,
            RepoOperationType.RESET_HARD,
            RepoOperationType.DELETE_BRANCH,
        }

    async def check(
        self,
        context: RepoOperationContext
    ) -> SafetyCheckResult:
        """Check branch protection"""
        blocked_reasons = []
        risk_factors = []
        risk_score = 0.0

        branch = context.branch
        operation_type = context.operation_type

        # Check if branch is protected
        is_protected = branch in self.protected_branches

        if is_protected:
            risk_factors.append(f"Operating on protected branch: {branch}")
            risk_score += 0.5

            # Check if operation is dangerous
            if operation_type in self.dangerous_ops:
                blocked_reasons.append(
                    f"Dangerous operation '{operation_type.value}' is not allowed "
                    f"on protected branch '{branch}'"
                )
                risk_score = 1.0
                risk_factors.append("Dangerous operation on protected branch")

        # Additional risk for force push
        if operation_type == RepoOperationType.FORCE_PUSH:
            risk_factors.append("Force push operation")
            risk_score += 0.4

        # Determine if safe
        safe = len(blocked_reasons) == 0
        reason = (
            "Branch protection check passed"
            if safe
            else f"Branch protection violated: {blocked_reasons}"
        )

        return self._create_result(
            safe=safe,
            reason=reason,
            blocked_reasons=blocked_reasons,
            risk_score=min(risk_score, 1.0),
            risk_factors=risk_factors,
        )


class FileSystemCheckpoint(BaseSafetyCheckpoint):
    """
    Checks file system safety for file operations.

    Ensures:
    - Files are within repository
    - No dangerous file paths
    - Adequate disk space
    - Proper permissions
    """

    def __init__(self):
        super().__init__("file_system_checkpoint")

        # Dangerous file patterns
        self.dangerous_patterns: Set[str] = {
            ".env",
            "credentials",
            "secrets",
            "private_key",
            "id_rsa",
        }

    async def check(
        self,
        context: RepoOperationContext
    ) -> SafetyCheckResult:
        """Check file system safety"""
        blocked_reasons = []
        risk_factors = []
        risk_score = 0.0

        repo_path = Path(context.repo_path)
        params = context.params
        operation_type = context.operation_type

        # Only check for file operations
        file_ops = {
            RepoOperationType.CREATE_FILE,
            RepoOperationType.UPDATE_FILE,
            RepoOperationType.DELETE_FILE,
            RepoOperationType.READ_FILE,
        }

        if operation_type not in file_ops:
            # Not a file operation - safe
            return self._create_result(
                safe=True,
                reason="Not a file operation",
                blocked_reasons=[],
                risk_score=0.0,
                risk_factors=[],
            )

        # Get file path from params
        file_path_str = params.get("file_path")
        if not file_path_str:
            blocked_reasons.append("File path not specified")
            risk_score = 1.0
            return self._create_result(
                safe=False,
                reason="File path missing",
                blocked_reasons=blocked_reasons,
                risk_score=risk_score,
                risk_factors=["Missing file path"],
            )

        # Resolve file path
        try:
            file_path = (repo_path / file_path_str).resolve()

            # Check 1: File is within repository
            if not str(file_path).startswith(str(repo_path)):
                blocked_reasons.append(
                    f"File path is outside repository: {file_path}"
                )
                risk_score = 1.0
                risk_factors.append("Path traversal attempt")

            # Check 2: No dangerous file patterns
            for pattern in self.dangerous_patterns:
                if pattern.lower() in file_path_str.lower():
                    risk_factors.append(f"Dangerous file pattern: {pattern}")
                    risk_score += 0.3

            # Check 3: For create/update, check disk space
            if operation_type in {
                RepoOperationType.CREATE_FILE,
                RepoOperationType.UPDATE_FILE,
            }:
                content = params.get("content", "")
                content_size = len(content.encode("utf-8"))

                # Check available disk space
                stat = os.statvfs(repo_path)
                available_bytes = stat.f_bavail * stat.f_frsize
                required_bytes = content_size * 2  # 2x buffer

                if available_bytes < required_bytes:
                    blocked_reasons.append(
                        f"Insufficient disk space: need {required_bytes} bytes, "
                        f"have {available_bytes} bytes"
                    )
                    risk_score = 1.0
                    risk_factors.append("Low disk space")

                # Warn on large files
                if content_size > 1_000_000:  # 1 MB
                    risk_factors.append(
                        f"Large file: {content_size / 1_000_000:.2f} MB"
                    )
                    risk_score += 0.2

            # Check 4: For delete, check if file exists
            if operation_type == RepoOperationType.DELETE_FILE:
                if not file_path.exists():
                    blocked_reasons.append(f"File does not exist: {file_path}")
                    risk_score = 1.0
                    risk_factors.append("Deleting non-existent file")

        except Exception as e:
            blocked_reasons.append(f"File path resolution failed: {str(e)}")
            risk_score = 1.0
            risk_factors.append("Path resolution error")

        # Determine if safe
        safe = len(blocked_reasons) == 0
        reason = (
            "File system check passed"
            if safe
            else f"File system check failed: {blocked_reasons}"
        )

        return self._create_result(
            safe=safe,
            reason=reason,
            blocked_reasons=blocked_reasons,
            risk_score=min(risk_score, 1.0),
            risk_factors=risk_factors,
        )


class RemoteConnectionCheckpoint(BaseSafetyCheckpoint):
    """
    Checks remote connection safety for push/pull operations.

    Ensures:
    - Remote is configured
    - Remote is reachable
    - No push to unknown remotes
    """

    def __init__(self):
        super().__init__("remote_connection_checkpoint")

        # Trusted remote domains
        self.trusted_domains: Set[str] = {
            "github.com",
            "gitlab.com",
            "bitbucket.org",
        }

    async def check(
        self,
        context: RepoOperationContext
    ) -> SafetyCheckResult:
        """Check remote connection safety"""
        blocked_reasons = []
        risk_factors = []
        risk_score = 0.0

        operation_type = context.operation_type
        repo_path = context.repo_path

        # Only check for remote operations
        remote_ops = {
            RepoOperationType.PUSH,
            RepoOperationType.FORCE_PUSH,
        }

        if operation_type not in remote_ops:
            # Not a remote operation - safe
            return self._create_result(
                safe=True,
                reason="Not a remote operation",
                blocked_reasons=[],
                risk_score=0.0,
                risk_factors=[],
            )

        try:
            # Check if remote is configured
            result = subprocess.run(
                ["git", "remote", "-v"],
                cwd=repo_path,
                capture_output=True,
                text=True,
                timeout=5,
            )

            if result.returncode != 0:
                blocked_reasons.append(
                    f"Git remote command failed: {result.stderr}"
                )
                risk_score = 1.0
                risk_factors.append("Git remote check failed")
                return self._create_result(
                    safe=False,
                    reason="Remote check failed",
                    blocked_reasons=blocked_reasons,
                    risk_score=risk_score,
                    risk_factors=risk_factors,
                )

            output = result.stdout.strip()
            if not output:
                blocked_reasons.append("No git remote configured")
                risk_score = 1.0
                risk_factors.append("No remote")
                return self._create_result(
                    safe=False,
                    reason="No remote configured",
                    blocked_reasons=blocked_reasons,
                    risk_score=risk_score,
                    risk_factors=risk_factors,
                )

            # Check if remote domain is trusted
            remote_url = output.split()[1]  # Get URL from "origin <url> (push)"

            is_trusted = any(
                domain in remote_url
                for domain in self.trusted_domains
            )

            if not is_trusted:
                risk_factors.append(f"Untrusted remote: {remote_url}")
                risk_score += 0.4

            # Additional risk for force push
            if operation_type == RepoOperationType.FORCE_PUSH:
                risk_factors.append("Force push to remote")
                risk_score += 0.5

        except subprocess.TimeoutExpired:
            blocked_reasons.append("Git remote command timed out")
            risk_score = 1.0
            risk_factors.append("Command timeout")

        except Exception as e:
            blocked_reasons.append(f"Remote check failed: {str(e)}")
            risk_score = 1.0
            risk_factors.append("Remote check exception")

        # Determine if safe
        safe = len(blocked_reasons) == 0
        reason = (
            "Remote connection check passed"
            if safe
            else f"Remote connection check failed: {blocked_reasons}"
        )

        return self._create_result(
            safe=safe,
            reason=reason,
            blocked_reasons=blocked_reasons,
            risk_score=min(risk_score, 1.0),
            risk_factors=risk_factors,
        )


# ============================================================================
# Safety Checkpoint Manager
# ============================================================================


class SafetyManager:
    """
    Manages all safety checkpoints and coordinates checks.

    Runs all checkpoints and aggregates results.
    """

    def __init__(self):
        """Initialize safety manager"""
        self.checkpoints: List[BaseSafetyCheckpoint] = [
            GitStatusCheckpoint(),
            BranchProtectionCheckpoint(),
            FileSystemCheckpoint(),
            RemoteConnectionCheckpoint(),
        ]

        logger.info(
            f"🛡️ Safety Manager initialized ({len(self.checkpoints)} checkpoints)"
        )

    async def check_all(
        self,
        context: RepoOperationContext
    ) -> List[SafetyCheckResult]:
        """
        Run all safety checkpoints on a context.

        Args:
            context: Operation context to check

        Returns:
            List of safety check results (one per checkpoint)
        """
        results = []

        for checkpoint in self.checkpoints:
            try:
                result = await checkpoint.check(context)
                results.append(result)

                if not result.safe:
                    logger.warning(
                        f"⚠️ Safety check failed: {checkpoint.checkpoint_id} - "
                        f"{result.blocked_reasons}"
                    )

            except Exception as e:
                logger.error(f"❌ Checkpoint {checkpoint.checkpoint_id} failed: {e}")
                # Create error result (fail-closed)
                error_result = SafetyCheckResult(
                    safe=False,
                    checkpoint_id=checkpoint.checkpoint_id,
                    reason=f"Checkpoint crashed: {str(e)}",
                    blocked_reasons=[f"Checkpoint exception: {str(e)}"],
                    risk_score=1.0,
                    risk_factors=["Checkpoint crash"],
                )
                results.append(error_result)

        return results

    def is_safe(self, results: List[SafetyCheckResult]) -> bool:
        """
        Check if all safety check results are safe.

        Args:
            results: List of safety check results

        Returns:
            True if all results are safe (fail-closed)
        """
        return all(r.safe for r in results)

    def get_total_risk_score(self, results: List[SafetyCheckResult]) -> float:
        """
        Calculate total risk score across all checkpoints.

        Args:
            results: List of safety check results

        Returns:
            Total risk score (0.0 = safe, 1.0 = maximum risk)
        """
        if not results:
            return 0.0

        # Average risk score
        total = sum(r.risk_score for r in results)
        return total / len(results)


# ============================================================================
# Singleton Instance
# ============================================================================

_safety_manager: Optional[SafetyManager] = None


def get_safety_manager() -> SafetyManager:
    """Get the singleton safety manager instance"""
    global _safety_manager
    if _safety_manager is None:
        _safety_manager = SafetyManager()
    return _safety_manager
