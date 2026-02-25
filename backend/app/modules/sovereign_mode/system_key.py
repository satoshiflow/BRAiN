"""
System Key Management - Persistent Bundle Signing Key

Manages the persistent system key used for bundle signing.
Replaces ephemeral key generation with secure persistent storage.

Security Model:
- System key is generated once and persisted to disk
- Generated using cryptographically secure random sources
- Loaded from persistent storage on service startup
- Never regenerated unless explicitly rotated
- Stored with restricted file permissions (0600)
"""

import os
import json
from pathlib import Path
from threading import RLock
from typing import Tuple, Optional
from datetime import datetime
from loguru import logger

from app.modules.sovereign_mode.crypto import (
    generate_keypair,
    export_private_key_pem,
    export_public_key_pem,
    export_public_key_hex,
    import_private_key_pem,
    import_public_key_pem,
)
from cryptography.hazmat.primitives.asymmetric import ed25519


class SystemKeyManager:
    """
    Manages the persistent system signing key for bundle signatures.

    Security Features:
    - Single key per system (no ephemeral keys)
    - Persistent storage with secure file permissions
    - Key metadata including creation timestamp
    - Optional key rotation support
    - Audit logging of key operations
    """

    DEFAULT_KEY_DIR = Path("storage/system_keys")
    SYSTEM_KEY_ID = "system-key-001"
    SYSTEM_KEY_FILE = "system-key.json"

    def __init__(self, key_dir: Optional[Path] = None):
        """
        Initialize system key manager.

        Args:
            key_dir: Directory for key storage (default: storage/system_keys)
        """
        self.key_dir = key_dir or self.DEFAULT_KEY_DIR
        self.key_dir.mkdir(parents=True, exist_ok=True)
        self.lock = RLock()

        # Cache loaded key
        self._cached_private_key: Optional[ed25519.Ed25519PrivateKey] = None
        self._cached_public_key: Optional[ed25519.Ed25519PublicKey] = None
        self._key_loaded_at: Optional[datetime] = None

        logger.info(f"System key manager initialized: {self.key_dir}")

    @property
    def system_key_path(self) -> Path:
        """Get full path to system key file."""
        return self.key_dir / self.SYSTEM_KEY_FILE

    def ensure_system_key_exists(self) -> Tuple[ed25519.Ed25519PrivateKey, ed25519.Ed25519PublicKey]:
        """
        Ensure system key exists, creating if necessary.

        Returns:
            Tuple of (private_key, public_key)

        Raises:
            RuntimeError: If key creation fails
        """
        with self.lock:
            # Try to load existing key
            if self.system_key_path.exists():
                logger.debug(f"Loading existing system key from {self.system_key_path}")
                return self.load_system_key()

            # Create new key
            logger.warning(f"System key not found. Creating new key at {self.system_key_path}")
            return self.create_system_key()

    def create_system_key(self) -> Tuple[ed25519.Ed25519PrivateKey, ed25519.Ed25519PublicKey]:
        """
        Create and persist a new system signing key.

        Returns:
            Tuple of (private_key, public_key)

        Raises:
            RuntimeError: If key creation or persistence fails
        """
        with self.lock:
            try:
                # Generate new keypair
                private_key, public_key = generate_keypair()

                # Export to PEM format
                private_key_pem = export_private_key_pem(private_key)
                public_key_pem = export_public_key_pem(public_key)
                public_key_hex = export_public_key_hex(public_key)

                # Create metadata
                key_data = {
                    "key_id": self.SYSTEM_KEY_ID,
                    "type": "ed25519",
                    "private_key_pem": private_key_pem,
                    "public_key_pem": public_key_pem,
                    "public_key_hex": public_key_hex,
                    "created_at": datetime.utcnow().isoformat(),
                    "origin": "system",
                    "version": 1,
                    "rotation_count": 0,
                }

                # Persist to disk with restricted permissions
                self.system_key_path.parent.mkdir(parents=True, exist_ok=True)

                # Write file with restrictive permissions
                with open(self.system_key_path, 'w') as f:
                    json.dump(key_data, f, indent=2)

                # Set file permissions to 0600 (read/write for owner only)
                os.chmod(self.system_key_path, 0o600)

                # Cache the key
                self._cached_private_key = private_key
                self._cached_public_key = public_key
                self._key_loaded_at = datetime.utcnow()

                logger.warning(
                    f"System key created and persisted: {self.system_key_path} "
                    f"(permissions: 0600, key_id: {self.SYSTEM_KEY_ID})"
                )

                return private_key, public_key

            except Exception as e:
                logger.error(f"Failed to create system key: {e}", exc_info=True)
                raise RuntimeError(f"Failed to create system key: {e}") from e

    def load_system_key(self) -> Tuple[ed25519.Ed25519PrivateKey, ed25519.Ed25519PublicKey]:
        """
        Load persisted system signing key.

        Returns:
            Tuple of (private_key, public_key)

        Raises:
            FileNotFoundError: If system key file doesn't exist
            ValueError: If key data is corrupted or invalid
            RuntimeError: If key loading fails
        """
        with self.lock:
            # Return cached key if available
            if self._cached_private_key is not None and self._cached_public_key is not None:
                return self._cached_private_key, self._cached_public_key

            try:
                # Check file exists
                if not self.system_key_path.exists():
                    raise FileNotFoundError(
                        f"System key file not found: {self.system_key_path}"
                    )

                # Check file permissions
                stat = self.system_key_path.stat()
                if stat.st_mode & 0o077:  # Check if group/other have any permissions
                    logger.warning(
                        f"System key file has insecure permissions: "
                        f"{oct(stat.st_mode)}. Fixing to 0600."
                    )
                    os.chmod(self.system_key_path, 0o600)

                # Load and parse key file
                with open(self.system_key_path, 'r') as f:
                    key_data = json.load(f)

                # Validate key data
                required_fields = ["key_id", "private_key_pem", "public_key_pem"]
                for field in required_fields:
                    if field not in key_data:
                        raise ValueError(f"Missing required field in key data: {field}")

                # Import keys from PEM
                private_key_pem = key_data["private_key_pem"]
                public_key_pem = key_data["public_key_pem"]

                private_key = import_private_key_pem(private_key_pem)
                public_key = import_public_key_pem(public_key_pem)

                # Cache the keys
                self._cached_private_key = private_key
                self._cached_public_key = public_key
                self._key_loaded_at = datetime.utcnow()

                logger.debug(
                    f"System key loaded: {key_data.get('key_id')} "
                    f"(created: {key_data.get('created_at')})"
                )

                return private_key, public_key

            except (FileNotFoundError, ValueError) as e:
                logger.error(f"Failed to load system key: {e}")
                raise
            except Exception as e:
                logger.error(f"Unexpected error loading system key: {e}", exc_info=True)
                raise RuntimeError(f"Failed to load system key: {e}") from e

    def get_public_key_pem(self) -> str:
        """
        Get system public key in PEM format.

        Returns:
            Public key in PEM format
        """
        if not self.system_key_path.exists():
            self.ensure_system_key_exists()

        with open(self.system_key_path, 'r') as f:
            key_data = json.load(f)

        return key_data["public_key_pem"]

    def get_public_key_hex(self) -> str:
        """
        Get system public key in hex format.

        Returns:
            Public key in hex format
        """
        if not self.system_key_path.exists():
            self.ensure_system_key_exists()

        with open(self.system_key_path, 'r') as f:
            key_data = json.load(f)

        return key_data.get("public_key_hex", "")

    def rotate_system_key(self) -> Tuple[ed25519.Ed25519PrivateKey, ed25519.Ed25519PublicKey]:
        """
        Rotate the system signing key (create new, archive old).

        Returns:
            Tuple of (new_private_key, new_public_key)

        Raises:
            RuntimeError: If key rotation fails
        """
        with self.lock:
            try:
                # Archive existing key if it exists
                if self.system_key_path.exists():
                    archive_path = self.key_dir / f"system-key.backup.{datetime.utcnow().isoformat()}.json"
                    self.system_key_path.rename(archive_path)
                    logger.warning(f"Archived previous system key: {archive_path}")

                # Clear cache
                self._cached_private_key = None
                self._cached_public_key = None

                # Create new key
                return self.create_system_key()

            except Exception as e:
                logger.error(f"Failed to rotate system key: {e}", exc_info=True)
                raise RuntimeError(f"Failed to rotate system key: {e}") from e

    def get_key_metadata(self) -> dict:
        """
        Get system key metadata.

        Returns:
            Dictionary with key metadata (creation time, rotation count, etc.)
        """
        if not self.system_key_path.exists():
            return {"status": "not_created"}

        with open(self.system_key_path, 'r') as f:
            key_data = json.load(f)

        return {
            "key_id": key_data.get("key_id"),
            "created_at": key_data.get("created_at"),
            "rotation_count": key_data.get("rotation_count", 0),
            "type": key_data.get("type"),
            "origin": key_data.get("origin"),
            "file_path": str(self.system_key_path),
            "file_size_bytes": self.system_key_path.stat().st_size,
        }


# Singleton instance
_system_key_manager: Optional[SystemKeyManager] = None


def get_system_key_manager(key_dir: Optional[Path] = None) -> SystemKeyManager:
    """Get or create system key manager singleton."""
    global _system_key_manager

    if _system_key_manager is None:
        _system_key_manager = SystemKeyManager(key_dir)

    return _system_key_manager


def get_system_signing_key() -> Tuple[ed25519.Ed25519PrivateKey, ed25519.Ed25519PublicKey]:
    """
    Get the persistent system signing key.

    Creates the key if it doesn't exist.

    Returns:
        Tuple of (private_key, public_key)
    """
    manager = get_system_key_manager()
    return manager.ensure_system_key_exists()
