from pydantic_settings import BaseSettings, SettingsConfigDict
from typing import List


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",  # .env contains vars for other services (NAS, MinIO, etc.)
    )

    # Database
    DATABASE_URL: str

    # Auth
    SECRET_KEY: str
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60

    # External services
    REDIS_URL: str = "redis://redis:6379"
    LIGHTRAG_URL: str = "http://lightrag:9621"
    LIGHTRAG_TIMEOUT_SECONDS: float = 300.0
    GRAPHITI_URL: str = "http://graphiti-service:9622"
    SEQ_URL: str = "http://seq:5341"
    ADAPTIVE_CHUNKING_ARTIFACT_DIR: str = "/app/docs/experiments/artifacts/adaptive-chunking"

    # CORS
    CORS_ORIGINS: List[str] = ["http://localhost:3000"]

    # Rate limiting
    MCP_RATE_LIMIT_PER_MINUTE: int = 100


settings = Settings()
