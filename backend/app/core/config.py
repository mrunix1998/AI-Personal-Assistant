from functools import lru_cache
from pydantic_settings import BaseSettings, SettingsConfigDict

class Settings(BaseSettings):
    app_name: str = "AI Personal Assistant"
    api_v1_prefix: str = "/api/v1"
    database_url: str
    redis_url: str = "redis://redis:6379/0"
    secret_key: str
    access_token_expire_minutes: int = 43200
    token_encryption_key: str
    google_client_id: str = ""
    google_client_secret: str = ""
    google_redirect_uri: str = "http://localhost:8000/api/v1/integrations/google/callback"
    n8n_base_url: str = "http://n8n:5678"

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

@lru_cache
def get_settings() -> Settings:
    return Settings()
