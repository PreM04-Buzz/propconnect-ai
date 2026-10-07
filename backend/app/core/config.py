from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """App settings, read from environment variables or backend/.env."""

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    app_name: str = "PropConnect AI"
    database_url: str = "postgresql+psycopg://propconnect:propconnect@localhost:5432/propconnect"
    jwt_secret: str = "dev-only-insecure-secret-change-me-before-deploy"
    jwt_algorithm: str = "HS256"
    jwt_expire_minutes: int = 60
    cors_origins: str = "http://localhost:5173"
    admin_email: str = "admin@propconnect-demo.com"
    admin_password: str = "change-me-now"
    demo_password: str = "DemoAgent2026"
    # AI Next Step. Leave the key blank to use the rule-based fallback only.
    openai_api_key: str = ""
    openai_model: str = "gpt-4o-mini"
    openai_base_url: str = "https://api.openai.com/v1"
    ai_timeout_seconds: float = 20.0

    @property
    def cors_origin_list(self) -> list[str]:
        return [o.strip() for o in self.cors_origins.split(",") if o.strip()]


@lru_cache
def get_settings() -> Settings:
    return Settings()
