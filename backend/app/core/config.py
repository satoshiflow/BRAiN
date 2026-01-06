from functools import lru_cache
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

    # CORS - Accepts both CSV string and JSON array
    cors_origins: list[str] = ["*"]

    @field_validator("cors_origins", mode="before")
    @classmethod
    def parse_cors_origins(cls, v):
        """Parse CORS origins from CSV string or JSON array."""
        if isinstance(v, str):
            # Split CSV string and strip whitespace
            return [origin.strip() for origin in v.split(",") if origin.strip()]
        return v

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"

@lru_cache
def get_settings() -> Settings:
    return Settings()
