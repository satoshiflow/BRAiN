"""
Cryptography Module - Ed25519 Keypair Management

Provides Ed25519 signature generation and verification for bundle signing.
Part of G1 - Bundle Signing & Trusted Origin governance implementation.
"""

from typing import Tuple
from pathlib import Path
import base64
from loguru import logger

from cryptography.hazmat.primitives.asymmetric import ed25519
from cryptography.hazmat.primitives import serialization


class CryptoError(Exception):
    """Base exception for cryptographic operations."""

    pass


class KeyGenerationError(CryptoError):
    """Raised when key generation fails."""

    pass


class KeyImportError(CryptoError):
    """Raised when key import fails."""

    pass


class SignatureError(CryptoError):
    """Raised when signature generation/verification fails."""

    pass


def generate_keypair() -> Tuple[ed25519.Ed25519PrivateKey, ed25519.Ed25519PublicKey]:
    """
    Generate a new Ed25519 keypair.

    Returns:
        Tuple of (private_key, public_key)

    Raises:
        KeyGenerationError: If key generation fails
    """
    try:
        private_key = ed25519.Ed25519PrivateKey.generate()
        public_key = private_key.public_key()

        logger.info("Generated new Ed25519 keypair")
        return private_key, public_key

    except Exception as e:
        logger.error(f"Failed to generate Ed25519 keypair: {e}")
        raise KeyGenerationError(f"Key generation failed: {e}") from e


def export_private_key_pem(private_key: ed25519.Ed25519PrivateKey) -> str:
    """
    Export private key to PEM format (PKCS8).

    Args:
        private_key: Ed25519 private key

    Returns:
        PEM-encoded private key string

    Raises:
        CryptoError: If export fails
    """
    try:
        pem_bytes = private_key.private_bytes(
            encoding=serialization.Encoding.PEM,
            format=serialization.PrivateFormat.PKCS8,
            encryption_algorithm=serialization.NoEncryption(),
        )
        return pem_bytes.decode("utf-8")

    except Exception as e:
        logger.error(f"Failed to export private key: {e}")
        raise CryptoError(f"Private key export failed: {e}") from e


def export_public_key_pem(public_key: ed25519.Ed25519PublicKey) -> str:
    """
    Export public key to PEM format (SubjectPublicKeyInfo).

    Args:
        public_key: Ed25519 public key

    Returns:
        PEM-encoded public key string

    Raises:
        CryptoError: If export fails
    """
    try:
        pem_bytes = public_key.public_bytes(
            encoding=serialization.Encoding.PEM,
            format=serialization.PublicFormat.SubjectPublicKeyInfo,
        )
        return pem_bytes.decode("utf-8")

    except Exception as e:
        logger.error(f"Failed to export public key: {e}")
        raise CryptoError(f"Public key export failed: {e}") from e


def export_private_key_hex(private_key: ed25519.Ed25519PrivateKey) -> str:
    """
    Export private key to hex format (raw 32 bytes).

    Args:
        private_key: Ed25519 private key

    Returns:
        Hex-encoded private key string (64 characters)

    Raises:
        CryptoError: If export fails
    """
    try:
        raw_bytes = private_key.private_bytes(
            encoding=serialization.Encoding.Raw,
            format=serialization.PrivateFormat.Raw,
            encryption_algorithm=serialization.NoEncryption(),
        )
        return raw_bytes.hex()

    except Exception as e:
        logger.error(f"Failed to export private key (hex): {e}")
        raise CryptoError(f"Private key hex export failed: {e}") from e


def export_public_key_hex(public_key: ed25519.Ed25519PublicKey) -> str:
    """
    Export public key to hex format (raw 32 bytes).

    Args:
        public_key: Ed25519 public key

    Returns:
        Hex-encoded public key string (64 characters)

    Raises:
        CryptoError: If export fails
    """
    try:
        raw_bytes = public_key.public_bytes(
            encoding=serialization.Encoding.Raw,
            format=serialization.PublicFormat.Raw,
        )
        return raw_bytes.hex()

    except Exception as e:
        logger.error(f"Failed to export public key (hex): {e}")
        raise CryptoError(f"Public key hex export failed: {e}") from e


def import_private_key_pem(pem_data: str) -> ed25519.Ed25519PrivateKey:
    """
    Import private key from PEM format.

    Args:
        pem_data: PEM-encoded private key string

    Returns:
        Ed25519 private key

    Raises:
        KeyImportError: If import fails or key is invalid
    """
    try:
        pem_bytes = pem_data.encode("utf-8")
        private_key = serialization.load_pem_private_key(pem_bytes, password=None)

        if not isinstance(private_key, ed25519.Ed25519PrivateKey):
            raise KeyImportError("Imported key is not an Ed25519 private key")

        logger.info("Imported Ed25519 private key from PEM")
        return private_key

    except KeyImportError:
        raise
    except Exception as e:
        logger.error(f"Failed to import private key from PEM: {e}")
        raise KeyImportError(f"Private key import failed: {e}") from e


def import_public_key_pem(pem_data: str) -> ed25519.Ed25519PublicKey:
    """
    Import public key from PEM format.

    Args:
        pem_data: PEM-encoded public key string

    Returns:
        Ed25519 public key

    Raises:
        KeyImportError: If import fails or key is invalid
    """
    try:
        pem_bytes = pem_data.encode("utf-8")
        public_key = serialization.load_pem_public_key(pem_bytes)

        if not isinstance(public_key, ed25519.Ed25519PublicKey):
            raise KeyImportError("Imported key is not an Ed25519 public key")

        logger.info("Imported Ed25519 public key from PEM")
        return public_key

    except KeyImportError:
        raise
    except Exception as e:
        logger.error(f"Failed to import public key from PEM: {e}")
        raise KeyImportError(f"Public key import failed: {e}") from e


def import_private_key_hex(hex_data: str) -> ed25519.Ed25519PrivateKey:
    """
    Import private key from hex format (raw 32 bytes).

    Args:
        hex_data: Hex-encoded private key string (64 characters)

    Returns:
        Ed25519 private key

    Raises:
        KeyImportError: If import fails or hex is invalid
    """
    try:
        if len(hex_data) != 64:
            raise KeyImportError(
                f"Invalid hex key length: {len(hex_data)} (expected 64)"
            )

        raw_bytes = bytes.fromhex(hex_data)
        private_key = ed25519.Ed25519PrivateKey.from_private_bytes(raw_bytes)

        logger.info("Imported Ed25519 private key from hex")
        return private_key

    except KeyImportError:
        raise
    except Exception as e:
        logger.error(f"Failed to import private key from hex: {e}")
        raise KeyImportError(f"Private key hex import failed: {e}") from e


def import_public_key_hex(hex_data: str) -> ed25519.Ed25519PublicKey:
    """
    Import public key from hex format (raw 32 bytes).

    Args:
        hex_data: Hex-encoded public key string (64 characters)

    Returns:
        Ed25519 public key

    Raises:
        KeyImportError: If import fails or hex is invalid
    """
    try:
        if len(hex_data) != 64:
            raise KeyImportError(
                f"Invalid hex key length: {len(hex_data)} (expected 64)"
            )

        raw_bytes = bytes.fromhex(hex_data)
        public_key = ed25519.Ed25519PublicKey.from_public_bytes(raw_bytes)

        logger.info("Imported Ed25519 public key from hex")
        return public_key

    except KeyImportError:
        raise
    except Exception as e:
        logger.error(f"Failed to import public key from hex: {e}")
        raise KeyImportError(f"Public key hex import failed: {e}") from e


def sign_data(data: bytes, private_key: ed25519.Ed25519PrivateKey) -> bytes:
    """
    Sign data using Ed25519 private key.

    Args:
        data: Data to sign (raw bytes)
        private_key: Ed25519 private key

    Returns:
        Signature (64 bytes)

    Raises:
        SignatureError: If signing fails
    """
    try:
        signature = private_key.sign(data)
        logger.debug(f"Signed {len(data)} bytes of data")
        return signature

    except Exception as e:
        logger.error(f"Failed to sign data: {e}")
        raise SignatureError(f"Signature generation failed: {e}") from e


def verify_signature(
    data: bytes, signature: bytes, public_key: ed25519.Ed25519PublicKey
) -> bool:
    """
    Verify Ed25519 signature.

    Args:
        data: Original data (raw bytes)
        signature: Signature to verify (64 bytes)
        public_key: Ed25519 public key

    Returns:
        True if signature is valid, False otherwise

    Raises:
        SignatureError: If verification process fails (not same as invalid signature)
    """
    try:
        public_key.verify(signature, data)
        logger.debug("Signature verification: VALID")
        return True

    except Exception as e:
        # Ed25519 verification raises exception on invalid signature
        logger.debug(f"Signature verification: INVALID ({e})")
        return False


def sign_data_hex(data: bytes, private_key: ed25519.Ed25519PrivateKey) -> str:
    """
    Sign data and return hex-encoded signature.

    Args:
        data: Data to sign (raw bytes)
        private_key: Ed25519 private key

    Returns:
        Hex-encoded signature string (128 characters)

    Raises:
        SignatureError: If signing fails
    """
    signature_bytes = sign_data(data, private_key)
    return signature_bytes.hex()


def verify_signature_hex(
    data: bytes, signature_hex: str, public_key: ed25519.Ed25519PublicKey
) -> bool:
    """
    Verify hex-encoded Ed25519 signature.

    Args:
        data: Original data (raw bytes)
        signature_hex: Hex-encoded signature string (128 characters)
        public_key: Ed25519 public key

    Returns:
        True if signature is valid, False otherwise

    Raises:
        SignatureError: If hex decoding or verification fails
    """
    try:
        if len(signature_hex) != 128:
            raise SignatureError(
                f"Invalid signature hex length: {len(signature_hex)} (expected 128)"
            )

        signature_bytes = bytes.fromhex(signature_hex)
        return verify_signature(data, signature_bytes, public_key)

    except SignatureError:
        raise
    except Exception as e:
        logger.error(f"Signature hex verification failed: {e}")
        raise SignatureError(f"Hex signature verification failed: {e}") from e


# ============================================================================
# Storage Utilities
# ============================================================================


def save_private_key_file(private_key: ed25519.Ed25519PrivateKey, file_path: Path):
    """
    Save private key to file in PEM format.

    Args:
        private_key: Ed25519 private key
        file_path: Path to save key file

    Raises:
        CryptoError: If save fails
    """
    try:
        pem_data = export_private_key_pem(private_key)
        file_path.parent.mkdir(parents=True, exist_ok=True)

        with open(file_path, "w") as f:
            f.write(pem_data)

        # Set restrictive permissions (owner read/write only)
        file_path.chmod(0o600)

        logger.info(f"Saved private key to: {file_path}")

    except Exception as e:
        logger.error(f"Failed to save private key to {file_path}: {e}")
        raise CryptoError(f"Private key save failed: {e}") from e


def save_public_key_file(public_key: ed25519.Ed25519PublicKey, file_path: Path):
    """
    Save public key to file in PEM format.

    Args:
        public_key: Ed25519 public key
        file_path: Path to save key file

    Raises:
        CryptoError: If save fails
    """
    try:
        pem_data = export_public_key_pem(public_key)
        file_path.parent.mkdir(parents=True, exist_ok=True)

        with open(file_path, "w") as f:
            f.write(pem_data)

        logger.info(f"Saved public key to: {file_path}")

    except Exception as e:
        logger.error(f"Failed to save public key to {file_path}: {e}")
        raise CryptoError(f"Public key save failed: {e}") from e


def load_private_key_file(file_path: Path) -> ed25519.Ed25519PrivateKey:
    """
    Load private key from PEM file.

    Args:
        file_path: Path to private key file

    Returns:
        Ed25519 private key

    Raises:
        KeyImportError: If load fails or file doesn't exist
    """
    try:
        if not file_path.exists():
            raise KeyImportError(f"Private key file not found: {file_path}")

        with open(file_path, "r") as f:
            pem_data = f.read()

        return import_private_key_pem(pem_data)

    except KeyImportError:
        raise
    except Exception as e:
        logger.error(f"Failed to load private key from {file_path}: {e}")
        raise KeyImportError(f"Private key load failed: {e}") from e


def load_public_key_file(file_path: Path) -> ed25519.Ed25519PublicKey:
    """
    Load public key from PEM file.

    Args:
        file_path: Path to public key file

    Returns:
        Ed25519 public key

    Raises:
        KeyImportError: If load fails or file doesn't exist
    """
    try:
        if not file_path.exists():
            raise KeyImportError(f"Public key file not found: {file_path}")

        with open(file_path, "r") as f:
            pem_data = f.read()

        return import_public_key_pem(pem_data)

    except KeyImportError:
        raise
    except Exception as e:
        logger.error(f"Failed to load public key from {file_path}: {e}")
        raise KeyImportError(f"Public key load failed: {e}") from e


# ============================================================================
# Bundle Signing & Verification (G1)
# ============================================================================


def _bundle_to_signable_data(bundle_dict: dict) -> bytes:
    """
    Convert bundle dictionary to canonical bytes for signing.

    Creates deterministic representation by:
    1. Excluding signature fields
    2. Sorting keys alphabetically
    3. Using compact JSON (no whitespace)

    Args:
        bundle_dict: Bundle data as dictionary

    Returns:
        Canonical bytes representation

    Raises:
        SignatureError: If serialization fails
    """
    import json

    try:
        # Remove signature fields to get original bundle data
        signable = bundle_dict.copy()
        signable.pop("signature", None)
        signable.pop("signature_algorithm", None)
        signable.pop("signed_by_key_id", None)
        signable.pop("signed_at", None)

        # Convert to canonical JSON (sorted keys, compact)
        canonical_json = json.dumps(signable, sort_keys=True, separators=(",", ":"))

        return canonical_json.encode("utf-8")

    except Exception as e:
        logger.error(f"Failed to serialize bundle for signing: {e}")
        raise SignatureError(f"Bundle serialization failed: {e}") from e


def sign_bundle(
    bundle_dict: dict, private_key: ed25519.Ed25519PrivateKey
) -> str:
    """
    Sign a bundle using Ed25519 private key.

    Creates a detached signature of the bundle's canonical representation.
    The signature is hex-encoded (128 characters).

    Args:
        bundle_dict: Bundle data as dictionary (must include id, name, version, etc.)
        private_key: Ed25519 private key

    Returns:
        Hex-encoded signature string (128 characters)

    Raises:
        SignatureError: If signing fails

    Example:
        >>> from backend.app.modules.sovereign_mode.crypto import generate_keypair, sign_bundle
        >>> private_key, public_key = generate_keypair()
        >>> bundle = {"id": "test", "name": "Test", "version": "1.0.0", ...}
        >>> signature = sign_bundle(bundle, private_key)
        >>> len(signature)
        128
    """
    try:
        # Convert bundle to canonical bytes
        signable_data = _bundle_to_signable_data(bundle_dict)

        # Sign the data
        signature_hex = sign_data_hex(signable_data, private_key)

        logger.info(f"Signed bundle: {bundle_dict.get('id', 'unknown')}")
        return signature_hex

    except SignatureError:
        raise
    except Exception as e:
        logger.error(f"Bundle signing failed: {e}")
        raise SignatureError(f"Failed to sign bundle: {e}") from e


def verify_bundle_signature(
    bundle_dict: dict,
    signature_hex: str,
    public_key: ed25519.Ed25519PublicKey,
) -> bool:
    """
    Verify a bundle's Ed25519 signature.

    Args:
        bundle_dict: Bundle data as dictionary (with or without signature fields)
        signature_hex: Hex-encoded signature to verify (128 characters)
        public_key: Ed25519 public key

    Returns:
        True if signature is valid, False otherwise

    Raises:
        SignatureError: If verification process fails (not same as invalid signature)

    Example:
        >>> from backend.app.modules.sovereign_mode.crypto import (
        ...     generate_keypair, sign_bundle, verify_bundle_signature
        ... )
        >>> private_key, public_key = generate_keypair()
        >>> bundle = {"id": "test", "name": "Test", "version": "1.0.0", ...}
        >>> signature = sign_bundle(bundle, private_key)
        >>> verify_bundle_signature(bundle, signature, public_key)
        True
    """
    try:
        # Convert bundle to canonical bytes (same as signing)
        signable_data = _bundle_to_signable_data(bundle_dict)

        # Verify the signature
        is_valid = verify_signature_hex(signable_data, signature_hex, public_key)

        if is_valid:
            logger.info(
                f"Bundle signature VALID: {bundle_dict.get('id', 'unknown')}"
            )
        else:
            logger.warning(
                f"Bundle signature INVALID: {bundle_dict.get('id', 'unknown')}"
            )

        return is_valid

    except SignatureError:
        raise
    except Exception as e:
        logger.error(f"Bundle signature verification failed: {e}")
        raise SignatureError(f"Failed to verify bundle signature: {e}") from e
