from functools import lru_cache

from pydantic import field_validator
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
    # Automatic emails go through Brevo's web API (Render's free plan blocks normal SMTP).
    # Leave BREVO_API_KEY empty and nothing is sent; assignments still work.
    brevo_api_key: str | None = None
    email_from_address: str | None = None   # a sender address verified in Brevo
    email_from_name: str = "PropConnect AI"
    email_timeout_seconds: float = 10.0
    # Where the website lives, for links in emails (portal invitations).
    app_url: str = "http://localhost:5173"
    portal_invite_days: int = 7
    login_max_attempts: int = 5
    login_window_seconds: int = 60
    # Each user can ask the AI this many times per hour. Protects the OpenAI bill on a public site.
    ai_requests_per_hour: int = 30

    @field_validator("database_url")
    @classmethod
    def use_psycopg_driver(cls, v: str) -> str:
        """Hosted databases (Neon, Render, Heroku) hand out postgres:// or postgresql:// URLs.
        SQLAlchemy needs to be told to use the psycopg 3 driver we install."""
        for prefix in ("postgres://", "postgresql://"):
            if v.startswith(prefix):
                return "postgresql+psycopg://" + v[len(prefix):]
        return v

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
