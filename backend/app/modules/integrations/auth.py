"""
Authentication manager for API clients.

Supports multiple authentication types:
- API Key (header/query)
- Bearer Token
- Basic Authentication
- OAuth 2.0 (with automatic token refresh)
- Custom authentication schemes

Handles credential management, token refresh, and multi-tenant scenarios.
"""

from __future__ import annotations

import asyncio
import base64
from datetime import datetime, timezone, timedelta
from typing import Dict, Optional, Any
from loguru import logger
import httpx

from .schemas import AuthConfig, AuthType, AuthLocation
from .exceptions import AuthenticationError, ConfigurationError


class AuthenticationManager:
    """
    Manages authentication for API clients.

    Handles different authentication types and automatically refreshes
    tokens when needed (OAuth 2.0).
    """

    def __init__(self, config: AuthConfig) -> None:
        """
        Initialize authentication manager.

        Args:
            config: Authentication configuration

        Raises:
            ConfigurationError: If configuration is invalid
        """
        self.config = config
        self._validate_config()

        # OAuth 2.0 state
        self._token_refresh_lock = asyncio.Lock()
        self._is_refreshing = False

        logger.debug(
            "AuthenticationManager initialized: type={auth_type}",
            auth_type=config.type,
        )

    def _validate_config(self) -> None:
        """
        Validate authentication configuration.

        Raises:
            ConfigurationError: If configuration is invalid
        """
        if self.config.type == AuthType.API_KEY:
            if not self.config.token:
                raise ConfigurationError("API key authentication requires 'token'")

        elif self.config.type == AuthType.BEARER:
            if not self.config.token:
                raise ConfigurationError("Bearer authentication requires 'token'")

        elif self.config.type == AuthType.BASIC:
            if not self.config.username or not self.config.password:
                raise ConfigurationError(
                    "Basic authentication requires 'username' and 'password'"
                )

        elif self.config.type == AuthType.OAUTH2:
            if not self.config.client_id or not self.config.client_secret:
                raise ConfigurationError(
                    "OAuth 2.0 requires 'client_id' and 'client_secret'"
                )
            if not self.config.token_url:
                raise ConfigurationError("OAuth 2.0 requires 'token_url'")

    async def apply_auth(
        self,
        headers: Dict[str, str],
        params: Dict[str, Any],
    ) -> tuple[Dict[str, str], Dict[str, Any]]:
        """
        Apply authentication to request headers/params.

        Args:
            headers: Request headers (will be modified)
            params: Request query parameters (will be modified)

        Returns:
            Tuple of (headers, params) with auth applied

        Raises:
            AuthenticationError: If authentication fails
        """
        if self.config.type == AuthType.NONE:
            return headers, params

        elif self.config.type == AuthType.API_KEY:
            return self._apply_api_key(headers, params)

        elif self.config.type == AuthType.BEARER:
            return self._apply_bearer(headers, params)

        elif self.config.type == AuthType.BASIC:
            return self._apply_basic(headers, params)

        elif self.config.type == AuthType.OAUTH2:
            return await self._apply_oauth2(headers, params)

        elif self.config.type == AuthType.CUSTOM:
            return self._apply_custom(headers, params)

        else:
            raise AuthenticationError(f"Unknown auth type: {self.config.type}")

    def _apply_api_key(
        self,
        headers: Dict[str, str],
        params: Dict[str, Any],
    ) -> tuple[Dict[str, str], Dict[str, Any]]:
        """Apply API key authentication."""
        if not self.config.token:
            raise AuthenticationError("API key not configured")

        # Build token value with prefix if configured
        token_value = self.config.token
        if self.config.token_prefix:
            token_value = f"{self.config.token_prefix} {token_value}"

        # Apply to header or query param
        if self.config.token_location == AuthLocation.HEADER:
            headers[self.config.token_key] = token_value
        elif self.config.token_location == AuthLocation.QUERY:
            params[self.config.token_key] = token_value

        return headers, params

    def _apply_bearer(
        self,
        headers: Dict[str, str],
        params: Dict[str, Any],
    ) -> tuple[Dict[str, str], Dict[str, Any]]:
        """Apply Bearer token authentication."""
        if not self.config.token:
            raise AuthenticationError("Bearer token not configured")

        # Bearer tokens always go in Authorization header
        headers["Authorization"] = f"Bearer {self.config.token}"

        return headers, params

    def _apply_basic(
        self,
        headers: Dict[str, str],
        params: Dict[str, Any],
    ) -> tuple[Dict[str, str], Dict[str, Any]]:
        """Apply Basic authentication."""
        if not self.config.username or not self.config.password:
            raise AuthenticationError("Username/password not configured")

        # Encode credentials
        credentials = f"{self.config.username}:{self.config.password}"
        encoded = base64.b64encode(credentials.encode()).decode()

        headers["Authorization"] = f"Basic {encoded}"

        return headers, params

    async def _apply_oauth2(
        self,
        headers: Dict[str, str],
        params: Dict[str, Any],
    ) -> tuple[Dict[str, str], Dict[str, Any]]:
        """
        Apply OAuth 2.0 authentication.

        Automatically refreshes token if expired.
        """
        # Check if we need to refresh the token
        if self._should_refresh_token():
            await self._refresh_access_token()

        # Apply access token
        if not self.config.access_token:
            raise AuthenticationError("OAuth 2.0 access token not available")

        headers["Authorization"] = f"Bearer {self.config.access_token}"

        return headers, params

    def _apply_custom(
        self,
        headers: Dict[str, str],
        params: Dict[str, Any],
    ) -> tuple[Dict[str, str], Dict[str, Any]]:
        """Apply custom authentication."""
        # Merge custom headers
        headers.update(self.config.custom_headers)

        # Merge custom params
        params.update(self.config.custom_params)

        return headers, params

    def _should_refresh_token(self) -> bool:
        """Check if OAuth 2.0 token should be refreshed."""
        if self.config.type != AuthType.OAUTH2:
            return False

        if not self.config.access_token:
            # No token yet, need to get one
            return True

        if not self.config.token_expires_at:
            # No expiration set, assume it's still valid
            return False

        # Check if token expires soon (within 5 minutes)
        now = datetime.now(timezone.utc)
        buffer = timedelta(minutes=5)

        return now + buffer >= self.config.token_expires_at

    async def _refresh_access_token(self) -> None:
        """
        Refresh OAuth 2.0 access token.

        Uses refresh_token if available, otherwise uses client_credentials flow.

        Raises:
            AuthenticationError: If token refresh fails
        """
        # Prevent concurrent refreshes
        async with self._token_refresh_lock:
            # Double-check if we still need to refresh (another request might have done it)
            if not self._should_refresh_token():
                return

            logger.info("Refreshing OAuth 2.0 access token")

            try:
                if self.config.refresh_token:
                    # Use refresh token flow
                    await self._refresh_with_refresh_token()
                else:
                    # Use client credentials flow
                    await self._refresh_with_client_credentials()

                logger.info("OAuth 2.0 access token refreshed successfully")

            except Exception as exc:
                logger.error(f"Failed to refresh OAuth 2.0 token: {exc}")
                raise AuthenticationError(
                    "Failed to refresh OAuth 2.0 token",
                    cause=exc,
                ) from exc

    async def _refresh_with_refresh_token(self) -> None:
        """Refresh token using refresh_token flow."""
        if not self.config.token_url:
            raise AuthenticationError("OAuth token URL not configured")

        data = {
            "grant_type": "refresh_token",
            "refresh_token": self.config.refresh_token,
            "client_id": self.config.client_id,
            "client_secret": self.config.client_secret,
        }

        async with httpx.AsyncClient() as client:
            response = await client.post(self.config.token_url, data=data)
            response.raise_for_status()

            token_data = response.json()

            # Update access token
            self.config.access_token = token_data["access_token"]

            # Update refresh token if provided
            if "refresh_token" in token_data:
                self.config.refresh_token = token_data["refresh_token"]

            # Calculate expiration
            if "expires_in" in token_data:
                expires_in = int(token_data["expires_in"])
                self.config.token_expires_at = datetime.now(timezone.utc) + timedelta(
                    seconds=expires_in
                )

    async def _refresh_with_client_credentials(self) -> None:
        """Refresh token using client_credentials flow."""
        if not self.config.token_url:
            raise AuthenticationError("OAuth token URL not configured")

        data = {
            "grant_type": "client_credentials",
            "client_id": self.config.client_id,
            "client_secret": self.config.client_secret,
        }

        # Add scopes if configured
        if self.config.scopes:
            data["scope"] = " ".join(self.config.scopes)

        async with httpx.AsyncClient() as client:
            response = await client.post(self.config.token_url, data=data)
            response.raise_for_status()

            token_data = response.json()

            # Update access token
            self.config.access_token = token_data["access_token"]

            # Calculate expiration
            if "expires_in" in token_data:
                expires_in = int(token_data["expires_in"])
                self.config.token_expires_at = datetime.now(timezone.utc) + timedelta(
                    seconds=expires_in
                )

    async def get_initial_token(self) -> None:
        """
        Get initial OAuth 2.0 token (if using client_credentials flow).

        For refresh_token flow, the refresh_token must be provided in config.

        Raises:
            AuthenticationError: If getting token fails
        """
        if self.config.type != AuthType.OAUTH2:
            return

        if self.config.access_token:
            # Already have a token
            return

        logger.info("Getting initial OAuth 2.0 access token")

        try:
            await self._refresh_with_client_credentials()
        except Exception as exc:
            logger.error(f"Failed to get initial OAuth 2.0 token: {exc}")
            raise AuthenticationError(
                "Failed to get initial OAuth 2.0 token",
                cause=exc,
            ) from exc

    def update_credentials(
        self,
        *,
        token: Optional[str] = None,
        username: Optional[str] = None,
        password: Optional[str] = None,
        access_token: Optional[str] = None,
        refresh_token: Optional[str] = None,
    ) -> None:
        """
        Update authentication credentials.

        Args:
            token: API key or bearer token
            username: Username for basic auth
            password: Password for basic auth
            access_token: OAuth 2.0 access token
            refresh_token: OAuth 2.0 refresh token
        """
        if token is not None:
            self.config.token = token

        if username is not None:
            self.config.username = username

        if password is not None:
            self.config.password = password

        if access_token is not None:
            self.config.access_token = access_token

        if refresh_token is not None:
            self.config.refresh_token = refresh_token

        logger.debug("Authentication credentials updated")


def create_api_key_auth(
    api_key: str,
    *,
    header_name: str = "X-API-Key",
    prefix: Optional[str] = None,
) -> AuthenticationManager:
    """
    Create API key authentication manager.

    Args:
        api_key: The API key
        header_name: Header name for API key (default: X-API-Key)
        prefix: Optional prefix (e.g., "Bearer")

    Returns:
        Configured AuthenticationManager
    """
    config = AuthConfig(
        type=AuthType.API_KEY,
        token=api_key,
        token_location=AuthLocation.HEADER,
        token_key=header_name,
        token_prefix=prefix,
    )

    return AuthenticationManager(config)


def create_bearer_auth(token: str) -> AuthenticationManager:
    """
    Create Bearer token authentication manager.

    Args:
        token: The bearer token

    Returns:
        Configured AuthenticationManager
    """
    config = AuthConfig(
        type=AuthType.BEARER,
        token=token,
    )

    return AuthenticationManager(config)


def create_basic_auth(username: str, password: str) -> AuthenticationManager:
    """
    Create Basic authentication manager.

    Args:
        username: Username
        password: Password

    Returns:
        Configured AuthenticationManager
    """
    config = AuthConfig(
        type=AuthType.BASIC,
        username=username,
        password=password,
    )

    return AuthenticationManager(config)


def create_oauth2_auth(
    client_id: str,
    client_secret: str,
    token_url: str,
    *,
    refresh_token: Optional[str] = None,
    scopes: Optional[list[str]] = None,
) -> AuthenticationManager:
    """
    Create OAuth 2.0 authentication manager.

    Args:
        client_id: OAuth client ID
        client_secret: OAuth client secret
        token_url: Token endpoint URL
        refresh_token: Optional refresh token
        scopes: Optional list of scopes

    Returns:
        Configured AuthenticationManager
    """
    config = AuthConfig(
        type=AuthType.OAUTH2,
        client_id=client_id,
        client_secret=client_secret,
        token_url=token_url,
        refresh_token=refresh_token,
        scopes=scopes or [],
    )

    return AuthenticationManager(config)
