"""
Data Encryption System for BRAiN Core.

Provides at-rest encryption for sensitive data:
- Field-level encryption (passwords, tokens, API keys, secrets)
- Key management (rotation, derivation)
- Symmetric encryption (Fernet - AES-128 CBC with HMAC)
- Asymmetric encryption (RSA for key exchange)
- Hashing (SHA-256, bcrypt for passwords)

Security Features:
- AES-128 encryption in CBC mode
- HMAC authentication (prevents tampering)
- Automatic IV generation (prevents replay attacks)
- Key rotation support
- Secure key derivation (PBKDF2)
- Constant-time comparison (prevents timing attacks)

Usage:
    from app.core.encryption import encryptor, hash_password, verify_password

    # Encrypt sensitive data
    encrypted = await encryptor.encrypt("my-secret-api-key")
    # Store encrypted in database

    # Decrypt when needed
    decrypted = await encryptor.decrypt(encrypted)

    # Hash passwords
    hashed = hash_password("user-password")
    # Store hashed in database

    # Verify passwords
    if verify_password("user-password", hashed):
        # Password correct
        pass
"""

from __future__ import annotations

import os
import base64
import hashlib
import secrets
from typing import Optional

from cryptography.fernet import Fernet, InvalidToken
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2
from cryptography.hazmat.backends import default_backend
import bcrypt
from loguru import logger


# ============================================================================
# Password Hashing (bcrypt)
# ============================================================================

def hash_password(password: str, cost: int = 12) -> str:
    """
    Hash password using bcrypt.

    bcrypt is designed for password hashing:
    - Adaptive cost factor (increases with hardware improvements)
    - Automatic salt generation
    - Slow by design (prevents brute force)

    Args:
        password: Plaintext password
        cost: Cost factor (2^cost iterations, default: 12 = ~250ms)

    Returns:
        Hashed password (bcrypt format)

    Example:
        hashed = hash_password("user-password")
        # Store hashed in database
    """
    password_bytes = password.encode('utf-8')
    salt = bcrypt.gensalt(rounds=cost)
    hashed = bcrypt.hashpw(password_bytes, salt)
    return hashed.decode('utf-8')


def verify_password(password: str, hashed: str) -> bool:
    """
    Verify password against bcrypt hash.

    Uses constant-time comparison to prevent timing attacks.

    Args:
        password: Plaintext password
        hashed: Hashed password from database

    Returns:
        True if password matches, False otherwise

    Example:
        if verify_password("user-password", stored_hash):
            # Password correct
            grant_access()
    """
    password_bytes = password.encode('utf-8')
    hashed_bytes = hashed.encode('utf-8')

    try:
        return bcrypt.checkpw(password_bytes, hashed_bytes)
    except Exception as e:
        logger.error(f"Password verification error: {e}")
        return False


# ============================================================================
# Data Hashing (SHA-256)
# ============================================================================

def hash_data(data: str, salt: Optional[str] = None) -> str:
    """
    Hash data using SHA-256.

    For non-password data that needs deterministic hashing
    (e.g., API keys, tokens for lookup).

    Args:
        data: Data to hash
        salt: Optional salt (for additional security)

    Returns:
        SHA-256 hash (hex string)

    Example:
        # Hash API key for lookup
        key_hash = hash_data(api_key)
    """
    if salt:
        data = f"{salt}{data}"

    return hashlib.sha256(data.encode('utf-8')).hexdigest()


def hash_data_hmac(data: str, key: str) -> str:
    """
    Hash data using HMAC-SHA256.

    Provides authentication (verifies data hasn't been tampered with).

    Args:
        data: Data to hash
        key: Secret key

    Returns:
        HMAC-SHA256 hash (hex string)

    Example:
        # Sign data
        signature = hash_data_hmac(data, secret_key)

        # Verify data
        if hash_data_hmac(received_data, secret_key) == signature:
            # Data is authentic
            pass
    """
    import hmac

    return hmac.new(
        key.encode('utf-8'),
        data.encode('utf-8'),
        hashlib.sha256
    ).hexdigest()


# ============================================================================
# Symmetric Encryption (Fernet/AES)
# ============================================================================

class Encryptor:
    """
    Symmetric encryption using Fernet (AES-128 CBC + HMAC).

    Fernet provides:
    - AES-128 encryption in CBC mode
    - HMAC-SHA256 authentication (prevents tampering)
    - Automatic IV generation (prevents replay attacks)
    - Base64 encoding (safe for storage)
    - Timestamp (for expiration)

    Thread-safe and suitable for encrypting sensitive data at rest.
    """

    def __init__(self, encryption_key: Optional[bytes] = None):
        """
        Initialize encryptor.

        Args:
            encryption_key: Optional encryption key (32 bytes)
                           If not provided, loads from environment or generates new

        Environment Variables:
            ENCRYPTION_KEY: Base64-encoded encryption key
        """
        if encryption_key is None:
            # Try to load from environment
            key_b64 = os.getenv("ENCRYPTION_KEY")
            if key_b64:
                encryption_key = base64.urlsafe_b64decode(key_b64)
            else:
                # Generate new key (WARNING: data encrypted with this key
                # cannot be decrypted after restart!)
                logger.warning(
                    "No ENCRYPTION_KEY in environment. Generating temporary key. "
                    "Set ENCRYPTION_KEY environment variable for production!"
                )
                encryption_key = Fernet.generate_key()

        self.key = encryption_key
        self.fernet = Fernet(self.key)

    @staticmethod
    def generate_key() -> bytes:
        """
        Generate new encryption key.

        Returns:
            32-byte encryption key (Fernet format)

        Example:
            key = Encryptor.generate_key()
            key_b64 = base64.urlsafe_b64encode(key).decode()
            # Store key_b64 in environment variable: ENCRYPTION_KEY
        """
        return Fernet.generate_key()

    async def encrypt(self, plaintext: str) -> str:
        """
        Encrypt string data.

        Args:
            plaintext: Data to encrypt

        Returns:
            Base64-encoded encrypted data (includes IV, ciphertext, HMAC)

        Example:
            encrypted = await encryptor.encrypt("my-api-key")
            # Store encrypted in database
        """
        try:
            plaintext_bytes = plaintext.encode('utf-8')
            encrypted_bytes = self.fernet.encrypt(plaintext_bytes)
            return base64.urlsafe_b64encode(encrypted_bytes).decode('utf-8')
        except Exception as e:
            logger.error(f"Encryption error: {e}")
            raise

    async def decrypt(self, ciphertext: str, ttl: Optional[int] = None) -> str:
        """
        Decrypt string data.

        Args:
            ciphertext: Base64-encoded encrypted data
            ttl: Optional time-to-live in seconds (rejects if older)

        Returns:
            Decrypted plaintext

        Raises:
            InvalidToken: If decryption fails or TTL exceeded

        Example:
            decrypted = await encryptor.decrypt(encrypted_from_db)
        """
        try:
            ciphertext_bytes = base64.urlsafe_b64decode(ciphertext)
            decrypted_bytes = self.fernet.decrypt(ciphertext_bytes, ttl=ttl)
            return decrypted_bytes.decode('utf-8')
        except InvalidToken:
            logger.warning("Decryption failed: invalid token or TTL exceeded")
            raise
        except Exception as e:
            logger.error(f"Decryption error: {e}")
            raise

    async def encrypt_dict(self, data: dict) -> str:
        """
        Encrypt dictionary as JSON.

        Args:
            data: Dictionary to encrypt

        Returns:
            Base64-encoded encrypted JSON

        Example:
            encrypted = await encryptor.encrypt_dict({
                "api_key": "secret",
                "token": "sensitive"
            })
        """
        import json

        json_str = json.dumps(data)
        return await self.encrypt(json_str)

    async def decrypt_dict(self, ciphertext: str, ttl: Optional[int] = None) -> dict:
        """
        Decrypt JSON to dictionary.

        Args:
            ciphertext: Base64-encoded encrypted JSON
            ttl: Optional time-to-live in seconds

        Returns:
            Decrypted dictionary

        Example:
            data = await encryptor.decrypt_dict(encrypted_from_db)
        """
        import json

        json_str = await self.decrypt(ciphertext, ttl=ttl)
        return json.loads(json_str)

    async def rotate_key(self, old_key: bytes, data: str) -> str:
        """
        Rotate encryption key (re-encrypt with new key).

        Args:
            old_key: Previous encryption key
            data: Encrypted data (with old key)

        Returns:
            Re-encrypted data (with current key)

        Example:
            # Load old encrypted data
            old_encrypted = load_from_db()

            # Rotate to new key
            new_encrypted = await encryptor.rotate_key(old_key, old_encrypted)

            # Update database
            save_to_db(new_encrypted)
        """
        # Decrypt with old key
        old_fernet = Fernet(old_key)
        ciphertext_bytes = base64.urlsafe_b64decode(data)
        plaintext_bytes = old_fernet.decrypt(ciphertext_bytes)

        # Encrypt with new key
        new_encrypted_bytes = self.fernet.encrypt(plaintext_bytes)
        return base64.urlsafe_b64encode(new_encrypted_bytes).decode('utf-8')


# ============================================================================
# Key Derivation (PBKDF2)
# ============================================================================

def derive_key(password: str, salt: Optional[bytes] = None, iterations: int = 100000) -> tuple[bytes, bytes]:
    """
    Derive encryption key from password using PBKDF2.

    Useful for deriving encryption keys from user passwords.

    Args:
        password: User password
        salt: Optional salt (generated if not provided)
        iterations: PBKDF2 iterations (default: 100,000)

    Returns:
        Tuple of (derived_key, salt)

    Example:
        # Derive key from user password
        key, salt = derive_key("user-password")

        # Store salt in database
        # Use key for encryption

        # Later: derive same key from same password + salt
        key, _ = derive_key("user-password", salt=stored_salt)
    """
    if salt is None:
        salt = os.urandom(16)

    kdf = PBKDF2(
        algorithm=hashes.SHA256(),
        length=32,  # 32 bytes = 256 bits
        salt=salt,
        iterations=iterations,
        backend=default_backend()
    )

    key = kdf.derive(password.encode('utf-8'))

    return key, salt


# ============================================================================
# Utilities
# ============================================================================

def generate_random_string(length: int = 32) -> str:
    """
    Generate cryptographically secure random string.

    Args:
        length: String length (default: 32)

    Returns:
        URL-safe random string

    Example:
        # Generate random token
        token = generate_random_string(64)
    """
    return secrets.token_urlsafe(length)


def generate_random_bytes(length: int = 32) -> bytes:
    """
    Generate cryptographically secure random bytes.

    Args:
        length: Byte length (default: 32)

    Returns:
        Random bytes

    Example:
        # Generate random key
        key = generate_random_bytes(32)
    """
    return secrets.token_bytes(length)


def constant_time_compare(a: str, b: str) -> bool:
    """
    Constant-time string comparison (prevents timing attacks).

    Args:
        a: First string
        b: Second string

    Returns:
        True if strings are equal, False otherwise

    Example:
        # Compare tokens
        if constant_time_compare(provided_token, stored_token):
            # Token valid
            pass
    """
    return secrets.compare_digest(a, b)


# ============================================================================
# Encrypted Field Helper
# ============================================================================

class EncryptedField:
    """
    Helper for transparently encrypting/decrypting database fields.

    Usage:
        class User(BaseModel):
            id: str
            email: str
            _password_encrypted: str  # Stored encrypted

            @property
            def password(self) -> str:
                # Decrypt on access
                return asyncio.run(
                    encryptor.decrypt(self._password_encrypted)
                )

            @password.setter
            def password(self, value: str):
                # Encrypt on set
                self._password_encrypted = asyncio.run(
                    encryptor.encrypt(value)
                )
    """

    def __init__(self, encryptor: Encryptor):
        self.encryptor = encryptor

    async def get(self, encrypted_value: str) -> str:
        """Decrypt field value."""
        return await self.encryptor.decrypt(encrypted_value)

    async def set(self, plaintext_value: str) -> str:
        """Encrypt field value."""
        return await self.encryptor.encrypt(plaintext_value)


# ============================================================================
# Global Encryptor Instance
# ============================================================================

_encryptor: Optional[Encryptor] = None


def get_encryptor() -> Encryptor:
    """Get global encryptor instance."""
    global _encryptor
    if _encryptor is None:
        _encryptor = Encryptor()
    return _encryptor


# Convenience global instance
encryptor = get_encryptor()


# ============================================================================
# Key Management
# ============================================================================

class KeyManager:
    """
    Encryption key management system.

    Features:
    - Key generation
    - Key rotation
    - Key storage (environment variables)
    - Key validation
    """

    @staticmethod
    def generate_and_print_key():
        """
        Generate new encryption key and print to console.

        Use this to generate keys for production deployment.

        Example:
            python -c "from app.core.encryption import KeyManager; KeyManager.generate_and_print_key()"
        """
        key = Encryptor.generate_key()
        key_b64 = base64.urlsafe_b64encode(key).decode('utf-8')

        print("=" * 80)
        print("GENERATED ENCRYPTION KEY")
        print("=" * 80)
        print()
        print("Add this to your .env file:")
        print()
        print(f"ENCRYPTION_KEY={key_b64}")
        print()
        print("⚠️  IMPORTANT:")
        print("- Store this key securely (e.g., AWS Secrets Manager, Vault)")
        print("- Never commit this key to version control")
        print("- Data encrypted with this key cannot be decrypted without it")
        print("- Losing this key means PERMANENT DATA LOSS")
        print()
        print("=" * 80)

    @staticmethod
    def validate_key(key_b64: str) -> bool:
        """
        Validate encryption key format.

        Args:
            key_b64: Base64-encoded encryption key

        Returns:
            True if valid, False otherwise
        """
        try:
            key_bytes = base64.urlsafe_b64decode(key_b64)
            if len(key_bytes) != 32:
                return False

            # Try to create Fernet instance
            Fernet(key_bytes)
            return True
        except Exception:
            return False


# ============================================================================
# CLI Command
# ============================================================================

if __name__ == "__main__":
    import sys

    if len(sys.argv) > 1 and sys.argv[1] == "generate-key":
        KeyManager.generate_and_print_key()
    else:
        print("Usage:")
        print("  python -m app.core.encryption generate-key")
        print()
        print("Generates a new encryption key for production deployment.")
