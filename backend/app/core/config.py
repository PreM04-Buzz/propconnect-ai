from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """App settings, read from environment variables or backend/.env."""

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    app_name: str = "PropConnect AI"
    environment: str = "development"  # set to "production" on a real server
    database_url: str = "postgresql+psycopg://propconnect:propconnect@localhost:5432/propconnect"
    jwt_secret: str = "dev-only-insecure-secret-change-me-before-deploy"  # same as DEV_SECRET below
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
    login_max_attempts: int = 5
    login_window_seconds: int = 60

    @property
    def cors_origin_list(self) -> list[str]:
        return [o.strip() for o in self.cors_origins.split(",") if o.strip()]


@lru_cache
def get_settings() -> Settings:
    return Settings()


DEV_SECRET = "dev-only-insecure-secret-change-me-before-deploy"


def check_production_settings(settings: Settings) -> None:
    """Refuse to start a production server with the development defaults."""
    if settings.environment.lower() != "production":
        return
    if settings.jwt_secret == DEV_SECRET or len(settings.jwt_secret) < 32:
        raise RuntimeError("Set a long random JWT_SECRET before running in production.")
    if settings.admin_password == "change-me-now":
        raise RuntimeError("Change ADMIN_PASSWORD before running in production.")
