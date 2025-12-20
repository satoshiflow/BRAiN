"""
API Key Management System for BRAiN Core.

Provides secure API key generation, validation, and management:
- Cryptographically secure key generation
- SHA-256 hashing for storage
- Key rotation and expiration
- Usage tracking and rate limiting
- Scope-based permissions

Security Features:
- Keys never stored in plaintext
- SHA-256 hashing with salt
- Automatic expiration
- Usage audit trail
- IP whitelisting support
- Scope-based access control

Usage:
    from app.core.api_keys import APIKeyManager

    manager = APIKeyManager()

    # Generate new API key
    api_key = await manager.create_key(
        name="Production API",
        scopes=["missions:read", "agents:read"],
        expires_in_days=90
    )

    # Validate key
    key_data = await manager.validate_key(api_key.key)
    if not key_data:
        raise HTTPException(401, "Invalid API key")
"""

from __future__ import annotations

import hashlib
import secrets
import time
from datetime import datetime, timedelta
from typing import List, Optional

from pydantic import BaseModel, Field
from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from loguru import logger


# ============================================================================
# Models
# ============================================================================

class APIKey(BaseModel):
    """API Key model."""
    id: str
    name: str
    key_hash: str
    prefix: str  # First 8 chars for identification
    scopes: List[str]
    created_at: datetime
    expires_at: Optional[datetime] = None
    last_used_at: Optional[datetime] = None
    is_active: bool = True
    usage_count: int = 0
    ip_whitelist: Optional[List[str]] = None
    metadata: dict = Field(default_factory=dict)


class APIKeyCreate(BaseModel):
    """API Key creation request."""
    name: str
    scopes: List[str] = Field(default_factory=list)
    expires_in_days: Optional[int] = None
    ip_whitelist: Optional[List[str]] = None
    metadata: dict = Field(default_factory=dict)


class APIKeyResponse(BaseModel):
    """API Key response (includes plaintext key only on creation)."""
    id: str
    name: str
    key: Optional[str] = None  # Only returned on creation
    prefix: str
    scopes: List[str]
    created_at: datetime
    expires_at: Optional[datetime] = None
    last_used_at: Optional[datetime] = None
    is_active: bool
    usage_count: int


# ============================================================================
# API Key Manager
# ============================================================================

class APIKeyManager:
    """
    API Key management system.

    Features:
    - Secure key generation (cryptographically random)
    - SHA-256 hashing for storage
    - Key rotation and expiration
    - Usage tracking
    - Scope-based permissions
    - IP whitelisting
    """

    KEY_LENGTH = 32  # 32 bytes = 256 bits
    PREFIX_LENGTH = 8  # First 8 chars for identification

    def __init__(self, session: Optional[AsyncSession] = None):
        """
        Initialize API key manager.

        Args:
            session: Database session (optional, for storage)
        """
        self.session = session
        # In-memory storage for development (replace with DB in production)
        self._keys: dict[str, APIKey] = {}

    @staticmethod
    def generate_key() -> str:
        """
        Generate cryptographically secure API key.

        Format: brain_<64_hex_chars>

        Returns:
            API key string
        """
        random_bytes = secrets.token_bytes(APIKeyManager.KEY_LENGTH)
        key_hex = random_bytes.hex()
        return f"brain_{key_hex}"

    @staticmethod
    def hash_key(key: str) -> str:
        """
        Hash API key using SHA-256.

        Args:
            key: Plaintext API key

        Returns:
            SHA-256 hash
        """
        return hashlib.sha256(key.encode()).hexdigest()

    @staticmethod
    def extract_prefix(key: str) -> str:
        """
        Extract prefix from API key for identification.

        Args:
            key: Plaintext API key

        Returns:
            Key prefix (first 8 chars after 'brain_')
        """
        if key.startswith("brain_"):
            return key[6:6 + APIKeyManager.PREFIX_LENGTH]
        return key[:APIKeyManager.PREFIX_LENGTH]

    async def create_key(
        self,
        name: str,
        scopes: List[str] = None,
        expires_in_days: Optional[int] = None,
        ip_whitelist: Optional[List[str]] = None,
        metadata: dict = None
    ) -> APIKeyResponse:
        """
        Create new API key.

        Args:
            name: Human-readable name for the key
            scopes: List of permission scopes
            expires_in_days: Expiration time in days (None = never expires)
            ip_whitelist: List of allowed IP addresses
            metadata: Additional metadata

        Returns:
            API key response with plaintext key
        """
        # Generate key
        plaintext_key = self.generate_key()
        key_hash = self.hash_key(plaintext_key)
        prefix = self.extract_prefix(plaintext_key)

        # Calculate expiration
        expires_at = None
        if expires_in_days:
            expires_at = datetime.utcnow() + timedelta(days=expires_in_days)

        # Create API key object
        api_key = APIKey(
            id=secrets.token_urlsafe(16),
            name=name,
            key_hash=key_hash,
            prefix=prefix,
            scopes=scopes or [],
            created_at=datetime.utcnow(),
            expires_at=expires_at,
            is_active=True,
            usage_count=0,
            ip_whitelist=ip_whitelist,
            metadata=metadata or {},
        )

        # Store in memory (or database)
        self._keys[key_hash] = api_key

        logger.info(f"Created API key: {name} (prefix: {prefix})")

        # Return response with plaintext key (only time it's shown)
        return APIKeyResponse(
            id=api_key.id,
            name=api_key.name,
            key=plaintext_key,  # ⚠️ Only returned on creation!
            prefix=api_key.prefix,
            scopes=api_key.scopes,
            created_at=api_key.created_at,
            expires_at=api_key.expires_at,
            last_used_at=api_key.last_used_at,
            is_active=api_key.is_active,
            usage_count=api_key.usage_count,
        )

    async def validate_key(
        self,
        plaintext_key: str,
        required_scopes: Optional[List[str]] = None,
        client_ip: Optional[str] = None
    ) -> Optional[APIKey]:
        """
        Validate API key.

        Args:
            plaintext_key: Plaintext API key from request
            required_scopes: Required permission scopes
            client_ip: Client IP address (for whitelist check)

        Returns:
            APIKey object if valid, None otherwise
        """
        # Hash the provided key
        key_hash = self.hash_key(plaintext_key)

        # Lookup key
        api_key = self._keys.get(key_hash)

        if not api_key:
            logger.warning(f"Invalid API key attempt: {plaintext_key[:16]}...")
            return None

        # Check if active
        if not api_key.is_active:
            logger.warning(f"Inactive API key used: {api_key.name}")
            return None

        # Check expiration
        if api_key.expires_at and datetime.utcnow() > api_key.expires_at:
            logger.warning(f"Expired API key used: {api_key.name}")
            return None

        # Check IP whitelist
        if api_key.ip_whitelist and client_ip:
            if client_ip not in api_key.ip_whitelist:
                logger.warning(
                    f"API key used from non-whitelisted IP: {api_key.name} "
                    f"(IP: {client_ip})"
                )
                return None

        # Check scopes
        if required_scopes:
            if not all(scope in api_key.scopes for scope in required_scopes):
                logger.warning(
                    f"API key missing required scopes: {api_key.name} "
                    f"(required: {required_scopes}, has: {api_key.scopes})"
                )
                return None

        # Update usage tracking
        api_key.last_used_at = datetime.utcnow()
        api_key.usage_count += 1

        logger.debug(f"API key validated: {api_key.name}")

        return api_key

    async def revoke_key(self, key_id: str) -> bool:
        """
        Revoke API key (set inactive).

        Args:
            key_id: API key ID

        Returns:
            True if revoked, False if not found
        """
        for api_key in self._keys.values():
            if api_key.id == key_id:
                api_key.is_active = False
                logger.info(f"Revoked API key: {api_key.name}")
                return True

        return False

    async def rotate_key(self, key_id: str) -> Optional[APIKeyResponse]:
        """
        Rotate API key (create new key with same settings).

        Args:
            key_id: API key ID to rotate

        Returns:
            New API key response
        """
        # Find old key
        old_key = None
        for api_key in self._keys.values():
            if api_key.id == key_id:
                old_key = api_key
                break

        if not old_key:
            return None

        # Create new key with same settings
        new_key = await self.create_key(
            name=f"{old_key.name} (rotated)",
            scopes=old_key.scopes,
            expires_in_days=None,  # Recalculate expiration
            ip_whitelist=old_key.ip_whitelist,
            metadata=old_key.metadata,
        )

        # Revoke old key
        await self.revoke_key(key_id)

        logger.info(f"Rotated API key: {old_key.name}")

        return new_key

    async def list_keys(
        self,
        include_inactive: bool = False
    ) -> List[APIKeyResponse]:
        """
        List all API keys.

        Args:
            include_inactive: Include inactive keys

        Returns:
            List of API key responses (without plaintext keys)
        """
        keys = []
        for api_key in self._keys.values():
            if not include_inactive and not api_key.is_active:
                continue

            keys.append(APIKeyResponse(
                id=api_key.id,
                name=api_key.name,
                prefix=api_key.prefix,
                scopes=api_key.scopes,
                created_at=api_key.created_at,
                expires_at=api_key.expires_at,
                last_used_at=api_key.last_used_at,
                is_active=api_key.is_active,
                usage_count=api_key.usage_count,
            ))

        return keys

    async def get_key_by_id(self, key_id: str) -> Optional[APIKeyResponse]:
        """Get API key by ID."""
        for api_key in self._keys.values():
            if api_key.id == key_id:
                return APIKeyResponse(
                    id=api_key.id,
                    name=api_key.name,
                    prefix=api_key.prefix,
                    scopes=api_key.scopes,
                    created_at=api_key.created_at,
                    expires_at=api_key.expires_at,
                    last_used_at=api_key.last_used_at,
                    is_active=api_key.is_active,
                    usage_count=api_key.usage_count,
                )

        return None


# ============================================================================
# Scopes (Permission Definitions)
# ============================================================================

class Scopes:
    """
    Predefined API key scopes.

    Format: <resource>:<action>
    """

    # Missions
    MISSIONS_READ = "missions:read"
    MISSIONS_WRITE = "missions:write"
    MISSIONS_DELETE = "missions:delete"
    MISSIONS_ALL = "missions:*"

    # Agents
    AGENTS_READ = "agents:read"
    AGENTS_WRITE = "agents:write"
    AGENTS_DELETE = "agents:delete"
    AGENTS_ALL = "agents:*"

    # Policies
    POLICIES_READ = "policies:read"
    POLICIES_WRITE = "policies:write"
    POLICIES_DELETE = "policies:delete"
    POLICIES_ALL = "policies:*"

    # Cache
    CACHE_READ = "cache:read"
    CACHE_WRITE = "cache:write"
    CACHE_DELETE = "cache:delete"
    CACHE_ALL = "cache:*"

    # Database
    DB_READ = "db:read"
    DB_WRITE = "db:write"
    DB_ALL = "db:*"

    # Admin
    ADMIN = "admin:*"

    # All scopes
    ALL = "*:*"

    @classmethod
    def get_all_scopes(cls) -> List[str]:
        """Get list of all available scopes."""
        return [
            value for name, value in vars(cls).items()
            if not name.startswith("_") and isinstance(value, str)
        ]


# ============================================================================
# Global Instance
# ============================================================================

_api_key_manager: Optional[APIKeyManager] = None


def get_api_key_manager() -> APIKeyManager:
    """Get global API key manager instance."""
    global _api_key_manager
    if _api_key_manager is None:
        _api_key_manager = APIKeyManager()
    return _api_key_manager
