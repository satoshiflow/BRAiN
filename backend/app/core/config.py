from functools import lru_cache
from typing import Union
from pydantic import field_validator
from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    app_name: str = "BRAiN Core v1.0"
    environment: str = "local"

    api_prefix: str = "/api"

    # Database
    db_url: str = "postgresql+asyncpg://brain:brain@localhost:5432/brain"

    # Redis
    redis_url: str = "redis://localhost:6379/0"

    # CORS - Accepts CSV string, JSON array, or wildcard
    # Type as Union to prevent Pydantic from auto-parsing as JSON before validation
    cors_origins: Union[str, list[str]] = "*"

    @field_validator("cors_origins", mode="before")
    @classmethod
    def parse_cors_origins(cls, v):
        """Parse CORS origins from CSV string, JSON array, or handle empty/None."""
        # Handle None or empty string - default to wildcard
        if v is None or v == "" or (isinstance(v, str) and not v.strip()):
            return ["*"]

        # Already a list (from JSON parsing)
        if isinstance(v, list):
            return v

        # String value
        if isinstance(v, str):
            # Wildcard
            if v.strip() == "*":
                return ["*"]
            # CSV string
            return [origin.strip() for origin in v.split(",") if origin.strip()]

        # Fallback to wildcard for any other type
        return ["*"]

    @field_validator("cors_origins", mode="after")
    @classmethod
    def ensure_list(cls, v):
        """Ensure cors_origins is always a list."""
        if isinstance(v, str):
            return [v]
        return v

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"

@lru_cache
def get_settings() -> Settings:
    return Settings()
