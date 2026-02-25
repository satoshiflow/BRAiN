"""
Token Keys Management - RSA Key Loading and JWKS Generation

Provides:
- RSA private key loading from environment
- JWKS endpoint generation
- Key ID derivation (SHA256 of public key DER, first 16 chars)
"""

import os
import hashlib
import base64
from typing import Dict, Any, Optional
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric import rsa
from cryptography.hazmat.backends import default_backend


class TokenKeyManager:
    """
    Manages RSA key pair for JWT signing and JWKS generation.
    
    Key ID (kid) is derived as: SHA256(public_key_der)[:16]
    This provides a stable, unique identifier for the key.
    """
    
    def __init__(self):
        self._private_key = None
        self._public_key = None
        self._key_id = None
        self._jwks_cache = None
    
    def _load_private_key_from_pem(self, pem_data: str) -> rsa.RSAPrivateKey:
        """Load RSA private key from PEM string"""
        pem_bytes = pem_data.encode('utf-8') if isinstance(pem_data, str) else pem_data
        
        # Handle both PKCS#8 and PKCS#1 formats
        try:
            private_key = serialization.load_pem_private_key(
                pem_bytes,
                password=None,
                backend=default_backend()
            )
        except Exception as e:
            raise ValueError(f"Failed to load private key: {e}")
        
        if not isinstance(private_key, rsa.RSAPrivateKey):
            raise ValueError("Private key must be an RSA key")
        
        return private_key
    
    def _derive_key_id(self, public_key: rsa.RSAPublicKey) -> str:
        """
        Derive Key ID from public key.
        
        Algorithm: SHA256(public_key_der)[:16]
        Returns: 16-character hex string
        """
        # Export public key in DER format (PKCS#1 SubjectPublicKeyInfo)
        public_key_der = public_key.public_bytes(
            encoding=serialization.Encoding.DER,
            format=serialization.PublicFormat.SubjectPublicKeyInfo
        )
        
        # Calculate SHA256 hash and take first 16 bytes (32 hex chars)
        hash_digest = hashlib.sha256(public_key_der).hexdigest()[:16]
        
        return hash_digest
    
    def _extract_jwk_components(self, public_key: rsa.RSAPublicKey) -> Dict[str, str]:
        """
        Extract n (modulus) and e (exponent) for JWK format.
        
        Returns base64url-encoded values.
        """
        public_numbers = public_key.public_numbers()
        
        # Convert modulus to base64url (no padding)
        n_bytes = public_numbers.n.to_bytes(
            (public_numbers.n.bit_length() + 7) // 8,
            byteorder='big'
        )
        n_b64 = base64.urlsafe_b64encode(n_bytes).rstrip(b'=').decode('ascii')
        
        # Convert exponent to base64url
        e_bytes = public_numbers.e.to_bytes(
            (public_numbers.e.bit_length() + 7) // 8,
            byteorder='big'
        )
        e_b64 = base64.urlsafe_b64encode(e_bytes).rstrip(b'=').decode('ascii')
        
        return {"n": n_b64, "e": e_b64}
    
    def load_key_from_env(self, env_var: str = "BRAIN_JWT_PRIVATE_KEY") -> None:
        """
        Load RSA private key from environment variable.
        
        Args:
            env_var: Name of environment variable containing PEM-encoded private key
        
        Raises:
            ValueError: If key is not found or invalid
        """
        pem_data = os.getenv(env_var)
        
        if not pem_data:
            raise ValueError(
                f"Environment variable {env_var} is not set. "
                "Please set BRAIN_JWT_PRIVATE_KEY with your RSA private key."
            )
        
        # Handle potential line ending issues
        pem_data = pem_data.replace('\\n', '\n')
        
        self._private_key = self._load_private_key_from_pem(pem_data)
        self._public_key = self._private_key.public_key()
        self._key_id = self._derive_key_id(self._public_key)
        self._jwks_cache = None  # Invalidate cache
    
    def get_key_id(self) -> str:
        """Get the derived Key ID for the current key"""
        if not self._key_id:
            raise RuntimeError("No key loaded. Call load_key_from_env() first.")
        return self._key_id
    
    def get_private_key(self) -> rsa.RSAPrivateKey:
        """Get the loaded RSA private key"""
        if not self._private_key:
            raise RuntimeError("No key loaded. Call load_key_from_env() first.")
        return self._private_key
    
    def get_public_key(self) -> rsa.RSAPublicKey:
        """Get the RSA public key"""
        if not self._public_key:
            raise RuntimeError("No key loaded. Call load_key_from_env() first.")
        return self._public_key
    
    def get_jwks(self) -> Dict[str, Any]:
        """
        Generate JWKS (JSON Web Key Set) for the current key.
        
        Returns:
            JWKS dictionary with a single key containing:
            - kty: Key type ("RSA")
            - kid: Key ID
            - use: Intended use ("sig" for signing)
            - alg: Algorithm ("RS256")
            - n: Modulus (base64url-encoded)
            - e: Exponent (base64url-encoded)
        """
        if self._jwks_cache:
            return self._jwks_cache
        
        if not self._public_key:
            raise RuntimeError("No key loaded. Call load_key_from_env() first.")
        
        jwk_components = self._extract_jwk_components(self._public_key)
        
        jwk = {
            "kty": "RSA",
            "kid": self._key_id,
            "use": "sig",
            "alg": "RS256",
            "n": jwk_components["n"],
            "e": jwk_components["e"]
        }
        
        self._jwks_cache = {"keys": [jwk]}
        return self._jwks_cache
    
    def get_jwks_json(self) -> str:
        """Get JWKS as JSON string"""
        import json
        return json.dumps(self.get_jwks(), indent=2)
    
    def get_public_key_pem(self) -> str:
        """Get public key in PEM format for external distribution"""
        if not self._public_key:
            raise RuntimeError("No key loaded. Call load_key_from_env() first.")
        
        pem_bytes = self._public_key.public_bytes(
            encoding=serialization.Encoding.PEM,
            format=serialization.PublicFormat.SubjectPublicKeyInfo
        )
        return pem_bytes.decode('utf-8')


# Global singleton instance
_token_key_manager: Optional[TokenKeyManager] = None


def get_token_key_manager() -> TokenKeyManager:
    """
    Get or create the global TokenKeyManager instance.
    
    Returns:
        TokenKeyManager singleton instance
    """
    global _token_key_manager
    if _token_key_manager is None:
        _token_key_manager = TokenKeyManager()
    return _token_key_manager


def init_token_keys(env_var: str = "BRAIN_JWT_PRIVATE_KEY") -> TokenKeyManager:
    """
    Initialize token keys from environment.
    
    Args:
        env_var: Environment variable name containing the private key
    
    Returns:
        Initialized TokenKeyManager
    
    Example:
        # In application startup:
        manager = init_token_keys()
        print(f"Key ID: {manager.get_key_id()}")
    """
    manager = get_token_key_manager()
    manager.load_key_from_env(env_var)
    return manager


def reset_token_keys() -> None:
    """Reset the global token key manager (useful for testing)"""
    global _token_key_manager
    _token_key_manager = None


# Convenience functions for direct access
def get_current_key_id() -> str:
    """Get the current key ID (requires initialization)"""
    return get_token_key_manager().get_key_id()


def get_current_jwks() -> Dict[str, Any]:
    """Get current JWKS (requires initialization)"""
    return get_token_key_manager().get_jwks()


def get_signing_key() -> rsa.RSAPrivateKey:
    """Get the current signing key (requires initialization)"""
    return get_token_key_manager().get_private_key()
