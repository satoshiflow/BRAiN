"""
Trusted Keyring - Ed25519 Public Key Management

Manages the registry of trusted public keys for bundle signature verification.
Part of G1 - Bundle Signing & Trusted Origin governance implementation.
"""

import json
from pathlib import Path
from typing import Dict, List, Optional
from datetime import datetime
from threading import RLock
from pydantic import BaseModel, Field
from loguru import logger

from app.modules.sovereign_mode.crypto import (
    import_public_key_pem,
    import_public_key_hex,
    export_public_key_pem,
    export_public_key_hex,
    KeyImportError,
)
from cryptography.hazmat.primitives.asymmetric import ed25519


class TrustLevel(str):
    """Trust level constants."""

    FULL = "full"  # Fully trusted - can sign any bundle
    LIMITED = "limited"  # Limited trust - require additional validation
    REVOKED = "revoked"  # Key revoked - do not trust


class KeyOrigin(str):
    """Key origin constants."""

    SYSTEM = "system"  # System-generated key (BRAiN internal)
    OWNER = "owner"  # Owner-provided key (manual import)
    EXTERNAL = "external"  # External provider key (third-party)


class TrustedKey(BaseModel):
    """Trusted public key entry."""

    key_id: str = Field(..., description="Unique key identifier")
    public_key_pem: str = Field(..., description="PEM-encoded Ed25519 public key")
    public_key_hex: str = Field(..., description="Hex-encoded public key (64 chars)")

    origin: str = Field(..., description="Key origin (system/owner/external)")
    trust_level: str = Field(default=TrustLevel.FULL, description="Trust level")

    added_at: datetime = Field(
        default_factory=datetime.utcnow, description="When key was added"
    )
    added_by: str = Field(default="system", description="Who added this key")

    description: Optional[str] = Field(None, description="Key description")
    metadata: Dict[str, str] = Field(
        default_factory=dict, description="Additional metadata"
    )

    # Revocation
    revoked: bool = Field(default=False, description="Key is revoked")
    revoked_at: Optional[datetime] = Field(None, description="Revocation timestamp")
    revoked_reason: Optional[str] = Field(None, description="Revocation reason")

    class Config:
        json_schema_extra = {
            "example": {
                "key_id": "system-key-001",
                "public_key_pem": "-----BEGIN PUBLIC KEY-----\n...\n-----END PUBLIC KEY-----",
                "public_key_hex": "a1b2c3...",
                "origin": "system",
                "trust_level": "full",
                "added_at": "2025-12-24T12:00:00Z",
                "added_by": "system",
                "description": "System master signing key",
            }
        }


class TrustedKeyring:
    """
    Manages trusted public keys for bundle signature verification.

    Provides persistent storage and management of Ed25519 public keys
    used to verify bundle signatures.
    """

    DEFAULT_KEYRING_PATH = "storage/trusted_keys/keyring.json"

    def __init__(self, keyring_path: Optional[str] = None):
        """
        Initialize trusted keyring.

        Args:
            keyring_path: Path to keyring.json file (default: storage/trusted_keys/keyring.json)
        """
        self.keyring_path = Path(keyring_path or self.DEFAULT_KEYRING_PATH)
        self.lock = RLock()

        # Key registry: key_id -> TrustedKey
        self.keys: Dict[str, TrustedKey] = {}

        # Ensure storage directory exists
        self.keyring_path.parent.mkdir(parents=True, exist_ok=True)

        # Load existing keyring
        self._load()

        logger.info(
            f"Trusted keyring initialized: {self.keyring_path} ({len(self.keys)} keys)"
        )

    def _load(self):
        """Load keyring from JSON file."""
        if not self.keyring_path.exists():
            logger.info("Keyring file not found, starting with empty keyring")
            return

        try:
            with open(self.keyring_path, "r") as f:
                data = json.load(f)

            for key_id, key_data in data.items():
                self.keys[key_id] = TrustedKey(**key_data)

            logger.info(f"Loaded {len(self.keys)} trusted keys from keyring")

        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse keyring JSON: {e}")
            raise ValueError(f"Invalid keyring JSON: {e}")
        except Exception as e:
            logger.error(f"Failed to load keyring: {e}")
            raise

    def _save(self):
        """Save keyring to JSON file."""
        try:
            # Convert keys to dict
            data = {key_id: key.model_dump() for key_id, key in self.keys.items()}

            # Write atomically (write to temp file, then rename)
            temp_path = self.keyring_path.with_suffix(".tmp")

            with open(temp_path, "w") as f:
                json.dump(data, f, indent=2, default=str)

            # Atomic rename
            temp_path.replace(self.keyring_path)

            logger.debug(f"Saved keyring: {len(self.keys)} keys")

        except Exception as e:
            logger.error(f"Failed to save keyring: {e}")
            raise

    def add_key(
        self,
        key_id: str,
        public_key_pem: str,
        origin: str = KeyOrigin.OWNER,
        trust_level: str = TrustLevel.FULL,
        added_by: str = "system",
        description: Optional[str] = None,
        metadata: Optional[Dict[str, str]] = None,
    ) -> TrustedKey:
        """
        Add a trusted public key to the keyring.

        Args:
            key_id: Unique key identifier
            public_key_pem: PEM-encoded Ed25519 public key
            origin: Key origin (system/owner/external)
            trust_level: Trust level (full/limited/revoked)
            added_by: Who added this key
            description: Optional key description
            metadata: Optional additional metadata

        Returns:
            TrustedKey object

        Raises:
            ValueError: If key_id already exists or key is invalid
            KeyImportError: If public key cannot be parsed
        """
        with self.lock:
            # Check if key already exists
            if key_id in self.keys:
                raise ValueError(f"Key ID already exists: {key_id}")

            # Validate public key by importing it
            try:
                public_key = import_public_key_pem(public_key_pem)
                public_key_hex = export_public_key_hex(public_key)
            except KeyImportError as e:
                raise ValueError(f"Invalid public key: {e}") from e

            # Create TrustedKey entry
            trusted_key = TrustedKey(
                key_id=key_id,
                public_key_pem=public_key_pem,
                public_key_hex=public_key_hex,
                origin=origin,
                trust_level=trust_level,
                added_at=datetime.utcnow(),
                added_by=added_by,
                description=description,
                metadata=metadata or {},
            )

            # Add to registry
            self.keys[key_id] = trusted_key

            # Persist
            self._save()

            logger.info(
                f"Added trusted key: {key_id} (origin={origin}, trust={trust_level})"
            )

            return trusted_key

    def remove_key(self, key_id: str) -> bool:
        """
        Remove a key from the keyring.

        Args:
            key_id: Key identifier to remove

        Returns:
            True if key was removed, False if key not found

        Note:
            Consider using revoke_key() instead of remove_key() to maintain
            audit trail.
        """
        with self.lock:
            if key_id not in self.keys:
                logger.warning(f"Cannot remove key (not found): {key_id}")
                return False

            # Remove from registry
            del self.keys[key_id]

            # Persist
            self._save()

            logger.warning(f"Removed trusted key: {key_id}")

            return True

    def revoke_key(self, key_id: str, reason: str = "Manual revocation") -> bool:
        """
        Revoke a trusted key (marks as revoked, does not delete).

        Args:
            key_id: Key identifier to revoke
            reason: Revocation reason

        Returns:
            True if key was revoked, False if key not found

        Raises:
            ValueError: If key is already revoked
        """
        with self.lock:
            if key_id not in self.keys:
                logger.warning(f"Cannot revoke key (not found): {key_id}")
                return False

            key = self.keys[key_id]

            if key.revoked:
                raise ValueError(f"Key already revoked: {key_id}")

            # Mark as revoked
            key.revoked = True
            key.revoked_at = datetime.utcnow()
            key.revoked_reason = reason
            key.trust_level = TrustLevel.REVOKED

            # Persist
            self._save()

            logger.warning(f"Revoked trusted key: {key_id} (reason: {reason})")

            return True

    def get_key(self, key_id: str) -> Optional[TrustedKey]:
        """
        Get a trusted key by ID.

        Args:
            key_id: Key identifier

        Returns:
            TrustedKey object or None if not found
        """
        return self.keys.get(key_id)

    def list_keys(
        self,
        origin: Optional[str] = None,
        trust_level: Optional[str] = None,
        include_revoked: bool = False,
    ) -> List[TrustedKey]:
        """
        List all trusted keys with optional filtering.

        Args:
            origin: Filter by origin (system/owner/external)
            trust_level: Filter by trust level (full/limited)
            include_revoked: Include revoked keys (default: False)

        Returns:
            List of TrustedKey objects
        """
        keys = list(self.keys.values())

        # Filter by origin
        if origin:
            keys = [k for k in keys if k.origin == origin]

        # Filter by trust level
        if trust_level:
            keys = [k for k in keys if k.trust_level == trust_level]

        # Filter revoked
        if not include_revoked:
            keys = [k for k in keys if not k.revoked]

        return keys

    def is_trusted(self, key_id: str) -> bool:
        """
        Check if a key is trusted (exists and not revoked).

        Args:
            key_id: Key identifier

        Returns:
            True if key is trusted, False otherwise
        """
        key = self.get_key(key_id)

        if not key:
            return False

        if key.revoked:
            return False

        if key.trust_level == TrustLevel.REVOKED:
            return False

        return True

    def get_public_key(self, key_id: str) -> Optional[ed25519.Ed25519PublicKey]:
        """
        Get Ed25519 public key object for verification.

        Args:
            key_id: Key identifier

        Returns:
            Ed25519 public key or None if not found

        Raises:
            KeyImportError: If key cannot be loaded
        """
        key = self.get_key(key_id)

        if not key:
            return None

        try:
            return import_public_key_pem(key.public_key_pem)
        except KeyImportError as e:
            logger.error(f"Failed to load public key {key_id}: {e}")
            raise

    def export_keyring(self, output_path: Path):
        """
        Export keyring to JSON file.

        Args:
            output_path: Path to export file

        Note:
            This exports the entire keyring including metadata.
            Only export to secure locations.
        """
        with self.lock:
            try:
                data = {
                    key_id: key.model_dump() for key_id, key in self.keys.items()
                }

                output_path.parent.mkdir(parents=True, exist_ok=True)

                with open(output_path, "w") as f:
                    json.dump(data, f, indent=2, default=str)

                logger.info(f"Exported keyring to: {output_path}")

            except Exception as e:
                logger.error(f"Failed to export keyring: {e}")
                raise

    def import_keyring(self, import_path: Path, merge: bool = False):
        """
        Import keyring from JSON file.

        Args:
            import_path: Path to import file
            merge: If True, merge with existing keyring; if False, replace

        Raises:
            ValueError: If import file is invalid
            FileNotFoundError: If import file doesn't exist
        """
        with self.lock:
            if not import_path.exists():
                raise FileNotFoundError(f"Import file not found: {import_path}")

            try:
                with open(import_path, "r") as f:
                    data = json.load(f)

                imported_keys = {
                    key_id: TrustedKey(**key_data) for key_id, key_data in data.items()
                }

                if merge:
                    # Merge with existing keys (imported keys take precedence)
                    self.keys.update(imported_keys)
                    logger.info(
                        f"Merged {len(imported_keys)} keys into keyring (total: {len(self.keys)})"
                    )
                else:
                    # Replace keyring
                    self.keys = imported_keys
                    logger.warning(
                        f"Replaced keyring with {len(imported_keys)} imported keys"
                    )

                # Persist
                self._save()

            except json.JSONDecodeError as e:
                logger.error(f"Invalid JSON in import file: {e}")
                raise ValueError(f"Invalid keyring JSON: {e}") from e
            except Exception as e:
                logger.error(f"Failed to import keyring: {e}")
                raise


# ============================================================================
# Singleton
# ============================================================================

_keyring_instance: Optional[TrustedKeyring] = None


def get_trusted_keyring() -> TrustedKeyring:
    """
    Get singleton trusted keyring instance.

    Returns:
        TrustedKeyring instance
    """
    global _keyring_instance

    if _keyring_instance is None:
        _keyring_instance = TrustedKeyring()

    return _keyring_instance
