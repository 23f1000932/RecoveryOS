"""
RecoveryOS — Application Configuration

All environment variables are loaded and validated here using pydantic-settings.
Fail-fast at startup if required variables are missing.
"""

from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    # ── Database ───────────────────────────────────────────────────────────────
    database_url: str = ""

    # ── AI ────────────────────────────────────────────────────────────────────
    gemini_api_key: str = ""

    # ── Payments ──────────────────────────────────────────────────────────────
    razorpay_key_id: str = ""
    razorpay_key_secret: str = ""
    razorpay_webhook_secret: str = ""

    # ── App ───────────────────────────────────────────────────────────────────
    environment: str = "development"
    log_level: str = "INFO"

    # ── ML ────────────────────────────────────────────────────────────────────
    model_path: str = ""

    # ── Policy ────────────────────────────────────────────────────────────────
    policy_path: str = "policies/recovery_policy.yaml"

    # ── API ───────────────────────────────────────────────────────────────────
    api_version: str = "1.0.0"
    cors_origins: list[str] = ["http://localhost:5173", "http://localhost:3000"]

    @property
    def is_production(self) -> bool:
        return self.environment == "production"

    @property
    def is_development(self) -> bool:
        return self.environment == "development"

    @property
    def gemini_available(self) -> bool:
        return bool(self.gemini_api_key)

    @property
    def razorpay_available(self) -> bool:
        return bool(self.razorpay_key_id and self.razorpay_key_secret)

    @property
    def database_available(self) -> bool:
        return bool(self.database_url)


@lru_cache
def get_settings() -> Settings:
    """
    Returns cached application settings.
    Call this function everywhere instead of importing Settings directly.
    """
    return Settings()
