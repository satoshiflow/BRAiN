from functools import lru_cache
from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    app_name: str = "BRAiN Core v1.0"
    environment: str = "local"

    api_prefix: str = "/api"

    # Database
    db_url: str = "postgresql+asyncpg://brain:brain@localhost:5432/brain"

    # Redis
    redis_url: str = "redis://localhost:6379/0"

    # CORS
    cors_origins: list[str] = ["*"]

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"

@lru_cache
def get_settings() -> Settings:
    return Settings()
