"""
JWT Middleware - JWKS-based token validation for BRAiN Auth

Provides:
- JWKS client with caching
- Token signature verification
- Issuer/Audience validation
- Scope extraction
- JWTBearer security dependency
"""

from __future__ import annotations

import asyncio
import logging
from typing import Any, Dict, List, Optional, Set
from dataclasses import dataclass
from datetime import datetime, timedelta

import httpx
from fastapi import Request, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from jose import jwt, JWTError, ExpiredSignatureError
from jose.exceptions import JWTClaimsError
from starlette.middleware.base import BaseHTTPMiddleware

from app.core.config import get_settings

logger = logging.getLogger(__name__)


@dataclass
class JWKSKey:
    """Represents a single JWKS key"""
    kid: str
    kty: str
    alg: str
    use: str
    n: Optional[str] = None  # RSA modulus
    e: Optional[str] = None  # RSA exponent
    x: Optional[str] = None  # EC x coordinate
    y: Optional[str] = None  # EC y coordinate
    crv: Optional[str] = None  # EC curve
    x5c: Optional[List[str]] = None  # X.509 certificate chain
    x5t: Optional[str] = None  # X.509 certificate SHA-1 thumbprint
    x5t_s256: Optional[str] = None  # X.509 certificate SHA-256 thumbprint

    def to_jwk_dict(self) -> Dict[str, Any]:
        """Convert to JWK dictionary format for python-jose"""
        jwk = {
            "kty": self.kty,
            "alg": self.alg,
            "use": self.use,
        }
        if self.kid:
            jwk["kid"] = self.kid
        if self.n:
            jwk["n"] = self.n
        if self.e:
            jwk["e"] = self.e
        if self.x:
            jwk["x"] = self.x
        if self.y:
            jwk["y"] = self.y
        if self.crv:
            jwk["crv"] = self.crv
        if self.x5c:
            jwk["x5c"] = self.x5c
        return jwk


@dataclass
class TokenPayload:
    """Validated token payload"""
    sub: str  # Subject (user ID)
    iss: str  # Issuer
    aud: List[str]  # Audience
    exp: datetime  # Expiration
    iat: datetime  # Issued at
    scope: List[str]  # Scopes
    roles: List[str]  # Roles
    token_type: str  # "human" or "agent"
    email: Optional[str] = None
    name: Optional[str] = None
    tenant_id: Optional[str] = None
    agent_id: Optional[str] = None  # For agent tokens
    parent_agent_id: Optional[str] = None  # For agent tokens
    raw_claims: Dict[str, Any] = None  # All claims

    def has_scope(self, scope: str) -> bool:
        """Check if token has a specific scope"""
        return scope in self.scope

    def has_any_scope(self, scopes: List[str]) -> bool:
        """Check if token has any of the specified scopes"""
        return any(s in self.scope for s in scopes)

    def has_role(self, role: str) -> bool:
        """Check if token has a specific role"""
        return role in self.roles

    def has_any_role(self, roles: List[str]) -> bool:
        """Check if token has any of the specified roles"""
        return any(r in self.roles for r in roles)


class JWKSClient:
    """
    JWKS client with caching for dynamic key fetching.
    
    Supports:
    - RSA (RS256, RS384, RS512)
    - ECDSA (ES256, ES384, ES512)
    - Automatic key rotation handling
    - Configurable cache TTL
    """
    
    def __init__(
        self,
        jwks_url: str,
        cache_ttl_seconds: int = 3600,
        request_timeout: float = 10.0,
    ):
        self.jwks_url = jwks_url
        self.cache_ttl = timedelta(seconds=cache_ttl_seconds)
        self.request_timeout = request_timeout
        self._keys: Dict[str, JWKSKey] = {}
        self._last_fetch: Optional[datetime] = None
        self._lock = asyncio.Lock()
        self._client: Optional[httpx.AsyncClient] = None
    
    async def _get_client(self) -> httpx.AsyncClient:
        """Get or create HTTP client"""
        if self._client is None:
            self._client = httpx.AsyncClient(timeout=self.request_timeout)
        return self._client
    
    async def close(self):
        """Close HTTP client"""
        if self._client:
            await self._client.aclose()
            self._client = None
    
    def _is_cache_valid(self) -> bool:
        """Check if cached keys are still valid"""
        if not self._last_fetch:
            return False
        return datetime.utcnow() - self._last_fetch < self.cache_ttl
    
    async def fetch_keys(self) -> Dict[str, JWKSKey]:
        """Fetch JWKS from the configured URL"""
        client = await self._get_client()
        
        try:
            response = await client.get(self.jwks_url)
            response.raise_for_status()
            jwks_data = response.json()
            
            keys = {}
            for key_data in jwks_data.get("keys", []):
                key = JWKSKey(
                    kid=key_data.get("kid", ""),
                    kty=key_data.get("kty", ""),
                    alg=key_data.get("alg", ""),
                    use=key_data.get("use", "sig"),
                    n=key_data.get("n"),
                    e=key_data.get("e"),
                    x=key_data.get("x"),
                    y=key_data.get("y"),
                    crv=key_data.get("crv"),
                    x5c=key_data.get("x5c"),
                    x5t=key_data.get("x5t"),
                    x5t_s256=key_data.get("x5t#S256"),
                )
                if key.kid:
                    keys[key.kid] = key
            
            logger.info(f"Fetched {len(keys)} keys from JWKS endpoint")
            return keys
            
        except httpx.HTTPStatusError as e:
            logger.error(f"JWKS fetch failed: HTTP {e.response.status_code}")
            raise
        except httpx.RequestError as e:
            logger.error(f"JWKS fetch failed: {e}")
            raise
        except Exception as e:
            logger.error(f"JWKS parse failed: {e}")
            raise
    
    async def get_key(self, kid: str) -> Optional[JWKSKey]:
        """Get a specific key by ID, refreshing cache if needed"""
        async with self._lock:
            # Check if key exists in cache
            if kid in self._keys and self._is_cache_valid():
                return self._keys[kid]
            
            # Refresh cache
            try:
                self._keys = await self.fetch_keys()
                self._last_fetch = datetime.utcnow()
            except Exception as e:
                logger.error(f"Failed to refresh JWKS cache: {e}")
                # Return cached key even if expired (fail open with stale data)
                if kid in self._keys:
                    logger.warning(f"Using expired cached key for kid={kid}")
                    return self._keys[kid]
                raise
            
            return self._keys.get(kid)
    
    async def get_all_keys(self) -> Dict[str, JWKSKey]:
        """Get all keys, refreshing cache if needed"""
        async with self._lock:
            if not self._is_cache_valid():
                try:
                    self._keys = await self.fetch_keys()
                    self._last_fetch = datetime.utcnow()
                except Exception as e:
                    logger.error(f"Failed to refresh JWKS cache: {e}")
                    if not self._keys:
                        raise
            
            return self._keys.copy()


class JWTValidator:
    """
    JWT token validator with JWKS support.
    
    Validates:
    - Signature (using JWKS)
    - Issuer
    - Audience
    - Expiration
    - Extracts scopes and roles
    """
    
    def __init__(
        self,
        jwks_client: JWKSClient,
        issuer: str,
        audience: str,
        allowed_algorithms: Optional[List[str]] = None,
    ):
        self.jwks_client = jwks_client
        self.issuer = issuer
        self.audience = audience
        self.allowed_algorithms = allowed_algorithms or ["RS256", "RS384", "RS512", "ES256", "ES384", "ES512"]
    
    def _get_unverified_header(self, token: str) -> Dict[str, Any]:
        """Extract header without verification"""
        try:
            return jwt.get_unverified_header(token)
        except JWTError as e:
            raise ValueError(f"Invalid token header: {e}")
    
    def _get_unverified_claims(self, token: str) -> Dict[str, Any]:
        """Extract claims without verification"""
        try:
            return jwt.get_unverified_claims(token)
        except JWTError as e:
            raise ValueError(f"Invalid token claims: {e}")
    
    async def validate(self, token: str) -> TokenPayload:
        """
        Validate a JWT token and return the payload.
        
        Raises:
            ValueError: If token is invalid
            ExpiredSignatureError: If token is expired
            JWTClaimsError: If claims are invalid
        """
        # Get token header to find the key
        header = self._get_unverified_header(token)
        kid = header.get("kid")
        alg = header.get("alg")
        
        if not kid:
            raise ValueError("Token missing 'kid' header")
        
        if alg not in self.allowed_algorithms:
            raise ValueError(f"Algorithm '{alg}' not allowed")
        
        # Fetch the signing key
        jwks_key = await self.jwks_client.get_key(kid)
        if not jwks_key:
            raise ValueError(f"Key with kid='{kid}' not found in JWKS")
        
        # Validate the token
        try:
            claims = jwt.decode(
                token,
                jwks_key.to_jwk_dict(),
                algorithms=[alg],
                issuer=self.issuer,
                audience=self.audience,
            )
        except ExpiredSignatureError:
            raise
        except JWTClaimsError:
            raise
        except JWTError as e:
            raise ValueError(f"Token validation failed: {e}")
        
        # Extract scopes
        scope_str = claims.get("scope", "")
        if isinstance(scope_str, str):
            scopes = [s.strip() for s in scope_str.split() if s.strip()]
        elif isinstance(scope_str, list):
            scopes = scope_str
        else:
            scopes = []
        
        # Extract roles
        roles = claims.get("roles", []) or claims.get("role", [])
        if isinstance(roles, str):
            roles = [roles]
        
        # Determine token type
        token_type = claims.get("type", "human")
        if token_type not in ("human", "agent"):
            token_type = "human"
        
        # Parse timestamps
        exp_ts = claims.get("exp")
        iat_ts = claims.get("iat")
        
        return TokenPayload(
            sub=claims.get("sub", ""),
            iss=claims.get("iss", ""),
            aud=claims.get("aud", []) if isinstance(claims.get("aud"), list) else [claims.get("aud", "")],
            exp=datetime.utcfromtimestamp(exp_ts) if exp_ts else datetime.utcnow(),
            iat=datetime.utcfromtimestamp(iat_ts) if iat_ts else datetime.utcnow(),
            scope=scopes,
            roles=roles,
            token_type=token_type,
            email=claims.get("email"),
            name=claims.get("name"),
            tenant_id=claims.get("tenant_id") or claims.get("org_id"),
            agent_id=claims.get("agent_id"),
            parent_agent_id=claims.get("parent_agent_id"),
            raw_claims=claims,
        )


# Global JWKS client and validator instances
_jwks_client: Optional[JWKSClient] = None
_jwt_validator: Optional[JWTValidator] = None


def get_jwks_client() -> JWKSClient:
    """Get or create the global JWKS client"""
    global _jwks_client
    if _jwks_client is None:
        settings = get_settings()
        if not settings.jwt_jwks_url:
            raise RuntimeError("JWT_JWKS_URL not configured")
        
        _jwks_client = JWKSClient(
            jwks_url=settings.jwt_jwks_url,
            cache_ttl_seconds=settings.jwks_cache_ttl_seconds,
        )
    return _jwks_client


def get_jwt_validator() -> JWTValidator:
    """Get or create the global JWT validator"""
    global _jwt_validator
    if _jwt_validator is None:
        settings = get_settings()
        if not settings.jwt_issuer or not settings.jwt_audience:
            raise RuntimeError("JWT_ISSUER and JWT_AUDIENCE must be configured")
        
        _jwt_validator = JWTValidator(
            jwks_client=get_jwks_client(),
            issuer=settings.jwt_issuer,
            audience=settings.jwt_audience,
        )
    return _jwt_validator


async def reset_jwks_cache():
    """Reset the JWKS cache (useful for testing)"""
    global _jwks_client, _jwt_validator
    if _jwks_client:
        await _jwks_client.close()
    _jwks_client = None
    _jwt_validator = None


class JWTAuthenticationMiddleware(BaseHTTPMiddleware):
    """
    Middleware that validates JWT tokens on incoming requests.
    
    Adds the validated token payload to request.state.token_payload
    for use by downstream handlers.
    """
    
    def __init__(
        self,
        app,
        excluded_paths: Optional[List[str]] = None,
        header_name: str = "Authorization",
    ):
        super().__init__(app)
        self.excluded_paths = set(excluded_paths or [])
        self.header_name = header_name
    
    def _is_path_excluded(self, path: str) -> bool:
        """Check if path should skip JWT validation"""
        return any(path.startswith(excluded) for excluded in self.excluded_paths)
    
    async def dispatch(self, request: Request, call_next):
        """Process request with optional JWT validation"""
        # Skip excluded paths
        if self._is_path_excluded(request.url.path):
            return await call_next(request)
        
        # Get authorization header
        auth_header = request.headers.get(self.header_name, "")
        
        if auth_header.startswith("Bearer "):
            token = auth_header[7:]
            
            try:
                validator = get_jwt_validator()
                payload = await validator.validate(token)
                request.state.token_payload = payload
                request.state.authenticated = True
                logger.debug(f"Authenticated: {payload.sub} ({payload.token_type})")
            except ExpiredSignatureError:
                request.state.token_payload = None
                request.state.authenticated = False
                request.state.auth_error = "Token expired"
                logger.warning("JWT validation failed: Token expired")
            except Exception as e:
                request.state.token_payload = None
                request.state.authenticated = False
                request.state.auth_error = str(e)
                logger.warning(f"JWT validation failed: {e}")
        else:
            request.state.token_payload = None
            request.state.authenticated = False
        
        return await call_next(request)


class JWTBearer(HTTPBearer):
    """
    FastAPI security dependency for JWT Bearer tokens.
    
    Usage:
        @router.get("/protected")
        async def protected_endpoint(
            token_payload: TokenPayload = Depends(JWTBearer())
        ):
            return {"user": token_payload.sub}
    """
    
    def __init__(
        self,
        auto_error: bool = True,
        required_scopes: Optional[List[str]] = None,
        required_roles: Optional[List[str]] = None,
    ):
        super().__init__(auto_error=auto_error)
        self.required_scopes = required_scopes or []
        self.required_roles = required_roles or []
    
    async def __call__(
        self, request: Request
    ) -> Optional[TokenPayload]:
        """Validate JWT token from request"""
        credentials: HTTPAuthorizationCredentials = await super().__call__(request)
        
        if not credentials:
            if self.auto_error:
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="Authorization header missing",
                    headers={"WWW-Authenticate": "Bearer"},
                )
            return None
        
        if credentials.scheme != "Bearer":
            if self.auto_error:
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="Invalid authentication scheme. Use Bearer.",
                    headers={"WWW-Authenticate": "Bearer"},
                )
            return None
        
        token = credentials.credentials
        
        try:
            validator = get_jwt_validator()
            payload = await validator.validate(token)
            
            # Check required scopes
            if self.required_scopes:
                missing_scopes = [s for s in self.required_scopes if not payload.has_scope(s)]
                if missing_scopes:
                    raise HTTPException(
                        status_code=status.HTTP_403_FORBIDDEN,
                        detail=f"Missing required scopes: {', '.join(missing_scopes)}",
                    )
            
            # Check required roles
            if self.required_roles:
                if not payload.has_any_role(self.required_roles):
                    raise HTTPException(
                        status_code=status.HTTP_403_FORBIDDEN,
                        detail=f"Missing required role. One of: {', '.join(self.required_roles)}",
                    )
            
            return payload
            
        except ExpiredSignatureError:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Token has expired",
                headers={"WWW-Authenticate": "Bearer error=\"invalid_token\" error_description=\"Token expired\""},
            )
        except JWTClaimsError as e:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail=f"Invalid token claims: {str(e)}",
                headers={"WWW-Authenticate": "Bearer"},
            )
        except Exception as e:
            logger.error(f"JWT validation error: {e}")
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid token",
                headers={"WWW-Authenticate": "Bearer"},
            )


# Convenience instances
jwt_bearer = JWTBearer()
optional_jwt_bearer = JWTBearer(auto_error=False)
