"""
Course Factory Certificate Signer - Sprint 14

Ed25519 signature generation and verification for course certificates.
Reuses G1 crypto patterns where applicable, minimal implementation.
"""

from __future__ import annotations

import os
from pathlib import Path
from typing import Tuple, Optional
from loguru import logger

from cryptography.hazmat.primitives.asymmetric.ed25519 import (
    Ed25519PrivateKey,
    Ed25519PublicKey,
)
from cryptography.hazmat.primitives import serialization

from app.modules.course_factory.monetization_models import (
    CertificatePayload,
    Certificate,
    CertificateVerificationResult,
)


# ========================================
# Key Management
# ========================================

class CertificateKeyStore:
    """
    Ed25519 key storage for certificate signing.

    Storage layout:
    - storage/courses/cert_keys/private.pem (0600 permissions)
    - storage/courses/cert_keys/public.pem
    """

    def __init__(self, key_dir: str = "storage/courses/cert_keys"):
        self.key_dir = Path(key_dir)
        self.key_dir.mkdir(parents=True, exist_ok=True)

        self.private_key_path = self.key_dir / "private.pem"
        self.public_key_path = self.key_dir / "public.pem"

        # Ensure keys exist
        self._ensure_keys()

    def _ensure_keys(self):
        """Ensure Ed25519 key pair exists, generate if missing."""
        if not self.private_key_path.exists() or not self.public_key_path.exists():
            logger.info("[CertificateKeyStore] Generating new Ed25519 key pair")
            self._generate_keys()
        else:
            logger.debug("[CertificateKeyStore] Using existing Ed25519 key pair")

    def _generate_keys(self):
        """Generate new Ed25519 key pair."""
        # Generate private key
        private_key = Ed25519PrivateKey.generate()

        # Serialize private key
        private_pem = private_key.private_bytes(
            encoding=serialization.Encoding.PEM,
            format=serialization.PrivateFormat.PKCS8,
            encryption_algorithm=serialization.NoEncryption()
        )

        # Write private key with restrictive permissions
        with open(self.private_key_path, 'wb') as f:
            f.write(private_pem)
        os.chmod(self.private_key_path, 0o600)  # Read/write for owner only

        # Serialize public key
        public_key = private_key.public_key()
        public_pem = public_key.public_bytes(
            encoding=serialization.Encoding.PEM,
            format=serialization.PublicFormat.SubjectPublicKeyInfo
        )

        # Write public key
        with open(self.public_key_path, 'wb') as f:
            f.write(public_pem)

        logger.info(f"[CertificateKeyStore] Keys generated at {self.key_dir}")

    def load_private_key(self) -> Ed25519PrivateKey:
        """Load private key."""
        with open(self.private_key_path, 'rb') as f:
            private_pem = f.read()

        private_key = serialization.load_pem_private_key(
            private_pem,
            password=None
        )

        if not isinstance(private_key, Ed25519PrivateKey):
            raise ValueError("Loaded key is not Ed25519")

        return private_key

    def load_public_key(self) -> Ed25519PublicKey:
        """Load public key."""
        with open(self.public_key_path, 'rb') as f:
            public_pem = f.read()

        public_key = serialization.load_pem_public_key(public_pem)

        if not isinstance(public_key, Ed25519PublicKey):
            raise ValueError("Loaded key is not Ed25519")

        return public_key


# ========================================
# Certificate Signer
# ========================================

class CertificateSigner:
    """
    Ed25519 certificate signing service.

    Responsibilities:
    - Sign certificate payloads
    - Verify signatures
    - Generate deterministic canonical JSON
    """

    def __init__(self, key_store: Optional[CertificateKeyStore] = None):
        self.key_store = key_store or CertificateKeyStore()

    def sign_certificate(self, payload: CertificatePayload) -> Certificate:
        """
        Sign certificate payload with Ed25519.

        Args:
            payload: CertificatePayload instance

        Returns:
            Certificate with signature

        Raises:
            Exception: If signing fails
        """
        try:
            # Get canonical JSON
            canonical_json = payload.to_canonical_json()

            # Load private key
            private_key = self.key_store.load_private_key()

            # Sign (Ed25519 signature is 64 bytes = 128 hex chars)
            signature_bytes = private_key.sign(canonical_json.encode('utf-8'))

            # Convert to hex
            signature_hex = signature_bytes.hex()

            logger.info(
                f"[CertificateSigner] Signed certificate: {payload.certificate_id}"
            )

            return Certificate(
                payload=payload,
                signature_hex=signature_hex
            )

        except Exception as e:
            logger.error(f"[CertificateSigner] Signing failed: {e}")
            raise

    def verify_certificate(
        self,
        payload: CertificatePayload,
        signature_hex: str
    ) -> CertificateVerificationResult:
        """
        Verify certificate signature.

        Args:
            payload: CertificatePayload instance
            signature_hex: Signature in hex format

        Returns:
            CertificateVerificationResult
        """
        try:
            # Validate signature format
            if len(signature_hex) != 128:
                return CertificateVerificationResult(
                    valid=False,
                    reason=f"Invalid signature length: {len(signature_hex)} (expected 128)"
                )

            # Get canonical JSON
            canonical_json = payload.to_canonical_json()

            # Load public key
            public_key = self.key_store.load_public_key()

            # Convert signature from hex
            signature_bytes = bytes.fromhex(signature_hex)

            # Verify
            public_key.verify(signature_bytes, canonical_json.encode('utf-8'))

            logger.info(
                f"[CertificateSigner] Certificate verified: {payload.certificate_id}"
            )

            return CertificateVerificationResult(
                valid=True,
                certificate_id=payload.certificate_id,
                issued_at=payload.issued_at
            )

        except ValueError as e:
            logger.warning(f"[CertificateSigner] Verification failed (invalid): {e}")
            return CertificateVerificationResult(
                valid=False,
                reason=f"Invalid signature: {str(e)}"
            )
        except Exception as e:
            logger.error(f"[CertificateSigner] Verification failed: {e}")
            return CertificateVerificationResult(
                valid=False,
                reason=f"Verification error: {str(e)}"
            )


# ========================================
# Singleton
# ========================================

_signer: Optional[CertificateSigner] = None


def get_certificate_signer() -> CertificateSigner:
    """Get CertificateSigner singleton."""
    global _signer
    if _signer is None:
        _signer = CertificateSigner()
    return _signer
