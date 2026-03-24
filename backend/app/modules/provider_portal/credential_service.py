from __future__ import annotations

import base64
import hashlib
import os

from cryptography.fernet import Fernet


def _derive_fernet_key() -> bytes:
    source = (
        os.getenv("BRAIN_PROVIDER_PORTAL_SECRET_KEY")
        or os.getenv("JWT_SECRET_KEY")
        or os.getenv("BRAIN_DMZ_GATEWAY_SECRET")
        or "brain-provider-portal-dev-key"
    )
    digest = hashlib.sha256(source.encode("utf-8")).digest()
    return base64.urlsafe_b64encode(digest)


class ProviderCredentialService:
    def __init__(self) -> None:
        self._fernet = Fernet(_derive_fernet_key())

    def encrypt(self, raw_secret: str) -> str:
        return self._fernet.encrypt(raw_secret.encode("utf-8")).decode("utf-8")

    def decrypt(self, ciphertext: str) -> str:
        return self._fernet.decrypt(ciphertext.encode("utf-8")).decode("utf-8")

    @staticmethod
    def masked_hint(raw_secret: str) -> str:
        last4 = raw_secret[-4:] if len(raw_secret) >= 4 else raw_secret
        return f"****{last4}"


_provider_credential_service: ProviderCredentialService | None = None


def get_provider_credential_service() -> ProviderCredentialService:
    global _provider_credential_service
    if _provider_credential_service is None:
        _provider_credential_service = ProviderCredentialService()
    return _provider_credential_service
