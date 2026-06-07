from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    app_name: str = "AI Personal Assistant"
    environment: str = "local"
    api_v1_prefix: str = "/api/v1"
    database_url: str
    redis_url: str
    secret_key: str
    access_token_expire_minutes: int = 60
    token_encryption_key: str

    google_client_id: str = ""
    google_client_secret: str = ""
    google_redirect_uri: str = "http://localhost:8000/api/v1/integrations/google/callback"

    n8n_base_url: str = "http://n8n:5678"
    n8n_daily_summary_webhook_path: str = "/webhook/daily-summary"
    n8n_ai_planning_webhook_path: str = "/webhook/ai-planning"
    n8n_unified_agenda_webhook_path: str = "/webhook/unified-agenda"
    n8n_webhook_secret: str = "local-dev-secret"

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8")


@lru_cache
def get_settings() -> Settings:
    return Settings()
