"""
Example: OAuth 2.0 Client

This example demonstrates OAuth 2.0 authentication with automatic
token refresh.
"""

import asyncio
from typing import List, Dict, Any

from backend.app.modules.integrations import (
    BaseAPIClient,
    APIClientConfig,
    AuthConfig,
    AuthType,
    RateLimitConfig,
    RetryConfig,
)


class GitHubClient(BaseAPIClient):
    """
    Example GitHub API client using OAuth 2.0.

    Note: This is a simplified example. For production use with GitHub,
    you would need to implement the full OAuth flow (authorization code,
    callback handling, etc.).
    """

    async def _build_base_url(self) -> str:
        """Return GitHub API base URL."""
        return "https://api.github.com"

    async def get_user(self) -> Dict[str, Any]:
        """
        Get authenticated user information.

        Returns:
            User data
        """
        response = await self.get("/user")
        return response.body

    async def list_repos(
        self,
        per_page: int = 30,
        sort: str = "updated",
    ) -> List[Dict[str, Any]]:
        """
        List repositories for authenticated user.

        Args:
            per_page: Number of repos per page
            sort: Sort order (created, updated, pushed, full_name)

        Returns:
            List of repositories
        """
        response = await self.get(
            "/user/repos",
            params={
                "per_page": per_page,
                "sort": sort,
            },
        )
        return response.body

    async def get_repo(self, owner: str, repo: str) -> Dict[str, Any]:
        """
        Get repository information.

        Args:
            owner: Repository owner
            repo: Repository name

        Returns:
            Repository data
        """
        response = await self.get(f"/repos/{owner}/{repo}")
        return response.body

    async def create_issue(
        self,
        owner: str,
        repo: str,
        title: str,
        body: str,
        labels: List[str] = None,
    ) -> Dict[str, Any]:
        """
        Create an issue in a repository.

        Args:
            owner: Repository owner
            repo: Repository name
            title: Issue title
            body: Issue body
            labels: Issue labels

        Returns:
            Created issue data
        """
        response = await self.post(
            f"/repos/{owner}/{repo}/issues",
            json={
                "title": title,
                "body": body,
                "labels": labels or [],
            },
        )
        return response.body


class SpotifyClient(BaseAPIClient):
    """
    Example Spotify API client using OAuth 2.0 Client Credentials flow.

    This demonstrates automatic token refresh using client credentials.
    """

    async def _build_base_url(self) -> str:
        """Return Spotify API base URL."""
        return "https://api.spotify.com/v1"

    async def search(
        self,
        query: str,
        search_type: str = "track",
        limit: int = 10,
    ) -> Dict[str, Any]:
        """
        Search for tracks, artists, albums, or playlists.

        Args:
            query: Search query
            search_type: Type to search (track, artist, album, playlist)
            limit: Number of results

        Returns:
            Search results
        """
        response = await self.get(
            "/search",
            params={
                "q": query,
                "type": search_type,
                "limit": limit,
            },
        )
        return response.body

    async def get_track(self, track_id: str) -> Dict[str, Any]:
        """
        Get track information.

        Args:
            track_id: Spotify track ID

        Returns:
            Track data
        """
        response = await self.get(f"/tracks/{track_id}")
        return response.body


async def example_github():
    """Example: GitHub API with personal access token (acts like OAuth)."""

    # Configure GitHub client
    # Note: In production, you would use actual OAuth 2.0 flow
    config = APIClientConfig(
        name="github",
        base_url="https://api.github.com",
        # Use bearer token auth (GitHub personal access token)
        auth=AuthConfig(
            type=AuthType.BEARER,
            token="ghp_your_token_here",  # Replace with actual token
        ),
        # GitHub rate limits
        rate_limit=RateLimitConfig(
            max_requests=60,
            window_seconds=60.0,
            respect_retry_after=True,
        ),
        # Retry configuration
        retry=RetryConfig(
            max_retries=3,
            initial_delay=1.0,
        ),
        # Default headers
        default_headers={
            "Accept": "application/vnd.github.v3+json",
        },
    )

    client = GitHubClient(config)

    try:
        # Get authenticated user
        print("Getting user info...")
        user = await client.get_user()
        print(f"Logged in as: {user['login']}")

        # List repos
        print("\nListing repositories...")
        repos = await client.list_repos(per_page=5)
        for repo in repos:
            print(f"  - {repo['full_name']} ({repo['stargazers_count']} stars)")

        # Get specific repo
        print("\nGetting repo details...")
        repo = await client.get_repo("octocat", "Hello-World")
        print(f"Repo: {repo['full_name']}")
        print(f"Description: {repo['description']}")

    finally:
        await client.close()


async def example_spotify():
    """Example: Spotify API with OAuth 2.0 Client Credentials."""

    # Configure Spotify client with OAuth 2.0
    config = APIClientConfig(
        name="spotify",
        base_url="https://api.spotify.com/v1",
        # OAuth 2.0 client credentials flow
        auth=AuthConfig(
            type=AuthType.OAUTH2,
            client_id="your_client_id",  # Replace with actual credentials
            client_secret="your_client_secret",
            token_url="https://accounts.spotify.com/api/token",
        ),
        # Spotify rate limits
        rate_limit=RateLimitConfig(
            max_requests=100,
            window_seconds=60.0,
        ),
        # Retry configuration
        retry=RetryConfig(
            max_retries=3,
            initial_delay=1.0,
        ),
    )

    client = SpotifyClient(config)

    try:
        # Get initial OAuth token (client credentials flow)
        if client.auth_manager:
            await client.auth_manager.get_initial_token()
            print("OAuth token obtained successfully")

        # Search for tracks
        print("\nSearching for tracks...")
        results = await client.search(query="BRAiN", search_type="track", limit=5)

        if "tracks" in results and results["tracks"]["items"]:
            print("Found tracks:")
            for track in results["tracks"]["items"]:
                print(f"  - {track['name']} by {track['artists'][0]['name']}")

        # The auth manager will automatically refresh the token when it expires!

    finally:
        await client.close()


async def main():
    """Run examples."""
    print("=" * 60)
    print("OAuth 2.0 Examples")
    print("=" * 60)

    print("\n" + "=" * 60)
    print("Example 1: GitHub API (Bearer Token)")
    print("=" * 60)
    # Note: Uncomment and add real token to test
    # await example_github()
    print("Skipped (requires GitHub token)")

    print("\n" + "=" * 60)
    print("Example 2: Spotify API (OAuth 2.0 Client Credentials)")
    print("=" * 60)
    # Note: Uncomment and add real credentials to test
    # await example_spotify()
    print("Skipped (requires Spotify credentials)")

    print("\nTo run these examples:")
    print("1. Replace 'your_token_here' with actual GitHub token")
    print("2. Replace Spotify client_id and client_secret")
    print("3. Uncomment the await lines above")


if __name__ == "__main__":
    asyncio.run(main())
