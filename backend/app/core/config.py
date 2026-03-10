import os
from functools import lru_cache
from typing import Literal, Union
from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

# Runtime Mode Detection (Runtime Deployment Contract)
def detect_runtime_mode() -> Literal["local", "remote"]:
    """
    Detect runtime mode based on environment markers.
    
    Priority:
    1. Explicit BRAIN_RUNTIME_MODE (local|remote)
    2. Auto-detection (Coolify markers, hostname, Docker)
    3. Default: remote (fail-safe)
    
    Returns:
        "local" for laptop dev, "remote" for Coolify/production
    """
    explicit = os.getenv("BRAIN_RUNTIME_MODE", "auto").lower()
    if explicit in ["local", "remote"]:
        return explicit  # type: ignore
    
    # Auto-detection: Remote markers (Coolify)
    if os.getenv("SERVICE_FQDN_BACKEND") or os.getenv("COOLIFY_APP_ID"):
        return "remote"
    
    # Auto-detection: Docker container check
    if os.path.exists("/.dockerenv"):
        # Inside container - check if Coolify (remote) or local docker-compose
        if os.getenv("COOLIFY_APP_ID"):
            return "remote"
        # Local docker-compose
        return "local"
    
    # Default: remote (fail-safe)
    return "remote"

class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    app_name: str = "BRAiN Core v1.0"
    environment: str = "local"

    api_prefix: str = "/api"

    # Runtime Mode Detection (Runtime Deployment Contract)
    runtime_mode: Literal["local", "remote"] = Field(
        default_factory=detect_runtime_mode,
        description="Runtime environment: local (laptop dev) or remote (Coolify/production)",
    )

    # Database - mode-aware defaults
    database_url: str = Field(
        default_factory=lambda: (
            "postgresql+asyncpg://brain:brain_dev_pass@localhost:5433/brain_dev"
            if detect_runtime_mode() == "local"
            else os.getenv("DATABASE_URL", "")  # Required in remote, fail if missing
        ),
        description="PostgreSQL connection URL (local default or required remote)",
    )

    # Redis - mode-aware defaults
    redis_url: str = Field(
        default_factory=lambda: (
            "redis://localhost:6380/0"
            if detect_runtime_mode() == "local"
            else os.getenv("REDIS_URL", "")  # Required in remote, fail if missing
        ),
        description="Redis connection URL (local default or required remote)",
    )

    # Qdrant (NEW - separate Coolify service)
    qdrant_url: str = "http://localhost:6333"

    # Ollama (NEW - separate Coolify service)
    ollama_host: str = "http://localhost:11434"

    # JWT Configuration (NEW - BRAiN Auth Foundation)
    jwt_issuer: str = "https://brain.falklabs.de"
    jwt_audience: str = "brain-api"
    jwt_jwks_url: str = "https://brain.falklabs.de/.well-known/jwks.json"
    jwks_cache_ttl_seconds: int = 3600  # 1 hour cache for JWKS keys

    # Token Key Configuration (A1 - Token Architecture)
    jwt_private_key_pem: str = ""  # RSA private key PEM (from BRAIN_JWT_PRIVATE_KEY env)
    jwt_algorithm: str = "RS256"  # JWT signing algorithm
    access_token_expire_minutes: int = 15  # Short-lived access tokens
    refresh_token_expire_days: int = 7  # Long-lived refresh tokens
    agent_token_expire_hours: int = 24  # Agent/service account tokens

    # CORS - mode-aware defaults (Runtime Deployment Contract)
    cors_origins: Union[str, list[str]] = Field(
        default_factory=lambda: (
            [
                "http://localhost:3000",
                "http://localhost:3001",
                "http://localhost:3002",
                "http://127.0.0.1:3000",
                "http://127.0.0.1:3001",
                "http://127.0.0.1:3002",
            ]
            if detect_runtime_mode() == "local"
            else [
                "https://control.brain.falklabs.de",
                "https://axe.brain.falklabs.de",
            ]
        ),
        description="CORS allowed origins (mode-aware: local localhost, remote production domains)",
    )

    # OpenRouter Configuration (Optional - for external LLM access)
    openrouter_api_key: str = ""
    openrouter_model: str = "moonshotai/kimi-k2.5"
    openrouter_site_url: str = "http://localhost:3000"
    openrouter_site_name: str = "BRAiN"

    # DMZ Gateway Secret (Optional - for trust tier validation)
    # SECURITY: No default - must be set via environment variable
    brain_dmz_gateway_secret: str = ""

    @field_validator("cors_origins", mode="before")
    @classmethod
    def parse_cors_origins(cls, v):
        """Parse CORS origins from CSV string, JSON array, or handle empty/None.
        
        SECURITY-001: Wildcard "*" is REJECTED in production.
        """
        # Handle None or empty string - use secure defaults
        if v is None or v == "" or (isinstance(v, str) and not v.strip()):
            return [
                "https://control.brain.falklabs.de",
                "https://axe.brain.falklabs.de",
            ]

        # Already a list (from JSON parsing)
        if isinstance(v, list):
            # SECURITY-001: Reject wildcard in production
            if "*" in v:
                raise ValueError("CORS wildcard '*' is not allowed in production (SECURITY-001)")
            return v

        # String value
        if isinstance(v, str):
            # SECURITY-001: Reject wildcard
            if v.strip() == "*":
                raise ValueError("CORS wildcard '*' is not allowed in production (SECURITY-001)")
            # CSV string
            return [origin.strip() for origin in v.split(",") if origin.strip()]

        # Fallback to secure defaults
        return [
            "https://control.brain.falklabs.de",
            "https://axe.brain.falklabs.de",
        ]

    @field_validator("cors_origins", mode="after")
    @classmethod
    def ensure_list(cls, v):
        """Ensure cors_origins is always a list."""
        if isinstance(v, str):
            return [v]
        return v

@lru_cache
def get_settings() -> Settings:
    return Settings()
