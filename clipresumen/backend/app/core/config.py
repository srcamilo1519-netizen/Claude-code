"""Application configuration.

Settings are loaded from environment variables (and a local `.env` file when
present). Defaults are dev-friendly so the skeleton boots without a fully
populated environment, but secrets must be set for real use.
"""

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
        case_sensitive=False,
    )

    # ── App ──────────────────────────────────────────────────────
    app_name: str = "ClipResumen API"
    app_version: str = "0.1.0"

    # ── Database ─────────────────────────────────────────────────
    database_url: str = (
        "postgresql+psycopg2://clipresumen:changeme@localhost:5432/clipresumen"
    )

    # ── Anthropic / Claude ───────────────────────────────────────
    anthropic_api_key: str = ""
    # Model used for summarization. Sonnet 4.6 supports structured outputs.
    summarizer_model: str = "claude-sonnet-4-6"

    # ── Auth (used from Fase 4 onward) ───────────────────────────
    jwt_secret: str = "change-me"
    jwt_algorithm: str = "HS256"
    access_token_expire_minutes: int = 30
    refresh_token_expire_days: int = 7

    # ── Stripe (Fase 6) ──────────────────────────────────────────
    # Usa claves de TEST de Stripe (sk_test_… / whsec_… / price_… de test)
    # mientras desarrollas. Para PRODUCCIÓN reemplaza estos valores en tu
    # `.env` por las claves LIVE (sk_live_…) — no cambies nada en el código.
    stripe_secret_key: str = ""
    stripe_webhook_secret: str = ""
    stripe_price_pro: str = ""
    stripe_price_business: str = ""
    # URL pública del frontend, usada para los redirects de checkout/portal.
    frontend_base_url: str = "http://localhost:3000"

    # ── CORS ─────────────────────────────────────────────────────
    cors_origins: str = "http://localhost:3000"

    @property
    def cors_origins_list(self) -> list[str]:
        return [o.strip() for o in self.cors_origins.split(",") if o.strip()]


settings = Settings()
