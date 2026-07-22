from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    environment: str = "development"
    database_url: str = "sqlite:///./crawler_api.db"
    redis_url: str = "redis://localhost:6379/0"
    jwt_secret: str = "development-only-change-me-with-at-least-32-bytes"
    credential_encryption_key: str = "MDEyMzQ1Njc4OWFiY2RlZjAxMjM0NTY3ODlhYmNkZWY="
    admin_email: str = "admin@example.com"
    admin_password: str = "change-me-now"
    cors_origins: str = "http://localhost:5173"


@lru_cache
def get_settings() -> Settings:
    return Settings()
