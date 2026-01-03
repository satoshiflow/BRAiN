"""
Example: Simple REST API Client

This example shows how to create a basic REST API client using the
BaseAPIClient framework.
"""

import asyncio
from typing import List, Dict, Any

from app.modules.integrations import (
    BaseAPIClient,
    APIClientConfig,
    AuthConfig,
    AuthType,
    RateLimitConfig,
    RetryConfig,
)


class JSONPlaceholderClient(BaseAPIClient):
    """
    Example client for JSONPlaceholder API (https://jsonplaceholder.typicode.com).

    This is a free fake REST API for testing and prototyping.
    """

    async def _build_base_url(self) -> str:
        """Return the base URL for JSONPlaceholder API."""
        return "https://jsonplaceholder.typicode.com"

    async def get_posts(self, limit: int = 10) -> List[Dict[str, Any]]:
        """
        Get list of posts.

        Args:
            limit: Maximum number of posts to return

        Returns:
            List of posts
        """
        response = await self.get("/posts", params={"_limit": limit})
        return response.body

    async def get_post(self, post_id: int) -> Dict[str, Any]:
        """
        Get a specific post by ID.

        Args:
            post_id: Post ID

        Returns:
            Post data
        """
        response = await self.get(f"/posts/{post_id}")
        return response.body

    async def create_post(
        self,
        title: str,
        body: str,
        user_id: int = 1,
    ) -> Dict[str, Any]:
        """
        Create a new post.

        Args:
            title: Post title
            body: Post content
            user_id: User ID

        Returns:
            Created post data
        """
        response = await self.post(
            "/posts",
            json={
                "title": title,
                "body": body,
                "userId": user_id,
            },
        )
        return response.body

    async def update_post(
        self,
        post_id: int,
        title: str,
        body: str,
    ) -> Dict[str, Any]:
        """
        Update an existing post.

        Args:
            post_id: Post ID
            title: New title
            body: New content

        Returns:
            Updated post data
        """
        response = await self.put(
            f"/posts/{post_id}",
            json={
                "title": title,
                "body": body,
            },
        )
        return response.body

    async def delete_post(self, post_id: int) -> None:
        """
        Delete a post.

        Args:
            post_id: Post ID
        """
        await self.delete(f"/posts/{post_id}")


async def main():
    """Example usage of JSONPlaceholder client."""

    # Configure client with rate limiting and retries
    config = APIClientConfig(
        name="jsonplaceholder",
        base_url="https://jsonplaceholder.typicode.com",
        # No authentication needed for this public API
        auth=AuthConfig(type=AuthType.NONE),
        # Rate limit: 10 requests per second
        rate_limit=RateLimitConfig(
            max_requests=10,
            window_seconds=1.0,
        ),
        # Retry failed requests up to 3 times
        retry=RetryConfig(
            max_retries=3,
            initial_delay=1.0,
        ),
        # Logging
        log_requests=True,
        log_responses=True,
    )

    # Create client
    client = JSONPlaceholderClient(config)

    try:
        # Get posts
        print("Fetching posts...")
        posts = await client.get_posts(limit=5)
        print(f"Got {len(posts)} posts")
        for post in posts[:2]:
            print(f"  - [{post['id']}] {post['title']}")

        # Get specific post
        print("\nFetching post #1...")
        post = await client.get_post(1)
        print(f"Post title: {post['title']}")

        # Create post
        print("\nCreating new post...")
        new_post = await client.create_post(
            title="BRAiN Integration Test",
            body="Testing the Generic API Client Framework",
        )
        print(f"Created post: {new_post}")

        # Update post
        print("\nUpdating post...")
        updated_post = await client.update_post(
            post_id=1,
            title="Updated Title",
            body="Updated content",
        )
        print(f"Updated post: {updated_post}")

        # Delete post
        print("\nDeleting post...")
        await client.delete_post(1)
        print("Post deleted successfully")

        # Get metrics
        print("\nClient Metrics:")
        metrics = client.get_metrics()
        print(f"  Total requests: {metrics.total_requests}")
        print(f"  Successful: {metrics.successful_requests}")
        print(f"  Failed: {metrics.failed_requests}")
        print(f"  Average response time: {metrics.average_response_time_ms:.2f}ms")

    finally:
        # Clean up
        await client.close()


if __name__ == "__main__":
    asyncio.run(main())
