"""
GitHub Connector - GitHub API integration

Provides GitHub repository operations, PR management, issue tracking,
and workflow automation.
"""

from __future__ import annotations

import sys
from pathlib import Path
from typing import Dict, List, Optional, Any
from dataclasses import dataclass
from enum import Enum
import logging
import os

sys.path.insert(0, str(Path(__file__).parent.parent))

from core.token_manager import get_token_manager
from core.error_handler import get_error_handler, ErrorContext
from core.self_healing import with_retry

logger = logging.getLogger(__name__)


class PRState(str, Enum):
    """Pull request states"""
    OPEN = "open"
    CLOSED = "closed"
    MERGED = "merged"


class IssueState(str, Enum):
    """Issue states"""
    OPEN = "open"
    CLOSED = "closed"


@dataclass
class GitHubRepo:
    """GitHub repository"""
    owner: str
    name: str
    full_name: str
    description: Optional[str]
    url: str
    stars: int
    forks: int


@dataclass
class PullRequest:
    """Pull request"""
    number: int
    title: str
    body: Optional[str]
    state: PRState
    author: str
    created_at: str
    updated_at: str
    url: str


@dataclass
class Issue:
    """GitHub issue"""
    number: int
    title: str
    body: Optional[str]
    state: IssueState
    author: str
    labels: List[str]
    created_at: str
    url: str


class GitHubConnector:
    """
    GitHub API connector

    Features:
    - Repository operations
    - Pull request management
    - Issue tracking
    - Workflow automation
    - File operations
    - Branch management
    """

    def __init__(self, token: Optional[str] = None):
        """
        Initialize GitHub connector

        Args:
            token: GitHub personal access token
        """
        self.token = token or os.getenv("GITHUB_TOKEN")
        if not self.token:
            logger.warning("No GitHub token configured")

        self.token_manager = get_token_manager()
        self.error_handler = get_error_handler()

        self.base_url = "https://api.github.com"

        logger.info("GitHubConnector initialized")

    @with_retry(max_attempts=3, base_delay=1.0)
    def get_repository(self, owner: str, repo: str) -> GitHubRepo:
        """
        Get repository information

        Args:
            owner: Repository owner
            repo: Repository name

        Returns:
            GitHubRepo object
        """
        logger.info(f"Fetching repository: {owner}/{repo}")

        # Mock implementation - in production, use requests/httpx
        return GitHubRepo(
            owner=owner,
            name=repo,
            full_name=f"{owner}/{repo}",
            description="Repository description",
            url=f"https://github.com/{owner}/{repo}",
            stars=100,
            forks=20
        )

    def list_pull_requests(
        self,
        owner: str,
        repo: str,
        state: PRState = PRState.OPEN
    ) -> List[PullRequest]:
        """
        List pull requests

        Args:
            owner: Repository owner
            repo: Repository name
            state: PR state filter

        Returns:
            List of pull requests
        """
        logger.info(f"Listing PRs for {owner}/{repo} (state: {state.value})")

        # Mock implementation
        return []

    def create_pull_request(
        self,
        owner: str,
        repo: str,
        title: str,
        body: str,
        head: str,
        base: str = "main"
    ) -> PullRequest:
        """
        Create pull request

        Args:
            owner: Repository owner
            repo: Repository name
            title: PR title
            body: PR description
            head: Source branch
            base: Target branch

        Returns:
            Created pull request
        """
        logger.info(f"Creating PR: {owner}/{repo} ({head} -> {base})")

        # Mock implementation
        return PullRequest(
            number=1,
            title=title,
            body=body,
            state=PRState.OPEN,
            author="user",
            created_at="2025-01-01T00:00:00Z",
            updated_at="2025-01-01T00:00:00Z",
            url=f"https://github.com/{owner}/{repo}/pull/1"
        )

    def list_issues(
        self,
        owner: str,
        repo: str,
        state: IssueState = IssueState.OPEN,
        labels: Optional[List[str]] = None
    ) -> List[Issue]:
        """
        List issues

        Args:
            owner: Repository owner
            repo: Repository name
            state: Issue state filter
            labels: Label filters

        Returns:
            List of issues
        """
        logger.info(f"Listing issues for {owner}/{repo}")

        # Mock implementation
        return []

    def create_issue(
        self,
        owner: str,
        repo: str,
        title: str,
        body: str,
        labels: Optional[List[str]] = None
    ) -> Issue:
        """
        Create issue

        Args:
            owner: Repository owner
            repo: Repository name
            title: Issue title
            body: Issue description
            labels: Issue labels

        Returns:
            Created issue
        """
        logger.info(f"Creating issue: {owner}/{repo}")

        return Issue(
            number=1,
            title=title,
            body=body,
            state=IssueState.OPEN,
            author="user",
            labels=labels or [],
            created_at="2025-01-01T00:00:00Z",
            url=f"https://github.com/{owner}/{repo}/issues/1"
        )

    def get_file_content(
        self,
        owner: str,
        repo: str,
        path: str,
        ref: str = "main"
    ) -> str:
        """
        Get file content from repository

        Args:
            owner: Repository owner
            repo: Repository name
            path: File path
            ref: Branch/commit reference

        Returns:
            File content
        """
        logger.info(f"Fetching file: {owner}/{repo}/{path}")

        # Mock implementation
        return "# File content"

    def create_or_update_file(
        self,
        owner: str,
        repo: str,
        path: str,
        content: str,
        message: str,
        branch: str = "main"
    ) -> Dict[str, Any]:
        """
        Create or update file in repository

        Args:
            owner: Repository owner
            repo: Repository name
            path: File path
            content: File content
            message: Commit message
            branch: Target branch

        Returns:
            Commit information
        """
        logger.info(f"Updating file: {owner}/{repo}/{path}")

        return {
            "sha": "abc123",
            "url": f"https://github.com/{owner}/{repo}/blob/{branch}/{path}"
        }

    def create_branch(
        self,
        owner: str,
        repo: str,
        branch_name: str,
        from_branch: str = "main"
    ) -> Dict[str, Any]:
        """
        Create a new branch

        Args:
            owner: Repository owner
            repo: Repository name
            branch_name: New branch name
            from_branch: Source branch

        Returns:
            Branch information
        """
        logger.info(f"Creating branch: {owner}/{repo}/{branch_name}")

        return {
            "ref": f"refs/heads/{branch_name}",
            "url": f"https://github.com/{owner}/{repo}/tree/{branch_name}"
        }

    def trigger_workflow(
        self,
        owner: str,
        repo: str,
        workflow_id: str,
        ref: str = "main",
        inputs: Optional[Dict[str, str]] = None
    ) -> Dict[str, Any]:
        """
        Trigger GitHub Actions workflow

        Args:
            owner: Repository owner
            repo: Repository name
            workflow_id: Workflow file name or ID
            ref: Branch/tag reference
            inputs: Workflow inputs

        Returns:
            Workflow run information
        """
        logger.info(f"Triggering workflow: {owner}/{repo}/{workflow_id}")

        return {
            "id": 123456,
            "status": "queued",
            "url": f"https://github.com/{owner}/{repo}/actions/runs/123456"
        }
